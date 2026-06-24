"""
MODULE : api/schemas/audit.py
DESCRIPTION : Schémas Pydantic v2 pour le domaine HITL — décisions et audit.
"""
from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel


class DecisionCreate(BaseModel):
    decision: Literal["CONFIRMED", "REJECTED", "ESCALATED"]
    motif: str | None = None


class DecisionResponse(BaseModel):
    id: UUID
    analysis_id: UUID
    decision: str
    motif: str | None = None
    gestionnaire_id: UUID
    created_at: datetime
    model_config = {"from_attributes": True}


class AuditListItem(BaseModel):
    analysis_id: UUID
    claim_id: str | None = None
    branch: str | None = None
    anomaly_score: float
    is_anomaly: bool
    rca_category: str | None = None
    rca_subcategory: str | None = None
    decision_status: str
    created_at: datetime
    model_config = {"from_attributes": True}


class ShapContributionResponse(BaseModel):
    id: UUID
    feature_name: str
    shap_value: float
    feature_value: float | None = None
    direction: str
    rank: int
    model_config = {"from_attributes": True}


# ──── REMPLACER uniquement AuditStatsResponse ─────────────────────────────

class AuditStatsResponse(BaseModel):
    """
    KPIs HITL de la file d'audit — BUG-AUDIT-03.
    Ancien contrat (period_days, total_analyzed, …) remplacé par les
    4 champs attendus par AuditStats (frontend audit.types.ts).
    [Amershi2019] §IV.D — métriques HITL pour mesurer la boucle gestionnaire.
    """
    pending: int
    escalated: int
    decided_today: int
    confirmation_rate: float
    pending_diff_24h: int | None = None
    unassigned_escalations: int | None = None
