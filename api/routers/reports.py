"""
MODULE : api/routers/reports.py
DESCRIPTION : Router FastAPI — Exports et statistiques (5 endpoints). Implémente BF-10.
"""
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from api.deps.auth import get_current_active_user
from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.common import PaginatedResponse
from api.schemas.reports import ExportReportResponse, ExportRequest
from api.services import analytics_service, report_service as svc
from core.db.models.iam import User

router = APIRouter(prefix="/reports", tags=["Rapports & Exports"])
_auditor = Depends(require_roles("auditeur", "administrateur"))
_all = Depends(get_current_active_user)


@router.post("/export", response_model=ExportReportResponse, status_code=202)
def request_export(data: ExportRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = _auditor):
    report = svc.create_export_request(db, data, current_user.id)
    background_tasks.add_task(svc.generate_export, db, report.id)
    return report


@router.get("/exports/{export_id}/download")
def download(export_id: UUID, db: Session = Depends(get_db), current_user: User = _auditor):
    content, mime, filename = svc.download_export(db, export_id, current_user.id)
    return Response(content=content, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/exports/{export_id}", response_model=ExportReportResponse)
def get_export(export_id: UUID, db: Session = Depends(get_db), current_user: User = _auditor):
    return svc.get_export(db, export_id, current_user.id)


@router.get("/exports", response_model=PaginatedResponse[ExportReportResponse])
def list_exports(page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), current_user: User = _auditor):
    total, items = svc.list_my_exports(db, current_user.id, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)


@router.get("/stats/global", response_model=None)  # response_model=None pour laisser passer le dict riche
def global_stats(period_days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db), _: User = _all):
    return svc.get_global_stats(db, period_days)


@router.get("/stats/{branch}")
def branch_stats(branch: str, period_days: int = Query(30, ge=1, le=365), db: Session = Depends(get_db), _: User = _all):
    return {"branch": branch, "period_days": period_days, "top_features": analytics_service.get_top_shap_features(db, branch, period_days)}
