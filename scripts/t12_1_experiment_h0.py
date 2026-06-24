"""
MODULE : scripts/t12_1_experiment_h0.py
DESCRIPTION : Expérience H0 — Entraîne M_sante, M_auto et M_makora (générique)
              sur leurs splits respectifs et calcule le delta F1 pour valider
              l'hypothèse centrale de généricité du framework MAKORA.

RÉFÉRENCES ACADÉMIQUES :
- [Caruana1997] Caruana, R. (1997). Multitask learning. Machine Learning, 28(1).
  → Fondement théorique : un modèle multi-tâche (M_makora) peut rivaliser
    avec des modèles spécialisés si les tâches partagent une structure latente.
- [Xu2023] Xu et al. (2023). Deep Isolation Forest. IEEE TKDE.
  → Algorithme retenu pour les 3 modèles H0. Convention de score PyOD :
    decision_function() élevé = anomalie (opposé de sklearn IF).
- [Kohavi1995] Kohavi, R. (1995). A study of cross-validation and bootstrap.
  IJCAI. → Split 70/15/15 reproductible seed=42 — protocole standard.
- [Goldstein2016] Goldstein & Uchida (2016). Comparative evaluation of
  unsupervised anomaly detection algorithms. PLOS ONE.
  → Protocole de comparaison sur mêmes splits immutables.

DÉCISIONS DE CONCEPTION :
- M_makora est entraîné sur la concaténation train_sante + train_auto,
  avec les features COMMUNES aux deux modules (intersection).
  [Caruana1997] : la généralisation inter-tâches requiert un espace
  de features partagé.
- Contamination M_makora = moyenne pondérée des deux branches.
- Les features sont normalisées (StandardScaler) AVANT concat pour
  éviter le biais d'échelle (XAF vs EUR, montants vs ratios [0,1]).
- Test sets IMMUTABLES — jamais touchés avant cette évaluation finale.
- Résultats écrits dans results/h0/ pour T12.2 (calcul Δ) et T12.3 (FP/FN).

CORRECTIONS v2 (08 juin 2026) :
- predict() : suppression de la normalisation 1-(raw-min)/(max-min) qui
  inversait le score DIF. Convention PyOD [Xu2023] : decision_function()
  retourne directement un score où anomalie = valeur haute. Cohérent avec
  t10_4b, t13_bootstrap et ML_PIPELINE.md §4.3.
- CONTAMINATION["auto"] : 0.080 → 0.100 (valeur calibrée sur val set T10.3,
  utilisée dans tous les résultats de production [Bauder2017]).

USAGE :
  python scripts/t12_1_experiment_h0.py
  python scripts/t12_1_experiment_h0.py --branch sante   # modèle seul
  python scripts/t12_1_experiment_h0.py --branch auto --no-makora  # validation rapide
  python scripts/t12_1_experiment_h0.py --no-makora      # spécialisés uniquement
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
from pyod.models.dif import DIF
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("makora.t12_1")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SPLITS_DIR  = PROJECT_ROOT / "data" / "splits"
MODELS_DIR  = PROJECT_ROOT / "data" / "models"
RESULTS_DIR = PROJECT_ROOT / "results" / "h0"

RANDOM_STATE = 42
LABEL_COL    = "Label_Anomalie"
NORMAL_VAL   = "NORMAL"
BOOTSTRAP_N  = 1000

# [CORRECTION] Contaminations issues de T10.3 (optimisées sur val set)
# auto : 0.080 → 0.100 — valeur calibrée T10.3, cohérente avec production
# [Bauder2017] taux fraude assurance auto : 5-10%, optimal val set = 10%
CONTAMINATION = {"sante": 0.068, "auto": 0.100}

META_COLS = {
    "Label_Anomalie", "Sous_Type_Anomalie", "Cause_Racine_RCA",
    "Severite_Anomalie", "Source_Detection", "Validee_Par_Auditeur",
    "Date_Validation", "Commentaire_Audit", "Montant_Prejudice",
    "ID_Sinistre", "ID_Assure", "ID_Praticien", "ID_Vehicule",
    "ID_Contrat", "ID_Expert", "ID_Garage", "Hash_Image", "Batch_Date",
    "community_id_sante", "community_id_auto",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_splits(branch: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Charge train + test (val non utilisé — protocole H0)."""
    bd = SPLITS_DIR / branch
    splits = {}
    for s in ("train", "test"):
        p = bd / f"{branch}_{s}.parquet"
        if not p.exists():
            raise FileNotFoundError(f"Split '{s}' introuvable : {p}")
        splits[s] = pd.read_parquet(p)
    log.info("[%s] train=%d | test=%d",
             branch.upper(), len(splits["train"]), len(splits["test"]))
    return splits["train"], splits["test"]


