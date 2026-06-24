"""
MODULE : api/services/analytics_service.py
DESCRIPTION : Service analytics — agrégations SQL pour le dashboard Next.js.

RÉFÉRENCES ACADÉMIQUES :
- [Sculley2015] Hidden Technical Debt in ML Systems → fenêtre glissante + deltas.
- [Bauder2017] Medicare fraud detection → FPR = REJECTED / décisions actées.
- [Chicco2020] BMC Genomics → MCC réservé à get_model_performance.

DÉCISIONS DE CONCEPTION :
- get_dashboard_stats expose un contrat figé miroir de DashboardKpis (frontend).
- Deltas T-1 sur la fenêtre `[since - period, since)` (longueur égale, adjacente).
- "Urgent" = PENDING dont score >= branche.anomaly_score_block (DB, non hardcodé).
- "Économies" = somme montant_xaf des sinistres avec décision CONFIRMED.
"""
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.orm import Session

_cache: dict = {}
_CACHE_TTL = 300


def _cached(key: str, fn, *args):
    now = time.monotonic()
    if key in _cache and now - _cache[key]["ts"] < _CACHE_TTL:
        return _cache[key]["data"]
    data = fn(*args)
    _cache[key] = {"data": data, "ts": now}
    return data


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _period_bounds(period_days: int) -> tuple[datetime, datetime, datetime]:
    """
    Retourne (now, since, prev_since) :
    - since      : début de la période courante (now - period)
    - prev_since : début de la période précédente (since - period)

    [Sculley2015] — fenêtre glissante adjacente pour comparaison T vs T-1.
    """
    now = datetime.now(tz=timezone.utc)
    since = now - timedelta(days=period_days)
    prev_since = since - timedelta(days=period_days)
    return now, since, prev_since


def _drift_status_by_branch(db: Session) -> dict[str, str]:
    """
    Dernier statut de drift par code de branche.
    Retourne un dict {"sante": "STABLE", "auto": "WARNING", ...}.
    Branches sans drift_report → "UNKNOWN".

    Implémentation : tri descendant + déduplication Python. Plus robuste qu'une
    sous-requête `MAX(computed_at) GROUP BY branch_id` qui produit du SQL
    ambigu avec SQLAlchemy si les noms de colonnes se télescopent.
    """
    from core.db.models.monitoring import DriftReport
    from core.db.models.referentiels import Branch

    rows = (
        db.query(Branch.code, DriftReport.status, DriftReport.computed_at)
        .join(DriftReport, DriftReport.branch_id == Branch.id)
        .order_by(DriftReport.computed_at.desc())
        .all()
    )
    result: dict[str, str] = {}
    for code, status, _ in rows:
        if code not in result:  # premier vu = plus récent (tri desc)
            result[code] = status
    # Branches actives non couvertes → UNKNOWN
    for b in db.query(Branch).all():
        result.setdefault(b.code, "UNKNOWN")
    return result


def _branch_block_thresholds(db: Session) -> dict[str, float]:
    """Seuil `anomaly_score_block` par code de branche (pour "urgent")."""
    from core.db.models.referentiels import Branch
    return {b.code: b.anomaly_score_block or 0.9 for b in db.query(Branch).all()}


# ---------------------------------------------------------------------------
# Endpoint principal : GET /analytics/dashboard
# ---------------------------------------------------------------------------

