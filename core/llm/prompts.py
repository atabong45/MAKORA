"""
MODULE : core/llm/prompts.py
DESCRIPTION : Templates de prompts pour la narration LLM (Qwen 2.5:7b).

RÉFÉRENCES ACADÉMIQUES :
- [Wei2022] Wei et al. (2022). Chain-of-thought prompting elicits reasoning
  in large language models. NeurIPS.
  → Le prompt structure le raisonnement en étapes : contexte → analyse →
    conclusion → recommandation. Meilleure cohérence narrative.
- [Jiang2023] Jiang et al. (2023). Mistral 7B. arXiv:2310.06825.
  → Même si Qwen 2.5:7b est retenu (ADR-003), la structure de prompt
    instruction-following est compatible avec les deux modèles.

DÉCISIONS DE CONCEPTION :
- Les prompts sont externalisés ici, jamais dans narrator.py.
  Facilite la modification sans toucher à la logique LLM.
- Le prompt système impose le JSON structuré pour le parsing robuste.
- La langue cible est le FRANÇAIS — contexte camerounais/africain.
- Les montants sont exprimés en XAF (Franc CFA CIMA).
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Prompt système — injecté en system message à chaque appel
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es un expert en détection de fraude en assurance santé \
dans le contexte camerounais (mercuriale CIMA, nomenclature ASAC).
Tu reçois un dossier suspect analysé par le système MAKORA.
Tu dois produire une explication claire, factuelle et professionnelle \
en FRANÇAIS, destinée à un gestionnaire de sinistres non-technique.

Réponds UNIQUEMENT avec un objet JSON valide, sans balises markdown, \
sans texte avant ou après le JSON.
Format attendu :
{
  "titre": "titre court du diagnostic (max 10 mots)",
  "resume": "résumé en 1 phrase du problème détecté",
  "analyse": "analyse détaillée en 2-3 phrases (causes probables, indices)",
  "recommandation": "action concrète recommandée au gestionnaire"
}"""


# ---------------------------------------------------------------------------
# Builder de prompt utilisateur
# ---------------------------------------------------------------------------

def build_user_prompt(context: dict[str, Any]) -> str:
    """
    Construit le prompt utilisateur à partir du contexte du dossier.

    [Wei2022] : structure chain-of-thought — fournir le contexte complet
    améliore la cohérence et réduit les hallucinations.

    Args:
        context: dict avec clés dossier_id, anomaly_score, top_features,
                 rca_diagnostic.

    Returns:
        str — prompt utilisateur formaté.
    """
    dossier_id = context.get("dossier_id", "INCONNU")
    score = float(context.get("anomaly_score", 0.0))
    top_features = context.get("top_features", [])
    rca = context.get("rca_diagnostic", {})

    # Formatage des features SHAP
    features_txt = ""
    if top_features:
        lines = []
        for f in top_features[:3]:  # top 3 uniquement
            name = f.get("feature_name", f.get("name", "?"))
            val = f.get("feature_value", f.get("value", "?"))
            shap = f.get("shap_value", 0.0)
            direction = "↑ suspect" if float(shap) > 0 else "↓ normal"
            lines.append(f"  - {name} = {val:.3f} ({direction}, SHAP={shap:.3f})")
        features_txt = "\n".join(lines)
    else:
        features_txt = "  (non disponibles)"

    # Formatage du diagnostic RCA
    if rca and rca.get("category") and rca.get("category") != "Indéterminée":
        rca_txt = (
            f"Catégorie : {rca.get('category', '?')}\n"
            f"Sous-catégorie : {rca.get('subcategory', '?')}\n"
            f"Règle déclenchée : {rca.get('rule_triggered', '?')}\n"
            f"Confiance diagnostic : {float(rca.get('confidence', 0)):.0%}"
        )
    else:
        rca_txt = "Aucune règle RCA n'a matché — anomalie statistique non catégorisée."

    return f"""DOSSIER À ANALYSER :
Identifiant : {dossier_id}
Score d'anomalie MAKORA : {score:.3f} (seuil alerte : 0.70)

FEATURES CONTRIBUTIVES (SHAP) :
{features_txt}

DIAGNOSTIC RCA :
{rca_txt}

Génère l'explication JSON pour le gestionnaire."""


