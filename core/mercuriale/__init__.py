"""
PACKAGE : core/mercuriale/
DESCRIPTION : Brique générique de chargement des référentiels de prix MAKORA.

              Utilisée par tout module ayant besoin de comparer des montants
              facturés à un prix de référence normé (mercuriale CIMA, barème
              ASAC Auto, etc.).

              Le Kernel expose ce package — les modules l'importent sans que
              le Kernel connaisse les modules concrets. Respecte la règle d'or
              d'isolation Kernel / modules.

Exports publics :
    MercurialeLoader  — classe principale de chargement
    MercurialeIndex   — index en mémoire, optimisé pour lookup vectorisé
    MercurialeEntry   — dataclass représentant une ligne du référentiel
    MercurialeFileError, MercurialeFormatError, CodeAbsentError — exceptions
"""

from core.mercuriale.exceptions import (
    CodeAbsentError,
    MercurialeError,
    MercurialeFileError,
    MercurialeFormatError,
)
from core.mercuriale.loader import MercurialeLoader
from core.mercuriale.models import (
    TAUX_BEAC_EUR_XAF,
    MercurialeEntry,
    MercurialeIndex,
)

__all__ = [
    "MercurialeLoader",
    "MercurialeIndex",
    "MercurialeEntry",
    "MercurialeError",
    "MercurialeFileError",
    "MercurialeFormatError",
    "CodeAbsentError",
    "TAUX_BEAC_EUR_XAF",
]