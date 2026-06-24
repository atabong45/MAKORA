"""
MODULE : scripts/t10_5_learning_curves.py
DESCRIPTION : Learning curves de l'Isolation Forest sur les deux branches.
              Mesure AUC-ROC et F1 en fonction de la taille du train set.

RÉFÉRENCES ACADÉMIQUES :
- [Ng2012] Ng, A. (2012). Advice for applying machine learning.
  Stanford CS229 lecture notes. → Référence canonique pour l'interprétation
  des learning curves : convergence → pas de high-bias, écart → high-variance.
- [Liu2008] Liu et al. (2008). Isolation Forest. ICDM.
  → Si IF converge rapidement avec peu de données, argument fort pour
    le déploiement en contexte africain où les données historiques sont rares.
- [Chandola2009] Chandola et al. (2009). Anomaly Detection: A Survey.
  ACM Computing Surveys. → Contexte : la détection non-supervisée est
  particulièrement sensible à la taille du train set (pas de labels).

DÉCISIONS DE CONCEPTION :
- Train sizes : [2000, 5000, 10000, 25000, 50000, 75000, 100000] puis max.
  Bornes basses à 2000 lignes pour avoir au moins ~160 anomalies (8%).
- 5 répétitions par taille (subsampling aléatoire) → IC empiriques.
  Réduit la variance due au subsampling aléatoire [Ng2012].
- Contamination issue de T10.3 (optimale) — pas recalibréé ici.
- Sorties : JSON + PNG (matplotlib) — la figure PNG est directement
  utilisable dans le mémoire (Chapitre 5, section résultats).

USAGE :
  python scripts/t10_5_learning_curves.py --branch sante
  python scripts/t10_5_learning_curves.py --branch auto
  python scripts/t10_5_learning_curves.py --branch sante --no-plot
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
from sklearn.ensemble import IsolationForest
from sklearn.metrics import f1_score, roc_auc_score
from sklearn.utils import resample

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("makora.t10_5")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPLITS_DIR   = PROJECT_ROOT / "data" / "splits"
MODELS_DIR   = PROJECT_ROOT / "data" / "models"
RESULTS_DIR  = PROJECT_ROOT / "results"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
FIGURES_DIR  = PROJECT_ROOT / "results" / "figures"

RANDOM_STATE = 42
LABEL_COL    = "Label_Anomalie"
NORMAL_VAL   = "NORMAL"
N_REPEATS    = 5      # répétitions par taille → IC empiriques [Ng2012]

# [Ng2012] : couvrir de 1.5% à 100% du train set pour voir la courbe complète
TRAIN_SIZES = [2_000, 5_000, 10_000, 25_000, 50_000, 75_000, 100_000]

META_COLS = {
    "Label_Anomalie", "Sous_Type_Anomalie", "Cause_Racine_RCA",
    "Severite_Anomalie", "Source_Detection", "Validee_Par_Auditeur",
    "Date_Validation", "Commentaire_Audit", "Montant_Prejudice",
    "ID_Sinistre", "ID_Assure", "ID_Praticien", "ID_Vehicule",
    "ID_Contrat", "ID_Expert", "ID_Garage", "Hash_Image", "Batch_Date",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_splits(branch: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Charge train et test — val non utilisé ici (pas de tuning)."""
    branch_dir = SPLITS_DIR / branch
    paths = {
        s: branch_dir / f"{branch}_{s}.parquet"
        for s in ("train", "test")
    }
    for s, p in paths.items():
        if not p.exists():
            raise FileNotFoundError(
                f"Split '{s}' introuvable : {p}\n"
                "Lancer d'abord : python scripts/t10_2_split.py"
            )
    df_train = pd.read_parquet(paths["train"])
    df_test  = pd.read_parquet(paths["test"])
    log.info("[%s] train=%d, test=%d", branch.upper(), len(df_train), len(df_test))
    return df_train, df_test


