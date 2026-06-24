"""
MODULE : api/schemas/governance.py
DESCRIPTION : Schémas Pydantic v2 pour la gouvernance ML.
Couvre : model_versions, production_deployments, drift, retraining, modules.
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field


class ModelVersionResponse(BaseModel):
    id: UUID
    branch_id: UUID
    algorithm: str
    version_tag: str
    contamination: float
    f1_score: float | None = None
    auc_roc: float | None = None
    precision_ppv: float | None = None
    recall_tpr: float | None = None
    fpr: float | None = None
    mcc: float | None = None
    train_size: int | None = None
    trained_at: datetime
    created_at: datetime
    model_config = {"from_attributes": True}


class ModelRegisterRequest(BaseModel):
    branch_code: str
    algorithm: str = "isolation_forest"
    version_tag: str
    file_path: str
    contamination: float
    feature_names: list[str]
    f1_score: float | None = None
    auc_roc: float | None = None
    mcc: float | None = None
    fpr: float | None = None
    train_size: int | None = None


class DeployRequest(BaseModel):
    model_version_id: UUID
    deployment_notes: str | None = None


class DeploymentResponse(BaseModel):
    id: UUID
    branch_id: UUID
    model_version_id: UUID
    deployed_by: UUID
    deployed_at: datetime
    replaced_at: datetime | None = None
    deployment_notes: str | None = None
    model_config = {"from_attributes": True}


class DriftFeatureMetricResponse(BaseModel):
    feature_name: str
    psi_value: float
    status: str
    n_reference: int
    n_current: int
    model_config = {"from_attributes": True}


class DriftReportResponse(BaseModel):
    id: UUID
    branch_id: UUID
    status: str
    psi_max: float
    n_features_analyzed: int
    n_features_warning: int
    n_features_critical: int
    reference_window_days: int
    current_window_days: int
    computed_at: datetime
    features: list[DriftFeatureMetricResponse] = []
    model_config = {"from_attributes": True}


class DriftRunRequest(BaseModel):
    reference_window_days: int = 90
    current_window_days: int = 30


class RetrainingCreate(BaseModel):
    branch_code: str
    reason: str
    drift_report_id: UUID | None = None


class RetrainingResponse(BaseModel):
    id: UUID
    branch_id: UUID
    reason: str
    status: str
    requested_by: UUID
    approved_by: UUID | None = None
    new_model_version_id: UUID | None = None
    created_at: datetime
    approved_at: datetime | None = None
    completed_at: datetime | None = None
    model_config = {"from_attributes": True}


class ModuleStatusResponse(BaseModel):
    branch: str
    version: str | None = None
    status: str
    model_version: str | None = None
    graph_enabled: bool
    last_reload: datetime | None = None


class ModuleConfigUpdate(BaseModel):
    contamination: float | None = Field(default=None, gt=0.0, lt=0.5)
    anomaly_score_alert: float | None = Field(default=None, gt=0.0, lt=1.0)
    anomaly_score_block: float | None = Field(default=None, gt=0.0, le=1.0)


class ModuleConfigSnapshotResponse(BaseModel):
    id: UUID
    branch_id: UUID
    version_tag: str
    yaml_hash: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class RcaRuleResponse(BaseModel):
    id: UUID
    rule_id: str
    category: str
    subcategory: str
    confidence_base: float
    priority: int
    logic: str
    model_config = {"from_attributes": True}
