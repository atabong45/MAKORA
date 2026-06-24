"""
Tests unitaires — DIFStrategy (core/detector.py)

Couvre :
- Construction et paramètres externalisés [Sculley2015]
- Convention de score PyOD : anomalie = valeur ÉLEVÉE [Xu2023]
- Seuil calibré et predict() booléen
- supports_shap() == False (KernelSHAP requis)
- Erreurs avant fit()
- Factory build_detector pour 'dif'
- load_strategy_from_joblib : détection automatique du type

Note sur pyod :
    DIFStrategy.fit() importe pyod localement. Les tests nécessitant fit()
    sont marqués @requires_pyod et skippés si pyod absent (cohérent avec
    l'exclusion de test_experiment_h0.py dans l'image Docker de tests).
    Les tests de construction/contrat ne nécessitent pas pyod.

[Xu2023] Xu et al. (2023). Deep Isolation Forest. IEEE TKDE.
[Davis2006] Davis & Goadrich (2006). PR vs ROC curves. ICML.
[Sculley2015] Sculley et al. (2015). Hidden technical debt in ML. NeurIPS.
"""

import numpy as np
import pytest

from core import detector as det
from core.detector import (
    DIFStrategy,
    DetectorConfigError,
    DetectorNotFittedError,
    SHAPNotSupportedError,
    build_detector,
    load_strategy_from_joblib,
)


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def pyod_available() -> bool:
    try:
        import pyod  # noqa: F401
        return True
    except ImportError:
        return False


requires_pyod = pytest.mark.skipif(
    not pyod_available(),
    reason="Package 'pyod' non installé — tests DIF nécessitant fit() ignorés.",
)

N_FEATURES = 10


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def X_train() -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.standard_normal((400, N_FEATURES))


@pytest.fixture
def X_normal() -> np.ndarray:
    """Points normaux issus de la même distribution que l'entraînement."""
    rng = np.random.default_rng(11)
    return rng.standard_normal((50, N_FEATURES))


@pytest.fixture
def X_fraud() -> np.ndarray:
    """Anomalies évidentes — fortement décalées de la distribution normale."""
    rng = np.random.default_rng(99)
    return rng.standard_normal((20, N_FEATURES)) * 0.1 + 8.0


@pytest.fixture
def X_test() -> np.ndarray:
    """Batch mixte : 10 normaux + 5 anomalies."""
    rng = np.random.default_rng(7)
    normals = rng.standard_normal((10, N_FEATURES))
    anomalies = rng.standard_normal((5, N_FEATURES)) * 0.1 + 8.0
    return np.vstack([normals, anomalies])


@pytest.fixture
def fitted_strategy(X_train) -> DIFStrategy:
    """DIFStrategy entraînée — nécessite pyod."""
    s = DIFStrategy(hidden_neurons=[64, 32], contamination=0.08, threshold=0.35)
    s.fit(X_train)
    return s


# ===========================================================================
# Construction et contrat — sans pyod
# ===========================================================================

class TestDIFStrategyContract:
    """Tests ne nécessitant pas fit() — exécutables sans pyod."""

    def test_get_name_is_dif(self):
        """get_name() retourne le nom de l'algorithme, pas l'architecture."""
        assert DIFStrategy().get_name() == "dif"

    def test_default_hidden_neurons(self):
        """Architecture par défaut [64, 32] — config phi_optimal."""
        assert DIFStrategy()._hidden_neurons == [64, 32]

    def test_hidden_neurons_configurable(self):
        """[Sculley2015] : architecture externalisée, jamais hardcodée."""
        s = DIFStrategy(hidden_neurons=[128, 64, 32])
        assert s._hidden_neurons == [128, 64, 32]

    def test_contamination_configurable(self):
        """[Sculley2015] : contamination externalisée."""
        assert DIFStrategy(contamination=0.068)._contamination == 0.068
        assert DIFStrategy(contamination=0.100)._contamination == 0.100

    def test_supports_shap_is_false(self):
        """DIF est un réseau de neurones — TreeExplainer inapplicable [Xu2023]."""
        assert DIFStrategy().supports_shap() is False

    def test_threshold_calibrated_range(self):
        """Seuil dans la plage raisonnable DIF [Davis2006]."""
        s = DIFStrategy(threshold=0.35)
        assert 0.2 < s._threshold < 0.6

    def test_get_underlying_model_raises(self):
        """DIF n'expose pas de modèle pour TreeExplainer [Lundberg2020]."""
        with pytest.raises(SHAPNotSupportedError):
            DIFStrategy().get_underlying_model()

    def test_score_before_fit_raises(self):
        with pytest.raises(DetectorNotFittedError):
            DIFStrategy().score(np.zeros((5, N_FEATURES)))

    def test_predict_before_fit_raises(self):
        with pytest.raises(DetectorNotFittedError):
            DIFStrategy().predict(np.zeros((5, N_FEATURES)))


# ===========================================================================
# Comportement après fit — nécessite pyod
# ===========================================================================

