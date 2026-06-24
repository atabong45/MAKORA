"""
MODULE : core/db/models/referentiels.py
DESCRIPTION : Modèles SQLAlchemy — Domaine Référentiels (8 tables).
  branches, insureds, contracts, practitioners, garages,
  employers, insured_employers, reference_prices

DÉCISIONS DE CONCEPTION :
- Toutes les colonnes d'identifiants sensibles (ID_Assure, ID_Praticien,
  ID_Garage, ID_Employeur) sont stockées hashées SHA-256 + sel.
  Jamais de données nominatives en clair (RGPD Art.5, CIMA Art.7).
- contracts.anciennete_jours : hybrid_property calculée en Python.
  Ne peut pas être GENERATED ALWAYS AS PostgreSQL (expression non
  déterministe : dépend de CURRENT_DATE qui change chaque jour).
- claims.branch_id est une colonne régulière dans claims.py.
  Elle est renseignée par l'application lors de la création du sinistre
  (copie de contracts.branch_id). Ce choix garantit les performances des
  requêtes GET /audit?branch=sante sans jointure systématique.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, Float, ForeignKey,
    Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db.base import Base
from core.db.mixins import UUIDMixin, TimestampMixin, CreatedAtMixin


class Branch(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "branches"

    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    contamination_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_score_alert: Mapped[float] = mapped_column(Float, nullable=False, default=0.65)
    anomaly_score_block: Mapped[float] = mapped_column(Float, nullable=False, default=0.90)

    __table_args__ = (
        CheckConstraint(
            "contamination_threshold > 0 AND contamination_threshold < 0.5",
            name="chk_branch_contamination",
        ),
        CheckConstraint(
            "anomaly_score_alert > 0 AND anomaly_score_alert <= 1",
            name="chk_branch_alert",
        ),
        CheckConstraint(
            "anomaly_score_block > 0 AND anomaly_score_block <= 1",
            name="chk_branch_block",
        ),
    )

    def __repr__(self) -> str:
        return f"<Branch code={self.code!r} active={self.is_active}>"


class Insured(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "insureds"

    id_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pays: Mapped[str] = mapped_column(String(10), nullable=False, default="CM")
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    sexe: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "age IS NULL OR (age >= 0 AND age <= 120)",
            name="chk_insured_age",
        ),
        CheckConstraint(
            "sexe IS NULL OR sexe IN ('M', 'F')",
            name="chk_insured_sexe",
        ),
    )

    # Relationships
    contracts: Mapped[list["Contract"]] = relationship(
        "Contract", back_populates="insured"
    )
    insured_employers: Mapped[list["InsuredEmployer"]] = relationship(
        "InsuredEmployer", back_populates="insured", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Insured id_hash={self.id_hash[:8]}...>"


class Contract(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "contracts"

    insured_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("insureds.id"), nullable=False
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    police_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    type_contrat: Mapped[str] = mapped_column(String(50), nullable=False)
    date_souscription: Mapped[date] = mapped_column(Date, nullable=False)
    date_resiliation: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    @hybrid_property
    def anciennete_jours(self) -> Optional[int]:
        """Ancienneté en jours — calculée en Python (non déterministe en DB)."""
        if self.date_souscription:
            return (date.today() - self.date_souscription).days
        return None

    # Relationships
    insured: Mapped["Insured"] = relationship("Insured", back_populates="contracts")
    branch: Mapped["Branch"] = relationship("Branch")
    claims: Mapped[list["Claim"]] = relationship("Claim", back_populates="contract")

    def __repr__(self) -> str:
        return f"<Contract police={self.police_number!r} active={self.is_active}>"


class Practitioner(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "practitioners"

    id_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    specialite: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pays: Mapped[str] = mapped_column(String(10), nullable=False, default="CM")
    agrement_cima: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ratio_prix_moyen: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    nb_sinistres_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<Practitioner id_hash={self.id_hash[:8]}... specialite={self.specialite!r}>"


class Garage(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "garages"

    id_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    nom: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    type_garage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ville: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pays: Mapped[str] = mapped_column(String(10), nullable=False, default="CM")
    agrement_cima: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    ratio_devis_moyen: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    nb_sinistres_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    def __repr__(self) -> str:
        return f"<Garage nom={self.nom!r} ville={self.ville!r}>"


class Employer(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "employers"

    id_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    secteur: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    region: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    nb_assures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    insured_employers: Mapped[list["InsuredEmployer"]] = relationship(
        "InsuredEmployer", back_populates="employer", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Employer id_hash={self.id_hash[:8]}... secteur={self.secteur!r}>"


class InsuredEmployer(UUIDMixin, Base):
    __tablename__ = "insured_employers"

    insured_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("insureds.id"), nullable=False
    )
    employer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employers.id"), nullable=False
    )
    date_debut: Mapped[date] = mapped_column(Date, nullable=False)
    date_fin: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    insured: Mapped["Insured"] = relationship("Insured", back_populates="insured_employers")
    employer: Mapped["Employer"] = relationship("Employer", back_populates="insured_employers")


class ReferencePrice(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "reference_prices"

    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    code_acte: Mapped[str] = mapped_column(String(50), nullable=False)
    libelle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nomenclature: Mapped[str] = mapped_column(String(20), nullable=False)
    prix_ref_xaf: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prix_ref_eur: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    devise_principale: Mapped[str] = mapped_column(String(5), nullable=False)
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_to: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source_document: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Relationships
    branch: Mapped["Branch"] = relationship("Branch")

    def __repr__(self) -> str:
        return f"<ReferencePrice code={self.code_acte!r} nomenclature={self.nomenclature!r}>"
