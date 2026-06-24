"""
TESTS : tests/unit/test_drift_monitor.py
DESCRIPTION : Suite de tests unitaires pour core/drift_monitor.py.

COUVERTURE :
  TestPSIFormula          — formule PSI isolée (zéro drift, drift maximal, symétrie)
  TestFitReference        — fit_reference() : colonnes manquantes, taille minimale
  TestClassification      — seuils STABLE/WARNING/CRITICAL/UNKNOWN
  TestAggregation         — statut global = max(statuts features)
  TestComputeBasic        — compute() sur données stables et driftées
  TestTemporalFiltering   — filtrage par fenêtre date (Batch_Date)
  TestUpdateReference     — update_reference() remplace la référence
  TestToDict              — sérialisation DriftReport.to_dict()
  TestGenericity          — même config fonctionne sur "sante" et "auto"
  TestEdgeCases           — df vide, feature absente, fit non appelé

RÉFÉRENCES :
- [Gama2014] Gama et al. (2014). A survey on concept drift adaptation. ACM CS.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

# ---------------------------------------------------------------------------
# Import du module testé
# Adapter le chemin selon la structure du projet :
#   from core.drift_monitor import DriftMonitor, DriftReport, FeatureDrift
# ---------------------------------------------------------------------------
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from core.drift_monitor import (  # noqa: E402
    DriftMonitor,
    DriftReport,
    FeatureDrift,
    _DEFAULT_CRITICAL,
    _DEFAULT_WARNING,
    _MIN_SAMPLES,
)


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES
# ─────────────────────────────────────────────────────────────────────────────

MINIMAL_CONFIG = {
    "features_to_monitor": ["feature_a", "feature_b"],
    "reference_window_days": 90,
    "current_window_days": 30,
    "thresholds": {"warning": 0.10, "critical": 0.20},
}


def _make_df(
    n: int = 200,
    shift: float = 0.0,
    seed: int = 42,
    add_date_col: bool = False,
    base_date: str = "2025-01-01",
) -> pd.DataFrame:
    """Génère un DataFrame de test avec feature_a et feature_b."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame({
        "feature_a": rng.normal(loc=0.0 + shift, scale=1.0, size=n),
        "feature_b": rng.normal(loc=5.0 + shift, scale=2.0, size=n),
    })
    if add_date_col:
        start = pd.Timestamp(base_date)
        df["Batch_Date"] = [
            (start + timedelta(days=i % 120)).strftime("%Y-%m-%d")
            for i in range(n)
        ]
    return df


def _fitted_monitor(config: dict = MINIMAL_CONFIG) -> DriftMonitor:
    """Retourne un DriftMonitor déjà fitté."""
    monitor = DriftMonitor(branch="test_branch", config=config)
    monitor.fit_reference(_make_df(n=500))
    return monitor


# ─────────────────────────────────────────────────────────────────────────────
# TestPSIFormula
# ─────────────────────────────────────────────────────────────────────────────

class TestPSIFormula:
    """Tests de la formule PSI isolée. [Gama2014]"""

    def test_zero_drift_yields_near_zero_psi(self):
        """Distribution identique → PSI ≈ 0."""
        monitor = DriftMonitor(branch="test", config=MINIMAL_CONFIG)
        dist = np.array([10.0, 20.0, 30.0, 25.0, 15.0])
        psi = monitor._psi_formula(dist, dist.copy())
        assert psi < 0.01, f"PSI attendu ≈ 0, obtenu {psi:.6f}"

    def test_high_drift_yields_large_psi(self):
        """Distribution très différente → PSI élevé (>= 0.20)."""
        monitor = DriftMonitor(branch="test", config=MINIMAL_CONFIG)
        expected = np.array([50.0, 30.0, 10.0, 5.0, 5.0])
        actual = np.array([5.0, 5.0, 10.0, 30.0, 50.0])
        psi = monitor._psi_formula(expected, actual)
        assert psi >= _DEFAULT_CRITICAL, f"PSI attendu >= {_DEFAULT_CRITICAL}, obtenu {psi:.4f}"

    def test_psi_non_negative(self):
        """Le PSI est toujours non-négatif."""
        monitor = DriftMonitor(branch="test", config=MINIMAL_CONFIG)
        rng = np.random.default_rng(0)
        for _ in range(20):
            a = rng.integers(1, 100, size=8).astype(float)
            b = rng.integers(1, 100, size=8).astype(float)
            psi = monitor._psi_formula(a, b)
            assert psi >= 0.0, f"PSI négatif : {psi}"

    def test_epsilon_prevents_division_by_zero(self):
        """Bin vide dans expected → pas d'exception."""
        monitor = DriftMonitor(branch="test", config=MINIMAL_CONFIG)
        expected = np.array([0.0, 10.0, 20.0, 30.0, 40.0])
        actual = np.array([5.0, 10.0, 20.0, 30.0, 35.0])
        psi = monitor._psi_formula(expected, actual)
        assert np.isfinite(psi), "PSI doit être fini même avec bin vide"