@requires_pyod
class TestDIFStrategyFitted:
    """Tests nécessitant un modèle DIF entraîné."""

    def test_fit_sets_model(self, X_train):
        s = DIFStrategy(contamination=0.08)
        s.fit(X_train)
        assert s._model is not None

    def test_fit_returns_self(self, X_train):
        s = DIFStrategy()
        assert s.fit(X_train) is s

    def test_score_returns_1d_array(self, fitted_strategy, X_test):
        scores = fitted_strategy.score(X_test)
        assert scores.shape == (len(X_test),)

    def test_predict_returns_bool_array(self, fitted_strategy, X_test):
        preds = fitted_strategy.predict(X_test)
        assert preds.dtype == bool
        assert preds.shape == (len(X_test),)

    def test_score_anomalie_higher_than_normal(self, fitted_strategy, X_normal, X_fraud):
        """[Xu2023] : anomalie = score ÉLEVÉ (convention opposée à sklearn IF)."""
        score_normal = fitted_strategy.score(X_normal).mean()
        score_fraud = fitted_strategy.score(X_fraud).mean()
        assert score_fraud > score_normal

    def test_predict_uses_calibrated_threshold(self, fitted_strategy, X_test):
        """predict() sans threshold utilise self._threshold."""
        preds_default = fitted_strategy.predict(X_test)
        preds_explicit = fitted_strategy.predict(X_test, threshold=fitted_strategy._threshold)
        np.testing.assert_array_equal(preds_default, preds_explicit)

    def test_higher_threshold_detects_fewer(self, fitted_strategy, X_test):
        """Seuil plus élevé → moins d'anomalies détectées (scores bruts)."""
        few = fitted_strategy.predict(X_test, threshold=10.0).sum()
        many = fitted_strategy.predict(X_test, threshold=-10.0).sum()
        assert many >= few

    def test_save_load_roundtrip(self, fitted_strategy, X_test, tmp_path):
        """Round-trip save/load produit des scores identiques."""
        path = tmp_path / "dif_strategy.joblib"
        fitted_strategy.save(path)
        loaded = DIFStrategy.load(path)
        np.testing.assert_array_almost_equal(
            fitted_strategy.score(X_test), loaded.score(X_test), decimal=6
        )


# ===========================================================================
# Factory build_detector — sans pyod (pas de fit)
# ===========================================================================

class TestBuildDetectorDIF:
    """La factory construit la stratégie sans l'entraîner — pas de pyod requis."""

    def test_build_dif(self):
        config = {
            "algorithm": "dif",
            "hidden_neurons": [64, 32],
            "contamination": 0.068,
            "threshold": 0.349775,
            "random_state": 42,
            "device": "cpu",
        }
        d = build_detector(config)
        assert d.get_name() == "dif"
        assert d.threshold == 0.349775
        assert d.supports_shap() is False

    def test_build_dif_passes_threshold_to_strategy(self):
        """Le seuil calibré doit être propagé à la stratégie elle-même."""
        d = build_detector({"algorithm": "dif", "threshold": 0.341498})
        assert d.strategy._threshold == 0.341498

    def test_build_dif_default_architecture(self):
        d = build_detector({"algorithm": "dif"})
        assert d.strategy._hidden_neurons == [64, 32]

    def test_build_dif_passes_hidden_neurons(self):
        d = build_detector({"algorithm": "dif", "hidden_neurons": [128, 64]})
        assert d.strategy._hidden_neurons == [128, 64]


# ===========================================================================
# load_strategy_from_joblib — détection automatique du type
# ===========================================================================

class TestLoadStrategyFromJoblib:
    """
    Détection DIF vs IF. On monkeypatch joblib.load pour fournir des bundles
    factices, ce qui évite le besoin d'un vrai modèle pyod et de pickling.
    """

    def test_detects_dif_sante_threshold(self, monkeypatch):
        class DIF:  # type(instance).__name__ == "DIF"
            pass
        monkeypatch.setattr(det.joblib, "load", lambda p: {"model": DIF()})
        strategy = load_strategy_from_joblib("dummy", branch="sante")
        assert strategy.get_name() == "dif"
        assert strategy._threshold == 0.349775

    def test_detects_dif_auto_threshold(self, monkeypatch):
        class DIF:
            pass
        monkeypatch.setattr(det.joblib, "load", lambda p: {"model": DIF()})
        strategy = load_strategy_from_joblib("dummy", branch="auto")
        assert strategy._threshold == 0.341498

    def test_dif_unknown_branch_fallback(self, monkeypatch):
        class DIF:
            pass
        monkeypatch.setattr(det.joblib, "load", lambda p: {"model": DIF()})
        strategy = load_strategy_from_joblib("dummy", branch="vie")
        assert strategy._threshold == 0.35

    def test_detects_isolation_forest(self, monkeypatch):
        class IsolationForest:
            pass
        monkeypatch.setattr(det.joblib, "load", lambda p: {"model": IsolationForest()})
        strategy = load_strategy_from_joblib("dummy", branch="sante")
        assert strategy.get_name() == "isolation_forest"

    def test_detector_strategy_passthrough(self, monkeypatch):
        """Un bundle qui EST déjà une DetectorStrategy est retourné tel quel."""
        original = det.IsolationForestStrategy()
        monkeypatch.setattr(det.joblib, "load", lambda p: original)
        strategy = load_strategy_from_joblib("dummy", branch="sante")
        assert strategy is original

    def test_unknown_type_raises(self, monkeypatch):
        monkeypatch.setattr(det.joblib, "load", lambda p: {"model": "not_a_model"})
        with pytest.raises(DetectorConfigError, match="non supporté"):
            load_strategy_from_joblib("dummy", branch="sante")