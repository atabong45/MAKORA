"""
MODULE : core/data_models.py
DESCRIPTION : Structures de données standardisées de sortie du pipeline MAKORA.
              Définit les types MAKORAOutput, RCAResult et FeatureSHAP utilisés
              par tous les composants du Kernel. Ce module ne contient AUCUNE
              logique métier — uniquement des conteneurs de données.

RÉFÉRENCES ACADÉMIQUES :
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML systems. NeurIPS.
  → Séparer les contrats de données du code de calcul réduit la dette technique.
- [Amershi2019] Amershi et al. (2019). Software Engineering for ML. ICSE.
  → Définir des types de sortie explicites facilite les tests et le monitoring.

DÉCISIONS DE CONCEPTION :
- Dataclasses Python (stdlib) plutôt que Pydantic pour ce module interne :
  légèreté, pas de dépendance externe, sérialisation manuelle simple.
  Pydantic est réservé à la validation du schéma universel (schema_validator.py).
- `MAKORAOutput` est immuable après création (frozen=False mais convention d'usage).
- `RCAResult.indeterminate()` est un constructeur sémantique pour le cas "aucune règle".
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# FeatureSHAP
# ---------------------------------------------------------------------------

@dataclass
class FeatureSHAP:
    """
    Contribution SHAP d'une feature individuelle pour un dossier.

    [Lundberg2017] Lundberg & Lee (2017). A unified approach to interpreting
    model predictions. NeurIPS.
    → shap_value est la contribution additive de la feature au score d'anomalie.
    → direction est redondant mais améliore la lisibilité côté API/UI.
    """

    name: str
    """Nom de la feature (ex: 'ratio_prix_mercuriale')."""

    shap_value: float
    """Valeur SHAP brute. Positif = contribue à l'anomalie, négatif = l'atténue."""

    direction: str
    """'positive' si shap_value > 0, 'negative' sinon."""

    rank: int
    """Rang dans le top-k (1 = plus contributif)."""

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "shap_value": round(self.shap_value, 6),
            "direction": self.direction,
            "rank": self.rank,
        }


# ---------------------------------------------------------------------------
# RCAResult
# ---------------------------------------------------------------------------

@dataclass
class RCAResult:
    """
    Résultat structuré du Moteur RCA (Root Cause Analysis).

    Produit par RCAEngine.apply_rules() — croise les valeurs SHAP avec les
    règles déclaratives du fichier YAML du module pour identifier la catégorie
    de fraude la plus probable.

    Pattern Chain of Responsibility [GoF1994] : la première règle qui matche
    fournit ce résultat.
    """

    category: str
    """Catégorie principale (ex: 'Fraude Intentionnelle', 'Erreur Administrative')."""

    subcategory: str
    """Sous-catégorie (ex: 'Surfacturation Prestataire', 'Upcoding')."""

    confidence: float
    """Confiance [0.0, 1.0] définie dans le YAML de la règle déclenchée."""

    rule_id: Optional[str] = None
    """Identifiant de la règle YAML déclenchée (ex: 'RCA_SURF_001')."""

    message_template: str = ""
    """Modèle de message d'explication (à interpoler par LLMNarrator)."""

    @classmethod
    def indeterminate(cls) -> "RCAResult":
        """
        Construit un RCAResult 'Indéterminé' lorsqu'aucune règle YAML ne matche.
        Confiance à 0.5 : le modèle détecte une anomalie mais ne peut pas la classer.
        """
        return cls(
            category="Indéterminé",
            subcategory="Aucune règle déclenchée",
            confidence=0.5,
            rule_id=None,
            message_template=(
                "Anomalie détectée (score={anomaly_score:.2f}) sans correspondance "
                "dans les règles RCA du module. Un examen manuel est recommandé."
            ),
        )

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "subcategory": self.subcategory,
            "confidence": round(self.confidence, 4),
            "rule_id": self.rule_id,
            "message_template": self.message_template,
        }


