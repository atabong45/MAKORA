"""
MODULE : core/detector.py
DESCRIPTION : Moteur de détection d'anomalies — Pattern Strategy.
              Quatre stratégies interchangeables (Isolation Forest, LOF,
              One-Class SVM, Deep Isolation Forest) exposées via une interface
              commune. Le Kernel n'utilise que `Detector` et `DetectorStrategy` ;
              le choix de l'algorithme est externalisé dans le YAML du module.

RÉFÉRENCES ACADÉMIQUES :
- [Liu2008] Liu et al. (2008). Isolation Forest. ICDM 2008.
  → Stratégie legacy, conservée pour la comparaison formelle ADR-006.
    Compatible SHAP TreeExplainer [Lundberg2020].
- [Xu2023] Xu et al. (2023). Deep Isolation Forest for Anomaly Detection.
  IEEE Transactions on Knowledge and Data Engineering.
  → Stratégie de PRODUCTION retenue après validation H0 (Φ=0.4660 Santé,
    Φ=0.4697 Auto). Convention de score OPPOSÉE à sklearn : valeur élevée
    = anomalie. Seuils calibrés sur val set [Davis2006].
- [Breunig2000] Breunig et al. (2000). LOF. SIGMOD.
  → Baseline de comparaison ADR-006. Capte les anomalies locales.
- [Schölkopf2001] Schölkopf et al. (2001). One-Class SVM. Neural Computation.
  → Baseline de comparaison ADR-006.
- [Goldstein2016] Goldstein & Uchida (2016). PLOS ONE.
  → Justifie la comparaison formelle IF vs LOF vs OC-SVM vs DIF.
- [GoF1994] Gamma et al. (1994). Design Patterns. chap. Strategy.
  → Pattern permettant de substituer l'algorithme sans modifier le Pipeline.
- [Amershi2019] Amershi et al. (2019). Software Engineering for ML. ICSE.
  → Recommande l'isolation du code de modélisation.
- [Bauder2017] Bauder & Khoshgoftaar (2017). ICMLA.
  → Taux de fraude estimé 3-10% → contamination par défaut 0.08.
- [Davis2006] Davis & Goadrich (2006). PR vs ROC curves. ICML.
  → Justifie la calibration de seuil sur val set par maximisation F1/Φ-score.
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML. NeurIPS.
  → Externaliser tout hyperparamètre, ne jamais hardcoder.

DÉCISIONS DE CONCEPTION :
- Convention de score hétérogène (documentée explicitement) :
    • IF / LOF / OC-SVM : score normalisé [0,1] via sigmoid inversée.
    • DIFStrategy [Xu2023] : score BRUT PyOD — anomalie = valeur ÉLEVÉE.
      Ne pas comparer directement avec les scores IF normalisés.
- Seuils DIF calibrés sur val set [Davis2006] — immuables :
    sante : 0.349775 (phi_optimal)       FPR=2.18%
    auto  : 0.341498 (fpr5_constrained)  FPR=4.79%
- `load_strategy_from_joblib()` détecte automatiquement le type de modèle
  persisté (DIF vs IF) et instancie la bonne stratégie [Sculley2015].
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import LocalOutlierFactor
from sklearn.svm import OneClassSVM

from core.exceptions import MAKORAError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class DetectorNotFittedError(MAKORAError):
    """Levée si score/predict appelé avant fit."""


class DetectorConfigError(MAKORAError):
    """Levée si la configuration YAML est invalide."""


class SHAPNotSupportedError(MAKORAError):
    """Levée si get_underlying_model() appelé sur une stratégie sans SHAP."""


# ---------------------------------------------------------------------------
# Interface — DetectorStrategy
# ---------------------------------------------------------------------------

class DetectorStrategy(ABC):
    """
    Interface de détection d'anomalies — Pattern Strategy [GoF1994].

    Le Pipeline et le Detector Context ne connaissent QUE cette interface.

    CONVENTION DE SCORE — deux familles (documenter explicitement) :
    - Stratégies sklearn (IF, LOF, OC-SVM) :
        score normalisé dans [0, 1] via sigmoid inversée.
        1.0 = anomalie certaine, 0.0 = normal certain.
    - DIFStrategy [Xu2023] :
        score BRUT PyOD, non borné. Anomalie = valeur ÉLEVÉE.
        Ne pas comparer directement avec les scores IF normalisés.
    """

    @abstractmethod
    def fit(self, X: np.ndarray) -> "DetectorStrategy":
        """Entraîne la stratégie. Retourne self pour le chaînage."""
        ...

    @abstractmethod
    def score(self, X: np.ndarray) -> np.ndarray:
        """
        Retourne un vecteur de scores d'anomalie.
        Convention selon la famille — voir docstring de classe.
        """
        ...

    @abstractmethod
    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        """Retourne un tableau booléen : True = anomalie détectée."""
        ...

    @abstractmethod
    def get_name(self) -> str:
        """Identifiant lisible de l'algorithme (ex: 'isolation_forest')."""
        ...

    @abstractmethod
    def supports_shap(self) -> bool:
        """
        True si la stratégie est compatible avec SHAP TreeExplainer.
        Seul IsolationForestStrategy retourne True.
        [Lundberg2020] TreeExplainer réservé aux ensembles d'arbres.
        """
        ...

    def get_underlying_model(self) -> Any:
        """
        Retourne le modèle sklearn sous-jacent pour SHAP TreeExplainer.
        Soulève SHAPNotSupportedError si supports_shap() == False.
        """
        raise SHAPNotSupportedError(
            f"La stratégie '{self.get_name()}' ne supporte pas SHAP TreeExplainer. "
            f"Utiliser IsolationForestStrategy pour l'explicabilité."
        )

    def save(self, path: Path) -> None:
        """Persiste le modèle entraîné via joblib."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        logger.info("Stratégie '%s' sauvegardée → %s", self.get_name(), path)

    @classmethod
    def load(cls, path: Path) -> "DetectorStrategy":
        """Charge un modèle persisté via joblib."""
        strategy = joblib.load(Path(path))
        logger.info("Stratégie chargée depuis %s", path)
        return strategy

    @staticmethod
    def _sigmoid_normalize(raw_scores: np.ndarray) -> np.ndarray:
        """
        Normalise les scores sklearn vers [0, 1] via sigmoid inversée.
        Convention sklearn : score négatif = anomalie.
        Formule : 1 / (1 + exp(raw * 10)).
        Facteur 10 calibré sur la plage naturelle [-0.5, 0.5] de l'IF [Liu2008 Fig.2].
        """
        return 1.0 / (1.0 + np.exp(raw_scores * 10))


# ---------------------------------------------------------------------------
# Stratégie 1 — Isolation Forest (LEGACY / COMPARAISON)
# ---------------------------------------------------------------------------

class IsolationForestStrategy(DetectorStrategy):
    """
    [Liu2008] Isolation Forest.

    Stratégie legacy conservée pour la comparaison formelle [ADR-006] et la
    rétrocompatibilité. Remplacée en production par DIFStrategy [Xu2023]
    après validation H0 (positive transfer [Caruana1997]).

    Compatible SHAP TreeExplainer → supports_shap() == True.
    Contamination 0.08 : [Bauder2017] estime le taux de fraude à 3-10%.
    """

    def __init__(
        self,
        n_estimators: int = 200,
        contamination: float = 0.08,
        max_samples: str | int = "auto",
        random_state: int = 42,
        n_jobs: int = -1,
    ) -> None:
        # [Sculley2015] — valeurs par défaut overridées par le YAML du module.
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.max_samples = max_samples
        self.random_state = random_state
        self.n_jobs = n_jobs
        self._model: Optional[IsolationForest] = None

    def fit(self, X: np.ndarray) -> "IsolationForestStrategy":
        """[Liu2008] : O(n log n), random_state=42 pour reproductibilité."""
        self._model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            max_samples=self.max_samples,
            random_state=self.random_state,
            n_jobs=self.n_jobs,
        )
        self._model.fit(X)
        logger.info(
            "IsolationForest entraîné : n=%d, contamination=%.3f",
            X.shape[0], self.contamination,
        )
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        """Scores normalisés [0,1] via sigmoid inversée [Liu2008 Fig.2]."""
        self._assert_fitted()
        raw = self._model.decision_function(X)  # type: ignore[union-attr]
        return self._sigmoid_normalize(raw)

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        return self.score(X) >= threshold

    def get_name(self) -> str:
        return "isolation_forest"

    def supports_shap(self) -> bool:
        return True

    def get_underlying_model(self) -> IsolationForest:
        """Retourne le modèle sklearn pour SHAP TreeExplainer [Lundberg2020]."""
        self._assert_fitted()
        return self._model  # type: ignore[return-value]

    def _assert_fitted(self) -> None:
        if self._model is None:
            raise DetectorNotFittedError(
                "IsolationForestStrategy non entraîné. Appelez fit() d'abord."
            )


# ---------------------------------------------------------------------------
# Stratégie 2 — Local Outlier Factor (COMPARAISON)
# ---------------------------------------------------------------------------

class LOFStrategy(DetectorStrategy):
    """
    [Breunig2000] Local Outlier Factor — comparaison formelle ADR-006.

    Capte les anomalies locales (densité relative vs k voisins) que l'IF
    peut manquer. Non retenu en production : O(n²), incompatible SHAP.
    [Goldstein2016] : LOF surpasse IF sur les fraudes prestataire ciblées.
    """

    def __init__(
        self,
        n_neighbors: int = 20,
        contamination: float = 0.08,
        n_jobs: int = -1,
    ) -> None:
        self.n_neighbors = n_neighbors
        self.contamination = contamination
        self.n_jobs = n_jobs
        self._model: Optional[LocalOutlierFactor] = None

    def fit(self, X: np.ndarray) -> "LOFStrategy":
        """[Breunig2000] : novelty=True requis pour scorer de nouveaux points."""
        self._model = LocalOutlierFactor(
            n_neighbors=self.n_neighbors,
            contamination=self.contamination,
            novelty=True,
            n_jobs=self.n_jobs,
        )
        self._model.fit(X)
        logger.info(
            "LOF entraîné : n=%d, k=%d, contamination=%.3f",
            X.shape[0], self.n_neighbors, self.contamination,
        )
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        self._assert_fitted()
        raw = self._model.decision_function(X)  # type: ignore[union-attr]
        return self._sigmoid_normalize(raw)

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        return self.score(X) >= threshold

    def get_name(self) -> str:
        return "lof"

    def supports_shap(self) -> bool:
        # [Lundberg2020] : TreeExplainer réservé aux ensembles d'arbres.
        return False

    def _assert_fitted(self) -> None:
        if self._model is None:
            raise DetectorNotFittedError(
                "LOFStrategy non entraîné. Appelez fit() d'abord."
            )


# ---------------------------------------------------------------------------
# Stratégie 3 — One-Class SVM (COMPARAISON)
# ---------------------------------------------------------------------------

class OneClassSVMStrategy(DetectorStrategy):
    """
    [Schölkopf2001] One-Class SVM — comparaison formelle ADR-006.

    Modélise la frontière de la classe normale dans l'espace noyau RBF.
    Non retenu en production : O(n²-n³), requiert StandardScaler [Sculley2015].
    nu ≈ contamination pour cohérence de comparaison avec IF et LOF.
    """

    def __init__(
        self,
        nu: float = 0.08,
        kernel: str = "rbf",
        gamma: str = "scale",
    ) -> None:
        self.nu = nu
        self.kernel = kernel
        self.gamma = gamma
        self._model: Optional[OneClassSVM] = None
        self._scaler = None

    def fit(self, X: np.ndarray) -> "OneClassSVMStrategy":
        """[Schölkopf2001] : StandardScaler obligatoire avant entraînement."""
        from sklearn.preprocessing import StandardScaler
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(X)
        self._model = OneClassSVM(nu=self.nu, kernel=self.kernel, gamma=self.gamma)
        self._model.fit(X_scaled)
        logger.info(
            "OneClassSVM entraîné : n=%d, nu=%.3f, kernel=%s",
            X.shape[0], self.nu, self.kernel,
        )
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        self._assert_fitted()
        X_scaled = self._scaler.transform(X)  # type: ignore[union-attr]
        raw = self._model.decision_function(X_scaled)  # type: ignore[union-attr]
        return self._sigmoid_normalize(raw)

    def predict(self, X: np.ndarray, threshold: float = 0.5) -> np.ndarray:
        return self.score(X) >= threshold

    def get_name(self) -> str:
        return "one_class_svm"

    def supports_shap(self) -> bool:
        return False

    def _assert_fitted(self) -> None:
        if self._model is None:
            raise DetectorNotFittedError(
                "OneClassSVMStrategy non entraîné. Appelez fit() d'abord."
            )


# ---------------------------------------------------------------------------
# Stratégie 4 — Deep Isolation Forest (PRODUCTION)
# ---------------------------------------------------------------------------

class DIFStrategy(DetectorStrategy):
    """
    [Xu2023] Deep Isolation Forest — stratégie de PRODUCTION de MAKORA.

    Projette les données dans des sous-espaces aléatoires via un réseau de
    neurones avant l'isolation — plus discriminant qu'IF classique sur les
    espaces de haute dimension [Xu2023 §4].

    Architecture retenue : [64, 32] — configuration phi_optimal issue de la
    comparaison bootstrap sur 10 candidats (t13_bootstrap, 08/06/2026).
    Expérience H0 validée : Φ=0.4660 (Santé), Φ=0.4697 (Auto) [Caruana1997].

    CONVENTION DE SCORE (différente des stratégies sklearn) :
        decision_function() → valeur ÉLEVÉE = anomalie [Xu2023].
        score() retourne les valeurs BRUTES PyOD, sans normalisation.
        Seuil calibré sur val set [Davis2006], non comparable au [0,1] de l'IF.

    Seuils immuables (calibrés val set, stratégie phi_optimal/fpr5) :
        sante : 0.349775  FPR=2.18%
        auto  : 0.341498  FPR=4.79%

    supports_shap() == False → KernelSHAP requis dans core/explainer.py.
    [Lundberg2017] : KernelExplainer est agnostique au type de modèle.
    """

    def __init__(
        self,
        hidden_neurons: list[int] | None = None,
        contamination: float = 0.07,
        threshold: float = 0.35,
        random_state: int = 42,
        device: str = "cpu",
    ) -> None:
        # [Sculley2015] — paramètres externalisés, jamais hardcodés dans le Kernel.
        self._hidden_neurons = hidden_neurons or [64, 32]
        self._contamination = contamination
        self._threshold = threshold  # Seuil calibré val set [Davis2006]
        self._random_state = random_state
        self._device = device
        self._model = None

    def fit(self, X: np.ndarray) -> "DIFStrategy":
        """
        Entraîne le Deep Isolation Forest.
        [Xu2023] : représentation neuronale des données avant isolation.
        random_state=42 pour reproductibilité des expériences H0.
        """
        from pyod.models.dif import DIF  # Import local — pyod optionnel en test
        self._model = DIF(
            hidden_neurons=self._hidden_neurons,
            contamination=self._contamination,
            random_state=self._random_state,
            device=self._device,
        )
        self._model.fit(X)
        logger.info(
            "DIF entraîné : n=%d, architecture=%s, contamination=%.3f",
            X.shape[0], self._hidden_neurons, self._contamination,
        )
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        """
        Scores BRUTS PyOD — anomalie = valeur ÉLEVÉE [Xu2023].
        NE PAS normaliser : les seuils calibrés (0.349775 / 0.341498) sont
        des scores bruts. Incompatible avec les scores IF normalisés [0,1].
        """
        self._assert_fitted()
        return self._model.decision_function(X)

    def predict(self, X: np.ndarray, threshold: float | None = None) -> np.ndarray:
        """
        True = anomalie. Seuil sur score brut PyOD.
        threshold=None → utilise self._threshold (calibré [Davis2006]).
        """
        thr = threshold if threshold is not None else self._threshold
        return (self.score(X) >= thr).astype(bool)

    def get_name(self) -> str:
        return "dif"

    def supports_shap(self) -> bool:
        # DIF est un réseau de neurones — TreeExplainer inapplicable.
        # KernelSHAP [Lundberg2017] requis — voir core/explainer.py.
        return False

    def _assert_fitted(self) -> None:
        if self._model is None:
            raise DetectorNotFittedError(
                "DIFStrategy non entraîné. Appelez fit(X_train) d'abord."
            )


# ---------------------------------------------------------------------------
# Context — Detector
# ---------------------------------------------------------------------------

class Detector:
    """
    Contexte du Pattern Strategy [GoF1994] — délègue à une DetectorStrategy.

    Responsabilités :
    - Tenir la stratégie active et le seuil de décision.
    - Exposer une interface unique fit/score/predict au Pipeline.
    - Permettre le swap de stratégie à chaud (expériences comparatives).

    Note sur le seuil pour DIF : threshold = 0.349775 (Santé) ou 0.341498 (Auto).
    Ces valeurs sont calibrées sur val set [Davis2006] et externalisées en YAML.
    """

    def __init__(
        self,
        strategy: DetectorStrategy,
        threshold: float = 0.5,
    ) -> None:
        """
        Args:
            strategy: Algorithme de détection actif.
            threshold: Seuil de décision — DOIT venir du YAML [Sculley2015].
                       Pour DIF : 0.349775 (Santé) ou 0.341498 (Auto).
                       [Bauder2017] : seuil bas → recall élevé, FPR élevé.
        """
        self._strategy = strategy
        self.threshold = threshold

    def fit(self, X: np.ndarray) -> "Detector":
        """Entraîne la stratégie active."""
        self._strategy.fit(X)
        return self

    def score(self, X: np.ndarray) -> np.ndarray:
        """Délègue à la stratégie — voir convention de score de la classe."""
        return self._strategy.score(X)

    def predict(self, X: np.ndarray) -> np.ndarray:
        """True = anomalie (score >= self.threshold)."""
        return self._strategy.predict(X, threshold=self.threshold)

    @property
    def strategy(self) -> DetectorStrategy:
        return self._strategy

    @strategy.setter
    def strategy(self, new_strategy: DetectorStrategy) -> None:
        """Swap de stratégie pour les expériences comparatives."""
        logger.info(
            "Swap stratégie : %s → %s",
            self._strategy.get_name(), new_strategy.get_name(),
        )
        self._strategy = new_strategy

    def get_name(self) -> str:
        return self._strategy.get_name()

    def supports_shap(self) -> bool:
        return self._strategy.supports_shap()

    def get_underlying_model(self) -> Any:
        """Expose le modèle sous-jacent pour SHAP (délégation)."""
        return self._strategy.get_underlying_model()

    def save(self, path: Path) -> None:
        self._strategy.save(path)

    @classmethod
    def load(cls, path: Path, threshold: float = 0.5) -> "Detector":
        strategy = DetectorStrategy.load(path)
        return cls(strategy=strategy, threshold=threshold)

    def __repr__(self) -> str:
        return (
            f"Detector(strategy={self.get_name()!r}, "
            f"threshold={self.threshold}, "
            f"shap_compatible={self.supports_shap()})"
        )


# ---------------------------------------------------------------------------
# Factory — build_detector
# ---------------------------------------------------------------------------

_STRATEGY_REGISTRY: dict[str, type[DetectorStrategy]] = {
    "isolation_forest": IsolationForestStrategy,
    "lof":              LOFStrategy,
    "one_class_svm":    OneClassSVMStrategy,
    "dif":              DIFStrategy,
}


def build_detector(config: dict) -> Detector:
    """
    Construit un Detector à partir d'un dictionnaire de configuration YAML.

    Format pour DIF (section `detection` du YAML du module) :
        detection:
          algorithm: dif
          hidden_neurons: [64, 32]
          contamination: 0.068      # 0.068 Santé / 0.100 Auto
          threshold: 0.349775       # calibré val set [Davis2006]
          random_state: 42
          device: cpu

    [Sculley2015] : externaliser tous les hyperparamètres.

    Raises:
        DetectorConfigError: si l'algorithme est inconnu.
    """
    algorithm    = config.get("algorithm", "isolation_forest")
    contamination = float(config.get("contamination", 0.08))
    threshold    = float(config.get("threshold", 0.5))
    random_state = int(config.get("random_state", 42))

    if algorithm not in _STRATEGY_REGISTRY:
        raise DetectorConfigError(
            f"Algorithme inconnu : '{algorithm}'. "
            f"Supportés : {list(_STRATEGY_REGISTRY.keys())}"
        )

    if algorithm == "isolation_forest":
        strategy: DetectorStrategy = IsolationForestStrategy(
            n_estimators=int(config.get("n_estimators", 200)),
            contamination=contamination,
            random_state=random_state,
        )
    elif algorithm == "lof":
        strategy = LOFStrategy(
            n_neighbors=int(config.get("n_neighbors", 20)),
            contamination=contamination,
        )
    elif algorithm == "one_class_svm":
        strategy = OneClassSVMStrategy(
            nu=contamination,
            kernel=config.get("kernel", "rbf"),
        )
    elif algorithm == "dif":
        strategy = DIFStrategy(
            hidden_neurons=config.get("hidden_neurons", [64, 32]),
            contamination=contamination,
            threshold=threshold,  # seuil calibré passé à la stratégie
            random_state=random_state,
            device=config.get("device", "cpu"),
        )

    logger.info(
        "Detector construit : algo=%s, contamination=%.3f, threshold=%.6f",
        algorithm, contamination, threshold,
    )
    return Detector(strategy=strategy, threshold=threshold)


# ---------------------------------------------------------------------------
# Utilitaire — chargement depuis un bundle joblib
# ---------------------------------------------------------------------------

# Seuils calibrés sur val set [Davis2006] — immuables, ne pas modifier.
_CALIBRATED_THRESHOLDS_DIF: dict[str, float] = {
    "sante": 0.349775,   # phi_optimal — FPR=2.18%
    "auto":  0.341498,   # fpr5_constrained — FPR=4.79%
}


def load_strategy_from_joblib(
    model_path: Path,
    branch: str,
) -> DetectorStrategy:
    """
    Charge une stratégie depuis un bundle joblib et détecte automatiquement
    le type de modèle (DIF vs IsolationForest) [Sculley2015].

    Le bundle peut être :
    - Un objet DetectorStrategy directement (via strategy.save())
    - Un dictionnaire {"model": <pyod.DIF|sklearn.IF>, ...} (format scripts H0)

    Args:
        model_path : Chemin vers le fichier .joblib entraîné.
        branch     : "sante" ou "auto" — détermine le seuil DIF calibré.

    Returns:
        DetectorStrategy configurée et prête à l'usage.

    Raises:
        DetectorConfigError: si le type de modèle dans le bundle est inconnu.
    """
    bundle = joblib.load(Path(model_path))

    # Gestion du format dict {"model": ...} produit par les scripts H0
    model = bundle.get("model", bundle) if isinstance(bundle, dict) else bundle
    model_type = type(model).__name__

    if model_type == "DIF":
        # [Xu2023] Deep Isolation Forest — seuil calibré par branche [Davis2006]
        threshold = _CALIBRATED_THRESHOLDS_DIF.get(branch, 0.35)
        strategy = DIFStrategy(threshold=threshold)
        strategy._model = model
        logger.info(
            "DIF chargé depuis %s (branche=%s, seuil=%.6f)",
            model_path, branch, threshold,
        )

    elif model_type == "IsolationForest":
        # [Liu2008] IF sklearn brut — seuil normalisé [0,1]
        strategy = IsolationForestStrategy()
        strategy._model = model
        logger.info("IsolationForest chargé depuis %s", model_path)

    elif isinstance(model, DetectorStrategy):
        # Bundle déjà une DetectorStrategy persistée via strategy.save()
        strategy = model
        logger.info(
            "DetectorStrategy '%s' chargée depuis %s",
            strategy.get_name(), model_path,
        )

    else:
        raise DetectorConfigError(
            f"Type de modèle non supporté dans le bundle : '{model_type}'. "
            f"Types supportés : DIF, IsolationForest, DetectorStrategy."
        )

    return strategy