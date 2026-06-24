"""
Tests unitaires — core/explainer.py

Couvre :
- Explainer : construction, initialize, compute_top_k, compute_batch_top_k
- Validation SHAP avec IsolationForestStrategy
- Rejet des stratégies sans SHAP (LOF, OC-SVM)
- Propriétés SHAP attendues : ranking, directions, top-k cohérence

Note sur les imports SHAP :
    Les tests SHAP nécessitent le package `shap`.
    Les tests sont marqués @pytest.mark.requires_shap et skippés si absent.
    Cela permet d'exécuter la suite sans shap en CI allégée.

[Lundberg2017] Lundberg & Lee (2017). NeurIPS.
[Lundberg2020] Lundberg et al. (2020). Nature MI.
"""

import numpy as np
import pytest

from core.data_models import FeatureSHAP
from core.detector import (
    IsolationForestStrategy,
    LOFStrategy,
    OneClassSVMStrategy,
    SHAPNotSupportedError,
)
from core.explainer import Explainer, ExplainerNotFittedError


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def shap_available() -> bool:
    try:
        import shap  # noqa: F401
        return True
    except ImportError:
        return False


requires_shap = pytest.mark.skipif(
    not shap_available(),
    reason="Package 'shap' non installé — tests SHAP ignorés.",
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FEATURE_NAMES = [
    "ratio_prix_mercuriale",
    "incoherence_sexe_acte",
    "historique_ratio_praticien",
    "nb_sinistres_30j",
    "is_weekend_care",
]
N_FEATURES = len(FEATURE_NAMES)


@pytest.fixture
def X_train() -> np.ndarray:
    rng = np.random.default_rng(42)
    return rng.standard_normal((500, N_FEATURES))


@pytest.fixture
def X_anomaly() -> np.ndarray:
    """Points clairement anormaux (loin de la distribution d'entraînement)."""
    rng = np.random.default_rng(0)
    return rng.standard_normal((5, N_FEATURES)) * 0.1 + 10


@pytest.fixture
def fitted_if_strategy(X_train) -> IsolationForestStrategy:
    s = IsolationForestStrategy(n_estimators=50, contamination=0.08, random_state=42)
    s.fit(X_train)
    return s


@pytest.fixture
def initialized_explainer(fitted_if_strategy) -> Explainer:
    """Explainer initialisé et prêt à l'emploi."""
    exp = Explainer(strategy=fitted_if_strategy, feature_names=FEATURE_NAMES)
    if shap_available():
        exp.initialize()
    return exp


# ===========================================================================
# Construction et validation de l'interface
# ===========================================================================

class TestExplainerConstruction:

    def test_construction_with_if_strategy(self, fitted_if_strategy):
        """Doit construire sans erreur avec une stratégie SHAP-compatible."""
        exp = Explainer(strategy=fitted_if_strategy, feature_names=FEATURE_NAMES)
        assert exp.feature_names == FEATURE_NAMES

    @requires_shap
    def test_lof_initialize_without_background_raises(self):
        """LOF → KernelSHAP requis. initialize() sans background lève ValueError."""
        rng = np.random.default_rng(42)
        lof = LOFStrategy(n_neighbors=10, contamination=0.08)
        lof.fit(rng.standard_normal((200, N_FEATURES)))

        exp = Explainer(strategy=lof, feature_names=FEATURE_NAMES)
        with pytest.raises(ValueError, match="X_background"):
            exp.initialize()
            
    # APRÈS
    @requires_shap
    def test_ocsvm_initialize_without_background_raises(self):
        """OC-SVM → KernelSHAP requis. initialize() sans background lève ValueError."""
        rng = np.random.default_rng(42)
        svm = OneClassSVMStrategy(nu=0.08)
        svm.fit(rng.standard_normal((200, N_FEATURES)))

        exp = Explainer(strategy=svm, feature_names=FEATURE_NAMES)
        with pytest.raises(ValueError, match="X_background"):
            exp.initialize()

    def test_compute_top_k_before_initialize_raises(self, fitted_if_strategy):
        """compute_top_k avant initialize → ExplainerNotFittedError."""
        exp = Explainer(strategy=fitted_if_strategy, feature_names=FEATURE_NAMES)
        rng = np.random.default_rng(0)
        X_row = rng.standard_normal(N_FEATURES)
        with pytest.raises(ExplainerNotFittedError):
            exp.compute_top_k(X_row)


# ===========================================================================
# compute_top_k — propriétés SHAP
# ===========================================================================

@requires_shap
class TestComputeTopK:

    def test_returns_list_of_feature_shap(self, initialized_explainer, X_anomaly):
        result = initialized_explainer.compute_top_k(X_anomaly[0], k=3)
        assert isinstance(result, list)
        assert all(isinstance(f, FeatureSHAP) for f in result)

    def test_returns_k_features(self, initialized_explainer, X_anomaly):
        for k in [1, 2, 3]:
            result = initialized_explainer.compute_top_k(X_anomaly[0], k=k)
            assert len(result) == k, f"Attendu {k} features, obtenu {len(result)}"

    def test_rank_is_sequential(self, initialized_explainer, X_anomaly):
        """Les rangs doivent être 1, 2, 3, ... [Lundberg2017]."""
        result = initialized_explainer.compute_top_k(X_anomaly[0], k=3)
        ranks = [f.rank for f in result]
        assert ranks == list(range(1, len(result) + 1))

    def test_sorted_by_abs_shap_desc(self, initialized_explainer, X_anomaly):
        """
        Le top-1 doit avoir la plus grande valeur |SHAP|.
        [Lundberg2017] : importance = valeur absolue de la contribution.
        """
        result = initialized_explainer.compute_top_k(X_anomaly[0], k=3)
        abs_values = [abs(f.shap_value) for f in result]
        assert abs_values == sorted(abs_values, reverse=True), (
            "Les features doivent être triées par |SHAP| décroissant."
        )

    def test_direction_matches_sign(self, initialized_explainer, X_anomaly):
        """direction='positive' ↔ shap_value > 0 [Lundberg2017]."""
        result = initialized_explainer.compute_top_k(X_anomaly[0], k=3)
        for f in result:
            if f.shap_value > 0:
                assert f.direction == "positive"
            else:
                assert f.direction == "negative"

    def test_feature_names_in_result(self, initialized_explainer, X_anomaly):
        """Les noms de features retournés doivent être dans la liste initiale."""
        result = initialized_explainer.compute_top_k(X_anomaly[0], k=3)
        for f in result:
            assert f.name in FEATURE_NAMES, (
                f"Feature '{f.name}' inconnue. "
                f"Attendu l'un de : {FEATURE_NAMES}"
            )

    def test_input_1d_or_2d_both_accepted(self, initialized_explainer, X_anomaly):
        """Doit accepter un vecteur 1D et une matrice (1, n_features)."""
        result_1d = initialized_explainer.compute_top_k(X_anomaly[0], k=2)
        result_2d = initialized_explainer.compute_top_k(X_anomaly[0:1], k=2)
        # Les deux doivent retourner le même nombre de features
        assert len(result_1d) == len(result_2d) == 2

    def test_shap_values_are_floats(self, initialized_explainer, X_anomaly):
        result = initialized_explainer.compute_top_k(X_anomaly[0], k=3)
        for f in result:
            assert isinstance(f.shap_value, float)

    def test_to_dict_serializable(self, initialized_explainer, X_anomaly):
        """FeatureSHAP.to_dict() doit être JSON-sérialisable."""
        import json
        result = initialized_explainer.compute_top_k(X_anomaly[0], k=3)
        for f in result:
            d = f.to_dict()
            # Ne doit pas lever d'exception
            json.dumps(d)
            assert "name" in d
            assert "shap_value" in d
            assert "direction" in d
            assert "rank" in d


# ===========================================================================
# compute_batch_top_k
# ===========================================================================

@requires_shap
class TestComputeBatchTopK:

    def test_returns_list_of_length_n(self, initialized_explainer, X_train):
        """La liste retournée doit avoir la même longueur que X."""
        N = 20
        X = X_train[:N]
        mask = np.zeros(N, dtype=bool)
        mask[0] = True
        mask[5] = True

        results = initialized_explainer.compute_batch_top_k(X, mask, k=3)
        assert len(results) == N

    def test_none_for_non_anomalies(self, initialized_explainer, X_train):
        """Les dossiers non-anomalies doivent avoir None."""
        N = 10
        X = X_train[:N]
        mask = np.zeros(N, dtype=bool)
        mask[2] = True  # Seul index 2 est anomalie

        results = initialized_explainer.compute_batch_top_k(X, mask, k=3)

        for i, r in enumerate(results):
            if i == 2:
                assert r is not None, "Index 2 (anomalie) doit avoir des SHAP."
            else:
                assert r is None, f"Index {i} (non-anomalie) doit être None."

    def test_anomalies_get_top_k_features(self, initialized_explainer, X_train):
        """Les dossiers anomalies doivent avoir k features SHAP."""
        N = 15
        rng = np.random.default_rng(42)
        X = rng.standard_normal((N, N_FEATURES)) * 0.1 + 10  # Anomalies
        mask = np.ones(N, dtype=bool)

        results = initialized_explainer.compute_batch_top_k(X, mask, k=3)
        for r in results:
            assert r is not None
            assert len(r) == 3

    def test_empty_anomaly_mask(self, initialized_explainer, X_train):
        """Aucune anomalie → toutes les sorties sont None."""
        N = 10
        X = X_train[:N]
        mask = np.zeros(N, dtype=bool)

        results = initialized_explainer.compute_batch_top_k(X, mask, k=3)
        assert all(r is None for r in results)

    def test_consistent_with_single_compute(self, initialized_explainer, X_train):
        """
        compute_batch_top_k et compute_top_k doivent donner le même top-1
        pour le même point.
        Vérifie la cohérence interne [Lundberg2017].
        """
        X = X_train[:5]
        mask = np.array([True, False, False, False, False])

        batch_results = initialized_explainer.compute_batch_top_k(X, mask, k=1)
        single_result = initialized_explainer.compute_top_k(X[0], k=1)

        assert batch_results[0] is not None
        assert batch_results[0][0].name == single_result[0].name


# ===========================================================================
# Performance indicative (non-bloquante)
# ===========================================================================

@requires_shap
class TestExplainerPerformance:

    def test_single_compute_under_500ms(self, initialized_explainer, X_anomaly):
        """
        Indicatif — cible BNF-06 : SHAP top-3 < 200ms p50.
        Ce test ne fail pas en CI mais log un warning si dépassé.
        """
        import time
        start = time.perf_counter()
        initialized_explainer.compute_top_k(X_anomaly[0], k=3)
        elapsed_ms = (time.perf_counter() - start) * 1000

        if elapsed_ms > 500:
            pytest.xfail(
                f"SHAP trop lent : {elapsed_ms:.0f}ms > 500ms. "
                f"Cible BNF-06 : < 200ms p50."
            )