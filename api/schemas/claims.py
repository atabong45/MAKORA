"""
MODULE : api/schemas/claims.py
DESCRIPTION : Schémas Pydantic v2 pour le domaine Sinistres & Documents.
Cycle de vie : DRAFT → SUBMITTED → OPEN → CLOSED

CORRECTIONS APPLIQUÉES :

DT-CLAIM-002 (existant, conservé) :
  ClaimResponse.branch_code est résolu depuis la relation ORM `branch.code`
  car le modèle Claim stocke branch_id (UUID), pas un attribut branch_code
  direct. Sans ce validator, Pydantic ne sait pas mapper branch_id → code.

PATCH G4 BUG-WIZARD-01 (existant, conservé) :
  Les champs `latest_anomaly_score` et `latest_is_anomaly` ne sont pas des
  colonnes du modèle ORM Claim — ils sont injectés manuellement par le
  service `list_claims` après une jointure avec la table Analysis.

  Sur un sinistre fraîchement créé (POST /claims/), `db.refresh(claim)` ne
  fait PAS cette injection : ces attributs n'existent simplement pas sur
  l'objet ORM. L'accès direct `data.latest_anomaly_score` levait alors un
  AttributeError qui se transformait en 500 Internal Server Error côté
  client, propagé en "Network Error" côté navigateur à cause de la
  désynchronisation du middleware CORS sur les erreurs non capturées.

  Le bug est latent pour tous les endpoints retournant ClaimResponse sans
  passer par list_claims : POST /claims/, GET /claims/{id}, PATCH /claims/{id},
  POST /claims/{id}/submit. Le fix les corrige tous en une fois.

  Solution : utiliser `getattr(data, "attr", None)` au lieu de l'accès direct.
  Si l'attribut n'a pas été injecté (cas POST/GET détail/PATCH/submit), la
  valeur retournée est None — conforme au typage `float | None` /
  `bool | None` du schéma.

PATCH PHASE 4 BUG B-DOC-01 (nouveau, ce fichier) :
  DocumentMeta.uploaded_at ne matchait aucun attribut du modèle ORM
  ClaimDocument, qui hérite de CreatedAtMixin et n'expose donc que
  `created_at`. Sans alias explicite, FastAPI levait une
  ResponseValidationError 500 silencieuse lors de la sérialisation,
  avalée par le middleware CORS — symptôme observé en frontend :
  "Network Error" sur l'upload PDF (B-DOC-01) et toasts rouges
  "Connexion impossible" sur la fiche détail (B-DET-01, B-DET-05).

  Log uvicorn caractéristique (11 juin 2026) :
      ResponseValidationError: 1 validation errors:
      {'type': 'missing', 'loc': ('response', 0, 'uploaded_at'),
       'msg': 'Field required',
       'input': <core.db.models.sinistres.ClaimDocument object>}

  Solution : Pydantic v2 AliasChoices accepte les deux noms en entrée
  (validation_alias) et expose toujours `uploaded_at` en sortie API
  (serialization_alias). Le contrat API et les types TypeScript du
  frontend (DocumentMeta.uploaded_at) restent inchangés — zéro
  migration DB, zéro changement frontend.

RÉFÉRENCES ACADÉMIQUES :
  [Sculley2015] Sculley et al. (2015). Hidden technical debt in machine
  learning systems. NeurIPS 2015. § "Pipeline Jungles".
    → Un schéma de réponse partagé entre N cas d'usage avec des hypothèses
      contextuelles différentes (ici : claim avec ou sans analyse) est une
      source classique de dette technique. La séparation propre serait :
        - ClaimResponse (POST/GET détail/PATCH/submit) sans latest_*
        - ClaimListItem(ClaimResponse) avec latest_* (GET liste)
      Cette refonte est documentée comme dette à traiter post-Phase 5, mais
      le `getattr` défensif suffit pour débloquer la Phase 4 sans risque
      de régression sur les endpoints qui fonctionnent.
    → Le mismatch DocumentMeta/ClaimDocument illustre le même problème à
      la frontière API ↔ ORM. L'AliasChoices résout l'instance sans
      introduire de dette supplémentaire.
"""
from datetime import date, datetime
from uuid import UUID
from typing import Any, Literal
from pydantic import (
    AliasChoices,
    BaseModel,
    Field,
    field_validator,
    model_validator,
)


class ClaimLineCreate(BaseModel):
    code_acte: str | None = None
    libelle: str | None = None
    montant_ligne: float | None = None
    quantite: int = 1
    praticien_id_hash: str | None = None
    garage_id_hash: str | None = None


class ClaimLineResponse(ClaimLineCreate):
    id: UUID
    claim_id: UUID
    prix_ref: float | None = None
    ratio_prix: float | None = None
    created_at: datetime
    model_config = {"from_attributes": True}


class ClaimCreate(BaseModel):
    claim_id: str
    branch_code: str
    source_flux: Literal["structured", "documentary", "batch"] = "structured"
    montant_facture: float | None = None
    devise: str = "XAF"
    date_soin: date | None = None
    date_declaration: date | None = None

    @field_validator("branch_code")
    @classmethod
    def validate_branch(cls, v: str) -> str:
        if v not in ("sante", "auto", "vie", "agricole"):
            raise ValueError(f"Branche inconnue : {v}")
        return v


class ClaimUpdate(BaseModel):
    montant_facture: float | None = None
    devise: str | None = None
    date_soin: date | None = None
    date_declaration: date | None = None


