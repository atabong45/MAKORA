"""
MODULE : api/routers/analyze.py
DESCRIPTION : Router FastAPI — Pipeline d'analyse MAKORA (4 endpoints).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.analyze import AnalyzeBatchResponse, AnalyzeRequest, RunStatusResponse
from api.schemas.common import PaginatedResponse
from api.services import analyze_service as svc
from core.db.models.iam import User

router = APIRouter(prefix="/analyze", tags=["Analyse ML"])
_access = Depends(require_roles("gestionnaire", "auditeur", "administrateur"))


@router.post("/", response_model=AnalyzeBatchResponse)
def analyze_batch(data: AnalyzeRequest, db: Session = Depends(get_db), current_user: User = _access):
    return svc.run_analysis(db, data.branch, data.source, data.dossiers, current_user.id)


@router.post("/upload", response_model=AnalyzeBatchResponse)
async def analyze_upload(
    branch: str = Query(...), source_name: str = Query("upload"),
    file: UploadFile = File(...),
    db: Session = Depends(get_db), current_user: User = _access,
):
    import json, csv, io
    content = await file.read()
    if file.content_type == "application/json":
        dossiers = json.loads(content)
        if not isinstance(dossiers, list):
            dossiers = [dossiers]
    elif file.content_type == "text/csv":
        reader = csv.DictReader(io.StringIO(content.decode("utf-8-sig")))
        dossiers = [row for row in reader]
    else:
        from fastapi import HTTPException
        raise HTTPException(status_code=415, detail="Format accepté : JSON ou CSV")
    return svc.run_analysis(db, branch, source_name, dossiers, current_user.id)


@router.get("/runs/{run_id}", response_model=RunStatusResponse)
def get_run(run_id: UUID, db: Session = Depends(get_db), _: User = _access):
    return svc.get_run(db, run_id)


@router.get("/runs", response_model=PaginatedResponse[RunStatusResponse])
def list_runs(
    branch: str | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _access,
):
    total, items = svc.list_runs(db, branch, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)
