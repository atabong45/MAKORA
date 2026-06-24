"""
MODULE : api/routers/models.py
DESCRIPTION : Router FastAPI — Catalogue modèles ML (7 endpoints).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.common import PaginatedResponse
from api.schemas.governance import DeployRequest, DeploymentResponse, ModelRegisterRequest, ModelVersionResponse
from api.services import model_service as svc
from core.db.models.iam import User

router = APIRouter(prefix="/models", tags=["Modèles ML"])
_admin = Depends(require_roles("administrateur"))
_read = Depends(require_roles("administrateur", "expert_metier", "auditeur"))


@router.get("/", response_model=PaginatedResponse[ModelVersionResponse])
def list_models(
    branch: str | None = Query(None), page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _read,
):
    total, items = svc.list_models(db, branch, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)


@router.post("/register", response_model=ModelVersionResponse, status_code=201)
def register_model(data: ModelRegisterRequest, db: Session = Depends(get_db), current_user: User = _admin):
    return svc.register_model(db, data, current_user.id)


@router.get("/branch/{branch}/current", response_model=ModelVersionResponse)
def get_current(branch: str, db: Session = Depends(get_db), _: User = _read):
    return svc.get_current_production(db, branch)


@router.get("/branch/{branch}/history", response_model=PaginatedResponse[ModelVersionResponse])
def get_history(
    branch: str, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _read,
):
    total, items = svc.get_model_history(db, branch, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)


@router.post("/deploy", response_model=DeploymentResponse, status_code=201)
def deploy_model(data: DeployRequest, db: Session = Depends(get_db), current_user: User = _admin):
    return svc.deploy_model(db, data, current_user.id)


@router.get("/deployments", response_model=PaginatedResponse[DeploymentResponse])
def list_deployments(
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _read,
):
    total, items = svc.list_deployments(db, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)


@router.get("/{model_id}", response_model=ModelVersionResponse)
def get_model(model_id: UUID, db: Session = Depends(get_db), _: User = _read):
    return svc.get_model(db, model_id)
