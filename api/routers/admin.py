"""
MODULE : api/routers/admin.py
DESCRIPTION : Router FastAPI — Administration système (6 endpoints).
Accès réservé aux administrateurs.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.common import MessageResponse, PaginatedResponse
from api.services import admin_service as svc
from core.db.models.iam import User

router = APIRouter(prefix="/admin", tags=["Administration"])
_admin = Depends(require_roles("administrateur"))


@router.get("/status")
def get_system_status(db: Session = Depends(get_db), _: User = _admin):
    return svc.get_system_status(db)


@router.get("/branches")
def list_branches(db: Session = Depends(get_db), _: User = _admin):
    branches = svc.list_branches(db)
    return [{"code": b.code, "is_active": b.is_active, "contamination_threshold": b.contamination_threshold,
             "anomaly_score_alert": b.anomaly_score_alert} for b in branches]


@router.get("/branches/{branch_code}")
def get_branch(branch_code: str, db: Session = Depends(get_db), _: User = _admin):
    b = svc.get_branch(db, branch_code)
    return {"code": b.code, "is_active": b.is_active, "contamination_threshold": b.contamination_threshold,
            "anomaly_score_alert": b.anomaly_score_alert, "anomaly_score_block": b.anomaly_score_block}


@router.patch("/branches/{branch_code}/activate", response_model=MessageResponse)
def activate_branch(branch_code: str, db: Session = Depends(get_db), _: User = _admin):
    result = svc.toggle_branch(db, branch_code, True)
    return MessageResponse(message=result["message"])


@router.patch("/branches/{branch_code}/deactivate", response_model=MessageResponse)
def deactivate_branch(branch_code: str, db: Session = Depends(get_db), _: User = _admin):
    result = svc.toggle_branch(db, branch_code, False)
    return MessageResponse(message=result["message"])


@router.get("/activity-log", response_model=PaginatedResponse[dict])
def get_activity_log(
    user_id: UUID | None = Query(None), action: str | None = Query(None),
    resource_type: str | None = Query(None), period_days: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _admin,
):
    total, items = svc.get_activity_log(db, user_id, action, resource_type, period_days, (page-1)*page_size, page_size)
    results = [{"id": str(i.id), "user_id": str(i.user_id) if i.user_id else None,
                "action": i.action, "resource_type": i.resource_type,
                "resource_id": i.resource_id, "result": i.result, "created_at": str(i.created_at)} for i in items]
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=results)
