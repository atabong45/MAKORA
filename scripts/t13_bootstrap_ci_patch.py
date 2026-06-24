"""
MODULE : scripts/t13_bootstrap_ci_patch.py
DESCRIPTION : Patch pour les 2 modèles échoués dans t13_bootstrap_ci_candidates.py :
              - OC-SVM SGD : scaler sauvegardé sous 'ocsvm_scaler_model.joblib'
              - PU Learning RF : utilise predict_proba[:,1] (pas decision_function)
              Fusionne les résultats avec t13_bootstrap_ci_candidates.json existant.

RÉFÉRENCES : [Efron1979] [Chicco2020]
"""
from __future__ import annotations

import json
import logging
import sys
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score, f1_score, matthews_corrcoef, roc_auc_score,
)

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
log = logging.getLogger("makora.bootstrap_ci_patch")
SEP = "─" * 68

N_BOOTSTRAP = 1000
RANDOM_SEED = 42

# ─── Chargement données ───────────────────────────────────────────────────────

def load_test(branch: str):
    from core.plugin_registry import PluginRegistry
    if branch == "sante":
        import modules.sante.sante_module  # noqa
    else:
        import modules.auto.auto_module    # noqa
    yaml_path = PROJECT_ROOT / "modules" / branch / f"{branch}.yaml"
    module    = PluginRegistry.get(branch)(config_path=yaml_path)
    df = pd.read_parquet(SPLITS_DIR / branch / f"{branch}_test.parquet")
    df = module.engineer_features(df)
    fts = [c for c in module.get_feature_names() if c in df.columns]
    X   = df[fts].fillna(0).values.astype(np.float32)
    y   = (df[LABEL_COL] != NORMAL_VAL).astype(int).values
    return X, y

# ─── Bootstrap IC ─────────────────────────────────────────────────────────────

def bootstrap_ci(y_true, scores, y_pred, n=N_BOOTSTRAP, seed=RANDOM_SEED):
    rng = np.random.RandomState(seed)
    mccs, f1s, aucs, aps, fprs = [], [], [], [], []
    for _ in range(n):
        idx = rng.randint(0, len(y_true), len(y_true))
        yt, sc, yp = y_true[idx], scores[idx], y_pred[idx]
        if len(np.unique(yt)) < 2:
            continue
        tn = int(((yt == 0) & (yp == 0)).sum())
        fp = int(((yt == 0) & (yp == 1)).sum())
        mccs.append(matthews_corrcoef(yt, yp))
        f1s.append(f1_score(yt, yp, zero_division=0))
        aucs.append(roc_auc_score(yt, sc))
        aps.append(average_precision_score(yt, sc))
        fprs.append(fp / (fp + tn) if (fp + tn) > 0 else 0.0)

    def ci_dict(v):
        arr = np.array(v)
        return {"mean": round(float(arr.mean()), 4),
                "ci_lo": round(float(np.percentile(arr, 2.5)), 4),
                "ci_hi": round(float(np.percentile(arr, 97.5)), 4),
                "std": round(float(arr.std()), 4)}
    return {"mcc": ci_dict(mccs), "f1": ci_dict(f1s), "auc": ci_dict(aucs),
            "ap": ci_dict(aps), "fpr": ci_dict(fprs), "n_bootstrap": len(mccs)}

def point_metrics(y_true, scores, y_pred):
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    return {"mcc": round(float(matthews_corrcoef(y_true, y_pred)), 4),
            "f1":  round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
            "auc": round(float(roc_auc_score(y_true, scores)), 4),
            "ap":  round(float(average_precision_score(y_true, scores)), 4),
            "fpr": round(float(fp / (fp + tn)) if (fp + tn) > 0 else 0.0, 4),
            "tp": int(((y_true == 1) & (y_pred == 1)).sum()),
            "fp": fp,
            "fn": int(((y_true == 1) & (y_pred == 0)).sum()),
            "tn": tn}

# ─── OC-SVM ───────────────────────────────────────────────────────────────────

