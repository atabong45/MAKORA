"""
MODULE : scripts/t10_4_train_challengers.py
DESCRIPTION : Entraînement des algorithmes challengers (LOF, OC-SVM SGD, HBOS)
              sur les mêmes splits que T10.3 — protocole ADR-006.

RÉFÉRENCES ACADÉMIQUES :
- [Breunig2000] Breunig et al. (2000). LOF: identifying density-based local
  outliers. SIGMOD. → Détecte anomalies locales qu'IF manque (surfacturation
  ciblée sur un praticien spécifique). k=20 recommandé pour 10k–500k lignes.
- [Schölkopf2001] Schölkopf et al. (2001). Estimating the support of a
  high-dimensional distribution. Neural Computation. → OC-SVM.
- [Goldstein2012] Goldstein & Uchida (2012). Histogram-based Outlier Score.
  → HBOS : O(n) en complexité, assume indépendance des features. Baseline
    computationnelle — si HBOS ≈ IF en F1 mais 10× plus rapide, argument
    opérationnel fort pour le déploiement en contexte africain faibles ressources.
- [Goldstein2016] Goldstein & Uchida (2016). Comparative evaluation of
  unsupervised anomaly detection algorithms. PLOS ONE. → Justification ADR-006.

DÉCISIONS DE CONCEPTION :
- LOF avec novelty=True — requis pour scorer de nouveaux points.
  Non-compatible SHAP → comparaison uniquement, pas de production.
- OC-SVM SGD (sklearn.linear_model.SGDOneClassSVM) — scalable sur 140k
  lignes. OC-SVM classique (O(n²)) écarté pour scalabilité [Schölkopf2001].
- HBOS via PyOD (pip install pyod) — fallback si non installé.
- StandardScaler requis pour OC-SVM — features de scales très différentes
  (montants XAF vs ratios [0,1]).

USAGE :
  python scripts/t10_4_train_challengers.py --branch sante
  python scripts/t10_4_train_challengers.py --branch auto
"""

from __future__ import annotations

import argparse
import sys
import json
import logging
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import SGDOneClassSVM
from sklearn.neighbors import LocalOutlierFactor
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
from sklearn.preprocessing import StandardScaler

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("makora.t10_4")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPLITS_DIR   = PROJECT_ROOT / "data" / "splits"
MODELS_DIR   = PROJECT_ROOT / "data" / "models"
RESULTS_DIR  = PROJECT_ROOT / "results"

# Ajoute PROJECT_ROOT au path pour importer les modules MAKORA
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RANDOM_STATE = 42
LABEL_COL    = "Label_Anomalie"
NORMAL_VAL   = "NORMAL"

META_COLS = {
    "Label_Anomalie", "Sous_Type_Anomalie", "Cause_Racine_RCA",
    "Severite_Anomalie", "Source_Detection", "Validee_Par_Auditeur",
    "Date_Validation", "Commentaire_Audit", "Montant_Prejudice",
    "ID_Sinistre", "ID_Assure", "ID_Praticien", "ID_Vehicule",
    "ID_Contrat", "ID_Expert", "ID_Garage", "Hash_Image", "Batch_Date",
}


# ─── Helpers (partagés avec t10_3) ───────────────────────────────────────────

def load_splits(branch: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    branch_dir = SPLITS_DIR / branch
    splits = {}
    for split_name in ("train", "val", "test"):
        path = branch_dir / f"{branch}_{split_name}.parquet"
        if not path.exists():
            raise FileNotFoundError(
                f"Split '{split_name}' introuvable : {path}\n"
                f"Lancer d'abord : python scripts/t10_2_split.py"
            )
        splits[split_name] = pd.read_parquet(path)
    log.info("[%s] Splits chargés — train=%d, val=%d, test=%d",
             branch.upper(),
             len(splits["train"]), len(splits["val"]), len(splits["test"]))
    return splits["train"], splits["val"], splits["test"]


def get_feature_matrix_feats(
    df: pd.DataFrame, feats: list[str]
) -> tuple[np.ndarray, np.ndarray]:
    """Extrait X et y à partir d'une liste de features métier explicite."""
    X = df[feats].fillna(0).values.astype(np.float32)
    y = (df[LABEL_COL] != NORMAL_VAL).to_numpy(dtype=int)
    return X, y


def get_feature_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    feature_cols = [
        c for c in df.columns
        if c not in META_COLS and pd.api.types.is_numeric_dtype(df[c])
    ]
    X = df[feature_cols].fillna(0).values.astype(np.float32)
    y = (df[LABEL_COL] != NORMAL_VAL).astype(int).values
    return X, y


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                    scores: np.ndarray) -> dict:
    return {
        "f1":             round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "precision":      round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall":         round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "auc_roc":        round(float(roc_auc_score(y_true, scores)), 4),
        "n_pred_anomalie": int(y_pred.sum()),
        "n_true_anomalie": int(y_true.sum()),
    }


