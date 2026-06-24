"""
MODULE : api/schemas/escalations.py
DESCRIPTION : Schémas Pydantic v2 pour les escalades HITL.
"""
from datetime import datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel


class EscalationCreate(BaseModel):
    analysis_id: UUID
    motif_escalade: str
    # BUG-ESCAL-02 : sélecteur d'auditeur (EscalationModal.tsx).
    # Si None → le backend laisse PENDING non-assigné (auditeur choisit).
    assigned_to: UUID | None = None


class EscalationAssign(BaseModel):
    assigned_to: UUID


class EscalationResolve(BaseModel):
    resolution_note: str


class EscalationResponse(BaseModel):
    id: UUID
    analysis_id: UUID
    escalated_by: UUID
    assigned_to: UUID | None = None
    motif_escalade: str
    statut: str
    resolution_note: str | None = None
    created_at: datetime
    assigned_at: datetime | None = None
    resolved_at: datetime | None = None
    model_config = {"from_attributes": True}
