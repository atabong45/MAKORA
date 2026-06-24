"""
MODULE : scripts/t10_7_evaluation.py
DESCRIPTION : Évaluation finale et tableau comparatif des 6 algorithmes.
              PR/ROC curves, calibration seuil, McNemar, bootstrap IC.

RÉFÉRENCES ACADÉMIQUES :
- [Davis2006] Davis & Goadrich (2006). The relationship between Precision-Recall
  and ROC curves. ICML. → PR curve = référence principale sur données
  déséquilibrées. ROC surestime les performances quand les négatifs >> positifs.
- [Efron1979] Efron, B. (1979). Bootstrap methods: another look at the
  jackknife. Annals of Statistics. → 1000 itérations bootstrap → IC 95%.
- [McNemar1947] McNemar, Q. (1947). Note on the sampling error of the
  difference between correlated proportions. Psychometrika. → Test de
  significativité entre deux classifieurs sur les mêmes données.
- [Chicco2020] Chicco & Jurman (2020). The advantages of the Matthews
  correlation coefficient (MCC). BioData Mining. → MCC = meilleure
  métrique unique sur classes déséquilibrées (vs F1 et accuracy).
- [Goldstein2016] Goldstein & Uchida (2016). Comparative evaluation of
  unsupervised anomaly detection algorithms. PLOS ONE. → Protocole ADR-006.

DÉCISIONS DE CONCEPTION :
- Seuil optimal calibré sur Precision-Recall (F1 max) — pas sur ROC.
  [Davis2006] : PR curve est la référence primaire pour la fraude.
- Bootstrap 1000 itérations sur le test set (avec replacement) [Efron1979].
- Test McNemar entre IF classique et chaque challenger [McNemar1947].
- PCA 2D ajoutée pour la figure de visualisation clusters (→ mémoire ch.5).
- Tableau comparatif final : 6 algos × 8 métriques + IC + temps.
- Métriques secondaires obligatoires : MCC [Chicco2020] + FPR.

USAGE :
  python scripts/t10_7_evaluation.py --branch sante
  python scripts/t10_7_evaluation.py --branch auto --no-plot
"""

from __future__ import annotations
import sys

import argparse
import json
import logging
from pathlib import Path

import sys
import joblib
import numpy as np
import pandas as pd

# Ajoute PROJECT_ROOT au path avant tout import MAKORA
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    matthews_corrcoef,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
    roc_curve,
)
from sklearn.decomposition import PCA
from statsmodels.stats.contingency_tables import mcnemar

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("makora.t10_7")

PROJECT_ROOT  = Path(__file__).resolve().parent.parent
SPLITS_DIR    = PROJECT_ROOT / "data" / "splits"
MODELS_DIR    = PROJECT_ROOT / "data" / "models"
RESULTS_DIR   = PROJECT_ROOT / "results"
FIGURES_DIR   = PROJECT_ROOT / "results" / "figures"

RANDOM_STATE  = 42
LABEL_COL     = "Label_Anomalie"
NORMAL_VAL    = "NORMAL"
BOOTSTRAP_N   = 1000    # [Efron1979] : 1000 itérations pour IC 95%
CI_ALPHA      = 0.95

META_COLS = {
    "Label_Anomalie", "Sous_Type_Anomalie", "Cause_Racine_RCA",
    "Severite_Anomalie", "Source_Detection", "Validee_Par_Auditeur",
    "Date_Validation", "Commentaire_Audit", "Montant_Prejudice",
    "ID_Sinistre", "ID_Assure", "ID_Praticien", "ID_Vehicule",
    "ID_Contrat", "ID_Expert", "ID_Garage", "Hash_Image", "Batch_Date",
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_test_split(branch: str) -> pd.DataFrame:
    path = SPLITS_DIR / branch / f"{branch}_test.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Split test introuvable : {path}")
    return pd.read_parquet(path)

def get_feature_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    feature_cols = [
        c for c in df.columns
        if c not in META_COLS and pd.api.types.is_numeric_dtype(df[c])
    ]
    X = df[feature_cols].fillna(0).values.astype(np.float32)
    y = (df[LABEL_COL] != NORMAL_VAL).astype(int).values
    return X, y, feature_cols

