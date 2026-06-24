"""
MODULE : scripts/t13_bootstrap_ci_candidates.py
DESCRIPTION : IC bootstrap 95% sur les 10 meilleurs candidats par famille.
              Charge chaque modèle persisté, applique le seuil calibré,
              calcule MCC / F1 / AUC / AP / FPR + IC [2.5%-97.5%].
              Résultats dans results/{branch}/t13_bootstrap_ci_candidates.json

RÉFÉRENCES ACADÉMIQUES :
- [Efron1979] Efron, B. (1979). Bootstrap Methods: Another Look at the
  Jackknife. The Annals of Statistics, 7(1), 1-26.
  → n=1000 rééchantillonnages avec remise, percentiles [2.5, 97.5]
- [Chicco2020] Chicco & Jurman (2020). The advantages of MCC. BMC Genomics.
  → MCC est la métrique principale ; F1/AUC reportés pour comparaison
- [Goldstein2016] Goldstein & Uchida (2016). Comparative evaluation of
  unsupervised anomaly detection algorithms. PLOS ONE.
  → Protocole : test set IMMUTABLE, même split pour tous les modèles

DÉCISIONS DE CONCEPTION :
- Pas de réentraînement : les modèles sont chargés depuis joblib.
- Les seuils DIF sont hardcodés (calibrés en T10.4e sur val set).
- Pour HBOS / COPOD / ECOD (PyOD) : predict() retourne 0/1 directement,
  decision_function() retourne le score continu.
- LOF et OC-SVM : inclus pour complétude malgré leur exclusion production.
- EIF : métriques issues de t10_3 (pas de modèle persisté — ADR-010).
- IC OC-SVM : attendu [0.000, 0.000] sur MCC (FPR=1.0, MCC=0.0 connu).
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    matthews_corrcoef,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

# ─── Paths ────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPLITS_DIR   = PROJECT_ROOT / "data" / "splits"
MODELS_DIR   = PROJECT_ROOT / "data" / "models"
RESULTS_DIR  = PROJECT_ROOT / "results"
LABEL_COL    = "Label_Anomalie"
NORMAL_VAL   = "NORMAL"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("makora.bootstrap_ci")
SEP = "─" * 68

# ─── Constantes bootstrap [Efron1979] ─────────────────────────────────────────
N_BOOTSTRAP = 1000
ALPHA       = 0.05
RANDOM_SEED = 42

# ─── Seuils DIF calibrés (hardcodés — T10.4e) ────────────────────────────────
# [Xu2023] — seuils issus de la calibration sur val set
DIF_THRESHOLDS = {
    "sante": {
        "phi_optimal":     0.349775,   # ★ PROD Santé
        "fpr5_constrained": 0.345393,
        "pr_exact":        0.345247,
        "percentile_f1":   0.344733,
        "youden":          0.337231,
    },
    "auto": {
        "fpr5_constrained": 0.341498,  # ★ PROD Auto
        "phi_optimal":     0.339640,
        "pr_exact":        0.332567,
        "percentile_f1":   0.332379,
        "youden":          0.322939,
    },
}

# ─── Candidats par branche ────────────────────────────────────────────────────
# Format : (label_affichage, modele_joblib, scaler_joblib|None, seuil|None,
#            source_scores_override|None)
#   - seuil=None → utiliser model.predict() directement (PyOD / sklearn threshold)
#   - source_scores_override : chemin JSON pour les modèles sans joblib (EIF)
CANDIDATES = {
    "sante": [
        # DIF — modèle unique, 2 seuils de calibration
        ("DIF [64,32] phi_optimal ★",
         "sante/dif_model.joblib", None,
         DIF_THRESHOLDS["sante"]["phi_optimal"], None),
        ("DIF [64,32] fpr5_constrained",
         "sante/dif_model.joblib", None,
         DIF_THRESHOLDS["sante"]["fpr5_constrained"], None),
        # PU Learning — semi-supervisé
        ("PU Learning RF c=0.0935",
         "sante/pu_rf_model.joblib", None, None, None),
        # HBOS
        ("HBOS n_bins=5",
         "sante/hbos_model.joblib", None, None, None),
        # IF famille
        ("IF max_feat=0.7",
         "sante/if_maxfeatures07_model.joblib", None, None, None),
        ("IF classique (baseline)",
         "sante/if_classic_model.joblib", None, None, None),
        # Copule / CDF
        ("COPOD empirique",
         "sante/copod_model.joblib", None, None, None),
        ("ECOD CDF",
         "sante/ecod_model.joblib", None, None, None),
        # LOF — inclus pour complétude (non scalable en prod)
        ("LOF k=20",
         "sante/lof_k20_model.joblib", None, None, None),
        # OC-SVM — écarté (FPR=1.0 attendu)
        ("OC-SVM SGD",
         "sante/ocsvm_sgd_model.joblib",
         "sante/ocsvm_scaler_model.joblib", None, None),
    ],
    "auto": [
        # DIF — fpr5 est le modèle PROD Auto
        ("DIF [64,32] fpr5_constrained ★",
         "auto/dif_model.joblib", None,
         DIF_THRESHOLDS["auto"]["fpr5_constrained"], None),
        ("DIF [64,32] phi_optimal",
         "auto/dif_model.joblib", None,
         DIF_THRESHOLDS["auto"]["phi_optimal"], None),
        # PU Learning
        ("PU Learning RF c=0.0885",
         "auto/pu_rf_model.joblib", None, None, None),
        # HBOS
        ("HBOS n_bins=5",
         "auto/hbos_model.joblib", None, None, None),
        # IF famille
        ("IF max_feat=0.7",
         "auto/if_maxfeatures07_model.joblib", None, None, None),
        ("IF classique (baseline)",
         "auto/if_classic_model.joblib", None, None, None),
        # Copule / CDF
        ("COPOD empirique",
         "auto/copod_model.joblib", None, None, None),
        ("ECOD CDF",
         "auto/ecod_model.joblib", None, None, None),
        # LOF
        ("LOF k=20",
         "auto/lof_k20_model.joblib", None, None, None),
        # OC-SVM
        ("OC-SVM SGD",
         "auto/ocsvm_sgd_model.joblib",
         "auto/ocsvm_scaler_model.joblib", None, None),
    ],
}

# ─── Chargement données ───────────────────────────────────────────────────────

def load_test(branch: str) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Charge le test set, applique le module métier, retourne (X, y, features)."""
    from core.plugin_registry import PluginRegistry
    if branch == "sante":
        import modules.sante.sante_module  # noqa: F401
    else:
        import modules.auto.auto_module    # noqa: F401

    yaml_path = PROJECT_ROOT / "modules" / branch / f"{branch}.yaml"
    module    = PluginRegistry.get(branch)(config_path=yaml_path)

    p  = SPLITS_DIR / branch / f"{branch}_test.parquet"
    df = pd.read_parquet(p)
    df = module.engineer_features(df)
    fts = [c for c in module.get_feature_names() if c in df.columns]
    X   = df[fts].fillna(0).values.astype(np.float32)
    y   = (df[LABEL_COL] != NORMAL_VAL).astype(int).values
    log.info("[%s] test=%d | anomalies=%d (%.1f%%) | features=%d",
             branch.upper(), len(y), y.sum(), 100 * y.mean(), len(fts))
    return X, y, fts

