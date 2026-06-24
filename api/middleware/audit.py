"""
MODULE : api/middleware/audit.py
DESCRIPTION : Middleware d'audit — log toutes les mutations (POST/PATCH/DELETE)
dans la table audit_logs. Résout DT-AUDIT (core/audit_logger.py stub).

DÉCISION : Le middleware intercepte toutes les requêtes mutantes et délègue
l'écriture à core.audit_logger pour respecter la séparation des couches.
"""
import json
import time
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

MUTATING_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
SKIP_PATHS = {"/api/v1/health", "/api/v1/auth/login", "/api/v1/auth/refresh"}


class AuditLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.method not in MUTATING_METHODS or request.url.path in SKIP_PATHS:
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        try:
            user_id = getattr(request.state, "user_id", None)
            await _write_audit_log(
                user_id=user_id,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                ip=request.client.host if request.client else None,
                duration_ms=duration_ms,
            )
        except Exception:
            pass  # Audit ne doit jamais bloquer la réponse

        return response


async def _write_audit_log(
    user_id: str | None,
    method: str,
    path: str,
    status_code: int,
    ip: str | None,
    duration_ms: int,
) -> None:
    """Délègue l'écriture à core.audit_logger (séparation des couches)."""
    try:
        from core.audit_logger import log_action
        resource_parts = [p for p in path.split("/") if p and p != "api"]
        resource_type = resource_parts[1] if len(resource_parts) > 1 else "unknown"
        resource_id = resource_parts[2] if len(resource_parts) > 2 else None
        log_action(
            user_id=user_id,
            action=f"{method.lower()}:{resource_type}",
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip,
            result="SUCCESS" if status_code < 400 else "FAILURE",
        )
    except Exception:
        pass
