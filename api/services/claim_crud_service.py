"""
MODULE : api/services/claim_crud_service.py
DESCRIPTION : Service CRUD sinistres — DRAFT → SUBMITTED → OPEN → CLOSED.

CORRECTION DT-CLAIM-001 :
- branch_id=branch.id ajouté dans create_claim() (NOT NULL contrainte DB).

PATCH B-AI-NEW-01 — Pipeline IA post-submit :
- claim_to_dossier_dict() : Claim ORM → dict pipeline (formats Santé/Auto).
- submit_claim() : accepte background_tasks + triggered_by_id, planifie
  run_pipeline_for_claim en arrière-plan (BNF-06 : p50 < 2s respecté).
- get_claim() : enrichit l'ORM avec latest_anomaly_score / latest_is_anomaly
  (attributs Python dynamiques, lus par Pydantic via from_attributes).

PATCH B-DOSSIER-02 — Features batch calculées depuis l'historique DB :
- praticien_concentration : calculé sur 30j glissants (plus hardcodé à 1.0).
- historique_ratio_praticien : moyenne des ratio_prix stockés dans ClaimLine.
- Montant_Facture / Prix_Unitaire_Ref : agrégés sur TOUTES les lignes pour
  sinistres multi-actes (ratio pondéré, cohérent avec [Bauder2017]).
- Même correction appliquée à garage_concentration (branche Auto).

RÉFÉRENCES :
- [Xu2023] DIF — pipeline de production déclenché en background.
- [Sculley2015] §4 — séparer le service HTTP du compute ML.
- [Bauder2017] — ratio total facturé / total référence mercuriale.
- [Jiang2014] — concentration praticien sur fenêtre glissante 30j.
"""
from typing import Optional
from uuid import UUID

from fastapi import BackgroundTasks, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from api.schemas.claims import ClaimCreate, ClaimLineCreate, ClaimUpdate
from core.db.models.sinistres import Claim, ClaimLine

VALID_TRANSITIONS = {
    "DRAFT": ["SUBMITTED"],
    "SUBMITTED": ["OPEN"],
    "OPEN": ["CLOSED"],
    "CLOSED": [],
}


# ───────────────────────────────────────────────────────────────────────────
# Helpers privés
# ───────────────────────────────────────────────────────────────────────────

def _get_claim(db: Session, claim_id: str) -> Claim:
    claim = db.query(Claim).filter(Claim.claim_id == claim_id).first()
    if not claim:
        raise HTTPException(
            status_code=404, detail=f"Sinistre '{claim_id}' introuvable"
        )
    return claim


def _get_claim_by_uuid(db: Session, claim_uuid: UUID) -> Claim:
    claim = db.query(Claim).filter(Claim.id == claim_uuid).first()
    if not claim:
        raise HTTPException(status_code=404, detail="Sinistre introuvable")
    return claim


def _enrich_with_latest_analysis(db: Session, claim: Claim) -> Claim:
    """Injecte latest_anomaly_score/latest_is_anomaly sur l'ORM (Décision 3)."""
    from core.db.models.pipeline import Analysis

    latest = (
        db.query(Analysis)
        .filter(Analysis.claim_id == claim.id)
        .order_by(desc(Analysis.created_at))
        .first()
    )
    claim.latest_anomaly_score = latest.anomaly_score if latest else None
    claim.latest_is_anomaly = latest.is_anomaly if latest else None
    claim.latest_analysis_id = str(latest.id) if latest else None
    return claim


# ───────────────────────────────────────────────────────────────────────────
# Helpers B-DOSSIER-02 — features contextuelles depuis l'historique DB
# ───────────────────────────────────────────────────────────────────────────

