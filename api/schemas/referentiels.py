"""
MODULE : api/schemas/referentiels.py
DESCRIPTION : Schémas Pydantic v2 pour les référentiels métier pseudonymisés.
"""
from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel


class PractitionerResponse(BaseModel):
    id: UUID
    id_hash: str
    specialite: str | None = None
    region: str | None = None
    pays: str
    agrement_cima: bool | None = None
    ratio_prix_moyen: float | None = None
    nb_sinistres_total: int
    model_config = {"from_attributes": True}


class GarageResponse(BaseModel):
    id: UUID
    id_hash: str
    nom: str | None = None
    type_garage: str | None = None
    ville: str | None = None
    pays: str
    agrement_cima: bool | None = None
    ratio_devis_moyen: float | None = None
    nb_sinistres_total: int
    model_config = {"from_attributes": True}


class ReferencePriceResponse(BaseModel):
    id: UUID
    branch_id: UUID
    code_acte: str
    libelle: str | None = None
    nomenclature: str
    prix_ref_xaf: float | None = None
    prix_ref_eur: float | None = None
    devise_principale: str
    valid_from: date
    valid_to: date | None = None
    source_document: str | None = None
    model_config = {"from_attributes": True}


class ReferencePriceImport(BaseModel):
    branch_code: str
    code_acte: str
    libelle: str | None = None
    nomenclature: str
    prix_ref_xaf: float | None = None
    prix_ref_eur: float | None = None
    devise_principale: str = "XAF"
    valid_from: date
    source_document: str | None = None


class InsuredSummary(BaseModel):
    id: UUID
    id_hash: str
    region: str | None = None
    pays: str
    age: int | None = None
    sexe: str | None = None
    model_config = {"from_attributes": True}


class EmployerResponse(BaseModel):
    id: UUID
    id_hash: str
    secteur: str | None = None
    region: str | None = None
    nb_assures: int
    model_config = {"from_attributes": True}
