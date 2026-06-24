"""
MODULE : api/services/watchlist_service.py
DESCRIPTION : Service watchlist MAKORA — agrégations par entité opérationnelle.

Gère les vues "à surveiller" du dashboard :
- Praticiens à surveiller (Gap #4, Étape 6)
- Focus régional Cameroun (Gap #5, Étape 7)

RÉFÉRENCES ACADÉMIQUES :
- [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection using
  machine learning methods. ICMLA. → §4 analyse par prestataire.
- [Sculley2015] Hidden Technical Debt in ML Systems → §3 slice monitoring.
- [Chandola2009] Anomaly Detection: A Survey. §6.5 — analyse contextuelle
  par sous-population (région) révèle des anomalies invisibles globalement.

DÉCISIONS DE CONCEPTION :
- Fichier séparé de analytics_service.py pour respecter IMP-007 (≤ 400 lignes)
  et regrouper les vues opérationnelles (cohésion fonctionnelle).
- Hash praticien exposé complet (déjà SHA-256 pseudonymisé). UI tronque.
- Seuils heuristiques opérationnels (pas des métriques scientifiques) :
  · score_trend ±0.05
  · regional level : 0.04 et 0.08
- Régional : pas de colonne claims.region en DB → dérivation par jointures :
  · santé : claim_lines → practitioners.region
  · auto  : claim_lines → garages.ville → mapping _VILLE_TO_REGION_CM
- Mapping ville→région hardcodé (4 entrées seulement). À promouvoir en
  référentiel YAML si la liste grandit (dette technique DT-WATCHLIST-01).
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func
from sqlalchemy.orm import Session


# ─────────────────────────────────────────────────────────────────────
# Constantes
# ─────────────────────────────────────────────────────────────────────

_TREND_THRESHOLD = 0.05
"""Delta absolu en dessous duquel score_trend = 'stable'."""

_REGIONAL_HIGH = 0.08
_REGIONAL_MEDIUM = 0.04
"""Seuils opérationnels pour le level régional."""

# 10 régions officielles ASAC du Cameroun (ordre administratif)
REGIONS_CM = [
    "Adamaoua", "Centre", "Est", "Extrême-Nord", "Littoral",
    "Nord", "Nord-Ouest", "Ouest", "Sud", "Sud-Ouest",
]

# Mapping ville (champ garages.ville) → région ASAC
# Couvre les villes seedées par seed_06_demo_claims_v2.
# DT-WATCHLIST-01 : à promouvoir en config/referentials/regions_cameroun.yaml
# si le nombre de villes dépasse une dizaine.
_VILLE_TO_REGION_CM: dict[str, str] = {
    "Douala": "Littoral",
    "Yaoundé": "Centre",
    "Bafoussam": "Ouest",
    "Garoua": "Nord",
    # Extensions futures à ajouter ici, ou migrer vers YAML.
}


# ─────────────────────────────────────────────────────────────────────
# Helpers internes
# ─────────────────────────────────────────────────────────────────────

def _period_bounds(period_days: int) -> tuple[datetime, datetime]:
    """Retourne (since, prev_since) — bornes courante et précédente."""
    now = datetime.now(tz=timezone.utc)
    since = now - timedelta(days=period_days)
    prev_since = since - timedelta(days=period_days)
    return since, prev_since


def _classify_trend(curr_score: float, prev_score: float | None) -> str:
    """Classifie l'évolution d'un score d'anomalie entre deux périodes."""
    if prev_score is None:
        return "stable"
    delta = curr_score - prev_score
    if delta > _TREND_THRESHOLD:
        return "up"
    if delta < -_TREND_THRESHOLD:
        return "down"
    return "stable"


def _classify_level(claim_count: int, anomaly_rate: float) -> str:
    """Classifie le niveau d'alerte régional selon le taux d'anomalie."""
    if claim_count == 0:
        return "no_data"
    if anomaly_rate > _REGIONAL_HIGH:
        return "high"
    if anomaly_rate > _REGIONAL_MEDIUM:
        return "medium"
    return "low"


