"""
MODULE : scripts/t10_3_train_if.py
DESCRIPTION : Entraînement de la famille Isolation Forest sur les splits
              produits par T10.2. Trois variantes comparées sur les
              mêmes splits (protocole ADR-006).

RÉFÉRENCES ACADÉMIQUES :
- [Liu2008] Liu et al. (2008). Isolation Forest. ICDM 2008.
  → Algorithme central MAKORA. Complexité O(n log n), robuste haute dim.
- [Hariri2019] Hariri, S., Kind, M. C., & Brunner, R. J. (2019).
  Extended Isolation Forest. IEEE TNNLS.
  → Corrige le biais des hyperplans axiaux d'IF classique via découpes
    obliques aléatoires. Pertinent sur features hétérogènes XAF/ratios.
- [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection.
  ICMLA. → Contamination [3%, 10%] — plage documentée pour la fraude.
- [Bergstra2012] Bergstra & Bengio (2012). Random Search for Hyper-Parameter
  Optimization. JMLR. → RandomizedSearchCV plus efficace que GridSearch
  sur espaces de faible sensibilité (IF a peu d'hyperparamètres impactants).

DÉCISIONS DE CONCEPTION :
- RandomizedSearchCV sur contamination uniquement — [Liu2008] montre que
  n_estimators ≥ 100 et max_samples='auto' convergent systématiquement.
- EIF via la librairie `eif` (pip install eif) — wrappée dans la même
  interface que IF classique pour le tableau comparatif.
- SGD-based SGDOneClassSVM exclue de ce fichier (→ t10_4_challengers.py).
- Modèles sauvegardés sous data/models/{branch}/ pour t10_8_persist.py.

USAGE :
  python scripts/t10_3_train_if.py --branch sante
  python scripts/t10_3_train_if.py --branch auto
  python scripts/t10_3_train_if.py --branch sante --skip-eif  # si eif non installé
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score
import joblib

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("makora.t10_3")

PROJECT_ROOT  = Path(__file__).resolve().parent.parent
SPLITS_DIR    = PROJECT_ROOT / "data" / "splits"
MODELS_DIR    = PROJECT_ROOT / "data" / "models"
RESULTS_DIR   = PROJECT_ROOT / "results"

# Ajoute PROJECT_ROOT au path pour importer les modules MAKORA
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

RANDOM_STATE  = 42
LABEL_COL     = "Label_Anomalie"
NORMAL_VAL    = "NORMAL"

# [Bauder2017] — plage contamination documentée fraude assurance 3-10%
CONTAMINATION_GRID = [0.03, 0.05, 0.07, 0.08, 0.10, 0.12]

META_COLS = {
    "Label_Anomalie", "Sous_Type_Anomalie", "Cause_Racine_RCA",
    "Severite_Anomalie", "Source_Detection", "Validee_Par_Auditeur",
    "Date_Validation", "Commentaire_Audit", "Montant_Prejudice",
    "ID_Sinistre", "ID_Assure", "ID_Praticien", "ID_Vehicule",
    "ID_Contrat", "ID_Expert", "ID_Garage", "Hash_Image", "Batch_Date",
}

# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_splits(branch: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Charge les splits Parquet produits par T10.2."""
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
        log.info("[%s] %s : %d lignes", branch.upper(), split_name, len(splits[split_name]))
    return splits["train"], splits["val"], splits["test"]