def _compute_praticien_concentration(
    db: Session, branch_id: UUID, praticien_hash: str,
    source_flux: str = "batch",
) -> float:
    """
    Concentration du praticien = nb de ses lignes / total lignes branche
    sur les 30 derniers jours, filtrée par source_flux.

    B-DOSSIER-02 — Filtre source_flux :
      - source_flux="batch"  : concentration parmi les imports batch
        uniquement (seed "structured" exclus → ratio représentatif du batch).
      - autres               : concentration sur tous les sinistres (30j).

    [Jiang2014] Fallback 0.0 si erreur DB ou praticien inconnu.
    """
    from datetime import date, timedelta

    if not praticien_hash:
        return 0.0

    try:
        cutoff = str(date.today() - timedelta(days=30))
        base_q = (
            db.query(ClaimLine.id)
            .join(Claim, ClaimLine.claim_id == Claim.id)
            .filter(Claim.branch_id == branch_id)
            .filter(Claim.date_soin >= cutoff)
        )
        # Filtre source_flux sur la valeur brute stockée en DB
        if source_flux == "batch":
            base_q = base_q.filter(Claim.source_flux.in_(["batch", "BATCH"]))

        total = base_q.count()
        if total == 0:
            return 0.0

        praticien_count = (
            base_q.filter(ClaimLine.praticien_id_hash == praticien_hash)
            .count()
        )
        return round(min(praticien_count / total, 1.0), 4)

    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "_compute_praticien_concentration échec : %s — fallback 0.0", exc
        )
        return 0.0


def _compute_historique_ratio_praticien(
    db: Session, branch_id: UUID, praticien_hash: str
) -> float:
    """
    Historique ratio praticien = moyenne des ratio_prix stockés dans ClaimLine.

    [Bauder2017] : un praticien avec un ratio moyen élevé sur l'ensemble
    de ses dossiers est suspect même si chaque dossier semble raisonnable.

    Fallback : 1.0 (valeur neutre) si aucun historique ou erreur DB.
    """
    if not praticien_hash:
        return 1.0

    try:
        lines = (
            db.query(ClaimLine)
            .join(Claim, ClaimLine.claim_id == Claim.id)
            .filter(Claim.branch_id == branch_id)
            .filter(ClaimLine.praticien_id_hash == praticien_hash)
            .all()
        )
        ratios = []
        for ln in lines:
            rp = getattr(ln, "ratio_prix", None)
            if rp and float(rp) > 0:
                ratios.append(float(rp))
        if not ratios:
            return 1.0
        return round(sum(ratios) / len(ratios), 4)

    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "_compute_historique_ratio_praticien échec : %s — fallback 1.0", exc
        )
        return 1.0


def _compute_garage_concentration(
    db: Session, branch_id: UUID, garage_hash: str
) -> float:
    """Même logique que praticien_concentration pour la branche Auto."""
    from datetime import date, timedelta

    if not garage_hash:
        return 0.0

    cutoff = str(date.today() - timedelta(days=30))

    total = (
        db.query(ClaimLine)
        .join(Claim, ClaimLine.claim_id == Claim.id)
        .filter(Claim.branch_id == branch_id)
        .filter(Claim.date_soin >= cutoff)
        .count()
    )
    if total == 0:
        return 0.0

    garage_count = (
        db.query(ClaimLine)
        .join(Claim, ClaimLine.claim_id == Claim.id)
        .filter(Claim.branch_id == branch_id)
        .filter(Claim.date_soin >= cutoff)
        .filter(ClaimLine.garage_id_hash == garage_hash)
        .count()
    )
    return round(min(garage_count / total, 1.0), 4)


# ───────────────────────────────────────────────────────────────────────────
# claim_to_dossier_dict (B-AI-NEW-01 + B-DOSSIER-02)
# ───────────────────────────────────────────────────────────────────────────

