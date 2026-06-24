"""
MODULE : api/services/retraining_service.py
DESCRIPTION : Service réentraînement — state machine PENDING→APPROVED→DONE.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.schemas.governance import RetrainingCreate

VALID_TRANSITIONS = {"PENDING": ["APPROVED","REJECTED"], "APPROVED": ["IN_PROGRESS","REJECTED"], "IN_PROGRESS": ["DONE"]}


def create_request(db: Session, data: RetrainingCreate, requested_by: UUID):
    from core.db.models.monitoring import RetrainingRequest
    from core.db.models.referentiels import Branch
    b = db.query(Branch).filter(Branch.code == data.branch_code).first()
    if not b:
        raise HTTPException(status_code=400, detail=f"Branche inconnue : {data.branch_code}")
    req = RetrainingRequest(branch_id=b.id, drift_report_id=data.drift_report_id, reason=data.reason, status="PENDING", requested_by=requested_by)
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


def list_requests(db: Session, branch: str | None, status: str | None, offset: int, limit: int):
    from core.db.models.monitoring import RetrainingRequest
    q = db.query(RetrainingRequest)
    if status:
        q = q.filter(RetrainingRequest.status == status)
    total = q.count()
    return total, q.order_by(RetrainingRequest.created_at.desc()).offset(offset).limit(limit).all()


def get_request(db: Session, req_id: UUID):
    from core.db.models.monitoring import RetrainingRequest
    req = db.query(RetrainingRequest).filter(RetrainingRequest.id == req_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    return req


def approve_request(db: Session, req_id: UUID, approved_by: UUID):
    req = get_request(db, req_id)
    if req.status != "PENDING":
        raise HTTPException(status_code=400, detail=f"Statut actuel '{req.status}' — seul PENDING peut être approuvé")
    req.status = "APPROVED"
    req.approved_by = approved_by
    req.approved_at = datetime.now(tz=timezone.utc)
    db.commit()
    db.refresh(req)
    return req


def reject_request(db: Session, req_id: UUID, reason: str, rejected_by: UUID):
    req = get_request(db, req_id)
    if req.status not in ("PENDING", "APPROVED"):
        raise HTTPException(status_code=400, detail=f"Impossible de rejeter depuis le statut '{req.status}'")
    req.status = "REJECTED"
    req.approved_by = rejected_by
    req.approved_at = datetime.now(tz=timezone.utc)
    db.commit()
    db.refresh(req)
    return req


def complete_request(db: Session, req_id: UUID, new_model_version_id: UUID):
    req = get_request(db, req_id)
    if req.status not in ("APPROVED", "IN_PROGRESS"):
        raise HTTPException(status_code=400, detail="Seul APPROVED/IN_PROGRESS peut être complété")
    req.status = "DONE"
    req.new_model_version_id = new_model_version_id
    req.completed_at = datetime.now(tz=timezone.utc)
    db.commit()
    db.refresh(req)
    return req
