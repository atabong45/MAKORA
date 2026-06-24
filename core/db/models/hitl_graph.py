"""
MODULE : core/db/models/hitl_graph.py
DESCRIPTION : Modèles SQLAlchemy — HITL + Graphe de fraude (4 tables).
  decisions, escalations, fraud_communities, community_members

DÉCISIONS DE CONCEPTION :
- decisions est append-only : on ne modifie pas une décision existante,
  on crée une nouvelle. La plus récente fait foi.
  Un trigger met à jour analyses.decision_status après chaque INSERT.
- escalations : une seule escalade par analyse (uselist=False depuis Analysis).
- fraud_communities liée à analysis_runs (pas à analyses individuelles)
  car la détection de communautés opère sur un batch complet.
- community_members.entity_type + entity_id_hash : référence souple
  (pas de FK formelle) car les entités peuvent être de types différents
  (praticien, assuré, garage, employeur) résidant dans des tables distinctes.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Float, ForeignKey,
    Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db.base import Base
from core.db.mixins import UUIDMixin, CreatedAtMixin, TimestampMixin

_DECISION_TYPES = "('CONFIRMED', 'REJECTED', 'ESCALATED')"
_ESCALATION_STATUTS = "('PENDING', 'IN_PROGRESS', 'RESOLVED')"
_ENTITY_TYPES = "('praticien', 'assure', 'garage', 'employeur')"


class Decision(UUIDMixin, CreatedAtMixin, Base):
    """
    Décisions humaines sur les analyses — append-only.
    Plusieurs décisions peuvent exister pour la même analyse (historique).
    La plus récente (MAX created_at) détermine decision_status de l'analyse.
    """

    __tablename__ = "decisions"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    motif: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gestionnaire_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )

    __table_args__ = (
        CheckConstraint(f"decision IN {_DECISION_TYPES}", name="chk_decision_type"),
    )

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="decisions")
    gestionnaire: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<Decision decision={self.decision!r} analysis={self.analysis_id}>"


class Escalation(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "escalations"

    analysis_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analyses.id"), nullable=False
    )
    escalated_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    motif_escalade: Mapped[str] = mapped_column(Text, nullable=False)
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    resolution_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            f"statut IN {_ESCALATION_STATUTS}",
            name="chk_escalation_statut",
        ),
    )

    # Relationships
    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="escalation")
    escalator: Mapped["User"] = relationship("User", foreign_keys=[escalated_by])
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to])

    def __repr__(self) -> str:
        return f"<Escalation statut={self.statut!r} analysis={self.analysis_id}>"


class FraudCommunity(UUIDMixin, CreatedAtMixin, Base):
    """
    Communauté d'entités suspectes détectée par Louvain [Blondel2008]
    lors d'un analysis_run. Liée à un run, pas à une analyse individuelle —
    la détection graphe est batch par nature.
    """

    __tablename__ = "fraud_communities"

    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("analysis_runs.id"), nullable=False
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    community_id_louvain: Mapped[int] = mapped_column(Integer, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    density: Mapped[float] = mapped_column(Float, nullable=False)
    modularity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    avg_weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_suspicious: Mapped[bool] = mapped_column(Boolean, nullable=False)
    suspicion_score: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint("size >= 2", name="chk_community_size"),
        CheckConstraint(
            "density >= 0 AND density <= 1",
            name="chk_community_density",
        ),
        CheckConstraint(
            "suspicion_score >= 0 AND suspicion_score <= 1",
            name="chk_community_score",
        ),
    )

    # Relationships
    run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun", back_populates="fraud_communities"
    )
    members: Mapped[list["CommunityMember"]] = relationship(
        "CommunityMember",
        back_populates="community",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<FraudCommunity size={self.size} "
            f"density={self.density:.2f} "
            f"suspicious={self.is_suspicious}>"
        )


class CommunityMember(UUIDMixin, Base):
    __tablename__ = "community_members"

    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fraud_communities.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # Référence souple — pas de FK formelle (polymorphisme multi-tables)
    entity_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    node_score: Mapped[float] = mapped_column(Float, nullable=False)
    is_central: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint(
            f"entity_type IN {_ENTITY_TYPES}",
            name="chk_member_entity_type",
        ),
        CheckConstraint(
            "node_score >= 0 AND node_score <= 1",
            name="chk_member_score",
        ),
    )

    # Relationships
    community: Mapped["FraudCommunity"] = relationship(
        "FraudCommunity", back_populates="members"
    )

    def __repr__(self) -> str:
        return (
            f"<CommunityMember type={self.entity_type!r} "
            f"score={self.node_score:.3f} "
            f"central={self.is_central}>"
        )
