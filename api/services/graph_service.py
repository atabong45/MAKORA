"""
MODULE : api/services/graph_service.py
DESCRIPTION : Service graphe de fraude — lecture communautés Louvain [Blondel2008].
Ce service est read-only : les communautés sont calculées par analyze_service.
"""
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session


def list_communities(db: Session, branch: str | None, is_suspicious: bool | None, size_min: int | None, offset: int, limit: int):
    from core.db.models.hitl_graph import FraudCommunity
    q = db.query(FraudCommunity)
    if is_suspicious is not None:
        q = q.filter(FraudCommunity.is_suspicious == is_suspicious)
    if size_min:
        q = q.filter(FraudCommunity.size >= size_min)
    total = q.count()
    return total, q.order_by(FraudCommunity.suspicion_score.desc()).offset(offset).limit(limit).all()


def get_community(db: Session, community_id: UUID):
    from core.db.models.hitl_graph import FraudCommunity
    c = db.query(FraudCommunity).filter(FraudCommunity.id == community_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Communauté introuvable")
    return c


def get_community_members(db: Session, community_id: UUID):
    from core.db.models.hitl_graph import CommunityMember
    return db.query(CommunityMember).filter(CommunityMember.community_id == community_id).order_by(CommunityMember.node_score.desc()).all()


def get_run_communities(db: Session, run_id: UUID, offset: int, limit: int):
    from core.db.models.hitl_graph import FraudCommunity
    q = db.query(FraudCommunity).filter(FraudCommunity.run_id == run_id)
    total = q.count()
    return total, q.offset(offset).limit(limit).all()