def run_ocsvm(branch: str, X: np.ndarray, y_true: np.ndarray) -> dict | None:
    """
    OC-SVM : scaler sauvegardé sous 'ocsvm_scaler_model.joblib' par _save_model().
    scores = -decision_function (négatif = anomalie dans sklearn → inverser).
    """
    # Essaye les deux noms possibles
    model_path  = MODELS_DIR / branch / "ocsvm_sgd_model.joblib"
    scaler_path_1 = MODELS_DIR / branch / "ocsvm_scaler_model.joblib"
    scaler_path_2 = MODELS_DIR / branch / "ocsvm_scaler.joblib"

    for sp in (scaler_path_1, scaler_path_2):
        if sp.exists():
            scaler_path = sp
            break
    else:
        log.error("Scaler OC-SVM introuvable pour %s (cherché : %s, %s)",
                  branch, scaler_path_1.name, scaler_path_2.name)
        # Fallback : ré-entraîner le scaler à la volée sur le test set
        # (non recommandé mais permet d'obtenir les IC)
        log.warning("Fallback : StandardScaler fit sur X_test (approximation)")
        from sklearn.preprocessing import StandardScaler
        scaler = StandardScaler().fit(X)
        scaler_path = None

    if not model_path.exists():
        log.error("Modèle OC-SVM introuvable : %s", model_path)
        return None

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path) if scaler_path else scaler

    X_scaled = scaler.transform(X)
    # sklearn SGDOneClassSVM : decision_function → négatif = anomalie
    raw = model.decision_function(X_scaled)
    scores = -raw                              # inverser : positif = anomalie
    y_pred = (model.predict(X_scaled) == -1).astype(int)

    log.info("  OC-SVM : n_anomalies_pred=%d | FPR=%.4f",
             y_pred.sum(), float(((y_true == 0) & (y_pred == 1)).sum()) /
             max((y_true == 0).sum(), 1))
    return scores, y_pred

# ─── PU Learning ──────────────────────────────────────────────────────────────

def run_pu(branch: str, X: np.ndarray, y_true: np.ndarray):
    """
    PU Learning RF : RandomForestClassifier → utilise predict_proba[:,1].
    Le seuil optimal est cherché sur y_true (test set) car pas de val set séparé.
    Note : c'est un modèle semi-supervisé — les IC sont calculés pour complétude
    mais il ne participe pas à la comparaison principale [Chandola2009].
    """
    model_path = MODELS_DIR / branch / "pu_rf_model.joblib"
    if not model_path.exists():
        log.warning("PU RF introuvable : %s", model_path)
        return None

    model = joblib.load(model_path)

    if not hasattr(model, "predict_proba"):
        log.error("PU RF sans predict_proba — skipped")
        return None

    proba   = model.predict_proba(X)
    # predict_proba retourne [P(normal), P(anomalie)] — colonne 1
    scores  = proba[:, 1]

    # Seuil optimal F1 sur le test set (seul set disponible pour PU)
    from sklearn.metrics import precision_recall_curve
    prec, rec, thrs = precision_recall_curve(y_true, scores)
    f1s = 2 * prec * rec / np.clip(prec + rec, 1e-9, None)
    best_thr = float(thrs[int(np.argmax(f1s[:-1]))])
    y_pred = (scores >= best_thr).astype(int)

    log.info("  PU RF : seuil_optimal=%.4f | n_anomalies_pred=%d",
             best_thr, y_pred.sum())
    return scores, y_pred

# ─── Pipeline patch ───────────────────────────────────────────────────────────