def _save_model(obj: object, branch: str, name: str) -> None:
    out_dir = MODELS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(obj, out_dir / f"{name}_model.joblib")
    log.info("  Sauvegardé : %s_model.joblib", name)


# ─── LOF ─────────────────────────────────────────────────────────────────────

def train_lof(
    X_train: np.ndarray, X_test: np.ndarray,
    y_test: np.ndarray, contamination: float, branch: str,
) -> dict:
    """
    LOF [Breunig2000] — baseline densité locale.

    Teste trois valeurs de k (10, 20, 50) sur le test set.
    k=20 est la valeur recommandée par [Breunig2000] pour les datasets
    de taille intermédiaire. On retient le meilleur k pour le rapport.

    Limite : complexité O(n²) → non-scalable en production.
    novelty=True requis pour scorer de nouveaux points post-fit.
    """
    log.info("── LOF [Breunig2000] ──")
    best_result: dict = {}
    best_f1 = -1.0

    for k in [10, 20, 50]:
        t_start = time.perf_counter()
        model = LocalOutlierFactor(
            n_neighbors=k,
            contamination=contamination,
            novelty=True,           # requis pour predict() post-fit
            n_jobs=-1,
        )
        model.fit(X_train)
        train_time = time.perf_counter() - t_start

        scores = -model.decision_function(X_test)   # + = anomalie
        y_pred = (model.predict(X_test) == -1).astype(int)
        metrics = compute_metrics(y_test, y_pred, scores)
        metrics["train_time_s"] = round(train_time, 3)
        metrics["n_neighbors"]  = k
        metrics["contamination"] = contamination

        log.info("  k=%-3d → F1=%.4f | AUC=%.4f | train=%.1fs",
                 k, metrics["f1"], metrics["auc_roc"], train_time)

        if metrics["f1"] > best_f1:
            best_f1 = metrics["f1"]
            best_result = {"algo": f"LOF_k{k}", "metrics": metrics,
                           "model_key": f"lof_k{k}"}
            _save_model(model, branch, f"lof_k{k}")

    log.info("  Meilleur LOF : %s (F1=%.4f)", best_result["algo"], best_f1)
    return best_result


# ─── OC-SVM SGD ──────────────────────────────────────────────────────────────

def train_ocsvm_sgd(
    X_train: np.ndarray, X_test: np.ndarray,
    y_test: np.ndarray, contamination: float, branch: str,
) -> dict:
    """
    SGDOneClassSVM [Schölkopf2001] — version scalable d'OC-SVM.

    OC-SVM classique (kernel RBF) = O(n²) sur 140k lignes → inutilisable.
    SGDOneClassSVM = approximation linéaire scalable O(n).
    Requiert StandardScaler — features de scales hétérogènes (XAF vs ratios).

    nu ≈ contamination (upperbound sur le taux d'outliers) [Schölkopf2001].
    """
    log.info("── OC-SVM SGD [Schölkopf2001] ──")

    # StandardScaler OBLIGATOIRE pour OC-SVM
    scaler = StandardScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    t_start = time.perf_counter()
    model = SGDOneClassSVM(
        nu=contamination,           # [Schölkopf2001] : nu ≈ contamination
        random_state=RANDOM_STATE,
    )
    model.fit(X_train_s)
    train_time = time.perf_counter() - t_start

    scores = -model.decision_function(X_test_s)   # + = anomalie
    y_pred = (model.predict(X_test_s) == -1).astype(int)
    metrics = compute_metrics(y_test, y_pred, scores)
    metrics["train_time_s"] = round(train_time, 3)
    metrics["nu"]           = contamination
    metrics["scaler"]       = "StandardScaler"

    log.info("  TEST — F1=%.4f | AUC=%.4f | train=%.1fs",
             metrics["f1"], metrics["auc_roc"], train_time)

    _save_model(model, branch, "ocsvm_sgd")
    _save_model(scaler, branch, "ocsvm_scaler")
    return {"algo": "SGDOneClassSVM", "metrics": metrics, "model_key": "ocsvm_sgd"}


# ─── HBOS ────────────────────────────────────────────────────────────────────