# ─────────────────────────────────────────────────────────────────────────────
# TestFitReference
# ─────────────────────────────────────────────────────────────────────────────

class TestFitReference:

    def test_fit_marks_fitted(self):
        monitor = DriftMonitor(branch="test", config=MINIMAL_CONFIG)
        assert not monitor.is_fitted
        monitor.fit_reference(_make_df(n=200))
        assert monitor.is_fitted

    def test_fit_stores_both_features(self):
        monitor = DriftMonitor(branch="test", config=MINIMAL_CONFIG)
        monitor.fit_reference(_make_df(n=200))
        assert "feature_a" in monitor._reference
        assert "feature_b" in monitor._reference

    def test_fit_ignores_missing_columns(self):
        """Feature absente du df → pas d'entrée dans _reference, pas d'exception."""
        config = {**MINIMAL_CONFIG, "features_to_monitor": ["feature_a", "MISSING"]}
        monitor = DriftMonitor(branch="test", config=config)
        monitor.fit_reference(_make_df(n=200))
        assert "feature_a" in monitor._reference
        assert "MISSING" not in monitor._reference

    def test_fit_skips_small_series(self):
        """Série < _MIN_SAMPLES → non stockée dans _reference."""
        monitor = DriftMonitor(branch="test", config=MINIMAL_CONFIG)
        monitor.fit_reference(_make_df(n=_MIN_SAMPLES - 1))
        # Les deux features ont n < _MIN_SAMPLES → rien stocké
        assert len(monitor._reference) == 0
        assert not monitor.is_fitted

    def test_fit_with_nans_handles_gracefully(self):
        """NaN dans la série de référence → dropna() → fit sans erreur."""
        df = _make_df(n=200)
        df.loc[:10, "feature_a"] = np.nan
        monitor = DriftMonitor(branch="test", config=MINIMAL_CONFIG)
        monitor.fit_reference(df)
        assert "feature_a" in monitor._reference


# ─────────────────────────────────────────────────────────────────────────────
# TestClassification
# ─────────────────────────────────────────────────────────────────────────────

class TestClassification:

    def _monitor(self):
        return DriftMonitor(branch="test", config=MINIMAL_CONFIG)

    def test_stable(self):
        assert self._monitor()._classify(0.05) == "STABLE"

    def test_warning_lower_bound(self):
        assert self._monitor()._classify(0.10) == "WARNING"

    def test_warning_mid(self):
        assert self._monitor()._classify(0.15) == "WARNING"

    def test_critical_lower_bound(self):
        assert self._monitor()._classify(0.20) == "CRITICAL"

    def test_critical_high(self):
        assert self._monitor()._classify(0.50) == "CRITICAL"

    def test_custom_thresholds(self):
        """Seuils personnalisés depuis YAML."""
        config = {**MINIMAL_CONFIG, "thresholds": {"warning": 0.05, "critical": 0.15}}
        monitor = DriftMonitor(branch="test", config=config)
        assert monitor._classify(0.06) == "WARNING"
        assert monitor._classify(0.15) == "CRITICAL"


# ─────────────────────────────────────────────────────────────────────────────
# TestAggregation
# ─────────────────────────────────────────────────────────────────────────────

class TestAggregation:

    def _monitor(self):
        return DriftMonitor(branch="test", config=MINIMAL_CONFIG)

    def _fd(self, status: str) -> FeatureDrift:
        return FeatureDrift(feature="f", psi=0.0, status=status, n_reference=100, n_current=100)

    def test_all_stable(self):
        features = {"a": self._fd("STABLE"), "b": self._fd("STABLE")}
        assert self._monitor()._aggregate_status(features) == "STABLE"

    def test_one_warning(self):
        features = {"a": self._fd("STABLE"), "b": self._fd("WARNING")}
        assert self._monitor()._aggregate_status(features) == "WARNING"

    def test_one_critical_wins(self):
        features = {
            "a": self._fd("STABLE"),
            "b": self._fd("WARNING"),
            "c": self._fd("CRITICAL"),
        }
        assert self._monitor()._aggregate_status(features) == "CRITICAL"

    def test_empty_returns_unknown(self):
        assert self._monitor()._aggregate_status({}) == "UNKNOWN"

    def test_unknown_below_warning(self):
        features = {"a": self._fd("UNKNOWN"), "b": self._fd("STABLE")}
        assert self._monitor()._aggregate_status(features) == "UNKNOWN"


