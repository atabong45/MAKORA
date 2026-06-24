"""
MODULE : core/exceptions.py
DESCRIPTION : Hiérarchie d'exceptions centralisée pour le Kernel MAKORA.

DÉCISIONS DE CONCEPTION :
- Une seule racine MAKORAError permet aux callers de catch toutes les
  erreurs du framework avec un seul except.
- Chaque erreur transporte un code stable (string) pour les logs et l'API,
  + un payload optionnel pour le debug.
- Les exceptions n'héritent jamais de built-ins (sauf Exception) pour
  éviter les ambiguïtés de catch.
"""

from __future__ import annotations
from typing import Any


class MAKORAError(Exception):
    """Racine de toutes les exceptions MAKORA."""

    code: str = "MAKORA_ERROR"

    def __init__(self, message: str, payload: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.payload = payload or {}

    def __str__(self) -> str:
        if self.payload:
            return f"[{self.code}] {self.message} | payload={self.payload}"
        return f"[{self.code}] {self.message}"


# ─── Plugin Contract ────────────────────────────────────────────────────
class PluginContractError(MAKORAError):
    """Violation du Plugin Contract (YAML invalide, méthode manquante...)."""
    code = "PLUGIN_CONTRACT_ERROR"


class PluginNotFoundError(MAKORAError):
    """Module demandé absent du PluginRegistry."""
    code = "PLUGIN_NOT_FOUND"


class PluginAlreadyRegisteredError(MAKORAError):
    """Tentative d'enregistrer deux fois la même branche."""
    code = "PLUGIN_ALREADY_REGISTERED"


# ─── ETL / Pipeline ─────────────────────────────────────────────────────
class IngestionError(MAKORAError):
    """Erreur de lecture d'un fichier source."""
    code = "INGESTION_ERROR"


class MappingError(MAKORAError):
    """Erreur d'application du mapping source → universel."""
    code = "MAPPING_ERROR"


class SchemaValidationError(MAKORAError):
    """Le DataFrame ne respecte pas le schéma universel."""
    code = "SCHEMA_VALIDATION_ERROR"


class NormalizationError(MAKORAError):
    """Erreur lors de la normalisation (devise, encodage...)."""
    code = "NORMALIZATION_ERROR"


# ─── ML / Détection ─────────────────────────────────────────────────────
class DetectorError(MAKORAError):
    """Erreur dans le détecteur (modèle non chargé, features manquantes...)."""
    code = "DETECTOR_ERROR"