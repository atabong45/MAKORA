"""
MODULE : api/services/claim_document_service.py
DESCRIPTION : Service documents — upload/download/OCR pour sinistres.

Règles métier Sprint 5 :
- Upload, OCR et suppression autorisés sur DRAFT + OPEN
- 1 document maximum par sinistre
- run_ocr() : sémantique "remplace" — l'OCR précédent du document est écrasé
"""
import hashlib
import os
from datetime import date as date_type, datetime as dt_type
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.config import get_settings
from core.db.models.sinistres import Claim, ClaimDocument, OcrExtraction
from core.ingestion.documentary_reader import DocumentaryReader
from core.logging_config import get_logger

logger = get_logger(__name__)
settings = get_settings()

ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png"}
MAX_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Sprint 5 — statuts autorisés pour les opérations documentaires
_UPLOAD_STATUTS = {"DRAFT", "OPEN"}
_DELETE_STATUTS = {"DRAFT", "OPEN"}


# ---------------------------------------------------------------------------
# Helpers internes
# ---------------------------------------------------------------------------

def _get_claim(db: Session, claim_id: str) -> Claim:
    c = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not c:
        raise HTTPException(status_code=404, detail=f"Sinistre '{claim_id}' introuvable")
    return c


def _parse_ocr_date(value) -> date_type | None:
    """Convertit la date renvoyée par le LLM (str/date/None) en date Python."""
    if value is None:
        return None
    if isinstance(value, date_type):
        return value
    try:
        return dt_type.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _clip01(x) -> float:
    """Clip [0,1] défensif pour respecter les CHECK constraints DB."""
    if x is None:
        return 0.0
    return min(1.0, max(0.0, float(x)))


# ---------------------------------------------------------------------------
# Documents — CRUD
# ---------------------------------------------------------------------------

def list_documents(db: Session, claim_id: str) -> list[ClaimDocument]:
    claim = _get_claim(db, claim_id)
    return db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).all()


