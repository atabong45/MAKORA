"""
MODULE : api/routers/escalations.py
DESCRIPTION : Router FastAPI — Escalades HITL (6 endpoints).

CORRECTIONS APPLIQUÉES :

BUG-ESCAL-01 — list_escalations : assigned_to ignoré
  Ajout du query param assigned_to: UUID | None.
  Permet à l'onglet "Mes escalades" du frontend de filtrer correctement.

BUG-ESCAL-03 — RBAC : gestionnaire ne pouvait pas voir les escalades
  Ajout de _read = require_roles("gestionnaire", "auditeur", "administrateur")
  pour les endpoints de lecture (GET / et GET /{id}).
  Le gestionnaire peut donc consulter les escalades qu'il a créées.
  Les endpoints mutants (assign, resolve) restent réservés aux auditeurs.

RÉFÉRENCES ACADÉMIQUES :
- [Amershi2019] §IV.D — HITL à deux niveaux : le gestionnaire escalade,
  l'auditeur senior arbitre. Les deux rôles doivent pouvoir lire les
  escalades pour que la boucle de feedback fonctionne.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps.auth import get_current_active_user
from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.common import PaginatedResponse
from api.schemas.escalations import (
    EscalationAssign, EscalationCreate, EscalationResolve, EscalationResponse,
)
from api.services import escalation_service as svc
from core.db.models.iam import User

router = APIRouter(prefix="/escalations", tags=["Escalades"])

# Création : gestionnaire uniquement (il escalade depuis DecisionPanel)
_gestionnaire = Depends(require_roles("gestionnaire"))

# Lecture : gestionnaire + auditeur + admin — BUG-ESCAL-03
_read = Depends(require_roles("gestionnaire", "auditeur", "administrateur"))

# Mutation (assign/resolve) : auditeur + admin uniquement
_auditeur = Depends(require_roles("auditeur", "administrateur"))


@router.post("/", response_model=EscalationResponse, status_code=201)
def create_escalation(
    data: EscalationCreate,
    db: Session = Depends(get_db),
    current_user: User = _gestionnaire,
):
    return svc.create_escalation(db, data, current_user.id)


@router.get("/pending", response_model=PaginatedResponse[EscalationResponse])
def get_pending(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = _read,
):
    total, items = svc.get_pending_escalations(db, (page - 1) * page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)


@router.get("/", response_model=PaginatedResponse[EscalationResponse])
def list_escalations(
    statut: str | None = Query(None),
    # BUG-ESCAL-01 : query param pour filtrer par auditeur assigné
    assigned_to: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = _read,  # BUG-ESCAL-03 : _read (inclut gestionnaire)
):
    roles = [ur.role.name for ur in current_user.user_roles]
    total, items = svc.list_escalations(
        db, current_user.id, roles, statut, assigned_to,
        (page - 1) * page_size, page_size,
    )
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)


@router.get("/{escalation_id}", response_model=EscalationResponse)
def get_escalation(
    escalation_id: UUID,
    db: Session = Depends(get_db),
    _: User = _read,  # BUG-ESCAL-03 : _read (inclut gestionnaire)
):
    return svc.get_escalation(db, escalation_id)


@router.patch("/{escalation_id}/assign", response_model=EscalationResponse)
def assign_escalation(
    escalation_id: UUID,
    data: EscalationAssign,
    db: Session = Depends(get_db),
    _: User = _auditeur,
):
    return svc.assign_escalation(db, escalation_id, data)


@router.patch("/{escalation_id}/resolve", response_model=EscalationResponse)
def resolve_escalation(
    escalation_id: UUID,
    data: EscalationResolve,
    db: Session = Depends(get_db),
    current_user: User = _auditeur,
):
    return svc.resolve_escalation(db, escalation_id, data, current_user.id)