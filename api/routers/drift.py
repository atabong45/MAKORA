"""
MODULE : api/routers/drift.py
DESCRIPTION : Router FastAPI — Drift monitoring PSI (5 endpoints).
Référence : [Gama2014] — seuils STABLE<0.10 < WARNING<0.20 <= CRITICAL.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.common import PaginatedResponse
from api.schemas.governance import DriftReportResponse, DriftRunRequest
from api.services import drift_service as svc
from core.db.models.iam import User

router = APIRouter(prefix="/drift", tags=["Drift Monitoring"])
_read = Depends(require_roles("auditeur", "administrateur", "expert_metier"))
_run = Depends(require_roles("administrateur", "expert_metier"))


@router.get("/status")
def get_all_status(db: Session = Depends(get_db), _: User = _read):
    return svc.get_all_status(db)


@router.get("/status/{branch}")
def get_branch_status(branch: str, db: Session = Depends(get_db), _: User = _read):
    return svc.get_branch_status(db, branch)


@router.get("/history/{branch}", response_model=PaginatedResponse[dict])
def get_history(
    branch: str, days: int = Query(90, ge=1, le=365),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _read,
):
    total, items = svc.get_drift_history(db, branch, days, (page-1)*page_size, page_size)
    results = [{"id": str(r.id), "status": r.status, "psi_max": r.psi_max, "computed_at": str(r.computed_at)} for r in items]
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=results)


@router.get("/reports/{report_id}", response_model=DriftReportResponse)
def get_report(report_id: UUID, db: Session = Depends(get_db), _: User = _read):
    return svc.get_report_detail(db, report_id)


@router.post("/run/{branch}")
def run_drift(branch: str, data: DriftRunRequest, db: Session = Depends(get_db), current_user: User = _run):
    return svc.run_drift(db, branch, data.reference_window_days, data.current_window_days, current_user.id)
