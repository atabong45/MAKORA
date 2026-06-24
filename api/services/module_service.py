"""
MODULE : api/services/module_service.py
DESCRIPTION : Service modules — wrapping PluginRegistry, config YAML versionnée.
Respecte ADR-002 : jamais d'import de module métier par nom concret.
"""
import hashlib
import yaml
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from api.schemas.governance import ModuleConfigUpdate


def list_modules(db: Session) -> list[dict]:
    from core.db.models.referentiels import Branch
    from core.plugin_registry import PluginRegistry
    branches = db.query(Branch).all()
    result = []
    for b in branches:
        # loaded = PluginRegistry.is_loaded(b.code) if hasattr(PluginRegistry, "is_loaded") else False
        loaded = PluginRegistry.is_registered(b.code)
        result.append({"branch": b.code, "status": "LOADED" if loaded else "NOT_LOADED",
                        "is_active": b.is_active, "contamination": b.contamination_threshold})
    return result


def get_module_detail(db: Session, branch: str) -> dict:
    from core.db.models.referentiels import Branch
    from core.db.models.monitoring import ModuleConfig
    b = db.query(Branch).filter(Branch.code == branch).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche inconnue : {branch}")
    active_config = db.query(ModuleConfig).filter(ModuleConfig.branch_id == b.id, ModuleConfig.is_active == True).first()
    return {
        "branch": branch, "is_active": b.is_active,
        "contamination_threshold": b.contamination_threshold,
        "anomaly_score_alert": b.anomaly_score_alert, "anomaly_score_block": b.anomaly_score_block,
        "active_config_version": active_config.version_tag if active_config else None,
    }


def reload_module(branch: str) -> dict:
    from core.plugin_registry import PluginRegistry
    try:
        PluginRegistry.reload(branch) if hasattr(PluginRegistry, "reload") else PluginRegistry.discover()
        return {"message": f"Module '{branch}' rechargé", "branch": branch}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur rechargement : {e}")


def get_active_config(db: Session, branch: str) -> dict:
    from core.db.models.referentiels import Branch
    from core.db.models.monitoring import ModuleConfig
    b = db.query(Branch).filter(Branch.code == branch).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche inconnue : {branch}")
    config = db.query(ModuleConfig).filter(ModuleConfig.branch_id == b.id, ModuleConfig.is_active == True).first()
    if config:
        try:
            return yaml.safe_load(config.yaml_content)
        except Exception:
            return {"raw": config.yaml_content}
    module_yaml_path = f"modules/{branch}/{branch}.yaml"
    try:
        with open(module_yaml_path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Config YAML introuvable pour {branch}")


def update_config(db: Session, branch: str, data: ModuleConfigUpdate, updated_by: UUID) -> dict:
    from core.db.models.referentiels import Branch
    from core.db.models.monitoring import ModuleConfig
    b = db.query(Branch).filter(Branch.code == branch).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche inconnue : {branch}")
    if data.anomaly_score_alert and data.anomaly_score_block:
        if data.anomaly_score_alert >= data.anomaly_score_block:
            raise HTTPException(status_code=400, detail="anomaly_score_alert doit être < anomaly_score_block")
    if data.contamination is not None:
        b.contamination_threshold = data.contamination
    if data.anomaly_score_alert is not None:
        b.anomaly_score_alert = data.anomaly_score_alert
    if data.anomaly_score_block is not None:
        b.anomaly_score_block = data.anomaly_score_block
    db.query(ModuleConfig).filter(ModuleConfig.branch_id == b.id).update({"is_active": False})
    config_dict = {"contamination": b.contamination_threshold, "anomaly_score_alert": b.anomaly_score_alert}
    yaml_str = yaml.dump(config_dict)
    snap = ModuleConfig(
        branch_id=b.id, version_tag=f"v{datetime.now(tz=timezone.utc).strftime('%Y%m%d%H%M%S')}",
        yaml_content=yaml_str, yaml_hash=hashlib.sha256(yaml_str.encode()).hexdigest(),
        is_active=True, created_by=updated_by,
    )
    db.add(snap)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail=f"Contrainte DB violée. Vérifier contamination ∈ ]0,0.5[. Détail : {exc.orig}",
        )
    return {"message": "Configuration mise à jour", "branch": branch}

def list_config_snapshots(db: Session, branch: str):
    from core.db.models.referentiels import Branch
    from core.db.models.monitoring import ModuleConfig
    b = db.query(Branch).filter(Branch.code == branch).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche inconnue : {branch}")
    return db.query(ModuleConfig).filter(ModuleConfig.branch_id == b.id).order_by(ModuleConfig.created_at.desc()).all()


def activate_config_snapshot(db: Session, branch: str, config_id: UUID) -> dict:
    from core.db.models.referentiels import Branch
    from core.db.models.monitoring import ModuleConfig
    b = db.query(Branch).filter(Branch.code == branch).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche inconnue : {branch}")
    config = db.query(ModuleConfig).filter(ModuleConfig.id == config_id, ModuleConfig.branch_id == b.id).first()
    if not config:
        raise HTTPException(status_code=404, detail="Snapshot introuvable")
    db.query(ModuleConfig).filter(ModuleConfig.branch_id == b.id).update({"is_active": False})
    config.is_active = True
    db.commit()
    return {"message": f"Snapshot {config.version_tag} activé"}


def get_rca_rules(db: Session, branch: str):
    from core.db.models.referentiels import Branch
    from core.db.models.monitoring import ModuleConfig, RcaRuleSnapshot
    b = db.query(Branch).filter(Branch.code == branch).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche inconnue : {branch}")
    config = db.query(ModuleConfig).filter(ModuleConfig.branch_id == b.id, ModuleConfig.is_active == True).first()
    if not config:
        return []
    return db.query(RcaRuleSnapshot).filter(RcaRuleSnapshot.module_config_id == config.id).order_by(RcaRuleSnapshot.priority).all()
