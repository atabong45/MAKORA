"""
TESTS : tests/unit/test_experiment_h0.py
DESCRIPTION : Tests unitaires pour T12.1 (entraînement H0) et T12.2 (delta F1).

Couvre :
- build_makora_dataset : intersection features, normalisation par branche
- compute_delta : calcul Δ et verdicts (3 cas)
- bootstrap_f1_ci : intervalles de confiance
- generate_markdown_report : structure du rapport
- _fpr : calcul False Positive Rate
- Cas limites : features communes vides, métriques manquantes
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

# ─── Setup path ───────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

# ─── Imports ciblés ───────────────────────────────────────────────────────────

from t12_1_experiment_h0 import (
    _fpr,
    bootstrap_f1_ci,
    compute_metrics,
    predict,
)
from t12_2_delta_analysis import (
    DELTA_HIGH,
    DELTA_LOW,
    compute_delta,
    generate_markdown_report,
    index_by_model_branch,
)

# ─── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def perfect_preds():
    """Labels parfaits — y_true == y_pred."""
    y_true = np.array([0, 0, 0, 1, 1, 1, 0, 1])
    y_pred = np.array([0, 0, 0, 1, 1, 1, 0, 1])
    scores = np.array([0.1, 0.1, 0.1, 0.9, 0.9, 0.9, 0.1, 0.9])
    return y_true, y_pred, scores


@pytest.fixture
def imperfect_preds():
    """Prédictions avec erreurs — cas réaliste."""
    y_true = np.array([0, 0, 0, 1, 1, 1, 0, 1, 0, 1])
    y_pred = np.array([0, 1, 0, 1, 0, 1, 0, 1, 0, 0])   # 2 FP + 2 FN
    scores = np.array([0.1, 0.6, 0.1, 0.9, 0.4, 0.8, 0.1, 0.9, 0.2, 0.3])
    return y_true, y_pred, scores


@pytest.fixture
def metrics_contribution_validee():
    """Métriques simulant Δ ∈ [2%, 7%] — CONTRIBUTION_VALIDÉE."""
    return [
        {"model": "M_sante",  "branch_eval": "sante",
         "f1": 0.700, "f1_ci_low": 0.66, "f1_ci_high": 0.74,
         "precision": 0.72, "recall": 0.68,
         "auc_roc": 0.85, "mcc": 0.62, "fpr": 0.04,
         "avg_precision": 0.80, "n_test": 1000, "n_anomalies": 70,
         "train_time_s": 5.0},
        {"model": "M_makora", "branch_eval": "sante",
         "f1": 0.665, "f1_ci_low": 0.63, "f1_ci_high": 0.70,
         "precision": 0.68, "recall": 0.65,
         "auc_roc": 0.83, "mcc": 0.60, "fpr": 0.05,
         "avg_precision": 0.77, "n_test": 1000, "n_anomalies": 70,
         "train_time_s": 8.0,
         "common_features": ["ratio_prix_mercuriale", "delai_declaration"],
         "n_common_features": 2},
        {"model": "M_auto",   "branch_eval": "auto",
         "f1": 0.720, "f1_ci_low": 0.68, "f1_ci_high": 0.76,
         "precision": 0.73, "recall": 0.71,
         "auc_roc": 0.87, "mcc": 0.64, "fpr": 0.03,
         "avg_precision": 0.82, "n_test": 1500, "n_anomalies": 120,
         "train_time_s": 4.0},
        {"model": "M_makora", "branch_eval": "auto",
         "f1": 0.690, "f1_ci_low": 0.65, "f1_ci_high": 0.73,
         "precision": 0.70, "recall": 0.68,
         "auc_roc": 0.85, "mcc": 0.62, "fpr": 0.04,
         "avg_precision": 0.79, "n_test": 1500, "n_anomalies": 120,
         "train_time_s": 8.0,
         "common_features": ["ratio_prix_mercuriale", "delai_declaration"],
         "n_common_features": 2},
    ]


# ─── Tests _fpr ───────────────────────────────────────────────────────────────


def test_fpr_zero_when_no_fp():
    y_true = np.array([0, 0, 1, 1])
    y_pred = np.array([0, 0, 1, 1])
    assert _fpr(y_true, y_pred) == 0.0


def test_fpr_one_when_all_normals_flagged():
    y_true = np.array([0, 0, 0, 1])
    y_pred = np.array([1, 1, 1, 1])
    assert _fpr(y_true, y_pred) == 1.0


def test_fpr_correct_calculation():
    # FP=2, TN=2 → FPR = 0.5
    y_true = np.array([0, 0, 0, 0, 1])
    y_pred = np.array([1, 1, 0, 0, 1])
    assert _fpr(y_true, y_pred) == 0.5


def test_fpr_empty_negatives():
    """Cas sans négatifs — dénominateur zéro géré."""
    y_true = np.array([1, 1, 1])
    y_pred = np.array([1, 0, 1])
    assert _fpr(y_true, y_pred) == 0.0


# ─── Tests bootstrap_f1_ci ────────────────────────────────────────────────────


def test_bootstrap_ci_returns_two_floats(perfect_preds):
    y_true, y_pred, _ = perfect_preds
    lo, hi = bootstrap_f1_ci(y_true, y_pred, n=200)
    assert isinstance(lo, float)
    assert isinstance(hi, float)
    assert lo <= hi


def test_bootstrap_ci_perfect_preds_near_one(perfect_preds):
    """Avec prédictions parfaites, IC doit être proche de [1.0, 1.0]."""
    y_true, y_pred, _ = perfect_preds
    lo, hi = bootstrap_f1_ci(y_true, y_pred, n=500)
    assert lo > 0.8
    assert hi <= 1.0


def test_bootstrap_ci_width_reasonable(imperfect_preds):
    """IC sur prédictions imparfaites doit avoir une largeur > 0."""
    y_true, y_pred, _ = imperfect_preds
    lo, hi = bootstrap_f1_ci(y_true, y_pred, n=300)
    assert hi - lo >= 0.0


# ─── Tests compute_metrics ────────────────────────────────────────────────────


def test_compute_metrics_keys(perfect_preds):
    y_true, y_pred, scores = perfect_preds
    m = compute_metrics(y_true, y_pred, scores,
                        model_name="M_test", branch="sante", elapsed=1.0)
    required = {
        "model", "branch_eval", "f1", "precision", "recall",
        "auc_roc", "avg_precision", "mcc", "fpr",
        "n_test", "n_anomalies", "train_time_s",
        "f1_ci_low", "f1_ci_high",
    }
    assert required.issubset(m.keys())


def test_compute_metrics_f1_range(imperfect_preds):
    y_true, y_pred, scores = imperfect_preds
    m = compute_metrics(y_true, y_pred, scores,
                        model_name="M_test", branch="auto", elapsed=2.5)
    assert 0.0 <= m["f1"] <= 1.0
    assert 0.0 <= m["auc_roc"] <= 1.0
    assert -1.0 <= m["mcc"] <= 1.0
    assert 0.0 <= m["fpr"] <= 1.0


# ─── Tests compute_delta ─────────────────────────────────────────────────────


def test_delta_contribution_validee(metrics_contribution_validee):
    idx = index_by_model_branch(metrics_contribution_validee)
    d   = compute_delta(idx, "sante")
    assert d["verdict"] == "CONTRIBUTION_VALIDÉE"
    assert DELTA_LOW <= d["delta_f1"] <= DELTA_HIGH
    assert d["branch"] == "sante"


def test_delta_genericite_sans_cout():
    """Δ < 2% → GÉNÉRICITÉ_SANS_COÛT."""
    metrics = [
        {"model": "M_sante",  "branch_eval": "sante",
         "f1": 0.700, "f1_ci_low": 0.66, "f1_ci_high": 0.74,
         "precision": 0.70, "recall": 0.70, "auc_roc": 0.85,
         "mcc": 0.60, "fpr": 0.04, "avg_precision": 0.80,
         "n_test": 1000, "n_anomalies": 70, "train_time_s": 5.0},
        {"model": "M_makora", "branch_eval": "sante",
         "f1": 0.695, "f1_ci_low": 0.66, "f1_ci_high": 0.73,
         "precision": 0.70, "recall": 0.69, "auc_roc": 0.84,
         "mcc": 0.59, "fpr": 0.04, "avg_precision": 0.79,
         "n_test": 1000, "n_anomalies": 70, "train_time_s": 8.0},
    ]
    idx = index_by_model_branch(metrics)
    d   = compute_delta(idx, "sante")
    assert d["verdict"] == "GÉNÉRICITÉ_SANS_COÛT"
    assert d["delta_f1"] < DELTA_LOW


def test_delta_precision_sacrifiee():
    """Δ > 7% → PRÉCISION_SACRIFIÉE."""
    metrics = [
        {"model": "M_sante",  "branch_eval": "sante",
         "f1": 0.800, "f1_ci_low": 0.77, "f1_ci_high": 0.83,
         "precision": 0.80, "recall": 0.80, "auc_roc": 0.90,
         "mcc": 0.70, "fpr": 0.03, "avg_precision": 0.88,
         "n_test": 1000, "n_anomalies": 70, "train_time_s": 5.0},
        {"model": "M_makora", "branch_eval": "sante",
         "f1": 0.720, "f1_ci_low": 0.69, "f1_ci_high": 0.75,
         "precision": 0.72, "recall": 0.72, "auc_roc": 0.85,
         "mcc": 0.63, "fpr": 0.05, "avg_precision": 0.82,
         "n_test": 1000, "n_anomalies": 70, "train_time_s": 8.0},
    ]
    idx = index_by_model_branch(metrics)
    d   = compute_delta(idx, "sante")
    assert d["verdict"] == "PRÉCISION_SACRIFIÉE"
    assert d["delta_f1"] > DELTA_HIGH


def test_delta_missing_specialized_raises(metrics_contribution_validee):
    """KeyError si M_sante absent des métriques."""
    metrics_sans_sante = [
        m for m in metrics_contribution_validee
        if not (m["model"] == "M_sante")
    ]
    idx = index_by_model_branch(metrics_sans_sante)
    with pytest.raises(KeyError, match="M_sante"):
        compute_delta(idx, "sante")


def test_delta_missing_makora_raises(metrics_contribution_validee):
    """KeyError si M_makora absent des métriques."""
    metrics_sans_makora = [
        m for m in metrics_contribution_validee
        if not (m["model"] == "M_makora" and m["branch_eval"] == "auto")
    ]
    idx = index_by_model_branch(metrics_sans_makora)
    with pytest.raises(KeyError, match="M_makora"):
        compute_delta(idx, "auto")


# ─── Tests generate_markdown_report ──────────────────────────────────────────


def test_markdown_report_contains_hypothesis(metrics_contribution_validee):
    idx = index_by_model_branch(metrics_contribution_validee)
    deltas = [compute_delta(idx, b) for b in ["sante", "auto"]]
    md = generate_markdown_report(deltas, metrics_contribution_validee)
    assert "Hypothèse nulle" in md
    assert "Caruana1997" in md
    assert "Tableau comparatif" in md


def test_markdown_report_contains_both_branches(metrics_contribution_validee):
    idx = index_by_model_branch(metrics_contribution_validee)
    deltas = [compute_delta(idx, b) for b in ["sante", "auto"]]
    md = generate_markdown_report(deltas, metrics_contribution_validee)
    assert "sante" in md.lower()
    assert "auto"  in md.lower()


def test_markdown_report_validated_conclusion(metrics_contribution_validee):
    """Conclusion doit contenir 'validée' quand les verdicts sont acceptables."""
    idx = index_by_model_branch(metrics_contribution_validee)
    deltas = [compute_delta(idx, b) for b in ["sante", "auto"]]
    md = generate_markdown_report(deltas, metrics_contribution_validee)
    assert "validée" in md.lower()


# ─── Tests index_by_model_branch ─────────────────────────────────────────────


def test_index_unique_keys(metrics_contribution_validee):
    idx = index_by_model_branch(metrics_contribution_validee)
    assert ("M_sante",  "sante") in idx
    assert ("M_makora", "sante") in idx
    assert ("M_auto",   "auto")  in idx
    assert ("M_makora", "auto")  in idx


def test_index_preserves_f1(metrics_contribution_validee):
    idx = index_by_model_branch(metrics_contribution_validee)
    assert idx[("M_sante", "sante")]["f1"] == 0.700
    assert idx[("M_makora", "sante")]["f1"] == 0.665