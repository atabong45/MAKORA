"""
MODULE : core/schema_validator.py
DESCRIPTION : Validation Pydantic v2 du schéma universel MAKORA.
              Vérifie que tout DataFrame entrant dans le Kernel contient
              les colonnes universelles minimales avec les bons types.

RÉFÉRENCES ACADÉMIQUES :
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML systems.
  → Justifie la validation systématique des données en entrée du pipeline.
- [Polyzotis2017] Polyzotis et al. (2017). Data management challenges in
  production ML. Section "Data Validation".

DÉCISIONS DE CONCEPTION :
- Pydantic v2 (D-09 figée dans MASTER_CONTEXT.md) — performance + clarté
  des erreurs.
- Le schéma universel ne valide QUE les colonnes du Kernel ; les colonnes
  métier sont validées par module.validate_input().
- Validation row-by-row optionnelle (lent) ou colonnes-only (rapide). Le
  pipeline utilise colonnes-only par défaut, row-by-row uniquement en CI.
"""

from __future__ import annotations
from typing import Literal
from datetime import datetime
import pandas as pd
from pydantic import BaseModel, Field, ConfigDict, field_validator

from core.exceptions import SchemaValidationError
from core.logging_config import get_logger

logger = get_logger(__name__) 


# ────────────────────────────────────────────────────────────────────────
# SCHÉMA UNIVERSEL — colonnes minimales pour traverser le Kernel
# ────────────────────────────────────────────────────────────────────────

class UniversalRecord(BaseModel):
    """
    Schéma universel MAKORA — colonnes minimales du dataset universel
    (cf. CAHIER_TECHNIQUE §25 — 7 dimensions fonctionnelles).

    Les modules métiers ajoutent leurs propres colonnes via input_schema
    dans leur YAML et les valident via validate_input().
    """

    model_config = ConfigDict(extra="allow", strict=False)

    # Dim 1 — IDENTITÉ & CONTRAT
    ID_Sinistre: str = Field(..., min_length=1, description="Identifiant unique du dossier")
    ID_Assure: str = Field(..., min_length=1, description="Identifiant pseudonymisé de l'assuré")

    # Dim 3 — FINANCIÈRE
    Montant_Facture: float = Field(..., ge=0, description="Montant facturé")
    Devise: Literal["EUR", "XAF", "USD"] = Field(..., description="Devise du montant")

    # Dim 4 — TEMPORELLE
    Date_Soin: datetime = Field(..., description="Date du soin / sinistre")

    # Dim 5 — PREUVES & SOURCE
    Source_Flux: str = Field(..., min_length=1, description="Identifiant de la source")

    @field_validator("Devise", mode="before")
    @classmethod
    def _normalize_currency_code(cls, v):  # noqa: D401
        """Force le code devise en majuscules."""
        return str(v).strip().upper() if v is not None else v
    
    @field_validator("Date_Soin", mode="before")
    @classmethod
    def _coerce_date_soin(cls, v):
        """
        Accepte les formats date ISO sans heure (ex: '2025-01-15') en plus
        des datetimes complets (ex: '2025-01-15T10:30:00').
        Justification : les sources de données assurance fournissent souvent
        des dates sans heure (champ Date_Soin = date métier, pas timestamp).
        [Polyzotis2017] — tolérance sur types ISO 8601 dans validation pipeline.
        """
        if v is None:
            return v
        # Déjà datetime
        if isinstance(v, datetime):
            return v
        # Date ISO sans heure : "2025-01-15"
        if isinstance(v, str):
            try:
                # Tentative parse complet datetime ISO
                return datetime.fromisoformat(v)
            except ValueError:
                # Fallback : essayer comme date pure
                try:
                    from datetime import date
                    d = date.fromisoformat(v)
                    return datetime(d.year, d.month, d.day)
                except ValueError:
                    pass
        # Pandas Timestamp
        if hasattr(v, "to_pydatetime"):
            return v.to_pydatetime()
        return v


# ────────────────────────────────────────────────────────────────────────
# VALIDATEUR DataFrame
# ────────────────────────────────────────────────────────────────────────

# Colonnes universelles minimales — extrait des Field requis ci-dessus
UNIVERSAL_REQUIRED_COLUMNS: tuple[str, ...] = (
    "ID_Sinistre",
    "ID_Assure",
    "Montant_Facture",
    "Devise",
    "Date_Soin",
    "Source_Flux",
)


def validate_universal_schema(
    df: pd.DataFrame,
    *,
    full_row_validation: bool = False,
    max_errors_to_report: int = 10,
) -> None:
    """
    Valide qu'un DataFrame respecte le schéma universel MAKORA.

    Args:
        df: DataFrame à valider.
        full_row_validation: si True, valide chaque ligne avec Pydantic
            (lent sur >10k lignes — réservé aux tests).
        max_errors_to_report: nombre max d'erreurs détaillées dans la payload.

    Raises:
        SchemaValidationError: si une colonne manque, un type est invalide,
            ou (si full_row_validation=True) une ligne est invalide.
    """
    if df is None or df.empty:
        raise SchemaValidationError(
            "DataFrame vide ou None.",
            payload={"n_rows": 0 if df is None else len(df)},
        )

    # 1. Colonnes obligatoires présentes ?
    missing = [c for c in UNIVERSAL_REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise SchemaValidationError(
            f"Colonnes universelles manquantes : {missing}",
            payload={
                "missing_columns": missing,
                "received_columns": list(df.columns),
            },
        )

    # 2. Types des colonnes universelles
    type_errors: list[str] = []

    if not pd.api.types.is_numeric_dtype(df["Montant_Facture"]):
        type_errors.append("Montant_Facture doit être numérique")

    if pd.to_numeric(df["Montant_Facture"], errors="coerce").min() < 0:
        type_errors.append("Montant_Facture contient des valeurs négatives")

    if not (
        pd.api.types.is_datetime64_any_dtype(df["Date_Soin"])
        or pd.api.types.is_string_dtype(df["Date_Soin"])
    ):
        type_errors.append("Date_Soin doit être datetime ou string parseable")

    if type_errors:
        raise SchemaValidationError(
            f"Types invalides : {type_errors}",
            payload={"type_errors": type_errors},
        )

    # 3. Validation ligne-à-ligne (optionnelle, lente)
    if full_row_validation:
        row_errors: list[dict] = []
        for idx, row in df.iterrows():
            try:
                UniversalRecord.model_validate(row.to_dict())
            except Exception as e:
                row_errors.append({"row": int(idx), "error": str(e)})
                if len(row_errors) >= max_errors_to_report:
                    break
        if row_errors:
            raise SchemaValidationError(
                f"{len(row_errors)} ligne(s) invalide(s) "
                f"(top {max_errors_to_report} reportées).",
                payload={"row_errors": row_errors},
            )

    logger.info(
        "Schéma universel validé : %d lignes, %d colonnes",
        len(df), len(df.columns),
    )