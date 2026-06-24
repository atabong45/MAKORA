"""
MODULE : api/deps/rbac.py
DESCRIPTION : Contrôle d'accès basé sur les rôles (RBAC).
Fournit require_roles() comme dépendance FastAPI injectable.
"""
from typing import Callable

from fastapi import Depends, HTTPException, status

from api.deps.auth import get_current_active_user
from core.db.models.iam import User


def require_roles(*roles: str) -> Callable:
    """Retourne une dépendance FastAPI qui vérifie que l'utilisateur possède au moins un des rôles."""
    def dependency(current_user: User = Depends(get_current_active_user)) -> User:
        user_roles = {ur.role.name for ur in current_user.user_roles}
        if not roles or set(roles) & user_roles:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Rôle requis : {', '.join(roles)}",
        )
    return dependency


def require_any_role(*roles: str) -> Callable:
    return require_roles(*roles)


def get_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    return require_roles("administrateur")(current_user)
