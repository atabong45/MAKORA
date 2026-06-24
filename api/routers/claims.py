"""
MODULE : api/routers/claims.py
DESCRIPTION : Router FastAPI pour le domaine Sinistres.
Cycle de vie DRAFT → SUBMITTED → OPEN → CLOSED.

PATCH B-AI-NEW-01 :
- L'endpoint POST /{claim_id}/submit injecte désormais `BackgroundTasks`
  pour planifier l'exécution du pipeline IA en arrière-plan (BNF-06).
- L'identité du current_user est transmise au service pour audit trail
  (AnalysisRun.triggered_by).
"""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from core.db.models.sinistres import Claim
from api.services import claim_crud_service as claim_svc
from api.services.analyze_service import run_pipeline_for_claim

from api.deps.auth import get_current_active_user
from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.schemas.claims import (
    ClaimCreate, ClaimLineCreate, ClaimLineResponse, ClaimResponse, ClaimUpdate,
    DocumentMeta, ImportReport, OcrResult,
)
from api.schemas.common import MessageResponse, PaginatedResponse
from api.services import claim_crud_service as svc
from api.services import claim_document_service as doc_svc
from api.services import claim_import_service as import_svc
from core.db.models.iam import User

router = APIRouter(prefix="/claims", tags=["Sinistres"])
_access = Depends(require_roles("gestionnaire", "auditeur", "administrateur"))
_write = Depends(require_roles("gestionnaire", "administrateur"))


@router.get("/", response_model=PaginatedResponse[ClaimResponse])
def list_claims(
    branch_code: str | None = Query(None),
    statut: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = _access,
):
    total, items = svc.list_claims(
        db, branch_code, statut, date_from, date_to,
        None, None, (page - 1) * page_size, page_size,
    )
    return PaginatedResponse(total=total, page=page, page_size=page_size, results=items)


@router.post("/", response_model=ClaimResponse, status_code=201)
def create_claim(
    data: ClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = _write,
):
    return svc.create_claim(db, data, current_user.id)


@router.get("/{claim_id}", response_model=ClaimResponse)
def get_claim(claim_id: str, db: Session = Depends(get_db), _: User = _access):
    return svc.get_claim(db, claim_id)


@router.patch("/{claim_id}", response_model=ClaimResponse)
def update_claim(
    claim_id: str,
    data: ClaimUpdate,
    db: Session = Depends(get_db),
    _: User = _write,
):
    return svc.update_claim(db, claim_id, data)


# ───────────────────────────────────────────────────────────────────────────
# POST /{claim_id}/submit — MODIFIÉ pour planifier la pipeline IA en background
# ───────────────────────────────────────────────────────────────────────────

@router.post("/{claim_id}/submit", response_model=ClaimResponse)
def submit_claim(
    claim_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = _write,
):
    """
    Soumet un sinistre au pipeline IA : DRAFT → SUBMITTED.

    Le pipeline (DIF + KernelSHAP + RCA + LLM) s'exécute en arrière-plan
    APRÈS l'envoi de la réponse HTTP, pour respecter la cible BNF-06 (p50 < 2s).

    Une fois le pipeline terminé :
    - succès : statut → OPEN, Analysis créée, accessible via GET /{claim_id}
    - échec : statut reste SUBMITTED (signal d'alerte dans le stepper)

    RÉFÉRENCE : [Xu2023] DIF — pipeline de production MAKORA.
    """
    return svc.submit_claim(
        db,
        claim_id,
        background_tasks=background_tasks,
        triggered_by_id=current_user.id,
    )


# ───────────────────────────────────────────────────────────────────────────
# Lignes de détail — inchangé
# ───────────────────────────────────────────────────────────────────────────

@router.get("/{claim_id}/lines", response_model=list[ClaimLineResponse])
def get_lines(claim_id: str, db: Session = Depends(get_db), _: User = _access):
    from core.db.models.sinistres import ClaimLine
    claim = svc.get_claim(db, claim_id)
    return db.query(ClaimLine).filter(ClaimLine.claim_id == claim.id).all()