class ClaimResponse(BaseModel):
    id: UUID
    claim_id: str
    branch_code: str | None = None
    source_flux: str
    montant_facture: float | None = None
    devise: str | None = None
    montant_xaf: float | None = None
    date_soin: date | None = None
    date_declaration: date | None = None
    statut: str
    created_at: datetime
    updated_at: datetime
    # Champs dérivés issus de la dernière Analysis liée — peuvent être None
    # si le claim n'a jamais été analysé OU si l'endpoint ne fait pas la
    # jointure (POST, GET détail, PATCH, submit). Voir docstring du fichier.
    latest_anomaly_score: float | None = None
    latest_is_anomaly: bool | None = None
    latest_analysis_id: str | None = None   # ← AJOUTER
    assure_id_hash: str | None = None
    region: str | None = None
    model_config = {"from_attributes": True}

    @model_validator(mode="before")
    @classmethod
    def resolve_branch_code(cls, data: Any) -> Any:
        """
        Résout branch_code depuis la relation ORM `branch.code` et protège
        l'accès aux champs dérivés `latest_*` qui peuvent ne pas avoir été
        injectés sur l'objet ORM (cas POST/GET détail/PATCH/submit).

        Deux entrées possibles :
          - Objet ORM SQLAlchemy `Claim` avec relation .branch chargée
            → on construit un dict pour Pydantic
          - Dict (appel test direct ou objet déjà mappé)
            → on retourne tel quel
        """
        # Cas dict : déjà au bon format, passer à Pydantic sans transformer
        if isinstance(data, dict):
            return data

        # Cas objet ORM : construire le dict avec accès défensif
        if hasattr(data, "branch") and data.branch is not None:
            return {
                "id":              data.id,
                "claim_id":        data.claim_id,
                "branch_code":     data.branch.code,
                "source_flux":     data.source_flux,
                "montant_facture": data.montant_facture,
                "devise":          data.devise,
                "montant_xaf":     data.montant_xaf,
                "date_soin":       data.date_soin,
                "date_declaration": data.date_declaration,
                "statut":          data.statut,
                "created_at":      data.created_at,
                "updated_at":      data.updated_at,
                # PATCH G4 BUG-WIZARD-01 : getattr défensif.
                # Sur un claim fraîchement créé (POST), ces attributs ne
                # sont pas injectés par le service — getattr retourne None
                # au lieu de lever AttributeError.
                "latest_anomaly_score": getattr(data, "latest_anomaly_score", None),
                "latest_is_anomaly":    getattr(data, "latest_is_anomaly", None),
                "latest_analysis_id":   getattr(data, "latest_analysis_id", None),
                "assure_id_hash":       getattr(data, "assure_id_hash", None),
                "region":               getattr(data, "region", None),
            }

        # Objet ORM sans relation branch chargée (ne devrait pas arriver en
        # pratique car les services font db.refresh, mais on protège quand
        # même pour ne pas masquer un futur bug par un 500).
        return data


class DocumentMeta(BaseModel):
    """
    Métadonnées d'un document attaché à un sinistre.

    PATCH PHASE 4 B-DOC-01 :
    - Le champ API s'appelle `uploaded_at` (vocabulaire métier explicite),
      mais le modèle ORM `ClaimDocument` hérite de `CreatedAtMixin` qui
      expose `created_at`. AliasChoices accepte les deux noms en entrée
      et le serialization_alias garantit que la sortie JSON expose
      toujours `uploaded_at` — préservation totale du contrat API.
    - `populate_by_name=True` permet la construction directe avec
      `uploaded_at=...` dans les tests unitaires (rétrocompatibilité).
    """
    id: UUID
    claim_id: UUID
    filename: str
    mime_type: str
    file_size_bytes: int
    document_type: str | None = None
    hash_sha256: str
    uploaded_at: datetime = Field(
        ...,
        validation_alias=AliasChoices("uploaded_at", "created_at"),
        serialization_alias="uploaded_at",
        description="Date d'upload — mappée depuis ClaimDocument.created_at",
    )
    model_config = {
        "from_attributes": True,
        "populate_by_name": True,
    }


class OcrResult(BaseModel):
    id: UUID
    document_id: UUID
    score_confiance_global: float
    score_confiance_montant: float
    montant_extrait: float | None = None
    devise_extraite: str | None = None
    date_soin_extraite: date | None = None
    code_acte_extrait: str | None = None
    presence_cachet: bool
    flag_altere: bool
    logiciel_retouche: str | None = None
    success: bool
    error_code: str | None = None
    llm_backend_used: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ───────────────────────────────────────────────────────────────────────────
# Sprint 8 — Import batch
# ───────────────────────────────────────────────────────────────────────────


class ImportRowError(BaseModel):
    """Erreur sur une ligne du CSV. row_number 1-indexé (header = ligne 1)."""
    row_number: int
    field: str | None = None
    message: str


class ImportedClaimSummary(BaseModel):
    """Récapitulatif d'un sinistre créé par l'import."""
    claim_id: str
    uuid: str
    statut: Literal["DRAFT", "SUBMITTED"]


class ImportReport(BaseModel):
    """
    Rapport retourné par POST /claims/import.

    auto_analyze=True → les sinistres créés sont passés SUBMITTED et leur
    pipeline IA tourne en arrière-plan (séquentiel via BackgroundTask).
    """
    total_rows: int
    created_count: int
    duplicates_count: int
    errors_count: int
    auto_analyze: bool
    created: list[ImportedClaimSummary]
    duplicates: list[str]
    errors: list[ImportRowError]