# ─── Scoring ──────────────────────────────────────────────────────────────────

def get_scores_and_preds(
    model_path: str,
    scaler_path: str | None,
    threshold: float | None,
    X: np.ndarray,
) -> tuple[np.ndarray, np.ndarray] | None:
    """
    Charge le modèle, calcule scores continus et prédictions binaires.
    Retourne (scores, y_pred) ou None si le fichier est absent.
    """
    full_path = MODELS_DIR / model_path
    if not full_path.exists():
        log.warning("Modèle absent : %s — skipped", full_path)
        return None

    model  = joblib.load(full_path)
    scaler = joblib.load(MODELS_DIR / scaler_path) if scaler_path else None
    X_in   = scaler.transform(X) if scaler else X

    # Scores continus
    if hasattr(model, "decision_function"):
        raw_scores = model.decision_function(X_in)
        # DIF / PyOD : score élevé = anomalie
        # sklearn IF/LOF : score négatif = anomalie → inverser
        # Heuristique : si la majorité des scores est négative → inverser
        if raw_scores.mean() < 0:
            scores = -raw_scores
        else:
            scores = raw_scores
    elif hasattr(model, "score_samples"):
        scores = -model.score_samples(X_in)
    else:
        log.error("Modèle %s sans decision_function ni score_samples", model_path)
        return None

    # Prédictions binaires
    if threshold is not None:
        # Seuil explicite (DIF calibré)
        y_pred = (scores >= threshold).astype(int)
    elif hasattr(model, "predict"):
        raw_pred = model.predict(X_in)
        # sklearn : -1 = anomalie | PyOD : 1 = anomalie
        if set(np.unique(raw_pred)).issubset({-1, 1}):
            y_pred = (raw_pred == -1).astype(int)
        else:
            y_pred = raw_pred.astype(int)
    else:
        log.error("Modèle %s sans predict()", model_path)
        return None

    return scores, y_pred