@router.post("/{claim_id}/lines", response_model=ClaimLineResponse, status_code=201)
def add_line(
    claim_id: str,
    data: ClaimLineCreate,
    db: Session = Depends(get_db),
    _: User = _write,
):
    return svc.add_line(db, claim_id, data)


@router.patch("/{claim_id}/lines/{line_id}", response_model=ClaimLineResponse)
def update_line(
    claim_id: str,
    line_id: UUID,
    data: ClaimLineCreate,
    db: Session = Depends(get_db),
    _: User = _write,
):
    return svc.update_line(db, claim_id, line_id, data)


@router.delete("/{claim_id}/lines/{line_id}", response_model=MessageResponse)
def delete_line(
    claim_id: str,
    line_id: UUID,
    db: Session = Depends(get_db),
    _: User = _write,
):
    svc.delete_line(db, claim_id, line_id)
    return MessageResponse(message="Ligne supprimée")


# ───────────────────────────────────────────────────────────────────────────
# Documents — inchangé (cf. patch B-DOC-01 déjà appliqué dans claims.py schema)
# ───────────────────────────────────────────────────────────────────────────

@router.get("/{claim_id}/documents", response_model=list[DocumentMeta])
def list_documents(claim_id: str, db: Session = Depends(get_db), _: User = _access):
    return doc_svc.list_documents(db, claim_id)


@router.post("/{claim_id}/documents", response_model=DocumentMeta, status_code=201)
async def upload_document(
    claim_id: str,
    file: UploadFile = File(...),
    document_type: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = _write,
):
    return await doc_svc.upload_document(
        db, claim_id, file, document_type, current_user.id
    )


@router.get("/{claim_id}/documents/{doc_id}", response_model=DocumentMeta)
def get_document(
    claim_id: str,
    doc_id: UUID,
    db: Session = Depends(get_db),
    _: User = _access,
):
    return doc_svc.get_document(db, claim_id, doc_id)


@router.get("/{claim_id}/documents/{doc_id}/download")
def download_document(
    claim_id: str,
    doc_id: UUID,
    db: Session = Depends(get_db),
    _: User = _access,
):
    content, mime_type, filename = doc_svc.get_document_bytes(db, claim_id, doc_id)
    return Response(
        content=content,
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/{claim_id}/documents/{doc_id}", response_model=MessageResponse)
def delete_document(
    claim_id: str,
    doc_id: UUID,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("administrateur")),
):
    doc_svc.delete_document(db, claim_id, doc_id)
    return MessageResponse(message="Document supprimé")


# ───────────────────────────────────────────────────────────────────────────
# OCR — inchangé
# ───────────────────────────────────────────────────────────────────────────

@router.post("/{claim_id}/ocr/run", response_model=OcrResult)
def run_ocr(
    claim_id: str,
    doc_id: UUID,
    db: Session = Depends(get_db),
    _: User = _write,
):
    return doc_svc.run_ocr(db, claim_id, doc_id)


@router.get("/{claim_id}/ocr", response_model=list[OcrResult])
def get_ocr_results(claim_id: str, db: Session = Depends(get_db), _: User = _access):
    return doc_svc.list_ocr_results(db, claim_id)


# ───────────────────────────────────────────────────────────────────────────
# Historique des analyses pour ce sinistre
# ───────────────────────────────────────────────────────────────────────────

