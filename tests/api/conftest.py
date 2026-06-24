"""
MODULE : tests/api/conftest.py
DESCRIPTION : Fixtures pytest pour les tests API MAKORA Phase 3.

DÉCISIONS DE CONCEPTION :
- PostgreSQL exclusivement (pas SQLite).
- bcrypt direct (>=4.0) — suppression passlib (DT-AUTH-001 corrigé).
- Scope "session" pour engine et client.
- Rate limiting désactivé via TESTING=true dans docker-compose.yml.
- Branches seedées dans la DB de test (requis pour /analyze, /retraining,
  /referentiels/prices/{branch}).
"""
from __future__ import annotations

import os
import uuid
from typing import Generator

import bcrypt as _bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

_DEFAULT = "postgresql://makora:makora@localhost:5432/makora_test"
TEST_DB_URL = os.environ.get("DATABASE_URL", _DEFAULT)


def _hash(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode("utf-8"), _bcrypt.gensalt(rounds=12)).decode("utf-8")


@pytest.fixture(scope="session")
def engine():
    eng = create_engine(TEST_DB_URL, pool_pre_ping=True)

    from core.db.base import Base  # noqa: F401
    from core.db.models.iam import (  # noqa: F401
        User, Role, Permission, UserRole, RolePermission, UserSession,
    )
    from core.db.models.sinistres import (  # noqa: F401
        Claim, ClaimLine, ClaimDocument, OcrExtraction,
    )
    from core.db.models.pipeline import (  # noqa: F401
        ModelVersion, ProductionDeployment, AnalysisRun, Analysis, ShapContribution,
    )
    from core.db.models.hitl_graph import (  # noqa: F401
        FraudCommunity, CommunityMember, Decision, Escalation,
    )
    from core.db.models.monitoring import (  # noqa: F401
        DriftReport, DriftFeatureMetric, RetrainingRequest,
        AuditLog, ExportReport, ModuleConfig, RcaRuleSnapshot,
    )
    from core.db.models.referentiels import (  # noqa: F401
        Branch, Insured, Practitioner, Garage,
        Employer, InsuredEmployer, ReferencePrice,
    )

    Base.metadata.create_all(bind=eng)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def SessionLocal(engine):
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="function")
def db(SessionLocal) -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session", autouse=True)
def seed_test_data(engine, SessionLocal):
    """Insère rôles, utilisateurs ET branches de test. Idempotent."""
    from core.db.models.iam import User, Role, UserRole
    from core.db.models.referentiels import Branch

    session = SessionLocal()
    try:
        # ── Rôles ────────────────────────────────────────────────────────────
        roles_def = [
            ("administrateur",  "Administrateur Système",             "Accès total"),
            ("gestionnaire",    "Gestionnaire de Sinistres",          "Gestion sinistres"),
            ("auditeur",        "Auditeur / Responsable Anti-Fraude", "Lecture + validation"),
            ("expert_metier",   "Expert Métier YAML",                 "Configuration règles"),
            ("data_scientist",  "Data Scientist",                     "ML et modèles"),
        ]
        roles: dict[str, Role] = {}
        for name, display_name, desc in roles_def:
            role = session.query(Role).filter(Role.name == name).first()
            if not role:
                role = Role(
                    id=uuid.uuid4(),
                    name=name,
                    display_name=display_name,
                    description=desc,
                )
                session.add(role)
            roles[name] = role
        session.flush()

        # ── Utilisateurs ─────────────────────────────────────────────────────
        users_def = [
            ("admin",          "admin@makora.cm",   "Admin1234!",  "Administrateur",   "administrateur"),
            ("gestionnaire1",  "gest1@makora.cm",   "Test1234!",   "Jean-Pierre Gest", "gestionnaire"),
            ("auditeur1",      "audit1@makora.cm",  "Test1234!",   "Marie Auditrice",  "auditeur"),
            ("expert1",        "expert1@makora.cm", "Test1234!",   "Paul Expert",      "expert_metier"),
            ("datascientist1", "ds1@makora.cm",     "Test1234!",   "Alice DS",         "data_scientist"),
        ]
        for username, email, pwd, full_name, role_name in users_def:
            user = session.query(User).filter(User.username == username).first()
            if not user:
                user = User(
                    id=uuid.uuid4(),
                    username=username,
                    email=email,
                    full_name=full_name,
                    password_hash=_hash(pwd),
                    is_active=True,
                )
                session.add(user)
                session.flush()
                if role_name in roles:
                    session.add(UserRole(
                        user_id=user.id,
                        role_id=roles[role_name].id,
                        granted_by=user.id,
                    ))

        # ── Branches ─────────────────────────────────────────────────────────
        # Requis pour /analyze, /retraining, /referentiels/prices/{branch}
        # Contamination [Bauder2017] : taux fraude 3-10% en assurance
        branches_def = [
            {
                "code": "sante",
                "display_name": "Assurance Santé",
                "is_active": True,
                "contamination_threshold": 0.068,
                "anomaly_score_alert": 0.65,
                "anomaly_score_block": 0.90,
            },
            {
                "code": "auto",
                "display_name": "Assurance Automobile",
                "is_active": True,
                "contamination_threshold": 0.080,
                "anomaly_score_alert": 0.65,
                "anomaly_score_block": 0.90,
            },
            {
                "code": "vie",
                "display_name": "Assurance Vie",
                "is_active": False,
                "contamination_threshold": 0.080,
                "anomaly_score_alert": 0.65,
                "anomaly_score_block": 0.90,
            },
            {
                "code": "agricole",
                "display_name": "Assurance Agricole",
                "is_active": False,
                "contamination_threshold": 0.080,
                "anomaly_score_alert": 0.65,
                "anomaly_score_block": 0.90,
            },
        ]
        for bdata in branches_def:
            existing = session.query(Branch).filter(Branch.code == bdata["code"]).first()
            if not existing:
                session.add(Branch(id=uuid.uuid4(), **bdata))

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── TestClient ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def client(engine, SessionLocal) -> Generator:
    from api.main import create_app
    from api.deps.db import get_db

    def override_get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ── Helpers login ─────────────────────────────────────────────────────────────
def _login(client, username: str, password: str) -> str:
    r = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert r.status_code == 200, f"Login {username} échoué : {r.status_code} {r.text}"
    return r.json()["access_token"]


@pytest.fixture(scope="session")
def admin_token(client) -> str:
    return _login(client, "admin", "Admin1234!")


@pytest.fixture(scope="session")
def gestionnaire_token(client) -> str:
    return _login(client, "gestionnaire1", "Test1234!")


@pytest.fixture(scope="session")
def auditeur_token(client) -> str:
    return _login(client, "auditeur1", "Test1234!")


@pytest.fixture(scope="session")
def expert_token(client) -> str:
    return _login(client, "expert1", "Test1234!")


@pytest.fixture(scope="session")
def ds_token(client) -> str:
    return _login(client, "datascientist1", "Test1234!")


@pytest.fixture(scope="session")
def admin_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture(scope="session")
def gestionnaire_headers(gestionnaire_token) -> dict:
    return {"Authorization": f"Bearer {gestionnaire_token}"}


@pytest.fixture(scope="session")
def auditeur_headers(auditeur_token) -> dict:
    return {"Authorization": f"Bearer {auditeur_token}"}


@pytest.fixture(scope="session")
def expert_headers(expert_token) -> dict:
    return {"Authorization": f"Bearer {expert_token}"}


@pytest.fixture(scope="session")
def ds_headers(ds_token) -> dict:
    return {"Authorization": f"Bearer {ds_token}"}