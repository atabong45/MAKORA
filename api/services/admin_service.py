"""
MODULE : api/services/admin_service.py
DESCRIPTION : Service administration système — branches, healthcheck, activity-log.
"""
import subprocess
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.config import get_settings

settings = get_settings()


def get_system_status(db: Session) -> dict:
    components = {}
    # DB check
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        components["database"] = {"status": "OK"}
    except Exception as e:
        components["database"] = {"status": "ERROR", "detail": str(e)}
    # Ollama check
    try:
        import urllib.request
        with urllib.request.urlopen(f"{settings.OLLAMA_URL}/api/tags", timeout=3) as r:
            components["ollama"] = {"status": "OK", "http": r.status}
    except Exception as e:
        components["ollama"] = {"status": "UNAVAILABLE", "detail": str(e)}
    # Model files
    from pathlib import Path
    data_path = Path(settings.MAKORA_DATA_PATH)
    model_files = list(data_path.glob("**/*.joblib")) if data_path.exists() else []
    components["model_files"] = {"status": "OK", "count": len(model_files)}
    # Documents dir
    doc_path = Path(settings.MAKORA_DOCUMENTS_PATH)
    components["documents_dir"] = {"status": "OK" if doc_path.exists() else "MISSING"}

    all_ok = all(c.get("status") == "OK" for c in components.values())
    return {
        "overall": "HEALTHY" if all_ok else "DEGRADED",
        "components": components,
        "checked_at": datetime.now(tz=timezone.utc).isoformat(),
    }


def list_branches(db: Session) -> list:
    from core.db.models.referentiels import Branch
    return db.query(Branch).order_by(Branch.code).all()


def get_branch(db: Session, branch_code: str):
    from core.db.models.referentiels import Branch
    b = db.query(Branch).filter(Branch.code == branch_code).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche '{branch_code}' introuvable")
    return b


def toggle_branch(db: Session, branch_code: str, is_active: bool) -> dict:
    b = get_branch(db, branch_code)
    b.is_active = is_active
    db.commit()
    return {"message": f"Branche '{branch_code}' {'activée' if is_active else 'désactivée'}", "is_active": is_active}


def get_activity_log(db: Session, user_id: UUID | None, action: str | None, resource_type: str | None, period_days: int, offset: int, limit: int):
    from core.db.models.monitoring import AuditLog
    since = datetime.now(tz=timezone.utc) - timedelta(days=period_days)
    q = db.query(AuditLog).filter(AuditLog.created_at >= since)
    if user_id:
        q = q.filter(AuditLog.user_id == str(user_id))
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if resource_type:
        q = q.filter(AuditLog.resource_type == resource_type)
    total = q.count()
    items = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return total, items
