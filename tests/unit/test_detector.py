"""
Tests unitaires — core/detector.py

Couvre :
- Les trois stratégies (IF, LOF, OC-SVM) : fit, score, predict
- Le Context Detector : délégation, swap de stratégie, save/load
- La factory build_detector : config valide, config invalide
- Les erreurs : DetectorNotFittedError, DetectorConfigError

Convention [Sculley2015] : chaque test est indépendant, déterministe
(random_state=42), rapide (< 1s par test).
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from core.detector import (
    Detector,
    DetectorConfigError,
    DetectorNotFittedError,
    IsolationForestStrategy,
    LOFStrategy,
    OneClassSVMStrategy,
    SHAPNotSupportedError,
    build_detector,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def X_normal() -> np.ndarray:
    """1000 points normaux (distribution gaussienne)."""
    rng = np.random.default_rng(42)
    return rng.standard_normal((1000, 5))


@pytest.fixture
def X_with_anomalies(X_normal) -> tuple[np.ndarray, np.ndarray]:
    """Dataset mixte : 920 normaux + 80 anomalies évidentes (loin de la normale)."""
    rng = np.random.default_rng(42)
    anomalies = rng.standard_normal((80, 5)) * 0.1 + 10  # Très éloignés
    X = np.vstack([X_normal[:920], anomalies])
    labels = np.array([0] * 920 + [1] * 80)  # 1 = anomalie
    return X, labels


@pytest.fixture
def X_test() -> np.ndarray:
    """Petit batch de test : 10 normaux + 5 anomalies."""
    rng = np.random.default_rng(0)
    normals = rng.standard_normal((10, 5))
    anomalies = rng.standard_normal((5, 5)) * 0.1 + 10
    return np.vstack([normals, anomalies])


@pytest.fixture
def fitted_if_strategy(X_normal) -> IsolationForestStrategy:
    """IsolationForestStrategy entraîné."""
    s = IsolationForestStrategy(n_estimators=50, contamination=0.08, random_state=42)
    s.fit(X_normal)
    return s


@pytest.fixture
def if_config() -> dict:
    return {
        "algorithm": "isolation_forest",
        "contamination": 0.08,
        "n_estimators": 50,
        "threshold": 0.5,
        "random_state": 42,
    }


# ===========================================================================
# IsolationForestStrategy
# ===========================================================================

class TestIsolationForestStrategy:
    """[Liu2008] Tests de la stratégie principale."""

    def test_get_name(self):
        s = IsolationForestStrategy()
        assert s.get_name() == "isolation_forest"

    def test_supports_shap_true(self):
        """IF doit supporter SHAP — critère non-négociable [Lundberg2020]."""
        s = IsolationForestStrategy()
        assert s.supports_shap() is True

    def test_fit_returns_self(self, X_normal):
        s = IsolationForestStrategy(n_estimators=50, random_state=42)
        result = s.fit(X_normal)
        assert result is s

    def test_score_shape_matches_input(self, fitted_if_strategy, X_test):
        scores = fitted_if_strategy.score(X_test)
        assert scores.shape == (len(X_test),)

    def test_score_values_in_unit_interval(self, fitted_if_strategy, X_test):
        """Les scores normalisés doivent être dans [0, 1]."""
        scores = fitted_if_strategy.score(X_test)
        assert np.all(scores >= 0.0), "Score minimum doit être >= 0"
        assert np.all(scores <= 1.0), "Score maximum doit être <= 1"

    def test_anomalies_score_higher_than_normals(self, fitted_if_strategy):
        """
        Les anomalies évidentes (loin de la distribution d'entraînement)
        doivent avoir des scores plus élevés que les points normaux.
        [Liu2008] : les anomalies sont isolées en moins de coupes.
        """
        rng = np.random.default_rng(42)
        X_normal_test = rng.standard_normal((100, 5))
        X_anomaly_test = rng.standard_normal((100, 5)) * 0.1 + 10

        scores_normal = fitted_if_strategy.score(X_normal_test)
        scores_anomaly = fitted_if_strategy.score(X_anomaly_test)

        assert scores_anomaly.mean() > scores_normal.mean(), (
            "Le score moyen des anomalies doit dépasser celui des points normaux."
        )

    def test_predict_returns_bool_array(self, fitted_if_strategy, X_test):
        preds = fitted_if_strategy.predict(X_test, threshold=0.5)
        assert preds.dtype == bool

    def test_predict_threshold_effect(self, fitted_if_strategy, X_test):
        """Un seuil bas → plus de détections qu'un seuil élevé."""
        preds_low = fitted_if_strategy.predict(X_test, threshold=0.1)
        preds_high = fitted_if_strategy.predict(X_test, threshold=0.9)
        assert preds_low.sum() >= preds_high.sum()

    def test_not_fitted_raises_error(self, X_test):
        s = IsolationForestStrategy()
        with pytest.raises(DetectorNotFittedError):
            s.score(X_test)

    def test_get_underlying_model_returns_sklearn_model(self, fitted_if_strategy):
        """get_underlying_model() doit retourner le modèle sklearn pour SHAP."""
        from sklearn.ensemble import IsolationForest
        model = fitted_if_strategy.get_underlying_model()
        assert isinstance(model, IsolationForest)

    def test_get_underlying_model_not_fitted_raises(self):
        s = IsolationForestStrategy()
        with pytest.raises(DetectorNotFittedError):
            s.get_underlying_model()

    def test_save_and_load(self, fitted_if_strategy, X_test):
        """Round-trip save/load doit produire des scores identiques."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "if_strategy.joblib"
            fitted_if_strategy.save(path)

            loaded = IsolationForestStrategy.load(path)
            scores_original = fitted_if_strategy.score(X_test)
            scores_loaded = loaded.score(X_test)

            np.testing.assert_array_almost_equal(
                scores_original, scores_loaded, decimal=6
            )

    def test_contamination_not_hardcoded(self):
        """La contamination est configurable — ne jamais hardcoder [Sculley2015]."""
        s1 = IsolationForestStrategy(contamination=0.03)
        s2 = IsolationForestStrategy(contamination=0.15)
        assert s1.contamination == 0.03
        assert s2.contamination == 0.15


# ===========================================================================
# LOFStrategy
# ===========================================================================

class TestLOFStrategy:
    """[Breunig2000] Tests de la stratégie de comparaison LOF."""

    def test_get_name(self):
        assert LOFStrategy().get_name() == "lof"

    def test_supports_shap_false(self):
        """LOF ne supporte pas SHAP — critère éliminatoire pour la production."""
        assert LOFStrategy().supports_shap() is False

    def test_get_underlying_model_raises(self):
        s = LOFStrategy()
        rng = np.random.default_rng(42)
        s.fit(rng.standard_normal((200, 5)))
        with pytest.raises(SHAPNotSupportedError):
            s.get_underlying_model()

    def test_fit_and_score(self):
        rng = np.random.default_rng(42)
        X = rng.standard_normal((300, 5))
        s = LOFStrategy(n_neighbors=10, contamination=0.08)
        s.fit(X)
        scores = s.score(X[:20])
        assert scores.shape == (20,)
        assert np.all(scores >= 0) and np.all(scores <= 1)

    def test_not_fitted_raises(self):
        rng = np.random.default_rng(42)
        with pytest.raises(DetectorNotFittedError):
            LOFStrategy().score(rng.standard_normal((10, 5)))


# ===========================================================================
# OneClassSVMStrategy
# ===========================================================================

class TestOneClassSVMStrategy:
    """[Schölkopf2001] Tests de la stratégie de comparaison OC-SVM."""

    def test_get_name(self):
        assert OneClassSVMStrategy().get_name() == "one_class_svm"

    def test_supports_shap_false(self):
        assert OneClassSVMStrategy().supports_shap() is False

    def test_fit_scales_data(self):
        """OC-SVM doit initialiser un StandardScaler pendant fit."""
        rng = np.random.default_rng(42)
        X = rng.standard_normal((200, 5))
        s = OneClassSVMStrategy(nu=0.08)
        s.fit(X)
        assert s._scaler is not None

    def test_fit_and_score(self):
        rng = np.random.default_rng(42)
        X = rng.standard_normal((300, 5))
        s = OneClassSVMStrategy(nu=0.08)
        s.fit(X)
        scores = s.score(X[:20])
        assert scores.shape == (20,)
        assert np.all(scores >= 0) and np.all(scores <= 1)

    def test_not_fitted_raises(self):
        rng = np.random.default_rng(42)
        with pytest.raises(DetectorNotFittedError):
            OneClassSVMStrategy().score(rng.standard_normal((10, 5)))


# ===========================================================================
# Detector (Context)
# ===========================================================================

class TestDetector:
    """Tests du Context Pattern [GoF1994]."""

    def test_repr_contains_strategy_name(self, if_config):
        detector = build_detector(if_config)
        repr_str = repr(detector)
        assert "isolation_forest" in repr_str
        assert "shap_compatible=True" in repr_str

    def test_delegates_fit_to_strategy(self, X_normal, if_config):
        detector = build_detector(if_config)
        detector.fit(X_normal)
        # Vérifier que la stratégie est bien entraînée
        assert detector.strategy._model is not None

    def test_get_name_delegates_to_strategy(self, if_config):
        detector = build_detector(if_config)
        assert detector.get_name() == "isolation_forest"

    def test_supports_shap_delegates_to_strategy(self, if_config):
        detector = build_detector(if_config)
        assert detector.supports_shap() is True

    def test_threshold_used_in_predict(self, X_normal, X_test):
        """Le seuil du Detector doit être respecté dans predict()."""
        s = IsolationForestStrategy(n_estimators=50, random_state=42)
        s.fit(X_normal)

        detector_low = Detector(strategy=s, threshold=0.1)
        detector_high = Detector(strategy=s, threshold=0.9)

        # Plus de détections avec un seuil bas
        preds_low = detector_low.predict(X_test)
        preds_high = detector_high.predict(X_test)
        assert preds_low.sum() >= preds_high.sum()

    def test_strategy_swap(self, X_normal, X_test):
        """Swap de stratégie sans modifier le Pipeline."""
        if_strat = IsolationForestStrategy(n_estimators=50, random_state=42)
        lof_strat = LOFStrategy(n_neighbors=10, contamination=0.08)
        if_strat.fit(X_normal)
        lof_strat.fit(X_normal)

        detector = Detector(strategy=if_strat)
        assert detector.get_name() == "isolation_forest"

        detector.strategy = lof_strat
        assert detector.get_name() == "lof"

    def test_save_load_roundtrip(self, X_normal, X_test, if_config):
        detector = build_detector(if_config)
        detector.fit(X_normal)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "detector.joblib"
            detector.save(path)
            loaded = Detector.load(path, threshold=0.5)

            scores_orig = detector.score(X_test)
            scores_load = loaded.score(X_test)
            np.testing.assert_array_almost_equal(scores_orig, scores_load, decimal=6)


# ===========================================================================
# build_detector factory
# ===========================================================================

class TestBuildDetector:
    """Tests de la factory — config YAML → Detector."""

    def test_build_isolation_forest(self, if_config):
        d = build_detector(if_config)
        assert d.get_name() == "isolation_forest"
        assert d.threshold == 0.5

    def test_build_lof(self):
        config = {
            "algorithm": "lof",
            "contamination": 0.05,
            "n_neighbors": 15,
            "threshold": 0.6,
        }
        d = build_detector(config)
        assert d.get_name() == "lof"
        assert d.threshold == 0.6

    def test_build_one_class_svm(self):
        config = {
            "algorithm": "one_class_svm",
            "contamination": 0.10,
            "threshold": 0.5,
        }
        d = build_detector(config)
        assert d.get_name() == "one_class_svm"

    def test_unknown_algorithm_raises(self):
        with pytest.raises(DetectorConfigError, match="Algorithme inconnu"):
            build_detector({"algorithm": "autoencoder"})

    def test_default_algorithm_is_isolation_forest(self):
        """Sans 'algorithm', IF doit être utilisé par défaut."""
        d = build_detector({})
        assert d.get_name() == "isolation_forest"

    def test_contamination_from_config(self):
        """La contamination du YAML est bien transmise à la stratégie."""
        config = {
            "algorithm": "isolation_forest",
            "contamination": 0.03,
            "n_estimators": 50,
        }
        d = build_detector(config)
        assert d.strategy.contamination == pytest.approx(0.03)

    def test_config_params_not_hardcoded(self):
        """
        Vérification [Sculley2015] : les paramètres doivent être externalisés.
        Deux configs différentes doivent produire deux détecteurs différents.
        """
        d1 = build_detector({"algorithm": "isolation_forest", "contamination": 0.03})
        d2 = build_detector({"algorithm": "isolation_forest", "contamination": 0.15})
        assert d1.strategy.contamination != d2.strategy.contamination


# ===========================================================================
# Sigmoid normalization (propriété mathématique)
# ===========================================================================

class TestSigmoidNormalization:
    """Vérification mathématique de la normalisation."""

    def test_negative_raw_gives_high_score(self):
        """Score négatif (anomalie IF) → score normalisé élevé."""
        raw = np.array([-0.5, -0.3, -0.1])
        result = IsolationForestStrategy._sigmoid_normalize(raw)
        assert np.all(result > 0.5), "Scores négatifs doivent donner > 0.5"

    def test_positive_raw_gives_low_score(self):
        """Score positif (normal IF) → score normalisé faible."""
        raw = np.array([0.1, 0.3, 0.5])
        result = IsolationForestStrategy._sigmoid_normalize(raw)
        assert np.all(result < 0.5), "Scores positifs doivent donner < 0.5"

    def test_zero_gives_half(self):
        """Score = 0 → score normalisé = 0.5."""
        raw = np.array([0.0])
        result = IsolationForestStrategy._sigmoid_normalize(raw)
        assert result[0] == pytest.approx(0.5, abs=1e-6)

    def test_output_in_unit_interval(self):
        """Invariant global : sortie toujours dans [0, 1]."""
        rng = np.random.default_rng(0)
        raw = rng.uniform(-1.0, 1.0, 1000)
        result = IsolationForestStrategy._sigmoid_normalize(raw)
        assert np.all(result >= 0) and np.all(result <= 1)