"""
MODULE : core/explainer.py
DESCRIPTION : Moteur d'explicabilité SHAP — supporte TreeExplainer (IF) et
              KernelExplainer (DIF et autres stratégies sans arbre).

RÉFÉRENCES ACADÉMIQUES :
- [Lundberg2017] Lundberg & Lee (2017). A unified approach to interpreting
  model predictions. NeurIPS.
  → Valeurs de Shapley : φᵢ = contribution marginale de la feature i.
    KernelSHAP est agnostique au type de modèle — applicable à DIF.
- [Lundberg2020] Lundberg et al. (2020). From local explanations to global
  understanding with explainable AI for trees. Nature MI.
  → TreeExplainer : O(T·L²) vs O(n²) pour KernelSHAP.
    Sur IF (n_estimators=200), TreeExplainer est ~50× plus rapide.
    Retenu pour IF ; KernelSHAP retenu pour DIF [Xu2023].
- [Xu2023] Xu et al. (2023). Deep Isolation Forest. IEEE TKDE.
  → DIF est un réseau de neurones — TreeExplainer inapplicable.
    KernelSHAP est la seule option générique [Lundberg2017].
- [Ribeiro2016] Ribeiro et al. (2016). "Why should I trust you?". KDD.
  → LIME est l'alternative à SHAP. Non retenu : moins cohérent
    théoriquement (approximation locale vs valeurs exactes de Shapley).
- [Chandola2009] Chandola et al. (2009). Anomaly Detection: A Survey.
  ACM Computing Surveys.
  → Souligne l'importance de l'explicabilité en contexte opérationnel.

DÉCISIONS DE CONCEPTION :
- Deux modes d'explicabilité selon la stratégie de détection :
    mode="tree"   → shap.TreeExplainer   (IsolationForestStrategy)
    mode="kernel" → shap.KernelExplainer (DIFStrategy, LOF, OC-SVM)
  Le branchement est automatique dans initialize() via supports_shap().
- SHAP calculé UNIQUEMENT sur les dossiers is_anomaly=True [Perf BNF-06].
  Sur 140k lignes à 8% de fraude (~11.2k anomalies), éviter le calcul
  SHAP sur 128.8k dossiers normaux est critique pour la latence.
- KernelSHAP : nsamples=100, l1_reg="aic" — compromis vitesse/précision
  (~1-3s par dossier). Calculé uniquement si is_anomaly=True [BNF-06].
- check_additivity=False requis pour IsolationForest (scores non-additifs).
  [Lundberg2020] §A.2 : approximation suffisante pour le ranking top-k.
- top_k=3 par défaut : le dashboard affiche 3 facteurs principaux pour ne
  pas surcharger le gestionnaire de sinistres.
- Explainer ne connaît pas le module métier — reçoit feature_names et la
  stratégie via le Plugin Contract [ADR-002].
- X_background : 100 dossiers normaux du train set, requis pour KernelSHAP.
  Persisté dans data/models/{branch}/shap_background.npy.
"""

from __future__ import annotations

import logging
from typing import Optional

import numpy as np

from core.data_models import FeatureSHAP
from core.detector import DetectorStrategy

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------

class ExplainerNotFittedError(Exception):
    """Levée si compute_top_k() appelé avant initialize()."""


# ---------------------------------------------------------------------------
# Explainer
# ---------------------------------------------------------------------------

