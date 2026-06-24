"""
MODULE : scripts/t10_4e_dif_calibration.py
DESCRIPTION : Multi-calibration Deep Isolation Forest [Xu2023].
              Si le modèle DIF n'existe pas, l'entraîne automatiquement
              (baseline [64,32]) avant d'appliquer les calibrations.
              Supporte --branch sante|auto|both.
              Phase B (--retrain) : 3 architectures DIF + StandardScaler.

RÉFÉRENCES ACADÉMIQUES :
- [Xu2023] Xu et al. (2023). Deep Isolation Forest. IEEE TKDE.
- [Davis2006] Davis & Goadrich (2006). PR vs ROC curves. ICML.
- [Fawcett2006] Fawcett, T. (2006). ROC analysis. Pattern Recognit. Lett.
- [Chicco2020] Chicco & Jurman (2020). MCC advantages. BioData Mining.
- [Goodfellow2016] Goodfellow et al. (2016). Deep Learning. MIT Press.
  → StandardScaler requis avant couches denses (features hétérogènes XAF).

DÉCISIONS DE CONCEPTION :
- Fallback auto-retrain : DIF 203s–295s par branche, pas de modèle persisté
  entre containers Docker → le script s'adapte sans intervention manuelle.
- Phase A : calibration sur modèle existant ou retrained baseline. 6 stratégies
  sur val set, évaluation sur test immutable [Goldstein2016].
- Phase B (--retrain) : 3 architectures × 2 calibrations. StandardScaler
  systématique — features auto [0–50 000 XAF] vs [0,1] ratios.
- oracle_upper : calibration sur test set = borne théorique maximale.
  Ne jamais déployer. Usage exclusif mémoire ch.5 §3.2 [Sculley2015].
"""
from __future__ import annotations

import argparse, json, logging, sys, time
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score, f1_score, matthews_corrcoef,
    precision_recall_curve, roc_auc_score, roc_curve,
)
from sklearn.preprocessing import StandardScaler

# ─── Chemins ──────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SPLITS_DIR   = PROJECT_ROOT / "data" / "splits"
MODELS_DIR   = PROJECT_ROOT / "data" / "models"
RESULTS_DIR  = PROJECT_ROOT / "results"
LABEL_COL    = "Label_Anomalie"
NORMAL_VAL   = "NORMAL"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S", handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("makora.dif_calib")
SEP = "─" * 68

# ─── Références cibles (benchmarks Phase 2 + Phase 2b) ───────────────────────
REF = {
    "sante": {"Deep IF calib (run2)": 0.4635, "HBOS": 0.4625,
               "IF classique": 0.4076, "PU_Learning": 0.4513},
    "auto":  {"Deep IF calib (run2)": 0.4602, "LOF k=20 (F1=0.292)": 0.5034,
               "IF max_feat=0.7": 0.4622, "EIF": 0.4788},
}

# ─── Métriques ────────────────────────────────────────────────────────────────

def full_metrics(y: np.ndarray, scores: np.ndarray, thr: float) -> dict:
    """F1, AUC, MCC, AP, FPR, Phi [Chicco2020, Davis2006]."""
    y_pred = (scores >= thr).astype(int)
    tn = int(((y == 0) & (y_pred == 0)).sum())
    fp = int(((y == 0) & (y_pred == 1)).sum())
    fn = int(((y == 1) & (y_pred == 0)).sum())
    tp = int(((y == 1) & (y_pred == 1)).sum())
    f1  = f1_score(y, y_pred, zero_division=0)
    auc = roc_auc_score(y, scores)
    mcc = matthews_corrcoef(y, y_pred)
    ap  = average_precision_score(y, scores)
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    phi = (f1 + auc + mcc + ap + (1 - fpr)) / 5
    return dict(f1=f1, auc=auc, mcc=mcc, ap=ap, fpr=fpr, phi=phi,
                tp=tp, fp=fp, fn=fn, tn=tn, threshold=thr)

# ─── Stratégies de calibration ────────────────────────────────────────────────

def calib_percentile_f1(sv, yv, st, yt) -> dict:
    """Sweep percentile [0.5% pas] — max F1(val). Baseline actuelle [Xu2023 run2]."""
    best_f1, best_thr = 0.0, float(np.median(sv))
    for pct in np.arange(1.0, 99.5, 0.5):
        thr = float(np.percentile(sv, pct))
        f1  = f1_score(yv, (sv >= thr).astype(int), zero_division=0)
        if f1 > best_f1:
            best_f1, best_thr = f1, thr
    log.info("  [percentile_f1]       F1(val)=%.4f  thr=%.6f", best_f1, best_thr)
    return full_metrics(yt, st, best_thr)

