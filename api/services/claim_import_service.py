"""
MODULE : api/services/claim_import_service.py
DESCRIPTION : Import batch de sinistres depuis CSV. Orchestrateur réutilisant
              create_claim + add_line, avec auto-analyse optionnelle séquentielle.

RÉFÉRENCE : [Sculley2015] Hidden technical debt in ML systems — l'import batch
réduit la dette de pipeline jungle liée à la saisie manuelle.

DÉCISIONS (Sprint 8) :
- D1 Option A : 1 ligne CSV = 1 sinistre + 1 ligne prestation.
- D2 : import mono-branche (branch_code en form-data, pas dans le CSV).
- D3 : CSV = champs métier uniquement. Les 17 features DIF sont dérivées
       au Submit comme pour les sinistres manuels (cohérence pipeline).
- D5 : commit partiel — lignes valides créées, invalides reportées.
- D6 : sinistres DRAFT par défaut ; auto_analyze=True déclenche pipeline IA.
- D8 : déduplication par claim_id métier.

Auto-analyse : N exécutions séquentielles encapsulées dans UNE BackgroundTask
(évite la surcharge CPU d'un fan-out parallèle).
"""
import csv
import io
import logging
from datetime import date, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, HTTPException, UploadFile
from sqlalchemy.orm import Session

from api.schemas.claims import (
    ClaimCreate, ClaimLineCreate, ImportReport, ImportRowError,
    ImportedClaimSummary,
)
from api.services import claim_crud_service as claim_svc
from core.db.models.sinistres import Claim

logger = logging.getLogger(__name__)

MAX_ROWS_PER_IMPORT = 500
ALLOWED_MIME = {
    "text/csv",
    "application/vnd.ms-excel",
    "application/octet-stream",
}


# ───────────────────────────────────────────────────────────────────────────
# 1. Parsing
# ───────────────────────────────────────────────────────────────────────────

def _detect_delimiter(sample: str) -> str:
    return ";" if sample.count(";") > sample.count(",") else ","


