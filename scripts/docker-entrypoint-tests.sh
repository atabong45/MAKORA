#!/bin/bash
# ============================================================
# scripts/docker-entrypoint-tests.sh
# Point d'entrée du service `tests` dans Docker Compose.
# 1. Attend que PostgreSQL soit prêt
# 2. Crée la base makora_test si elle n'existe pas
# 3. Lance les migrations (create_all)
# 4. Lance pytest avec le scope demandé
#
# Variables d'environnement attendues :
#   DATABASE_URL      = postgresql://makora:makora@postgres:5432/makora_test
#   TEST_SCOPE        = "all" | "api" | "unit" | "integration" (défaut: all)
# ============================================================
set -euo pipefail

# ── Couleurs pour lisibilité ─────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[MAKORA-TESTS]${NC} $*"; }
warn() { echo -e "${YELLOW}[MAKORA-TESTS]${NC} $*"; }
err()  { echo -e "${RED}[MAKORA-TESTS]${NC} $*"; exit 1; }

# ── 1. Attendre PostgreSQL ───────────────────────────────────
log "Attente de PostgreSQL sur postgres:5432..."
RETRIES=30
until pg_isready -h postgres -U makora -q 2>/dev/null; do
    RETRIES=$((RETRIES - 1))
    if [ $RETRIES -le 0 ]; then
        err "PostgreSQL non disponible après 30 tentatives — abandon"
    fi
    warn "PostgreSQL pas encore prêt... ($RETRIES tentatives restantes)"
    sleep 2
done
log "PostgreSQL prêt ✓"

# ── 2. Créer la DB de test si absente ────────────────────────
log "Vérification/création de la base makora_test..."
PGPASSWORD=makora psql -h postgres -U makora -tc \
    "SELECT 1 FROM pg_database WHERE datname='makora_test'" \
    | grep -q 1 \
    || PGPASSWORD=makora psql -h postgres -U makora \
       -c "CREATE DATABASE makora_test;" \
    && log "Base makora_test créée ✓" \
    || log "Base makora_test déjà existante ✓"

# ── 3. Migrations (SQLAlchemy create_all) ───────────────────
log "Application des migrations sur makora_test..."
python -c "
import os
os.environ['DATABASE_URL'] = 'postgresql://makora:makora@postgres:5432/makora_test'
from sqlalchemy import create_engine
from core.db.base import Base
# Import explicite de tous les modèles pour que SQLAlchemy les connaisse
from core.db.models.iam import User, Role, Permission, UserRole, RolePermission, UserSession
from core.db.models.sinistres import Claim, ClaimLine, ClaimDocument, OcrExtraction
from core.db.models.pipeline import ModelVersion, ProductionDeployment, AnalysisRun, Analysis, ShapContribution
from core.db.models.hitl_graph import FraudCommunity, CommunityMember, Decision, Escalation
from core.db.models.monitoring import DriftReport, DriftFeatureMetric, RetrainingRequest, AuditLog, ExportReport, ModuleConfig, RcaRuleSnapshot
from core.db.models.referentiels import Branch, Insured, Practitioner, Garage, Employer, InsuredEmployer, ReferencePrice
engine = create_engine('postgresql://makora:makora@postgres:5432/makora_test')
Base.metadata.create_all(bind=engine)
print('Migrations OK')
"
log "Migrations appliquées ✓"

# ── 4. Seeding des données de test ──────────────────────────
log "Seeding des utilisateurs de test..."
python -c "
import os, uuid, bcrypt
os.environ['DATABASE_URL'] = 'postgresql://makora:makora@postgres:5432/makora_test'
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.db.models.iam import User, Role, UserRole

engine = create_engine('postgresql://makora:makora@postgres:5432/makora_test')
Session = sessionmaker(bind=engine)
db = Session()

def hash_pwd(p):
    return bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

roles_data = [
    ('administrateur', 'Administrateur Systeme',             'Acces total'),
    ('gestionnaire',   'Gestionnaire de Sinistres',          'Gestion des sinistres'),
    ('auditeur',       'Auditeur / Responsable Anti-Fraude', 'Lecture seule + validation'),
    ('data_scientist', 'Data Scientist',                     'Acces ML et modeles'),
]
roles = {}
for name, display_name, desc in roles_data:
    role = db.query(Role).filter(Role.name == name).first()
    if not role:
        role = Role(id=uuid.uuid4(), name=name, display_name=display_name, description=desc)
        db.add(role)
    roles[name] = role
db.flush()

users_data = [
    ('admin',         'admin@makora.cm',   'Admin1234!', 'Administrateur MAKORA', 'administrateur'),
    ('gestionnaire1', 'gest1@makora.cm',   'Test1234!',  'Gestionnaire Test',     'gestionnaire'),
    ('auditeur1',     'audit1@makora.cm',  'Test1234!',  'Auditeur Test',         'auditeur'),
    ('datascientist1','ds1@makora.cm',     'Test1234!',  'Data Scientist Test',   'data_scientist'),
]
for username, email, pwd, full_name, role_name in users_data:
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(
            id=uuid.uuid4(), username=username, email=email,
            full_name=full_name, password_hash=hash_pwd(pwd), is_active=True
        )
        db.add(user)
        db.flush()
        if role_name in roles:
            db.add(UserRole(user_id=user.id, role_id=roles[role_name].id, granted_by=user.id))

db.commit()
db.close()
print('Seed OK')
"
log "Seeding termine ✓"

# ── 5. Lancer pytest ─────────────────────────────────────────
TEST_SCOPE="${TEST_SCOPE:-all}"
log "Lancement des tests — scope: ${TEST_SCOPE}"

case "$TEST_SCOPE" in
    api)
        pytest tests/api/ -v --tb=short -p no:cov
        ;;
    authenticated)
        pytest tests/api/authenticated/ -v --tb=short -p no:cov
        ;;
    unit)
        pytest tests/unit/ -v --tb=short -p no:cov
        ;;
    integration)
        pytest tests/integration/ -v --tb=short -p no:cov
        ;;
    kernel)
        pytest tests/api/test_kernel_isolation_api.py -v --tb=short -p no:cov
        ;;
    all)
        pytest tests/ -v --tb=short -p no:cov
        ;;
    *)
        err "TEST_SCOPE invalide: ${TEST_SCOPE}. Valeurs: all | api | authenticated | unit | integration | kernel"
        ;;
esac
 
