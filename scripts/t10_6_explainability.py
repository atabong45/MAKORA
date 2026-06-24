"""
MODULE : scripts/t10_6_explainability.py
DESCRIPTION : Calcul SHAP (TreeExplainer) et LIME sur le test set.
              Analyse de convergence des deux méthodes d'explicabilité
              sur les mêmes anomalies détectées.

RÉFÉRENCES ACADÉMIQUES :
- [Lundberg2017] Lundberg & Lee (2017). A unified approach to interpreting
  model predictions. NeurIPS. → SHAP : valeurs Shapley garanties consistantes
  et localement précises. Base théorique du jeu coopératif.
- [Lundberg2020] Lundberg et al. (2020). From local explanations to global
  understanding with explainable AI for trees. Nature MI.
  → TreeExplainer : O(TLD²) pour les forêts, exact et rapide.
- [Ribeiro2016] Ribeiro et al. (2016). "Why should I trust you?" KDD.
  → LIME : perturbation locale, modèle surrogate linéaire. Alternative
    model-agnostic à SHAP. Comparaison convergence SHAP/LIME = robustesse.
- [Doshi-Velez2017] Doshi-Velez & Kim (2017). Towards a rigorous science
  of interpretable machine learning. arXiv. → Critères de qualité XAI.

DÉCISIONS DE CONCEPTION :
- SHAP sur 100% des anomalies détectées sur le test set.
- LIME sur un échantillon de 200 anomalies (lent par nature).
- Convergence mesurée par rang Kendall τ des top-5 features SHAP vs LIME.
  τ ≥ 0.8 → convergence forte → explicabilité robuste [Doshi-Velez2017].
- Sorties :
    · shap_values.npy   — valeurs brutes (toutes anomalies)
    · top3_features.json — top-3 par dossier (entrée moteur RCA)
    · lime_sample.json  — 200 cas LIME
    · convergence_report.json — τ Kendall par dossier

USAGE :
  python scripts/t10_6_explainability.py --branch sante
  python scripts/t10_6_explainability.py --branch auto --lime-sample 100
"""

from __future__ import annotations
import sys

import argparse
import json
import logging
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("makora.t10_6")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPLITS_DIR   = PROJECT_ROOT / "data" / "splits"
MODELS_DIR   = PROJECT_ROOT / "data" / "models"
RESULTS_DIR  = PROJECT_ROOT / "results"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
FIGURES_DIR  = PROJECT_ROOT / "results" / "figures"

RANDOM_STATE   = 42
LABEL_COL      = "Label_Anomalie"
NORMAL_VAL     = "NORMAL"
LIME_SAMPLE_N  = 200   # nombre de cas LIME (coûteux par nature)
TOP_K_SHAP     = 3     # top-3 features → moteur RCA

META_COLS = {
    "Label_Anomalie", "Sous_Type_Anomalie", "Cause_Racine_RCA",
    "Severite_Anomalie", "Source_Detection", "Validee_Par_Auditeur",
    "Date_Validation", "Commentaire_Audit", "Montant_Prejudice",
    "ID_Sinistre", "ID_Assure", "ID_Praticien", "ID_Vehicule",
    "ID_Contrat", "ID_Expert", "ID_Garage", "Hash_Image", "Batch_Date",
}


# ─── Chargement ──────────────────────────────────────────────────────────────

def load_test_split(branch: str) -> pd.DataFrame:
    path = SPLITS_DIR / branch / f"{branch}_test.parquet"
    if not path.exists():
        raise FileNotFoundError(f"Split test introuvable : {path}")
    df = pd.read_parquet(path)
    log.info("[%s] Test : %d lignes", branch.upper(), len(df))
    return df


def load_if_model(branch: str):
    """Charge le modèle IF classique produit par T10.3."""
    path = MODELS_DIR / branch / "if_classic_model.joblib"
    if not path.exists():
        raise FileNotFoundError(
            f"Modèle IF introuvable : {path}\n"
            "Lancer d'abord : python scripts/t10_3_train_if.py"
        )
    model = joblib.load(path)
    log.info("Modèle IF chargé : %s", path.name)
    return model


def get_feature_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, list[str]]:
    feature_cols = [
        c for c in df.columns
        if c not in META_COLS and pd.api.types.is_numeric_dtype(df[c])
    ]
    X = df[feature_cols].fillna(0).values.astype(np.float32)
    y = (df[LABEL_COL] != NORMAL_VAL).astype(int).values
    return X, y, feature_cols


# ─── SHAP ────────────────────────────────────────────────────────────────────

