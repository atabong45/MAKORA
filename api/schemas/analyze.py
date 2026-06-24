"""
MODULE : api/schemas/analyze.py
DESCRIPTION : Schémas Pydantic v2 pour le pipeline d'analyse MAKORA.
Miroir de MAKORAOutput pour les réponses API.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class DossierInput(BaseModel):
    """Dossier brut envoyé pour analyse — champs libres selon la branche."""
    model_config = {"extra": "allow"}

    ID_Sinistre: str | None = None
    Montant_Facture: float | None = None
    Devise: str = "XAF"


class AnalyzeRequest(BaseModel):
    branch: str
    source: str = "api"
    dossiers: list[dict]

    def validate_branch(self) -> None:
        if self.branch not in ("sante", "auto", "vie", "agricole"):
            raise ValueError(f"Branche inconnue : {self.branch}")


class ShapFeature(BaseModel):
    name: str
    shap_value: float
    direction: str
    rank: int = 1


class RcaResult(BaseModel):
    category: str | None = None
    subcategory: str | None = None
    confidence: float | None = None
    rule_triggered: str | None = None
    top_features: list[ShapFeature] = []
    explanation_fr: str | None = None


class AnalysisResult(BaseModel):
    claim_id: str
    branch: str
    anomaly_score: float
    is_anomaly: bool
    processing_time_ms: float | None = None
    rca: RcaResult | None = None
    graph_analysis: dict | None = None
    decision_status: str = "PENDING"
    analysis_id: UUID | None = None


class AnalyzeBatchResponse(BaseModel):
    batch_id: str
    run_id: UUID | None = None
    branch: str
    processed: int
    anomalies_detected: int
    results: list[AnalysisResult]
    started_at: datetime
    completed_at: datetime


class RunStatusResponse(BaseModel):
    id: UUID
    branch_id: UUID | None = None
    branch_code: "str | None" = None
    run_type: str
    nb_dossiers: int
    nb_anomalies: int
    graph_enabled: bool
    started_at: datetime
    completed_at: datetime | None = None
    model_config = {"from_attributes": True}
