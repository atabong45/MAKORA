"""
MODULE : api/routers/auth.py
DESCRIPTION : Router FastAPI — Authentification (10 endpoints).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from api.deps.auth import get_current_active_user
from api.deps.db import get_db
from api.middleware.rate_limit import limiter
from api.schemas.common import MessageResponse
from api.schemas.iam import (
    AccessTokenResponse, ChangePasswordRequest, ForgotPasswordRequest,
    LoginRequest, RefreshRequest, ResetPasswordRequest, SessionInfo,
    TokenResponse, UserMe, UserUpdate,
)
from api.services import auth_service
from core.db.models.iam import User, UserSession

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return auth_service.login(db, data.username, data.password, ip, ua)


@router.post("/logout", response_model=MessageResponse)
def logout(data: RefreshRequest, db: Session = Depends(get_db), _: User = Depends(get_current_active_user)):
    auth_service.logout(db, data.refresh_token)
    return MessageResponse(message="Déconnecté avec succès")


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    return auth_service.refresh_access_token(db, data.refresh_token)


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if user and user.is_active:
        token = auth_service.create_reset_token(str(user.id))
        return MessageResponse(message=f"Token de réinitialisation (prototype): {token}")
    return MessageResponse(message="Si ce compte existe, un email a été envoyé")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    auth_service.reset_password_with_token(db, data.token, data.new_password)
    return MessageResponse(message="Mot de passe réinitialisé")


@router.post("/change-password", response_model=MessageResponse)
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    auth_service.change_password(db, current_user, data.current_password, data.new_password)
    return MessageResponse(message="Mot de passe modifié")


@router.get("/me", response_model=UserMe)
def get_me(current_user: User = Depends(get_current_active_user)):
    roles = [ur.role.name for ur in current_user.user_roles]
    return UserMe(
        id=current_user.id, username=current_user.username,
        email=current_user.email, full_name=current_user.full_name,
        is_active=current_user.is_active, last_login=current_user.last_login,
        created_at=current_user.created_at, roles=roles,
    )


@router.patch("/me", response_model=UserMe)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    from api.services.user_service import update_user
    user = update_user(db, current_user.id, data)
    roles = [ur.role.name for ur in user.user_roles]
    return UserMe(**user.__dict__, roles=roles)


@router.get("/sessions", response_model=list[SessionInfo])
def list_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    return db.query(UserSession).filter(
        UserSession.user_id == current_user.id,
        UserSession.is_revoked == False,
    ).all()


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
def revoke_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    auth_service.revoke_session(db, session_id, current_user.id)
    return MessageResponse(message="Session révoquée")