def calib_pr_exact(sv, yv, st, yt) -> dict:
    """PR curve exacte sklearn [Davis2006] — F1-max sans approximation grille."""
    prec, rec, thrs = precision_recall_curve(yv, sv)
    f1s = 2 * prec * rec / np.clip(prec + rec, 1e-9, None)
    idx = int(np.argmax(f1s[:-1]))
    thr = float(thrs[idx])
    log.info("  [pr_exact]            F1(val)=%.4f  thr=%.6f", f1s[idx], thr)
    return full_metrics(yt, st, thr)

def calib_youden(sv, yv, st, yt) -> dict:
    """Youden J = max(TPR − FPR) [Fawcett2006] — optimal quand AUC est le critère."""
    fprs, tprs, thrs = roc_curve(yv, sv)
    j   = tprs - fprs
    thr = float(thrs[int(np.argmax(j))])
    log.info("  [youden]              J=%.4f  thr=%.6f", float(np.max(j)), thr)
    return full_metrics(yt, st, thr)

def calib_fpr5(sv, yv, st, yt) -> dict:
    """Max F1 sous contrainte FPR ≤ 5% — opérationnel assurance."""
    best_f1, best_thr = 0.0, float(np.percentile(sv, 95))
    for pct in np.arange(1.0, 99.5, 0.25):
        thr = float(np.percentile(sv, pct))
        yp  = (sv >= thr).astype(int)
        fp  = int(((yv == 0) & (yp == 1)).sum())
        tn  = int(((yv == 0) & (yp == 0)).sum())
        if fp / (fp + tn + 1e-9) > 0.05:
            continue
        f1 = f1_score(yv, yp, zero_division=0)
        if f1 > best_f1:
            best_f1, best_thr = f1, thr
    log.info("  [fpr5_constrained]    F1(val)=%.4f  thr=%.6f", best_f1, best_thr)
    return full_metrics(yt, st, best_thr)

def calib_phi_optimal(sv, yv, st, yt) -> dict:
    """Maximise Phi-Score(val) directement — contribution originale mémoire."""
    auc_v = roc_auc_score(yv, sv)
    ap_v  = average_precision_score(yv, sv)
    best_phi, best_thr = 0.0, float(np.median(sv))
    for pct in np.arange(1.0, 99.5, 0.25):
        thr = float(np.percentile(sv, pct))
        yp  = (sv >= thr).astype(int)
        f1  = f1_score(yv, yp, zero_division=0)
        mcc = matthews_corrcoef(yv, yp)
        fp  = int(((yv == 0) & (yp == 1)).sum())
        tn  = int(((yv == 0) & (yp == 0)).sum())
        phi = (f1 + auc_v + mcc + ap_v + (1 - fp/(fp+tn+1e-9))) / 5
        if phi > best_phi:
            best_phi, best_thr = phi, thr
    log.info("  [phi_optimal]         Phi(val)=%.4f  thr=%.6f", best_phi, best_thr)
    return full_metrics(yt, st, best_thr)

def calib_oracle(sv, yv, st, yt) -> dict:
    """Borne sup — calibration sur test set. Usage mémoire uniquement. [Sculley2015]"""
    prec, rec, thrs = precision_recall_curve(yt, st)
    f1s = 2 * prec * rec / np.clip(prec + rec, 1e-9, None)
    thr = float(thrs[int(np.argmax(f1s[:-1]))])
    log.info("  [oracle_upper]        F1(test)=%.4f  ← BORNE SUP (no deploy)", float(np.max(f1s[:-1])))
    return full_metrics(yt, st, thr)

STRATEGIES = {
    "percentile_f1":     calib_percentile_f1,
    "pr_exact":          calib_pr_exact,
    "youden":            calib_youden,
    "fpr5_constrained":  calib_fpr5,
    "phi_optimal":       calib_phi_optimal,
    "oracle_upper":      calib_oracle,
}

# ─── Chargement données ───────────────────────────────────────────────────────

