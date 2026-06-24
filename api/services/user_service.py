"""
MODULE : api/services/user_service.py
DESCRIPTION : Service CRUD utilisateurs — soft-delete, gestion rôles.
"""
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from api.schemas.iam import UserCreate, UserUpdate
from api.services.auth_service import hash_password
from core.db.models.iam import User, Role, UserRole, UserSession, Permission, RolePermission


def get_users(db: Session, is_active: bool | None, role: str | None, search: str | None, offset: int, limit: int):
    q = db.query(User)
    if is_active is not None:
        q = q.filter(User.is_active == is_active)
    if search:
        q = q.filter(
            (User.username.ilike(f"%{search}%")) |
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%"))
        )
    total = q.count()
    users = q.offset(offset).limit(limit).all()
    return total, users


def get_user(db: Session, user_id: UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail=f"Utilisateur {user_id} introuvable")
    return user


def create_user(db: Session, data: UserCreate, created_by: UUID) -> User:
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=409, detail="Username déjà pris")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=409, detail="Email déjà utilisé")
    user = User(
        username=data.username,
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    role = db.query(Role).filter(Role.name == data.role).first()
    if not role:
        raise HTTPException(status_code=400, detail=f"Rôle inconnu : {data.role}")
    user_role = UserRole(user_id=user.id, role_id=role.id, granted_by=created_by)
    db.add(user_role)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: UUID, data: UserUpdate) -> User:
    user = get_user(db, user_id)
    if data.email and data.email != user.email:
        if db.query(User).filter(User.email == data.email).first():
            raise HTTPException(status_code=409, detail="Email déjà utilisé")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, user_id: UUID) -> None:
    user = get_user(db, user_id)
    user.is_active = False
    db.query(UserSession).filter(UserSession.user_id == user_id).update({"is_revoked": True})
    db.commit()


def reactivate_user(db: Session, user_id: UUID) -> User:
    user = get_user(db, user_id)
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def reset_user_password(db: Session, user_id: UUID, new_password: str) -> None:
    user = get_user(db, user_id)
    user.password_hash = hash_password(new_password)
    db.query(UserSession).filter(UserSession.user_id == user_id).update({"is_revoked": True})
    db.commit()


def assign_role(db: Session, user_id: UUID, role_id: UUID, granted_by: UUID) -> None:
    get_user(db, user_id)
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Rôle introuvable")
    existing = db.query(UserRole).filter(UserRole.user_id == user_id, UserRole.role_id == role_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Rôle déjà assigné")
    db.add(UserRole(user_id=user_id, role_id=role_id, granted_by=granted_by))
    db.commit()


def remove_role(db: Session, user_id: UUID, role_id: UUID) -> None:
    user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id, UserRole.role_id == role_id
    ).first()
    if not user_role:
        raise HTTPException(status_code=404, detail="Association rôle/utilisateur introuvable")
    admin_role = db.query(Role).filter(Role.name == "administrateur").first()
    if admin_role and role_id == admin_role.id:
        count = db.query(UserRole).filter(UserRole.role_id == admin_role.id).count()
        if count <= 1:
            raise HTTPException(status_code=400, detail="Impossible de retirer le dernier administrateur système")
    db.delete(user_role)
    db.commit()
