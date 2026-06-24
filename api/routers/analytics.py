"""
MODULE : api/routers/analytics.py
DESCRIPTION : Router FastAPI — Endpoints analytics MAKORA.

Endpoints :
- GET /analytics/dashboard                  — KPIs globaux
- GET /analytics/shap/top-features          — Top features SHAP toutes branches
- GET /analytics/shap/top-features/{branch} — Top features par branche
- GET /analytics/rca/distribution           — Distribution catégories RCA
- GET /analytics/models/performance         — Tableau métriques modèles (H0)
- GET /analytics/practitioners/watchlist    — Praticiens à surveiller (Gap #4)
- GET /analytics/regions/anomalies          — Focus régional Cameroun (Gap #5)
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.deps.auth import get_current_active_user
from api.deps.db import get_db
from api.deps.rbac import require_roles
from api.services import analytics_service as svc
from api.services import watchlist_service as watchlist_svc
from core.db.models.iam import User

router = APIRouter(prefix="/analytics", tags=["Analytics"])
_read = Depends(require_roles("auditeur", "administrateur", "expert_metier"))
_all = Depends(get_current_active_user)


@router.get("/dashboard")
def get_dashboard(
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db), _: User = _all,
):
    return svc.get_dashboard_stats(db, period_days)


@router.get("/shap/top-features")
def get_top_features(
    period_days: int = Query(30, ge=1, le=365), limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db), _: User = _read,
):
    return svc.get_top_shap_features(db, None, period_days, limit)


@router.get("/shap/top-features/{branch}")
def get_top_features_branch(
    branch: str, period_days: int = Query(30, ge=1, le=365), limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db), _: User = _read,
):
    return svc.get_top_shap_features(db, branch, period_days, limit)


@router.get("/rca/distribution")
def get_rca_distribution(
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db), _: User = _read,
):
    return svc.get_rca_distribution(db, period_days)


@router.get("/models/performance")
def get_model_performance(db: Session = Depends(get_db), _: User = _read):
    return svc.get_model_performance(db)


# ─────────────────────────────────────────────────────────────────────
# Gap #4 — Praticiens à surveiller (Étape 6)
# ─────────────────────────────────────────────────────────────────────

@router.get("/practitioners/watchlist")
def get_practitioners_watchlist(
    branch: str | None = Query(None, description="'sante' | 'auto' | None (toutes)"),
    limit: int = Query(10, ge=1, le=50),
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: User = _read,
):
    """
    Liste les praticiens à surveiller, triés par score d'anomalie moyen
    décroissant, avec tendance vs période précédente.

    Référence : [Bauder2017] Medicare fraud detection — analyse par prestataire.
    """
    return watchlist_svc.get_practitioners_watchlist(db, branch, limit, period_days)


# ─────────────────────────────────────────────────────────────────────
# Gap #5 — Focus régional Cameroun (Étape 7)
# ─────────────────────────────────────────────────────────────────────

@router.get("/regions/anomalies")
def get_regional_anomalies(
    branch: str | None = Query(None, description="'sante' | 'auto' | None (toutes)"),
    period_days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: User = _read,
):
    """
    Statistiques d'anomalies par région camerounaise sur la période.
    Retourne systématiquement les 10 régions ASAC (level="no_data" si vide),
    triées par anomaly_count DESC.

    Référence : [Chandola2009] §6.5 — analyse contextuelle par sous-population.
    """
    return watchlist_svc.get_regional_anomalies(db, branch, period_days)