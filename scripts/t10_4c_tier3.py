"""
MODULE : scripts/t10_4c_tier3.py
DESCRIPTION : Challengers Phase 2b — Tier 3 (apprentissage profond & semi-
              supervisé). AutoEncoder (reconstruction) et PU Learning
              (Positive-Unlabeled) exploitant les cas RCA haute confiance
              comme ensemble positif. Mêmes splits immuables que T10.3/T10.4.
              Exécution résiliente (voir scripts/_ml_common.py).

RÉFÉRENCES ACADÉMIQUES :
- [Hawkins2002] Hawkins et al. (2002). Outlier Detection Using Replicator
  Neural Networks. DaWaK. → Erreur de reconstruction comme score d'anomalie.
- [An2015] An & Cho (2015). Variational Autoencoder based Anomaly Detection
  using Reconstruction Probability. ICML Workshop.
- [Elkan2008] Elkan & Noto (2008). Learning classifiers from only positive and
  unlabeled data. KDD. → Cadre PU : P = cas RCA confirmés, U = reste.
- [Liu2002] Liu, B. et al. (2002). Partially Supervised Classification. ICML.

DÉCISIONS DE CONCEPTION :
- AutoEncoder via PyOD (backend torch CPU) — famille différente des arbres,
  attribution naturelle par erreur de reconstruction par feature (pas de SHAP).
- PU Learning : approche Elkan-Noto. On entraîne un classifieur probabiliste
  sur (P vs U), puis on corrige le score par le facteur c = P(s=1|y=1) estimé
  sur un held-out de P. Classifieur = RandomForest → COMPATIBLE SHAP
  TreeExplainer (contrairement aux autres challengers).
- Le seuil de confiance RCA pour constituer P est un hyperparamètre balayé.
- Si aucune colonne RCA exploitable n'existe dans les splits, PU est skippé
  proprement (status "skipped") — la campagne continue.

USAGE :
  python scripts/t10_4c_tier3.py --branch sante
  python scripts/t10_4c_tier3.py --branch auto --timeout 900
  python scripts/t10_4c_tier3.py --branch sante --only autoencoder
  python scripts/t10_4c_tier3.py --branch auto --pu-threshold 0.85
"""
from __future__ import annotations

import argparse
import time

import numpy as np
import pandas as pd

from _ml_common import (
    LABEL_COL,
    MODELS_DIR,
    NORMAL_VAL,
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

OUT_FILE = "t10_4c_tier3_results.json"

# Colonnes susceptibles de porter un signal RCA de confiance (selon dataset)
RCA_CONF_COLS = ["Cause_Racine_RCA", "Severite_Anomalie", "Validee_Par_Auditeur"]


def _persist(model: object, branch: str, key: str) -> None:
    import joblib

    out_dir = MODELS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, out_dir / f"{key}_model.joblib")
    log.info("  Modèle persisté : %s_model.joblib", key)


# ─── AutoEncoder [Hawkins2002, An2015] ───────────────────────────────────────

