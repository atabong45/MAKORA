"""
Package core/db — Base de données MAKORA (PostgreSQL 15+ / SQLAlchemy 2.0).

Exports publics :
- Base       : classe déclarative SQLAlchemy (tous les modèles en héritent)
- engine     : moteur SQLAlchemy connecté à PostgreSQL
- SessionLocal : factory de sessions
- get_db()   : générateur FastAPI pour l'injection de dépendances
"""

from core.db.base import Base, engine, SessionLocal, get_db
from core.db.models import *  # noqa: F401, F403 — enregistrement de tous les modèles

__all__ = ["Base", "engine", "SessionLocal", "get_db"]
