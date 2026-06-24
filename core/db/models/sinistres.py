"""
MODULE : core/db/models/sinistres.py
DESCRIPTION : Modèles SQLAlchemy — Domaine Sinistres & Documents (4 tables).
  claims, claim_lines, claim_documents, ocr_extractions

DÉCISIONS DE CONCEPTION :
- claims.statut = état administratif du dossier (DRAFT → CLOSED).
  Distinct de analyses.decision_status (PENDING → CONFIRMED/REJECTED)
  qui représente la décision IA+humain. Les deux coexistent sans ambiguïté.
- claims.branch_id : colonne régulière, renseignée par l'application
  lors de la création (copiée de contracts.branch_id). Denormalisation
  assumée pour la performance des requêtes /audit?branch=sante.
- claim_lines.praticien_id_hash et garage_id_hash : références souples
  (pas de FK formelle) — un prestataire peut apparaître dans un sinistre
  sans fiche dans la table practitioners/garages. L'enrichissement est async.
- ocr_extractions est append-only (preuve forensique).
  Aucun UPDATE autorisé après création.
- claim_documents.file_path est relatif à la variable MAKORA_DOCUMENTS_PATH.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import Optional

from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Date,
    Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.db.base import Base
from core.db.mixins import UUIDMixin, TimestampMixin, CreatedAtMixin

_CLAIM_STATUTS = "('DRAFT', 'SUBMITTED', 'OPEN', 'CLOSED')"
_SOURCE_FLUX = "('structured', 'documentary', 'batch')"


class Claim(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    contract_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )
    branch_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False
    )
    source_flux: Mapped[str] = mapped_column(String(20), nullable=False)
    montant_facture: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    devise: Mapped[Optional[str]] = mapped_column(String(5), nullable=True, default="XAF")
    montant_xaf: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    date_soin: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_declaration: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    date_saisie: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    heure_saisie: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    statut: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            f"source_flux IN {_SOURCE_FLUX}",
            name="chk_claim_source_flux",
        ),
        CheckConstraint(
            f"statut IN {_CLAIM_STATUTS}",
            name="chk_claim_statut",
        ),
        CheckConstraint(
            "heure_saisie IS NULL OR (heure_saisie >= 0 AND heure_saisie <= 23)",
            name="chk_claim_heure",
        ),
    )

    # Relationships
    contract: Mapped[Optional["Contract"]] = relationship(
        "Contract", back_populates="claims"
    )
    branch: Mapped["Branch"] = relationship("Branch")
    creator: Mapped[Optional["User"]] = relationship("User")
    lines: Mapped[list["ClaimLine"]] = relationship(
        "ClaimLine", back_populates="claim", cascade="all, delete-orphan"
    )
    documents: Mapped[list["ClaimDocument"]] = relationship(
        "ClaimDocument", back_populates="claim", cascade="all, delete-orphan"
    )
    analyses: Mapped[list["Analysis"]] = relationship(
        "Analysis", back_populates="claim"
    )

    def __repr__(self) -> str:
        return f"<Claim claim_id={self.claim_id!r} statut={self.statut!r}>"


class ClaimLine(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "claim_lines"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    code_acte: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    libelle: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    montant_ligne: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    prix_ref: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ratio_prix: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quantite: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=1)
    # Référence souple — pas de FK formelle (enrichissement async)
    praticien_id_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    garage_id_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="lines")


class ClaimDocument(UUIDMixin, CreatedAtMixin, Base):
    __tablename__ = "claim_documents"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # Chemin relatif à MAKORA_DOCUMENTS_PATH (ex: sante/2026/05/SIN_xxx.pdf)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    hash_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    uploaded_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="documents")
    ocr_extraction: Mapped[Optional["OcrExtraction"]] = relationship(
        "OcrExtraction",
        back_populates="document",
        uselist=False,
    )


class OcrExtraction(UUIDMixin, CreatedAtMixin, Base):
    """
    Preuve forensique immuable — append-only.
    Aucun UPDATE autorisé après création.
    En cas de re-traitement OCR, créer une nouvelle ligne.
    """

    __tablename__ = "ocr_extractions"

    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("claim_documents.id"),
        nullable=False,
    )
    score_confiance_global: Mapped[float] = mapped_column(Float, nullable=False)
    score_confiance_montant: Mapped[float] = mapped_column(Float, nullable=False)
    montant_extrait: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    devise_extraite: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    date_soin_extraite: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    code_acte_extrait: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    nom_praticien_extrait: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    etablissement_extrait: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    presence_cachet: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    flag_altere: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    logiciel_retouche: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    hash_image: Mapped[str] = mapped_column(String(64), nullable=False)
    llm_backend_used: Mapped[str] = mapped_column(String(50), nullable=False)
    paddle_text_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tesseract_text_length: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    __table_args__ = (
        CheckConstraint(
            "score_confiance_global >= 0 AND score_confiance_global <= 1",
            name="chk_ocr_score_global",
        ),
        CheckConstraint(
            "score_confiance_montant >= 0 AND score_confiance_montant <= 1",
            name="chk_ocr_score_montant",
        ),
    )

    # Relationships
    document: Mapped["ClaimDocument"] = relationship(
        "ClaimDocument", back_populates="ocr_extraction"
    )

    def __repr__(self) -> str:
        return (
            f"<OcrExtraction success={self.success} "
            f"score={self.score_confiance_global:.2f} "
            f"altere={self.flag_altere}>"
        )
