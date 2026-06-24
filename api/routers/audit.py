"""
MODULE : api/routers/audit.py
DESCRIPTION : Router FastAPI — Audit HITL (6 endpoints).

CORRECTION BUG-UI-01 (TEST_REPORT_G1_G3.md) :
  L'ancienne sérialisation de list_analyses retournait :
    {"id": str(a.id), "anomaly_score": ..., "is_anomaly": ...,
     "decision_status": ..., "created_at": ...}

  Deux problèmes :
  1. Le champ était nommé "id" alors que le frontend attend "analysis_id"
     (type AuditListItem.analysis_id — audit.types.ts).
  2. Les champs "claim_id" et "branch" étaient absents, laissant la colonne
     SINISTRE entièrement vide dans DashboardAuditWidget et AuditQueueTable.

  Fix :
  - Renommer "id" → "analysis_id"
  - Ajouter "claim_id" via la relation a.claim.claim_id (lazy-load SQLAlchemy)
  - Ajouter "branch" via a.claim.branch.code
  - audit_service.list_analyses utilise désormais joinedload pour éviter
    les requêtes N+1 (voir api/services/audit_service.py).
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps.auth import get_current_active_user
from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.audit import (
    AuditListItem,
    AuditStatsResponse,
    DecisionCreate,
    DecisionResponse,
    ShapContributionResponse,
)
from api.schemas.common import PaginatedResponse
from api.services import audit_service as svc
from core.db.models.iam import User

router = APIRouter(prefix="/audit", tags=["Audit HITL"])
_access = Depends(require_roles("gestionnaire", "auditeur", "administrateur"))
_decide = Depends(require_roles("gestionnaire", "auditeur"))


@router.get("/stats", response_model=AuditStatsResponse)
def get_stats(
    branch: str | None = Query(None),
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    return svc.get_audit_stats(db, branch, period_days)


@router.get("/", response_model=PaginatedResponse[dict])
def list_analyses(
    branch: str | None = Query(None),
    decision_status: str | None = Query(None),
    score_min: float | None = Query(None, ge=0.0, le=1.0),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = _access,
):
    total, items = svc.list_analyses(
        db, branch, decision_status, score_min,
        date_from, date_to,
        (page - 1) * page_size, page_size,
    )

    # BUG-UI-01 : "analysis_id" + "claim_id" + "branch" requis par le frontend.
    # La relation a.claim est chargée via joinedload dans list_analyses (service).
    results = [
        {
            "analysis_id": str(a.id),
            "claim_id": a.claim.claim_id if a.claim else None,
            "branch": a.claim.branch.code if (a.claim and a.claim.branch) else None,
            "anomaly_score": a.anomaly_score,
            "is_anomaly": a.is_anomaly,
            "rca_category": a.rca_category,
            "decision_status": a.decision_status,
            "created_at": str(a.created_at),
        }
        for a in items
    ]
    return PaginatedResponse(
        total=total, page=page, page_size=page_size, results=results
    )


# ──── REMPLACER l'entier bloc get_analysis ────────────────────────────────

@router.get("/{analysis_id}", response_model=dict)
def get_analysis(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    _: User = _access,
):
    # BUG-AUDIT-01 : "id" → "analysis_id" (contrat analysis.types.ts)
    # BUG-AUDIT-02 : construction de l'objet rca imbriqué + top_features
    #   depuis ShapContribution (table séparée). Le frontend attend
    #   AnalysisResult.rca: RcaResult | null, pas des champs plats.
    a = svc.get_analysis(db, analysis_id)
    shap_items = svc.get_shap(db, analysis_id)

    top_features = [
        {
            "name": s.feature_name,
            "shap_value": float(s.shap_value),
            "direction": s.direction,
            "rank": s.rank,
        }
        for s in shap_items[:3]
    ]

    rca = None
    if a.rca_category is not None or top_features:
        rca = {
            "category": a.rca_category,
            "subcategory": a.rca_subcategory,
            "confidence": None,
            "rule_triggered": None,
            "top_features": top_features,
            "explanation_fr": a.explanation_fr,
        }

    return {
        "analysis_id": str(a.id),
        "claim_id": a.claim.claim_id if a.claim else None,
        "branch": a.claim.branch.code if (a.claim and a.claim.branch) else None,
        "anomaly_score": a.anomaly_score,
        "is_anomaly": a.is_anomaly,
        "processing_time_ms": None,
        "rca": rca,
        "graph_analysis": None,
        "decision_status": a.decision_status,
    }


@router.post(
    "/{analysis_id}/decision",
    response_model=DecisionResponse,
    status_code=201,
)
def create_decision(
    analysis_id: UUID,
    data: DecisionCreate,
    db: Session = Depends(get_db),
    current_user: User = _decide,
):
    return svc.create_decision(db, analysis_id, data, current_user.id)


@router.get(
    "/{analysis_id}/decisions",
    response_model=list[DecisionResponse],
)
def get_decisions(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    _: User = _access,
):
    return svc.get_decisions_history(db, analysis_id)


@router.get(
    "/{analysis_id}/shap",
    response_model=list[ShapContributionResponse],
)
def get_shap(
    analysis_id: UUID,
    db: Session = Depends(get_db),
    _: User = _access,
):
    return svc.get_shap(db, analysis_id)

