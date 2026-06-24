"""
MODULE : api/deps/db.py
DESCRIPTION : Dépendance FastAPI pour l'injection de session SQLAlchemy.
"""
from typing import Generator
from sqlalchemy.orm import Session
from core.db.base import SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