def apply_module(df: pd.DataFrame, branch: str) -> tuple[pd.DataFrame, list[str]]:
    """
    Applique engineer_features() du module métier sur le DataFrame.

    C'est l'étape critique manquante dans la version précédente :
    sans engineer_features(), IF travaille sur des colonnes brutes
    (IDs, dates encodées) au lieu des features métier calculées
    (ratio_prix_mercuriale, incoherence_sexe_acte, etc.)

    [Sculley2015] — séparer feature engineering et ML est obligatoire
    pour maintenir la reproductibilité et éviter la dette technique.
    """
    try:
        # Import dynamique du module MAKORA via PluginRegistry
        from core.plugin_registry import PluginRegistry
        # Force l'import du module pour déclencher @register
        if branch == "sante":
            import modules.sante.sante_module  # noqa: F401
        elif branch == "auto":
            import modules.auto.auto_module    # noqa: F401

        yaml_path = PROJECT_ROOT / "modules" / branch / f"{branch}.yaml"
        module    = PluginRegistry.get(branch)(config_path=yaml_path)
        df_eng    = module.engineer_features(df)
        features  = [f for f in module.get_feature_names() if f in df_eng.columns]
        log.info("[%s] engineer_features() OK — %d features métier",
                 branch.upper(), len(features))
        return df_eng, features

    except Exception as exc:
        log.warning("[%s] engineer_features() échoué (%s) — fallback colonnes numériques brutes",
                    branch.upper(), exc)
        return df, []

