"""
MODULE : scripts/t10_4b_pyod_tier1.py
DESCRIPTION : Challengers Phase 2b — famille PyOD (Tier 1 & 2).
              ECOD, COPOD, HBOS, SUOD et Deep Isolation Forest, évalués sur
              les MÊMES splits immuables que T10.3/T10.4 — protocole ADR-006.
              Exécution résiliente : sauvegarde incrémentale + timeout par
              modèle (voir scripts/_ml_common.py).

RÉFÉRENCES ACADÉMIQUES :
- [Li2022] Li, Z. et al. (2022). ECOD: Unsupervised Outlier Detection Using
  Empirical Cumulative Distribution Functions. IEEE TKDE.
- [Li2020] Li, Z. et al. (2020). COPOD: Copula-Based Outlier Detection. ICDM.
- [Goldstein2012] Goldstein & Uchida (2012). Histogram-based Outlier Score.
- [Zhao2021] Zhao, Y. et al. (2021). SUOD. MLSys.
- [Xu2023] Xu, H. et al. (2023). Deep Isolation Forest. IEEE TKDE.

DÉCISIONS DE CONCEPTION :
- PyOD uniforme : tous exposent fit / decision_function / predict.
- HBOS : grid sur n_bins évalué sur le val set.
- ECOD / COPOD : hyperparameter-free, aucun tuning.
- Deep IF : seuil calibré sur val set (maximisation F1) plutôt que
  contamination — corrige le biais ultra-conservateur observé en premier run
  (FPR=0.003 Santé). [Xu2023] §4.3 : le seuil de décision est indépendant
  de la capacité discriminante (AUC).
- Aucun de ces modèles n'est compatible SHAP TreeExplainer → comparaison
  scientifique uniquement, IF classique reste le modèle de production.

USAGE :
  python scripts/t10_4b_pyod_tier1.py --branch sante
  python scripts/t10_4b_pyod_tier1.py --branch auto --timeout 600
  python scripts/t10_4b_pyod_tier1.py --branch sante --only ecod copod
  python scripts/t10_4b_pyod_tier1.py --branch auto --only dif
  python scripts/t10_4b_pyod_tier1.py --branch sante --skip dif
"""
from __future__ import annotations

import argparse
import time
from typing import Optional

import numpy as np

from _ml_common import (
    MODELS_DIR,
    RANDOM_STATE,
    apply_module,
    compute_metrics,
    get_xy,
    load_best_contamination,
    load_splits,
    log,
    print_summary,
    run_model_safe,
    setup_logging,
)

OUT_FILE = "t10_4b_pyod_results.json"
HBOS_NBINS_GRID = [5, 10, 20, 50]


def _import_pyod(module_path: str, cls_name: str):
    """Import PyOD défensif : renvoie la classe ou None (modèle skippé)."""
    try:
        mod = __import__(module_path, fromlist=[cls_name])
        return getattr(mod, cls_name)
    except ImportError as exc:
        log.warning("  PyOD indisponible (%s) : %s", module_path, exc)
        log.warning("  Installer via Docker : voir requirements.txt (pyod==1.1.3)")
        return None


def _persist(model: object, branch: str, key: str) -> None:
    import joblib
    out_dir = MODELS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_dir / f"{key}_model.joblib")
    log.info("  Modèle persisté : %s_model.joblib", key)


# ─── ECOD [Li2022] ───────────────────────────────────────────────────────────

def train_ecod(X_train, X_test, y_test, branch) -> Optional[dict]:
    ECOD = _import_pyod("pyod.models.ecod", "ECOD")
    if ECOD is None:
        return None
    model = ECOD()
    model.fit(X_train)
    scores = model.decision_function(X_test)
    y_pred = model.predict(X_test)
    metrics = compute_metrics(y_test, y_pred, scores)
    _persist(model, branch, "ecod")
    return {"algo": "ECOD", "metrics": metrics, "model_key": "ecod"}


# ─── COPOD [Li2020] ──────────────────────────────────────────────────────────

def train_copod(X_train, X_test, y_test, branch) -> Optional[dict]:
    COPOD = _import_pyod("pyod.models.copod", "COPOD")
    if COPOD is None:
        return None
    model = COPOD()
    model.fit(X_train)
    scores = model.decision_function(X_test)
    y_pred = model.predict(X_test)
    metrics = compute_metrics(y_test, y_pred, scores)
    _persist(model, branch, "copod")
    return {"algo": "COPOD", "metrics": metrics, "model_key": "copod"}