# ─── Métriques ponctuelles ────────────────────────────────────────────────────

def point_metrics(
    y_true: np.ndarray,
    scores: np.ndarray,
    y_pred: np.ndarray,
) -> dict:
    """Calcule MCC, F1, AUC, AP, FPR sur les prédictions fournies."""
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return {
        "mcc": round(float(matthews_corrcoef(y_true, y_pred)), 4),
        "f1":  round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "auc": round(float(roc_auc_score(y_true, scores)), 4),
        "ap":  round(float(average_precision_score(y_true, scores)), 4),
        "fpr": round(float(fpr), 4),
        "tp": int(((y_true == 1) & (y_pred == 1)).sum()),
        "fp": fp,
        "fn": int(((y_true == 1) & (y_pred == 0)).sum()),
        "tn": tn,
    }

# ─── Bootstrap IC [Efron1979] ─────────────────────────────────────────────────

def bootstrap_ci(
    y_true: np.ndarray,
    scores: np.ndarray,
    y_pred: np.ndarray,
    n: int = N_BOOTSTRAP,
    seed: int = RANDOM_SEED,
) -> dict:
    """
    IC bootstrap [2.5%-97.5%] sur MCC, F1, AUC, AP, FPR.
    n=1000 rééchantillonnages avec remise [Efron1979].
    Métrique principale : MCC [Chicco2020].
    """
    rng = np.random.RandomState(seed)
    mccs, f1s, aucs, aps, fprs = [], [], [], [], []

    for _ in range(n):
        idx = rng.randint(0, len(y_true), len(y_true))
        yt, sc, yp = y_true[idx], scores[idx], y_pred[idx]
        if len(np.unique(yt)) < 2:
            continue  # skip si un seul classe dans le rééchantillon
        tn = int(((yt == 0) & (yp == 0)).sum())
        fp = int(((yt == 0) & (yp == 1)).sum())
        fpr_i = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        mccs.append(matthews_corrcoef(yt, yp))
        f1s.append(f1_score(yt, yp, zero_division=0))
        aucs.append(roc_auc_score(yt, sc))
        aps.append(average_precision_score(yt, sc))
        fprs.append(fpr_i)

    def ci_dict(values: list) -> dict:
        arr = np.array(values)
        return {
            "mean": round(float(arr.mean()), 4),
            "ci_lo": round(float(np.percentile(arr, 2.5)), 4),
            "ci_hi": round(float(np.percentile(arr, 97.5)), 4),
            "std": round(float(arr.std()), 4),
        }

    return {
        "mcc": ci_dict(mccs),   # ← métrique principale [Chicco2020]
        "f1":  ci_dict(f1s),
        "auc": ci_dict(aucs),
        "ap":  ci_dict(aps),
        "fpr": ci_dict(fprs),
        "n_bootstrap": len(mccs),
    }