def _query_practitioners_aggregates(
    db: Session,
    since: datetime,
    until: datetime | None,
    branch: str | None,
    limit: int,
    restrict_hashes: list[str] | None = None,
):
    """Agrégats par praticien sur une fenêtre temporelle."""
    from core.db.models.pipeline import Analysis
    from core.db.models.referentiels import Practitioner, Branch
    from core.db.models.sinistres import Claim, ClaimLine

    q = (
        db.query(
            Practitioner.id_hash.label("id_hash"),
            Practitioner.specialite.label("specialite"),
            Practitioner.region.label("region"),
            Branch.code.label("branch_code"),
            func.count(func.distinct(Claim.id)).label("claims_count"),
            func.sum(
                case((Analysis.is_anomaly.is_(True), 1), else_=0)
            ).label("anomaly_count"),
            func.avg(Analysis.anomaly_score).label("avg_score"),
        )
        .join(ClaimLine, ClaimLine.praticien_id_hash == Practitioner.id_hash)
        .join(Claim, Claim.id == ClaimLine.claim_id)
        .join(Analysis, Analysis.claim_id == Claim.id)
        .join(Branch, Branch.id == Analysis.branch_id)
        .filter(Analysis.created_at >= since)
    )

    if until is not None:
        q = q.filter(Analysis.created_at < until)
    if branch:
        q = q.filter(Branch.code == branch)
    if restrict_hashes is not None:
        if not restrict_hashes:
            return []
        q = q.filter(Practitioner.id_hash.in_(restrict_hashes))

    q = q.group_by(
        Practitioner.id_hash,
        Practitioner.specialite,
        Practitioner.region,
        Branch.code,
    ).order_by(func.avg(Analysis.anomaly_score).desc())

    if restrict_hashes is None:
        q = q.limit(limit)

    return q.all()


# ─────────────────────────────────────────────────────────────────────
# Praticiens à surveiller — Gap #4 (Étape 6)
# ─────────────────────────────────────────────────────────────────────

def get_practitioners_watchlist(
    db: Session,
    branch: str | None,
    limit: int,
    period_days: int,
) -> list[dict]:
    """
    Top `limit` praticiens les plus suspects + tendance vs période N-1.

    Référence : [Bauder2017] §4 — analyse de fraude par prestataire.
    """
    since, prev_since = _period_bounds(period_days)

    curr_rows = _query_practitioners_aggregates(
        db, since=since, until=None, branch=branch, limit=limit,
    )
    if not curr_rows:
        return []

    top_hashes = [r.id_hash for r in curr_rows]
    prev_rows = _query_practitioners_aggregates(
        db,
        since=prev_since,
        until=since,
        branch=branch,
        limit=limit,
        restrict_hashes=top_hashes,
    )
    prev_score_by_hash: dict[str, float] = {
        r.id_hash: float(r.avg_score) for r in prev_rows
    }

    result: list[dict] = []
    for r in curr_rows:
        curr_score = float(r.avg_score)
        prev_score = prev_score_by_hash.get(r.id_hash)
        result.append({
            "practitioner_hash": r.id_hash,
            "specialty": r.specialite,
            "region": r.region,
            "branch": r.branch_code,
            "claims_count": int(r.claims_count),
            "anomaly_count": int(r.anomaly_count or 0),
            "avg_anomaly_score": round(curr_score, 4),
            "score_trend": _classify_trend(curr_score, prev_score),
        })

    return result


# ─────────────────────────────────────────────────────────────────────
# Focus régional — Gap #5 (Étape 7)
# ─────────────────────────────────────────────────────────────────────

def _query_sante_region_aggregates(db: Session, since: datetime):
    """
    Claims santé agrégés par région via jointure practitioners.region.

    Returns: liste de Row(region, claims, anoms).
    """
    from core.db.models.pipeline import Analysis
    from core.db.models.referentiels import Practitioner, Branch
    from core.db.models.sinistres import Claim, ClaimLine

    return (
        db.query(
            Practitioner.region.label("region"),
            func.count(func.distinct(Claim.id)).label("claims"),
            func.sum(
                case((Analysis.is_anomaly.is_(True), 1), else_=0)
            ).label("anoms"),
        )
        .join(ClaimLine, ClaimLine.praticien_id_hash == Practitioner.id_hash)
        .join(Claim, Claim.id == ClaimLine.claim_id)
        .join(Analysis, Analysis.claim_id == Claim.id)
        .join(Branch, Branch.id == Analysis.branch_id)
        .filter(
            Analysis.created_at >= since,
            Branch.code == "sante",
            Practitioner.region.isnot(None),
        )
        .group_by(Practitioner.region)
        .all()
    )