def _decode_content(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("latin-1", errors="replace")


async def parse_file(file: UploadFile) -> list[dict[str, Any]]:
    """Lit le CSV. Lève HTTPException si invalide."""
    if file.content_type and file.content_type not in ALLOWED_MIME:
        if not file.filename or not file.filename.lower().endswith(".csv"):
            raise HTTPException(
                status_code=415,
                detail=f"Type MIME non supporté : {file.content_type}. CSV attendu.",
            )

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide.")

    text = _decode_content(content)
    delimiter = _detect_delimiter(text[:2048])

    try:
        reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
        rows = list(reader)
    except csv.Error as e:
        raise HTTPException(status_code=422, detail=f"CSV illisible : {e}")

    if not rows:
        raise HTTPException(status_code=400, detail="Aucune ligne détectée.")

    if len(rows) > MAX_ROWS_PER_IMPORT:
        raise HTTPException(
            status_code=400,
            detail=f"Trop de lignes ({len(rows)}). Max : {MAX_ROWS_PER_IMPORT}.",
        )

    return rows


# ───────────────────────────────────────────────────────────────────────────
# 2. Validation ligne
# ───────────────────────────────────────────────────────────────────────────

def _parse_float(val: Any) -> float | None:
    if val is None or val == "":
        return None
    try:
        return float(str(val).strip().replace(",", "."))
    except (ValueError, TypeError):
        return None


def _parse_int(val: Any, default: int = 1) -> int:
    if val is None or val == "":
        return default
    try:
        return int(float(str(val).strip().replace(",", ".")))
    except (ValueError, TypeError):
        return default


def _parse_date(val: Any) -> date | None:
    if val is None or val == "":
        return None
    s = str(val).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _validate_row(
    row: dict[str, Any], branch_code: str, row_index: int
) -> tuple[ClaimCreate, ClaimLineCreate] | ImportRowError:
    """row_index 1-indexé (header=1, 1ère donnée=2)."""
    montant = _parse_float(row.get("montant_facture"))
    if montant is None or montant <= 0:
        return ImportRowError(
            row_number=row_index, field="montant_facture",
            message="Montant manquant ou invalide (doit être > 0).",
        )

    date_soin = _parse_date(row.get("date_soin"))
    if date_soin is None:
        return ImportRowError(
            row_number=row_index, field="date_soin",
            message="Date de soin manquante ou invalide (YYYY-MM-DD ou DD/MM/YYYY).",
        )

    claim_id = (row.get("claim_id") or "").strip()
    if not claim_id:
        claim_id = f"SIN-{branch_code.upper()}-{uuid4().hex[:8].upper()}"

    devise = (row.get("devise") or "XAF").strip().upper()
    source_flux_raw = (row.get("source_flux") or "batch").strip().lower()
    if source_flux_raw not in ("structured", "documentary", "batch"):
        source_flux_raw = "batch"

    date_declaration = _parse_date(row.get("date_declaration"))

    try:
        claim_payload = ClaimCreate(
            claim_id=claim_id, branch_code=branch_code,
            source_flux=source_flux_raw,  # type: ignore[arg-type]
            montant_facture=montant, devise=devise,
            date_soin=date_soin, date_declaration=date_declaration,
        )
    except Exception as e:
        return ImportRowError(
            row_number=row_index, field=None, message=f"Validation : {e}"
        )

    line_payload = ClaimLineCreate(
        code_acte=(row.get("code_acte") or None) or None,
        libelle=(row.get("libelle") or None) or None,
        montant_ligne=_parse_float(row.get("montant_ligne")) or montant,
        quantite=_parse_int(row.get("quantite"), default=1),
        praticien_id_hash=(row.get("praticien_id_hash") or None) or None,
        garage_id_hash=(row.get("garage_id_hash") or None) or None,
    )

    return claim_payload, line_payload


# ───────────────────────────────────────────────────────────────────────────
# 3. Pipeline IA séquentiel
# ───────────────────────────────────────────────────────────────────────────

def _process_batch_pipeline(pipeline_payload: list[dict[str, Any]]) -> None:
    """run_pipeline_for_claim ne lève jamais d'exception (Décision 1 B-AI-NEW-01).
    Le try/except ici est un filet de sécurité."""
    from api.services.analyze_service import run_pipeline_for_claim

    logger.info(
        "Batch pipeline : %d sinistres", len(pipeline_payload),
    )
    for idx, item in enumerate(pipeline_payload, start=1):
        try:
            run_pipeline_for_claim(
                claim_uuid=item["claim_uuid"],
                branch_code=item["branch_code"],
                dossier=item["dossier"],
                triggered_by_id=item.get("triggered_by_id"),
            )
        except Exception as e:
            logger.exception(
                "Batch pipeline : erreur sur %s (%d/%d) : %s",
                item.get("claim_id"), idx, len(pipeline_payload), e,
            )
    logger.info("Batch pipeline : terminé.")


# ───────────────────────────────────────────────────────────────────────────
# 4. Import principal
# ───────────────────────────────────────────────────────────────────────────

def import_claims(
    db: Session,
    rows: list[dict[str, Any]],
    branch_code: str,
    created_by: UUID,
    auto_analyze: bool,
    background_tasks: BackgroundTasks | None = None,
) -> ImportReport:
    """Boucle principale : validation + création + auto-analyse optionnelle."""
    if branch_code not in ("sante", "auto", "vie", "agricole"):
        raise HTTPException(
            status_code=400, detail=f"Branche inconnue : {branch_code}"
        )

    created: list[ImportedClaimSummary] = []
    errors: list[ImportRowError] = []
    duplicates: list[str] = []
    pipeline_payload: list[dict[str, Any]] = []

    for idx, row in enumerate(rows, start=2):
        result = _validate_row(row, branch_code, idx)
        if isinstance(result, ImportRowError):
            errors.append(result)
            continue

        claim_payload, line_payload = result

        existing = (
            db.query(Claim)
            .filter(Claim.claim_id == claim_payload.claim_id)
            .first()
        )
        if existing:
            duplicates.append(claim_payload.claim_id)
            continue

        try:
            claim = claim_svc.create_claim(db, claim_payload, created_by)
            if line_payload.code_acte or line_payload.montant_ligne:
                claim_svc.add_line(db, claim.claim_id, line_payload)
        except HTTPException as e:
            errors.append(ImportRowError(
                row_number=idx, field=None,
                message=f"Erreur création : {e.detail}",
            ))
            continue
        except Exception as e:
            logger.exception("Import ligne %d : erreur inattendue", idx)
            errors.append(ImportRowError(
                row_number=idx, field=None,
                message=f"Erreur inattendue : {e}",
            ))
            continue

        final_status = "DRAFT"
        if auto_analyze:
            try:
                dossier = claim_svc.claim_to_dossier_dict(db, claim)
                claim.statut = "SUBMITTED"
                db.commit()
                db.refresh(claim)
                final_status = "SUBMITTED"
                pipeline_payload.append({
                    "claim_id": claim.claim_id,
                    "claim_uuid": claim.id,
                    "branch_code": branch_code,
                    "dossier": dossier,
                    "triggered_by_id": created_by,
                })
            except Exception as e:
                logger.exception(
                    "Auto-analyze : impossible de soumettre %s",
                    claim.claim_id,
                )
                errors.append(ImportRowError(
                    row_number=idx, field=None,
                    message=f"Création OK mais auto-soumission impossible : {e}",
                ))

        created.append(ImportedClaimSummary(
            claim_id=claim.claim_id,
            uuid=str(claim.id),
            statut=final_status,
        ))

    if auto_analyze and background_tasks is not None and pipeline_payload:
        background_tasks.add_task(_process_batch_pipeline, pipeline_payload)
        logger.info(
            "Import batch : %d sinistres planifiés pour analyse",
            len(pipeline_payload),
        )

    return ImportReport(
        total_rows=len(rows),
        created_count=len(created),
        duplicates_count=len(duplicates),
        errors_count=len(errors),
        auto_analyze=auto_analyze,
        created=created,
        duplicates=duplicates,
        errors=errors,
    )