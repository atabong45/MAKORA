"""
MODULE : api/services/referentiel_service.py
DESCRIPTION : Service référentiels pseudonymisés — praticiens, garages, prix, assurés.
Respecte la pseudonymisation : jamais d'exposition de données nominatives.
"""
from datetime import date
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.schemas.referentiels import ReferencePriceImport


def list_practitioners(db: Session, pays: str | None, specialite: str | None, agrement: bool | None, ratio_min: float | None, offset: int, limit: int):
    from core.db.models.referentiels import Practitioner
    q = db.query(Practitioner)
    if pays:
        q = q.filter(Practitioner.pays == pays)
    if specialite:
        q = q.filter(Practitioner.specialite.ilike(f"%{specialite}%"))
    if agrement is not None:
        q = q.filter(Practitioner.agrement_cima == agrement)
    if ratio_min:
        q = q.filter(Practitioner.ratio_prix_moyen >= ratio_min)
    total = q.count()
    return total, q.order_by(Practitioner.ratio_prix_moyen.desc()).offset(offset).limit(limit).all()


def get_practitioner(db: Session, practitioner_id: UUID):
    from core.db.models.referentiels import Practitioner
    p = db.query(Practitioner).filter(Practitioner.id == practitioner_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Praticien introuvable")
    return p


def get_practitioner_claims(db: Session, id_hash: str, offset: int, limit: int):
    from core.db.models.sinistres import ClaimLine, Claim
    lines = db.query(ClaimLine).filter(ClaimLine.praticien_id_hash == id_hash).all()
    claim_ids = list({l.claim_id for l in lines})
    total = len(claim_ids)
    claims = db.query(Claim).filter(Claim.id.in_(claim_ids[offset:offset+limit])).all()
    return total, claims


def list_garages(db: Session, ville: str | None, type_garage: str | None, agrement: bool | None, ratio_min: float | None, offset: int, limit: int):
    from core.db.models.referentiels import Garage
    q = db.query(Garage)
    if ville:
        q = q.filter(Garage.ville.ilike(f"%{ville}%"))
    if type_garage:
        q = q.filter(Garage.type_garage == type_garage)
    if agrement is not None:
        q = q.filter(Garage.agrement_cima == agrement)
    total = q.count()
    return total, q.order_by(Garage.ratio_devis_moyen.desc()).offset(offset).limit(limit).all()


def get_garage(db: Session, garage_id: UUID):
    from core.db.models.referentiels import Garage
    g = db.query(Garage).filter(Garage.id == garage_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Garage introuvable")
    return g


def get_reference_prices(db: Session, branch: str, code_acte: str | None):
    from core.db.models.referentiels import ReferencePrice, Branch
    b = db.query(Branch).filter(Branch.code == branch).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche inconnue : {branch}")
    q = db.query(ReferencePrice).filter(
        ReferencePrice.branch_id == b.id,
        (ReferencePrice.valid_to == None) | (ReferencePrice.valid_to >= date.today()),
    )
    if code_acte:
        q = q.filter(ReferencePrice.code_acte == code_acte)
    return q.order_by(ReferencePrice.code_acte).all()


def import_reference_price(db: Session, data: ReferencePriceImport) -> dict:
    from core.db.models.referentiels import ReferencePrice, Branch
    b = db.query(Branch).filter(Branch.code == data.branch_code).first()
    if not b:
        raise HTTPException(status_code=400, detail=f"Branche inconnue : {data.branch_code}")
    price = ReferencePrice(
        branch_id=b.id, code_acte=data.code_acte, libelle=data.libelle,
        nomenclature=data.nomenclature, prix_ref_xaf=data.prix_ref_xaf,
        prix_ref_eur=data.prix_ref_eur, devise_principale=data.devise_principale,
        valid_from=data.valid_from, source_document=data.source_document,
    )
    db.add(price)
    db.commit()
    return {"message": "Prix importé", "code_acte": data.code_acte}


def get_insured(db: Session, id_hash: str):
    from core.db.models.referentiels import Insured
    insured = db.query(Insured).filter(Insured.id_hash == id_hash).first()
    if not insured:
        raise HTTPException(status_code=404, detail="Assuré introuvable")
    return insured


def get_employer(db: Session, employer_id: UUID):
    from core.db.models.referentiels import Employer
    emp = db.query(Employer).filter(Employer.id == employer_id).first()
    if not emp:
        raise HTTPException(status_code=404, detail="Employeur introuvable")
    return emp


def get_employer_insureds(db: Session, employer_id: UUID, offset: int, limit: int):
    from core.db.models.referentiels import InsuredEmployer, Insured
    links = db.query(InsuredEmployer).filter(InsuredEmployer.employer_id == employer_id, InsuredEmployer.is_active == True)
    total = links.count()
    insured_ids = [l.insured_id for l in links.offset(offset).limit(limit).all()]
    return total, db.query(Insured).filter(Insured.id.in_(insured_ids)).all()
