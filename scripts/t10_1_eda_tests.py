"""
MODULE : scripts/t10_1_eda_tests.py
DESCRIPTION : Tests statistiques pour l'EDA MAKORA — Phase T10.1
              Kolmogorov-Smirnov par scénario × feature, d de Cohen,
              heatmap de détectabilité, rapport go/no-go.

RÉFÉRENCES :
- [Kolmogorov1933] Test KS : H0 = distributions identiques.
- [Cohen1988] d de Cohen : effet petit ≥ 0.2, moyen ≥ 0.5, grand ≥ 0.8.
- [Chandola2009] Critère de détectabilité pour IF non-supervisé.
- [Goldstein2016] Protocole évaluation features anomalies.
- [Bauder2017] Référence taux fraude assurance 3–10%.

DÉCISIONS :
- Détectable si KS p < 0.05 ET |d de Cohen| > 0.3.
- "go"    ≥ 2 features détectables → IF attendu performant.
- "warn"  = 1 feature détectable  → F1 attendu modéré.
- "no-go"   0 feature détectable  → documenter comme limite mémoire.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

if TYPE_CHECKING:
    from t10_1_eda import EDAConfig

log = logging.getLogger("makora.eda.tests")

ALPHA  = 0.05
D_MIN  = 0.30
MIN_N  = 10
GO_N   = 2
WARN_N = 1

# Catalogue des scénarios par catégorie
_CAT_MAP: dict[str, str] = {}
for _s in {"Staging_Accident","Vol_Fictif","Multi_Sinistres","Antidatage_Contrat",
           "Vehicule_Sur_Value","Pieces_Reemploi","Constat_Retroactif","Surfacturation",
           "Expert_Corrompu","Recyclage_Numerique","Faux_Conducteur","Benford_Deviation",
           "Collusion_Garage_Assure","Falsification_Constat","Pieces_Non_Montees",
           "Surfacturation_Praticien","Phantom_Billing","Upcoding","Pret_Carte",
           "Fraude_Post_Mortem","Falsification_Ordo","Unbundling","Doublon_Facturation"}:
    _CAT_MAP[_s] = "FRAUDE"
for _s in {"Erreur_Bareme_MO","Double_Declaration","Inversion_Montant",
           "Sinistre_Hors_Garantie","Erreur_Codification_Reparation","Oubli_Conversion_XAF_EUR"}:
    _CAT_MAP[_s] = "ERREUR_OP"
for _s in {"Derive_Bareme_Inflation","Biais_OCR_Rural","Biais_Geographique_BonusMalus",
           "Surestimation_Expert","Rejet_OCR_Matriciel"}:
    _CAT_MAP[_s] = "BIAIS"
for _s in {"Doublon_Batch_API","Derive_Nomenclature","Schema_Drift_Dates","Corruption_Hash"}:
    _CAT_MAP[_s] = "TECHNIQUE"


# ─── Structures ───────────────────────────────────────────────────────────

@dataclass
class FeatureSignal:
    feature: str;  ks_stat: float;  p_value: float
    cohens_d: float;  detectable: bool
    n_normal: int;  n_scenario: int


@dataclass
class ScenarioReport:
    scenario: str;  category: str;  n_dossiers: int
    n_detectable: int;  decision: str
    top_feature: str;  top_cohens_d: float
    feature_signals: list[FeatureSignal];  comment: str


# ─── Statistiques ─────────────────────────────────────────────────────────

def _cohens_d(a: np.ndarray, b: np.ndarray) -> float:
    """d de Cohen (écart-type poolé). [Cohen1988]"""
    if len(a) < 2 or len(b) < 2: return 0.0
    s = np.sqrt((np.var(a, ddof=1) + np.var(b, ddof=1)) / 2.0)
    return float(abs(np.mean(a) - np.mean(b)) / s) if s > 0 else 0.0


def _test_feature(norm: np.ndarray, scen: np.ndarray, feat: str) -> FeatureSignal:
    """Test KS + d de Cohen pour une paire (feature, scénario). [Kolmogorov1933]"""
    a = norm[~np.isnan(norm)]; b = scen[~np.isnan(scen)]
    if len(a) < MIN_N or len(b) < MIN_N:
        return FeatureSignal(feat, 0., 1., 0., False, len(a), len(b))
    ks = stats.ks_2samp(a, b); d = _cohens_d(a, b)
    return FeatureSignal(
        feature=feat, ks_stat=round(float(ks.statistic), 4),
        p_value=round(float(ks.pvalue), 6), cohens_d=round(d, 4),
        detectable=bool(ks.pvalue < ALPHA and d > D_MIN),
        n_normal=int(len(a)), n_scenario=int(len(b)),
    )


def _analyse_scenario(
    norm_df: pd.DataFrame, scen_df: pd.DataFrame,
    features: list[str], name: str,
) -> ScenarioReport:
    sigs = [_test_feature(norm_df[f].values, scen_df[f].values, f)
            for f in features if f in norm_df.columns and f in scen_df.columns]
    n_det = sum(s.detectable for s in sigs)
    top   = max(sigs, key=lambda s: s.cohens_d, default=None)

    decision = "go" if n_det >= GO_N else "warn" if n_det == WARN_N else "no-go"
    comments = {
        "go":    f"{n_det}/{len(sigs)} features discriminantes. Signal fort — IF attendu performant. ✅",
        "warn":  f"1/{len(sigs)} feature discriminante. Signal faible — F1 attendu modéré. ⚠️",
        "no-go": (f"0/{len(sigs)} features discriminantes (critère : p < {ALPHA}, |d| > {D_MIN}). "
                  "IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire."),
    }
    return ScenarioReport(
        scenario=name, category=_CAT_MAP.get(name, "INCONNU"),
        n_dossiers=len(scen_df), n_detectable=n_det, decision=decision,
        top_feature=top.feature   if top else "N/A",
        top_cohens_d=top.cohens_d if top else 0.0,
        feature_signals=sigs, comment=comments[decision],
    )


# ─── Heatmap ──────────────────────────────────────────────────────────────

def _plot_heatmap(
    reports: list[ScenarioReport], features: list[str], cfg: "EDAConfig",
) -> Path:
    """
    Heatmap |d de Cohen| par (scénario × feature).
    Gras = détectable (p < 0.05 ET |d| > 0.3). [Cohen1988]
    """
    n_sc, n_ft = len(reports), len(features)
    mat = np.zeros((n_sc, n_ft)); det = np.zeros((n_sc, n_ft), dtype=bool)
    for i, r in enumerate(reports):
        sm = {s.feature: s for s in r.feature_signals}
        for j, ft in enumerate(features):
            if ft in sm:
                mat[i, j] = sm[ft].cohens_d; det[i, j] = sm[ft].detectable

    BG  = {"go": "#EAF3DE", "warn": "#FAEEDA", "no-go": "#FCEBEB"}
    SYM = {"go": "✅", "warn": "⚠️", "no-go": "❌"}
    fig, ax = plt.subplots(figsize=(max(9, n_ft * 1.1), max(8, n_sc * 0.44)))
    im = ax.imshow(mat, aspect="auto", cmap="Greens", vmin=0, vmax=1.5)

    for i in range(n_sc):
        for j in range(n_ft):
            v = mat[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7,
                    color="white" if v > 0.9 else "black",
                    fontweight="bold" if det[i, j] else "normal")
        ax.axhspan(i - 0.5, i + 0.5, xmin=0, xmax=1,
                   alpha=0.15, color=BG[reports[i].decision], zorder=0)

    ax.set_xticks(range(n_ft)); ax.set_xticklabels(features, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(n_sc))
    ax.set_yticklabels(
        [f"{SYM[r.decision]} {r.scenario} (n={r.n_dossiers})" for r in reports], fontsize=8)
    fig.colorbar(im, ax=ax, shrink=0.65).set_label("|d de Cohen| [Cohen1988]", fontsize=8)
    ax.set_xlabel("Features ML calculées", fontsize=9)
    ax.set_ylabel("Scénarios injectés", fontsize=9)
    ax.set_title(
        f"MAKORA — Détectabilité par scénario · {cfg.branch.upper()}\n"
        f"Gras = p < {ALPHA} ET |d| > {D_MIN} [Kolmogorov1933, Cohen1988]",
        fontsize=10, fontweight="bold")
    ax.legend(handles=[
        plt.Rectangle((0,0),1,1, facecolor=BG[k], label=f"{SYM[k]} {k}")
        for k in ("go","warn","no-go")
    ], loc="lower right", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    out = cfg.output_dir / "eda_signal_heatmap.png"
    fig.savefig(out, dpi=200, bbox_inches="tight"); plt.close(fig)
    log.info("Heatmap : %s", out); return out


# ─── Rapports JSON + Markdown ─────────────────────────────────────────────

def _save_json(reports: list[ScenarioReport], cfg: "EDAConfig") -> Path:
    n_g = sum(1 for r in reports if r.decision == "go")
    n_w = sum(1 for r in reports if r.decision == "warn")
    n_n = sum(1 for r in reports if r.decision == "no-go")
    payload = {
        "branch": cfg.branch, "ks_alpha": ALPHA, "cohen_d_min": D_MIN,
        "n_scenarios_total": len(reports),
        "n_go": n_g, "n_warn": n_w, "n_no_go": n_n,
        "scenarios": [
            {**{k: v for k, v in asdict(r).items() if k != "feature_signals"},
             "feature_signals": [asdict(s) for s in r.feature_signals]}
            for r in reports
        ],
    }
    out = cfg.output_dir / "eda_signal_report.json"
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
    log.info("Rapport JSON : %s", out); return out


def _save_markdown(reports: list[ScenarioReport], cfg: "EDAConfig") -> Path:
    """Rapport Markdown copié-collable dans le mémoire (section EDA)."""
    n = len(reports)
    n_g = sum(1 for r in reports if r.decision == "go")
    n_w = sum(1 for r in reports if r.decision == "warn")
    n_n = sum(1 for r in reports if r.decision == "no-go")
    SYM = {"go": "✅", "warn": "⚠️", "no-go": "❌"}

    lines = [
        f"# EDA — Détectabilité des scénarios ({cfg.branch.upper()})",
        f"> seed={cfg.random_state} · KS p < {ALPHA} ET |d| > {D_MIN} "
        "[Kolmogorov1933, Cohen1988]", "",
        "## Synthèse", "",
        "| Décision | Nb | % |", "|---|---|---|",
        f"| {SYM['go']} **Go** ≥ 2 features | {n_g} | {n_g/n:.0%} |",
        f"| {SYM['warn']} **Warn** 1 feature | {n_w} | {n_w/n:.0%} |",
        f"| {SYM['no-go']} **No-go** 0 feature | {n_n} | {n_n/n:.0%} |",
        f"| **Total** | **{n}** | 100% |", "",
        "## Détail par scénario", "",
        "| Scénario | Catégorie | n | Décision | Feature clé | |d| | Commentaire |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in sorted(reports, key=lambda x: (x.decision=="no-go", x.decision=="warn", -x.n_detectable)):
        best = next(
            (s for s in sorted(r.feature_signals, key=lambda s: -s.cohens_d)
             if s.detectable), None,
        )
        p_val = f"{best.p_value:.4f}" if best else "—"
        lines.append(
            f"| {r.scenario} | {r.category} | {r.n_dossiers} "
            f"| {SYM[r.decision]} {r.decision} "
            f"| {r.top_feature} | {r.top_cohens_d:.3f} | {p_val} |"
        )
    if n_n:
        lines += ["", "## ⚠️ Scénarios No-Go — À documenter dans le mémoire", "",
                  f"Ces {n_n} scénario(s) ne présentent aucun signal dans les features "
                  "V1. Isolation Forest ne peut pas les détecter en mode tabulaire non-supervisé. "
                  "→ Section **'Limites du modèle'** du mémoire.", ""]
        for r in reports:
            if r.decision == "no-go":
                lines += [f"- **{r.scenario}** ({r.category}, n={r.n_dossiers})",
                          f"  {r.comment}", ""]
    lines += ["---",
              f"*MAKORA T10.1 EDA · {cfg.branch} · "
              "Réf : [Kolmogorov1933] [Cohen1988] [Chandola2009]*"]
    out = cfg.output_dir / "eda_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    log.info("Rapport Markdown : %s", out); return out


# ─── Point d'entrée public ────────────────────────────────────────────────

def run_statistical_tests(
    df:       pd.DataFrame,
    features: list[str],
    cfg:      "EDAConfig",
) -> list[ScenarioReport]:
    """
    Orchestre les tests KS par scénario, génère heatmap + JSON + Markdown.
    Appelé par t10_1_eda.py.
    """
    norm_df   = df[df["Label_Anomalie"] == "NORMAL"]
    scenarios = [s for s in df["Sous_Type_Anomalie"].dropna().unique()
                 if s not in ("RAS", "NORMAL", "", "nan")]
    log.info("Tests KS : %d scénarios × %d features...", len(scenarios), len(features))

    reports: list[ScenarioReport] = []
    SYM = {"go": "✅", "warn": "⚠️", "no-go": "❌"}
    for scen in sorted(scenarios):
        scen_df = df[df["Sous_Type_Anomalie"] == scen]
        if len(scen_df) < MIN_N:
            log.warning("'%s' : %d < MIN_N=%d → ignoré.", scen, len(scen_df), MIN_N)
            continue
        r = _analyse_scenario(norm_df, scen_df, features, scen)
        reports.append(r)
        log.info("  %s %-35s n=%-4d det=%d/%d top_d=%.3f (%s)",
                 SYM[r.decision], r.scenario, r.n_dossiers,
                 r.n_detectable, len(r.feature_signals),
                 r.top_cohens_d, r.top_feature)

    if not reports:
        log.warning("Aucun scénario testable — vérifier Sous_Type_Anomalie.")
        return []

    _plot_heatmap(reports, features, cfg)
    _save_json(reports, cfg)
    _save_markdown(reports, cfg)

    n_g = sum(1 for r in reports if r.decision == "go")
    n_w = sum(1 for r in reports if r.decision == "warn")
    n_n = sum(1 for r in reports if r.decision == "no-go")
    log.info("Résumé KS — ✅ go:%d ⚠️ warn:%d ❌ no-go:%d / %d scénarios",
             n_g, n_w, n_n, len(reports))
    if n_n:
        log.warning("No-go → documenter dans mémoire : %s",
                    [r.scenario for r in reports if r.decision == "no-go"])
    return reports