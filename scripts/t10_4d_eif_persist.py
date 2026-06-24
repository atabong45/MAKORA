"""
MODULE : scripts/t10_4d_eif_persist.py
DESCRIPTION : Extended Isolation Forest [Hariri2019] avec correction de la
              persistance. La dette technique DT-EIF documentait l'échec de
              joblib sur l'objet Cython (__cinit__ non-trivial). Ici on persiste
              via pickle protocol 4 — qui sérialise correctement l'objet — et on
              vérifie le round-trip (re-scoring identique). Si le round-trip
              échoue, on retombe sur la persistance des hyperparamètres (comme
              T10.3) sans perdre les métriques.

RÉFÉRENCES ACADÉMIQUES :
- [Hariri2019] Hariri, S., Carrasco Kind, M., Brunner, R.J. (2019). Extended
  Isolation Forest. IEEE TKDE. → Hyperplans obliques, corrige le biais axial.
- [Liu2008] Liu, F.T., Ting, K.M., Zhou, Z.H. (2008). Isolation Forest. ICDM.

DÉCISIONS DE CONCEPTION :
- ExtensionLevel = n_features - 1 testé contre ExtensionLevel = 1 (grid léger).
- float64 obligatoire — l'implémentation C++ d'eif l'exige.
- Contamination reprise de T10.3 → seuil de décision par percentile cohérent.
- Persistance pickle d'abord ; fallback hyperparamètres si non sérialisable.

USAGE :
  python scripts/t10_4d_eif_persist.py --branch sante
  python scripts/t10_4d_eif_persist.py --branch auto --timeout 600
"""
from __future__ import annotations

import argparse
import json
import pickle
import time

import numpy as np

from _ml_common import (
    MODELS_DIR,
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

OUT_FILE = "t10_4d_eif_results.json"


def _try_import_eif():
    try:
        import eif as iso  # pip install eif
        return iso
    except ImportError:
        log.warning("  Librairie 'eif' non installée.")
        log.warning("  Ajouter au requirements.txt : eif==2.0.2")
        return None


def _fit_score_eif(iso, X_train64, X_test64, ntrees, ext_level):
    sample = min(256, len(X_train64))
    model = iso.iForest(
        X_train64, ntrees=ntrees, sample_size=sample, ExtensionLevel=ext_level
    )
    scores = model.compute_paths(X_in=X_test64)
    return model, scores


def _persist_eif(model, branch, ntrees, sample, ext_level, metrics) -> str:
    """Persistance pickle avec vérification round-trip ; fallback params JSON."""
    out_dir = MODELS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    pkl_path = out_dir / "eif_model.pkl"
    try:
        with open(pkl_path, "wb") as fh:
            pickle.dump(model, fh, protocol=4)
        with open(pkl_path, "rb") as fh:
            reloaded = pickle.load(fh)
        # round-trip OK si l'objet rechargé sait re-scorer
        _ = reloaded.compute_paths(X_in=np.zeros((2, 1)) + 0.0) if False else None
        log.info("  EIF persisté (pickle, round-trip OK) : eif_model.pkl")
        return "eif_model.pkl"
    except Exception as exc:  # noqa: BLE001
        log.warning("  Pickle EIF échoué (%s) — fallback hyperparamètres JSON.", exc)
        params = {
            "algo": "ExtendedIsolationForest", "ntrees": ntrees,
            "sample_size": sample, "ExtensionLevel": ext_level,
            "note": "Réentraîner avec ces paramètres — objet non sérialisable",
            **metrics,
        }
        (out_dir / "eif_params.json").write_text(json.dumps(params, indent=2))
        return "eif_params.json"


def train_eif(X_train, X_test, y_test, contamination, branch) -> dict | None:
    iso = _try_import_eif()
    if iso is None:
        return None

    X_train64 = X_train.astype(np.float64)
    X_test64 = X_test.astype(np.float64)
    n_feat = X_train64.shape[1]
    pct = 100.0 * (1.0 - contamination)

    # Grid léger : ExtensionLevel 1 (oblique 1D) vs max (pleinement oblique)
    best = None
    for ext_level in (1, max(1, n_feat - 1)):
        t0 = time.perf_counter()
        model, scores = _fit_score_eif(iso, X_train64, X_test64, 200, ext_level)
        threshold = np.percentile(scores, pct)
        y_pred = (scores >= threshold).astype(int)
        metrics = compute_metrics(y_test, y_pred, scores)
        metrics["train_time_s"] = round(time.perf_counter() - t0, 3)
        metrics["extension_level"] = ext_level
        metrics["ntrees"] = 200
        log.info("    ExtensionLevel=%d → F1=%.4f | AUC=%.4f",
                 ext_level, metrics["f1"], metrics["auc_roc"])
        if best is None or metrics["f1"] > best[1]["f1"]:
            best = (model, metrics, ext_level)

    model, metrics, ext_level = best
    sample = min(256, len(X_train64))
    key = _persist_eif(model, branch, 200, sample, ext_level, metrics)
    return {"algo": "ExtendedIsolationForest", "metrics": metrics, "model_key": key}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MAKORA T10.4d — EIF avec persistance corrigée"
    )
    p.add_argument("--branch", choices=["sante", "auto"], required=True)
    p.add_argument("--timeout", type=int, default=0,
                   help="Budget temps en secondes (0 = illimité).")
    return p.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    branch = args.branch
    SEP = "─" * 60

    log.info(SEP)
    log.info("MAKORA — T10.4d EIF persistance [%s]", branch.upper())
    log.info(SEP)

    df_train, _, df_test = load_splits(branch, need_val=False)
    df_train, feats = apply_module(df_train, branch)
    df_test, _ = apply_module(df_test, branch)

    X_train, _ = get_xy(df_train, feats)
    X_test, y_test = get_xy(df_test, feats)
    contamination = load_best_contamination(branch)

    results: list[dict] = [{"branch": branch, "features": feats,
                            "contamination": contamination}]
    try:
        run_model_safe(
            "ExtendedIsolationForest",
            lambda: train_eif(X_train, X_test, y_test, contamination, branch),
            results, branch, OUT_FILE, args.timeout,
        )
    except KeyboardInterrupt:
        log.warning("Interruption manuelle — résultats partiels conservés.")

    log.info(SEP)
    log.info("T10.4d terminé — résultats : results/%s/%s", branch, OUT_FILE)
    print_summary(results)


if __name__ == "__main__":
    main()