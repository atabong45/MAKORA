"""
MODULE : api/schemas/graph.py
DESCRIPTION : Schémas Pydantic v2 — Graphe de fraude (Louvain [Blondel2008]).
"""
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class CommunityMemberResponse(BaseModel):
    id: UUID
    entity_type: str
    entity_id_hash: str
    node_score: float
    is_central: bool
    model_config = {"from_attributes": True}


class FraudCommunityResponse(BaseModel):
    id: UUID
    run_id: UUID
    branch_id: UUID
    community_id_louvain: int
    size: int
    density: float
    modularity: float | None = None
    avg_weight: float | None = None
    is_suspicious: bool
    suspicion_score: float
    reason: str | None = None
    detected_at: datetime
    members: list[CommunityMemberResponse] = []
    model_config = {"from_attributes": True}