def apply_module(df: pd.DataFrame, branch: str) -> tuple[pd.DataFrame, list[str]]:
    """Appelle engineer_features() du module via PluginRegistry."""
    from core.plugin_registry import PluginRegistry
    if branch == "sante":
        import modules.sante.sante_module  # noqa — déclenche @register
    elif branch == "auto":
        import modules.auto.auto_module    # noqa — déclenche @register

    yaml_path = PROJECT_ROOT / "modules" / branch / f"{branch}.yaml"
    module    = PluginRegistry.get(branch)(config_path=yaml_path)
    df_eng    = module.engineer_features(df.copy())
    feats     = [f for f in module.get_feature_names() if f in df_eng.columns]
    log.info("[%s] engineer_features → %d features", branch.upper(), len(feats))
    return df_eng, feats


def get_xy(df: pd.DataFrame, feats: list[str]) -> tuple[np.ndarray, np.ndarray]:
    X = df[feats].fillna(0).values.astype(np.float32)
    y = (df[LABEL_COL] != NORMAL_VAL).astype(int).values
    return X, y


def bootstrap_f1_ci(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    n: int = BOOTSTRAP_N,
    alpha: float = 0.05,
    seed: int = RANDOM_STATE,
) -> tuple[float, float]:
    """Intervalle de confiance F1 par bootstrap [Kohavi1995]."""
    rng = np.random.default_rng(seed)
    scores = []
    for _ in range(n):
        idx = rng.integers(0, len(y_true), len(y_true))
        if y_true[idx].sum() == 0:
            continue
        scores.append(f1_score(y_true[idx], y_pred[idx], zero_division=0))
    lo = float(np.percentile(scores, 100 * alpha / 2))
    hi = float(np.percentile(scores, 100 * (1 - alpha / 2)))
    return lo, hi


def compute_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    scores: np.ndarray,
    model_name: str,
    branch: str,
    elapsed: float,
) -> dict:
    """Calcule toutes les métriques ADR-006 + IC bootstrap."""
    f1  = float(f1_score(y_true, y_pred, zero_division=0))
    ci  = bootstrap_f1_ci(y_true, y_pred)
    return {
        "model":           model_name,
        "branch_eval":     branch,
        "f1":              round(f1, 4),
        "f1_ci_low":       round(ci[0], 4),
        "f1_ci_high":      round(ci[1], 4),
        "precision":       round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall":          round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "auc_roc":         round(float(roc_auc_score(y_true, scores)), 4),
        "avg_precision":   round(float(average_precision_score(y_true, scores)), 4),
        "mcc":             round(float(matthews_corrcoef(y_true, y_pred)), 4),
        "fpr":             _fpr(y_true, y_pred),
        "n_test":          int(len(y_true)),
        "n_anomalies":     int(y_true.sum()),
        "train_time_s":    round(elapsed, 2),
    }


