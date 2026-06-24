# MAKORA Phase 3 — API FastAPI

## Description

API REST du Framework MAKORA — Détection générique d'anomalies assurance.
Mémoire Master, ATABONG EFON STEPHANE FRITZ, ITNS Nearshore Services, 2025-2026.

## Architecture

```
api/
├── main.py              # Point d'entrée FastAPI — 17 routers
├── config.py            # Settings via pydantic-settings (.env)
├── deps/                # Dépendances FastAPI (auth, rbac, pagination, db)
├── middleware/          # Audit, erreurs, rate-limit
├── schemas/             # Pydantic v2 — 11 modules de schémas
├── routers/             # 17 routers — 117 endpoints
└── services/            # Service layer — logique métier

core/
└── audit_logger.py      # Journal immuable (DT-AUDIT résolu)

tests/api/
├── conftest.py          # Fixtures pytest — TestClient, DB SQLite
├── test_*.py            # Tests unitaires (14 fichiers)
└── test_e2e_*.py        # Tests E2E (3 flux critiques)
```

## Démarrage rapide

```bash
# 1. Installer les dépendances
pip install -r requirements_api.txt

# 2. Configurer l'environnement
cp .env.example .env
# Éditer .env avec les valeurs réelles

# 3. Lancer l'API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 4. Documentation interactive
# http://localhost:8000/api/docs (Swagger UI)
# http://localhost:8000/api/redoc (ReDoc)
```

## Tests

```bash
# Lancer tous les tests API
pytest tests/api/ -v

# Tests avec couverture
pytest tests/api/ --cov=api --cov-report=html

# Test isolation Kernel uniquement (ADR-002)
pytest tests/api/test_kernel_isolation_api.py -v
```

## Endpoints (117 total)

| Router | Prefix | Endpoints | Rôles |
|--------|--------|-----------|-------|
| auth | /api/v1/auth | 10 | public/all |
| users | /api/v1/users | 9 | administrateur |
| roles | /api/v1/roles | 3 | administrateur |
| claims | /api/v1/claims | 17 | gestionnaire/auditeur |
| analyze | /api/v1/analyze | 4 | gestionnaire+ |
| audit | /api/v1/audit | 6 | gestionnaire/auditeur |
| escalations | /api/v1/escalations | 6 | gestionnaire/auditeur |
| models | /api/v1/models | 7 | administrateur/expert |
| drift | /api/v1/drift | 5 | expert/administrateur |
| retraining | /api/v1/retraining | 6 | expert/administrateur |
| modules | /api/v1/modules | 10 | expert/administrateur |
| graph | /api/v1/graph | 4 | auditeur/administrateur |
| referentiels | /api/v1/referentiels | 13 | gestionnaire+ |
| analytics | /api/v1/analytics | 5 | all |
| reports | /api/v1/reports | 5 | auditeur/administrateur |
| admin | /api/v1/admin | 6 | administrateur |
| health | / | 1 | public |

## Règles d'architecture

- **ADR-002 Kernel isolation** : `analyze_service.py` utilise **uniquement** `PluginRegistry.get(branch)`.
  Jamais d'import direct d'un module métier par nom concret.
- **IMP-007** : Aucun fichier > 400 lignes.
- **DT-AUDIT** : `core/audit_logger.py` implémenté (session DB indépendante).
- **Service Layer** : Router → Service → DB. Aucune logique SQL dans les routers.

## Références académiques

- [Liu2008] Liu, F.T., Ting, K.M., Zhou, Z.H. — Isolation Forest
- [Blondel2008] Blondel, V.D. et al. — Louvain community detection
- [Gama2014] Gama, J. et al. — Survey on concept drift adaptation