# ─── HBOS [Goldstein2012] — grid n_bins sur val ──────────────────────────────

def train_hbos(
    X_train, X_val, y_val, X_test, y_test, contamination, branch
) -> Optional[dict]:
    HBOS = _import_pyod("pyod.models.hbos", "HBOS")
    if HBOS is None:
        return None

    best_f1, best_bins, best_model = -1.0, 10, None
    grid_log = {}
    for n_bins in HBOS_NBINS_GRID:
        m = HBOS(n_bins=n_bins, alpha=0.1, tol=0.5, contamination=contamination)
        m.fit(X_train)
        if X_val is not None and y_val is not None:
            from sklearn.metrics import f1_score
            yv = m.predict(X_val)
            f1 = float(f1_score(y_val, yv, zero_division=0))
        else:
            f1 = 0.0
        grid_log[n_bins] = round(f1, 4)
        log.info("    n_bins=%2d → F1(val)=%.4f", n_bins, f1)
        if f1 > best_f1:
            best_f1, best_bins, best_model = f1, n_bins, m

    if best_model is None:
        best_model = HBOS(n_bins=10, alpha=0.1, tol=0.5, contamination=contamination)
        best_model.fit(X_train)
        best_bins = 10

    scores = best_model.decision_function(X_test)
    y_pred = best_model.predict(X_test)
    metrics = compute_metrics(y_test, y_pred, scores)
    metrics["n_bins"] = best_bins
    metrics["n_bins_grid"] = grid_log
    _persist(best_model, branch, "hbos")
    return {"algo": "HBOS", "metrics": metrics, "model_key": "hbos"}


# ─── SUOD [Zhao2021] — fusion IF + LOF + HBOS ────────────────────────────────

def train_suod(
    X_train, X_test, y_test, contamination, branch
) -> Optional[dict]:
    SUOD = _import_pyod("pyod.models.suod", "SUOD")
    IForest = _import_pyod("pyod.models.iforest", "IForest")
    LOF = _import_pyod("pyod.models.lof", "LOF")
    HBOS = _import_pyod("pyod.models.hbos", "HBOS")
    if None in (SUOD, IForest, LOF, HBOS):
        return None

    base = [
        IForest(n_estimators=200, contamination=contamination, random_state=RANDOM_STATE),
        LOF(n_neighbors=20, contamination=contamination),
        HBOS(n_bins=10, contamination=contamination),
    ]
    model = SUOD(
        base_estimators=base,
        contamination=contamination,
        combination="average",
        n_jobs=-1,
        verbose=False,
    )
    model.fit(X_train)
    scores = model.decision_function(X_test)
    y_pred = model.predict(X_test)
    metrics = compute_metrics(y_test, y_pred, scores)
    metrics["combination"] = "average"
    metrics["base_estimators"] = ["IForest", "LOF_k20", "HBOS"]
    _persist(model, branch, "suod")
    return {"algo": "SUOD", "metrics": metrics, "model_key": "suod"}


# ─── Deep Isolation Forest [Xu2023] — seuil calibré sur val ──────────────────