async def upload_document(
    db: Session,
    claim_id: str,
    file: UploadFile,
    document_type: str | None,
    uploaded_by: UUID,
) -> ClaimDocument:
    claim = _get_claim(db, claim_id)

    # Sprint 5 — statut autorisé
    if claim.statut not in _UPLOAD_STATUTS:
        raise HTTPException(
            status_code=400,
            detail=f"Upload impossible en statut '{claim.statut}'. "
                   f"Autorisé : {sorted(_UPLOAD_STATUTS)}.",
        )

    # Sprint 5 — 1 doc max par claim
    existing_count = (
        db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).count()
    )
    if existing_count >= 1:
        raise HTTPException(
            status_code=400,
            detail="Un document est déjà attaché à ce sinistre. "
                   "Supprimez-le pour en uploader un autre.",
        )

    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(
            status_code=415,
            detail=f"Type MIME non supporté : {file.content_type}",
        )
    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Fichier trop volumineux (max {settings.MAX_UPLOAD_SIZE_MB}MB)",
        )
    sha256 = hashlib.sha256(content).hexdigest()
    rel_path = f"{claim.claim_id}/{sha256[:8]}_{file.filename}"
    abs_path = Path(settings.MAKORA_DOCUMENTS_PATH) / rel_path
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(content)
    doc = ClaimDocument(
        claim_id=claim.id,
        filename=file.filename,
        file_path=str(rel_path),
        mime_type=file.content_type,
        file_size_bytes=len(content),
        hash_sha256=sha256,
        document_type=document_type,
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_document(db: Session, claim_id: str, doc_id: UUID) -> ClaimDocument:
    claim = _get_claim(db, claim_id)
    doc = (
        db.query(ClaimDocument)
        .filter(ClaimDocument.id == doc_id, ClaimDocument.claim_id == claim.id)
        .first()
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Document introuvable")
    return doc


def get_document_bytes(db: Session, claim_id: str, doc_id: UUID) -> tuple[bytes, str, str]:
    doc = get_document(db, claim_id, doc_id)
    abs_path = Path(settings.MAKORA_DOCUMENTS_PATH) / doc.file_path
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Fichier physique introuvable")
    return abs_path.read_bytes(), doc.mime_type, doc.filename


def delete_document(db: Session, claim_id: str, doc_id: UUID) -> None:
    claim = _get_claim(db, claim_id)
    # Sprint 5 — suppression autorisée sur DRAFT + OPEN (avant : DRAFT seul)
    if claim.statut not in _DELETE_STATUTS:
        raise HTTPException(
            status_code=400,
            detail=f"Suppression impossible en statut '{claim.statut}'. "
                   f"Autorisé : {sorted(_DELETE_STATUTS)}.",
        )
    doc = get_document(db, claim_id, doc_id)
    abs_path = Path(settings.MAKORA_DOCUMENTS_PATH) / doc.file_path
    if abs_path.exists():
        abs_path.unlink()
    db.delete(doc)
    db.commit()


# ---------------------------------------------------------------------------
# OCR
# ---------------------------------------------------------------------------

def list_ocr_results(db: Session, claim_id: str) -> list[OcrExtraction]:
    """Retourne tous les OCR du sinistre, le plus récent en premier."""
    claim = _get_claim(db, claim_id)
    docs = db.query(ClaimDocument).filter(ClaimDocument.claim_id == claim.id).all()
    doc_ids = [d.id for d in docs]
    if not doc_ids:
        return []
    return (
        db.query(OcrExtraction)
        .filter(OcrExtraction.document_id.in_(doc_ids))
        .order_by(OcrExtraction.created_at.desc())
        .all()
    )


def run_ocr(db: Session, claim_id: str, doc_id: UUID) -> OcrExtraction:
    """
    Sprint 5 — exécute le pipeline OCR (PaddleOCR + Tesseract + LLM) sur un document.

    Sémantique "remplace" : tout OcrExtraction antérieur pour ce document est
    supprimé avant insertion du nouveau — un seul OCR vivant par document.

    Référence : [Bauder2017] — qualité documentaire comme signal de fraude.
    """
    doc = get_document(db, claim_id, doc_id)
    abs_path = Path(settings.MAKORA_DOCUMENTS_PATH) / doc.file_path
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Fichier physique introuvable")

    # Replace : supprimer toute extraction existante pour ce document
    db.query(OcrExtraction).filter(OcrExtraction.document_id == doc.id).delete(
        synchronize_session=False
    )
    db.flush()

    # Pipeline OCR — non-bloquant : retourne success=False plutôt que de lever
    reader = DocumentaryReader()
    result = reader.process(abs_path)

    # Mapping OCRResult (core) → OcrExtraction (DB)
    # Attention : les noms diffèrent (montant_facture → montant_extrait, etc.)
    extraction = OcrExtraction(
        document_id=doc.id,
        score_confiance_global=_clip01(result.score_confiance_global),
        score_confiance_montant=_clip01(result.score_confiance_montant),
        montant_extrait=result.montant_facture,
        devise_extraite=result.devise,
        date_soin_extraite=_parse_ocr_date(result.date_soin),
        code_acte_extrait=result.code_acte,
        nom_praticien_extrait=result.nom_praticien,
        etablissement_extrait=result.etablissement,
        presence_cachet=bool(result.presence_cachet),
        flag_altere=bool(result.flag_altere),
        logiciel_retouche=result.logiciel_retouche,
        hash_image=result.hash_image or "",
        llm_backend_used=reader.backend.name,
        paddle_text_length=None,
        tesseract_text_length=None,
        success=bool(result.success),
        error_code=result.error,
    )
    db.add(extraction)
    db.commit()
    db.refresh(extraction)

    logger.info(
        "[OCR] claim=%s doc=%s success=%s score=%.2f cachet=%s altere=%s backend=%s",
        claim_id, doc.filename, extraction.success,
        extraction.score_confiance_global,
        extraction.presence_cachet, extraction.flag_altere,
        extraction.llm_backend_used,
    )
    return extraction