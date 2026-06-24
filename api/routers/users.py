"""
MODULE : api/routers/users.py
DESCRIPTION : Router FastAPI — Gestion utilisateurs (9 endpoints, admin uniquement).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps.auth import get_current_active_user
from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.common import MessageResponse, PaginatedResponse
from api.schemas.iam import RoleAssign, UserCreate, UserResponse, UserUpdate
from api.services import user_service
from core.db.models.iam import User

router = APIRouter(prefix="/users", tags=["Utilisateurs"])
_admin = Depends(require_roles("administrateur"))


@router.get("/", response_model=PaginatedResponse[UserResponse])
def list_users(
    is_active: bool | None = Query(None),
    role: str | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _admin,
):
    total, users = user_service.get_users(db, is_active, role, search, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=users)


@router.post("/", response_model=UserResponse, status_code=201)
def create_user(data: UserCreate, db: Session = Depends(get_db), current_user: User = _admin):
    return user_service.create_user(db, data, current_user.id)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: UUID, db: Session = Depends(get_db), _: User = _admin):
    return user_service.get_user(db, user_id)


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: UUID, data: UserUpdate, db: Session = Depends(get_db), _: User = _admin):
    return user_service.update_user(db, user_id, data)


@router.delete("/{user_id}", response_model=MessageResponse)
def deactivate_user(user_id: UUID, db: Session = Depends(get_db), _: User = _admin):
    user_service.deactivate_user(db, user_id)
    return MessageResponse(message="Compte désactivé")


@router.post("/{user_id}/reactivate", response_model=UserResponse)
def reactivate_user(user_id: UUID, db: Session = Depends(get_db), _: User = _admin):
    return user_service.reactivate_user(db, user_id)


@router.patch("/{user_id}/password", response_model=MessageResponse)
def reset_user_password(user_id: UUID, data: dict, db: Session = Depends(get_db), _: User = _admin):
    new_password = data.get("new_password", "")
    user_service.reset_user_password(db, user_id, new_password)
    return MessageResponse(message="Mot de passe réinitialisé")


@router.post("/{user_id}/roles", response_model=MessageResponse, status_code=201)
def assign_role(user_id: UUID, data: RoleAssign, db: Session = Depends(get_db), current_user: User = _admin):
    user_service.assign_role(db, user_id, data.role_id, current_user.id)
    return MessageResponse(message="Rôle assigné")


@router.delete("/{user_id}/roles/{role_id}", response_model=MessageResponse)
def remove_role(user_id: UUID, role_id: UUID, db: Session = Depends(get_db), _: User = _admin):
    user_service.remove_role(db, user_id, role_id)
    return MessageResponse(message="Rôle retiré")