# ---------------------------------------------------------------------------
# MAKORAOutput
# ---------------------------------------------------------------------------

@dataclass
class MAKORAOutput:
    """
    Sortie standardisée du pipeline MAKORA pour un dossier analysé.

    Ce type est le contrat de sortie universel : il est identique quelle que
    soit la branche d'assurance (Santé, Auto, Vie...). Les champs
    branch-spécifiques sont encodés dans rca_result et shap_top_k.

    Référence au BF-03 (détection ML) et BF-04 (RCA explicable) du cahier
    des charges.
    """

    # Identification
    dossier_id: str
    """Identifiant unique du dossier (col 'Dossier_ID' du schéma universel)."""

    branch: str
    """Branche d'assurance (ex: 'sante', 'auto'). Provient du module actif."""

    # Détection
    anomaly_score: float
    """Score d'anomalie normalisé [0.0, 1.0]. 1.0 = anomalie certaine."""

    is_anomaly: bool
    """True si anomaly_score >= threshold configuré dans le YAML du module."""

    detector_name: str
    """Nom de l'algorithme utilisé (ex: 'isolation_forest', 'lof')."""

    # Explicabilité — uniquement peuplé si is_anomaly=True
    shap_top_k: list[FeatureSHAP] = field(default_factory=list)
    """Top-k features SHAP contributrices. Vide si is_anomaly=False."""

    # RCA — uniquement peuplé si RCAEngine disponible et is_anomaly=True
    rca_result: Optional[RCAResult] = None
    """Diagnostic RCA structuré. None si RCAEngine non configuré."""

    # Narration — uniquement peuplé si LLMNarrator disponible et is_anomaly=True
    explanation_fr: Optional[str] = None
    """Explication en français générée par Qwen 2.5:7b (ou fallback template)."""

    # Méta
    processing_time_ms: float = 0.0
    """Temps de traitement total du pipeline en millisecondes."""

    model_version: str = "unknown"
    """Version/hash du modèle utilisé — pour l'auditabilité."""

    errors: list[str] = field(default_factory=list)
    """Erreurs non-bloquantes rencontrées pendant le traitement."""

    # Optionnel — peuplé si flux documentaire OCR (SS-02)
    ocr_metadata: Optional["OCRResult"] = None

    # Optionnel — peuplé si graph_analysis activé dans le module
    graph_analysis: Optional[dict] = None


    timestamp: str = field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z"
    )
    """Horodatage UTC ISO-8601 de l'analyse."""

    

    @property
    def is_high_severity(self) -> bool:
        """True si anomaly_score >= 0.85 — seuil de sévérité haute."""
        return self.anomaly_score >= 0.85

    def to_dict(self) -> dict:
        """Sérialisation JSON-compatible pour l'API."""
        return {
            "dossier_id": self.dossier_id,
            "branch": self.branch,
            "anomaly_score": round(self.anomaly_score, 6),
            "is_anomaly": self.is_anomaly,
            "detector_name": self.detector_name,
            "is_high_severity": self.is_high_severity,
            "shap_top_k": [f.to_dict() for f in self.shap_top_k],
            "rca_result": self.rca_result.to_dict() if self.rca_result else None,
            "explanation_fr": self.explanation_fr,
            "processing_time_ms": round(self.processing_time_ms, 2),
            "model_version": self.model_version,
            "errors": self.errors,
            "timestamp": self.timestamp,
            "ocr_metadata": self.ocr_metadata.to_dict() if self.ocr_metadata else None,
            "graph_analysis": self.graph_analysis,
        }


# ---------------------------------------------------------------------------
# OCRResult — à ajouter à la FIN de core/data_models.py
# ---------------------------------------------------------------------------

