"""
MODULE : api/routers/roles.py
DESCRIPTION : Router FastAPI — Rôles et permissions (3 endpoints, lecture seule).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.iam import PermissionResponse, RoleBase, RoleDetail
from core.db.models.iam import Permission, Role, User

router = APIRouter(prefix="/roles", tags=["Rôles & Permissions"])
_admin = Depends(require_roles("administrateur"))


@router.get("/", response_model=list[RoleBase])
def list_roles(db: Session = Depends(get_db), _: User = _admin):
    return db.query(Role).all()


@router.get("/permissions", response_model=list[PermissionResponse])
def list_permissions(
    resource: str | None = Query(None),
    action: str | None = Query(None),
    db: Session = Depends(get_db), _: User = _admin,
):
    q = db.query(Permission)
    if resource:
        q = q.filter(Permission.resource == resource)
    if action:
        q = q.filter(Permission.action == action)
    return q.all()


@router.get("/{role_id}", response_model=RoleDetail)
def get_role(role_id: UUID, db: Session = Depends(get_db), _: User = _admin):
    from fastapi import HTTPException
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Rôle introuvable")
    return role