def _query_auto_ville_aggregates(db: Session, since: datetime):
    """
    Claims auto agrégés par ville (à mapper vers région côté Python).

    Returns: liste de Row(ville, claims, anoms).
    """
    from core.db.models.pipeline import Analysis
    from core.db.models.referentiels import Garage, Branch
    from core.db.models.sinistres import Claim, ClaimLine

    return (
        db.query(
            Garage.ville.label("ville"),
            func.count(func.distinct(Claim.id)).label("claims"),
            func.sum(
                case((Analysis.is_anomaly.is_(True), 1), else_=0)
            ).label("anoms"),
        )
        .join(ClaimLine, ClaimLine.garage_id_hash == Garage.id_hash)
        .join(Claim, Claim.id == ClaimLine.claim_id)
        .join(Analysis, Analysis.claim_id == Claim.id)
        .join(Branch, Branch.id == Analysis.branch_id)
        .filter(
            Analysis.created_at >= since,
            Branch.code == "auto",
            Garage.ville.isnot(None),
        )
        .group_by(Garage.ville)
        .all()
    )


def get_regional_anomalies(
    db: Session,
    branch: str | None,
    period_days: int,
) -> list[dict]:
    """
    Statistiques d'anomalies par région camerounaise sur la période.

    Stratégie : pas de colonne claims.region en DB, dérivation par jointures.
    Toutes les 10 régions ASAC sont systématiquement retournées (level="no_data"
    pour celles sans claims).

    Référence : [Chandola2009] §6.5 — analyse contextuelle par sous-population.

    Args:
        db: session SQLAlchemy
        branch: 'sante' | 'auto' | None (toutes branches)
        period_days: longueur de la fenêtre (1-365)

    Returns:
        Liste de dicts conformes à RegionalAnomalyItem, triés par
        anomaly_count DESC puis region ASC.
    """
    since, _ = _period_bounds(period_days)

    # Initialiser les 10 régions à 0
    accum: dict[str, dict] = {
        r: {
            "region": r,
            "claim_count": 0,
            "anomaly_count": 0,
            "branch_breakdown": {"sante": 0, "auto": 0},
        }
        for r in REGIONS_CM
    }

    # 1) Claims santé via practitioners.region
    if branch in (None, "sante"):
        for row in _query_sante_region_aggregates(db, since):
            if row.region in accum:
                accum[row.region]["claim_count"] += int(row.claims)
                accum[row.region]["anomaly_count"] += int(row.anoms or 0)
                accum[row.region]["branch_breakdown"]["sante"] = int(
                    row.anoms or 0
                )

    # 2) Claims auto via garages.ville → mapping vers région
    if branch in (None, "auto"):
        for row in _query_auto_ville_aggregates(db, since):
            region = _VILLE_TO_REGION_CM.get(row.ville)
            if region and region in accum:
                accum[region]["claim_count"] += int(row.claims)
                accum[region]["anomaly_count"] += int(row.anoms or 0)
                accum[region]["branch_breakdown"]["auto"] = int(row.anoms or 0)

    # 3) Calcul rate + level + sérialisation
    items: list[dict] = []
    for region_name, data in accum.items():
        claim_count = data["claim_count"]
        anomaly_count = data["anomaly_count"]
        rate = (anomaly_count / claim_count) if claim_count > 0 else 0.0
        items.append({
            "region": region_name,
            "claim_count": claim_count,
            "anomaly_count": anomaly_count,
            "anomaly_rate": round(rate, 4),
            "level": _classify_level(claim_count, rate),
            "branch_breakdown": data["branch_breakdown"],
        })

    # Tri : anomaly_count DESC, puis region ASC pour stabilité
    items.sort(key=lambda x: (-x["anomaly_count"], x["region"]))
    return items