def get_feature_matrix(df: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    feature_cols = [
        c for c in df.columns
        if c not in META_COLS and pd.api.types.is_numeric_dtype(df[c])
    ]
    X = df[feature_cols].fillna(0).values.astype(np.float32)
    y = (df[LABEL_COL] != NORMAL_VAL).astype(int).values
    return X, y


def load_best_contamination(branch: str) -> float:
    """Récupère la contamination optimale depuis T10.3."""
    path = RESULTS_DIR / branch / "t10_3_if_results.json"
    if path.exists():
        data = json.loads(path.read_text())
        for entry in data:
            if entry.get("algo") == "IsolationForest":
                c = entry.get("metrics", {}).get("contamination", 0.08)
                log.info("Contamination issue de T10.3 : %.2f", c)
                return float(c)
    log.info("T10.3 non trouvé — contamination par défaut : 0.08 [Bauder2017]")
    return 0.08


# ─── Calcul des learning curves ──────────────────────────────────────────────

def compute_lc_point(
    X_train_full: np.ndarray, y_train_full: np.ndarray,
    X_test: np.ndarray, y_test: np.ndarray,
    n_train: int, contamination: float,
) -> dict:
    """
    Calcule AUC et F1 pour une taille de train donnée.

    N_REPEATS subsamples aléatoires → mean ± std (IC empiriques).
    Préserve la stratification : ~8% d'anomalies dans chaque subsample.
    """
    auc_list, f1_list = [], []
    rng = np.random.default_rng(RANDOM_STATE)

    n_anom   = int(n_train * contamination)
    n_normal = n_train - n_anom

    idx_anom   = np.where(y_train_full == 1)[0]
    idx_normal = np.where(y_train_full == 0)[0]

    # Si pas assez d'anomalies ou de normaux → skip
    if len(idx_anom) < n_anom or len(idx_normal) < n_normal:
        log.warning("  n_train=%d : pas assez de données stratifiées — skip.", n_train)
        return {}

    for rep in range(N_REPEATS):
        seed = RANDOM_STATE + rep
        chosen_anom   = rng.choice(idx_anom,   size=n_anom,   replace=False)
        chosen_normal = rng.choice(idx_normal, size=n_normal, replace=False)
        idx_sub = np.concatenate([chosen_anom, chosen_normal])
        rng.shuffle(idx_sub)

        X_sub = X_train_full[idx_sub]

        model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            max_samples="auto",
            random_state=seed,
            n_jobs=-1,
        )
        model.fit(X_sub)

        scores = -model.decision_function(X_test)
        y_pred = (model.predict(X_test) == -1).astype(int)

        auc_list.append(float(roc_auc_score(y_test, scores)))
        f1_list.append(float(f1_score(y_test, y_pred, zero_division=0)))

    return {
        "n_train":    n_train,
        "auc_mean":   round(float(np.mean(auc_list)), 4),
        "auc_std":    round(float(np.std(auc_list)),  4),
        "f1_mean":    round(float(np.mean(f1_list)),  4),
        "f1_std":     round(float(np.std(f1_list)),   4),
        "n_repeats":  N_REPEATS,
    }


def run_learning_curves(
    X_train: np.ndarray, y_train: np.ndarray,
    X_test: np.ndarray,  y_test: np.ndarray,
    contamination: float, branch: str,
) -> list[dict]:
    """
    Exécute les learning curves sur toutes les tailles configurées.
    Ajoute automatiquement la taille complète (n_train_full).
    """
    sizes = [s for s in TRAIN_SIZES if s < len(X_train)]
    sizes.append(len(X_train))   # point final = 100% du train set

    log.info("Tailles de train à évaluer : %s", sizes)
    log.info("Répétitions par taille : %d", N_REPEATS)
    log.info("Test set (fixe) : %d lignes", len(X_test))

    results = []
    for i, n in enumerate(sizes):
        log.info("[%d/%d] n_train=%d ...", i + 1, len(sizes), n)
        point = compute_lc_point(X_train, y_train, X_test, y_test, n, contamination)
        if point:
            results.append(point)
            log.info(
                "  AUC=%.4f±%.4f | F1=%.4f±%.4f",
                point["auc_mean"], point["auc_std"],
                point["f1_mean"],  point["f1_std"],
            )
    return results


