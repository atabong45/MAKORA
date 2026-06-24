"""
MODULE : api/deps/pagination.py
DESCRIPTION : Paramètres de pagination réutilisables sur tous les endpoints list.
"""
from fastapi import Query
from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int = Query(default=1, ge=1, description="Numéro de page (débute à 1)")
    page_size: int = Query(default=50, ge=1, le=200, description="Taille de page (max 200)")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def get_pagination(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)