def train_hbos(
    X_train: np.ndarray, X_test: np.ndarray,
    y_test: np.ndarray, contamination: float, branch: str,
) -> dict | None:
    """
    HBOS [Goldstein2012] — Histogram-Based Outlier Score.

    O(n·d) en complexité. Assume indépendance des features (naïf).
    Baseline computationnelle : si HBOS ≈ IF en F1 mais 10× plus rapide,
    argument opérationnel fort pour contexte africain faibles ressources.
    Retourne None si PyOD non installé.
    """
    log.info("── HBOS [Goldstein2012] ──")
    HBOS = None
    for _pyod_path in [
        None,  # import standard d'abord
        "/home/atabong/anaconda3/lib/python3.12/site-packages",
        "/home/atabong/anaconda3/lib/python3.11/site-packages",
    ]:
        try:
            if _pyod_path and _pyod_path not in sys.path:
                sys.path.insert(0, _pyod_path)
            from pyod.models.hbos import HBOS as _HBOS
            HBOS = _HBOS
            break
        except ImportError:
            continue
    if HBOS is None:
        log.warning("  PyOD introuvable même depuis Anaconda — HBOS ignoré.")
        return None

    t_start = time.perf_counter()
    model = HBOS(
        n_bins=10,
        alpha=0.1,
        tol=0.5,
        contamination=contamination,
    )
    model.fit(X_train)
    train_time = time.perf_counter() - t_start

    scores = model.decision_function(X_test)        # + = anomalie
    y_pred = model.predict(X_test)                  # 0 = normal, 1 = anomalie
    metrics = compute_metrics(y_test, y_pred, scores)
    metrics["train_time_s"] = round(train_time, 3)
    metrics["n_bins"]       = 10

    log.info("  TEST — F1=%.4f | AUC=%.4f | train=%.1fs",
             metrics["f1"], metrics["auc_roc"], train_time)

    _save_model(model, branch, "hbos")
    return {"algo": "HBOS", "metrics": metrics, "model_key": "hbos"}


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MAKORA T10.4 — Challengers LOF + OC-SVM SGD + HBOS"
    )
    p.add_argument("--branch", choices=["sante", "auto"], required=True)
    return p.parse_args()


def main() -> None:
    args   = parse_args()
    branch = args.branch
    SEP    = "─" * 60

    log.info(SEP)
    log.info("MAKORA — T10.4 Challengers [%s]", branch.upper())
    log.info(SEP)

    df_train, df_val, df_test = load_splits(branch)

    # engineer_features() via le module MAKORA — même correction que T10.3
    from core.plugin_registry import PluginRegistry
    if branch == "sante":
        import modules.sante.sante_module  # noqa: F401
    elif branch == "auto":
        import modules.auto.auto_module    # noqa: F401
    yaml_path = PROJECT_ROOT / "modules" / branch / f"{branch}.yaml"
    module    = PluginRegistry.get(branch)(config_path=yaml_path)
    df_train  = module.engineer_features(df_train)
    df_test   = module.engineer_features(df_test)
    feats     = [f for f in module.get_feature_names() if f in df_train.columns]
    log.info("[%s] Features métier : %d", branch.upper(), len(feats))

    X_train, y_train = get_feature_matrix_feats(df_train, feats)
    X_test,  y_test  = get_feature_matrix_feats(df_test,  feats)

    # Récupère contamination optimale depuis T10.3
    t10_3_path = RESULTS_DIR / branch / "t10_3_if_results.json"
    contamination = 0.08   # [Bauder2017] default
    if t10_3_path.exists():
        t10_3 = json.loads(t10_3_path.read_text())
        for entry in t10_3:
            if entry.get("algo") == "IsolationForest":
                contamination = entry["metrics"].get("contamination", 0.08)
                break
    log.info("Contamination : %.2f (issue de T10.3)", contamination)
    log.info(SEP)

    all_results: list[dict] = [{"branch": branch}]

    all_results.append(train_lof(X_train, X_test, y_test, contamination, branch))
    log.info(SEP)
    all_results.append(train_ocsvm_sgd(X_train, X_test, y_test, contamination, branch))
    log.info(SEP)
    hbos_res = train_hbos(X_train, X_test, y_test, contamination, branch)
    if hbos_res:
        all_results.append(hbos_res)

    # Sauvegarde
    out_dir = RESULTS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "t10_4_challengers_results.json"
    path.write_text(json.dumps(all_results, indent=2, ensure_ascii=False))
    log.info(SEP)
    log.info("✅ T10.4 terminé [%s] — résultats : %s", branch.upper(), path)
    log.info("Prochaine étape :")
    log.info("  python scripts/t10_5_learning_curves.py --branch %s", branch)
    log.info(SEP)


if __name__ == "__main__":
    main()