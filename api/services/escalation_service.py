"""
MODULE : api/services/escalation_service.py
DESCRIPTION : Service escalades HITL — workflow PENDING → IN_PROGRESS → RESOLVED.

CORRECTIONS APPLIQUÉES :

BUG-ESCAL-02 — create_escalation : assigned_to ignoré
  EscalationCreate accepte désormais assigned_to (UUID | None).
  Si fourni, l'escalade démarre directement en IN_PROGRESS avec l'auditeur
  pré-assigné. Sinon elle reste PENDING pour assignation ultérieure.

BUG-ESCAL-01 — list_escalations : filtre assigned_to absent
  Ajout du paramètre assigned_to: UUID | None.
  Permet l'onglet "Mes escalades" du frontend (assigned_to=user.id).

BUG-ESCAL-03 — Visibilité gestionnaire
  Un gestionnaire (rôle ≠ auditeur) peut désormais voir ses propres
  escalades (celles qu'il a créées) via le filtre escalated_by.
  Les auditeurs voient leurs assignées + les non-assignées (inchangé).
  Les admins voient tout (inchangé).

RÉFÉRENCES ACADÉMIQUES :
- [Amershi2019] Amershi et al. (2019). Software engineering for ML. ICSE.
  §IV.D — La traçabilité HITL requiert que chaque acteur (gestionnaire,
  auditeur) ait accès aux escalades qui le concernent.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.schemas.escalations import EscalationAssign, EscalationCreate, EscalationResolve


def create_escalation(db: Session, data: EscalationCreate, escalated_by: UUID):
    from core.db.models.hitl_graph import Escalation
    from core.db.models.pipeline import Analysis

    analysis = db.query(Analysis).filter(Analysis.id == data.analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    # BUG-ESCAL-02 : si assigned_to fourni → pré-assignation directe
    statut = "IN_PROGRESS" if data.assigned_to else "PENDING"
    assigned_at = datetime.now(tz=timezone.utc) if data.assigned_to else None

    esc = Escalation(
        analysis_id=data.analysis_id,
        escalated_by=escalated_by,
        motif_escalade=data.motif_escalade,
        assigned_to=data.assigned_to,   # BUG-ESCAL-02
        statut=statut,
        assigned_at=assigned_at,
    )
    db.add(esc)
    analysis.decision_status = "ESCALATED"
    db.commit()
    db.refresh(esc)
    return esc


def list_escalations(
    db: Session,
    user_id: UUID,
    user_roles: list[str],
    statut: str | None,
    assigned_to: UUID | None,   # BUG-ESCAL-01 : filtre explicite
    offset: int,
    limit: int,
):
    from core.db.models.hitl_graph import Escalation

    q = db.query(Escalation)

    is_admin = "administrateur" in user_roles
    is_gestionnaire = "gestionnaire" in user_roles

    if not is_admin:
        if is_gestionnaire:
            # BUG-ESCAL-03 : gestionnaire ne voit que ses propres escalades
            q = q.filter(Escalation.escalated_by == user_id)
        else:
            # Auditeur : ses assignées + les non-assignées (disponibles)
            q = q.filter(
                (Escalation.assigned_to == user_id) | (Escalation.assigned_to.is_(None))
            )

    # BUG-ESCAL-01 : filtre assigned_to explicite (onglet "Mes escalades")
    if assigned_to:
        q = q.filter(Escalation.assigned_to == assigned_to)

    if statut:
        q = q.filter(Escalation.statut == statut)

    total = q.count()
    return total, q.order_by(Escalation.created_at.desc()).offset(offset).limit(limit).all()


def get_escalation(db: Session, escalation_id: UUID):
    from core.db.models.hitl_graph import Escalation
    esc = db.query(Escalation).filter(Escalation.id == escalation_id).first()
    if not esc:
        raise HTTPException(status_code=404, detail="Escalade introuvable")
    return esc


def assign_escalation(db: Session, escalation_id: UUID, data: EscalationAssign):
    esc = get_escalation(db, escalation_id)
    if esc.statut == "RESOLVED":
        raise HTTPException(status_code=400, detail="Escalade déjà résolue")
    esc.assigned_to = data.assigned_to
    esc.statut = "IN_PROGRESS"
    esc.assigned_at = datetime.now(tz=timezone.utc)
    db.commit()
    db.refresh(esc)
    return esc


def resolve_escalation(
    db: Session, escalation_id: UUID, data: EscalationResolve, resolved_by: UUID
):
    esc = get_escalation(db, escalation_id)
    if esc.statut == "RESOLVED":
        raise HTTPException(status_code=400, detail="Escalade déjà résolue")
    esc.resolution_note = data.resolution_note
    esc.statut = "RESOLVED"
    esc.resolved_at = datetime.now(tz=timezone.utc)
    db.commit()
    db.refresh(esc)
    return esc


def get_pending_escalations(db: Session, offset: int, limit: int):
    from core.db.models.hitl_graph import Escalation
    q = db.query(Escalation).filter(
        Escalation.statut == "PENDING",
        Escalation.assigned_to.is_(None),
    )
    total = q.count()
    return total, q.order_by(Escalation.created_at).offset(offset).limit(limit).all()