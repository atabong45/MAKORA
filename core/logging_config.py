"""
MODULE : core/logging_config.py
DESCRIPTION : Configuration centralisée du logging pour tout le Kernel.

DÉCISIONS DE CONCEPTION :
- Format structuré (timestamp | level | module | message) — facilite
  l'analyse a posteriori et la corrélation avec audit_log.jsonl.
- Niveau lu depuis la variable d'environnement MAKORA_LOG_LEVEL (défaut INFO).
- setup_logging() est idempotent — peut être appelé plusieurs fois sans
  dupliquer les handlers.
"""

from __future__ import annotations
import logging
import os
import sys


_CONFIGURED = False


def setup_logging(level: str | None = None) -> None:
    """
    Configure le logger racine pour tout MAKORA.

    Appelé une fois au démarrage de l'API ou des scripts.
    Idempotent : appels suivants sans effet.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = (level or os.getenv("MAKORA_LOG_LEVEL", "INFO")).upper()

    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
        force=True,
    )

    # Réduction du bruit des libs externes
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)

    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Raccourci pour récupérer un logger nommé."""
    setup_logging()
    return logging.getLogger(name)