"""
MODULE : core/base_module.py
DESCRIPTION : Interface abstraite Plugin Contract — contrat que tout module
              MAKORA (Santé, Auto, Vie, Agricole...) doit respecter.
              Le Kernel ne connaît QUE cette interface.

RÉFÉRENCES ACADÉMIQUES :
- [Wolfinger2008] Wolfinger, Reiter & Dhungana (2008). Plug-in architecture
  and design guidelines for customizable enterprise applications. ACM SIGPLAN.
  → Justifie la séparation stricte Kernel / modules via interface abstraite.
- [Gamma1994] Gamma et al. (1994). Design Patterns: Elements of Reusable
  Object-Oriented Software. Pattern : Strategy + Plugin.

DÉCISIONS DE CONCEPTION :
- ABC Python choisi sur typing.Protocol — vérification à l'instanciation,
  pas uniquement au type-check statique. Fail-fast garanti.
- _validate_contract() appelé dans __init__ — impossible de créer un module
  avec un YAML incomplet.
- Méthodes concrètes (get_contamination, is_graph_enabled...) centralisées
  ici pour éviter la duplication dans chaque module.

CONTRAINTE D'ARCHITECTURE (cf. ARCHITECTURE.md, RÈGLE 1) :
  Le Kernel ne contient AUCUN import direct d'un module métier.
  Il reçoit uniquement des instances de BaseModule.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any
import pandas as pd
import yaml

from core.exceptions import PluginContractError
from core.logging_config import get_logger

logger = get_logger(__name__)


# Clés obligatoires dans le YAML d'un module — vérifiées au chargement
_REQUIRED_YAML_KEYS: tuple[str, ...] = (
    "branch",
    "version",
    "features",
    "rca_rules",
    "thresholds",
    "input_schema",
)

_REQUIRED_THRESHOLDS: tuple[str, ...] = (
    "contamination",
    "anomaly_score_alert",
)


class BaseModule(ABC):
    """
    Plugin Contract Python — Interface obligatoire pour tout module MAKORA.

    Pour créer un nouveau module :
        1. Hériter de BaseModule
        2. Implémenter les 4 méthodes abstraites
        3. Appeler super().__init__(config_path) dans __init__
        4. Décorer la classe avec @PluginRegistry.register("nom_branche")

    Exemple minimal :
        @PluginRegistry.register("sante")
        class SanteModule(BaseModule):
            def get_feature_names(self) -> list[str]: ...
            def engineer_features(self, df): ...
            def get_rca_rules(self) -> list[dict]: ...
            def validate_input(self, df) -> tuple[bool, list[str]]: ...
    """

    def __init__(self, config_path: str | Path) -> None:
        self.config_path: Path = Path(config_path)

        if not self.config_path.exists():
            raise PluginContractError(
                f"Fichier de configuration introuvable : {self.config_path}",
                payload={"config_path": str(self.config_path)},
            )

        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                self.config: dict[str, Any] = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise PluginContractError(
                f"YAML invalide : {self.config_path}",
                payload={"yaml_error": str(e)},
            ) from e

        # Validation fail-fast
        self._validate_contract()

        # Attributs centraux extraits du YAML
        self.branch: str = self.config["branch"]
        self.version: str = str(self.config["version"])
        self.thresholds: dict[str, Any] = self.config["thresholds"]

        logger.info(
            "Module chargé : branch=%s version=%s features=%d rca_rules=%d",
            self.branch, self.version,
            len(self.config.get("features", [])),
            len(self.config.get("rca_rules", [])),
        )

    # ────────────────────────────────────────────────────────────────
    # MÉTHODES ABSTRAITES — TOUTES OBLIGATOIRES
    # ────────────────────────────────────────────────────────────────

    @abstractmethod
    def get_feature_names(self) -> list[str]:
        """
        Retourne la liste ordonnée des features que ce module calcule et
        que l'Isolation Forest doit recevoir.

        Contrat :
            - Toutes les features retournées DOIVENT être calculées par
              engineer_features().
            - L'ordre DOIT être stable entre les appels (déterminisme).
            - Limite recommandée : ≤ 20 features (cf. [Liu2008] — dégradation
              de l'Isolation Forest au-delà).
        """
        ...

    @abstractmethod
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule toutes les features dérivées spécifiques à ce module.

        Contrat :
            - Reçoit le DataFrame normalisé (schéma universel).
            - Retourne le DataFrame ENRICHI avec les features calculées.
            - NE MODIFIE PAS les colonnes existantes (uniquement ajout).
            - Gère les valeurs manquantes (aucun NaN ne doit subsister dans
              les colonnes retournées par get_feature_names()).
        """
        ...

    @abstractmethod
    def get_rca_rules(self) -> list[dict[str, Any]]:
        """
        Retourne les règles RCA (Root Cause Analysis) du fichier YAML.

        Contrat :
            - Retourne self.config["rca_rules"].
            - L'ordre des règles = ordre de priorité (première règle matchée
              = diagnostic retenu).
        """
        ...

    @abstractmethod
    def validate_input(self, df: pd.DataFrame) -> tuple[bool, list[str]]:
        """
        Valide que le DataFrame entrant contient les colonnes requises
        pour ce module (en plus du schéma universel).

        Returns:
            (True, []) si valide.
            (False, [liste des messages d'erreur]) sinon.
        """
        ...

    # ────────────────────────────────────────────────────────────────
    # MÉTHODES CONCRÈTES — NE PAS SURCHARGER SAUF RAISON DOCUMENTÉE
    # ────────────────────────────────────────────────────────────────

    def get_contamination(self) -> float:
        """Proportion estimée d'anomalies dans ce module (cf. [Liu2008])."""
        return float(self.thresholds["contamination"])

    def get_anomaly_threshold(self) -> float:
        """Seuil de score au-delà duquel un dossier est marqué anomalie."""
        return float(self.thresholds["anomaly_score_alert"])

    def is_graph_enabled(self) -> bool:
        """True si la brique d'analyse de graphe est activée pour ce module."""
        return bool(self.config.get("graph_analysis", {}).get("enabled", False))

    def get_graph_config(self) -> dict[str, Any] | None:
        """Configuration de la brique graphe, ou None si désactivée."""
        cfg = self.config.get("graph_analysis")
        return cfg if cfg and cfg.get("enabled") else None

    def get_drift_config(self) -> dict[str, Any]:
        """Configuration du drift monitoring."""
        return self.config.get("drift_monitoring", {})

    def get_drift_features(self) -> list[str]:
        """Features à surveiller pour le drift."""
        return list(self.get_drift_config().get("features_to_monitor", []))

    def get_source_mapping(self, source_name: str) -> dict[str, str]:
        """
        Mapping de colonnes source → universel pour une source donnée.

        Args:
            source_name: nom de la source (ex: "noemie_api", "scan_cm").

        Returns:
            Dict {col_source: col_universelle}, ou {} si source inconnue.
        """
        return dict(
            self.config.get("source_mappings", {}).get(source_name, {})
        )

    def list_known_sources(self) -> list[str]:
        """Liste des sources connues pour ce module."""
        return list(self.config.get("source_mappings", {}).keys())

    def get_input_schema(self) -> dict[str, Any]:
        """Schéma des colonnes attendues (déclaré dans le YAML)."""
        return self.config.get("input_schema", {})

    # ────────────────────────────────────────────────────────────────
    # VALIDATION INTERNE — NE PAS SURCHARGER
    # ────────────────────────────────────────────────────────────────

    def _validate_contract(self) -> None:
        """
        Vérifie que le YAML respecte le Plugin Contract minimal.
        Fail-fast : empêche le chargement d'un module incomplet.
        """
        branch_name = self.config.get("branch", "INCONNU")

        # 1. Clés racines obligatoires
        missing = [k for k in _REQUIRED_YAML_KEYS if k not in self.config]
        if missing:
            raise PluginContractError(
                f"Module '{branch_name}' — clés YAML manquantes : {missing}",
                payload={"branch": branch_name, "missing_keys": missing},
            )

        # 2. Seuils obligatoires
        thresholds = self.config.get("thresholds", {})
        missing_t = [t for t in _REQUIRED_THRESHOLDS if t not in thresholds]
        if missing_t:
            raise PluginContractError(
                f"Module '{branch_name}' — thresholds manquants : {missing_t}",
                payload={"branch": branch_name, "missing_thresholds": missing_t},
            )

        # 3. Cohérence contamination ∈ ]0, 0.5[
        c = thresholds["contamination"]
        if not isinstance(c, (int, float)) or not (0 < c < 0.5):
            raise PluginContractError(
                f"Module '{branch_name}' — contamination doit être dans ]0, 0.5[, "
                f"reçu : {c}",
                payload={"contamination": c},
            )

        # 4. features non vide
        if not self.config.get("features"):
            raise PluginContractError(
                f"Module '{branch_name}' — liste de features vide",
                payload={"branch": branch_name},
            )

    def __repr__(self) -> str:
        return (
            f"<{self.__class__.__name__} "
            f"branch='{self.branch}' version='{self.version}'>"
        )