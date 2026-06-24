"""
MODULE : core/db/models/pipeline.py
DESCRIPTION : Modèles SQLAlchemy — Domaine Pipeline ML (5 tables).
  model_versions, production_deployments, analysis_runs,
  analyses, shap_contributions

DÉCISIONS DE CONCEPTION :
- production_deployments remplace le booléen is_production sur model_versions.
  Index partiel UNIQUE (branch_id WHERE replaced_at IS NULL) garantit
  l'unicité du modèle actif par branche sans code applicatif.
- analysis_runs représente une session de détection complète (batch ou single).
  Nécessaire pour lier fraud_communities à leur contexte d'analyse.
- analyses.decision_status = décision humaine HITL.
  Distinct de claims.statut (état administratif du dossier).
- analyses.ocr_extraction_id : FK nullable — null si flux structuré.
- analyses.fraud_community_id : FK nullable — null si graphe désactivé
  ou aucune communauté suspecte détectée pour ce dossier.
- shap_contributions séparée pour requêtes analytiques par feature
  (ex : "quelle feature déclenche le plus d'anomalies ce mois-ci ?").
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db.base import Base
from core.db.mixins import UUIDMixin, CreatedAtMixin, TimestampMixin

_DECISION_STATUTS = "('PENDING', 'CONFIRMED', 'REJECTED', 'ESCALATED')"
_RUN_TYPES = "('single', 'batch', 'reanalysis')"
_DIRECTIONS = "('positive', 'negative')"


class ModelVersion(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "model_versions"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    algorithm: Mapped[str] = mapped_column(String(50), nullable=False)
    version_tag: Mapped[str] = mapped_column(String(50), nullable=False)
    # Chemin relatif à MAKORA_DATA_PATH (ex: models/sante/production/if_v1.joblib)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    feature_names: Mapped[dict] = mapped_column(JSONB, nullable=False)
    contamination: Mapped[float] = mapped_column(Float, nullable=False)
    f1_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    auc_roc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    precision_ppv: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recall_tpr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fpr: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mcc: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    train_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    branch: Mapped["Branch"] = relationship("Branch")
    deployments: Mapped[list["ProductionDeployment"]] = relationship(
        "ProductionDeployment", back_populates="model_version"
    )

    def __repr__(self) -> str:
        return f"<ModelVersion tag={self.version_tag!r} algo={self.algorithm!r}>"


class ProductionDeployment(UUIDMixin, CreatedAtMixin, Base):
    """
    Historique des déploiements en production.
    Contrainte partielle : un seul déploiement actif (replaced_at IS NULL)
    par branche — garantie par l'index partiel unique.

    Pour déployer un nouveau modèle :
      1. Mettre replaced_at = now() sur le déploiement actif
      2. Insérer un nouveau déploiement avec replaced_at = NULL
    """

    __tablename__ = "production_deployments"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=False
    )
    deployed_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    replaced_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deployment_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        Index(
            "idx_production_active_unique",
            "branch_id",
            unique=True,
            postgresql_where=text("replaced_at IS NULL"),
        ),
    )

    # Relationships
    branch: Mapped["Branch"] = relationship("Branch")
    model_version: Mapped["ModelVersion"] = relationship(
        "ModelVersion", back_populates="deployments"
    )
    deployer: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return (
            f"<ProductionDeployment branch={self.branch_id} "
            f"active={self.replaced_at is None}>"
        )


class AnalysisRun(UUIDMixin, CreatedAtMixin, Base):
    """
    Session de détection complète — un ou plusieurs dossiers analysés ensemble.
    Permet de lier les fraud_communities à leur contexte d'analyse.
    started_at ≠ created_at : started_at est l'heure de début réelle du run,
    created_at est l'horodatage d'insertion en base.
    """

    __tablename__ = "analysis_runs"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=False
    )
    run_type: Mapped[str] = mapped_column(String(20), nullable=False)
    nb_dossiers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nb_anomalies: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    graph_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    triggered_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(f"run_type IN {_RUN_TYPES}", name="chk_run_type"),
    )

    # Relationships
    analyses: Mapped[list["Analysis"]] = relationship(
        "Analysis", back_populates="run"
    )
    fraud_communities: Mapped[list["FraudCommunity"]] = relationship(
        "FraudCommunity", back_populates="run"
    )

    def __repr__(self) -> str:
        return f"<AnalysisRun type={self.run_type!r} dossiers={self.nb_dossiers}>"


class Analysis(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "analyses"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("claims.id"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    model_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=False
    )
    # Null si flux structuré (pas de document scanné)
    ocr_extraction_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ocr_extractions.id"), nullable=True
    )
    # Null si graphe désactivé ou aucune communauté détectée
    fraud_community_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fraud_communities.id"), nullable=True
    )
    anomaly_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, nullable=False)
    detector_name: Mapped[str] = mapped_column(String(50), nullable=False)
    rca_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    rca_subcategory: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    rca_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rca_rule_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    explanation_fr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="PENDING"
    )
    processing_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "anomaly_score >= 0 AND anomaly_score <= 1",
            name="chk_analysis_score",
        ),
        CheckConstraint(
            f"decision_status IN {_DECISION_STATUTS}",
            name="chk_analysis_decision",
        ),
        CheckConstraint(
            "rca_confidence IS NULL OR (rca_confidence >= 0 AND rca_confidence <= 1)",
            name="chk_analysis_rca_confidence",
        ),
    )

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="analyses")
    run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="analyses")
    ocr_extraction: Mapped[Optional["OcrExtraction"]] = relationship("OcrExtraction")
    fraud_community: Mapped[Optional["FraudCommunity"]] = relationship("FraudCommunity")
    shap_contributions: Mapped[list["ShapContribution"]] = relationship(
        "ShapContribution", back_populates="analysis", cascade="all, delete-orphan"
    )
    decisions: Mapped[list["Decision"]] = relationship(
        "Decision", back_populates="analysis"
    )
    escalation: Mapped[Optional["Escalation"]] = relationship(
        "Escalation", back_populates="analysis", uselist=False
    )

    def __repr__(self) -> str:
        return (
            f"<Analysis score={self.anomaly_score:.3f} "
            f"anomaly={self.is_anomaly} "
            f"status={self.decision_status!r}>"
        )


class ShapContribution(UUIDMixin, Base):
    __tablename__ = "shap_contributions"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analyses.id", ondelete="CASCADE"),
        nullable=False,
    )
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    shap_value: Mapped[float] = mapped_column(Float, nullable=False)
    feature_value: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    direction: Mapped[str] = mapped_column(String(10), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint(f"direction IN {_DIRECTIONS}", name="chk_shap_direction"),
        CheckConstraint("rank >= 1", name="chk_shap_rank"),
    )

    # Relationships
    analysis: Mapped["Analysis"] = relationship(
        "Analysis", back_populates="shap_contributions"
    )
