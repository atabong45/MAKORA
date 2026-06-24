"""
MODULE : api/routers/health.py
DESCRIPTION : Healthcheck public MAKORA — GET /health (sans auth).
Conforme API_CONTRACTS Phase 0.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.config import get_settings
from api.deps.db import get_db

router = APIRouter(tags=["Health"])
settings = get_settings()


@router.get("/health", include_in_schema=True)
def health(db: Session = Depends(get_db)):
    db_ok = True
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "version": settings.VERSION,
        "project": settings.PROJECT_NAME,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "components": {
            "database": "ok" if db_ok else "error",
        },
    }