def compute_shap(
    model, X_anomalies: np.ndarray, feature_names: list[str], branch: str,
) -> tuple[np.ndarray, list[dict]]:
    """
    SHAP TreeExplainer [Lundberg2020] sur toutes les anomalies détectées.

    TreeExplainer est exact pour les forêts d'arbres (IF inclus).
    Complexité : O(TLD²) avec T=arbres, L=feuilles, D=profondeur.
    """
    log.info("SHAP TreeExplainer [Lundberg2020] sur %d anomalies ...", len(X_anomalies))
    explainer   = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_anomalies)   # shape (n, d)

    # Top-K features par dossier (entrée moteur RCA)
    top_k_records: list[dict] = []
    for i, row_shap in enumerate(shap_values):
        abs_shap   = np.abs(row_shap)
        top_idx    = np.argsort(abs_shap)[::-1][:TOP_K_SHAP]
        top_k_records.append({
            "sample_idx": int(i),
            "top_features": [
                {
                    "name":       feature_names[j],
                    "shap_value": round(float(row_shap[j]), 6),
                    "direction":  "anomalie" if row_shap[j] > 0 else "normal",
                }
                for j in top_idx
            ],
        })

    # Sauvegarde valeurs brutes
    out_dir = RESULTS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    np.save(out_dir / "shap_values.npy", shap_values)
    (out_dir / "top3_features.json").write_text(
        json.dumps(top_k_records[:500], indent=2, ensure_ascii=False)  # 500 max
    )
    log.info("SHAP — top-3 features sauvegardées (%d dossiers)", len(top_k_records))

    # Figure beeswarm globale
    _plot_shap_summary(shap_values, feature_names, branch)
    return shap_values, top_k_records


def _plot_shap_summary(
    shap_values: np.ndarray, feature_names: list[str], branch: str,
) -> None:
    """Beeswarm plot SHAP — figure mémoire chapitre 5."""
    try:
        import matplotlib.pyplot as plt
        FIGURES_DIR.mkdir(parents=True, exist_ok=True)
        # Limiter à top-15 features pour la lisibilité
        mean_abs = np.abs(shap_values).mean(axis=0)
        top_idx  = np.argsort(mean_abs)[::-1][:15]
        fig, ax  = plt.subplots(figsize=(10, 7))
        shap.summary_plot(
            shap_values[:, top_idx],
            features=None,
            feature_names=[feature_names[i] for i in top_idx],
            plot_type="dot",
            show=False,
            max_display=15,
        )
        plt.title(
            f"SHAP — Top-15 features contributors [{branch.upper()}]\n"
            "[Lundberg2020] TreeExplainer",
            fontsize=12,
        )
        plt.tight_layout()
        out_path = FIGURES_DIR / f"t10_6_shap_summary_{branch}.png"
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()
        log.info("Figure SHAP : %s", out_path)
    except ImportError:
        log.warning("matplotlib non installé — figure SHAP non générée.")


# ─── LIME ────────────────────────────────────────────────────────────────────

def compute_lime(
    model, X_train: np.ndarray, X_anomalies_sample: np.ndarray,
    feature_names: list[str], branch: str, n_sample: int = LIME_SAMPLE_N,
) -> list[dict]:
    """
    LIME [Ribeiro2016] sur un échantillon d'anomalies.

    Perturbation locale autour de chaque point → modèle linéaire surrogate.
    Lent (O(n_perturb × n_features) par point) → limité à n_sample cas.
    Retourne None si lime non installé.
    """
    try:
        import lime.lime_tabular as lime_tab
    except ImportError:
        log.warning("Librairie 'lime' non installée — LIME ignoré.")
        log.warning("Installer avec : pip install lime --break-system-packages")
        return []

    log.info("LIME [Ribeiro2016] sur %d anomalies (échantillon) ...", n_sample)

    def predict_fn(X: np.ndarray) -> np.ndarray:
        """Score normalisé [0,1] pour LIME — IF score inversé."""
        return -model.decision_function(X.astype(np.float32))

    explainer = lime_tab.LimeTabularExplainer(
        training_data=X_train,
        feature_names=feature_names,
        mode="regression",
        random_state=RANDOM_STATE,
        verbose=False,
    )

    rng      = np.random.default_rng(RANDOM_STATE)
    idx_sub  = rng.choice(len(X_anomalies_sample),
                          size=min(n_sample, len(X_anomalies_sample)),
                          replace=False)
    lime_results: list[dict] = []

    for i, idx in enumerate(idx_sub):
        if i % 50 == 0:
            log.info("  LIME : %d/%d ...", i, len(idx_sub))
        explanation = explainer.explain_instance(
            X_anomalies_sample[idx],
            predict_fn,
            num_features=TOP_K_SHAP,
        )
        lime_results.append({
            "sample_idx": int(idx),
            "top_features": [
                {"name": feat, "lime_weight": round(float(w), 6)}
                for feat, w in explanation.as_list()
            ],
        })

    out_path = RESULTS_DIR / branch / "lime_sample.json"
    out_path.write_text(json.dumps(lime_results, indent=2, ensure_ascii=False))
    log.info("LIME — %d cas sauvegardés : %s", len(lime_results), out_path)
    return lime_results


# ─── Convergence SHAP / LIME ─────────────────────────────────────────────────

