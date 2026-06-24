"""
MODULE : api/routers/modules.py
DESCRIPTION : Router FastAPI — Modules MAKORA (10 endpoints).
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.common import MessageResponse
from api.schemas.governance import ModuleConfigSnapshotResponse, ModuleConfigUpdate, RcaRuleResponse
from api.services import module_service as svc
from core.db.models.iam import User

router = APIRouter(prefix="/modules", tags=["Modules"])
_read = Depends(require_roles("auditeur", "administrateur", "expert_metier"))
_admin = Depends(require_roles("administrateur"))
_expert = Depends(require_roles("administrateur", "expert_metier"))


@router.get("/", response_model=list[dict])
def list_modules(db: Session = Depends(get_db), _: User = _read):
    return svc.list_modules(db)


@router.get("/rca-rules/stats")
def rca_stats(_: User = _read):
    return {"message": "Stats RCA — à implémenter avec données agrégées"}


@router.get("/{branch}", response_model=dict)
def get_module(branch: str, db: Session = Depends(get_db), _: User = _expert):
    return svc.get_module_detail(db, branch)


@router.post("/{branch}/reload", response_model=MessageResponse)
def reload_module(branch: str, _: User = _admin):
    result = svc.reload_module(branch)
    return MessageResponse(message=result["message"])


@router.get("/{branch}/config", response_model=dict)
def get_config(branch: str, db: Session = Depends(get_db), _: User = _expert):
    return svc.get_active_config(db, branch)


@router.patch("/{branch}/config", response_model=MessageResponse)
def update_config(branch: str, data: ModuleConfigUpdate, db: Session = Depends(get_db), current_user: User = _admin):
    result = svc.update_config(db, branch, data, current_user.id)
    return MessageResponse(message=result["message"])


@router.get("/{branch}/configs", response_model=list[ModuleConfigSnapshotResponse])
def list_configs(branch: str, db: Session = Depends(get_db), _: User = _expert):
    return svc.list_config_snapshots(db, branch)


@router.get("/{branch}/configs/{config_id}", response_model=ModuleConfigSnapshotResponse)
def get_config_snapshot(branch: str, config_id: UUID, db: Session = Depends(get_db), _: User = _expert):
    from core.db.models.monitoring import ModuleConfig
    config = db.query(ModuleConfig).filter(ModuleConfig.id == config_id).first()
    if not config:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Snapshot introuvable")
    return config


@router.post("/{branch}/configs/{config_id}/activate", response_model=MessageResponse)
def activate_snapshot(branch: str, config_id: UUID, db: Session = Depends(get_db), _: User = _admin):
    result = svc.activate_config_snapshot(db, branch, config_id)
    return MessageResponse(message=result["message"])


@router.get("/{branch}/rca-rules", response_model=list[RcaRuleResponse])
def get_rca_rules(branch: str, db: Session = Depends(get_db), _: User = _expert):
    return svc.get_rca_rules(db, branch)