@router.get("/{claim_id}/analyses")
def get_claim_analyses(
    claim_id: str,
    db: Session = Depends(get_db),
    _: User = _access,
):
# [Lundberg2017] — top_features SHAP chargées en une seule requête
    # via joinedload pour éviter le N+1 sur shap_contributions.
    # Structure de retour alignée sur AnalysisResult (analysis.types.ts)
    # afin que ClaimAnalysisTab lise analysis.rca.category et
    # analysis.rca.top_features sans adaptation côté frontend.
    from core.db.models.pipeline import Analysis, ShapContribution
    from sqlalchemy import desc
    from sqlalchemy.orm import joinedload

    claim = svc.get_claim(db, claim_id)
    analyses = (
        db.query(Analysis)
        .options(joinedload(Analysis.shap_contributions))
        .filter(Analysis.claim_id == claim.id)
        .order_by(desc(Analysis.created_at))
        .all()
    )

    def _serialize(a: Analysis) -> dict:
        # Construction du bloc rca imbriqué — None si aucune règle n'a matché
        rca_block = None
        if a.rca_category:
            top_features = sorted(
                a.shap_contributions, key=lambda s: s.rank
            )[:3]
            rca_block = {
                "category":      a.rca_category,
                "subcategory":   a.rca_subcategory,
                "confidence":    a.rca_confidence,
                "rule_triggered": a.rca_rule_id,
                "top_features": [
                    {
                        "name":       s.feature_name,
                        "shap_value": s.shap_value,
                        "direction":  s.direction,
                        "rank":       s.rank,
                    }
                    for s in top_features
                ],
                "explanation_fr": a.explanation_fr,
            }

        return {
            "analysis_id":       str(a.id),
            "id":                str(a.id),   # compat ClaimHistoryTimeline
            "claim_id":          claim.claim_id,
            "anomaly_score":     a.anomaly_score,
            "is_anomaly":        a.is_anomaly,
            "detector_name":     a.detector_name,
            "decision_status":   a.decision_status,
            "processing_time_ms": a.processing_time_ms,
            "created_at":        a.created_at.isoformat() if a.created_at else None,
            "rca":               rca_block,
        }

    return [_serialize(a) for a in analyses]



@router.post("/{claim_id}/reanalyze", response_model=MessageResponse)
def reanalyze_claim(
    claim_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = _write,
):
    """Re-déclenche le pipeline DIF sur un sinistre OPEN (après re-run OCR)."""
    from core.db.models.referentiels import Branch as BranchModel

    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not claim:
        raise HTTPException(status_code=404, detail=f"Sinistre '{claim_id}' introuvable")
    if claim.statut != "OPEN":
        raise HTTPException(
            status_code=400,
            detail=f"Re-analyse disponible uniquement sur un sinistre OPEN "
                   f"(actuel : {claim.statut}).",
        )
    # Résoudre branch + dossier AVANT le commit (évite claim bloqué si erreur)
    branch = db.query(BranchModel).filter(BranchModel.id == claim.branch_id).first()
    if not branch:
        raise HTTPException(status_code=500, detail="Branche introuvable.")
    branch_code = branch.code
    dossier = claim_svc.claim_to_dossier_dict(db, claim)

    claim.statut = "SUBMITTED"
    db.commit()

    background_tasks.add_task(
        run_pipeline_for_claim,
        claim.id,
        branch_code,
        dossier,
        current_user.id,
    )
    return MessageResponse(message="Re-analyse lancée en tâche de fond.")


# ───────────────────────────────────────────────────────────────────────────
# Sprint 8 — Import batch
# ───────────────────────────────────────────────────────────────────────────

@router.post("/import", response_model=ImportReport)
async def import_claims_batch(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Fichier CSV"),
    branch_code: str = Form(..., description="sante | auto | vie | agricole"),
    auto_analyze: bool = Form(
        False,
        description="Si True, les sinistres créés sont soumis et analysés en arrière-plan.",
    ),
    db: Session = Depends(get_db),
    current_user: User = _write,
):
    """
    Importe un lot de sinistres depuis un fichier CSV (mono-branche, 1 ligne = 1 sinistre).
    RBAC identique à POST /claims/ (gestionnaire + administrateur).
    """
    rows = await import_svc.parse_file(file)
    return import_svc.import_claims(
        db=db, rows=rows, branch_code=branch_code,
        created_by=current_user.id, auto_analyze=auto_analyze,
        background_tasks=background_tasks,
    )