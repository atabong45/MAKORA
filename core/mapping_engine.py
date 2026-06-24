"""
MODULE : core/mapping_engine.py
DESCRIPTION : Adapter universel — traduit n'importe quel schéma source
              (NOEMIE FR, scan CM, futurs partenaires) vers le schéma
              universel MAKORA.

RÉFÉRENCES ACADÉMIQUES :
- [Gamma1994] Gamma et al. (1994). Design Patterns. Pattern : Adapter.
  → Le MappingEngine est l'adapter canonique source → universel.
- [Kandel2011] Kandel et al. (2011). Research directions in data wrangling.
  → Justifie l'externalisation des mappings dans des fichiers déclaratifs.

DÉCISIONS DE CONCEPTION :
- Mapping déclaratif dans le YAML du module (pas dans le code) — un expert
  métier peut ajouter une nouvelle source sans toucher au Python.
- Renommage non-destructif : si une colonne universelle existe déjà dans
  la source, elle est conservée (identity mapping implicite).
- Fail-fast sur colonnes attendues absentes APRÈS mapping (pas avant —
  certaines colonnes peuvent provenir du normalizer).
"""

from __future__ import annotations
from typing import Iterable
import pandas as pd

from core.exceptions import MappingError
from core.logging_config import get_logger

logger = get_logger(__name__)


class MappingEngine:
    """
    Applique un mapping de colonnes (déclaré dans le YAML d'un module)
    sur un DataFrame brut pour produire un DataFrame au schéma universel.

    Le MappingEngine est stateless — toute la config vient des arguments.
    """

    @staticmethod
    def apply(
        df: pd.DataFrame,
        mapping: dict[str, str],
        *,
        strict: bool = False,
        drop_unmapped: bool = False,
    ) -> pd.DataFrame:
        """
        Applique le mapping {col_source: col_universelle} sur df.

        Args:
            df: DataFrame brut (colonnes en schéma source).
            mapping: dict {col_source: col_universelle}.
            strict: si True, lève si une col_source du mapping est absente
                du df. Sinon log un warning et continue.
            drop_unmapped: si True, supprime du df final toutes les colonnes
                qui ne sont ni dans le mapping ni déjà en schéma universel.

        Returns:
            DataFrame avec colonnes renommées vers le schéma universel.

        Raises:
            MappingError: mapping invalide ou (si strict) colonne absente.
        """
        if df is None or df.empty:
            raise MappingError(
                "DataFrame vide ou None — impossible d'appliquer le mapping.",
                payload={"n_rows": 0 if df is None else len(df)},
            )

        if not isinstance(mapping, dict):
            raise MappingError(
                "Le mapping doit être un dict {col_source: col_universelle}.",
                payload={"mapping_type": type(mapping).__name__},
            )

        # Mapping vide → identity (le DataFrame est supposé déjà en universel)
        if not mapping:
            logger.info(
                "Mapping vide — DataFrame supposé déjà en schéma universel."
            )
            return df.copy()

        present_sources = [c for c in mapping if c in df.columns]
        missing_sources = [c for c in mapping if c not in df.columns]

        if missing_sources:
            msg = (
                f"{len(missing_sources)} colonne(s) source absente(s) du DataFrame : "
                f"{missing_sources[:5]}{'...' if len(missing_sources) > 5 else ''}"
            )
            if strict:
                raise MappingError(
                    msg,
                    payload={"missing_source_columns": missing_sources},
                )
            logger.warning(msg)

        # Détection des collisions : col_universelle déjà présente
        rename_dict = {src: mapping[src] for src in present_sources}
        target_columns = set(rename_dict.values())
        collisions = [
            col for col in target_columns
            if col in df.columns and col not in rename_dict
        ]
        if collisions:
            raise MappingError(
                f"Collision : colonnes universelles déjà présentes dans la source : "
                f"{collisions}. Impossible de mapper sans écrasement.",
                payload={"collisions": collisions},
            )

        result = df.rename(columns=rename_dict).copy()

        if drop_unmapped:
            keep = set(mapping.values())
            # Conserver aussi les colonnes déjà en schéma universel
            # (elles ne sont pas dans le mapping mais sont valides)
            kept_cols = [c for c in result.columns if c in keep or c in df.columns and c not in mapping]
            result = result[[c for c in kept_cols if c in result.columns]]

        logger.info(
            "Mapping appliqué : %d colonne(s) renommée(s), %d colonne(s) source absente(s).",
            len(rename_dict), len(missing_sources),
        )
        return result

    # ────────────────────────────────────────────────────────────────
    # DÉTECTION DE SOURCE
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def detect_source(
        df: pd.DataFrame,
        available_sources: dict[str, dict[str, str]],
    ) -> str:
        """
        Détecte la source d'un DataFrame en cherchant le mapping qui
        couvre le plus de colonnes présentes.

        Args:
            df: DataFrame brut.
            available_sources: dict {nom_source: mapping}, typiquement
                module.config["source_mappings"].

        Returns:
            Nom de la source détectée.

        Raises:
            MappingError: si aucune source ne correspond.
        """
        if not available_sources:
            raise MappingError(
                "Aucune source disponible — vérifier source_mappings dans le YAML.",
                payload={},
            )

        df_cols = set(df.columns)
        scores: dict[str, float] = {}

        for source_name, mapping in available_sources.items():
            if not mapping:
                # Mapping vide = source "universelle" — match toutes les
                # colonnes universelles présentes
                scores[source_name] = sum(
                    1 for c in df_cols if not c.startswith("_")
                ) / max(len(df_cols), 1)
                continue
            n_matched = sum(1 for src in mapping if src in df_cols)
            scores[source_name] = n_matched / max(len(mapping), 1)

        best = max(scores, key=scores.get)
        if scores[best] < 0.5:
            raise MappingError(
                f"Aucune source ne correspond à plus de 50% des colonnes "
                f"(meilleur match : {best} = {scores[best]:.0%}).",
                payload={"scores": scores, "columns": list(df_cols)[:20]},
            )

        logger.info(
            "Source détectée : '%s' (couverture %.0f%%)", best, scores[best] * 100,
        )
        return best

    @staticmethod
    def validate_mapping_completeness(
        mapping: dict[str, str],
        required_universal_columns: Iterable[str],
    ) -> list[str]:
        """
        Vérifie qu'un mapping couvre toutes les colonnes universelles
        requises.

        Returns:
            Liste des colonnes universelles non couvertes (vide si OK).
        """
        target_cols = set(mapping.values())
        return [c for c in required_universal_columns if c not in target_cols]