# ─── Visualisation ───────────────────────────────────────────────────────────

def plot_learning_curves(results: list[dict], branch: str) -> Path | None:
    """
    Génère la figure learning curves (AUC + F1 vs n_train).
    Figure directement utilisable dans le mémoire.
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib.ticker as mticker
    except ImportError:
        log.warning("matplotlib non installé — figure non générée.")
        return None

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    fig.suptitle(
        f"Learning Curves — Isolation Forest [{branch.upper()}]\n"
        f"[Liu2008] — {N_REPEATS} répétitions par taille, IC empirique (±1σ)",
        fontsize=13,
    )

    xs      = [r["n_train"] for r in results]
    colors  = {"auc": "#2E75B6", "f1": "#C0392B"}

    for ax, metric, label in [
        (axes[0], "auc", "AUC-ROC"),
        (axes[1], "f1",  "F1-score"),
    ]:
        means = np.array([r[f"{metric}_mean"] for r in results])
        stds  = np.array([r[f"{metric}_std"]  for r in results])
        ax.plot(xs, means, "o-", color=colors[metric], linewidth=2, label=label)
        ax.fill_between(xs, means - stds, means + stds,
                        alpha=0.2, color=colors[metric], label="±1σ")
        ax.set_xlabel("Taille du train set (n lignes)", fontsize=11)
        ax.set_ylabel(label, fontsize=11)
        ax.set_title(label, fontsize=12)
        ax.set_ylim(0, 1.05)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(
            lambda x, _: f"{int(x/1000)}k"
        ))
        ax.legend(fontsize=10)

        # Annotation point de convergence (premier point où Δ < 0.01)
        for i in range(1, len(means)):
            if abs(means[i] - means[i - 1]) < 0.01:
                ax.axvline(xs[i], color="gray", linestyle=":", alpha=0.6)
                ax.text(xs[i], 0.05, f"≈conv.\n{xs[i]//1000}k",
                        fontsize=8, ha="center", color="gray")
                break

    plt.tight_layout()
    out_path = FIGURES_DIR / f"t10_5_learning_curves_{branch}.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info("Figure sauvegardée : %s", out_path)
    return out_path


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MAKORA T10.5 — Learning curves Isolation Forest"
    )
    p.add_argument("--branch",  choices=["sante", "auto"], required=True)
    p.add_argument("--no-plot", action="store_true", help="Pas de figure matplotlib")
    return p.parse_args()


def main() -> None:
    args   = parse_args()
    branch = args.branch
    SEP    = "─" * 60

    log.info(SEP)
    log.info("MAKORA — T10.5 Learning Curves [%s]", branch.upper())
    log.info(SEP)

    df_train, df_test   = load_splits(branch)

    # engineer_features via module MAKORA
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

    # Surcharge get_feature_matrix pour utiliser les features métier
    def _get_fm(df):
        X = df[feats].fillna(0).values.astype(np.float32)
        y = (df[LABEL_COL] != NORMAL_VAL).to_numpy(dtype=int)
        return X, y

    X_train, y_train    = _get_fm(df_train)
    X_test,  y_test     = _get_fm(df_test)
    contamination       = load_best_contamination(branch)

    results = run_learning_curves(
        X_train, y_train, X_test, y_test, contamination, branch
    )

    # Sauvegarde JSON
    out_dir = RESULTS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "t10_5_learning_curves.json"
    json_path.write_text(json.dumps(
        {"branch": branch, "contamination": contamination, "points": results},
        indent=2, ensure_ascii=False,
    ))
    log.info("Résultats JSON : %s", json_path)

    # Figure
    if not args.no_plot:
        plot_learning_curves(results, branch)

    log.info(SEP)
    log.info("✅ T10.5 terminé [%s]", branch.upper())
    log.info("Prochaine étape :")
    log.info("  python scripts/t10_6_explainability.py --branch %s", branch)
    log.info(SEP)


if __name__ == "__main__":
    main()
