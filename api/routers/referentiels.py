"""
MODULE : api/routers/referentiels.py
DESCRIPTION : Router FastAPI — Référentiels pseudonymisés (13 endpoints).
"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.common import MessageResponse, PaginatedResponse
from api.schemas.referentiels import (
    EmployerResponse, GarageResponse, InsuredSummary,
    PractitionerResponse, ReferencePriceImport, ReferencePriceResponse,
)
from api.services import referentiel_service as svc
from core.db.models.iam import User

router = APIRouter(prefix="/referentiels", tags=["Référentiels"])
_read = Depends(require_roles("auditeur", "administrateur"))
_gestionnaire_plus = Depends(require_roles("gestionnaire", "auditeur", "administrateur", "expert_metier"))
_admin = Depends(require_roles("administrateur", "expert_metier"))


@router.get("/practitioners", response_model=PaginatedResponse[PractitionerResponse])
def list_practitioners(
    pays: str | None = Query(None), specialite: str | None = Query(None),
    agrement_cima: bool | None = Query(None), ratio_min: float | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _read,
):
    total, items = svc.list_practitioners(db, pays, specialite, agrement_cima, ratio_min, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)


@router.get("/practitioners/{practitioner_id}", response_model=PractitionerResponse)
def get_practitioner(practitioner_id: UUID, db: Session = Depends(get_db), _: User = _read):
    return svc.get_practitioner(db, practitioner_id)


@router.get("/practitioners/{id_hash}/claims", response_model=PaginatedResponse[dict])
def get_practitioner_claims(
    id_hash: str, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _read,
):
    total, items = svc.get_practitioner_claims(db, id_hash, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=[{"id": str(c.id), "claim_id": c.claim_id, "statut": c.statut} for c in items])


@router.get("/garages", response_model=PaginatedResponse[GarageResponse])
def list_garages(
    ville: str | None = Query(None), type_garage: str | None = Query(None),
    agrement_cima: bool | None = Query(None), ratio_min: float | None = Query(None),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db), _: User = _read,
):
    total, items = svc.list_garages(db, ville, type_garage, agrement_cima, ratio_min, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)


@router.get("/garages/{garage_id}", response_model=GarageResponse)
def get_garage(garage_id: UUID, db: Session = Depends(get_db), _: User = _read):
    return svc.get_garage(db, garage_id)


@router.get("/garages/{id_hash}/claims", response_model=PaginatedResponse[dict])
def get_garage_claims(id_hash: str, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), _: User = _read):
    return PaginatedResponse(total=0, page=page, page_size=page_size, results=[])


@router.get("/prices/{branch}", response_model=list[ReferencePriceResponse])
def get_prices(branch: str, code_acte: str | None = Query(None), db: Session = Depends(get_db), _: User = _gestionnaire_plus):
    return svc.get_reference_prices(db, branch, code_acte)


@router.get("/prices/{branch}/{code_acte}", response_model=list[ReferencePriceResponse])
def get_price_for_act(branch: str, code_acte: str, db: Session = Depends(get_db), _: User = _gestionnaire_plus):
    return svc.get_reference_prices(db, branch, code_acte)


@router.post("/prices", response_model=MessageResponse, status_code=201)
def import_price(data: ReferencePriceImport, db: Session = Depends(get_db), _: User = _admin):
    result = svc.import_reference_price(db, data)
    return MessageResponse(message=result["message"])


@router.get("/insureds/{id_hash}", response_model=InsuredSummary)
def get_insured(id_hash: str, db: Session = Depends(get_db), _: User = _read):
    return svc.get_insured(db, id_hash)


@router.get("/insureds/{id_hash}/claims", response_model=PaginatedResponse[dict])
def get_insured_claims(id_hash: str, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), _: User = _read):
    return PaginatedResponse(total=0, page=page, page_size=page_size, results=[])


@router.get("/employers/{employer_id}", response_model=EmployerResponse)
def get_employer(employer_id: UUID, db: Session = Depends(get_db), _: User = _read):
    return svc.get_employer(db, employer_id)


@router.get("/employers/{employer_id}/insureds", response_model=PaginatedResponse[InsuredSummary])
def get_employer_insureds(employer_id: UUID, page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=200), db: Session = Depends(get_db), _: User = _read):
    total, items = svc.get_employer_insureds(db, employer_id, (page-1)*page_size, page_size)
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)