# ─── Pipeline principal ───────────────────────────────────────────────────────

def run_branch(branch: str) -> list[dict]:
    log.info(SEP)
    log.info("T-05 Bootstrap IC — Branche %s", branch.upper())
    log.info("n_bootstrap=%d | alpha=%.2f | seed=%d [Efron1979]",
             N_BOOTSTRAP, ALPHA, RANDOM_SEED)
    log.info(SEP)

    X, y_true, _ = load_test(branch)
    candidates   = CANDIDATES[branch]
    results      = []

    for label, model_path, scaler_path, threshold, _ in candidates:
        log.info("── %s ──", label)
        t0 = time.perf_counter()

        out = get_scores_and_preds(model_path, scaler_path, threshold, X)
        if out is None:
            results.append({"label": label, "branch": branch, "status": "SKIPPED"})
            continue

        scores, y_pred = out
        metrics = point_metrics(y_true, scores, y_pred)

        log.info("  MCC=%.4f | F1=%.4f | AUC=%.4f | FPR=%.4f",
                 metrics["mcc"], metrics["f1"], metrics["auc"], metrics["fpr"])
        log.info("  Bootstrap IC [Efron1979] — %d itérations ...", N_BOOTSTRAP)

        ci = bootstrap_ci(y_true, scores, y_pred)

        log.info("  MCC : %.4f [%.4f – %.4f]",
                 ci["mcc"]["mean"], ci["mcc"]["ci_lo"], ci["mcc"]["ci_hi"])
        log.info("  F1  : %.4f [%.4f – %.4f]",
                 ci["f1"]["mean"], ci["f1"]["ci_lo"], ci["f1"]["ci_hi"])
        log.info("  Temps : %.1fs", time.perf_counter() - t0)

        results.append({
            "label":    label,
            "branch":   branch,
            "status":   "OK",
            "metrics":  metrics,
            "bootstrap_ci": ci,
            "threshold": float(threshold) if threshold else None,
            "model_path": model_path,
        })

    # Sauvegarde JSON
    out_dir = RESULTS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "t13_bootstrap_ci_candidates.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    log.info(SEP)
    log.info("JSON → %s", out_path)

    # Résumé console
    log.info("%-40s %8s %14s %8s", "Modèle", "MCC", "IC 95% MCC", "FPR")
    log.info("─" * 76)
    for r in results:
        if r["status"] != "OK":
            log.info("%-40s   SKIPPED", r["label"])
            continue
        ci_mcc = r["bootstrap_ci"]["mcc"]
        log.info("%-40s %8.4f  [%.4f–%.4f]  %6.4f",
                 r["label"],
                 ci_mcc["mean"],
                 ci_mcc["ci_lo"],
                 ci_mcc["ci_hi"],
                 r["metrics"]["fpr"])

    return results

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="T-05 — Bootstrap IC 95% sur 10 candidats par famille [Efron1979]"
    )
    p.add_argument("--branch", choices=["sante", "auto", "both"], default="both")
    return p.parse_args()

def main() -> None:
    args     = parse_args()
    branches = ["sante", "auto"] if args.branch == "both" else [args.branch]
    log.info(SEP)
    log.info("MAKORA — T13 Bootstrap IC 95%% — 10 candidats par famille")
    log.info("Référence : [Efron1979] · Métrique principale : MCC [Chicco2020]")
    log.info(SEP)
    for b in branches:
        run_branch(b)
    log.info("✅ T13 terminé.")
    log.info("Commandes :")
    log.info("  Les deux    : docker compose run --rm api python scripts/t13_bootstrap_ci_candidates.py --branch both")
    log.info("  Santé seul  : docker compose run --rm api python scripts/t13_bootstrap_ci_candidates.py --branch sante")
    log.info("  Auto seul   : docker compose run --rm api python scripts/t13_bootstrap_ci_candidates.py --branch auto")

if __name__ == "__main__":
    main()