class Explainer:
    """
    Moteur d'explicabilité SHAP.

    Supporte deux modes selon la stratégie de détection active :
    - mode="tree"   : shap.TreeExplainer  — IF classique, rapide [Lundberg2020].
    - mode="kernel" : shap.KernelExplainer — DIF et autres, générique [Lundberg2017].

    Cycle de vie :
        1. Explainer(strategy, feature_names)           ← construction
        2. .initialize(X_background=None)               ← sélectionne le mode
        3. .compute_top_k(X_row, k=3)                   ← appelé si is_anomaly
        4. .compute_batch_top_k(X, mask, k=3)           ← version batch
    """

    def __init__(
        self,
        strategy: DetectorStrategy,
        feature_names: list[str],
    ) -> None:
        """
        Args:
            strategy     : Stratégie de détection active (IF ou DIF ou autre).
            feature_names: Noms des features dans l'ordre des colonnes de X.
                           Provient de module.get_feature_columns().

        Note : la validation de supports_shap() est désormais dans initialize(),
        non à la construction. Cela permet d'utiliser KernelSHAP avec toute
        stratégie (DIF, LOF, OC-SVM) [Lundberg2017].
        """
        self._strategy = strategy
        self.feature_names = feature_names
        self._shap_explainer = None  # Initialisé dans .initialize()
        self._mode: Optional[str] = None  # "tree" ou "kernel"

    def initialize(self, X_background: Optional[np.ndarray] = None) -> "Explainer":
        """
        Initialise le bon explainer SHAP selon la stratégie active.

        - supports_shap()==True  → shap.TreeExplainer  (mode="tree")
          Rapide, O(T·L²), pré-calcule des structures internes [Lundberg2020].
        - supports_shap()==False → shap.KernelExplainer (mode="kernel")
          Générique, O(n²), requiert X_background [Lundberg2017].
          X_background = 100 dossiers normaux du train set.

        Args:
            X_background: Background set pour KernelSHAP (shape: 100 × n_features).
                          Ignoré si mode="tree". Obligatoire si mode="kernel".

        Raises:
            ValueError: si mode="kernel" et X_background est None.
            ImportError: si le package 'shap' n'est pas installé.
        """
        try:
            import shap
        except ImportError as e:
            raise ImportError(
                "Le package 'shap' est requis pour Explainer. "
                "Installer avec : pip install shap"
            ) from e

        if self._strategy.supports_shap():
            # [Lundberg2020] TreeExplainer — IF uniquement.
            model = self._strategy.get_underlying_model()
            self._shap_explainer = shap.TreeExplainer(model)
            self._mode = "tree"
            logger.info(
                "SHAP TreeExplainer initialisé pour stratégie '%s'",
                self._strategy.get_name(),
            )
        else:
            # [Lundberg2017] KernelExplainer — DIF, LOF, OC-SVM.
            if X_background is None:
                raise ValueError(
                    "KernelSHAP requiert X_background (100 dossiers normaux du "
                    "train set). Charger depuis data/models/{branch}/shap_background.npy. "
                    "[Lundberg2017] : le background set définit la valeur de référence φ₀."
                )
            self._shap_explainer = shap.KernelExplainer(
                self._strategy.score,
                X_background,
                link="identity",
            )
            self._mode = "kernel"
            logger.info(
                "SHAP KernelExplainer initialisé pour stratégie '%s' "
                "(background n=%d) [Lundberg2017]",
                self._strategy.get_name(),
                len(X_background),
            )

        return self

    # ------------------------------------------------------------------
    # Méthode interne partagée — calcul SHAP brut
    # ------------------------------------------------------------------

    def _compute_shap_values(self, X: np.ndarray) -> np.ndarray:
        """
        Calcule les valeurs SHAP brutes pour un batch X.

        Centralise le branchement tree/kernel pour éviter la duplication
        dans compute_top_k et compute_batch_top_k [Sculley2015].

        Retourne un np.ndarray de shape (n_samples, n_features).
        """
        if self._mode == "kernel":
            # [Lundberg2017] nsamples=100 : compromis vitesse/précision (~1-3s/obs).
            # l1_reg="aic" : sélection automatique du sous-ensemble de features.
            sv = self._shap_explainer.shap_values(
                X, nsamples=100, l1_reg="aic"
            )
        else:
            # [Lundberg2020] check_additivity=False : IF scores non strictement additifs.
            sv = self._shap_explainer.shap_values(X, check_additivity=False)

        # Normalisation du format — certaines versions SHAP retournent une liste
        if isinstance(sv, list):
            return np.array(sv[0])
        return np.array(sv)

    # ------------------------------------------------------------------
    # compute_top_k — une observation
    # ------------------------------------------------------------------

    def compute_top_k(
        self,
        X_row: np.ndarray,
        k: int = 3,
    ) -> list[FeatureSHAP]:
        """
        Calcule les top-k features SHAP pour UNE observation.

        Appelé uniquement si is_anomaly=True (voir Pipeline) [BNF-06].
        [Lundberg2017] : φᵢ = contribution marginale de la feature i au
        score de sortie par rapport à la valeur moyenne (base value).

        Args:
            X_row: Vecteur de features. Shape (n_features,) ou (1, n_features).
            k    : Nombre de features à retourner (default=3).

        Returns:
            Liste de FeatureSHAP triée par |shap_value| décroissant.

        Raises:
            ExplainerNotFittedError: si initialize() n'a pas été appelé.
        """
        self._assert_initialized()

        # Normaliser la forme : (1, n_features) pour les deux explainers
        if X_row.ndim == 1:
            X_row = X_row.reshape(1, -1)

        shap_matrix = self._compute_shap_values(X_row)
        shap_row = shap_matrix.flatten()

        if len(shap_row) != len(self.feature_names):
            logger.warning(
                "Incohérence SHAP : %d valeurs pour %d features. "
                "Vérifier feature_names.",
                len(shap_row), len(self.feature_names),
            )

        # Trier par |φᵢ| décroissant — [Lundberg2017] : importance = |shap_value|
        abs_values = np.abs(shap_row)
        top_indices = np.argsort(abs_values)[::-1][:k]

        results: list[FeatureSHAP] = []
        for rank, idx in enumerate(top_indices, start=1):
            val = float(shap_row[idx])
            name = (
                self.feature_names[idx]
                if idx < len(self.feature_names)
                else f"feature_{idx}"
            )
            results.append(
                FeatureSHAP(
                    name=name,
                    shap_value=val,
                    direction="positive" if val > 0 else "negative",
                    rank=rank,
                )
            )

        logger.debug(
            "SHAP top-%d [mode=%s] : %s",
            k, self._mode,
            [(f.name, round(f.shap_value, 4)) for f in results],
        )
        return results

    # ------------------------------------------------------------------
    # compute_batch_top_k — batch d'observations
    # ------------------------------------------------------------------

    def compute_batch_top_k(
        self,
        X: np.ndarray,
        is_anomaly_mask: np.ndarray,
        k: int = 3,
    ) -> list[Optional[list[FeatureSHAP]]]:
        """
        Calcule SHAP top-k pour un batch, uniquement sur les anomalies.

        Optimisation [BNF-06] : SHAP calculé en une passe sur les
        N_anomalies observations (N_anomalies << N_total), puis les
        résultats sont re-mappés aux positions originales.

        Pour le mode kernel, chaque anomalie est traitée individuellement
        afin d'isoler la latence KernelSHAP aux seuls dossiers suspects.

        Args:
            X             : Matrice (N, n_features).
            is_anomaly_mask: Booléen (N,) — True = appliquer SHAP.
            k             : Top-k features.

        Returns:
            Liste de longueur N. Élément i = list[FeatureSHAP] si anomalie,
            sinon None.
        """
        self._assert_initialized()

        N = X.shape[0]
        results: list[Optional[list[FeatureSHAP]]] = [None] * N

        anomaly_indices = np.where(is_anomaly_mask)[0]
        if len(anomaly_indices) == 0:
            logger.debug("Aucune anomalie dans le batch — SHAP non calculé.")
            return results

        if self._mode == "tree":
            # TreeExplainer : calcul vectorisé sur tout le sous-batch [Lundberg2020].
            X_anomalies = X[anomaly_indices]
            shap_matrix = self._compute_shap_values(X_anomalies)

            for local_i, global_i in enumerate(anomaly_indices):
                shap_row = shap_matrix[local_i]
                results[global_i] = self._build_top_k_from_row(shap_row, k)

        else:
            # KernelExplainer : passe individuelle par anomalie.
            # [Lundberg2017] nsamples=100 — latence ~1-3s par dossier,
            # acceptable car SHAP calculé uniquement si is_anomaly=True [BNF-06].
            for global_i in anomaly_indices:
                results[global_i] = self.compute_top_k(X[global_i], k=k)

        logger.info(
            "SHAP batch [mode=%s] : %d anomalies / %d total — top-%d calculé.",
            self._mode, len(anomaly_indices), N, k,
        )
        return results

    # ------------------------------------------------------------------
    # Utilitaires internes
    # ------------------------------------------------------------------

    def _build_top_k_from_row(
        self,
        shap_row: np.ndarray,
        k: int,
    ) -> list[FeatureSHAP]:
        """
        Construit la liste FeatureSHAP depuis un vecteur de valeurs SHAP.
        Factorisé pour éviter la duplication entre les deux modes batch.
        """
        abs_values = np.abs(shap_row)
        top_indices = np.argsort(abs_values)[::-1][:k]

        features = []
        for rank, idx in enumerate(top_indices, start=1):
            val = float(shap_row[idx])
            name = (
                self.feature_names[idx]
                if idx < len(self.feature_names)
                else f"feature_{idx}"
            )
            features.append(
                FeatureSHAP(
                    name=name,
                    shap_value=val,
                    direction="positive" if val > 0 else "negative",
                    rank=rank,
                )
            )
        return features

    def _assert_initialized(self) -> None:
        if self._shap_explainer is None:
            raise ExplainerNotFittedError(
                "Explainer non initialisé. Appeler .initialize() après "
                "Detector.fit(). Pour DIF, fournir X_background."
            )