def claim_to_dossier_dict(db: Session, claim: Claim) -> dict:
    """
    Convertit un Claim ORM + ClaimLines + Contract → dict pipeline.

    Format Santé : ID_Sinistre, ID_Assure, ID_Praticien, Code_Acte,
        Montant_Facture, Prix_Unitaire_Ref, Devise, Taux_Change, Date_Soin,
        Source_Flux.
    Format Auto : ID_Sinistre, ID_Assure, ID_Garage, Poste_Reparation,
        Montant_Devis, Montant_Ref_Reparation, Devise, Taux_Change,
        Date_Sinistre, Source_Flux.

    B-DOSSIER-02 : pour les sinistres multi-lignes, Montant_Facture et
    Prix_Unitaire_Ref sont les SOMMES sur toutes les lignes (ratio pondéré).
    Les features contextuelles (concentration, historique) sont calculées
    depuis l'historique DB et non hardcodées à 1.0.

    [Bauder2017] : Prix_Unitaire_Ref est la feature centrale d'upcoding.
    """
    from math import log1p as _log1p
    from core.db.models.referentiels import Branch, Contract

    branch = db.query(Branch).filter(Branch.id == claim.branch_id).first()
    branch_code = branch.code if branch else "unknown"

    insured_hash = ""
    if claim.contract_id:
        contract = db.query(Contract).filter(Contract.id == claim.contract_id).first()
        if contract and getattr(contract, "insured", None):
            insured_hash = contract.insured.id_hash or ""

    # ── Récupération de TOUTES les lignes (multi-actes) ──────────────────
    try:
        all_lines = (
            db.query(ClaimLine)
            .filter(ClaimLine.claim_id == claim.id)
            .all()
        )
    except Exception:
        all_lines = []
    first_line = all_lines[0] if all_lines else None

    # ── Montant agrégé : somme de toutes les lignes (B-DOSSIER-02) ────────
    # Pour mono-ligne : identique à l'ancien comportement.
    # Pour multi-lignes : ratio pondéré = total_facturé / total_référence.
    if all_lines:
        total_facture = sum(float(getattr(l, "montant_ligne", None) or 0) for l in all_lines)
        total_ref     = sum(float(getattr(l, "prix_ref", None) or 0) for l in all_lines)
        montant  = total_facture if total_facture > 0 else float(claim.montant_facture or 0.0)
        prix_ref = total_ref     if total_ref > 0     else (
            float(getattr(first_line, "prix_ref", None) or 0.0) if first_line else 0.0
        )
    else:
        montant  = float(claim.montant_xaf or claim.montant_facture or 0.0)
        prix_ref = float(getattr(first_line, "prix_ref", None) or 0.0) if first_line else 0.0

    devise      = claim.devise or "XAF"
    date_str    = claim.date_soin.isoformat() if claim.date_soin else ""
    source_flux = claim.source_flux or "structured"

    _is_weekend  = int(claim.date_soin.weekday() >= 5) if claim.date_soin else 0
    _montant_log = round(_log1p(montant / 1_000), 6) if montant > 0 else 0.0
    _delai_days  = (
        (claim.date_declaration - claim.date_soin).days
        if claim.date_declaration and claim.date_soin else 0
    )

    if branch_code == "sante":
        _praticien_hash = (first_line.praticien_id_hash if first_line else "") or ""

        # B-DOSSIER-02 : features contextuelles depuis historique DB
        _concentration      = _compute_praticien_concentration(db, claim.branch_id, _praticien_hash, source_flux)
        _historique_ratio   = _compute_historique_ratio_praticien(db, claim.branch_id, _praticien_hash)

        return {
            # ── Colonnes brutes ───────────────────────────────────────────
            "ID_Sinistre":       claim.claim_id,
            "ID_Assure":         insured_hash,
            "ID_Praticien":      _praticien_hash,
            "Code_Acte":         (first_line.code_acte if first_line else "") or "",
            "Montant_Facture":   montant,
            "Prix_Unitaire_Ref": prix_ref,
            "Devise":            devise,
            "Taux_Change":       1.0,
            "Date_Soin":         date_str,
            "Source_Flux":       source_flux,
            # ── Features DIF pré-calculées (noms v0.4.0 — NE PAS RENOMMER) ──────
            # [Xu2023] Le MinMaxScaler a été entraîné avec ces noms exacts.
            # Renommer flag_doublon_sante/community_score_sante/praticien_concentration
            # enlève 3 features → 14/17 → crash "MinMaxScaler is expecting 17 features".
            # B-DOSSIER-02 : praticien_concentration passe de 1.0 hardcodé
            # à une valeur calculée depuis l'historique DB (source_flux filtre).
            "flag_weekend_care":        _is_weekend,
            "flag_doublon_sante":       0,           # ← NOM v0.4.0 — NE PAS CHANGER
            "community_score_sante":    0.0,         # ← NOM v0.4.0 — NE PAS CHANGER
            "montant_normalise_log":    _montant_log,
            "delai_soin_depot_anormal": int(_delai_days > 30),
            "praticien_concentration":  _concentration,        # ← NOM v0.4.0 + valeur dynamique
            "historique_ratio_praticien": _historique_ratio,  # ← pré-calculé DB
        }

    if branch_code == "auto":
        _garage_hash = (first_line.garage_id_hash if first_line else "") or ""
        _concentration = _compute_garage_concentration(db, claim.branch_id, _garage_hash)

        return {
            # ── Colonnes brutes ───────────────────────────────────────────
            "ID_Sinistre":            claim.claim_id,
            "ID_Assure":              insured_hash,
            "ID_Garage":              _garage_hash,
            "Poste_Reparation":       (first_line.libelle if first_line else "") or "",
            "Montant_Devis":          montant,
            "Montant_Ref_Reparation": prix_ref,
            "Devise":                 devise,
            "Taux_Change":            1.0,
            "Date_Sinistre":          date_str,
            "Source_Flux":            source_flux,
            # ── Features DIF pré-calculées (noms originaux — NE PAS RENOMMER) ──
            "flag_weekend_care":              _is_weekend,
            "flag_doublon_auto":              0,
            "community_score_auto":           0.0,
            "montant_normalise_log":          _montant_log,
            "delai_sinistre_depot_anormal":   int(_delai_days > 30),
            "garage_concentration":           _concentration,  # ← dynamique
        }

    return {
        "ID_Sinistre":     claim.claim_id,
        "Montant_Facture": montant,
        "Devise":          devise,
        "Taux_Change":     1.0,
        "Date_Soin":       date_str,
        "Source_Flux":     source_flux,
    }


