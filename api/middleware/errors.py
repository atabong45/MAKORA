"""
MODULE : api/middleware/errors.py
DESCRIPTION : Handler global d'erreurs — format unifié {error, message, timestamp}.

CORRECTION DT-LOG-001 :
- generic_exception_handler loggue maintenant la stacktrace complète via
  logging.exception(). Avant cette correction, toute exception non-HTTP
  était avalée silencieusement — impossible de diagnostiquer les 500.
"""
import logging
import uuid
from datetime import datetime, timezone

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("makora.errors")


def _error_response(error: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "message": message,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            "request_id": str(uuid.uuid4())[:8],
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    error_map = {
        400: "BAD_REQUEST", 401: "UNAUTHORIZED", 403: "FORBIDDEN",
        404: "NOT_FOUND", 409: "CONFLICT", 413: "PAYLOAD_TOO_LARGE",
        422: "VALIDATION_ERROR", 429: "RATE_LIMIT_EXCEEDED", 503: "SERVICE_UNAVAILABLE",
    }
    error_code = error_map.get(exc.status_code, "HTTP_ERROR")
    return _error_response(error_code, str(exc.detail), exc.status_code)


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = exc.errors()
    message = "; ".join(f"{'.'.join(str(l) for l in e['loc'])}: {e['msg']}" for e in errors[:3])
    return _error_response("VALIDATION_ERROR", message, status.HTTP_422_UNPROCESSABLE_ENTITY)


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # DT-LOG-001 : log la stacktrace complète pour diagnostiquer les 500
    logger.exception(
        "Erreur inattendue sur %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return _error_response(
        "INTERNAL_SERVER_ERROR",
        "Une erreur inattendue s'est produite",
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )