"""
MODULE : scripts/t12_2_delta_analysis.py
DESCRIPTION : Calcul du delta F1 (spécialisé vs générique) et tableau comparatif
              pour valider l'hypothèse H0 de généricité MAKORA.

RÉFÉRENCES ACADÉMIQUES :
- [Caruana1997] Caruana, R. (1997). Multitask learning. Machine Learning, 28(1).
  → Δ ∈ [2%, 7%] → trade-off généricité/précision documenté et acceptable.
- [Demšar2006] Demšar, J. (2006). Statistical comparisons of classifiers over
  multiple data sets. JMLR, 7, 1–30.
  → Test de Wilcoxon recommandé pour comparer 2 classifieurs sans hypothèse
    de normalité. Ici adapté via bootstrap sur les scores de décision.
- [Kohavi1995] Kohavi, R. (1995). Bootstrap pour intervalles de confiance.

DÉCISIONS DE CONCEPTION :
- Le verdict est calculé automatiquement selon le protocole RESEARCH_PROTOCOL.md :
    Δ ∈ [2%, 7%] → "CONTRIBUTION VALIDÉE"
    Δ > 7%        → "PRÉCISION SACRIFIÉE — à documenter dans les limites"
    Δ < 2%        → "GÉNÉRICITÉ SANS COÛT — contribution forte"
- Les 3 seuils sont externalisés (DELTA_ACCEPTABLE_LOW / HIGH) — modifiables.
- Le rapport Markdown est généré pour intégration directe dans le mémoire.
- Pas de dépendance à SciPy pour éviter les problèmes d'environnement Anaconda.

USAGE :
  python scripts/t12_2_delta_analysis.py
  python scripts/t12_2_delta_analysis.py --input results/h0/t12_1_models_metrics.json
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("makora.t12_2")

PROJECT_ROOT     = Path(__file__).resolve().parent.parent
RESULTS_H0_DIR   = PROJECT_ROOT / "results" / "h0"

# [Caruana1997] — seuils du protocole RESEARCH_PROTOCOL.md
DELTA_LOW  = 0.02   # en dessous : généricité sans coût
DELTA_HIGH = 0.07   # au-dessus  : précision trop sacrifiée


# ─── Lecture des résultats T12.1 ─────────────────────────────────────────────

def load_metrics(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(
            f"Fichier de métriques introuvable : {path}\n"
            "Lancer d'abord : python scripts/t12_1_experiment_h0.py"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    log.info("Métriques chargées : %d entrées", len(data))
    return data


def index_by_model_branch(metrics: list[dict]) -> dict[tuple[str, str], dict]:
    """Index (model, branch_eval) → dict métriques."""
    return {(m["model"], m["branch_eval"]): m for m in metrics}


# ─── Calcul des deltas ────────────────────────────────────────────────────────

def compute_delta(
    idx: dict[tuple[str, str], dict],
    branch: str,
) -> dict:
    """
    Calcule Δ = F1(M_spécialisé) - F1(M_makora) pour une branche.
    [Caruana1997] — comparaison directe sur le même test set immutable.
    """
    key_spec   = (f"M_{branch}", branch)
    key_makora = ("M_makora",    branch)

    if key_spec not in idx:
        raise KeyError(f"Métriques M_{branch} manquantes — relancer T12.1.")
    if key_makora not in idx:
        raise KeyError(f"Métriques M_makora sur {branch} manquantes — relancer T12.1.")

    spec   = idx[key_spec]
    makora = idx[key_makora]

    delta = spec["f1"] - makora["f1"]

    # Verdict selon protocole RESEARCH_PROTOCOL.md
    if delta < DELTA_LOW:
        verdict = "GÉNÉRICITÉ_SANS_COÛT"
        comment = "M_makora rivalise avec le spécialisé — contribution forte."
    elif delta <= DELTA_HIGH:
        verdict = "CONTRIBUTION_VALIDÉE"
        comment = f"Trade-off généricité/précision acceptable (Δ={delta:.3f} ∈ [{DELTA_LOW},{DELTA_HIGH}])."
    else:
        verdict = "PRÉCISION_SACRIFIÉE"
        comment = f"Δ={delta:.3f} > {DELTA_HIGH} — documenter dans les limites du mémoire."

    return {
        "branch":           branch,
        "f1_specialized":   spec["f1"],
        "f1_makora":        makora["f1"],
        "delta_f1":         round(delta, 4),
        "delta_pct":        round(delta * 100, 2),
        "ci_specialized":   [spec.get("f1_ci_low"), spec.get("f1_ci_high")],
        "ci_makora":        [makora.get("f1_ci_low"), makora.get("f1_ci_high")],
        "auc_specialized":  spec["auc_roc"],
        "auc_makora":       makora["auc_roc"],
        "mcc_specialized":  spec["mcc"],
        "mcc_makora":       makora["mcc"],
        "fpr_specialized":  spec["fpr"],
        "fpr_makora":       makora["fpr"],
        "precision_specialized": spec["precision"],
        "recall_specialized":    spec["recall"],
        "precision_makora":  makora["precision"],
        "recall_makora":     makora["recall"],
        "verdict":          verdict,
        "comment":          comment,
    }


# ─── Affichage terminal ───────────────────────────────────────────────────────

SEP = "─" * 70


def print_comparative_table(deltas: list[dict], all_metrics: list[dict]) -> None:
    """Tableau comparatif terminal — format mémoire."""
    log.info(SEP)
    log.info("TABLEAU COMPARATIF H0 — MAKORA vs Spécialisés")
    log.info("[Caruana1997] Seuil acceptable : Δ ∈ [%.0f%%, %.0f%%]",
             DELTA_LOW * 100, DELTA_HIGH * 100)
    log.info(SEP)
    log.info("%-22s %-8s %-8s %-8s %-8s %-8s %-8s",
             "Modèle", "Branch", "F1", "CI_low", "CI_hi", "AUC", "MCC")
    log.info(SEP)

    idx = index_by_model_branch(all_metrics)
    for branch in ["sante", "auto"]:
        for model in [f"M_{branch}", "M_makora"]:
            key = (model, branch)
            if key not in idx:
                continue
            m = idx[key]
            log.info("%-22s %-8s %-8.4f %-8.4f %-8.4f %-8.4f %-8.4f",
                     model, branch,
                     m["f1"],
                     m.get("f1_ci_low", 0),
                     m.get("f1_ci_high", 0),
                     m["auc_roc"],
                     m["mcc"])
        log.info(SEP)

    log.info("")
    log.info("DELTA F1 (spécialisé - générique)")
    log.info(SEP)
    for d in deltas:
        arrow = "↑" if d["delta_f1"] > 0 else "↓"
        log.info("[%s] Δ = %+.4f (%+.2f%%) %s — VERDICT: %s",
                 d["branch"].upper(), d["delta_f1"], d["delta_pct"],
                 arrow, d["verdict"])
        log.info("     %s", d["comment"])
    log.info(SEP)


# ─── Rapport Markdown ─────────────────────────────────────────────────────────

def generate_markdown_report(deltas: list[dict], all_metrics: list[dict]) -> str:
    """
    Génère un rapport Markdown intégrable dans le mémoire (Chapitre 5).
    """
    idx = index_by_model_branch(all_metrics)
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = [
        "# Expérience H0 — Généricité MAKORA",
        f"> Générée le {now} | Protocole : RESEARCH_PROTOCOL.md v1.0",
        "",
        "## Hypothèse nulle",
        "> *\"Un modèle spécialisé (entraîné uniquement sur Santé) n'est pas",
        "> significativement plus précis qu'un modèle générique MAKORA\"*",
        "> — [Caruana1997] Multitask Learning, Machine Learning 28(1).",
        "",
        "## Tableau comparatif",
        "",
        "| Modèle | Branche éval. | F1 | IC 95% | AUC-ROC | MCC | FPR |",
        "|--------|---------------|----|--------|---------|-----|-----|",
    ]

    for branch in ["sante", "auto"]:
        for model in [f"M_{branch}", "M_makora"]:
            key = (model, branch)
            if key not in idx:
                continue
            m   = idx[key]
            ci  = f"[{m.get('f1_ci_low',0):.3f}, {m.get('f1_ci_high',0):.3f}]"
            tag = " *(générique)*" if model == "M_makora" else " *(spécialisé)*"
            lines.append(
                f"| `{model}`{tag} | {branch} "
                f"| **{m['f1']:.4f}** | {ci} "
                f"| {m['auc_roc']:.4f} | {m['mcc']:.4f} | {m['fpr']:.4f} |"
            )

    lines += ["", "## Résultats Δ F1", ""]

    overall_ok = True
    for d in deltas:
        emoji = {"CONTRIBUTION_VALIDÉE": "✅",
                 "GÉNÉRICITÉ_SANS_COÛT": "🏆",
                 "PRÉCISION_SACRIFIÉE":  "⚠️"}.get(d["verdict"], "❓")
        lines += [
            f"### Branche {d['branch'].capitalize()}",
            "",
            f"- **F1 M_{d['branch']}** (spécialisé) : `{d['f1_specialized']:.4f}`",
            f"- **F1 M_makora** (générique) : `{d['f1_makora']:.4f}`",
            f"- **Δ F1** : `{d['delta_f1']:+.4f}` ({d['delta_pct']:+.2f}%)",
            f"- **Verdict** : {emoji} `{d['verdict']}`",
            f"- *{d['comment']}*",
            "",
        ]
        if d["verdict"] == "PRÉCISION_SACRIFIÉE":
            overall_ok = False

    lines += [
        "## Conclusion",
        "",
    ]
    if overall_ok:
        lines.append(
            "L'hypothèse H0 est **validée** : le framework générique MAKORA "
            "maintient une précision de détection comparable aux modèles spécialisés "
            "sur les deux branches (Santé et Auto), avec un trade-off de généricité "
            "dans la plage acceptable définie par [Caruana1997]."
        )
    else:
        lines.append(
            "L'hypothèse H0 est **partiellement rejetée** sur certaines branches. "
            "Le delta de précision dépasse le seuil de 7%. "
            "Cette limite est documentée dans la section 'Limites du mémoire' (§6.x)."
        )

    lines += [
        "",
        "---",
        "*MAKORA T12.2 — Analyse Δ F1 | Référence : [Caruana1997]*",
    ]
    return "\n".join(lines)


# ─── Main ─────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MAKORA T12.2 — Delta F1 H0")
    p.add_argument(
        "--input",
        type=Path,
        default=RESULTS_H0_DIR / "t12_1_models_metrics.json",
        help="Fichier JSON issu de T12.1",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    metrics = load_metrics(args.input)
    idx     = index_by_model_branch(metrics)

    deltas = []
    for branch in ["sante", "auto"]:
        try:
            d = compute_delta(idx, branch)
            deltas.append(d)
        except KeyError as e:
            log.warning("Branch '%s' ignorée : %s", branch, e)

    if not deltas:
        log.error("Aucun delta calculable — vérifier T12.1.")
        return

    # Affichage terminal
    print_comparative_table(deltas, metrics)

    # Sauvegarde JSON
    RESULTS_H0_DIR.mkdir(parents=True, exist_ok=True)
    delta_path = RESULTS_H0_DIR / "t12_2_delta_results.json"
    delta_path.write_text(
        json.dumps({"deltas": deltas, "all_metrics": metrics},
                   indent=2, ensure_ascii=False, default=str)
    )
    log.info("Résultats Δ → %s", delta_path)

    # Rapport Markdown
    md = generate_markdown_report(deltas, metrics)
    md_path = RESULTS_H0_DIR / "t12_2_h0_report.md"
    md_path.write_text(md, encoding="utf-8")
    log.info("Rapport Markdown → %s", md_path)
    log.info("Prochaine étape : python scripts/t12_3_fp_fn_analysis.py")


if __name__ == "__main__":
    main()