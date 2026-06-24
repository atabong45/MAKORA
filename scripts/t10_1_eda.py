"""
MODULE : scripts/t10_1_eda.py
DESCRIPTION : Analyse Exploratoire des Données (EDA) — Phase T10.1
              Vérifie que les anomalies injectées créent un signal
              détectable dans l'espace des features calculées.

RÉFÉRENCES :
- [Chandola2009] ACM Computing Surveys — vérification préalable du signal.
- [Goldstein2016] PLOS ONE — EDA sur features d'anomalies hétérogènes.
- [Bauder2017] ICMLA — distributions features fraude assurance.
- [Sculley2015] NeurIPS — features à vérifier avant entraînement.

USAGE :
  python scripts/t10_1_eda.py --branch sante
  python scripts/t10_1_eda.py --branch auto --sample 50000

SORTIES dans results/{branch}/ :
  eda_overview.json · eda_distributions.png · eda_correlation.png
  eda_pca.png · eda_signal_heatmap.png · eda_signal_report.json · eda_report.md
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import Patch
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR  = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SCRIPTS_DIR))

from core.plugin_registry import PluginRegistry
import modules.sante.sante_module  # noqa: F401 — déclenche @register("sante")
import modules.auto.auto_module    # noqa: F401 — déclenche @register("auto")

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
                    datefmt="%H:%M:%S")
log = logging.getLogger("makora.eda")

RANDOM_STATE = 42
FIGURE_DPI   = 200
CAT_ORDER    = ["NORMAL", "FRAUDE", "ERREUR_OP", "BIAIS", "TECHNIQUE"]
CAT_PALETTE  = {
    "NORMAL": "#4A5568", "FRAUDE": "#C53030",
    "ERREUR_OP": "#B7791F", "BIAIS": "#2B6CB0", "TECHNIQUE": "#553C9A",
}
DEFAULT_PATHS: dict[str, Path] = {
    "sante": PROJECT_ROOT / "data" / "processed" / "sante" / "dataset_sante_v1.parquet",
    "auto":  PROJECT_ROOT / "data" / "processed" / "auto"  / "dataset_auto_v1.parquet",
}


@dataclass
class EDAConfig:
    branch: str;  data_path: Path;  output_dir: Path
    sample_n: Optional[int] = None;  random_state: int = RANDOM_STATE
    def __post_init__(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)


def _is_binary(s: pd.Series) -> bool:
    """Retourne True si la série a ≤ 3 valeurs uniques (feature binaire/catégorielle basse cardinalité)."""
    return int(s.dropna().nunique()) <= 3

# ─── Chargement ──────────────────────────────────────────────────────────

def load_dataset(cfg: EDAConfig) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """
    Charge le dataset, appelle engineer_features() via Plugin Contract.
    [Chandola2009] : vérifier le signal sur les features exactes du modèle.
    """
    if not cfg.data_path.exists():
        raise FileNotFoundError(f"Dataset introuvable : {cfg.data_path}")
    log.info("Chargement : %s", cfg.data_path)
    df = (pd.read_parquet(cfg.data_path) if cfg.data_path.suffix == ".parquet"
          else pd.read_csv(cfg.data_path, low_memory=False))
    log.info("Dimensions : %d × %d", *df.shape)

    if cfg.sample_n and cfg.sample_n < len(df):
        rng = np.random.default_rng(cfg.random_state)
        n_n = int(cfg.sample_n * 0.92)
        n_a = cfg.sample_n - n_n
        idx = np.concatenate([
            rng.choice(df.index[df["Label_Anomalie"] == "NORMAL"],
                       size=min(n_n, (df["Label_Anomalie"] == "NORMAL").sum()), replace=False),
            rng.choice(df.index[df["Label_Anomalie"] != "NORMAL"],
                       size=min(n_a, (df["Label_Anomalie"] != "NORMAL").sum()), replace=False),
        ])
        df = df.loc[idx].sample(frac=1, random_state=cfg.random_state)
        log.info("Échantillon stratifié : %d lignes", len(df))

    yaml_path = PROJECT_ROOT / "modules" / cfg.branch / f"{cfg.branch}.yaml"
    module = PluginRegistry.get(cfg.branch)(config_path=yaml_path)
    is_valid, errs = module.validate_input(df)
    if not is_valid:
        log.warning("validate_input — %d erreur(s) : %s", len(errs), errs[:3])

    df_enriched = module.engineer_features(df)
    features    = [f for f in module.get_feature_names() if f in df_enriched.columns]
    log.info("Features (%d) : %s", len(features), features)
    meta = ["Label_Anomalie", "Sous_Type_Anomalie"]
    return df_enriched, df_enriched[features + meta], features


# ─── Vue d'ensemble ───────────────────────────────────────────────────────

def compute_overview(df: pd.DataFrame, features: list[str]) -> dict:
    mask = df["Label_Anomalie"] != "NORMAL"
    out: dict = {
        "n_total": int(len(df)), "n_normal": int((~mask).sum()),
        "n_anomalie": int(mask.sum()), "taux_anomalie": round(float(mask.mean()), 4),
        "n_features": len(features),
        "categories": df["Label_Anomalie"].value_counts().to_dict(),
        "scenarios":  df.loc[mask, "Sous_Type_Anomalie"].value_counts().to_dict(),
        "features_stats": {},
    }
    for col in features:
        s = df[col].dropna()
        out["features_stats"][col] = {
            "dtype": str(df[col].dtype), "nan_pct": round(float(df[col].isna().mean()), 4),
            "n_unique": int(s.nunique()),
            "mean": round(float(s.mean()), 4) if len(s) else None,
            "std":  round(float(s.std()),  4) if len(s) > 1 else None,
            "min":  round(float(s.min()),  4) if len(s) else None,
            "max":  round(float(s.max()),  4) if len(s) else None,
        }
    return out


# ─── Distributions ────────────────────────────────────────────────────────

def plot_distributions(df: pd.DataFrame, features: list[str], cfg: EDAConfig) -> Path:
    """
    Violin plots (continues) et bar plots (binaires) par catégorie.
    [Goldstein2016] : analyse préalable pour identifier les features discriminantes.
    """
    sns.set_style("whitegrid")
    n_cols = min(3, len(features))
    n_rows = (len(features) + n_cols - 1) // n_cols
    fig, axes = plt.subplots(n_rows, n_cols, figsize=(16, n_rows * 3.8),
                              constrained_layout=True)
    axes_flat = axes.flatten() if len(features) > 1 else [axes]
    cats = [c for c in CAT_ORDER if c in df["Label_Anomalie"].unique()]
    palette = {c: CAT_PALETTE[c] for c in cats}

    for ax, feat in zip(axes_flat, features):
        sub = df[["Label_Anomalie", feat]].dropna()
        is_bin = sub[feat].dropna().nunique() <= 3

        if is_bin:
            rates = sub.groupby("Label_Anomalie")[feat].mean().reindex(cats).fillna(0)
            ax.bar(range(len(cats)), rates.values, color=[palette[c] for c in rates.index],
                   edgecolor="white", linewidth=0.8, width=0.65)
            ax.set_xticks(range(len(cats)))
            ax.set_xticklabels(cats, rotation=35, ha="right", fontsize=7)
            ax.set_ylim(0, 1.05); ax.set_ylabel("Taux d'activation", fontsize=8)
        else:
            parts = ax.violinplot([sub.loc[sub["Label_Anomalie"] == c, feat].values
                                   for c in cats],
                                  positions=range(len(cats)),
                                  showmedians=True, showextrema=False, widths=0.7)
            for pc, cat in zip(parts["bodies"], cats):
                pc.set_facecolor(palette[cat]); pc.set_alpha(0.72)
            parts["cmedians"].set_color("black"); parts["cmedians"].set_linewidth(1.5)
            ax.set_xticks(range(len(cats)))
            ax.set_xticklabels(cats, rotation=35, ha="right", fontsize=7)
            ax.set_ylabel("Valeur", fontsize=8)

        nan_pct = df[feat].isna().mean()
        ax.set_title(f"{feat}\n(NaN : {nan_pct:.1%})", fontsize=9, fontweight="bold")

    for ax in axes_flat[len(features):]: ax.set_visible(False)
    fig.legend(
        handles=[Patch(facecolor=palette[c], label=c, alpha=0.75) for c in cats],
        loc="lower center", ncol=len(cats), frameon=True, fontsize=9,
        bbox_to_anchor=(0.5, -0.015))
    fig.suptitle(
        f"MAKORA — Distributions features ML · {cfg.branch.upper()}\n"
        "[Goldstein2016] · NORMAL vs catégories d'anomalies",
        fontsize=11, fontweight="bold", y=1.01)
    out = cfg.output_dir / "eda_distributions.png"
    fig.savefig(out, dpi=FIGURE_DPI, bbox_inches="tight"); plt.close(fig)
    log.info("Distributions : %s", out); return out


# ─── Corrélation de Spearman ──────────────────────────────────────────────

def plot_correlation(df: pd.DataFrame, features: list[str], cfg: EDAConfig) -> Path:
    """
    Matrice de corrélation de Spearman. Spearman > Pearson car features
    incluent des indicateurs binaires non-gaussiens. [Goldstein2016]
    """
    imp = SimpleImputer(strategy="median")
    X_imp = pd.DataFrame(
        imp.fit_transform(df[features].dropna(how="all")), columns=features)
    corr = X_imp.corr(method="spearman")
    sz   = max(7, len(features) * 0.75)
    fig, ax = plt.subplots(figsize=(sz, sz * 0.9))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(corr, mask=mask, annot=True, fmt=".2f", cmap="RdBu_r",
                center=0, vmin=-1, vmax=1, square=True,
                linewidths=0.5, linecolor="white",
                cbar_kws={"shrink": 0.75, "label": "Spearman ρ"},
                ax=ax, annot_kws={"size": 8})
    high = [(features[i], features[j], round(float(corr.iloc[i, j]), 3))
            for i in range(len(features)) for j in range(i)
            if abs(corr.iloc[i, j]) > 0.85]
    ax.set_title(
        f"MAKORA — Corrélation de Spearman · {cfg.branch.upper()}\n"
        "Seuil ablation : |ρ| > 0.85 → candidat suppression (T10.4)",
        fontsize=10, fontweight="bold")
    ax.tick_params(axis="x", rotation=45, labelsize=8)
    ax.tick_params(axis="y", rotation=0,  labelsize=8)
    if high:
        note = "Paires > 0.85 : " + " | ".join(f"{a}↔{b}({v})" for a, b, v in high)
        fig.text(0.5, -0.02, note, ha="center", fontsize=7.5, color="#C53030")
    fig.tight_layout()
    out = cfg.output_dir / "eda_correlation.png"
    fig.savefig(out, dpi=FIGURE_DPI, bbox_inches="tight"); plt.close(fig)
    log.info("Corrélation : %s", out); return out


# ─── PCA + UMAP ───────────────────────────────────────────────────────────

def plot_pca_umap(df: pd.DataFrame, features: list[str], cfg: EDAConfig) -> Path:
    """Projection PCA 2D + UMAP 2D (optionnel) colorée par catégorie."""
    sub = df[features + ["Label_Anomalie"]].dropna(subset=features, how="all")
    X   = StandardScaler().fit_transform(
            SimpleImputer(strategy="median").fit_transform(sub[features].values))
    y   = sub["Label_Anomalie"].values
    cats = [c for c in CAT_ORDER if c in np.unique(y)]

    pca = PCA(n_components=2, random_state=RANDOM_STATE)
    X_pca = pca.fit_transform(X)
    var_e = pca.explained_variance_ratio_

    X_umap, umap_ok = None, False
    try:
        import umap as _umap
        X_umap = _umap.UMAP(n_components=2, n_neighbors=15,
                             random_state=RANDOM_STATE).fit_transform(X)
        umap_ok = True
    except ImportError:
        log.warning("umap-learn absent — UMAP ignoré (pip install umap-learn).")

    n_plots = 2 if umap_ok else 1
    fig, axes = plt.subplots(1, n_plots, figsize=(16 if umap_ok else 9, 7))
    if not umap_ok: axes = [axes]
    rng = np.random.default_rng(RANDOM_STATE)
    idx = rng.choice(len(X_pca), size=min(20_000, len(X_pca)), replace=False)

    plots_data = [(X_pca, f"PCA · PC1={var_e[0]:.1%} PC2={var_e[1]:.1%}")]
    if umap_ok: plots_data.append((X_umap, "UMAP · n_neighbors=15"))

    for ax, (X2d, title) in zip(axes, plots_data):
        for cat in cats:
            m = y[idx] == cat
            ax.scatter(X2d[idx][m, 0], X2d[idx][m, 1], c=CAT_PALETTE[cat],
                       s=4 if cat == "NORMAL" else 14,
                       alpha=0.28 if cat == "NORMAL" else 0.80,
                       label=f"{cat} (n={m.sum():,})",
                       zorder=1 if cat == "NORMAL" else 2, edgecolors="none")
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.set_xlabel("Dim 1", fontsize=9); ax.set_ylabel("Dim 2", fontsize=9)
        ax.legend(loc="best", fontsize=8, markerscale=3, framealpha=0.85)
        ax.tick_params(labelsize=8); sns.despine(ax=ax)

    fig.suptitle(
        f"MAKORA — Réduction dimensionnelle · {cfg.branch.upper()}\n"
        "Séparation NORMAL vs anomalies dans l'espace des features ML",
        fontsize=11, fontweight="bold")
    fig.tight_layout()
    out = cfg.output_dir / "eda_pca.png"
    fig.savefig(out, dpi=FIGURE_DPI, bbox_inches="tight"); plt.close(fig)
    log.info("PCA/UMAP : %s", out); return out


# ─── CLI + Main ───────────────────────────────────────────────────────────

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MAKORA T10.1 — EDA")
    p.add_argument("--branch", required=True, choices=["sante", "auto"])
    p.add_argument("--data-path",  type=Path, default=None)
    p.add_argument("--sample",     type=int,  default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def main() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    args = _parse_args()
    cfg  = EDAConfig(
        branch     = args.branch,
        data_path  = args.data_path or DEFAULT_PATHS[args.branch],
        output_dir = args.output_dir or (PROJECT_ROOT / "results" / args.branch),
        sample_n   = args.sample,
    )
    SEP = "═" * 60
    log.info(SEP)
    log.info("MAKORA T10.1 — EDA | branche : %s", cfg.branch.upper())
    log.info("Dataset  : %s", cfg.data_path)
    log.info("Sorties  : %s", cfg.output_dir)
    log.info(SEP)

    log.info("── [1/5] Chargement + feature engineering")
    df_full, df_feat, features = load_dataset(cfg)

    log.info("── [2/5] Statistiques d'ensemble")
    overview = compute_overview(df_full, features)
    with open(cfg.output_dir / "eda_overview.json", "w", encoding="utf-8") as fh:
        json.dump(overview, fh, ensure_ascii=False, indent=2, default=str)
    log.info("  JSON : eda_overview.json")
    for cat, n in sorted(overview["categories"].items(), key=lambda x: -x[1]):
        log.info("  %-15s %8d  %6.1f%%", cat, n, n / overview["n_total"] * 100)

    log.info("── [3/5] Distributions features × catégories")
    plot_distributions(df_feat, features, cfg)

    log.info("── [4/5] Corrélation de Spearman")
    plot_correlation(df_feat, features, cfg)

    log.info("── [5/5] PCA + UMAP")
    plot_pca_umap(df_feat, features, cfg)

    log.info("── [KS]  Tests Kolmogorov-Smirnov par scénario")
    try:
        from t10_1_eda_tests import run_statistical_tests
        run_statistical_tests(df_feat, features, cfg)
    except ImportError as exc:
        log.error("t10_1_eda_tests.py introuvable : %s", exc)

    log.info(SEP)
    log.info("EDA terminée → %s", cfg.output_dir)
    log.info("Prochaine étape : t10_2_baseline.py --branch %s", cfg.branch)
    log.info(SEP)


if __name__ == "__main__":
    main()