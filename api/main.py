"""
MODULE : api/main.py
DESCRIPTION : Point d'entrée FastAPI MAKORA Phase 3.
Initialise l'application, enregistre tous les routers (17), configure
les middlewares et les handlers d'erreur.
"""
from __future__ import annotations
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.config import get_settings
from api.middleware.audit import AuditLogMiddleware
from api.middleware.errors import (
    generic_exception_handler, http_exception_handler, validation_exception_handler,
)
from api.middleware.rate_limit import setup_rate_limit

# ── Routers ──────────────────────────────────────────────
from api.routers.health import router as health_router
from api.routers.auth import router as auth_router
from api.routers.users import router as users_router
from api.routers.roles import router as roles_router
from api.routers.claims import router as claims_router
from api.routers.analyze import router as analyze_router
from api.routers.audit import router as audit_router
from api.routers.escalations import router as escalations_router
from api.routers.models import router as models_router
from api.routers.drift import router as drift_router
from api.routers.retraining import router as retraining_router
from api.routers.modules import router as modules_router
from api.routers.graph import router as graph_router
from api.routers.referentiels import router as referentiels_router
from api.routers.analytics import router as analytics_router
from api.routers.reports import router as reports_router
from api.routers.admin import router as admin_router

settings = get_settings()


# ── APRÈS ────────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle FastAPI — chargement des modèles joblib au démarrage."""
    import logging
    import threading
    logger = logging.getLogger("makora.startup")
    logger.info("🚀 MAKORA API démarrage — version %s", settings.VERSION)
    try:
        from core.plugin_registry import PluginRegistry
        PluginRegistry.discover()
        loaded = PluginRegistry.list_branches()
        logger.info("✓ PluginRegistry : %d module(s) chargé(s) : %s", len(loaded), loaded)
    except Exception as e:
        logger.warning("⚠ PluginRegistry non disponible au démarrage : %s", e)

    # Préchauffage du cache pipeline DIF en arrière-plan [Sculley2015].
    # Thread daemon : n'empêche pas le démarrage de l'API ni son arrêt propre.
    # La première soumission de claim ne subira pas la latence de 5-8s
    # liée au chargement des modèles DIF (~300 Mo).
    def _warmup_pipeline_cache() -> None:
        from api.services.analyze_service import _get_pipeline
        for branch in ("sante", "auto"):
            try:
                _get_pipeline(branch)
                logger.info("✓ Cache DIF préchauffé : branche=%s", branch)
            except Exception as exc:
                logger.warning(
                    "⚠ Préchauffage DIF échoué (branche=%s) : %s — "
                    "première soumission sera lente.",
                    branch, exc,
                )

    threading.Thread(target=_warmup_pipeline_cache, daemon=True).start()

    yield
    logger.info("🛑 MAKORA API arrêt propre")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description=(
            "API REST du Framework MAKORA — Détection générique d'anomalies assurance. "
            "Mémoire Master ITNS Nearshore Services 2025-2026."
        ),
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Audit middleware
    app.add_middleware(AuditLogMiddleware)

    # Rate limiting
    setup_rate_limit(app)

    # Error handlers
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # ── Enregistrement des 17 routers ─────────────────────
    prefix = settings.API_V1_PREFIX
    app.include_router(health_router)                               # /health
    app.include_router(auth_router,          prefix=prefix)         # /api/v1/auth
    app.include_router(users_router,         prefix=prefix)         # /api/v1/users
    app.include_router(roles_router,         prefix=prefix)         # /api/v1/roles
    app.include_router(claims_router,        prefix=prefix)         # /api/v1/claims
    app.include_router(analyze_router,       prefix=prefix)         # /api/v1/analyze
    app.include_router(audit_router,         prefix=prefix)         # /api/v1/audit
    app.include_router(escalations_router,   prefix=prefix)         # /api/v1/escalations
    app.include_router(models_router,        prefix=prefix)         # /api/v1/models
    app.include_router(drift_router,         prefix=prefix)         # /api/v1/drift
    app.include_router(retraining_router,    prefix=prefix)         # /api/v1/retraining
    app.include_router(modules_router,       prefix=prefix)         # /api/v1/modules
    app.include_router(graph_router,         prefix=prefix)         # /api/v1/graph
    app.include_router(referentiels_router,  prefix=prefix)         # /api/v1/referentiels
    app.include_router(analytics_router,     prefix=prefix)         # /api/v1/analytics
    app.include_router(reports_router,       prefix=prefix)         # /api/v1/reports
    app.include_router(admin_router,         prefix=prefix)         # /api/v1/admin

    return app


app = create_app()
