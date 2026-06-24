"""
MODULE : core/db/models/monitoring.py
DESCRIPTION : Modèles SQLAlchemy — Monitoring + Audit + Config (7 tables).
  drift_reports, drift_feature_metrics, retraining_requests,
  audit_logs, export_reports, module_configs, rca_rule_snapshots

CORRECTION DT-DRIFT-001 :
- computed_at ajouté sur DriftReport.
  drift_service.py utilise .order_by(DriftReport.computed_at.desc()) et
  last.computed_at.isoformat() — le champ était absent du modèle, causant
  un AttributeError avalé en 500 par generic_exception_handler.
  Valeur par défaut : datetime.now(timezone.utc) — cohérent avec les autres
  timestamps du projet (created_at dans CreatedAtMixin).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, text,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db.base import Base
from core.db.mixins import UUIDMixin, TimestampMixin, CreatedAtMixin

_DRIFT_STATUTS = "('STABLE', 'WARNING', 'CRITICAL')"
_DRIFT_FEAT_STATUTS = "('STABLE', 'WARNING', 'CRITICAL', 'UNKNOWN')"
_RETRAINING_STATUTS = "('PENDING', 'APPROVED', 'IN_PROGRESS', 'DONE', 'REJECTED')"
_AUDIT_RESULTS = "('SUCCESS', 'FAILURE')"
_EXPORT_STATUTS = "('PENDING', 'GENERATING', 'READY', 'FAILED')"
_LOGIC_TYPES = "('AND', 'OR')"


class DriftReport(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "drift_reports"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    psi_max: Mapped[float] = mapped_column(Float, nullable=False)
    n_features_analyzed: Mapped[int] = mapped_column(Integer, nullable=False)
    n_features_warning: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    n_features_critical: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reference_window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    current_window_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    triggered_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    # DT-DRIFT-001 : champ manquant — utilisé dans drift_service.py
    # order_by(DriftReport.computed_at.desc()) et last.computed_at.isoformat()
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint(f"status IN {_DRIFT_STATUTS}", name="chk_drift_status"),
        CheckConstraint("psi_max >= 0", name="chk_drift_psi"),
    )

    # Relationships
    feature_metrics: Mapped[list["DriftFeatureMetric"]] = relationship(
        "DriftFeatureMetric",
        back_populates="report",
        cascade="all, delete-orphan",
    )
    retraining_requests: Mapped[list["RetrainingRequest"]] = relationship(
        "RetrainingRequest", back_populates="drift_report"
    )

    def __repr__(self) -> str:
        return f"<DriftReport status={self.status!r} psi_max={self.psi_max:.3f}>"


class DriftFeatureMetric(UUIDMixin, Base):
    __tablename__ = "drift_feature_metrics"

    report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("drift_reports.id", ondelete="CASCADE"),
        nullable=False,
    )
    feature_name: Mapped[str] = mapped_column(String(100), nullable=False)
    psi_value: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    n_reference: Mapped[int] = mapped_column(Integer, nullable=False)
    n_current: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint(
            f"status IN {_DRIFT_FEAT_STATUTS}",
            name="chk_drift_feat_status",
        ),
        CheckConstraint("psi_value >= 0", name="chk_drift_feat_psi"),
    )

    # Relationships
    report: Mapped["DriftReport"] = relationship(
        "DriftReport", back_populates="feature_metrics"
    )


class RetrainingRequest(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "retraining_requests"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    drift_report_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drift_reports.id"), nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    new_model_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("model_versions.id"), nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN {_RETRAINING_STATUTS}",
            name="chk_retraining_status",
        ),
    )

    # Relationships
    drift_report: Mapped[Optional["DriftReport"]] = relationship(
        "DriftReport", back_populates="retraining_requests"
    )
    requester: Mapped["User"] = relationship("User", foreign_keys=[requested_by])
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by])

    def __repr__(self) -> str:
        return f"<RetrainingRequest status={self.status!r}>"


class AuditLog(UUIDMixin, CreatedAtMixin, Base):
    """
    Journal immuable — append-only.
    Conformité CIMA (Art.12 : conservation 10 ans) et RGPD (Art.5).
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    result: Mapped[str] = mapped_column(String(10), nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(f"result IN {_AUDIT_RESULTS}", name="chk_audit_result"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog action={self.action!r} result={self.result!r}>"


class ExportReport(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "export_reports"

    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)
    branch_filter: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    decision_filter: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    date_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    file_format: Mapped[str] = mapped_column(String(10), nullable=False, default="csv")
    row_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(f"status IN {_EXPORT_STATUTS}", name="chk_export_status"),
    )

    # Relationships
    requester: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<ExportReport type={self.report_type!r} status={self.status!r}>"


class ModuleConfig(UUIDMixin, CreatedAtMixin, Base):
    """
    Snapshots versionnés du YAML de chaque module.
    Index partiel unique : un seul config actif par branche.
    """

    __tablename__ = "module_configs"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    version_tag: Mapped[str] = mapped_column(String(50), nullable=False)
    yaml_content: Mapped[str] = mapped_column(Text, nullable=False)
    yaml_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        Index(
            "idx_module_config_active_unique",
            "branch_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    # Relationships
    rca_rule_snapshots: Mapped[list["RcaRuleSnapshot"]] = relationship(
        "RcaRuleSnapshot",
        back_populates="module_config",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<ModuleConfig branch={self.branch_id} version={self.version_tag!r}>"


class RcaRuleSnapshot(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "rca_rule_snapshots"

    module_config_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("module_configs.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_id: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    subcategory: Mapped[str] = mapped_column(String(200), nullable=False)
    conditions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    confidence_base: Mapped[float] = mapped_column(Float, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False)
    logic: Mapped[str] = mapped_column(String(5), nullable=False)

    __table_args__ = (
        CheckConstraint(f"logic IN {_LOGIC_TYPES}", name="chk_rca_logic"),
        CheckConstraint(
            "confidence_base >= 0 AND confidence_base <= 1",
            name="chk_rca_confidence",
        ),
        CheckConstraint("priority >= 1", name="chk_rca_priority"),
    )

    # Relationships
    module_config: Mapped["ModuleConfig"] = relationship(
        "ModuleConfig", back_populates="rca_rule_snapshots"
    )

    def __repr__(self) -> str:
        return f"<RcaRuleSnapshot rule={self.rule_id!r} priority={self.priority}>"