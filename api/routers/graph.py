"""
MODULE : api/routers/graph.py
DESCRIPTION : Router FastAPI — Graphe de fraude Louvain (4 endpoints).
Référence : [Blondel2008] Fast unfolding of communities in large networks.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.common import PaginatedResponse
from api.schemas.graph import CommunityMemberResponse, FraudCommunityResponse
from api.services import graph_service as svc
from core.db.models.iam import User

router = APIRouter(prefix="/graph", tags=["Graphe de Fraude"])
_read = Depends(require_roles("auditeur", "administrateur"))


@router.get("/communities", response_model=PaginatedResponse[FraudCommunityResponse])
def list_communities(
    is_suspicious: bool | None = Query(None), size_min: int | None = Query(None, ge=2),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _read,
):
    total, items = svc.list_communities(db, None, is_suspicious, size_min, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)


@router.get("/communities/{community_id}", response_model=FraudCommunityResponse)
def get_community(community_id: UUID, db: Session = Depends(get_db), _: User = _read):
    return svc.get_community(db, community_id)


@router.get("/communities/{community_id}/members", response_model=list[CommunityMemberResponse])
def get_members(community_id: UUID, db: Session = Depends(get_db), _: User = _read):
    return svc.get_community_members(db, community_id)


@router.get("/runs/{run_id}/communities", response_model=PaginatedResponse[FraudCommunityResponse])
def get_run_communities(
    run_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _read,
):
    total, items = svc.get_run_communities(db, run_id, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)