def load_all_models(branch: str) -> dict[str, object]:
    """Charge tous les modèles produits par T10.3 et T10.4."""
    model_map: dict[str, tuple[str, bool]] = {
        "IsolationForest":        ("if_classic_model.joblib",      False),
        "IF_maxfeat07":           ("if_maxfeatures07_model.joblib", False),
        "LOF_k20":                ("lof_k20_model.joblib",          False),
        "SGDOneClassSVM":         ("ocsvm_sgd_model.joblib",        True),
        "HBOS":                   ("hbos_model.joblib",             False),
    }
    models: dict[str, object] = {}
    for name, (fname, _) in model_map.items():
        path = MODELS_DIR / branch / fname
        if path.exists():
            models[name] = joblib.load(path)
            log.info("  ✅ Chargé : %s", name)
        else:
            log.warning("  ⚠️ Non trouvé : %s (%s)", name, fname)
    return models

def score_model(
    name: str, model: object, X: np.ndarray,
    scaler=None, contamination: float = 0.08,
) -> tuple[np.ndarray, np.ndarray]:
    """Retourne (scores, y_pred) pour n'importe quel modèle chargé."""
    X_in = scaler.transform(X) if scaler else X
    try:
        if hasattr(model, "decision_function"):
            raw   = model.decision_function(X_in)
            pred  = model.predict(X_in)
            scores = -raw  # IF/LOF/OC-SVM : négatif = anomalie → inverser
            y_pred = (pred == -1).astype(int)
        else:
            # PyOD models (HBOS)
            scores = model.decision_function(X_in)
            y_pred = model.predict(X_in)           # 0/1 directement
    except Exception as exc:
        log.error("Erreur scoring %s : %s", name, exc)
        scores = np.zeros(len(X))
        y_pred = np.zeros(len(X), dtype=int)
    return scores, y_pred

# ─── Bootstrap IC ────────────────────────────────────────────────────────────

def bootstrap_ci(
    y_true: np.ndarray, scores: np.ndarray, threshold: float,
    n_iter: int = BOOTSTRAP_N, alpha: float = CI_ALPHA,
) -> dict[str, dict]:
    """
    IC bootstrap [Efron1979] sur F1, AUC, MCC.
    1000 itérations — rééchantillonnage avec remise sur le test set.
    """
    rng = np.random.default_rng(RANDOM_STATE)
    f1_b, auc_b, mcc_b = [], [], []

    for _ in range(n_iter):
        idx = rng.choice(len(y_true), size=len(y_true), replace=True)
        yt  = y_true[idx]
        sc  = scores[idx]
        yp  = (sc >= threshold).astype(int)
        if len(np.unique(yt)) < 2:
            continue
        f1_b.append(f1_score(yt, yp, zero_division=0))
        auc_b.append(roc_auc_score(yt, sc))
        mcc_b.append(matthews_corrcoef(yt, yp))

    lo = (1 - alpha) / 2
    hi = 1 - lo

    def _ci(arr: list[float]) -> dict:
        a = np.array(arr)
        return {
            "mean": round(float(np.mean(a)), 4),
            "ci_lo": round(float(np.percentile(a, lo * 100)), 4),
            "ci_hi": round(float(np.percentile(a, hi * 100)), 4),
        }

    return {"f1": _ci(f1_b), "auc": _ci(auc_b), "mcc": _ci(mcc_b)}

# ─── Métriques complètes ─────────────────────────────────────────────────────

def full_metrics(
    y_true: np.ndarray, scores: np.ndarray, threshold: float,
) -> dict:
    """
    Calcule les 8 métriques MAKORA [Goldstein2016, Chicco2020, Davis2006].
    """
    y_pred = (scores >= threshold).astype(int)
    tn = int(((y_true == 0) & (y_pred == 0)).sum())
    fp = int(((y_true == 0) & (y_pred == 1)).sum())
    fn = int(((y_true == 1) & (y_pred == 0)).sum())
    tp = int(((y_true == 1) & (y_pred == 1)).sum())
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return {
        "threshold": round(float(threshold), 6),
        "f1":        round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall":    round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "auc_roc":   round(float(roc_auc_score(y_true, scores)), 4),
        "avg_prec":  round(float(average_precision_score(y_true, scores)), 4),
        "mcc":       round(float(matthews_corrcoef(y_true, y_pred)), 4),
        "fpr":       round(float(fpr), 4),
        "tp": tp, "fp": fp, "tn": tn, "fn": fn,
    }