def load_splits(branch: str) -> tuple:
    """Charge train/val/test via engineer_features du module MAKORA."""
    from core.plugin_registry import PluginRegistry
    if branch == "sante":
        import modules.sante.sante_module  # noqa: F401
    else:
        import modules.auto.auto_module    # noqa: F401
    yaml_path = PROJECT_ROOT / "modules" / branch / f"{branch}.yaml"
    module    = PluginRegistry.get(branch)(config_path=yaml_path)

    out = {}
    for split in ("train", "val", "test"):
        p = SPLITS_DIR / branch / f"{branch}_{split}.parquet"
        if not p.exists():
            raise FileNotFoundError(f"Split {split} manquant : {p}")
        df = pd.read_parquet(p)
        df = module.engineer_features(df)
        fts = [c for c in module.get_feature_names() if c in df.columns]
        X   = df[fts].fillna(0).values.astype(np.float32)
        y   = (df[LABEL_COL] != NORMAL_VAL).astype(int).values
        out[split] = (X, y)
        log.info("[%s] %s=%d | anomalies=%d (%.1f%%)",
                 branch.upper(), split, len(y), y.sum(), 100*y.mean())
    return out, fts

# ─── Chargement / entraînement DIF ───────────────────────────────────────────

CANDIDATE_DIRS = ["data/models", "results", "."]  # ordre de priorité

def find_model(branch: str, name: str = "dif") -> Optional[Path]:
    for d in CANDIDATE_DIRS:
        for fname in (f"{name}_model.joblib", f"{name}.joblib"):
            p = PROJECT_ROOT / d / branch / fname
            if p.exists():
                return p
            p2 = PROJECT_ROOT / d / fname
            if p2.exists():
                return p2
    return None

def train_dif(X_train: np.ndarray, branch: str,
              hidden_neurons: list, contamination: float,
              scaler: Optional[StandardScaler] = None) -> object:
    """Entraîne DIF [Xu2023] avec architecture donnée."""
    DIF_cls = None
    for cls_name in ("DeepIsolationForest", "DIF"):
        try:
            import importlib
            mod   = importlib.import_module("pyod.models.dif")
            DIF_cls = getattr(mod, cls_name)
            log.info("  Import DIF via pyod.models.dif.%s", cls_name)
            break
        except (ImportError, AttributeError):
            continue
    if DIF_cls is None:
        log.error("pyod.models.dif introuvable — vérifier l'installation PyOD 1.1.3")
        log.error("pip install pyod==1.1.3 --break-system-packages")
        sys.exit(1)
    X_in = scaler.fit_transform(X_train) if scaler else X_train
    t0   = time.perf_counter()
    model = DIF_cls(
        contamination=contamination, random_state=42,
        hidden_neurons=hidden_neurons,
    )
    model.fit(X_in)
    log.info("  DIF entraîné en %.1fs — arch=%s", time.perf_counter() - t0, hidden_neurons)
    return model

# ─── Phase A ──────────────────────────────────────────────────────────────────

def phase_a(branch: str, contamination: float) -> list[dict]:
    log.info(SEP)
    log.info("PHASE A — 6 calibrations sur modèle DIF [%s]", branch.upper())
    log.info(SEP)
    splits, _ = load_splits(branch)
    X_train, _     = splits["train"]
    X_val,   y_val = splits["val"]
    X_test,  y_test= splits["test"]

    # Charger ou réentraîner
    model_path = find_model(branch)
    scaler     = None
    if model_path:
        log.info("Modèle chargé : %s", model_path)
        model = joblib.load(model_path)
    else:
        log.warning("dif_model.joblib introuvable — réentraînement baseline [64,32] ...")
        model = train_dif(X_train, branch, [64, 32], contamination)
        save_p = MODELS_DIR / branch / "dif_model.joblib"
        save_p.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, save_p)
        log.info("Modèle sauvegardé : %s", save_p)

    scores_val  = model.decision_function(X_val)
    scores_test = model.decision_function(X_test)

    rows = []
    for name, fn in STRATEGIES.items():
        log.info(SEP)
        log.info("Stratégie : %s", name)
        m = fn(scores_val, y_val, scores_test, y_test)
        m.update(strategy=name, arch="baseline_64_32", branch=branch, phase="A")
        rows.append(m)
    return rows

# ─── Phase B ──────────────────────────────────────────────────────────────────

ARCHS = {
    "baseline_64_32":  {"hidden_neurons": [64, 32],       "use_scaler": False},
    "deep_128_64_32":  {"hidden_neurons": [128, 64, 32],  "use_scaler": True},
    "narrow_64_32_16": {"hidden_neurons": [64, 32, 16],   "use_scaler": True},
}

