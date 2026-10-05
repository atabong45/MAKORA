"""
MODULE : core/db/models/hitl_graph.py
DESCRIPTION : Modèles SQLAlchemy — HITL + Graphe de fraude (4 tables).
  decisions, escalations, fraud_communities, community_members

MODIFICATIONS PHASE 1 :
- Escalation.resolved_by (UUID nullable, FK → users.id) ajouté.
  Trace l'auditeur ayant clôturé l'escalade. Précédemment absent (Bug 6).
- Relationship Escalation.resolver ajoutée.

DÉCISIONS DE CONCEPTION :
- decisions est append-only : on ne modifie pas une décision existante,
  on crée une nouvelle. La plus récente fait foi.
- escalations : une seule escalade active par analyse (uselist=False).
- fraud_communities liée à analysis_runs (détection graphe batch).
- community_members.entity_type + entity_id_hash : référence souple
  (pas de FK formelle) car les entités sont dans des tables distinctes.

RÉFÉRENCES ACADÉMIQUES :
- [Amershi2019] Amershi et al. (2019). Software engineering for ML. ICSE.
  §IV.D — Traçabilité HITL : resolved_by garantit l'audit trail complet.
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
from core.db.mixins import UUIDMixin, CreatedAtMixin

_DECISION_TYPES = "('CONFIRMED', 'REJECTED', 'ESCALATED')"
_ESCALATION_STATUTS = "('PENDING', 'IN_PROGRESS', 'RESOLVED')"
_ENTITY_TYPES = "('praticien', 'assure', 'garage', 'employeur')"


class Decision(UUIDMixin, CreatedAtMixin, Base):
    """
    Décisions humaines sur les analyses — append-only.
    Plusieurs décisions peuvent exister pour la même analyse (historique).
    La plus récente (MAX created_at) détermine decision_status de l'analyse.
    Note : gestionnaire_id contient l'UUID du décideur (gestionnaire OU
    auditeur selon le contexte). Le nom est conservé pour compatibilité.
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

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="decisions")
    gestionnaire: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<Decision decision={self.decision!r} analysis={self.analysis_id}>"


class Escalation(UUIDMixin, CreatedAtMixin, Base):
    """
    Dossiers escaladés à un auditeur senior — workflow PENDING → IN_PROGRESS → RESOLVED.

    Cycle de vie :
      PENDING     : créée par gestionnaire, non assignée
      IN_PROGRESS : auditeur s'est auto-assigné (PATCH /assign)
      RESOLVED    : auditeur a rendu un verdict final (PATCH /resolve)
                    → déclenche la création d'une Decision + màj analyse
    """

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
    # Phase 1 — Bug 6 corrigé : resolved_by trace l'auditeur décideur
    resolved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
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

    analysis: Mapped["Analysis"] = relationship("Analysis", back_populates="escalation")
    escalator: Mapped["User"] = relationship("User", foreign_keys=[escalated_by])
    assignee: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to])
    # Phase 1 — nouvelle relationship
    resolver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by])

    @property
    def claim_id(self):
        """Déduit de l'analyse liée. Requiert que analysis soit eager-loaded."""
        return self.analysis.claim_id if self.analysis else None

    def __repr__(self) -> str:
        return f"<Escalation statut={self.statut!r} analysis={self.analysis_id}>"


class FraudCommunity(UUIDMixin, CreatedAtMixin, Base):
    """
    Communauté d'entités suspectes détectée par Louvain [Blondel2008]
    lors d'un analysis_run. Liée à un run, pas à une analyse individuelle.
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
        CheckConstraint("density >= 0 AND density <= 1", name="chk_community_density"),
        CheckConstraint(
            "suspicion_score >= 0 AND suspicion_score <= 1",
            name="chk_community_score",
        ),
    )

    run: Mapped["AnalysisRun"] = relationship(
        "AnalysisRun", back_populates="fraud_communities"
    )
    members: Mapped[list["CommunityMember"]] = relationship(
        "CommunityMember", back_populates="community", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<FraudCommunity size={self.size} "
            f"density={self.density:.2f} "
            f"suspicious={self.is_suspicious}>"
        )


class CommunityMember(UUIDMixin, Base):
    """
    Membre d'une communauté suspecte. Référence souple via entity_type +
    entity_id_hash (pas de FK formelle — entités hétérogènes).
    """

    __tablename__ = "community_members"

    community_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("fraud_communities.id"), nullable=False
    )
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    centrality_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"entity_type IN {_ENTITY_TYPES}", name="chk_member_entity_type"
        ),
    )

    community: Mapped["FraudCommunity"] = relationship(
        "FraudCommunity", back_populates="members"
    )

    def __repr__(self) -> str:
        return f"<CommunityMember type={self.entity_type!r} hash={self.entity_id_hash[:8]}>"