def optimal_threshold_pr(y_true: np.ndarray, scores: np.ndarray) -> float:
    """
    Seuil optimal par maximisation du F1 sur la courbe PR [Davis2006].
    Préféré à ROC sur données déséquilibrées.
    """
    prec, rec, thresholds = precision_recall_curve(y_true, scores)
    f1s = 2 * prec * rec / (prec + rec + 1e-9)
    best_idx = int(np.argmax(f1s[:-1]))
    return float(thresholds[best_idx])

# ─── McNemar ─────────────────────────────────────────────────────────────────

def mcnemar_test(
    y_true: np.ndarray,
    y_pred_ref: np.ndarray,
    y_pred_chal: np.ndarray,
    name_ref: str, name_chal: str,
) -> dict:
    """
    Test de McNemar [McNemar1947] entre IF classique et un challenger.
    H0 : les deux classifieurs ont les mêmes erreurs.
    p < 0.05 → différence significative.
    """
    b = int(((y_pred_ref == 1) & (y_pred_chal == 0)).sum())
    c = int(((y_pred_ref == 0) & (y_pred_chal == 1)).sum())
    table = [[0, b], [c, 0]]
    try:
        result = mcnemar(table, exact=True)
        pval = float(result.pvalue)
    except Exception:
        pval = float("nan")

    return {
        "ref": name_ref, "challenger": name_chal,
        "b": b, "c": c,
        "pvalue": round(pval, 6),
        "significant": pval < 0.05 if not np.isnan(pval) else None,
    }

# ─── PCA 2D ──────────────────────────────────────────────────────────────────

def plot_pca_clusters(
    X_test: np.ndarray, y_true: np.ndarray, y_pred: np.ndarray, branch: str,
) -> None:
    """PCA 2D — figure clusters fraude/normal pour le mémoire (ch. 5)."""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        pca    = PCA(n_components=2, random_state=RANDOM_STATE)
        X_2d   = pca.fit_transform(X_test)
        var_ex = pca.explained_variance_ratio_

        fig, ax = plt.subplots(figsize=(9, 7))
        # Normaux non détectés
        ax.scatter(X_2d[(y_true==0)&(y_pred==0), 0],
                   X_2d[(y_true==0)&(y_pred==0), 1],
                   s=5, alpha=0.3, color="#AED6F1", label="Normal (TN)")
        # Vrais positifs
        ax.scatter(X_2d[(y_true==1)&(y_pred==1), 0],
                   X_2d[(y_true==1)&(y_pred==1), 1],
                   s=15, alpha=0.7, color="#E74C3C", label="Fraude détectée (TP)")
        # Faux positifs
        ax.scatter(X_2d[(y_true==0)&(y_pred==1), 0],
                   X_2d[(y_true==0)&(y_pred==1), 1],
                   s=10, alpha=0.5, color="#F39C12", label="Faux positif (FP)", marker="^")
        # Faux négatifs
        ax.scatter(X_2d[(y_true==1)&(y_pred==0), 0],
                   X_2d[(y_true==1)&(y_pred==0), 1],
                   s=10, alpha=0.5, color="#884EA0", label="Faux négatif (FN)", marker="x")

        ax.set_xlabel(f"PC1 ({var_ex[0]*100:.1f}% variance)", fontsize=11)
        ax.set_ylabel(f"PC2 ({var_ex[1]*100:.1f}% variance)", fontsize=11)
        ax.set_title(
            f"PCA 2D — Isolation Forest [{branch.upper()}]\n"
            "Visualisation clusters Fraude vs Normal",
            fontsize=13,
        )
        ax.legend(fontsize=10, markerscale=2)
        ax.grid(True, linestyle="--", alpha=0.4)
        out_path = FIGURES_DIR / f"t10_7_pca_clusters_{branch}.png"
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        log.info("Figure PCA 2D : %s", out_path)
    except ImportError:
        log.warning("matplotlib non installé — PCA figure ignorée.")

# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MAKORA T10.7 — Évaluation finale + tableau comparatif"
    )
    p.add_argument("--branch",  choices=["sante", "auto"], required=True)
    p.add_argument("--no-plot", action="store_true")
    return p.parse_args()

