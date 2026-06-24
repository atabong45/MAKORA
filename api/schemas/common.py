"""
MODULE : api/schemas/common.py
DESCRIPTION : Schémas Pydantic v2 réutilisables — pagination, erreurs, réponses standard.
"""
from datetime import datetime
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    page_size: int
    results: list[T]


class ErrorResponse(BaseModel):
    error: str
    message: str
    timestamp: datetime
    request_id: str | None = None


class SuccessResponse(BaseModel):
    message: str
    data: dict | None = None


class MessageResponse(BaseModel):
    message: str