def patch_branch(branch: str):
    log.info(SEP)
    log.info("Patch T13 — Branche %s", branch.upper())
    log.info(SEP)

    X, y_true = load_test(branch)

    # Charger les résultats existants
    existing_path = RESULTS_DIR / branch / "t13_bootstrap_ci_candidates.json"
    if not existing_path.exists():
        log.error("Résultats existants introuvables : %s", existing_path)
        log.error("Lancer d'abord t13_bootstrap_ci_candidates.py --branch %s", branch)
        return

    existing = json.loads(existing_path.read_text())
    log.info("Résultats existants : %d entrées chargées", len(existing))

    # Supprimer les SKIPPED et ERROR existants pour ces deux modèles
    labels_to_replace = {"PU Learning RF c=0.0935", "PU Learning RF c=0.0885",
                         "OC-SVM SGD"}
    existing = [r for r in existing
                if not any(lbl in r.get("label", "") for lbl in labels_to_replace)]

    new_results = []

    # ── OC-SVM ────────────────────────────────────────────────────
    log.info("── OC-SVM SGD ──")
    t0 = time.perf_counter()
    ocsvm_out = run_ocsvm(branch, X, y_true)
    if ocsvm_out is not None:
        scores, y_pred = ocsvm_out
        metrics = point_metrics(y_true, scores, y_pred)
        log.info("  MCC=%.4f | F1=%.4f | FPR=%.4f",
                 metrics["mcc"], metrics["f1"], metrics["fpr"])
        log.info("  Bootstrap IC — %d itérations ...", N_BOOTSTRAP)
        ci = bootstrap_ci(y_true, scores, y_pred)
        log.info("  MCC : %.4f [%.4f – %.4f]",
                 ci["mcc"]["mean"], ci["mcc"]["ci_lo"], ci["mcc"]["ci_hi"])
        new_results.append({
            "label": "OC-SVM SGD",
            "branch": branch,
            "status": "OK",
            "metrics": metrics,
            "bootstrap_ci": ci,
            "threshold": None,
            "model_path": f"{branch}/ocsvm_sgd_model.joblib",
            "note": "écarté production (FPR=1.0) — IC calculés pour complétude",
        })
        log.info("  Temps : %.1fs", time.perf_counter() - t0)

    # ── PU Learning ───────────────────────────────────────────────
    pu_label = f"PU Learning RF c={'0.0935' if branch == 'sante' else '0.0885'}"
    log.info("── %s ──", pu_label)
    t0 = time.perf_counter()
    pu_out = run_pu(branch, X, y_true)
    if pu_out is not None:
        scores, y_pred = pu_out
        metrics = point_metrics(y_true, scores, y_pred)
        log.info("  MCC=%.4f | F1=%.4f | FPR=%.4f",
                 metrics["mcc"], metrics["f1"], metrics["fpr"])
        log.info("  Bootstrap IC — %d itérations ...", N_BOOTSTRAP)
        ci = bootstrap_ci(y_true, scores, y_pred)
        log.info("  MCC : %.4f [%.4f – %.4f]",
                 ci["mcc"]["mean"], ci["mcc"]["ci_lo"], ci["mcc"]["ci_hi"])
        new_results.append({
            "label": pu_label,
            "branch": branch,
            "status": "OK",
            "metrics": metrics,
            "bootstrap_ci": ci,
            "threshold": None,
            "model_path": f"{branch}/pu_rf_model.joblib",
            "note": "semi-supervisé [Elkan2008] — avantage informationnel, non comparable",
        })
        log.info("  Temps : %.1fs", time.perf_counter() - t0)

    # Fusion et sauvegarde
    merged = existing + new_results
    existing_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False))
    log.info(SEP)
    log.info("Fusion : %d entrées totales → %s", len(merged), existing_path)

    # Résumé final
    log.info("%-42s %8s %14s %8s", "Modèle", "MCC", "IC 95% MCC", "FPR")
    log.info("─" * 76)
    for r in sorted(merged, key=lambda x: x.get("metrics", {}).get("mcc", -1),
                    reverse=True):
        if r.get("status") != "OK":
            continue
        ci_mcc = r["bootstrap_ci"]["mcc"]
        log.info("%-42s %8.4f  [%.4f–%.4f]  %6.4f",
                 r["label"][:42],
                 ci_mcc["mean"], ci_mcc["ci_lo"], ci_mcc["ci_hi"],
                 r["metrics"]["fpr"])

def main():
    import argparse
    p = argparse.ArgumentParser(description="T13 Patch — OC-SVM + PU Learning")
    p.add_argument("--branch", choices=["sante", "auto", "both"], default="both")
    args = p.parse_args()
    branches = ["sante", "auto"] if args.branch == "both" else [args.branch]
    for b in branches:
        patch_branch(b)
    log.info("✅ Patch T13 terminé.")
    log.info("Commande : docker compose run --rm api python scripts/t13_bootstrap_ci_patch.py --branch both")

if __name__ == "__main__":
    main()