def get_dashboard_stats(db: Session, period_days: int) -> dict:
    """
    Stats globales du dashboard MAKORA.

    Contrat de sortie (miroir de DashboardKpis côté frontend) :
        - total_claims_analyzed, claims_analyzed_24h_diff
        - global_anomaly_rate, anomaly_rate_diff
        - pending_decisions, urgent_decisions
        - drift_status_sante, drift_status_auto
        - total_anomalies_count, anomalies_24h_diff, avg_anomaly_score  (Gap #1)
        - false_positives_count, false_positive_rate,
          confirmed_fraud_count, confirmation_rate                       (Gap #2)
        - estimated_savings_xaf, savings_breakdown                       (Gap #3)
        - period_days  (echo de l'input pour debug)

    Référence : [Sculley2015] §3 — monitoring d'un pipeline ML en production.
    """
    from core.db.models.pipeline import Analysis
    from core.db.models.hitl_graph import Decision
    from core.db.models.sinistres import Claim
    from core.db.models.referentiels import Branch

    _, since, prev_since = _period_bounds(period_days)

    # ------------------------------------------------------------------
    # 1. Volumes globaux période courante
    # ------------------------------------------------------------------
    total_curr = (
        db.query(func.count(Analysis.id))
        .filter(Analysis.created_at >= since)
        .scalar()
        or 0
    )
    anomalies_curr = (
        db.query(func.count(Analysis.id))
        .filter(Analysis.created_at >= since, Analysis.is_anomaly == True)
        .scalar()
        or 0
    )
    avg_score_curr = (
        db.query(func.avg(Analysis.anomaly_score))
        .filter(Analysis.created_at >= since)
        .scalar()
    )

    # ------------------------------------------------------------------
    # 2. Volumes période précédente (pour deltas T vs T-1)
    # ------------------------------------------------------------------
    total_prev = (
        db.query(func.count(Analysis.id))
        .filter(Analysis.created_at >= prev_since, Analysis.created_at < since)
        .scalar()
        or 0
    )
    anomalies_prev = (
        db.query(func.count(Analysis.id))
        .filter(
            Analysis.created_at >= prev_since,
            Analysis.created_at < since,
            Analysis.is_anomaly == True,
        )
        .scalar()
        or 0
    )

    # Deltas (entiers et taux)
    claims_diff = total_curr - total_prev
    anomalies_diff = anomalies_curr - anomalies_prev
    rate_curr = (anomalies_curr / total_curr) if total_curr else 0.0
    rate_prev = (anomalies_prev / total_prev) if total_prev else 0.0
    rate_diff = round(rate_curr - rate_prev, 4)

    # ------------------------------------------------------------------
    # 3. Décisions HITL — pending + urgent
    # ------------------------------------------------------------------
    block_thresholds = _branch_block_thresholds(db)
    pending_total = (
        db.query(func.count(Analysis.id))
        .filter(
            Analysis.created_at >= since,
            Analysis.decision_status == "PENDING",
        )
        .scalar()
        or 0
    )

    # Urgent = PENDING + score >= seuil block de la branche correspondante.
    # On agrège par branch_id puis on filtre côté Python (peu de branches).
    pending_by_branch = (
        db.query(Branch.code, Analysis.anomaly_score)
        .join(Branch, Analysis.branch_id == Branch.id)
        .filter(
            Analysis.created_at >= since,
            Analysis.decision_status == "PENDING",
        )
        .all()
    )
    urgent_count = sum(
        1
        for code, score in pending_by_branch
        if (score or 0.0) >= block_thresholds.get(code, 0.9)
    )

    # ------------------------------------------------------------------
    # 4. Gap #2 — Faux positifs et fraude confirmée
    #    [Bauder2017] : FPR opérationnel = REJECTED / (CONFIRMED + REJECTED).
    #    On ignore ESCALATED qui n'a pas de verdict final.
    # ------------------------------------------------------------------
    decisions_in_window = (
        db.query(Decision.decision, func.count(Decision.id))
        .filter(Decision.created_at >= since)
        .group_by(Decision.decision)
        .all()
    )
    dec_map = {d: int(c) for d, c in decisions_in_window}
    confirmed_count = dec_map.get("CONFIRMED", 0)
    rejected_count = dec_map.get("REJECTED", 0)
    decided_total = confirmed_count + rejected_count
    fp_rate = round(rejected_count / decided_total, 4) if decided_total else 0.0
    confirm_rate = (
        round(confirmed_count / decided_total, 4) if decided_total else 0.0
    )

    # ------------------------------------------------------------------
    # 5. Gap #3 — Économies estimées XAF par branche
    #    Hypothèse : sans détection, le montant des claims CONFIRMED aurait été
    #    versé. Somme par branche depuis la table Claim jointe via Analysis.
    # ------------------------------------------------------------------
    savings_rows = (
        db.query(Branch.code, func.coalesce(func.sum(Claim.montant_xaf), 0.0))
        .join(Analysis, Analysis.branch_id == Branch.id)
        .join(Claim, Claim.id == Analysis.claim_id)
        .join(Decision, Decision.analysis_id == Analysis.id)
        .filter(
            Decision.decision == "CONFIRMED",
            Decision.created_at >= since,
        )
        .group_by(Branch.code)
        .all()
    )
    savings_breakdown = {code: float(amount or 0.0) for code, amount in savings_rows}
    total_savings = float(sum(savings_breakdown.values()))

    # ------------------------------------------------------------------
    # 6. Drift status par branche (dernier rapport en date)
    # ------------------------------------------------------------------
    drift_by_branch = _drift_status_by_branch(db)

    # ------------------------------------------------------------------
    # 7. Décisions par statut (rétrocompatibilité — clef "decisions")
    # ------------------------------------------------------------------
    status_rows = (
        db.query(Analysis.decision_status, func.count(Analysis.id))
        .filter(Analysis.created_at >= since)
        .group_by(Analysis.decision_status)
        .all()
    )
    decisions_by_status = {s: int(c) for s, c in status_rows}

    # ------------------------------------------------------------------
    # 8. Sortie — contrat figé pour le frontend
    # ------------------------------------------------------------------
    return {
        # echo
        "period_days": period_days,
        # ----- Contrat DashboardKpis (frontend) -----
        "total_claims_analyzed": int(total_curr),
        "claims_analyzed_24h_diff": int(claims_diff),
        "global_anomaly_rate": round(rate_curr, 4),
        "anomaly_rate_diff": rate_diff,
        "pending_decisions": int(pending_total),
        "urgent_decisions": int(urgent_count),
        "drift_status_sante": drift_by_branch.get("sante", "UNKNOWN"),
        "drift_status_auto": drift_by_branch.get("auto", "UNKNOWN"),
        # ----- Gap #1 — anomalies en valeur absolue + score moyen -----
        "total_anomalies_count": int(anomalies_curr),
        "anomalies_24h_diff": int(anomalies_diff),
        "avg_anomaly_score": round(float(avg_score_curr or 0.0), 4),
        # ----- Gap #2 — faux positifs + taux de confirmation -----
        "false_positives_count": int(rejected_count),
        "false_positive_rate": fp_rate,
        "confirmed_fraud_count": int(confirmed_count),
        "confirmation_rate": confirm_rate,
        # ----- Gap #3 — économies estimées XAF -----
        "estimated_savings_xaf": round(total_savings, 0),
        "savings_breakdown": savings_breakdown,
        # ----- Compatibilité ascendante (autres consommateurs) -----
        "decisions": decisions_by_status,
        "by_branch": {},
        # Anciennes clés conservées (utilisées par /reports/stats si appelé)
        "total_analyzed": int(total_curr),
        "anomaly_count": int(anomalies_curr),
        "anomaly_rate": round(rate_curr, 4),
    }