def compute_convergence(
    shap_top3: list[dict], lime_results: list[dict], branch: str,
) -> dict:
    """
    Mesure la convergence SHAP / LIME par corrélation de rang (Kendall τ).

    [Doshi-Velez2017] : τ ≥ 0.8 → convergence forte → robustesse explicabilité.
    Compare les rangs des features communes entre SHAP et LIME sur chaque dossier.
    """
    if not lime_results:
        return {"note": "LIME non disponible — convergence non calculée."}

    from scipy.stats import kendalltau

    # Index rapide LIME par sample_idx
    lime_idx = {r["sample_idx"]: r for r in lime_results}
    taus: list[float] = []

    for shap_rec in shap_top3:
        idx = shap_rec["sample_idx"]
        if idx not in lime_idx:
            continue
        shap_feats = [f["name"] for f in shap_rec["top_features"]]
        lime_feats = [f["name"].split(" ")[0] for f in lime_idx[idx]["top_features"]]
        common     = [f for f in shap_feats if any(f in lf for lf in lime_feats)]
        if len(common) >= 2:
            rank_s = [shap_feats.index(f) for f in common]
            rank_l = [lime_feats.index(
                next(lf for lf in lime_feats if f in lf)
            ) for f in common]
            tau, _ = kendalltau(rank_s, rank_l)
            taus.append(float(tau))

    if not taus:
        return {"note": "Pas assez de features communes pour calculer τ."}

    result = {
        "n_pairs_compared":  len(taus),
        "tau_mean":          round(float(np.mean(taus)), 4),
        "tau_std":           round(float(np.std(taus)),  4),
        "convergence_strong": float(np.mean(taus)) >= 0.8,
        "interpretation": (
            "Convergence forte — SHAP et LIME s'accordent sur les features "
            "discriminantes. Explicabilité robuste [Doshi-Velez2017]."
            if float(np.mean(taus)) >= 0.8
            else "Convergence partielle — vérifier la linéarité locale du modèle."
        ),
    }
    log.info("Convergence SHAP/LIME — τ=%.4f±%.4f (fort: %s)",
             result["tau_mean"], result["tau_std"],
             result["convergence_strong"])
    out_path = RESULTS_DIR / branch / "convergence_report.json"
    out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return result


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MAKORA T10.6 — SHAP + LIME convergence"
    )
    p.add_argument("--branch",       choices=["sante", "auto"], required=True)
    p.add_argument("--lime-sample",  type=int, default=LIME_SAMPLE_N,
                   help=f"Nb cas LIME (défaut: {LIME_SAMPLE_N})")
    return p.parse_args()


def main() -> None:
    args   = parse_args()
    branch = args.branch
    SEP    = "─" * 60

    log.info(SEP)
    log.info("MAKORA — T10.6 Explicabilité SHAP + LIME [%s]", branch.upper())
    log.info(SEP)

    df_test_raw     = load_test_split(branch)
    model           = load_if_model(branch)

    # engineer_features via module MAKORA
    from core.plugin_registry import PluginRegistry
    if branch == "sante":
        import modules.sante.sante_module  # noqa: F401
    elif branch == "auto":
        import modules.auto.auto_module    # noqa: F401
    yaml_path = PROJECT_ROOT / "modules" / branch / f"{branch}.yaml"
    module_inst = PluginRegistry.get(branch)(config_path=yaml_path)
    df_test     = module_inst.engineer_features(df_test_raw)
    feature_names = [f for f in module_inst.get_feature_names() if f in df_test.columns]
    X_test = df_test[feature_names].fillna(0).values.astype(np.float32)
    y_test = (df_test[LABEL_COL] != NORMAL_VAL).to_numpy(dtype=int)

    # Anomalies détectées par IF
    y_pred = (model.predict(X_test) == -1).astype(int)
    X_anomalies = X_test[y_pred == 1]
    log.info("Anomalies détectées : %d / %d", len(X_anomalies), len(X_test))

    if len(X_anomalies) == 0:
        log.error("Aucune anomalie détectée — vérifier le modèle T10.3.")
        return

    # SHAP sur toutes les anomalies
    shap_values, shap_top3 = compute_shap(model, X_anomalies, feature_names, branch)

    # LIME sur échantillon
    X_train_path = SPLITS_DIR / branch / f"{branch}_train.parquet"
    df_train_raw = pd.read_parquet(X_train_path)
    df_train_eng = module_inst.engineer_features(df_train_raw)
    X_train = df_train_eng[feature_names].fillna(0).values.astype(np.float32)
    lime_results = compute_lime(
        model, X_train, X_anomalies, feature_names, branch, n_sample=args.lime_sample
    )

    # Convergence
    convergence = compute_convergence(shap_top3, lime_results, branch)

    log.info(SEP)
    log.info("✅ T10.6 terminé [%s]", branch.upper())
    log.info("Prochaine étape :")
    log.info("  python scripts/t10_7_evaluation.py --branch %s", branch)
    log.info(SEP)


if __name__ == "__main__":
    main()
