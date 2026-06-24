"""
MODULE : api/routers/retraining.py
DESCRIPTION : Router FastAPI — Réentraînement modèles (6 endpoints).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.common import PaginatedResponse
from api.schemas.governance import RetrainingCreate, RetrainingResponse
from api.services import retraining_service as svc
from core.db.models.iam import User

router = APIRouter(prefix="/retraining", tags=["Réentraînement"])
_admin = Depends(require_roles("administrateur"))
_expert = Depends(require_roles("administrateur", "expert_metier"))


@router.post("/", response_model=RetrainingResponse, status_code=201)
def create(data: RetrainingCreate, db: Session = Depends(get_db), current_user: User = _expert):
    return svc.create_request(db, data, current_user.id)


@router.get("/", response_model=PaginatedResponse[RetrainingResponse])
def list_requests(
    status: str | None = Query(None), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _expert,
):
    total, items = svc.list_requests(db, None, status, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)


@router.get("/{request_id}", response_model=RetrainingResponse)
def get_request(request_id: UUID, db: Session = Depends(get_db), _: User = _expert):
    return svc.get_request(db, request_id)


@router.patch("/{request_id}/approve", response_model=RetrainingResponse)
def approve(request_id: UUID, db: Session = Depends(get_db), current_user: User = _admin):
    return svc.approve_request(db, request_id, current_user.id)


@router.patch("/{request_id}/reject", response_model=RetrainingResponse)
def reject(request_id: UUID, reason: str = Query(...), db: Session = Depends(get_db), current_user: User = _admin):
    return svc.reject_request(db, request_id, reason, current_user.id)


@router.patch("/{request_id}/complete", response_model=RetrainingResponse)
def complete(request_id: UUID, new_model_version_id: UUID = Query(...), db: Session = Depends(get_db), _: User = _admin):
    return svc.complete_request(db, request_id, new_model_version_id)