# ─────────────────────────────────────────────────────────────────────────────
# TestComputeBasic
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeBasic:

    def test_compute_stable_on_same_distribution(self):
        """Même distribution → STABLE."""
        monitor = _fitted_monitor()
        report = monitor.compute(_make_df(n=300, seed=99))
        assert report.status == "STABLE"
        assert isinstance(report, DriftReport)

    def test_compute_critical_on_large_shift(self):
        """Shift de 10 sigma → CRITICAL."""
        monitor = _fitted_monitor()
        # shift=10 → distribution complètement différente
        report = monitor.compute(_make_df(n=300, shift=10.0, seed=7))
        assert report.status == "CRITICAL"

    def test_compute_returns_both_features(self):
        monitor = _fitted_monitor()
        report = monitor.compute(_make_df(n=200))
        assert "feature_a" in report.features
        assert "feature_b" in report.features

    def test_compute_feature_psi_non_negative(self):
        monitor = _fitted_monitor()
        report = monitor.compute(_make_df(n=200))
        for fd in report.features.values():
            assert fd.psi >= 0.0

    def test_compute_without_fit_returns_unknown(self):
        monitor = DriftMonitor(branch="test", config=MINIMAL_CONFIG)
        report = monitor.compute(_make_df(n=200))
        assert report.status == "UNKNOWN"
        assert len(report.features) == 0

    def test_compute_branch_in_report(self):
        monitor = _fitted_monitor()
        report = monitor.compute(_make_df(n=200))
        assert report.branch == "test_branch"

    def test_compute_counts_present(self):
        """n_reference et n_current doivent être remplis."""
        monitor = _fitted_monitor()
        report = monitor.compute(_make_df(n=150))
        for fd in report.features.values():
            assert fd.n_reference > 0
            assert fd.n_current > 0


# ─────────────────────────────────────────────────────────────────────────────
# TestTemporalFiltering
# ─────────────────────────────────────────────────────────────────────────────

class TestTemporalFiltering:

    def test_filter_with_date_col_returns_subset(self):
        """Avec reference_date, seule la fenêtre de 30j est retenue."""
        monitor = _fitted_monitor()
        df = _make_df(n=300, add_date_col=True, base_date="2025-01-01")
        ref_date = datetime(2025, 3, 31)
        df_filtered = monitor._filter_window(df, ref_date)
        dates = pd.to_datetime(df_filtered["Batch_Date"])
        cutoff = ref_date - timedelta(days=30)
        assert (dates >= cutoff).all()
        assert (dates <= ref_date).all()

    def test_filter_without_reference_date_returns_full_df(self):
        monitor = _fitted_monitor()
        df = _make_df(n=100, add_date_col=True)
        result = monitor._filter_window(df, reference_date=None)
        assert len(result) == len(df)

    def test_filter_without_date_col_returns_full_df(self):
        monitor = _fitted_monitor()
        df = _make_df(n=100, add_date_col=False)
        ref_date = datetime(2025, 3, 31)
        result = monitor._filter_window(df, ref_date)
        assert len(result) == len(df)

    def test_filter_empty_window_falls_back_to_full_df(self):
        """Fenêtre vide → fallback sur df entier, pas d'exception."""
        monitor = _fitted_monitor()
        df = _make_df(n=100, add_date_col=True, base_date="2020-01-01")
        # Date de référence très loin dans le futur → fenêtre 30j vide
        ref_date = datetime(2030, 1, 1)
        result = monitor._filter_window(df, ref_date)
        assert len(result) == len(df)


# ─────────────────────────────────────────────────────────────────────────────
# TestUpdateReference
# ─────────────────────────────────────────────────────────────────────────────

class TestUpdateReference:

    def test_update_reference_replaces_old_distributions(self):
        monitor = _fitted_monitor()
        old_ref = dict(monitor._reference)
        new_df = _make_df(n=400, shift=5.0, seed=17)
        monitor.update_reference(new_df)
        # Les distributions doivent avoir changé
        for feat in old_ref:
            old_counts = old_ref[feat][0]
            new_counts = monitor._reference[feat][0]
            assert not np.array_equal(old_counts, new_counts), (
                f"La référence de '{feat}' n'a pas été mise à jour"
            )

    def test_update_reference_keeps_fitted_true(self):
        monitor = _fitted_monitor()
        monitor.update_reference(_make_df(n=300))
        assert monitor.is_fitted


