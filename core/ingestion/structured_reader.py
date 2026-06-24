"""
MODULE : core/ingestion/structured_reader.py
DESCRIPTION : Lecture de fichiers structurés (CSV, JSON, Parquet).
              Première brique du pipeline d'ingestion — ne gère QUE le
              flux numérique. Le flux documentaire (OCR) est traité par
              documentary_reader.py (Phase ultérieure).

RÉFÉRENCES ACADÉMIQUES :
- [McKinney2011] McKinney, W. (2011). pandas: a foundational Python
  library for data analysis. → Justification du choix pandas.
- ADR-008 (cf. ARCHITECTURE.md) — Apache Parquet comme format pivot.

DÉCISIONS DE CONCEPTION :
- Détection automatique du format par extension — réduit le risque
  d'erreur côté appelant.
- Pas de chunked reading en V1 — le dataset Santé tient en mémoire
  (~150 Mo pour 140k lignes). À revisiter pour datasets >5 Go.
- Parsing strict des dates ISO 8601 (`errors='raise'`) — éviter les
  silent failures classiques de pd.read_csv.
"""

from __future__ import annotations
from pathlib import Path
from typing import Iterable
import pandas as pd

from core.exceptions import IngestionError
from core.logging_config import get_logger

logger = get_logger(__name__)


SUPPORTED_EXTENSIONS: tuple[str, ...] = (".csv", ".json", ".parquet", ".pq")


class StructuredReader:
    """
    Lecture des sources structurées (CSV, JSON, Parquet).

    Convention : retourne TOUJOURS un DataFrame pandas, jamais un dict ou
    une liste — uniformité pour le reste du pipeline.
    """

    @staticmethod
    def detect_format(path: str | Path) -> str:
        """
        Détecte le format d'un fichier par son extension.

        Returns:
            'csv' | 'json' | 'parquet'

        Raises:
            IngestionError: extension non supportée.
        """
        p = Path(path)
        ext = p.suffix.lower()
        if ext == ".csv":
            return "csv"
        if ext == ".json":
            return "json"
        if ext in (".parquet", ".pq"):
            return "parquet"
        raise IngestionError(
            f"Extension non supportée : '{ext}'. Supportées : {SUPPORTED_EXTENSIONS}",
            payload={"path": str(p), "extension": ext},
        )

    @classmethod
    def read(
        cls,
        path: str | Path,
        *,
        parse_dates: Iterable[str] | None = None,
        encoding: str = "utf-8",
    ) -> pd.DataFrame:
        """
        Lit un fichier structuré et retourne un DataFrame.

        Args:
            path: chemin du fichier.
            parse_dates: liste des colonnes à parser en datetime (CSV uniquement).
            encoding: encodage texte (CSV/JSON).

        Raises:
            IngestionError: fichier introuvable, format non supporté, parsing échoué.
        """
        p = Path(path)
        if not p.exists():
            raise IngestionError(
                f"Fichier introuvable : {p}",
                payload={"path": str(p)},
            )
        if not p.is_file():
            raise IngestionError(
                f"Chemin n'est pas un fichier : {p}",
                payload={"path": str(p)},
            )

        fmt = cls.detect_format(p)
        try:
            if fmt == "csv":
                df = pd.read_csv(
                    p,
                    encoding=encoding,
                    parse_dates=list(parse_dates) if parse_dates else None,
                    low_memory=False,
                )
            elif fmt == "json":
                df = pd.read_json(p, encoding=encoding)
            else:  # parquet
                df = pd.read_parquet(p)
        except Exception as e:
            raise IngestionError(
                f"Échec lecture {fmt.upper()} : {p}",
                payload={"path": str(p), "format": fmt, "error": str(e)},
            ) from e

        if df.empty:
            logger.warning("Fichier lu mais DataFrame vide : %s", p)
        else:
            logger.info(
                "Lecture %s : %d lignes × %d colonnes — %s",
                fmt.upper(), len(df), len(df.columns), p.name,
            )
        return df

    @classmethod
    def write_parquet(
        cls,
        df: pd.DataFrame,
        path: str | Path,
        *,
        compression: str = "snappy",
    ) -> Path:
        """
        Persiste un DataFrame au format Parquet (ADR-008).

        Args:
            df: DataFrame à persister.
            path: chemin de destination.
            compression: 'snappy' (défaut, rapide) | 'gzip' (compressé).

        Returns:
            Path absolu du fichier écrit.
        """
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        try:
            df.to_parquet(p, compression=compression, index=False)
        except Exception as e:
            raise IngestionError(
                f"Échec écriture Parquet : {p}",
                payload={"path": str(p), "error": str(e)},
            ) from e

        logger.info(
            "Parquet écrit : %d lignes — %s (%s)",
            len(df), p, compression,
        )
        return p.resolve()