# ---------------------------------------------------------------------------
# Top features SHAP — inchangé
# ---------------------------------------------------------------------------

def get_top_shap_features(
    db: Session, branch: str | None, period_days: int, limit: int = 10
) -> list[dict]:
    """
    Top features par |avg_shap| décroissant sur les anomalies de la période.

    Référence : [Lundberg2017] §3 — l'importance globale d'une feature SHAP
    est la moyenne des |φ_i| sur l'échantillon ; ici on prend la moyenne signée
    pour conserver la direction du contributeur.
    """
    from core.db.models.pipeline import ShapContribution, Analysis
    from core.db.models.referentiels import Branch

    since = datetime.now(tz=timezone.utc) - timedelta(days=period_days)
    q = (
        db.query(
            ShapContribution.feature_name,
            func.avg(ShapContribution.shap_value).label("avg_shap"),
            func.count().label("count"),
        )
        .join(Analysis, ShapContribution.analysis_id == Analysis.id)
        .filter(Analysis.created_at >= since, Analysis.is_anomaly == True)
    )
    if branch:
        q = q.join(Branch, Analysis.branch_id == Branch.id).filter(
            Branch.code == branch
        )
    q = (
        q.group_by(ShapContribution.feature_name)
        .order_by(func.abs(func.avg(ShapContribution.shap_value)).desc())
        .limit(limit)
    )
    return [
        {
            "feature_name": r.feature_name,
            "avg_shap": round(float(r.avg_shap), 4),
            "count": int(r.count),
        }
        for r in q.all()
    ]


# ---------------------------------------------------------------------------
# Distribution RCA — inchangé
# ---------------------------------------------------------------------------

def get_rca_distribution(db: Session, period_days: int) -> list[dict]:
    from core.db.models.pipeline import Analysis

    since = datetime.now(tz=timezone.utc) - timedelta(days=period_days)
    rows = (
        db.query(Analysis.rca_category, func.count().label("cnt"))
        .filter(Analysis.created_at >= since, Analysis.rca_category != None)
        .group_by(Analysis.rca_category)
        .order_by(func.count().desc())
        .all()
    )
    total = sum(r.cnt for r in rows)
    return [
        {
            "category": r.rca_category,
            "count": int(r.cnt),
            "percentage": round(r.cnt / total * 100, 1) if total else 0,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Performance modèles — inchangé
# ---------------------------------------------------------------------------

def get_model_performance(db: Session) -> list[dict]:
    from core.db.models.pipeline import ModelVersion, ProductionDeployment

    versions = db.query(ModelVersion).all()
    prod_ids = {
        d.model_version_id
        for d in db.query(ProductionDeployment)
        .filter(ProductionDeployment.replaced_at == None)
        .all()
    }
    return [
        {
            "model_id": str(v.id),
            "version_tag": v.version_tag,
            "algorithm": v.algorithm,
            "f1_score": v.f1_score,
            "auc_roc": v.auc_roc,
            "mcc": v.mcc,
            "fpr": v.fpr,
            "is_production": v.id in prod_ids,
        }
        for v in versions
    ]