def main() -> None:
    args   = parse_args()
    branch = args.branch
    SEP    = "─" * 60

    log.info(SEP)
    log.info("MAKORA — T10.7 Évaluation finale [%s]", branch.upper())
    log.info(SEP)

    df_test_raw          = load_test_split(branch)
    models               = load_all_models(branch)

    # engineer_features via module MAKORA
    from core.plugin_registry import PluginRegistry
    if branch == "sante":
        import modules.sante.sante_module  # noqa: F401
    elif branch == "auto":
        import modules.auto.auto_module    # noqa: F401
    yaml_path    = PROJECT_ROOT / "modules" / branch / f"{branch}.yaml"
    module_inst  = PluginRegistry.get(branch)(config_path=yaml_path)
    df_test      = module_inst.engineer_features(df_test_raw)
    feat_names   = [f for f in module_inst.get_feature_names() if f in df_test.columns]
    X_test       = df_test[feat_names].fillna(0).values.astype(np.float32)
    y_test       = (df_test[LABEL_COL] != NORMAL_VAL).to_numpy(dtype=int)

    # Scaler OC-SVM (sauvegardé séparément par T10.4)
    scaler_path = MODELS_DIR / branch / "ocsvm_scaler_model.joblib"
    ocsvm_scaler = joblib.load(scaler_path) if scaler_path.exists() else None

    comparative: list[dict] = []
    ref_pred: np.ndarray | None = None

    # Charger métriques EIF depuis T10.3 (modèle non persisté — Cython/joblib incompatible)
    t10_3_path = RESULTS_DIR / branch / "t10_3_if_results.json"
    eif_entry = None
    if t10_3_path.exists():
        t10_3_data = json.loads(t10_3_path.read_text())
        eif_entry = next((e for e in t10_3_data if e.get("algo") == "ExtendedIsolationForest"), None)
    if eif_entry:
        log.info("── ExtendedIsolationForest (métriques T10.3, modèle non persisté) ──")
        eif_m = eif_entry["metrics"]
        log.info("  F1=%.4f | AUC=%.4f | P=%.4f | R=%.4f",
                 eif_m.get("f1",0), eif_m.get("auc_roc",0),
                 eif_m.get("precision",0), eif_m.get("recall",0))
        comparative.append({
            "algo": "ExtendedIsolationForest",
            "metrics": eif_m,
            "note": "métriques issues de T10.3 — modèle non persisté (incompatibilité Cython/joblib)"
        })

    for name, model in models.items():
        log.info("── %s ──", name)
        scaler = ocsvm_scaler if name == "SGDOneClassSVM" else None
        scores, y_pred = score_model(name, model, X_test, scaler=scaler)

        threshold = optimal_threshold_pr(y_test, scores)
        y_pred_thr = (scores >= threshold).astype(int)
        metrics   = full_metrics(y_test, scores, threshold)
        ci        = bootstrap_ci(y_test, scores, threshold)
        metrics["bootstrap_ci"] = ci

        log.info("  F1=%.4f [%.4f-%.4f] | AUC=%.4f | MCC=%.4f | FPR=%.4f",
                 ci["f1"]["mean"], ci["f1"]["ci_lo"], ci["f1"]["ci_hi"],
                 metrics["auc_roc"], metrics["mcc"], metrics["fpr"])

        row = {"algo": name, "metrics": metrics}

        # McNemar vs IF classique
        if name == "IsolationForest":
            ref_pred = y_pred_thr
        elif ref_pred is not None:
            row["mcnemar_vs_if"] = mcnemar_test(
                y_test, ref_pred, y_pred_thr, "IsolationForest", name
            )
            sig = row["mcnemar_vs_if"]["significant"]
            log.info("  McNemar vs IF : p=%.4f (significatif: %s)",
                     row["mcnemar_vs_if"]["pvalue"], sig)

        comparative.append(row)

        # PCA figure pour IF classique uniquement
        if name == "IsolationForest" and not args.no_plot:
            plot_pca_clusters(X_test, y_test, y_pred_thr, branch)

    # Sauvegarde tableau comparatif
    out_dir = RESULTS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "t10_7_comparative_table.json"
    path.write_text(json.dumps(comparative, indent=2, ensure_ascii=False))
    log.info(SEP)
    log.info("✅ T10.7 terminé [%s] — %s", branch.upper(), path)
    log.info("Prochaine étape :")
    log.info("  python scripts/t10_8_persist.py --branch %s", branch)
    log.info(SEP)

if __name__ == "__main__":
    main()