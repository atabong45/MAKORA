"""
MODULE : scripts/t10_8_persist.py
DESCRIPTION : Persistance finale des modèles MAKORA après validation
              des métriques en T10.7. Produit le manifest de déploiement
              et le fichier metrics.json consolidé (entrée du mémoire ch.5).

RÉFÉRENCES ACADÉMIQUES :
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in machine
  learning systems. NeurIPS. → Recommande de versionner les artéfacts ML
  (modèle + scaler + threshold + metadata) comme une unité atomique.
- [Amershi2019] Amershi et al. (2019). Software Engineering for ML. ICSE.
  → Model cards : chaque modèle doit être accompagné de ses métriques,
    ses limites documentées et son contexte d'entraînement.

DÉCISIONS DE CONCEPTION :
- Seul le modèle IF classique est copié dans data/models/{branch}/production/
  (le seul compatible SHAP TreeExplainer → production MAKORA).
- Tous les challengers restent dans data/models/{branch}/ pour reproductibilité.
- Le fichier metrics_final.json est le livrable principal de T10 pour
  le tableau comparatif du mémoire (ch. 5 section résultats).
- model_card.json généré automatiquement [Amershi2019].

USAGE :
  python scripts/t10_8_persist.py --branch sante
  python scripts/t10_8_persist.py --branch auto
  python scripts/t10_8_persist.py --branch both
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path

import joblib

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("makora.t10_8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR   = PROJECT_ROOT / "data" / "models"
RESULTS_DIR  = PROJECT_ROOT / "results"

BRANCHES = ["sante", "auto"]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_json(path: Path) -> dict | list | None:
    if path.exists():
        return json.loads(path.read_text())
    return None


# ─── Consolidation métriques ─────────────────────────────────────────────────

def consolidate_metrics(branch: str) -> dict:
    """
    Fusionne les résultats T10.3, T10.4, T10.7 en un seul fichier
    metrics_final.json — livrable direct du mémoire chapitre 5.
    """
    results_dir = RESULTS_DIR / branch

    t10_3 = _load_json(results_dir / "t10_3_if_results.json")
    t10_4 = _load_json(results_dir / "t10_4_challengers_results.json")
    t10_7 = _load_json(results_dir / "t10_7_comparative_table.json")
    t10_5 = _load_json(results_dir / "t10_5_learning_curves.json")
    conv  = _load_json(results_dir / "convergence_report.json")

    # Table synthétique pour le mémoire
    summary_rows: list[dict] = []
    if t10_7:
        for entry in t10_7:
            if "metrics" not in entry:
                continue
            m  = entry["metrics"]
            ci = m.get("bootstrap_ci", {})
            row = {
                "algo":           entry.get("algo", "?"),
                "f1":             m.get("f1"),
                "f1_ci_lo":       ci.get("f1", {}).get("ci_lo"),
                "f1_ci_hi":       ci.get("f1", {}).get("ci_hi"),
                "precision":      m.get("precision"),
                "recall":         m.get("recall"),
                "auc_roc":        m.get("auc_roc"),
                "avg_precision":  m.get("avg_prec"),
                "mcc":            m.get("mcc"),
                "fpr":            m.get("fpr"),
                "threshold":      m.get("threshold"),
                "mcnemar_pvalue": entry.get("mcnemar_vs_if", {}).get("pvalue"),
                "significant_vs_if": entry.get("mcnemar_vs_if", {}).get("significant"),
            }
            summary_rows.append(row)

    return {
        "branch":              branch,
        "generated_at":        datetime.now(timezone.utc).isoformat(),
        "protocol":            "MAKORA Bloc B — T10.2 → T10.8",
        "random_state":        42,
        "summary_table":       summary_rows,
        "learning_curves":     t10_5,
        "shap_lime_convergence": conv,
        "raw_t10_3":           t10_3,
        "raw_t10_4":           t10_4,
    }


# ─── Production copy ─────────────────────────────────────────────────────────

def copy_production_model(branch: str) -> dict:
    """
    Copie les artéfacts de production dans data/models/{branch}/production/.
    Seul IF classique est éligible production (SHAP-compatible) [Sculley2015].
    """
    src_dir  = MODELS_DIR / branch
    prod_dir = src_dir / "production"
    prod_dir.mkdir(parents=True, exist_ok=True)

    artefacts = {
        "model":    src_dir / "if_classic_model.joblib",
        "threshold": RESULTS_DIR / branch / "t10_7_comparative_table.json",
    }

    checksums: dict[str, str] = {}
    for name, src in artefacts.items():
        if not src.exists():
            log.warning("  Artéfact '%s' introuvable : %s", name, src)
            continue
        dst = prod_dir / src.name
        shutil.copy2(src, dst)
        sha = _sha256(dst)
        checksums[name] = {"file": dst.name, "sha256": sha[:16] + "..."}
        log.info("  Copié : %s → production/ (SHA256: %s)", src.name, sha[:16])

    return checksums


# ─── Model card ──────────────────────────────────────────────────────────────

def generate_model_card(branch: str, metrics_final: dict) -> dict:
    """
    Model card [Amershi2019] — documentation du modèle déployé.
    Décrit les métriques, les limites et le contexte d'entraînement.
    """
    # Extrait les métriques IF classique depuis la table synthétique
    if_metrics = next(
        (r for r in metrics_final["summary_table"] if r["algo"] == "IsolationForest"),
        {},
    )

    card = {
        "model_name":    f"MAKORA-IF-{branch.upper()}-v1",
        "branch":        branch,
        "algorithm":     "IsolationForest",
        "reference":     "[Liu2008] Liu et al. (2008). Isolation Forest. ICDM.",
        "generated_at":  datetime.now(timezone.utc).isoformat(),
        "training_data": {
            "source": f"data/splits/{branch}/{branch}_train.parquet",
            "size":   "70% du dataset v1",
            "seed":   42,
        },
        "performance": {
            "f1":         if_metrics.get("f1"),
            "f1_ci":      f"[{if_metrics.get('f1_ci_lo')}, {if_metrics.get('f1_ci_hi')}]",
            "auc_roc":    if_metrics.get("auc_roc"),
            "mcc":        if_metrics.get("mcc"),
            "fpr":        if_metrics.get("fpr"),
            "threshold":  if_metrics.get("threshold"),
            "bootstrap":  "1000 itérations, IC 95% [Efron1979]",
        },
        "limitations": [
            "Entraîné sur données synthétiques — performance réelle à valider "
            "sur données ASAC/Activa réelles.",
            "Features stateless — pas de persistance inter-batches (DT-002).",
            "Contamination optimisée sur val set — peut varier selon la période.",
            "Non-supervisé — labels non utilisés à l'entraînement. "
            "Évaluation supervisée uniquement post-hoc.",
        ],
        "shap_compatible":   True,
        "production_ready":  True,
        "challengers_tested": [
            r["algo"] for r in metrics_final["summary_table"]
            if r["algo"] != "IsolationForest"
        ],
    }
    return card


# ─── Rapport console ─────────────────────────────────────────────────────────

def print_summary_table(metrics_final: dict) -> None:
    """Affiche le tableau comparatif final dans le terminal."""
    rows = metrics_final.get("summary_table", [])
    if not rows:
        log.warning("Pas de données dans la table comparative.")
        return

    SEP = "─" * 95
    log.info(SEP)
    log.info("TABLEAU COMPARATIF FINAL — %s", metrics_final["branch"].upper())
    log.info(SEP)
    header = f"{'Algo':<22} {'F1':>6} {'IC95':>14} {'AUC':>6} {'MCC':>6} "
    header += f"{'FPR':>6} {'AP':>6} {'McNemar':>8}"
    log.info(header)
    log.info("─" * 95)

    for r in rows:
        ci  = f"[{r.get('f1_ci_lo','?')},{r.get('f1_ci_hi','?')}]"
        pv  = r.get("mcnemar_pvalue")
        sig = "✓sig" if r.get("significant_vs_if") else (
              "n.s." if pv is not None else "ref")
        def _fmt(v, w=6):
            return f"{v:{w}}" if v is not None else f"{"—":>{w}}"
        line = (
            f"{r.get('algo','?'):<22} "
            f"{_fmt(r.get('f1'))} "
            f"{ci:>14} "
            f"{_fmt(r.get('auc_roc'))} "
            f"{_fmt(r.get('mcc'))} "
            f"{_fmt(r.get('fpr'))} "
            f"{_fmt(r.get('avg_precision'))} "
            f"{sig:>8}"
        )
        log.info(line)
    log.info(SEP)


# ─── Main ─────────────────────────────────────────────────────────────────────

def process_branch(branch: str) -> None:
    SEP = "─" * 60
    log.info(SEP)
    log.info("Persistance finale [%s]", branch.upper())

    # 1. Consolider métriques
    metrics_final = consolidate_metrics(branch)

    # 2. Sauvegarder metrics_final.json
    out_dir = RESULTS_DIR / branch
    out_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = out_dir / "metrics_final.json"
    metrics_path.write_text(
        json.dumps(metrics_final, indent=2, ensure_ascii=False, default=str)
    )
    log.info("metrics_final.json : %s", metrics_path)

    # 3. Copier modèle de production
    checksums = copy_production_model(branch)

    # 4. Model card
    card = generate_model_card(branch, metrics_final)
    card["production_checksums"] = checksums
    card_path = MODELS_DIR / branch / "production" / "model_card.json"
    card_path.write_text(json.dumps(card, indent=2, ensure_ascii=False, default=str))
    log.info("Model card : %s", card_path)

    # 5. Afficher tableau comparatif
    print_summary_table(metrics_final)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="MAKORA T10.8 — Persistance finale modèles"
    )
    p.add_argument("--branch", choices=["sante", "auto", "both"], default="both")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    SEP  = "─" * 60
    log.info(SEP)
    log.info("MAKORA — T10.8 Persistance finale")
    log.info(SEP)

    branches = BRANCHES if args.branch == "both" else [args.branch]
    for branch in branches:
        process_branch(branch)

    log.info(SEP)
    log.info("✅ T10.8 terminé — Bloc B complet.")
    log.info("Prochaine étape :")
    log.info("  python scripts/t12_1_experiment_h0.py  ← Expérience H0")
    log.info("  python scripts/t13_1_graph_engine.py   ← Graphe Louvain")
    log.info(SEP)


if __name__ == "__main__":
    main()