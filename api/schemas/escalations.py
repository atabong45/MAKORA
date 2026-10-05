"""
MODULE : api/schemas/escalations.py
DESCRIPTION : Schémas Pydantic v2 pour les escalades HITL.

MODIFICATIONS PHASE 1 :
- EscalationCreate : suppression de assigned_to (Redesign A).
  La pré-assignation d'auditeur est supprimée — l'auditeur se
  saisit lui-même des escalades disponibles via S'assigner.
- EscalationResolve : decision_final devient OBLIGATOIRE (Redesign C).
  L'auditeur doit rendre un verdict explicite CONFIRMED ou REJECTED.
  La résolution sans verdict final n'est plus acceptée.
- EscalationResponse : ajout resolved_by (Bug 6 corrigé).

RÉFÉRENCES ACADÉMIQUES :
- [Amershi2019] Amershi et al. (2019). Software engineering for ML. ICSE.
  §IV.D — Le HITL à deux niveaux exige que chaque auditeur rende
  un verdict explicite, pas seulement une note textuelle.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, field_validator


class EscalationCreate(BaseModel):
    """
    Payload POST /escalations/.
    Créé par un gestionnaire ou admin depuis le DecisionPanel.
    La pré-assignation a été supprimée (Phase 1 - Redesign A) :
    l'escalade part toujours en PENDING non assignée.
    """
    analysis_id: UUID
    motif_escalade: str

    @field_validator("motif_escalade")
    @classmethod
    def motif_not_empty(cls, v: str) -> str:
        if not v or len(v.strip()) < 10:
            raise ValueError("Le motif doit contenir au moins 10 caractères.")
        return v.strip()


class EscalationAssign(BaseModel):
    """
    Payload PATCH /escalations/{id}/assign.
    L'auditeur passe son propre UUID pour s'auto-assigner.
    """
    assigned_to: UUID


class EscalationResolve(BaseModel):
    """
    Payload PATCH /escalations/{id}/resolve.
    Phase 1 - Redesign C : decision_final est maintenant OBLIGATOIRE.
    L'auditeur doit explicitement confirmer ou rejeter la suspicion de fraude.
    La résolution déclenche côté service :
      1. Escalade → RESOLVED
      2. Decision créée (verdict auditeur)
      3. Analysis.decision_status = decision_final
      4. Claim.statut = CLOSED
    """
    decision_final: Literal["CONFIRMED", "REJECTED"]
    resolution_note: str

    @field_validator("resolution_note")
    @classmethod
    def note_not_empty(cls, v: str) -> str:
        if not v or len(v.strip()) < 20:
            raise ValueError("La note de résolution doit contenir au moins 20 caractères.")
        return v.strip()


class EscalationResponse(BaseModel):
    """
    Réponse sérialisée d'une escalade.
    Phase 1 : ajout de resolved_by (Bug 6 corrigé).
    """
    id: UUID
    analysis_id: UUID
    claim_id: UUID | None = None 
    escalated_by: UUID
    assigned_to: UUID | None = None
    resolved_by: UUID | None = None        # Phase 1 — Bug 6
    motif_escalade: str
    statut: str
    resolution_note: str | None = None
    created_at: datetime
    assigned_at: datetime | None = None
    resolved_at: datetime | None = None

    model_config = {"from_attributes": True}