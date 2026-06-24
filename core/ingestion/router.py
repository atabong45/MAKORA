"""
MODULE : core/ingestion/router.py
DESCRIPTION : Détecte le type de flux d'entrée (structuré vs documentaire)
              et route vers le reader approprié.

RÉFÉRENCES ACADÉMIQUES :
- [Gamma1994] Gamma et al. (1994). Design Patterns. Pattern : Chain of
  Responsibility / Strategy.
  → Le Router isole la logique de dispatch du reste du pipeline.

DÉCISIONS DE CONCEPTION :
- Détection par extension uniquement en V1 — suffisant pour le prototype.
  La détection par magic bytes (header PDF/PNG) serait plus robuste mais
  hors périmètre V1 (IMP-007 : ne pas sur-ingénier).
- Les deux familles d'extensions sont exhaustives pour le contexte CM :
  PDF (factures scannées) + images (photos de factures sur mobile).
- Fail-fast sur extension inconnue : mieux vaut une erreur claire qu'un
  comportement silencieux inattendu [Sculley2015].
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from core.exceptions import IngestionError
from core.logging_config import get_logger

logger = get_logger(__name__)

FluxType = Literal["structured", "documentary"]

_STRUCTURED_EXTENSIONS: frozenset[str] = frozenset({
    ".csv", ".json", ".parquet", ".pq", ".xlsx",
})

_DOCUMENTARY_EXTENSIONS: frozenset[str] = frozenset({
    ".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp",
})


class Router:
    """
    Détecte le type de flux d'un fichier d'entrée.

    Usage :
        flux = Router.detect("facture_scan.pdf")   # → "documentary"
        flux = Router.detect("sinistres.csv")       # → "structured"
    """

    @staticmethod
    def detect(path: str | Path) -> FluxType:
        """
        Retourne le type de flux selon l'extension du fichier.

        Args:
            path: chemin vers le fichier d'entrée.

        Returns:
            'structured'  → lire avec StructuredReader (CSV/JSON/Parquet)
            'documentary' → lire avec DocumentaryReader (OCR)

        Raises:
            IngestionError: extension non reconnue.
        """
        p = Path(path)
        ext = p.suffix.lower()

        if ext in _STRUCTURED_EXTENSIONS:
            logger.debug("Router : flux structuré détecté — %s", p.name)
            return "structured"

        if ext in _DOCUMENTARY_EXTENSIONS:
            logger.debug("Router : flux documentaire détecté — %s", p.name)
            return "documentary"

        raise IngestionError(
            f"Extension non reconnue : '{ext}'. "
            f"Structuré : {sorted(_STRUCTURED_EXTENSIONS)}. "
            f"Documentaire : {sorted(_DOCUMENTARY_EXTENSIONS)}.",
            payload={"path": str(p), "extension": ext},
        )

    @staticmethod
    def is_documentary(path: str | Path) -> bool:
        """Raccourci booléen — utile dans les conditions de pipeline."""
        try:
            return Router.detect(path) == "documentary"
        except IngestionError:
            return False

    @staticmethod
    def is_structured(path: str | Path) -> bool:
        """Raccourci booléen."""
        try:
            return Router.detect(path) == "structured"
        except IngestionError:
            return False