def train_autoencoder(X_train, X_test, y_test, contamination, branch) -> dict | None:
    try:
        from pyod.models.auto_encoder_torch import AutoEncoder
    except ImportError as exc:
        log.warning("  PyOD AutoEncoderTorch indisponible : %s", exc)
        return None

    from sklearn.preprocessing import StandardScaler
    n_feat = X_train.shape[1]
    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X_train).astype(np.float32)
    X_te = scaler.transform(X_test).astype(np.float32)
    # Protège contre std=0 (features constantes — cas Santé)
    X_tr = np.nan_to_num(X_tr, nan=0.0, posinf=0.0, neginf=0.0)
    X_te = np.nan_to_num(X_te, nan=0.0, posinf=0.0, neginf=0.0)
    model = AutoEncoder(
        hidden_neurons=[max(8, n_feat // 2), max(4, n_feat // 4)],
        epochs=30,
        batch_size=256,
        contamination=contamination,
        preprocessing=False,   # normalisation gérée manuellement
        device="cpu",
    )
    model.fit(X_tr)
    scores = model.decision_function(X_te) # erreur de reconstruction
    y_pred = model.predict(X_te)
    metrics = compute_metrics(y_test, y_pred, scores)
    metrics["epochs"] = 30
    metrics["explainability"] = "reconstruction_error_per_feature"
    _persist(model, branch, "autoencoder")
    return {"algo": "AutoEncoder", "metrics": metrics, "model_key": "autoencoder"}


# ─── PU Learning [Elkan2008] ─────────────────────────────────────────────────

def _build_positive_mask(df: pd.DataFrame, threshold: float) -> np.ndarray:
    """
    Construit l'ensemble P (positifs fiables) depuis les colonnes RCA.

    Heuristique robuste : un dossier est P si (a) il est labellisé anomalie ET
    (b) il porte un signal RCA fort (cause racine renseignée, sévérité haute,
    ou validation auditeur). Le 'threshold' module la sévérité retenue.
    Retourne un masque booléen aligné sur df.
    """
    is_anom = (df[LABEL_COL] != NORMAL_VAL).to_numpy()
    signal = np.zeros(len(df), dtype=bool)

    if "Validee_Par_Auditeur" in df.columns:
        signal |= df["Validee_Par_Auditeur"].fillna(False).astype(bool).to_numpy()
    if "Cause_Racine_RCA" in df.columns:
        signal |= df["Cause_Racine_RCA"].notna().to_numpy()
    if "Severite_Anomalie" in df.columns:
        sev = df["Severite_Anomalie"].astype(str).str.lower()
        strong = sev.isin(["haute", "high", "critique", "critical"])
        # threshold élevé → on n'exige la sévérité forte qu'au-delà de 0.8
        signal |= strong.to_numpy() if threshold >= 0.8 else df["Severite_Anomalie"].notna().to_numpy()

    return is_anom & signal


def train_pu_learning(
    df_train, X_train, X_test, y_test, threshold, branch
) -> dict | None:
    from sklearn.ensemble import RandomForestClassifier

    pos_mask = _build_positive_mask(df_train, threshold)
    n_pos = int(pos_mask.sum())
    log.info("  Ensemble P (RCA conf ≥ %.2f) : %d dossiers", threshold, n_pos)
    if n_pos < 50:
        log.warning("  P trop petit (%d < 50) — PU Learning non fiable, skip.", n_pos)
        return None

    # Étiquetage PU : P = 1 (positif fiable), reste = 0 (non-labellisé traité négatif)
    s = pos_mask.astype(int)

    # Held-out de P pour estimer c = P(s=1 | y=1) [Elkan2008 §3]
    rng = np.random.default_rng(RANDOM_STATE)
    pos_idx = np.where(pos_mask)[0]
    rng.shuffle(pos_idx)
    cut = int(0.8 * len(pos_idx))
    train_pos, hold_pos = pos_idx[:cut], pos_idx[cut:]

    s_fit = s.copy()
    s_fit[hold_pos] = 0  # on cache une partie des positifs pour estimer c

    clf = RandomForestClassifier(
        n_estimators=300, max_depth=None, n_jobs=-1,
        class_weight="balanced", random_state=RANDOM_STATE,
    )
    clf.fit(X_train, s_fit)

    # c = proba moyenne prédite sur les positifs tenus à l'écart
    proba_hold = clf.predict_proba(X_train[hold_pos])[:, 1]
    c = float(np.clip(proba_hold.mean(), 1e-3, 1.0))
    log.info("  Facteur de correction c = %.4f [Elkan2008]", c)

    # Score corrigé sur le test : P(y=1|x) ≈ P(s=1|x) / c
    proba_test = clf.predict_proba(X_test)[:, 1] / c
    scores = np.clip(proba_test, 0.0, 1.0)
    # Seuil de décision : taux d'anomalie réel du test (calibrage opérationnel)
    tau = float(np.quantile(scores, 1.0 - y_test.mean()))
    y_pred = (scores >= tau).astype(int)

    metrics = compute_metrics(y_test, y_pred, scores)
    metrics["n_positifs"] = n_pos
    metrics["correction_c"] = round(c, 4)
    metrics["rca_threshold"] = threshold
    metrics["explainability"] = "shap_tree_explainer"  # RF → compatible SHAP
    _persist(clf, branch, "pu_rf")
    return {"algo": "PU_Learning_RF", "metrics": metrics, "model_key": "pu_rf"}


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MAKORA T10.4c — Tier 3 : AutoEncoder + PU Learning"
    )
    p.add_argument("--branch", choices=["sante", "auto"], required=True)
    p.add_argument("--timeout", type=int, default=0,
                   help="Budget temps PAR modèle en secondes (0 = illimité).")
    p.add_argument("--pu-threshold", type=float, default=0.80,
                   help="Seuil de sévérité RCA pour constituer l'ensemble P.")
    p.add_argument("--only", nargs="+", default=None,
                   choices=["autoencoder", "pu"], help="N'exécuter que ces modèles.")
    p.add_argument("--skip", nargs="+", default=[],
                   choices=["autoencoder", "pu"], help="Exclure ces modèles.")
    return p.parse_args()


def main() -> None:
    setup_logging()
    args = parse_args()
    branch = args.branch
    SEP = "─" * 60

    log.info(SEP)
    log.info("MAKORA — T10.4c Tier 3 [%s]", branch.upper())
    if args.timeout:
        log.info("Timeout par modèle : %ds", args.timeout)
    log.info(SEP)

    df_train, _, df_test = load_splits(branch, need_val=False)
    df_train, feats = apply_module(df_train, branch)
    df_test, _ = apply_module(df_test, branch)

    X_train, _ = get_xy(df_train, feats)
    X_test, y_test = get_xy(df_test, feats)
    log.info("Matrice features : train=%s | test=%s", X_train.shape, X_test.shape)

    contamination = load_best_contamination(branch)

    runners = {
        "autoencoder": ("AutoEncoder", lambda: train_autoencoder(
            X_train, X_test, y_test, contamination, branch)),
        "pu": ("PU_Learning_RF", lambda: train_pu_learning(
            df_train, X_train, X_test, y_test, args.pu_threshold, branch)),
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
    log.info("T10.4c terminé en %.1fs — résultats : results/%s/%s",
             time.perf_counter() - t_start, branch, OUT_FILE)
    print_summary(results)


if __name__ == "__main__":
    main()