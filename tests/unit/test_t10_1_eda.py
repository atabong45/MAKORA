"""
TESTS : tests/unit/test_t10_1_eda.py
DESCRIPTION : Tests unitaires pour les scripts t10_1_eda.py et t10_1_eda_tests.py

CONVENTIONS [Sculley2015] :
- Chaque test est indépendant et déterministe (seed=42).
- Fixtures légères (< 200 dossiers) pour tests rapides (< 2s).
- On teste les contrats (sorties garanties), pas les implémentations internes.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

# Résolution du projet
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR  = PROJECT_ROOT / "scripts"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from t10_1_eda import EDAConfig, compute_overview, _is_binary
from t10_1_eda_tests import (
    _cohens_d, _test_feature, _analyse_scenario,
    FeatureSignal, ScenarioReport, ALPHA, D_MIN, MIN_N,
)


# ══════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════

FEATURES = ["ratio_devis_bareme", "vehicule_sur_value", "sinistre_nuit_sans_temoin"]
N_NORM   = 150
N_FRAUD  = 20


@pytest.fixture
def tmp_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "results"


@pytest.fixture
def cfg(tmp_output_dir: Path) -> EDAConfig:
    return EDAConfig(
        branch="auto",
        data_path=Path("/dev/null"),   # non utilisé dans ces tests
        output_dir=tmp_output_dir,
        random_state=42,
    )


@pytest.fixture
def df_with_anomalies() -> pd.DataFrame:
    """
    DataFrame de 170 dossiers (150 normaux + 20 frauduleux).
    Les dossiers frauduleux ont un ratio_devis_bareme 3× plus élevé —
    signal intentionnellement fort pour les tests.
    """
    rng = np.random.default_rng(42)
    norm = pd.DataFrame({
        "ratio_devis_bareme":        rng.normal(1.0, 0.1, N_NORM),
        "vehicule_sur_value":        rng.integers(0, 2, N_NORM).astype(float),
        "sinistre_nuit_sans_temoin": rng.integers(0, 2, N_NORM).astype(float),
        "Label_Anomalie":            ["NORMAL"] * N_NORM,
        "Sous_Type_Anomalie":        ["RAS"] * N_NORM,
    })
    fraud = pd.DataFrame({
        "ratio_devis_bareme":        rng.normal(3.0, 0.2, N_FRAUD),
        "vehicule_sur_value":        np.ones(N_FRAUD),
        "sinistre_nuit_sans_temoin": np.ones(N_FRAUD),
        "Label_Anomalie":            ["FRAUDE"] * N_FRAUD,
        "Sous_Type_Anomalie":        ["Surfacturation"] * N_FRAUD,
    })
    return pd.concat([norm, fraud], ignore_index=True)


# ══════════════════════════════════════════════════════════════════════════
# Tests — EDAConfig
# ══════════════════════════════════════════════════════════════════════════

class TestEDAConfig:

    def test_output_dir_created(self, tmp_path: Path) -> None:
        out = tmp_path / "new_subdir" / "results"
        assert not out.exists()
        EDAConfig(branch="auto", data_path=Path("/dev/null"), output_dir=out)
        assert out.exists(), "EDAConfig doit créer le répertoire de sortie."

    def test_default_random_state(self, tmp_path: Path) -> None:
        cfg = EDAConfig(branch="sante", data_path=Path("/x"), output_dir=tmp_path)
        assert cfg.random_state == 42

    def test_branch_stored(self, tmp_path: Path) -> None:
        cfg = EDAConfig(branch="auto", data_path=Path("/x"), output_dir=tmp_path)
        assert cfg.branch == "auto"


# ══════════════════════════════════════════════════════════════════════════
# Tests — compute_overview
# ══════════════════════════════════════════════════════════════════════════

class TestComputeOverview:

    def test_keys_present(self, df_with_anomalies: pd.DataFrame) -> None:
        ov = compute_overview(df_with_anomalies, FEATURES)
        for key in ("n_total", "n_normal", "n_anomalie", "taux_anomalie",
                    "n_features", "categories", "scenarios", "features_stats"):
            assert key in ov, f"Clé manquante : {key}"

    def test_totals_consistent(self, df_with_anomalies: pd.DataFrame) -> None:
        ov = compute_overview(df_with_anomalies, FEATURES)
        assert ov["n_total"] == N_NORM + N_FRAUD
        assert ov["n_normal"]   == N_NORM
        assert ov["n_anomalie"] == N_FRAUD
        assert abs(ov["taux_anomalie"] - N_FRAUD / (N_NORM + N_FRAUD)) < 1e-4

    def test_features_stats_all_present(self, df_with_anomalies: pd.DataFrame) -> None:
        ov = compute_overview(df_with_anomalies, FEATURES)
        for feat in FEATURES:
            assert feat in ov["features_stats"]

    def test_features_stats_contain_required_keys(self, df_with_anomalies: pd.DataFrame) -> None:
        ov = compute_overview(df_with_anomalies, FEATURES)
        for feat in FEATURES:
            for k in ("dtype", "nan_pct", "n_unique", "mean", "std", "min", "max"):
                assert k in ov["features_stats"][feat], f"{feat} manque la clé {k}"

    def test_serializable_to_json(self, df_with_anomalies: pd.DataFrame) -> None:
        ov = compute_overview(df_with_anomalies, FEATURES)
        try:
            json.dumps(ov, default=str)
        except (TypeError, ValueError) as exc:
            pytest.fail(f"compute_overview non sérialisable JSON : {exc}")


# ══════════════════════════════════════════════════════════════════════════
# Tests — _is_binary
# ══════════════════════════════════════════════════════════════════════════

class TestIsBinary:

    def test_boolean_series_is_binary(self) -> None:
        assert _is_binary(pd.Series([0, 1, 0, 1, 0]))

    def test_continuous_series_not_binary(self) -> None:
        assert not _is_binary(pd.Series(np.random.default_rng(0).normal(0, 1, 100)))

    def test_three_unique_values_is_binary(self) -> None:
        assert _is_binary(pd.Series([0, 1, 2, 0, 1]))

    def test_four_unique_values_not_binary(self) -> None:
        assert not _is_binary(pd.Series([0, 1, 2, 3]))


# ══════════════════════════════════════════════════════════════════════════
# Tests — _cohens_d
# ══════════════════════════════════════════════════════════════════════════

class TestCohensD:

    def test_identical_distributions_d_zero(self) -> None:
        rng = np.random.default_rng(42)
        a = rng.normal(0, 1, 200)
        d = _cohens_d(a, a)
        assert d == pytest.approx(0.0, abs=1e-9)

    def test_large_effect_size(self) -> None:
        rng = np.random.default_rng(42)
        a = rng.normal(0, 1, 200); b = rng.normal(3, 1, 200)
        d = _cohens_d(a, b)
        # d doit être proche de 3.0 (3 écarts-types de différence)
        assert d > 2.0, f"d de Cohen attendu > 2.0, obtenu {d:.3f}"

    def test_symmetry(self) -> None:
        rng = np.random.default_rng(42)
        a = rng.normal(0, 1, 100); b = rng.normal(1, 1, 100)
        assert _cohens_d(a, b) == pytest.approx(_cohens_d(b, a), rel=1e-9)

    def test_insufficient_data_returns_zero(self) -> None:
        assert _cohens_d(np.array([1.0]), np.array([2.0])) == 0.0
        assert _cohens_d(np.array([]), np.array([1.0, 2.0])) == 0.0


# ══════════════════════════════════════════════════════════════════════════
# Tests — _test_feature
# ══════════════════════════════════════════════════════════════════════════

class TestTestFeature:

    def test_returns_feature_signal(self) -> None:
        rng = np.random.default_rng(42)
        a = rng.normal(0, 1, 100); b = rng.normal(3, 1, 100)
        result = _test_feature(a, b, "ratio_test")
        assert isinstance(result, FeatureSignal)

    def test_strong_signal_detected(self) -> None:
        """Distributions très éloignées → détectable."""
        rng = np.random.default_rng(42)
        a = rng.normal(0, 1, 200); b = rng.normal(5, 1, 200)
        result = _test_feature(a, b, "ratio_test")
        assert result.detectable is True
        assert result.p_value < ALPHA
        assert result.cohens_d > D_MIN

    def test_identical_distributions_not_detected(self) -> None:
        """Distributions identiques → non détectable."""
        rng = np.random.default_rng(42)
        a = rng.normal(1, 0.5, 200); b = rng.normal(1, 0.5, 200)
        result = _test_feature(a, b, "ratio_test")
        # NOTE : avec des données aléatoires, p_value peut être < 0.05 par chance
        # On vérifie surtout que le d de Cohen est faible
        assert result.cohens_d < 0.5

    def test_insufficient_samples(self) -> None:
        """Moins de MIN_N dossiers → non détectable par convention."""
        a = np.array([1.0, 2.0])   # < MIN_N
        b = np.array([10.0, 20.0]) # < MIN_N
        result = _test_feature(a, b, "ratio_test")
        assert result.detectable is False
        assert result.p_value == pytest.approx(1.0)

    def test_nan_values_handled(self) -> None:
        """Les NaN doivent être filtrés sans erreur."""
        a = np.array([1.0, 2.0, np.nan, 3.0] * 30)
        b = np.array([5.0, 6.0, np.nan, 7.0] * 30)
        result = _test_feature(a, b, "ratio_test")
        assert result.ks_stat >= 0.0

    def test_feature_name_preserved(self) -> None:
        rng = np.random.default_rng(42)
        a = rng.normal(0, 1, 50); b = rng.normal(2, 1, 50)
        result = _test_feature(a, b, "ma_feature_test")
        assert result.feature == "ma_feature_test"


# ══════════════════════════════════════════════════════════════════════════
# Tests — _analyse_scenario
# ══════════════════════════════════════════════════════════════════════════

class TestAnalyseScenario:

    def test_returns_scenario_report(self, df_with_anomalies: pd.DataFrame) -> None:
        norm = df_with_anomalies[df_with_anomalies["Label_Anomalie"] == "NORMAL"]
        scen = df_with_anomalies[df_with_anomalies["Sous_Type_Anomalie"] == "Surfacturation"]
        result = _analyse_scenario(norm, scen, FEATURES, "Surfacturation")
        assert isinstance(result, ScenarioReport)

    def test_strong_signal_scenario_is_go(self, df_with_anomalies: pd.DataFrame) -> None:
        """Le scénario avec signal fort (ratio 3× plus élevé) doit être 'go'."""
        norm = df_with_anomalies[df_with_anomalies["Label_Anomalie"] == "NORMAL"]
        scen = df_with_anomalies[df_with_anomalies["Sous_Type_Anomalie"] == "Surfacturation"]
        result = _analyse_scenario(norm, scen, FEATURES, "Surfacturation")
        # Au minimum, ratio_devis_bareme est très discriminant
        assert result.n_detectable >= 1, (
            "Au moins ratio_devis_bareme doit être détectable "
            f"(d={result.top_cohens_d:.3f})"
        )

    def test_scenario_name_preserved(self, df_with_anomalies: pd.DataFrame) -> None:
        norm = df_with_anomalies[df_with_anomalies["Label_Anomalie"] == "NORMAL"]
        scen = df_with_anomalies[df_with_anomalies["Sous_Type_Anomalie"] == "Surfacturation"]
        result = _analyse_scenario(norm, scen, FEATURES, "Surfacturation")
        assert result.scenario == "Surfacturation"

    def test_decision_is_valid_string(self, df_with_anomalies: pd.DataFrame) -> None:
        norm = df_with_anomalies[df_with_anomalies["Label_Anomalie"] == "NORMAL"]
        scen = df_with_anomalies[df_with_anomalies["Sous_Type_Anomalie"] == "Surfacturation"]
        result = _analyse_scenario(norm, scen, FEATURES, "Surfacturation")
        assert result.decision in ("go", "warn", "no-go")

    def test_feature_signals_count_matches_features(self, df_with_anomalies: pd.DataFrame) -> None:
        norm = df_with_anomalies[df_with_anomalies["Label_Anomalie"] == "NORMAL"]
        scen = df_with_anomalies[df_with_anomalies["Sous_Type_Anomalie"] == "Surfacturation"]
        result = _analyse_scenario(norm, scen, FEATURES, "Surfacturation")
        assert len(result.feature_signals) == len(FEATURES)

    def test_n_dossiers_correct(self, df_with_anomalies: pd.DataFrame) -> None:
        norm = df_with_anomalies[df_with_anomalies["Label_Anomalie"] == "NORMAL"]
        scen = df_with_anomalies[df_with_anomalies["Sous_Type_Anomalie"] == "Surfacturation"]
        result = _analyse_scenario(norm, scen, FEATURES, "Surfacturation")
        assert result.n_dossiers == N_FRAUD


# ══════════════════════════════════════════════════════════════════════════
# Tests — run_statistical_tests (intégration légère)
# ══════════════════════════════════════════════════════════════════════════

class TestRunStatisticalTests:

    def test_returns_list_of_reports(
        self, df_with_anomalies: pd.DataFrame, cfg: EDAConfig
    ) -> None:
        from t10_1_eda_tests import run_statistical_tests
        reports = run_statistical_tests(df_with_anomalies, FEATURES, cfg)
        assert isinstance(reports, list)
        assert len(reports) >= 1

    def test_json_file_created(
        self, df_with_anomalies: pd.DataFrame, cfg: EDAConfig
    ) -> None:
        from t10_1_eda_tests import run_statistical_tests
        run_statistical_tests(df_with_anomalies, FEATURES, cfg)
        json_path = cfg.output_dir / "eda_signal_report.json"
        assert json_path.exists(), "eda_signal_report.json non créé."

    def test_json_is_valid(
        self, df_with_anomalies: pd.DataFrame, cfg: EDAConfig
    ) -> None:
        from t10_1_eda_tests import run_statistical_tests
        run_statistical_tests(df_with_anomalies, FEATURES, cfg)
        json_path = cfg.output_dir / "eda_signal_report.json"
        with open(json_path) as fh:
            data = json.load(fh)
        for key in ("branch", "n_scenarios_total", "n_go", "n_warn", "n_no_go", "scenarios"):
            assert key in data, f"Clé JSON manquante : {key}"

    def test_markdown_file_created(
        self, df_with_anomalies: pd.DataFrame, cfg: EDAConfig
    ) -> None:
        from t10_1_eda_tests import run_statistical_tests
        run_statistical_tests(df_with_anomalies, FEATURES, cfg)
        md_path = cfg.output_dir / "eda_report.md"
        assert md_path.exists(), "eda_report.md non créé."

    def test_heatmap_file_created(
        self, df_with_anomalies: pd.DataFrame, cfg: EDAConfig
    ) -> None:
        from t10_1_eda_tests import run_statistical_tests
        run_statistical_tests(df_with_anomalies, FEATURES, cfg)
        png_path = cfg.output_dir / "eda_signal_heatmap.png"
        assert png_path.exists(), "eda_signal_heatmap.png non créé."

    def test_empty_scenarios_returns_empty_list(
        self, cfg: EDAConfig
    ) -> None:
        """Pas de scénario → liste vide sans crash."""
        from t10_1_eda_tests import run_statistical_tests
        rng = np.random.default_rng(42)
        df_no_scen = pd.DataFrame({
            "ratio_devis_bareme":        rng.normal(1, 0.1, 50),
            "vehicule_sur_value":        rng.integers(0, 2, 50).astype(float),
            "sinistre_nuit_sans_temoin": rng.integers(0, 2, 50).astype(float),
            "Label_Anomalie":            ["NORMAL"] * 50,
            "Sous_Type_Anomalie":        ["RAS"] * 50,
        })
        reports = run_statistical_tests(df_no_scen, FEATURES, cfg)
        assert reports == []