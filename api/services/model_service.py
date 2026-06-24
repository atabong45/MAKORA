"""
MODULE : api/services/model_service.py
DESCRIPTION : Service gouvernance modèles ML — register, deploy, historique.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.schemas.governance import DeployRequest, ModelRegisterRequest


def list_models(db: Session, branch: str | None, offset: int, limit: int):
    from core.db.models.pipeline import ModelVersion
    from core.db.models.referentiels import Branch
    q = db.query(ModelVersion)
    if branch:
        b = db.query(Branch).filter(Branch.code == branch).first()
        if b:
            q = q.filter(ModelVersion.branch_id == b.id)
    total = q.count()
    return total, q.order_by(ModelVersion.trained_at.desc()).offset(offset).limit(limit).all()


def get_model(db: Session, model_id: UUID):
    from core.db.models.pipeline import ModelVersion
    m = db.query(ModelVersion).filter(ModelVersion.id == model_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Modèle introuvable")
    return m


def register_model(db: Session, data: ModelRegisterRequest, created_by: UUID):
    from core.db.models.pipeline import ModelVersion
    from core.db.models.referentiels import Branch
    branch = db.query(Branch).filter(Branch.code == data.branch_code).first()
    if not branch:
        raise HTTPException(status_code=400, detail=f"Branche inconnue : {data.branch_code}")
    model = ModelVersion(
        branch_id=branch.id, algorithm=data.algorithm, version_tag=data.version_tag,
        file_path=data.file_path, contamination=data.contamination,
        feature_names=data.feature_names, f1_score=data.f1_score,
        auc_roc=data.auc_roc, mcc=data.mcc, fpr=data.fpr,
        train_size=data.train_size, trained_at=datetime.now(tz=timezone.utc),
        created_by=created_by,
    )
    db.add(model)
    db.commit()
    db.refresh(model)
    return model


def get_current_production(db: Session, branch: str):
    from core.db.models.pipeline import ModelVersion, ProductionDeployment
    from core.db.models.referentiels import Branch
    b = db.query(Branch).filter(Branch.code == branch).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche inconnue : {branch}")
    dep = db.query(ProductionDeployment).filter(
        ProductionDeployment.branch_id == b.id, ProductionDeployment.replaced_at == None
    ).first()
    if not dep:
        raise HTTPException(status_code=404, detail=f"Aucun modèle en production pour {branch}")
    return db.query(ModelVersion).filter(ModelVersion.id == dep.model_version_id).first()


def deploy_model(db: Session, data: DeployRequest, deployed_by: UUID):
    from core.db.models.pipeline import ModelVersion, ProductionDeployment
    model = get_model(db, data.model_version_id)
    now = datetime.now(tz=timezone.utc)
    db.query(ProductionDeployment).filter(
        ProductionDeployment.branch_id == model.branch_id,
        ProductionDeployment.replaced_at == None,
    ).update({"replaced_at": now})
    dep = ProductionDeployment(
        branch_id=model.branch_id, model_version_id=model.id,
        deployed_by=deployed_by, deployed_at=now, deployment_notes=data.deployment_notes,
    )
    db.add(dep)
    db.commit()
    db.refresh(dep)
    from core.audit_logger import log_model_deploy
    log_model_deploy(str(deployed_by), str(model.branch_id), str(model.id))
    return dep


def list_deployments(db: Session, offset: int, limit: int):
    from core.db.models.pipeline import ProductionDeployment
    q = db.query(ProductionDeployment).order_by(ProductionDeployment.deployed_at.desc())
    total = q.count()
    return total, q.offset(offset).limit(limit).all()


def get_model_history(db: Session, branch: str, offset: int, limit: int):
    from core.db.models.pipeline import ModelVersion
    from core.db.models.referentiels import Branch
    b = db.query(Branch).filter(Branch.code == branch).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche inconnue : {branch}")
    q = db.query(ModelVersion).filter(ModelVersion.branch_id == b.id).order_by(ModelVersion.trained_at.desc())
    total = q.count()
    return total, q.offset(offset).limit(limit).all()