@dataclass
class OCRResult:
    """
    Résultat immutable du pipeline OCR documentaire.

    Ce type est une preuve forensique : une fois créé, aucun champ
    extrait ne doit être modifié. L'UI peut afficher ces valeurs pour
    information, mais l'écriture revient uniquement au DocumentaryReader.

    ADR-008 : OCR dual PaddleOCR + Tesseract, arbitrage LLM.
    Si LLM KO → success=False, error="LLM_KO". Pas de regex en fallback.

    RÉFÉRENCES :
    - [Wei2022] Wei et al. (2022). Chain-of-thought prompting. NeurIPS.
      → Justifie l'usage du LLM pour structurer la sortie OCR brute.
    - [Jiang2023] Jiang et al. (2023). Mistral 7B. arXiv:2310.06825.
      → Modèle local utilisé pour l'extraction JSON structuré.
    """

    # ------------------------------------------------------------------
    # Champs extraits par le LLM depuis les textes OCR bruts (nullable)
    # ------------------------------------------------------------------
    montant_facture: Optional[float] = None
    """Montant total facturé, normalisé en XAF."""

    devise: Optional[str] = None
    """Devise normalisée : 'XAF'. FCFA → XAF à l'extraction."""

    date_soin: Optional[str] = None
    """Date des soins au format YYYY-MM-DD."""

    code_acte: Optional[str] = None
    """Code ASAC (Cameroun) ou CCAM (France) de l'acte médical."""

    nom_praticien: Optional[str] = None
    """Nom du praticien tel qu'extrait du document."""

    etablissement: Optional[str] = None
    """Nom de l'établissement de soins."""

    # ------------------------------------------------------------------
    # Métadonnées forensiques — toujours calculées indépendamment du LLM
    # ------------------------------------------------------------------
    presence_cachet: bool = False
    """True si un cachet humide (rond, bleu/rouge) est détecté via HSV OpenCV."""

    flag_altere: bool = False
    """True si les métadonnées EXIF indiquent une retouche logicielle."""

    logiciel_retouche: Optional[str] = None
    """Nom du logiciel détecté dans les EXIF (ex: 'Adobe Photoshop', 'GIMP')."""

    hash_image: str = ""
    """SHA-256 de l'image originale — traçabilité forensique."""

    # ------------------------------------------------------------------
    # Scores de confiance OCR
    # ------------------------------------------------------------------
    score_confiance_global: float = 0.0
    """Score de confiance moyen sur tous les mots OCR. [0.0, 1.0]"""

    score_confiance_montant: float = 0.0
    """Score de confiance sur le token montant spécifiquement. [0.0, 1.0]"""

    # ------------------------------------------------------------------
    # Statut du pipeline
    # ------------------------------------------------------------------
    success: bool = False
    """False si le pipeline a échoué (qualité insuffisante, LLM KO...)."""

    error: Optional[str] = None
    """
    Code d'erreur si success=False :
    - 'QUALITE_INSUFFISANTE' : score_confiance_global < 0.30
    - 'LLM_KO'              : Ollama indisponible ou timeout
    - 'OCR_ENGINES_KO'      : PaddleOCR et Tesseract tous deux absents
    - 'PDF_PROTEGE'         : PDF avec mot de passe
    """

    def to_dict(self) -> dict:
        """Sérialisation pour l'API — champ ocr_metadata de MAKORAOutput."""
        return {
            "applicable": True,
            "success": self.success,
            "error": self.error,
            "champs_extraits": {
                "montant_facture": self.montant_facture,
                "devise": self.devise,
                "date_soin": self.date_soin,
                "code_acte": self.code_acte,
                "nom_praticien": self.nom_praticien,
                "etablissement": self.etablissement,
            },
            "forensique": {
                "presence_cachet_humide": self.presence_cachet,
                "flag_document_altere": self.flag_altere,
                "logiciel_retouche_detecte": self.logiciel_retouche,
                "hash_image": self.hash_image,
            },
            "confiance": {
                "score_global": round(self.score_confiance_global, 4),
                "score_montant": round(self.score_confiance_montant, 4),
            },
        }

    @classmethod
    def pipeline_ko(cls, error_code: str) -> "OCRResult":
        """Constructeur sémantique pour un échec pipeline — évite les None éparpillés."""
        return cls(success=False, error=error_code)