"""
MODULE : core/db/mixins.py
DESCRIPTION : Mixins réutilisables pour les modèles SQLAlchemy MAKORA.

DÉCISIONS DE CONCEPTION :
- UUIDMixin : UUID v4 généré côté Python — compatibilité tests sans DB,
  unicité garantie sans séquence DB, portabilité entre bases.
- TimestampMixin : updated_at géré via onupdate (Python) ET server_default
  (PostgreSQL) — robustesse en cas d'update SQL direct.
- CreatedAtMixin : séparé de TimestampMixin pour les tables append-only
  (audit_logs, decisions, ocr_extractions) qui ne doivent pas avoir de
  updated_at, ce qui éviterait toute confusion sur leur immuabilité.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


def _utcnow() -> datetime:
    """Retourne l'heure courante en UTC."""
    return datetime.now(timezone.utc)


class UUIDMixin:
    """Ajoute un champ id UUID v4 comme clé primaire."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )


class TimestampMixin:
    """Ajoute created_at et updated_at avec gestion automatique."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
        onupdate=_utcnow,
    )


class CreatedAtMixin:
    """
    Ajoute seulement created_at.
    Utilisé pour les tables append-only :
    audit_logs, decisions, ocr_extractions, shap_contributions.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        server_default=func.now(),
    )