# ─────────────────────────────────────────────────────────────────────────────
# TestToDict
# ─────────────────────────────────────────────────────────────────────────────

class TestToDict:

    def test_to_dict_has_required_keys(self):
        monitor = _fitted_monitor()
        report = monitor.compute(_make_df(n=200))
        d = report.to_dict()
        for key in ("branch", "computed_at", "status", "features",
                    "reference_window_days", "current_window_days"):
            assert key in d, f"Clé manquante : {key}"

    def test_to_dict_features_have_psi_and_status(self):
        monitor = _fitted_monitor()
        report = monitor.compute(_make_df(n=200))
        d = report.to_dict()
        for feat_name, feat_data in d["features"].items():
            assert "psi" in feat_data, f"'psi' absent pour {feat_name}"
            assert "status" in feat_data, f"'status' absent pour {feat_name}"
            assert "n_reference" in feat_data
            assert "n_current" in feat_data

    def test_to_dict_computed_at_is_iso_string(self):
        report = DriftReport(
            branch="sante",
            computed_at=datetime(2025, 6, 15, 10, 30),
            status="STABLE",
        )
        d = report.to_dict()
        assert "2025-06-15" in d["computed_at"]


# ─────────────────────────────────────────────────────────────────────────────
# TestGenericity
# ─────────────────────────────────────────────────────────────────────────────

class TestGenericity:
    """Vérifie que DriftMonitor fonctionne identiquement sur sante et auto."""

    def test_same_config_works_for_sante_and_auto(self):
        for branch in ("sante", "auto"):
            monitor = DriftMonitor(branch=branch, config=MINIMAL_CONFIG)
            monitor.fit_reference(_make_df(n=300))
            report = monitor.compute(_make_df(n=150))
            assert report.branch == branch
            assert report.status in ("STABLE", "WARNING", "CRITICAL", "UNKNOWN")

    def test_branch_name_does_not_affect_psi_computation(self):
        """PSI identique quelle que soit la branche pour les mêmes données."""
        df_ref = _make_df(n=300, seed=1)
        df_cur = _make_df(n=150, seed=2)
        results = {}
        for branch in ("sante", "auto", "vie"):
            m = DriftMonitor(branch=branch, config=MINIMAL_CONFIG)
            m.fit_reference(df_ref)
            report = m.compute(df_cur)
            results[branch] = {
                feat: fd.psi for feat, fd in report.features.items()
            }
        # Tous les PSI doivent être identiques
        assert results["sante"] == results["auto"] == results["vie"]


# ─────────────────────────────────────────────────────────────────────────────
# TestEdgeCases
# ─────────────────────────────────────────────────────────────────────────────

class TestEdgeCases:

    def test_compute_on_empty_df(self):
        """DataFrame vide → UNKNOWN sans exception."""
        monitor = _fitted_monitor()
        df_empty = pd.DataFrame(columns=["feature_a", "feature_b"])
        report = monitor.compute(df_empty)
        assert report.status == "UNKNOWN"
        for fd in report.features.values():
            assert fd.status == "UNKNOWN"

    def test_compute_feature_absent_in_current(self):
        """Feature présente en référence mais absente du batch → UNKNOWN."""
        monitor = _fitted_monitor()
        df = _make_df(n=200).drop(columns=["feature_b"])
        report = monitor.compute(df)
        assert report.features["feature_b"].status == "UNKNOWN"
        assert report.features["feature_b"].n_current == 0

    def test_monitored_features_property(self):
        monitor = DriftMonitor(branch="test", config=MINIMAL_CONFIG)
        assert set(monitor.monitored_features) == {"feature_a", "feature_b"}

    def test_empty_features_to_monitor(self):
        """Config sans features → DriftReport UNKNOWN sans erreur."""
        config = {**MINIMAL_CONFIG, "features_to_monitor": []}
        monitor = DriftMonitor(branch="test", config=config)
        monitor.fit_reference(_make_df(n=200))
        assert not monitor.is_fitted
        report = monitor.compute(_make_df(n=100))
        assert report.status == "UNKNOWN"

    def test_default_thresholds_used_when_absent(self):
        """Config sans 'thresholds' → seuils par défaut."""
        config = {"features_to_monitor": ["feature_a"]}
        monitor = DriftMonitor(branch="test", config=config)
        assert monitor._warn_thr == _DEFAULT_WARNING
        assert monitor._crit_thr == _DEFAULT_CRITICAL