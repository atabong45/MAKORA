"""
MODULE : api/services/escalation_service.py
DESCRIPTION : Service escalades HITL — PENDING → IN_PROGRESS → RESOLVED.

MODIFICATIONS PHASE 1 :

REDESIGN-A — Suppression de la pré-assignation
  create_escalation : l'escalade part toujours PENDING, assigned_to = None.
  La pré-assignation d'auditeur depuis EscalationModal est supprimée.
  L'auditeur choisit lui-même son dossier via PATCH /assign.

REDESIGN-C + BUG-6 — resolve_escalation devient une transaction 3-en-1
  Avant : fermait seulement l'escalade, sans verdict ni Decision.
  Après : transaction atomique qui :
    1. Ferme l'escalade (RESOLVED, resolved_by, resolved_at)
    2. Crée un enregistrement Decision immuable (audit trail complet)
    3. Met à jour analysis.decision_status = decision_final
    4. Ferme la claim (statut = CLOSED) dans les deux cas

RÉFÉRENCES ACADÉMIQUES :
- [Amershi2019] Amershi et al. (2019). Software engineering for ML. ICSE.
  §IV.D — HITL à deux niveaux : l'auditeur senior doit rendre un verdict
  final traçable, pas seulement une note textuelle non structurée.
- [Lundberg2017] §explicabilité — la resolution_note documente la prise
  en compte (ou non) des features SHAP dans la décision auditeur.

DÉCISIONS DE CONCEPTION :
- resolve_escalation ne réutilise pas create_decision d'audit_service
  pour éviter l'import circulaire (audit_service ↔ escalation_service).
  La logique de création de Decision est dupliquée intentionnellement.
- Le champ Decision.gestionnaire_id reçoit l'UUID de l'auditeur.
  Sémantiquement incorrect (nom historique) mais fonctionnellement correct.
  À renommer decided_by dans une migration future (dette documentée).
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from api.schemas.escalations import EscalationAssign, EscalationCreate, EscalationResolve


def create_escalation(db: Session, data: EscalationCreate, escalated_by: UUID):
    """
    Crée une escalade PENDING non assignée.
    Phase 1 - Redesign A : la pré-assignation est supprimée.
    L'escalade démarre toujours en PENDING pour que les auditeurs
    disponibles puissent se saisir du dossier librement.
    """
    from core.db.models.hitl_graph import Escalation
    from core.db.models.pipeline import Analysis

    analysis = db.query(Analysis).filter(Analysis.id == data.analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse introuvable")

    esc = Escalation(
        analysis_id=data.analysis_id,
        escalated_by=escalated_by,
        motif_escalade=data.motif_escalade,
        assigned_to=None,       # Redesign A : toujours None à la création
        statut="PENDING",       # Redesign A : toujours PENDING
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
    assigned_to: UUID | None,
    offset: int,
    limit: int,
):
    from core.db.models.hitl_graph import Escalation
    from sqlalchemy.orm import joinedload

    q = db.query(Escalation).options(joinedload(Escalation.analysis))

    is_admin = "administrateur" in user_roles
    is_gestionnaire = "gestionnaire" in user_roles

    if not is_admin:
        if is_gestionnaire:
            # Le gestionnaire voit ses propres escalades (celles qu'il a créées)
            q = q.filter(Escalation.escalated_by == user_id)
        else:
            # Auditeur : ses assignées + les non-assignées disponibles
            q = q.filter(
                (Escalation.assigned_to == user_id) | (Escalation.assigned_to.is_(None))
            )

    if assigned_to:
        q = q.filter(Escalation.assigned_to == assigned_to)
    if statut:
        q = q.filter(Escalation.statut == statut)

    total = q.count()
    return total, q.order_by(Escalation.created_at.desc()).offset(offset).limit(limit).all()


def get_escalation(db: Session, escalation_id: UUID):
    from core.db.models.hitl_graph import Escalation

    esc = (
        db.query(Escalation)
        .options(joinedload(Escalation.analysis))
        .filter(Escalation.id == escalation_id)
        .first()
    )
    if not esc:
        raise HTTPException(status_code=404, detail="Escalade introuvable")
    return esc


def assign_escalation(db: Session, escalation_id: UUID, data: EscalationAssign):
    """Auto-assignation : l'auditeur passe son propre UUID."""
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
    db: Session,
    escalation_id: UUID,
    data: EscalationResolve,
    resolved_by: UUID,
):
    """
    Résolution d'une escalade — transaction atomique 3-en-1.
    Phase 1 - Redesign C + Bug 6.

    Étape 1 : clôture de l'escalade
    Étape 2 : création d'un enregistrement Decision (audit trail)
    Étape 3 : mise à jour de l'analyse + fermeture de la claim

    [Amershi2019] §IV.D — la résolution doit produire un verdict
    traçable qui referme la boucle HITL sur l'analyse concernée.
    """
    from core.db.models.hitl_graph import Escalation, Decision
    from core.db.models.pipeline import Analysis
    from core.db.models.sinistres import Claim

    esc = get_escalation(db, escalation_id)
    if esc.statut == "RESOLVED":
        raise HTTPException(status_code=400, detail="Escalade déjà résolue")

    now = datetime.now(tz=timezone.utc)

    # ── Étape 1 : clôturer l'escalade ────────────────────────────────────
    esc.resolution_note = data.resolution_note
    esc.statut = "RESOLVED"
    esc.resolved_at = now
    esc.resolved_by = resolved_by          # Bug 6 corrigé

    # ── Étape 2 : créer la Decision immuable ─────────────────────────────
    # gestionnaire_id reçoit l'UUID de l'auditeur (nom historique conservé).
    decision = Decision(
        analysis_id=esc.analysis_id,
        decision=data.decision_final,      # CONFIRMED ou REJECTED
        motif=data.resolution_note,
        gestionnaire_id=resolved_by,
    )
    db.add(decision)

    # ── Étape 3 : mettre à jour l'analyse et fermer la claim ─────────────
    analysis = (
        db.query(Analysis)
        .options(joinedload(Analysis.claim))
        .filter(Analysis.id == esc.analysis_id)
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analyse liée introuvable")

    analysis.decision_status = data.decision_final

    if analysis.claim:
        analysis.claim.statut = "CLOSED"

    # ── Commit atomique ───────────────────────────────────────────────────
    db.commit()
    db.refresh(esc)

    try:
        from core.audit_logger import log_decision
        log_decision(
            str(resolved_by),
            str(esc.analysis_id),
            data.decision_final,
            f"[ESCALADE {escalation_id}] {data.resolution_note}",
        )
    except Exception:
        # Le log est non-bloquant : une erreur d'audit ne doit pas
        # annuler une transaction déjà commitée.
        pass

    return esc


def get_pending_escalations(db: Session, offset: int, limit: int):
    """Escalades PENDING non assignées — onglet 'En attente'."""
    from core.db.models.hitl_graph import Escalation

    q = db.query(Escalation).filter(
        Escalation.statut == "PENDING",
        Escalation.assigned_to.is_(None),
    )
    total = q.count()
    return total, q.order_by(Escalation.created_at).offset(offset).limit(limit).all()