# ───────────────────────────────────────────────────────────────────────────
# list_claims — Liste paginée avec enrichissement Analysis
# ───────────────────────────────────────────────────────────────────────────

def list_claims(
    db: Session,
    branch_code: str | None,
    statut: str | None,
    date_from,
    date_to,
    is_anomaly: bool | None,
    score_min: float | None,
    offset: int,
    limit: int,
):
    """Liste paginée avec dernière analyse jointe (anomaly_score exposé)."""
    from core.db.models.pipeline import Analysis
    from core.db.models.referentiels import Branch

    q = db.query(Claim)
    if branch_code:
        q = q.join(Branch, Claim.branch_id == Branch.id).filter(Branch.code == branch_code)
    if statut:
        q = q.filter(Claim.statut == statut)
    if date_from:
        q = q.filter(Claim.date_soin >= date_from)
    if date_to:
        q = q.filter(Claim.date_soin <= date_to)

    total = q.count()
    claims = q.order_by(desc(Claim.created_at)).offset(offset).limit(limit).all()

    claim_ids = [c.id for c in claims]
    if claim_ids:
        latest_analyses = (
            db.query(Analysis)
            .filter(Analysis.claim_id.in_(claim_ids))
            .order_by(Analysis.claim_id, desc(Analysis.created_at))
            .all()
        )
        latest_by_claim: dict = {}
        for a in latest_analyses:
            if a.claim_id not in latest_by_claim:
                latest_by_claim[a.claim_id] = a
        for c in claims:
            a = latest_by_claim.get(c.id)
            c.latest_anomaly_score = a.anomaly_score if a else None
            c.latest_is_anomaly = a.is_anomaly if a else None
            c.latest_analysis_id = str(a.id) if a else None
    else:
        for c in claims:
            c.latest_anomaly_score = None
            c.latest_is_anomaly = None
            c.latest_analysis_id = None

    if is_anomaly is not None:
        claims = [c for c in claims if c.latest_is_anomaly == is_anomaly]
    if score_min is not None:
        claims = [c for c in claims if (c.latest_anomaly_score or 0) >= score_min]

    return total, claims


