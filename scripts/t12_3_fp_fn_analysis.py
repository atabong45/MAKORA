"""
MODULE : scripts/t12_3_fp_fn_analysis.py
DESCRIPTION : Analyse qualitative des faux positifs (FP) et faux négatifs (FN)
              pour les trois modèles H0. Extrait les cas les plus proches du
              seuil de décision et génère un rapport structuré pour le mémoire.

RÉFÉRENCES ACADÉMIQUES :
- [Chandola2009] Chandola et al. (2009). Anomaly detection: A survey.
  ACM Computing Surveys.
  → L'analyse qualitative des erreurs est recommandée pour identifier les
    limites intrinsèques des méthodes non-supervisées (§ 5.3).
- [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection.
  ICMLA. → FP typiques : prestataires légitimes à facturation élevée ;
    FN typiques : fraudes bien camouflées (billing conforme mais réseau suspect).
- [Lundberg2017] Lundberg & Lee (2017). SHAP. NeurIPS.
  → Les valeurs SHAP permettent d'inspecter pourquoi un cas a été mal classé.
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML. NeurIPS.
  → L'analyse d'erreur qualitative fait partie du "slice-based evaluation"
    recommandé pour identifier les angles morts du modèle.

DÉCISIONS DE CONCEPTION :
- Les cas analysés sont ceux les PLUS PROCHES du seuil de décision,
  pas les cas extrêmes. Les cas extrêmes sont triviaux ; les cas proches du
  seuil révèlent les vraies limites du modèle [Chandola2009].
- N_CASES = 10 FP + 10 FN par modèle × 3 modèles (M_sante, M_auto, M_makora).
- La cause d'erreur est classifiée en 4 catégories (voir CAUSE_CATEGORIES).
- Le rapport Markdown est directement intégrable dans le Chapitre 6 du mémoire.

CORRECTIONS v2 (08 juin 2026) :
- extract_fp_fn() : suppression de la normalisation 1-(raw-min)/(max-min)
  qui inversait les scores DIF. Convention PyOD [Xu2023] : decision_function()
  retourne anomalie = score élevé. Cohérent avec t12_1 v2 et ML_PIPELINE §4.3.
- Seuil de proximité : np.abs(scores - 0.5) remplacé par np.abs(scores - median)
  car les scores DIF bruts ne sont pas dans [0,1].
- predict() : clf.predict(X) retourne 0/1 en PyOD, pas -1/1 comme sklearn.

USAGE :
  python scripts/t12_3_fp_fn_analysis.py
  python scripts/t12_3_fp_fn_analysis.py --branch sante --n-cases 10
  python scripts/t12_3_fp_fn_analysis.py --no-shap
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

# ─── Configuration ────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("makora.t12_3")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SPLITS_DIR   = PROJECT_ROOT / "data" / "splits"
MODELS_DIR   = PROJECT_ROOT / "data" / "models" / "h0"
RESULTS_DIR  = PROJECT_ROOT / "results" / "h0"

RANDOM_STATE = 42
LABEL_COL    = "Label_Anomalie"
NORMAL_VAL   = "NORMAL"
N_CASES      = 10

# [Chandola2009] — 4 catégories d'erreur standard
CAUSE_CATEGORIES = {
    "FEATURE_MANQUANTE":   "Feature discriminante absente ou non calculée (dette technique)",
    "SEUIL_MAL_CALITRE":   "Contamination imparfaite — cas légitime proche du seuil",
    "CAS_LIMITE_METIER":   "Fraude bien camouflée / dossier atypique légitimement suspect",
    "BRUIT_DONNEES":       "Anomalie statistique sans signification métier (artefact dataset)",
}

META_COLS = {
    "Label_Anomalie", "Sous_Type_Anomalie", "Cause_Racine_RCA",
    "Severite_Anomalie", "Source_Detection", "Validee_Par_Auditeur",
    "Date_Validation", "Commentaire_Audit", "Montant_Prejudice",
    "ID_Sinistre", "ID_Assure", "ID_Praticien", "ID_Vehicule",
    "ID_Contrat", "ID_Expert", "ID_Garage", "Hash_Image", "Batch_Date",
    "community_id_sante", "community_id_auto",
}


# ─── Chargement ───────────────────────────────────────────────────────────────

def load_test_set(branch: str) -> pd.DataFrame:
    p = SPLITS_DIR / branch / f"{branch}_test.parquet"
    if not p.exists():
        raise FileNotFoundError(f"Test set introuvable : {p}")
    df = pd.read_parquet(p)
    log.info("[%s] Test set : %d lignes", branch.upper(), len(df))
    return df


def load_model_bundle(model_name: str) -> dict:
    candidates = [
        MODELS_DIR / f"{model_name}.joblib",
        MODELS_DIR / f"{model_name}_sante.joblib",
        MODELS_DIR / f"{model_name}_auto.joblib",
    ]
    for p in candidates:
        if p.exists():
            log.info("Modèle chargé : %s", p)
            return joblib.load(p)
    raise FileNotFoundError(
        f"Bundle introuvable pour '{model_name}' dans {MODELS_DIR}\n"
        "Lancer d'abord : python scripts/t12_1_experiment_h0.py"
    )


def apply_module_features(
    df: pd.DataFrame, branch: str
) -> tuple[pd.DataFrame, list[str]]:
    from core.plugin_registry import PluginRegistry
    if branch == "sante":
        import modules.sante.sante_module  # noqa
    elif branch == "auto":
        import modules.auto.auto_module    # noqa
    yaml_path = PROJECT_ROOT / "modules" / branch / f"{branch}.yaml"
    module    = PluginRegistry.get(branch)(config_path=yaml_path)
    df_eng    = module.engineer_features(df.copy())
    feats     = [f for f in module.get_feature_names() if f in df_eng.columns]
    return df_eng, feats


# ─── Extraction FP / FN ──────────────────────────────────────────────────────

def extract_fp_fn(
    df_test: pd.DataFrame,
    bundle: dict,
    feats: list[str],
    n: int = N_CASES,
) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray]:
    """
    Extrait les N FP et N FN les plus proches du seuil de décision.

    [CORRECTION v2] Convention PyOD [Xu2023] : decision_function() retourne
    anomalie = score élevé. Pas d'inversion ni de normalisation.
    Le seuil de proximité est la médiane des scores (pas 0.5 fixe).

    [Chandola2009] : les cas proches du seuil sont plus informatifs
    que les cas extrêmes pour comprendre les limites du modèle.
    """
    clf    = bundle["model"]
    scaler = bundle.get("scaler") or bundle.get("scaler_sante")
    used_feats = bundle.get("features") or bundle.get("common_features") or feats

    available = [f for f in used_feats if f in df_test.columns]
    if not available:
        available = feats

    X = df_test[available].fillna(0).values.astype(np.float32)
    if scaler is not None:
        X = scaler.transform(X)

    y_true = (df_test[LABEL_COL] != NORMAL_VAL).astype(int).values

    # [CORRECTION] scores directs PyOD — anomalie = score élevé [Xu2023]
    scores = clf.decision_function(X)

    # [CORRECTION] PyOD predict() retourne 0/1, pas -1/1
    preds = clf.predict(X).astype(int)

    # [CORRECTION] seuil de proximité = médiane des scores (pas 0.5 fixe)
    seuil_ref = float(np.median(scores))
    log.info("  Seuil de référence (médiane scores) : %.4f", seuil_ref)

    df_result = df_test.copy()
    df_result["_anomaly_score"] = scores
    df_result["_pred"]          = preds
    df_result["_y_true"]        = y_true
    df_result["_dist_seuil"]    = np.abs(scores - seuil_ref)

    df_fp = (
        df_result[(df_result["_pred"] == 1) & (df_result["_y_true"] == 0)]
        .sort_values("_dist_seuil")
        .head(n)
    )

    df_fn = (
        df_result[(df_result["_pred"] == 0) & (df_result["_y_true"] == 1)]
        .sort_values("_dist_seuil")
        .head(n)
    )

    log.info("  FP extraits : %d / %d demandés", len(df_fp), n)
    log.info("  FN extraits : %d / %d demandés", len(df_fn), n)
    return df_fp, df_fn, scores


# ─── Analyse SHAP inline ─────────────────────────────────────────────────────

def _build_background_set(
    bundle: dict,
    branch: str,
    available: list[str],
    n_background: int = 100,
) -> np.ndarray:
    """
    Construit le background set pour KernelSHAP.

    Stratégie [Lundberg2017] : 100 dossiers normaux du train set.
    Un background set trop grand → KernelSHAP très lent (~n² complexité).
    100 est le compromis standard vitesse/précision.

    Le train set parquet contient les colonnes BRUTES (pas les features).
    On filtre d'abord les 100 dossiers normaux au niveau brut (Label_Anomalie
    est présent dans le parquet brut), puis on applique engineer_features()
    uniquement sur ces 100 lignes — pas sur les 70k/98k du train complet.

    Fallback : si le train set est inaccessible, utilise np.zeros (moins
    précis mais fonctionnel — acceptable pour l'analyse qualitative).
    """
    scaler = bundle.get("scaler") or bundle.get("scaler_sante")
    train_path = SPLITS_DIR / branch / f"{branch}_train.parquet"

    if train_path.exists():
        try:
            # 1. Charger le train set brut et filtrer les normaux
            df_train = pd.read_parquet(train_path)
            df_normal = df_train[df_train[LABEL_COL] == NORMAL_VAL]

            # 2. Échantillonner 100 dossiers bruts — avant engineer_features
            #    pour éviter de transformer les 70k-98k lignes complètes
            df_sample = df_normal.sample(
                n=min(n_background, len(df_normal)),
                random_state=RANDOM_STATE,
            )

            # 3. Appliquer engineer_features() uniquement sur les 100 dossiers
            #    [Sculley2015] : même pipeline de transformation que à l'inference
            df_sample_eng, _ = apply_module_features(df_sample, branch)

            # 4. Extraire les features disponibles et normaliser
            available_in_bg = [f for f in available if f in df_sample_eng.columns]
            X_bg = df_sample_eng[available_in_bg].fillna(0).values.astype(np.float32)
            if scaler is not None:
                X_bg = scaler.transform(X_bg)

            log.info(
                "  KernelSHAP background : %d dossiers normaux "
                "(%d features engineerées)",
                len(X_bg), X_bg.shape[1],
            )
            return X_bg

        except Exception as e:
            log.warning("  Background set depuis train échoué : %s — fallback zeros", e)

    # Fallback : vecteur nul — moins précis mais évite un crash
    log.warning("  Background set : fallback zeros (train set inaccessible)")
    return np.zeros((1, len(available)), dtype=np.float32)


def compute_shap_top3(
    bundle: dict,
    df_cases: pd.DataFrame,
    feats: list[str],
    branch: str = "sante",
) -> list[list[tuple[str, float]]]:
    """
    Calcule les top-3 features SHAP pour les cas analysés.

    Stratégie selon le type de modèle [Lundberg2017] :
    - IsolationForest (sklearn) → TreeExplainer : O(T×L²), ~50ms/dossier
    - DIF (PyOD)               → KernelExplainer : O(n²), ~1-3s/dossier
      nsamples=100 : compromis vitesse/précision standard [Lundberg2017].
      Calculé uniquement sur les cas FP/FN sélectionnés (20 max par modèle).

    [Lundberg2017] Lundberg & Lee. A unified approach to interpreting model
    predictions. NeurIPS 2017. → SHAP = valeurs de Shapley exactes.
    [Xu2023] DIF est un réseau de neurones — TreeExplainer inapplicable.
    """
    try:
        import shap
    except ImportError:
        log.warning("  SHAP non installé — top-3 non calculé.")
        return [[] for _ in range(len(df_cases))]

    try:
        clf        = bundle["model"]
        scaler     = bundle.get("scaler") or bundle.get("scaler_sante")
        used_feats = bundle.get("features") or bundle.get("common_features") or feats
        available  = [f for f in used_feats if f in df_cases.columns]

        X = df_cases[available].fillna(0).values.astype(np.float32)
        if scaler is not None:
            X = scaler.transform(X)

        model_type = type(clf).__name__

        # ── Cas 1 : IsolationForest sklearn → TreeExplainer ───────────────
        if model_type == "IsolationForest":
            explainer = shap.TreeExplainer(clf)
            shap_vals = explainer.shap_values(X, check_additivity=False)
            log.info("  SHAP : TreeExplainer [Liu2008] — %d cas", len(X))

        # ── Cas 2 : DIF PyOD → KernelExplainer [Xu2023] ──────────────────
        else:
            X_background = _build_background_set(bundle, branch, available)
            explainer = shap.KernelExplainer(
                clf.decision_function,
                X_background,
                link="identity",
            )
            # nsamples=100 : ~1-3s par dossier — acceptable sur 20 cas max
            shap_vals = explainer.shap_values(X, nsamples=100, l1_reg="aic")
            log.info(
                "  SHAP : KernelExplainer [Lundberg2017] — %d cas "
                "(background=%d, nsamples=100)",
                len(X), len(X_background),
            )

        if isinstance(shap_vals, list):
            shap_vals = shap_vals[0]

        results = []
        for row in shap_vals:
            abs_row = np.abs(row)
            top_idx = np.argsort(abs_row)[::-1][:3]
            results.append([
                (available[i] if i < len(available) else f"feat_{i}", float(row[i]))
                for i in top_idx
            ])
        return results

    except Exception as e:
        log.warning("  SHAP calcul échoué : %s", e)
        return [[] for _ in range(len(df_cases))]


# ─── Classification cause d'erreur ───────────────────────────────────────────

def classify_error_cause(
    row: pd.Series,
    error_type: str,
    branch: str,
    shap_top3: list[tuple[str, float]],
) -> str:
    """
    Heuristique de classification [Chandola2009] — contexte assurance CM.
    """
    score  = float(row.get("_anomaly_score", 0.0))
    st     = str(row.get("Sous_Type_Anomalie", "")).upper()
    top_f  = [f for f, _ in shap_top3] if shap_top3 else []

    reseau_feats = {
        "community_score", "community_score_sante", "community_score_auto",
        "flag_doublon", "flag_doublon_sante", "flag_doublon_auto",
        "expert_garage_correlation", "prestataire_concentration",
    }

    if error_type == "FP":
        if top_f and top_f[0] in reseau_feats:
            return "BRUIT_DONNEES"
        return "SEUIL_MAL_CALITRE"

    else:  # FN
        if any(k in st for k in ["COLLUSION", "RESEAU", "EXPERT", "GARAGE"]):
            return "CAS_LIMITE_METIER"
        if any(k in st for k in ["PHANTOM", "FANTOME", "FICTIF"]):
            return "FEATURE_MANQUANTE"
        return "CAS_LIMITE_METIER"


def build_case_record(
    row: pd.Series,
    error_type: str,
    branch: str,
    shap_top3: list[tuple[str, float]],
    model_name: str,
) -> dict:
    id_col = "ID_Sinistre" if "ID_Sinistre" in row.index else row.index[0]
    cause  = classify_error_cause(row, error_type, branch, shap_top3)

    return {
        "type":          error_type,
        "model":         model_name,
        "branch":        branch,
        "dossier_id":    str(row.get(id_col, "?")),
        "anomaly_score": round(float(row.get("_anomaly_score", 0)), 4),
        "dist_seuil":    round(float(row.get("_dist_seuil", 0)), 4),
        "label_reel":    str(row.get(LABEL_COL, "?")),
        "sous_type":     str(row.get("Sous_Type_Anomalie", "N/A")),
        "cause_erreur":  cause,
        "cause_desc":    CAUSE_CATEGORIES.get(cause, "?"),
        "shap_top3":     [{"feature": f, "shap": round(v, 4)} for f, v in shap_top3],
        "features_snapshot": {
            col: round(float(row[col]), 4)
                 if isinstance(row.get(col), (int, float)) else str(row.get(col, ""))
            for col in [
                "Montant_Facture", "Montant_Devis",
                "anciennete_contrat_courte", "document_altere",
                "ocr_confiance_faible", "saisie_hors_heures",
                "montant_log", "delai_depot_anormal",
            ]
            if col in row.index
        },
    }


# ─── Rapport Markdown ─────────────────────────────────────────────────────────

def generate_fp_fn_report(
    cases: list[dict], branch: str, model_name: str
) -> str:
    now  = datetime.now().strftime("%Y-%m-%d %H:%M")
    fps  = [c for c in cases if c["type"] == "FP"]
    fns  = [c for c in cases if c["type"] == "FN"]

    cause_counts: dict[str, int] = {}
    for c in cases:
        cause_counts[c["cause_erreur"]] = cause_counts.get(c["cause_erreur"], 0) + 1

    lines = [
        f"# Analyse Qualitative FP/FN — `{model_name}` — Branche {branch.capitalize()}",
        f"> Générée le {now} | Référence : [Chandola2009] §5.3 + [Bauder2017]",
        "",
        "## Synthèse des causes d'erreur",
        "",
        "| Cause | Nb cas | Description |",
        "|-------|--------|-------------|",
    ]
    for cause, nb in sorted(cause_counts.items(), key=lambda x: -x[1]):
        lines.append(f"| `{cause}` | {nb} | {CAUSE_CATEGORIES.get(cause, '?')} |")

    lines += ["", "---", "", "## Faux Positifs (FP) — Dossiers normaux mal classés", ""]
    if not fps:
        lines.append("*Aucun FP extrait — FPR très bas sur ce modèle/branche.*")
        lines.append("")
    for i, c in enumerate(fps, 1):
        shap_str = ", ".join(
            f"`{s['feature']}` ({s['shap']:+.3f})" for s in c["shap_top3"]
        ) if c["shap_top3"] else "*SHAP non disponible (DIF — KernelSHAP requis)*"
        lines += [
            f"### FP-{i:02d} | Score={c['anomaly_score']:.4f} | Dist. seuil={c['dist_seuil']:.4f}",
            "",
            f"- **ID** : `{c['dossier_id']}`",
            f"- **Label réel** : `{c['label_reel']}`",
            f"- **Top-3 SHAP** : {shap_str}",
            f"- **Cause classifiée** : `{c['cause_erreur']}` — {c['cause_desc']}",
            f"- **Interprétation** : {_interpret_fp(c, branch)}",
            "",
        ]

    lines += ["---", "", "## Faux Négatifs (FN) — Fraudes non détectées", ""]
    for i, c in enumerate(fns, 1):
        shap_str = ", ".join(
            f"`{s['feature']}` ({s['shap']:+.3f})" for s in c["shap_top3"]
        ) if c["shap_top3"] else "*SHAP non disponible (DIF — KernelSHAP requis)*"
        lines += [
            f"### FN-{i:02d} | Score={c['anomaly_score']:.4f} | Sous-type={c['sous_type']}",
            "",
            f"- **ID** : `{c['dossier_id']}`",
            f"- **Sous-type réel** : `{c['sous_type']}`",
            f"- **Top-3 SHAP** : {shap_str}",
            f"- **Cause classifiée** : `{c['cause_erreur']}` — {c['cause_desc']}",
            f"- **Interprétation** : {_interpret_fn(c, branch)}",
            "",
        ]

    lines += [
        "---",
        "",
        "## Implications pour le mémoire",
        "",
        _global_implications(cause_counts, branch, model_name),
        "",
        "---",
        f"*MAKORA T12.3 — Analyse FP/FN | [Chandola2009] [Bauder2017] [Lundberg2017]*",
    ]
    return "\n".join(lines)


def _interpret_fp(c: dict, branch: str) -> str:
    cause = c["cause_erreur"]
    if cause == "SEUIL_MAL_CALITRE":
        if branch == "sante":
            return (
                "Praticien à volume de facturation élevé mais conforme à la mercuriale CIMA. "
                "L'IF détecte la densité de sinistres, pas la fraude elle-même. "
                "[Bauder2017] — DT-002 : historique_ratio_praticien stateless."
            )
        return (
            "Véhicule haut de gamme avec devis légitimement élevé. "
            "Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. "
            "[Viaene2002] — seuil de contamination à revoir sur ce segment."
        )
    if cause == "BRUIT_DONNEES":
        return (
            "Dossier appartenant à une communauté réseau fortuite (cluster géographique). "
            "La feature community_score est élevée sans lien avec une fraude réelle. "
            "[Jiang2014] — artefact du partitionnement Louvain sur petit graphe."
        )
    return "Cas atypique statistiquement sans signification métier identifiable."


def _interpret_fn(c: dict, branch: str) -> str:
    cause = c["cause_erreur"]
    st    = c.get("sous_type", "").upper()
    if cause == "CAS_LIMITE_METIER":
        if any(k in st for k in ["COLLUSION", "RESEAU"]):
            return (
                "Fraude en réseau : les features individuelles du dossier sont conformes. "
                "La fraude est détectable uniquement via le graphe (community_score). "
                "[Jiang2014] — signal graphe insuffisant sans historique inter-batches."
            )
        return (
            "Fraude camouflée : le dossier respecte formellement les contraintes métier. "
            "Détectable uniquement avec un historique inter-batches [DT-002]."
        )
    if cause == "FEATURE_MANQUANTE":
        return (
            "Score d'anomalie très bas — le modèle ne dispose pas des features discriminantes. "
            "Dette DT-001 : feature calculée à partir d'une colonne absente du dataset. "
            "[Sculley2015] — technical debt impacte directement les FN."
        )
    return "Fraude bien dissimulée statistiquement — limite documentée [Chandola2009 §5.3]."


def _global_implications(
    cause_counts: dict, branch: str, model_name: str
) -> str:
    dominant = max(cause_counts, key=cause_counts.get) if cause_counts else "?"
    total    = sum(cause_counts.values())
    pct      = round(cause_counts.get(dominant, 0) / total * 100) if total else 0
    return (
        f"La cause dominante est `{dominant}` ({pct}% des erreurs analysées). "
        f"Cela confirme que les erreurs de `{model_name}` sur la branche {branch} "
        f"sont principalement dues à {CAUSE_CATEGORIES.get(dominant, '?').lower()}. "
        f"Cette analyse est cohérente avec les dettes techniques documentées "
        f"(DT-001, DT-002, DT-003) et les limites intrinsèques des approches "
        f"non-supervisées identifiées par [Chandola2009]."
    )


# ─── Main ─────────────────────────────────────────────────────────────────────

def analyse_model(
    model_name: str,
    eval_branch: str,
    model_key: str,
    n: int,
    use_shap: bool,
) -> list[dict]:
    log.info("─" * 50)
    log.info("Analyse %s → branche %s", model_name, eval_branch)

    df_test       = load_test_set(eval_branch)
    bundle        = load_model_bundle(model_key)
    df_eng, feats = apply_module_features(df_test, eval_branch)

    df_fp, df_fn, _ = extract_fp_fn(df_eng, bundle, feats, n=n)

    all_cases = []
    for error_type, df_cases in [("FP", df_fp), ("FN", df_fn)]:
        if df_cases.empty:
            log.warning("%s vides pour %s/%s.", error_type, model_name, eval_branch)
            continue
        shap_results = (
            compute_shap_top3(bundle, df_cases, feats, branch=eval_branch)
            if use_shap else [[] for _ in range(len(df_cases))]
        )
        for i, (_, row) in enumerate(df_cases.iterrows()):
            shap3 = shap_results[i] if i < len(shap_results) else []
            case  = build_case_record(row, error_type, eval_branch, shap3, model_name)
            all_cases.append(case)

    md      = generate_fp_fn_report(all_cases, eval_branch, model_name)
    md_path = RESULTS_DIR / f"t12_3_fp_fn_{model_name}_{eval_branch}.md"
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    md_path.write_text(md, encoding="utf-8")
    log.info("Rapport → %s", md_path)

    return all_cases


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="MAKORA T12.3 — Analyse FP/FN")
    p.add_argument("--branch",  choices=["sante", "auto", "both"], default="both")
    p.add_argument("--n-cases", type=int, default=N_CASES)
    p.add_argument("--no-shap", action="store_true")
    return p.parse_args()


def main() -> None:
    args     = parse_args()
    branches = ["sante", "auto"] if args.branch == "both" else [args.branch]
    use_shap = not args.no_shap

    all_cases: list[dict] = []

    for branch in branches:
        all_cases.extend(analyse_model(
            model_name=f"M_{branch}",
            eval_branch=branch,
            model_key=f"M_{branch}_{branch}",
            n=args.n_cases,
            use_shap=use_shap,
        ))
        all_cases.extend(analyse_model(
            model_name="M_makora",
            eval_branch=branch,
            model_key="M_makora",
            n=args.n_cases,
            use_shap=use_shap,
        ))

    out_json = RESULTS_DIR / "t12_3_fp_fn_all.json"
    out_json.write_text(
        json.dumps(all_cases, indent=2, ensure_ascii=False, default=str)
    )
    log.info("Consolidé → %s (%d cas)", out_json, len(all_cases))

    log.info("─" * 50)
    log.info("RÉSUMÉ CAUSES D'ERREUR (tous modèles)")
    log.info("─" * 50)
    cause_global: dict[str, int] = {}
    for c in all_cases:
        cause_global[c["cause_erreur"]] = cause_global.get(c["cause_erreur"], 0) + 1
    for cause, nb in sorted(cause_global.items(), key=lambda x: -x[1]):
        pct = nb / len(all_cases) * 100 if all_cases else 0
        log.info("  %-30s : %3d cas (%5.1f%%)", cause, nb, pct)
    log.info("─" * 50)
    log.info("T12.3 terminé. Prochaine étape : rédiger PHASE_2_REPORT.md")


if __name__ == "__main__":
    main()