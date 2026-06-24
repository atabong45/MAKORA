"""
MODULE : api/services/audit_service.py
DESCRIPTION : Service HITL — décisions gestionnaires, historique, statistiques.

CORRECTIONS APPLIQUÉES :

BUG-AUDIT-04 — list_analyses : filtre branch jamais appliqué
  Le paramètre branch était reçu mais ignoré dans le query.
  Fix : subquery Claim → Branch indépendante du joinedload existant.
  Référence : [Sculley2015] §4 NeurIPS 2015 — filtres silencieux = dette cachée.

BUG-AUDIT-03 — get_audit_stats : contrat backend ≠ contrat frontend
  L'ancienne AuditStatsResponse retournait period_days, total_analyzed,
  anomaly_count, anomaly_rate, decisions{}, top_rca_categories, by_branch.
  Le frontend (AuditStats dans audit.types.ts) attend :
    pending, escalated, decided_today, confirmation_rate.
  Réécriture complète sur les vraies tables Analysis et Decision.

RÉFÉRENCES ACADÉMIQUES :
- [Amershi2019] Amershi et al. (2019). Software engineering for ML. ICSE.
  §IV.D — Les boucles HITL imposent des contrats stricts UI↔backend.
  Le suivi de pending/escalated/confirmation_rate matérialise la boucle
  de feedback gestionnaire → modèle décrite dans ce protocole.
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML systems.
  NeurIPS 2015. — Filtres silencieux et pipeline jungles.
"""
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

from api.schemas.audit import AuditStatsResponse, DecisionCreate


# ─── Helpers privés ──────────────────────────────────────────────────────────

def _branch_claim_subquery(db: Session, branch: str):
    """
    Subquery retournant les Claim.id appartenant à une branche donnée.
    Utilisée par list_analyses et get_audit_stats pour filtrer sans
    interférer avec les joinedload d'eager-loading.
    [Sculley2015] — isolation des concerns dans le pipeline de requêtes.
    """
    from core.db.models.sinistres import Claim
    from core.db.models.referentiels import Branch as BranchModel
    return (
        db.query(Claim.id)
        .join(BranchModel, Claim.branch_id == BranchModel.id)
        .filter(BranchModel.code == branch)
        .scalar_subquery()
    )


# ─── Analyses ────────────────────────────────────────────────────────────────

