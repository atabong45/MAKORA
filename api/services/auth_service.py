"""
MODULE : api/services/auth_service.py
DESCRIPTION : Service d'authentification MAKORA — JWT access (15min) +
refresh token SHA-256 persisté (7 jours).

RÉFÉRENCES ACADÉMIQUES :
- Pas de référence algorithmique — couche infrastructure standard.

DÉCISIONS DE CONCEPTION :
- [DT-AUTH-001 CORRIGÉ] bcrypt direct (>=4.0) à la place de passlib 1.7.4.
  passlib.context.CryptContext provoque un INTERNAL_SERVER_ERROR avec
  bcrypt>=4.0 car l'API interne de bcrypt a changé (version string format).
  Solution : appels directs bcrypt.checkpw() / bcrypt.hashpw().
- Access token JWT stateless (15 min) — révocation impossible intentionnelle
  pour réduire la charge DB.
- Refresh token : token aléatoire 64 octets stocké en SHA-256 dans la DB,
  jamais en clair → compromission DB n'expose pas les tokens.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt as _bcrypt
from fastapi import HTTPException, status
from jose import jwt
from sqlalchemy.orm import Session

from api.config import get_settings
from core.db.models.iam import User, UserSession

settings = get_settings()


# ── Hashing ─────────────────────────────────────────────────────────────────

def verify_password(plain: str, hashed: str) -> bool:
    """Vérifie un mot de passe en clair contre son hash bcrypt.

    Compatible bcrypt >= 4.0 — utilise l'API native au lieu de passlib.
    """
    try:
        return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def hash_password(plain: str) -> str:
    """Hash un mot de passe avec bcrypt (rounds=12).

    Compatible bcrypt >= 4.0.
    """
    salt = _bcrypt.gensalt(rounds=12)
    return _bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


# ── JWT ─────────────────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    expire = datetime.now(tz=timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "access"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def create_refresh_token() -> tuple[str, str]:
    """Retourne (raw_token, sha256_hash)."""
    raw = secrets.token_urlsafe(64)
    hashed = hashlib.sha256(raw.encode()).hexdigest()
    return raw, hashed


def create_reset_token(user_id: str) -> str:
    expire = datetime.now(tz=timezone.utc) + timedelta(
        minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "type": "reset"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


# ── Authentification ────────────────────────────────────────────────────────

def authenticate_user(db: Session, username: str, password: str) -> User:
    user = db.query(User).filter(
        (User.username == username) | (User.email == username)
    ).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants invalides",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte désactivé",
        )
    return user


def login(
    db: Session,
    username: str,
    password: str,
    ip: str | None,
    user_agent: str | None,
) -> dict:
    user = authenticate_user(db, username, password)
    access_token = create_access_token(str(user.id))
    raw_refresh, hashed_refresh = create_refresh_token()
    session = UserSession(
        user_id=user.id,
        refresh_token_hash=hashed_refresh,
        ip_address=ip,
        user_agent=user_agent,
        expires_at=datetime.now(tz=timezone.utc)
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    user.last_login = datetime.now(tz=timezone.utc)
    db.commit()
    return {
        "access_token": access_token,
        "refresh_token": raw_refresh,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def logout(db: Session, refresh_token: str) -> None:
    hashed = hashlib.sha256(refresh_token.encode()).hexdigest()
    session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == hashed,
        UserSession.is_revoked == False,  # noqa: E712
    ).first()
    if session:
        session.is_revoked = True
        db.commit()


def refresh_access_token(db: Session, refresh_token: str) -> dict:
    hashed = hashlib.sha256(refresh_token.encode()).hexdigest()
    session = db.query(UserSession).filter(
        UserSession.refresh_token_hash == hashed,
        UserSession.is_revoked == False,  # noqa: E712
    ).first()
    if not session or session.expires_at.replace(tzinfo=timezone.utc) < datetime.now(
        tz=timezone.utc
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token invalide ou expiré",
        )
    access_token = create_access_token(str(session.user_id))
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


def get_user_sessions(db: Session, user_id: UUID) -> list[UserSession]:
    return (
        db.query(UserSession)
        .filter(UserSession.user_id == user_id, UserSession.is_revoked == False)  # noqa: E712
        .all()
    )


def revoke_session(db: Session, session_id: UUID, user_id: UUID) -> None:
    session = db.query(UserSession).filter(
        UserSession.id == session_id, UserSession.user_id == user_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session introuvable")
    session.is_revoked = True
    db.commit()


def change_password(
    db: Session, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise HTTPException(
            status_code=400, detail="Mot de passe actuel incorrect"
        )
    user.password_hash = hash_password(new_password)
    db.query(UserSession).filter(UserSession.user_id == user.id).update(
        {"is_revoked": True}
    )
    db.commit()


def reset_password_with_token(
    db: Session, token: str, new_password: str
) -> None:
    from jose import JWTError

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        if payload.get("type") != "reset":
            raise HTTPException(status_code=400, detail="Token invalide")
        user_id = payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=400, detail="Token expiré ou invalide")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    user.password_hash = hash_password(new_password)
    db.query(UserSession).filter(UserSession.user_id == user.id).update(
        {"is_revoked": True}
    )
    db.commit()