def build_fallback_narration(context: dict[str, Any]) -> str:
    """
    Narration de secours si Ollama est indisponible.
    Utilisée par LLMNarrator en mode dégradé.

    Args:
        context: même format que build_user_prompt().

    Returns:
        str — texte de narration en français.
    """
    dossier_id = context.get("dossier_id", "INCONNU")
    score = float(context.get("anomaly_score", 0.0))
    rca = context.get("rca_diagnostic", {})

    rca_part = ""
    if rca and rca.get("category") and rca.get("category") != "Indéterminée":
        rca_part = (
            f"Diagnostic : {rca.get('category')} — {rca.get('subcategory', '')}. "
            f"Confiance : {float(rca.get('confidence', 0)):.0%}. "
        )

    return (
        f"Anomalie détectée pour le dossier {dossier_id} "
        f"(score : {score:.2f}). "
        f"{rca_part}"
        f"Un examen approfondi par un gestionnaire est recommandé."
    )


# ---------------------------------------------------------------------------
# PROMPT OCR — à ajouter dans core/llm/prompts.py
# ---------------------------------------------------------------------------
# [Wei2022] Wei et al. (2022). Chain-of-thought prompting. NeurIPS.
#   → Prompt structuré avec exemples implicites pour forcer le JSON valide.
# [Jiang2023] Jiang et al. (2023). Mistral 7B / Qwen 2.5:7b.
#   → Modèle local Ollama — instruction-following strict requis.
#
# DÉCISION DE CONCEPTION :
# Le LLM reçoit les deux textes OCR bruts (PaddleOCR + Tesseract).
# Il est le seul responsable de la structuration — pas de regex en fallback
# (ADR-008). Si le LLM est KO, le pipeline retourne OCRResult.pipeline_ko("LLM_KO").
# ---------------------------------------------------------------------------

OCR_SYSTEM_PROMPT = """Tu es un extracteur de données de documents médicaux et assurantiels.
Tu reçois le texte brut extrait par deux moteurs OCR différents d'un même document.
Ta tâche est de fusionner ces deux textes, corriger les erreurs OCR évidentes, et extraire les champs demandés.
Réponds UNIQUEMENT avec un objet JSON valide. Aucun texte avant ou après le JSON. Aucun backtick."""

OCR_EXTRACTION_PROMPT = """\
Voici les résultats de deux moteurs OCR sur le même document :

INSTRUCTIONS DE ROBUSTESSE :
- Si les deux textes OCR (PaddleOCR et Tesseract) sont vides ou illisibles,
  retourne TOUS les champs à null. Ne pas inventer de valeurs.
- Si tu ne peux pas extraire un champ avec certitude, mets-le à null
  plutôt que de deviner.
- Réponds UNIQUEMENT en JSON valide selon le schéma demandé,
  même si tous les champs sont null.

=== Texte OCR moteur 1 (PaddleOCR) ===
{paddle_text}

=== Texte OCR moteur 2 (Tesseract) ===
{tesseract_text}

Extrais les champs suivants. Si un champ est absent ou illisible dans les deux textes, retourne null.

Règles :
- montant_facture : nombre décimal (ex: 45000.0). Ignore la devise.
- devise : normalise en "XAF". Si "FCFA" → "XAF". Si "EUR" → "EUR".
- date_soin : format YYYY-MM-DD uniquement. Si format DD/MM/YYYY → convertir.
- code_acte : code alphanumérique ASAC (ex: "CS001") ou CCAM français. Prends le plus lisible des deux OCR.
- nom_praticien : nom complet. Ignore "Dr." ou "Docteur" comme préfixe.
- etablissement : nom de la clinique, hôpital ou cabinet.
- presence_cachet : true si le texte mentionne un cachet, tampon, sceau ou signature officielle visible.

Réponds avec ce JSON et rien d'autre :
{{
  "montant_facture": <float ou null>,
  "devise": <string ou null>,
  "date_soin": <string YYYY-MM-DD ou null>,
  "code_acte": <string ou null>,
  "nom_praticien": <string ou null>,
  "etablissement": <string ou null>,
  "presence_cachet": <true ou false>
}}"""


def build_ocr_prompt(paddle_text: str, tesseract_text: str) -> str:
    """
    Construit le prompt utilisateur pour la structuration OCR.

    Args:
        paddle_text : texte brut extrait par PaddleOCR (peut être vide).
        tesseract_text : texte brut extrait par Tesseract.

    Returns:
        Prompt formaté prêt à envoyer à Ollama.
    """
    paddle_clean = paddle_text.strip() or "(aucun résultat)"
    tesseract_clean = tesseract_text.strip() or "(aucun résultat)"
    return OCR_EXTRACTION_PROMPT.format(
        paddle_text=paddle_clean,
        tesseract_text=tesseract_clean,
    )