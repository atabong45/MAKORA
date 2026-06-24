"""
Tests unitaires — Explainer en mode KernelSHAP (core/explainer.py)

Couvre :
- Sélection automatique du mode : tree (IF) vs kernel (DIF)
- initialize() sans X_background lève ValueError pour les stratégies kernel
- compute_top_k via KernelExplainer : top-k, ranking, directions
- compute_batch_top_k en mode kernel
- Erreur avant initialize()

Dépendances :
    - shap requis pour tout test appelant initialize() → @requires_shap
    - pyod requis pour entraîner DIF (fit) → @requires_pyod
    Les tests de contrat (mode None, erreur avant initialize) n'en ont besoin
    d'aucun.

[Lundberg2017] Lundberg & Lee (2017). NeurIPS. — KernelSHAP générique.
[Lundberg2020] Lundberg et al. (2020). Nature MI. — TreeExplainer.
[Xu2023] Xu et al. (2023). Deep Isolation Forest. IEEE TKDE.
"""

import numpy as np
import pytest

from core.data_models import FeatureSHAP
from core.detector import DIFStrategy, IsolationForestStrategy
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


def pyod_available() -> bool:
    try:
        import pyod  # noqa: F401
        return True
    except ImportError:
        return False


requires_shap = pytest.mark.skipif(
    not shap_available(), reason="Package 'shap' non installé."
)
requires_pyod = pytest.mark.skipif(
    not pyod_available(), reason="Package 'pyod' non installé."
)

N_FEATURES = 10
FEATS = [f"feat_{i}" for i in range(N_FEATURES)]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def X_background() -> np.ndarray:
    """Background set réduit pour la vitesse des tests KernelSHAP."""
    rng = np.random.default_rng(42)
    return rng.standard_normal((40, N_FEATURES))


@pytest.fixture
def X_train() -> np.ndarray:
    rng = np.random.default_rng(0)
    return rng.standard_normal((300, N_FEATURES))


@pytest.fixture
def X_row() -> np.ndarray:
    rng = np.random.default_rng(7)
    return rng.standard_normal(N_FEATURES)


@pytest.fixture
def dif_strategy(X_train) -> DIFStrategy:
    """DIF entraînée — nécessite pyod."""
    s = DIFStrategy(hidden_neurons=[64, 32], contamination=0.08, threshold=0.35)
    s.fit(X_train)
    return s


@pytest.fixture
def initialized_kernel_explainer(dif_strategy, X_background) -> Explainer:
    exp = Explainer(strategy=dif_strategy, feature_names=FEATS)
    exp.initialize(X_background=X_background)
    return exp


# ===========================================================================
# Sélection du mode et contrat — peu ou pas de dépendances
# ===========================================================================

class TestModeSelection:

    def test_mode_none_before_initialize(self):
        """_mode reste None tant que initialize() n'est pas appelé."""
        exp = Explainer(strategy=DIFStrategy(), feature_names=FEATS)
        assert exp._mode is None

    def test_compute_before_initialize_raises(self, X_row):
        """compute_top_k avant initialize → ExplainerNotFittedError."""
        exp = Explainer(strategy=DIFStrategy(), feature_names=FEATS)
        with pytest.raises(ExplainerNotFittedError):
            exp.compute_top_k(X_row, k=3)

    def test_construction_with_dif_succeeds(self):
        """Construction acceptée pour DIF (validation déplacée vers initialize)."""
        exp = Explainer(strategy=DIFStrategy(), feature_names=FEATS)
        assert exp.feature_names == FEATS

    @requires_shap
    def test_raises_without_background(self):
        """DIF (supports_shap=False) sans X_background → ValueError [Lundberg2017]."""
        exp = Explainer(strategy=DIFStrategy(), feature_names=FEATS)
        with pytest.raises(ValueError, match="X_background"):
            exp.initialize()

    @requires_shap
    def test_if_uses_tree_mode(self, X_train):
        """IF → mode tree, aucun background requis."""
        s = IsolationForestStrategy(n_estimators=50, random_state=42)
        s.fit(X_train)
        exp = Explainer(strategy=s, feature_names=FEATS)
        exp.initialize()
        assert exp._mode == "tree"


# ===========================================================================
# Mode kernel — initialize et compute (nécessite shap + pyod)
# ===========================================================================

@requires_shap
@requires_pyod
class TestKernelSHAP:

    def test_initialize_sets_kernel_mode(self, dif_strategy, X_background):
        exp = Explainer(strategy=dif_strategy, feature_names=FEATS)
        exp.initialize(X_background=X_background)
        assert exp._mode == "kernel"

    def test_compute_top3_returns_3_features(self, initialized_kernel_explainer, X_row):
        result = initialized_kernel_explainer.compute_top_k(X_row, k=3)
        assert len(result) == 3
        assert all(isinstance(f, FeatureSHAP) for f in result)

    def test_top_k_sorted_by_abs_desc(self, initialized_kernel_explainer, X_row):
        """[Lundberg2017] : importance = |φᵢ| décroissant."""
        result = initialized_kernel_explainer.compute_top_k(X_row, k=3)
        abs_vals = [abs(f.shap_value) for f in result]
        assert abs_vals == sorted(abs_vals, reverse=True)

    def test_ranks_sequential(self, initialized_kernel_explainer, X_row):
        result = initialized_kernel_explainer.compute_top_k(X_row, k=3)
        assert [f.rank for f in result] == [1, 2, 3]

    def test_feature_names_valid(self, initialized_kernel_explainer, X_row):
        result = initialized_kernel_explainer.compute_top_k(X_row, k=3)
        for f in result:
            assert f.name in FEATS

    def test_direction_matches_sign(self, initialized_kernel_explainer, X_row):
        result = initialized_kernel_explainer.compute_top_k(X_row, k=3)
        for f in result:
            expected = "positive" if f.shap_value > 0 else "negative"
            assert f.direction == expected

    def test_accepts_1d_and_2d(self, initialized_kernel_explainer, X_row):
        r1 = initialized_kernel_explainer.compute_top_k(X_row, k=2)
        r2 = initialized_kernel_explainer.compute_top_k(X_row.reshape(1, -1), k=2)
        assert len(r1) == len(r2) == 2

    def test_batch_kernel_mode(self, initialized_kernel_explainer, X_train):
        """Batch en mode kernel : None pour les non-anomalies, top-k sinon."""
        N = 6
        X = X_train[:N]
        mask = np.zeros(N, dtype=bool)
        mask[1] = True
        mask[4] = True

        results = initialized_kernel_explainer.compute_batch_top_k(X, mask, k=3)
        assert len(results) == N
        assert results[1] is not None and len(results[1]) == 3
        assert results[4] is not None
        assert results[0] is None
        assert results[2] is None

    def test_batch_empty_mask_all_none(self, initialized_kernel_explainer, X_train):
        N = 5
        results = initialized_kernel_explainer.compute_batch_top_k(
            X_train[:N], np.zeros(N, dtype=bool), k=3
        )
        assert all(r is None for r in results)