# ───────────────────────────────────────────────────────────────────────────
# get_claim — MODIFIÉ pour enrichissement Analysis (Décision 3)
# ───────────────────────────────────────────────────────────────────────────

def get_claim(db: Session, claim_id: str) -> Claim:
    """Récupère un claim + enrichit avec latest_anomaly_score/latest_is_anomaly."""
    claim = _get_claim(db, claim_id)
    return _enrich_with_latest_analysis(db, claim)


# ───────────────────────────────────────────────────────────────────────────
# create_claim — Inchangé (DT-CLAIM-001 préservé)
# ───────────────────────────────────────────────────────────────────────────

def create_claim(db: Session, data: ClaimCreate, created_by: UUID) -> Claim:
    if db.query(Claim).filter(Claim.claim_id == data.claim_id).first():
        raise HTTPException(
            status_code=409, detail=f"Sinistre '{data.claim_id}' existe déjà"
        )
    from core.db.models.referentiels import Branch
    branch = db.query(Branch).filter(Branch.code == data.branch_code).first()
    if not branch:
        raise HTTPException(
            status_code=400, detail=f"Branche inconnue : {data.branch_code}"
        )
    claim = Claim(
        claim_id=data.claim_id, branch_id=branch.id,
        source_flux=data.source_flux, montant_facture=data.montant_facture,
        devise=data.devise, date_soin=data.date_soin,
        date_declaration=data.date_declaration,
        statut="DRAFT", created_by=created_by,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim


def update_claim(db: Session, claim_id: str, data: ClaimUpdate) -> Claim:
    claim = _get_claim(db, claim_id)
    if claim.statut not in ("DRAFT", "OPEN"):
        raise HTTPException(
            status_code=400,
            detail=f"Sinistre en statut '{claim.statut}' non modifiable",
        )
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(claim, field, value)
    db.commit()
    db.refresh(claim)
    return claim


# ───────────────────────────────────────────────────────────────────────────
# submit_claim — MODIFIÉ pour planifier la pipeline IA (B-AI-NEW-01)
# ───────────────────────────────────────────────────────────────────────────

def submit_claim(
    db: Session,
    claim_id: str,
    background_tasks: Optional[BackgroundTasks] = None,
    triggered_by_id: Optional[UUID] = None,
) -> Claim:
    """
    DRAFT → SUBMITTED + planifie run_pipeline_for_claim en arrière-plan.

    SÉQUENCE :
    1. Vérifier statut == DRAFT.
    2. Construire le dossier dict AVANT le commit (claim attaché à la session).
    3. Résoudre le branch_code.
    4. Transition statut → SUBMITTED + commit.
    5. Si background_tasks fourni : add_task(run_pipeline_for_claim, ...).
    6. Retourner le claim (HTTP 200 immédiat — BNF-06).

    En cas d'échec du pipeline, le claim reste SUBMITTED (Décision 1).
    """
    from core.db.models.referentiels import Branch

    claim = _get_claim(db, claim_id)
    if claim.statut != "DRAFT":
        raise HTTPException(
            status_code=400, detail="Seuls les sinistres DRAFT peuvent être soumis"
        )

    dossier = claim_to_dossier_dict(db, claim)

    branch = db.query(Branch).filter(Branch.id == claim.branch_id).first()
    if not branch:
        raise HTTPException(
            status_code=500,
            detail="Branche introuvable pour ce sinistre (incohérence DB)",
        )
    branch_code = branch.code
    claim_uuid = claim.id

    claim.statut = "SUBMITTED"
    db.commit()
    db.refresh(claim)

    if background_tasks is not None:
        from api.services.analyze_service import run_pipeline_for_claim
        background_tasks.add_task(
            run_pipeline_for_claim,
            claim_uuid=claim_uuid,
            branch_code=branch_code,
            dossier=dossier,
            triggered_by_id=triggered_by_id,
        )

    return claim


# ───────────────────────────────────────────────────────────────────────────
# Helpers — enrichissement mercuriale (B-LIN-01/06)
# ───────────────────────────────────────────────────────────────────────────

def _enrich_line_with_reference(
    db: Session, branch_id: UUID, line: ClaimLine
) -> None:
    """
    Enrichit une ClaimLine avec prix_ref et ratio_prix depuis la mercuriale.

    [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection.
      → Le ratio facturé/référence > 1.5 est la règle RCA_SURF_001
        (surfacturation). Sans cette jointure, la règle ne se déclenche
        jamais et le LLM narrator reste désactivé.

    Logique :
      - code_acte vide ou prix_ref_xaf <= 0 → no-op (silencieux)
      - ReferencePrice doit être valide (valid_from <= today, valid_to NULL
        ou >= today). En cas de versions multiples on prend la plus récente.
      - Si montant_ligne renseigné > 0 → calcul ratio_prix arrondi 3 décimales
      - Sinon → on remplit seulement prix_ref (l'update ultérieur déclenchera
        le calcul du ratio quand le montant sera saisi)
    """
    from datetime import date
    from core.db.models.referentiels import ReferencePrice

    if not line.code_acte:
        return

    today = date.today()
    ref = (
        db.query(ReferencePrice)
        .filter(
            ReferencePrice.branch_id == branch_id,
            ReferencePrice.code_acte == line.code_acte,
            ReferencePrice.valid_from <= today,
        )
        .filter(
            (ReferencePrice.valid_to.is_(None))
            | (ReferencePrice.valid_to >= today)
        )
        .order_by(ReferencePrice.valid_from.desc())
        .first()
    )

    if not ref or not ref.prix_ref_xaf or ref.prix_ref_xaf <= 0:
        return

    line.prix_ref = ref.prix_ref_xaf
    if line.montant_ligne and line.montant_ligne > 0:
        line.ratio_prix = round(line.montant_ligne / ref.prix_ref_xaf, 3)


# ───────────────────────────────────────────────────────────────────────────
# Lignes de détail — inchangé
# ───────────────────────────────────────────────────────────────────────────

def add_line(db: Session, claim_id: str, data: ClaimLineCreate) -> ClaimLine:
    claim = _get_claim(db, claim_id)
    if claim.statut != "DRAFT":
        raise HTTPException(
            status_code=400, detail="Ajout de ligne impossible hors statut DRAFT"
        )
    line = ClaimLine(claim_id=claim.id, **data.model_dump())
    _enrich_line_with_reference(db, claim.branch_id, line)  # ← AJOUT B-LIN-01/06
    db.add(line)
    db.commit()
    db.refresh(line)
    return line


def update_line(
    db: Session, claim_id: str, line_id: UUID, data: ClaimLineCreate
) -> ClaimLine:
    claim = _get_claim(db, claim_id)
    if claim.statut != "DRAFT":
        raise HTTPException(
            status_code=400, detail="Modification impossible hors statut DRAFT"
        )
    line = (
        db.query(ClaimLine)
        .filter(ClaimLine.id == line_id, ClaimLine.claim_id == claim.id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="Ligne introuvable")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(line, field, value)
    _enrich_line_with_reference(db, claim.branch_id, line)
    db.commit()
    db.refresh(line)
    return line


def delete_line(db: Session, claim_id: str, line_id: UUID) -> None:
    claim = _get_claim(db, claim_id)
    if claim.statut != "DRAFT":
        raise HTTPException(
            status_code=400, detail="Suppression impossible hors statut DRAFT"
        )
    line = (
        db.query(ClaimLine)
        .filter(ClaimLine.id == line_id, ClaimLine.claim_id == claim.id)
        .first()
    )
    if not line:
        raise HTTPException(status_code=404, detail="Ligne introuvable")
    db.delete(line)
    db.commit()