def train_dif(
    X_train,
    X_val,
    y_val,
    X_test,
    y_test,
    contamination,
    branch,
) -> Optional[dict]:
    """
    Deep IF avec calibration du seuil sur val set.

    Premier run : seuil par contamination → FPR=0.003 (ultra-conservateur).
    Cause : distribution des scores DIF très différente d'IF → le percentile
    (1-contamination) sur train correspond à un score extrême sur test.
    Solution [Xu2023 §4.3] : chercher le seuil qui maximise F1 sur val set,
    indépendamment de la contamination.
    """
    DIF = _import_pyod("pyod.models.dif", "DIF")
    if DIF is None:
        log.warning("  Deep IF requiert pyod + torch (voir requirements.txt).")
        return None
    try:
        import torch  # noqa: F401
    except ImportError:
        log.warning("  PyTorch absent — Deep IF skippé. Ajouter torch==2.2.2+cpu.")
        return None

    model = DIF(
        hidden_neurons=[64, 32],
        n_ensemble=50,
        n_estimators=6,
        max_samples=256,
        contamination=contamination,
        random_state=RANDOM_STATE,
        device="cpu",
    )
    model.fit(X_train)
    scores = model.decision_function(X_test)

    if X_val is not None and y_val is not None:
        # Calibration du seuil : maximiser F1 sur val set
        from sklearn.metrics import f1_score as _f1
        scores_val = model.decision_function(X_val)
        best_t = np.percentile(scores_val, 90)
        best_f1_val = 0.0
        for pct in np.arange(70, 99, 0.5):
            t = np.percentile(scores_val, pct)
            pred_v = (scores_val >= t).astype(int)
            f = float(_f1(y_val, pred_v, zero_division=0))
            if f > best_f1_val:
                best_f1_val, best_t = f, t
        y_pred = (scores >= best_t).astype(int)
        log.info(
            "  Deep IF seuil calibré sur val : percentile=%.1f%% "
            "→ F1(val)=%.4f | FPR(test)=%.4f",
            np.mean(scores_val < best_t) * 100,
            best_f1_val,
            float(np.mean((scores >= best_t)[y_test == 0])),
        )
    else:
        y_pred = model.predict(X_test)
        log.warning("  Deep IF : pas de val set — seuil par contamination (non calibré).")

    metrics = compute_metrics(y_test, y_pred, scores)
    metrics["n_ensemble"] = 50
    metrics["hidden_neurons"] = [64, 32]
    metrics["threshold_calibrated"] = X_val is not None
    _persist(model, branch, "dif")
    return {"algo": "DeepIsolationForest", "metrics": metrics, "model_key": "dif"}


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MAKORA T10.4b — Challengers PyOD (ECOD, COPOD, HBOS, SUOD, Deep IF)"
    )
    p.add_argument("--branch", choices=["sante", "auto"], required=True)
    p.add_argument("--timeout", type=int, default=0,
                   help="Budget temps PAR modèle en secondes (0 = illimité).")
    p.add_argument("--only", nargs="+", default=None,
                   choices=["ecod", "copod", "hbos", "suod", "dif"],
                   help="N'exécuter que ces modèles.")
    p.add_argument("--skip", nargs="+", default=[],
                   choices=["ecod", "copod", "hbos", "suod", "dif"],
                   help="Exclure ces modèles.")
    return p.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    branch = args.branch
    SEP = "─" * 60

    log.info(SEP)
    log.info("MAKORA — T10.4b Challengers PyOD [%s]", branch.upper())
    if args.timeout:
        log.info("Timeout par modèle : %ds", args.timeout)
    log.info(SEP)

    df_train, df_val, df_test = load_splits(branch, need_val=True)
    df_train, feats = apply_module(df_train, branch)
    df_val, _ = apply_module(df_val, branch) if df_val is not None else (None, feats)
    df_test, _ = apply_module(df_test, branch)

    X_train, _ = get_xy(df_train, feats)
    X_val, y_val = (get_xy(df_val, feats) if df_val is not None else (None, None))
    X_test, y_test = get_xy(df_test, feats)
    log.info("Matrice features : train=%s | test=%s", X_train.shape, X_test.shape)

    contamination = load_best_contamination(branch)

    runners = {
        "ecod": ("ECOD", lambda: train_ecod(X_train, X_test, y_test, branch)),
        "copod": ("COPOD", lambda: train_copod(X_train, X_test, y_test, branch)),
        "hbos": ("HBOS", lambda: train_hbos(
            X_train, X_val, y_val, X_test, y_test, contamination, branch)),
        "suod": ("SUOD", lambda: train_suod(
            X_train, X_test, y_test, contamination, branch)),
        "dif": ("DeepIsolationForest", lambda: train_dif(
            X_train, X_val, y_val, X_test, y_test, contamination, branch)),
    }

    selected = args.only or list(runners.keys())
    selected = [k for k in selected if k not in args.skip]

    results: list[dict] = [{"branch": branch, "features": feats,
                            "contamination": contamination}]
    t_start = time.perf_counter()
    try:
        for key in selected:
            name, fn = runners[key]
            run_model_safe(name, fn, results, branch, OUT_FILE, args.timeout)
    except KeyboardInterrupt:
        log.warning("Campagne interrompue manuellement — résultats partiels conservés.")

    log.info(SEP)
    log.info("T10.4b terminé en %.1fs — résultats : results/%s/%s",
             time.perf_counter() - t_start, branch, OUT_FILE)
    print_summary(results)


if __name__ == "__main__":
    main()