def list_analyses(
    db: Session,
    branch: str | None,
    decision_status: str | None,
    score_min: float | None,
    date_from,
    date_to,
    offset: int,
    limit: int,
):
    """
    Liste les analyses avec filtres.

    BUG-UI-01  : joinedload(claim → branch) pour éviter le N+1.
    BUG-AUDIT-04 : filtre branch via _branch_claim_subquery —
      ne perturbe pas le joinedload d'eager-loading déjà configuré.
    """
    from core.db.models.pipeline import Analysis
    from core.db.models.sinistres import Claim

    q = db.query(Analysis).options(
        joinedload(Analysis.claim).joinedload(Claim.branch)
    )

    # BUG-AUDIT-04 : subquery indépendante du joinedload
    if branch:
        q = q.filter(Analysis.claim_id.in_(_branch_claim_subquery(db, branch)))

    if decision_status:
        q = q.filter(Analysis.decision_status == decision_status)
    if score_min is not None:
        q = q.filter(Analysis.anomaly_score >= score_min)
    if date_from:
        q = q.filter(Analysis.created_at >= date_from)
    if date_to:
        q = q.filter(Analysis.created_at <= date_to)

    total = q.count()
    items = (
        q.order_by(Analysis.anomaly_score.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return total, items


def get_analysis(db: Session, analysis_id: UUID):
    """Retourne une analyse par UUID avec ses relations claim et branch."""
    from core.db.models.pipeline import Analysis
    from core.db.models.sinistres import Claim

    a = (
        db.query(Analysis)
        .options(joinedload(Analysis.claim).joinedload(Claim.branch))
        .filter(Analysis.id == analysis_id)
        .first()
    )
    if not a:
        raise HTTPException(status_code=404, detail="Analyse introuvable")
    return a


def get_shap(db: Session, analysis_id: UUID):
    """Valeurs SHAP triées par rang pour une analyse donnée."""
    from core.db.models.pipeline import ShapContribution
    return (
        db.query(ShapContribution)
        .filter(ShapContribution.analysis_id == analysis_id)
        .order_by(ShapContribution.rank)
        .all()
    )


# ─── Décisions ───────────────────────────────────────────────────────────────

def create_decision(
    db: Session,
    analysis_id: UUID,
    data: DecisionCreate,
    gestionnaire_id: UUID,
):
    from core.db.models.pipeline import Analysis
    from core.db.models.hitl_graph import Decision

    analysis = get_analysis(db, analysis_id)
    decision = Decision(
        analysis_id=analysis_id,
        decision=data.decision,
        motif=data.motif,
        gestionnaire_id=gestionnaire_id,
    )
    db.add(decision)
    analysis.decision_status = data.decision
    if data.decision in ("CONFIRMED", "REJECTED"):
        from core.db.models.sinistres import Claim
        claim = db.query(Claim).filter(Claim.id == analysis.claim_id).first()
        if claim:
            claim.statut = "CLOSED"
    db.commit()
    db.refresh(decision)
    from core.audit_logger import log_decision
    log_decision(str(gestionnaire_id), str(analysis_id), data.decision, data.motif)
    return decision


def get_decisions_history(db: Session, analysis_id: UUID):
    from core.db.models.hitl_graph import Decision
    return (
        db.query(Decision)
        .filter(Decision.analysis_id == analysis_id)
        .order_by(Decision.created_at)
        .all()
    )


# ─── Statistiques ────────────────────────────────────────────────────────────

def get_audit_stats(
    db: Session, branch: str | None, period_days: int
) -> AuditStatsResponse:
    """
    BUG-AUDIT-03 : réécriture complète pour aligner le contrat backend
    sur AuditStats (frontend — audit.types.ts).

    KPIs calculés :
      pending           : COUNT analyses WHERE decision_status='PENDING'
      escalated         : COUNT analyses WHERE decision_status='ESCALATED'
      decided_today     : COUNT décisions créées dans les 24h glissantes
      confirmation_rate : CONFIRMED / (CONFIRMED + REJECTED) sur 7j glissants

    [Amershi2019] §IV.D — les métriques HITL permettent de mesurer
    l'efficacité de la boucle humain-machine sur les faux positifs.
    [Bauder2017] — le taux de confirmation est un proxy du taux de précision
    du modèle de détection tel que perçu par les gestionnaires.
    """
    from core.db.models.pipeline import Analysis
    from core.db.models.hitl_graph import Decision

    # ── Filtre optionnel par branche ──────────────────────────────────────
    branch_filter = []
    if branch:
        branch_filter.append(
            Analysis.claim_id.in_(_branch_claim_subquery(db, branch))
        )

    # ── pending ───────────────────────────────────────────────────────────
    pending = (
        db.query(Analysis)
        .filter(Analysis.decision_status == "PENDING", *branch_filter)
        .count()
    )

    # ── escalated ─────────────────────────────────────────────────────────
    escalated = (
        db.query(Analysis)
        .filter(Analysis.decision_status == "ESCALATED", *branch_filter)
        .count()
    )

    # ── decided_today : rolling 24h ───────────────────────────────────────
    since_24h = datetime.now(tz=timezone.utc) - timedelta(hours=24)
    decided_today = (
        db.query(Decision)
        .filter(Decision.created_at >= since_24h)
        .count()
    )

    # ── confirmation_rate : rolling 7j ────────────────────────────────────
    since_7d = datetime.now(tz=timezone.utc) - timedelta(days=7)
    confirmed_7d = (
        db.query(Decision)
        .filter(Decision.created_at >= since_7d, Decision.decision == "CONFIRMED")
        .count()
    )
    rejected_7d = (
        db.query(Decision)
        .filter(Decision.created_at >= since_7d, Decision.decision == "REJECTED")
        .count()
    )
    total_decided = confirmed_7d + rejected_7d
    confirmation_rate = round(confirmed_7d / total_decided, 4) if total_decided else 0.0

    return AuditStatsResponse(
        pending=pending,
        escalated=escalated,
        decided_today=decided_today,
        confirmation_rate=confirmation_rate,
    )