def _fpr(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """False Positive Rate = FP / (FP + TN) — critique en contexte opérationnel."""
    fp = int(((y_pred == 1) & (y_true == 0)).sum())
    tn = int(((y_pred == 0) & (y_true == 0)).sum())
    return round(fp / (fp + tn), 4) if (fp + tn) > 0 else 0.0


def train_if(
    X_train: np.ndarray,
    contamination: float,
    model_name: str,
) -> DIF:
    """
    Entraîne un Deep Isolation Forest [Xu2023].
    Nom conservé 'train_if' pour compatibilité avec les appels existants.
    """
    log.info("  Entraînement IF — %s | n=%d | contamination=%.3f",
             model_name, len(X_train), contamination)
    t0  = time.time()
    clf = DIF(
        hidden_neurons=[64, 32],
        contamination=contamination,
        random_state=RANDOM_STATE,
        device='cpu',
    )
    clf.fit(X_train)
    log.info("  → terminé en %.1fs", time.time() - t0)
    return clf


def predict(clf: DIF, X: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """
    Retourne (labels binaires, anomaly scores).

    [CORRECTION] Convention PyOD [Xu2023] : decision_function() retourne
    un score où anomalie = valeur haute. Pas de normalisation ni d'inversion.
    Cohérent avec t10_4b_pyod_tier1.py, t13_bootstrap_ci_candidates.py
    et ML_PIPELINE.md §4.3 : "scores = model.decision_function(X)".

    PyOD predict() retourne directement 0 (normal) ou 1 (anomalie).
    Pas de conversion -1/1 nécessaire (convention sklearn IF).
    """
    scores = clf.decision_function(X)   # anomalie = score élevé [Xu2023]
    preds  = clf.predict(X).astype(int) # 0=normal, 1=anomalie (convention PyOD)
    return preds, scores


def save_model(clf, scaler, feats: list[str], model_name: str, branch: str) -> None:
    out = MODELS_DIR / "h0"
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": clf, "scaler": scaler, "features": feats},
                out / f"{model_name}_{branch}.joblib")
    log.info("  Modèle sauvegardé : %s", out / f"{model_name}_{branch}.joblib")


# ─── M_sante & M_auto (spécialisés) ──────────────────────────────────────────

def train_specialized(branch: str) -> dict:
    """
    Entraîne M_sante ou M_auto sur leur split respectif.
    Évalue sur le test set IMMUTABLE du même branch.
    [Xu2023] + [Goldstein2016]
    """
    log.info("=" * 60)
    log.info("M_%s — Modèle spécialisé", branch)
    log.info("=" * 60)

    df_train, df_test = load_splits(branch)
    df_train_eng, feats = apply_module(df_train, branch)
    df_test_eng,  _     = apply_module(df_test,  branch)

    X_train, _      = get_xy(df_train_eng, feats)
    X_test,  y_test = get_xy(df_test_eng,  feats)

    # Normalisation — [Sculley2015] : features de scales très différentes
    scaler  = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_test  = scaler.transform(X_test)

    t0  = time.time()
    clf = train_if(X_train, CONTAMINATION[branch], f"M_{branch}")
    elapsed = time.time() - t0

    preds, scores = predict(clf, X_test)
    metrics = compute_metrics(
        y_test, preds, scores,
        model_name=f"M_{branch}",
        branch=branch,
        elapsed=elapsed,
    )

    save_model(clf, scaler, feats, f"M_{branch}", branch)

    log.info("  F1=%.4f | AUC=%.4f | MCC=%.4f | FPR=%.4f",
             metrics["f1"], metrics["auc_roc"], metrics["mcc"], metrics["fpr"])
    return metrics


# ─── M_makora (générique) ─────────────────────────────────────────────────────

def build_makora_dataset(
    df_sante_train: pd.DataFrame,
    feats_sante: list[str],
    df_auto_train: pd.DataFrame,
    feats_auto: list[str],
) -> tuple[np.ndarray, list[str], StandardScaler, StandardScaler]:
    """
    Construit le dataset d'entraînement générique de M_makora.

    Stratégie : intersection des features communes + normalisation par branche
    avant concaténation. [Caruana1997] — la structure latente commune
    (ratio prix/barème, concentration, délai) transcende les branches.

    Retourne X_makora, liste features communes, scaler_sante, scaler_auto.
    """
    common_feats = sorted(set(feats_sante) & set(feats_auto))
    log.info("Features communes Santé ∩ Auto : %d → %s", len(common_feats), common_feats)

    if not common_feats:
        raise ValueError(
            "Aucune feature commune Santé/Auto — vérifier les YAML. "
            "M_makora nécessite un espace de features partagé [Caruana1997]."
        )

    X_s, _ = get_xy(df_sante_train, common_feats)
    X_a, _ = get_xy(df_auto_train,  common_feats)

    # Normalisation par branche — évite que les grandes valeurs XAF écrasent
    scaler_s = StandardScaler()
    scaler_a = StandardScaler()
    X_s_norm = scaler_s.fit_transform(X_s)
    X_a_norm = scaler_a.fit_transform(X_a)

    X_makora = np.vstack([X_s_norm, X_a_norm])
    log.info("Dataset MAKORA : %d lignes × %d features communes", *X_makora.shape)
    return X_makora, common_feats, scaler_s, scaler_a


def train_makora(
    df_sante_train: pd.DataFrame, feats_sante: list[str],
    df_auto_train:  pd.DataFrame, feats_auto:  list[str],
    df_sante_test:  pd.DataFrame,
    df_auto_test:   pd.DataFrame,
) -> list[dict]:
    """
    Entraîne M_makora et l'évalue sur les deux test sets.
    [Caruana1997] — évaluation multi-tâche sur chaque domaine.
    """
    log.info("=" * 60)
    log.info("M_makora — Modèle générique (Santé + Auto)")
    log.info("=" * 60)

    X_makora, common_feats, scaler_s, scaler_a = build_makora_dataset(
        df_sante_train, feats_sante,
        df_auto_train,  feats_auto,
    )

    # Contamination = moyenne pondérée par taille de dataset
    n_s = len(df_sante_train)
    n_a = len(df_auto_train)
    contam_makora = (
        CONTAMINATION["sante"] * n_s + CONTAMINATION["auto"] * n_a
    ) / (n_s + n_a)
    log.info("Contamination M_makora = %.4f (moyenne pondérée)", contam_makora)

    t0  = time.time()
    clf = train_if(X_makora, contam_makora, "M_makora")
    elapsed = time.time() - t0

    results = []
    for branch, df_test, feats_br, scaler_br in [
        ("sante", df_sante_test, feats_sante, scaler_s),
        ("auto",  df_auto_test,  feats_auto,  scaler_a),
    ]:
        df_test_eng, _ = apply_module(df_test, branch)
        X_t, y_t = get_xy(df_test_eng, common_feats)
        X_t_norm = scaler_br.transform(X_t)

        preds, scores = predict(clf, X_t_norm)
        m = compute_metrics(
            y_t, preds, scores,
            model_name="M_makora",
            branch=branch,
            elapsed=elapsed,
        )
        m["common_features"]   = common_feats
        m["n_common_features"] = len(common_feats)
        results.append(m)
        log.info("  [%s] F1=%.4f | AUC=%.4f | MCC=%.4f | FPR=%.4f",
                 branch.upper(), m["f1"], m["auc_roc"], m["mcc"], m["fpr"])

    # Sauvegarder le modèle avec les deux scalers
    out = MODELS_DIR / "h0"
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump({
        "model":          clf,
        "scaler_sante":   scaler_s,
        "scaler_auto":    scaler_a,
        "common_features": common_feats,
    }, out / "M_makora.joblib")
    log.info("M_makora sauvegardé : %s", out / "M_makora.joblib")
    return results


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MAKORA T12.1 — Expérience H0")
    p.add_argument("--branch",     choices=["sante", "auto"], default=None,
                   help="Entraîner un modèle spécialisé uniquement")
    p.add_argument("--no-makora",  action="store_true",
                   help="Sauter M_makora (spécialisés uniquement)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    all_results: list[dict] = []

    # ── Modèles spécialisés ──────────────────────────────────────────
    branches_to_run = [args.branch] if args.branch else ["sante", "auto"]
    specialized: dict[str, dict] = {}

    for branch in branches_to_run:
        m = train_specialized(branch)
        specialized[branch] = m
        all_results.append(m)

    # ── M_makora ─────────────────────────────────────────────────────
    if not args.no_makora and not args.branch:
        df_s_train, df_s_test = load_splits("sante")
        df_a_train, df_a_test = load_splits("auto")

        df_s_train_eng, feats_s = apply_module(df_s_train, "sante")
        df_a_train_eng, feats_a = apply_module(df_a_train, "auto")

        makora_results = train_makora(
            df_s_train_eng, feats_s,
            df_a_train_eng, feats_a,
            df_s_test,
            df_a_test,
        )
        all_results.extend(makora_results)

    # ── Sauvegarde ───────────────────────────────────────────────────
    out_path = RESULTS_DIR / "t12_1_models_metrics.json"
    out_path.write_text(
        json.dumps(all_results, indent=2, ensure_ascii=False, default=str)
    )
    log.info("Métriques sauvegardées → %s", out_path)
    log.info("Prochaine étape : python scripts/t12_2_delta_analysis.py")


if __name__ == "__main__":
    main()