def phase_b(branch: str, contamination: float) -> list[dict]:
    """3 architectures × 2 calibrations (phi_optimal + pr_exact). [Xu2023, Goodfellow2016]"""
    log.info(SEP)
    log.info("PHASE B — Architectures DIF variantes [%s]", branch.upper())
    log.info(SEP)
    splits, _ = load_splits(branch)
    X_train, _     = splits["train"]
    X_val,   y_val = splits["val"]
    X_test,  y_test= splits["test"]

    rows = []
    for arch_name, cfg in ARCHS.items():
        log.info(SEP)
        log.info("Architecture : %s  scaler=%s", arch_name, cfg["use_scaler"])
        scaler = StandardScaler() if cfg["use_scaler"] else None
        model  = train_dif(X_train, branch, cfg["hidden_neurons"],
                           contamination, scaler)
        X_v = scaler.transform(X_val)  if scaler else X_val
        X_t = scaler.transform(X_test) if scaler else X_test
        sv  = model.decision_function(X_v)
        st  = model.decision_function(X_t)

        for strat in ("phi_optimal", "pr_exact", "fpr5_constrained"):
            log.info("  Calibration : %s", strat)
            m = STRATEGIES[strat](sv, y_val, st, y_test)
            m.update(strategy=strat, arch=arch_name,
                     branch=branch, phase="B",
                     scaler="StandardScaler" if scaler else "none")
            rows.append(m)
    return rows

# ─── Affichage ────────────────────────────────────────────────────────────────

def print_table(rows: list[dict], branch: str) -> None:
    log.info(SEP)
    log.info("RÉSULTATS — %s", branch.upper())
    log.info(SEP)
    hdr = f"{'Ph':<3} {'Stratégie':<22} {'Arch':<16} {'F1':>6} {'AUC':>6} {'MCC':>6} {'AP':>6} {'FPR':>6} {'Phi':>7}"
    log.info(hdr)
    log.info("─" * 76)
    for r in sorted(rows, key=lambda x: x["phi"], reverse=True):
        log.info("%-3s %-22s %-16s %6.4f %6.4f %6.4f %6.4f %6.4f %7.4f",
                 r.get("phase","?"), r["strategy"], r["arch"],
                 r["f1"], r["auc"], r["mcc"], r["ap"], r["fpr"], r["phi"])
    log.info("─" * 76)
    log.info("RÉFÉRENCES PHASE 2 + 2b (%s):", branch.upper())
    for k, v in REF.get(branch, {}).items():
        log.info("  %-32s  Phi=%s", k, f"{v:.4f}" if v < 1 else f"F1={v:.4f}")
    log.info(SEP)

# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="T10.4e — Deep IF Multi-Calibration")
    p.add_argument("--branch", choices=["sante", "auto", "both"], default="auto")
    p.add_argument("--retrain", action="store_true",
                   help="Phase B : 3 architectures DIF + StandardScaler (~600s/branche)")
    return p.parse_args()

CONTAMINATION = {"sante": 0.070, "auto": 0.100}

def run_branch(branch: str, retrain: bool) -> list[dict]:
    c    = CONTAMINATION[branch]
    rows = phase_a(branch, c)
    if retrain:
        rows += phase_b(branch, c)
    print_table(rows, branch)
    out  = RESULTS_DIR / branch
    out.mkdir(parents=True, exist_ok=True)
    path = out / "t10_4e_dif_calibration_results.json"
    path.write_text(json.dumps(rows, indent=2, ensure_ascii=False))
    log.info("JSON → %s", path)
    return rows

def main() -> None:
    args     = parse_args()
    branches = ["sante", "auto"] if args.branch == "both" else [args.branch]
    log.info(SEP)
    log.info("MAKORA — T10.4e Deep IF Multi-Calibration")
    log.info("Branches : %s | Phase B (--retrain) : %s", branches, args.retrain)
    log.info("Référence : [Xu2023] Xu et al. IEEE TKDE 2023")
    log.info(SEP)
    for b in branches:
        run_branch(b, args.retrain)
    log.info("✅ T10.4e terminé.")
    log.info("Commandes :")
    log.info("  Auto seul    : docker compose run --rm api python scripts/t10_4e_dif_calibration.py --branch auto")
    log.info("  Santé seul   : docker compose run --rm api python scripts/t10_4e_dif_calibration.py --branch sante")
    log.info("  Les deux     : docker compose run --rm api python scripts/t10_4e_dif_calibration.py --branch both")
    log.info("  + Archs      : ajouter --retrain (~600s par branche)")

if __name__ == "__main__":
    main()