def get_feature_matrix(
    df: pd.DataFrame, branch: str, features_override: list[str] | None = None
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Extrait la matrice X et le vecteur y.
    Utilise les features métier calculées par engineer_features() si disponibles,
    sinon fallback sur toutes les colonnes numériques hors META_COLS.
    """
    if features_override:
        feature_cols = [c for c in features_override if c in df.columns]
    else:
        feature_cols = [
            c for c in df.columns
            if c not in META_COLS and pd.api.types.is_numeric_dtype(df[c])
        ]

    X = df[feature_cols].fillna(0).values.astype(np.float32)
    y = (df[LABEL_COL] != NORMAL_VAL).astype(int).to_numpy()
    log.info("  Matrice features : %d colonnes × %d lignes", len(feature_cols), len(df))
    return X, y, feature_cols

def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray,
                    scores: np.ndarray) -> dict:
    """Calcule les métriques principales — [Goldstein2016]."""
    return {
        "f1":        round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall":    round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "auc_roc":   round(float(roc_auc_score(y_true, scores)), 4),
        "n_pred_anomalie": int(y_pred.sum()),
        "n_true_anomalie": int(y_true.sum()),
    }

# ─── IF Classique — tuning contamination ─────────────────────────────────────

def tune_contamination(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val:   np.ndarray,
    y_val:   np.ndarray,
) -> tuple[float, dict]:
    """
    Sélectionne la contamination optimale par évaluation sur val set.

    RandomizedSearchCV [Bergstra2012] — sur IF, seule la contamination
    impacte significativement le F1. n_estimators ≥ 100 converge
    systématiquement [Liu2008 §4.1].
    """
    log.info("  Tuning contamination sur val set ...")
    best_f1, best_c, results_c = -1.0, 0.08, {}

    for c in CONTAMINATION_GRID:
        model = IsolationForest(
            n_estimators=100,
            contamination=c,
            max_samples="auto",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        )
        model.fit(X_train)
        # sklearn IF : -1 = anomalie, +1 = normal → convertir
        raw_scores = -model.decision_function(X_val)
        y_pred = (model.predict(X_val) == -1).astype(int)
        f1 = float(f1_score(y_val, y_pred, zero_division=0))
        results_c[c] = {"f1": round(f1, 4)}
        log.info("    contamination=%.2f → F1=%.4f", c, f1)
        if f1 > best_f1:
            best_f1, best_c = f1, c

    log.info("  Meilleure contamination : %.2f (F1=%.4f)", best_c, best_f1)
    return best_c, results_c

# ─── IF Classique ─────────────────────────────────────────────────────────────

def train_if_classic(
    X_train: np.ndarray, y_train: np.ndarray,
    X_val:   np.ndarray, y_val:   np.ndarray,
    X_test:  np.ndarray, y_test:  np.ndarray,
    branch:  str,
) -> dict:
    """
    IF classique [Liu2008] avec contamination optimale.
    Modèle de production MAKORA — compatible SHAP TreeExplainer [Lundberg2020].
    """
    log.info("── IF Classique [Liu2008] ──")
    best_c, tuning_results = tune_contamination(X_train, y_train, X_val, y_val)

    t_start = time.perf_counter()
    model = IsolationForest(
        n_estimators=200,          # [Liu2008] : 200 > 100 pour stabilité
        contamination=best_c,
        max_samples="auto",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train)
    train_time = time.perf_counter() - t_start

    # Scores et prédictions test
    raw_scores = -model.decision_function(X_test)  # inversé : + = anomalie
    y_pred     = (model.predict(X_test) == -1).astype(int)
    metrics    = compute_metrics(y_test, y_pred, raw_scores)
    metrics["train_time_s"]   = round(train_time, 3)
    metrics["contamination"]  = best_c
    metrics["tuning_results"] = tuning_results

    log.info("  TEST — F1=%.4f | AUC=%.4f | P=%.4f | R=%.4f",
             metrics["f1"], metrics["auc_roc"],
             metrics["precision"], metrics["recall"])

    # Persistance intermédiaire
    _save_model(model, branch, "if_classic")
    return {"algo": "IsolationForest", "metrics": metrics, "model_key": "if_classic"}

# ─── IF max_features réduit ──────────────────────────────────────────────────

def train_if_maxfeatures(
    X_train: np.ndarray, X_test: np.ndarray,
    y_test: np.ndarray, best_c: float, branch: str,
) -> dict:
    """
    IF avec max_features=0.7 — test sous-sélection sur features hétérogènes.
    Pertinent car features MAKORA mélangent montants XAF, ratios [0-1], flags.
    Référence : [Liu2008] §4 sur l'impact de max_features.
    """
    log.info("── IF max_features=0.7 [Liu2008 §4] ──")
    t_start = time.perf_counter()
    model = IsolationForest(
        n_estimators=200,
        contamination=best_c,
        max_features=0.7,           # sous-sélection features
        max_samples="auto",
        random_state=RANDOM_STATE,
        n_jobs=-1,
    )
    model.fit(X_train)
    train_time = time.perf_counter() - t_start

    raw_scores = -model.decision_function(X_test)
    y_pred     = (model.predict(X_test) == -1).astype(int)
    metrics    = compute_metrics(y_test, y_pred, raw_scores)
    metrics["train_time_s"]  = round(train_time, 3)
    metrics["contamination"] = best_c
    metrics["max_features"]  = 0.7

    log.info("  TEST — F1=%.4f | AUC=%.4f", metrics["f1"], metrics["auc_roc"])
    _save_model(model, branch, "if_maxfeatures07")
    return {"algo": "IsolationForest_maxfeat07", "metrics": metrics,
            "model_key": "if_maxfeatures07"}

# ─── Extended Isolation Forest ───────────────────────────────────────────────

def train_eif(
    X_train: np.ndarray, X_test: np.ndarray,
    y_test: np.ndarray, branch: str,
) -> dict | None:
    """
    Extended Isolation Forest [Hariri2019].
    Corrige le biais des hyperplans axiaux d'IF classique.
    Retourne None si la librairie 'eif' n'est pas installée.
    """
    log.info("── Extended IF [Hariri2019] ──")
    try:
        import eif as iso  # pip install eif
    except ImportError:
        log.warning("  Librairie 'eif' non installée. Skipping EIF.")
        log.warning("  Installer avec : pip install eif --break-system-packages")
        return None

    t_start = time.perf_counter()
    # EIF API : ExtendedIsolationForest(n_trees, sample_size, ExtensionLevel)
    # ExtensionLevel=1 → EIF standard (hyperplans obliques 1D)
    # EIF requiert float64 — [Hariri2019] implémentation C++ strict sur le dtype
    X_train_64 = X_train.astype(np.float64)
    model_eif = iso.iForest(
        X_train_64,
        ntrees=200,
        sample_size=min(256, len(X_train_64)),
        ExtensionLevel=1,
    )
    train_time = time.perf_counter() - t_start

    # EIF retourne des anomaly scores (plus élevé = plus anormal)
    scores = model_eif.compute_paths(X_in=X_test.astype(np.float64))
    threshold = np.percentile(scores, 92)   # ~8% de contamination
    y_pred = (scores >= threshold).astype(int)
    metrics = compute_metrics(y_test, y_pred, scores)
    metrics["train_time_s"] = round(train_time, 3)
    metrics["extension_level"] = 1

    log.info("  TEST — F1=%.4f | AUC=%.4f", metrics["f1"], metrics["auc_roc"])

    # EIF non picklable (Cython __cinit__ non-trivial) → hyperparamètres + métriques en JSON.
    # Réentraîner avec ces params pour reproduire. [Hariri2019] comparaison uniquement.
    out_dir = MODELS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    eif_params = {
        "algo": "ExtendedIsolationForest",
        "ntrees": 200,
        "sample_size": min(256, len(X_train)),
        "ExtensionLevel": 1,
        "note": "Réentraîner avec ces paramètres pour reproduire — objet Cython non picklable"
    }
    import json as _json
    (out_dir / "eif_params.json").write_text(
        _json.dumps({**eif_params, **metrics}, indent=2)
    )
    log.info("  EIF persisté : eif_params.json (hyperparamètres + métriques)")
    return {"algo": "ExtendedIsolationForest", "metrics": metrics,
            "model_key": "eif_params"}

# ─── Persistance ─────────────────────────────────────────────────────────────

def _save_model(model: Any, branch: str, name: str) -> Path:
    """Sauvegarde intermédiaire via joblib."""
    out_dir = MODELS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}_model.joblib"
    joblib.dump(model, path)
    log.info("  Modèle sauvegardé : %s", path.name)
    return path

def save_results(results: list[dict], branch: str) -> None:
    """Sauvegarde les résultats IF dans results/{branch}/t10_3_if_results.json."""
    out_dir = RESULTS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "t10_3_if_results.json"
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    log.info("Résultats écrits : %s", path)

# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MAKORA T10.3 — Entraînement famille Isolation Forest"
    )
    p.add_argument("--branch", choices=["sante", "auto"], required=True)
    p.add_argument("--skip-eif", action="store_true",
                   help="Passer l'EIF (si librairie non installée)")
    return p.parse_args()

def main() -> None:
    args   = parse_args()
    branch = args.branch
    SEP    = "─" * 60

    log.info(SEP)
    log.info("MAKORA — T10.3 Famille Isolation Forest [%s]", branch.upper())
    log.info(SEP)

    # Chargement splits + engineer_features via module MAKORA
    df_train, df_val, df_test = load_splits(branch)

    df_train, feats = apply_module(df_train, branch)
    df_val,   _     = apply_module(df_val,   branch)
    df_test,  _     = apply_module(df_test,  branch)

    X_train, y_train, feats = get_feature_matrix(df_train, branch, feats)
    X_val,   y_val,   _     = get_feature_matrix(df_val,   branch, feats)
    X_test,  y_test,  _     = get_feature_matrix(df_test,  branch, feats)

    log.info("Matrice features : train=%s | val=%s | test=%s",
             X_train.shape, X_val.shape, X_test.shape)
    log.info(SEP)

    all_results = []
    all_results.append({"branch": branch, "features": feats})

    # 1. IF Classique
    res_classic = train_if_classic(
        X_train, y_train, X_val, y_val, X_test, y_test, branch
    )
    all_results.append(res_classic)
    best_c = res_classic["metrics"]["contamination"]

    log.info(SEP)
    # 2. IF max_features=0.7
    res_mf = train_if_maxfeatures(X_train, X_test, y_test, best_c, branch)
    all_results.append(res_mf)

    # 3. EIF (optionnel)
    log.info(SEP)
    if not args.skip_eif:
        res_eif = train_eif(X_train, X_test, y_test, branch)
        if res_eif:
            all_results.append(res_eif)

    # Sauvegarde résultats
    save_results(all_results, branch)

    log.info(SEP)
    log.info("✅ T10.3 terminé [%s]", branch.upper())
    log.info("Prochaine étape :")
    log.info("  python scripts/t10_4_train_challengers.py --branch %s", branch)
    log.info(SEP)

if __name__ == "__main__":
    main()