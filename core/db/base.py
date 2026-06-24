"""
MODULE : core/db/base.py
DESCRIPTION : Infrastructure SQLAlchemy — engine, session, Base déclaratif.

DÉCISIONS DE CONCEPTION :
- SQLAlchemy 2.0 (DeclarativeBase) — style moderne, annotations Mapped.
- pool_pre_ping=True : vérifie la connexion avant usage (robustesse Docker).
- DATABASE_URL lue depuis variable d'environnement — jamais hardcodée.
- get_db() : générateur FastAPI pour l'injection de dépendances.
- DB_ECHO=true active les logs SQL (utile en développement uniquement).
"""

from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://makora:makora@postgres:5432/makora",
)

engine: Engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=os.getenv("DB_ECHO", "false").lower() == "true",
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """
    Base déclarative SQLAlchemy pour tous les modèles MAKORA.
    Tous les modèles héritent de cette classe + les mixins appropriés.
    """
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Générateur FastAPI pour l'injection de dépendances.

    Usage dans un router FastAPI :
        def route(db: Session = Depends(get_db)): ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
