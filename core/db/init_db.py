"""
MODULE : core/db/init_db.py
DESCRIPTION : Script d'initialisation — crée les tables et insère les données seed.

Usage :
    python -m core.db.init_db
    # ou depuis l'API au démarrage (lifespan FastAPI)

ORDRE D'EXÉCUTION :
    1. create_tables()  — DDL : crée toutes les tables si elles n'existent pas
    2. seed_branches()  — Données initiales : 4 branches (sante, auto, vie, agricole)
    3. seed_roles()     — Données initiales : 4 rôles système
"""

from __future__ import annotations

from core.db.base import Base, engine, SessionLocal
# Import de tous les modèles pour que Base.metadata les connaisse
from core.db.models import *  # noqa: F401, F403
from core.logging_config import get_logger

logger = get_logger(__name__)


def create_tables() -> None:
    """Crée toutes les tables définies dans les modèles SQLAlchemy."""
    Base.metadata.create_all(bind=engine)
    table_count = len(Base.metadata.tables)
    logger.info("Base de données initialisée — %d tables créées.", table_count)
    print(f"✅ {table_count} tables créées.")


def seed_branches() -> None:
    """Insère les 4 branches initiales si elles n'existent pas."""
    from core.db.models.referentiels import Branch

    db = SessionLocal()
    try:
        branches_data = [
            dict(code="sante",    display_name="Assurance Santé",
                 is_active=True,  contamination_threshold=0.068,
                 anomaly_score_alert=0.65, anomaly_score_block=0.90),
            dict(code="auto",     display_name="Assurance Automobile",
                 is_active=True,  contamination_threshold=0.080,
                 anomaly_score_alert=0.65, anomaly_score_block=0.90),
            dict(code="vie",      display_name="Assurance Vie",
                 is_active=False, contamination_threshold=0.080,
                 anomaly_score_alert=0.65, anomaly_score_block=0.90),
            dict(code="agricole", display_name="Assurance Agricole",
                 is_active=False, contamination_threshold=0.080,
                 anomaly_score_alert=0.65, anomaly_score_block=0.90),
        ]
        existing_codes = {b.code for b in db.query(Branch).all()}
        new_branches = [
            Branch(**d) for d in branches_data if d["code"] not in existing_codes
        ]
        if new_branches:
            db.add_all(new_branches)
            db.commit()
            logger.info("%d branches insérées.", len(new_branches))
            print(f"✅ {len(new_branches)} branches insérées.")
        else:
            print("ℹ️  Branches déjà présentes — skip.")
    finally:
        db.close()


def seed_roles() -> None:
    """Insère les 4 rôles système initiaux si ils n'existent pas."""
    from core.db.models.iam import Role

    db = SessionLocal()
    try:
        roles_data = [
            dict(
                name="gestionnaire",
                display_name="Gestionnaire de Sinistres",
                description="Analyse les dossiers, valide ou rejette les alertes IA.",
            ),
            dict(
                name="auditeur",
                display_name="Auditeur / Responsable Anti-Fraude",
                description="Investigue les cas escaladés, exporte les rapports d'audit.",
            ),
            dict(
                name="administrateur",
                display_name="Administrateur Système",
                description=(
                    "Déploie les modèles, configure les modules, "
                    "surveille le drift et gère les utilisateurs."
                ),
            ),
            dict(
                name="expert_metier",
                display_name="Expert Métier",
                description="Rédige et maintient les règles RCA dans les fichiers YAML.",
            ),
        ]
        existing_names = {r.name for r in db.query(Role).all()}
        new_roles = [
            Role(**d) for d in roles_data if d["name"] not in existing_names
        ]
        if new_roles:
            db.add_all(new_roles)
            db.commit()
            logger.info("%d rôles insérés.", len(new_roles))
            print(f"✅ {len(new_roles)} rôles insérés.")
        else:
            print("ℹ️  Rôles déjà présents — skip.")
    finally:
        db.close()


def init_db() -> None:
    """Point d'entrée principal — exécute toutes les étapes d'initialisation."""
    print("🔧 Initialisation de la base de données MAKORA...")
    create_tables()
    seed_branches()
    seed_roles()
    print("✅ Base de données prête.")


if __name__ == "__main__":
    init_db()
