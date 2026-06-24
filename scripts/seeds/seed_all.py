"""
MODULE : scripts/seeds/seed_all.py
DESCRIPTION : Orchestrateur de seeding MAKORA.

Ordre d'exécution (respecter les dépendances FK) :
  1. seed_01_roles.py        — rôles + permissions (pas de dépendance)
  2. seed_02_branches.py     — branches assurance  (pas de dépendance)
  3. seed_03_users.py        — utilisateurs        (dépend des rôles)
  4. seed_04_referentiels.py — mercuriale CIMA     (dépend des branches)

Usage :
  docker exec makora_api python scripts/seeds/seed_all.py
  python scripts/seeds/seed_all.py
  python scripts/seeds/seed_all.py --only roles users
"""
from __future__ import annotations

import argparse
import importlib.util
import os
import sys
import time
import traceback

# Racine du projet dans PYTHONPATH
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, ROOT)

# Import au niveau module (obligatoire pour import *)
from core.db.base import SessionLocal, engine, Base  # noqa: E402
from core.db.models.iam import User, Role, Permission, UserRole, RolePermission, UserSession  # noqa: E402, F401
from core.db.models.sinistres import Claim, ClaimLine, ClaimDocument, OcrExtraction  # noqa: E402, F401
from core.db.models.pipeline import ModelVersion, ProductionDeployment, AnalysisRun, Analysis, ShapContribution  # noqa: E402, F401
from core.db.models.hitl_graph import FraudCommunity, CommunityMember, Decision, Escalation  # noqa: E402, F401
from core.db.models.monitoring import DriftReport, DriftFeatureMetric, RetrainingRequest, AuditLog, ExportReport, ModuleConfig, RcaRuleSnapshot  # noqa: E402, F401
from core.db.models.referentiels import Branch, Insured, Practitioner, Garage, Employer, InsuredEmployer, ReferencePrice  # noqa: E402, F401

SEEDS_DIR = os.path.dirname(os.path.abspath(__file__))

SEEDS = [
    ("roles_et_permissions", "seed_01_roles.py"),
    ("branches",             "seed_02_branches.py"),
    ("users",                "seed_03_users.py"),
    ("referentiels",         "seed_04_referentiels.py"),
    ("demo_claims",          "seed_05_demo_claims.py"),
    ("demo_claims v2",          "seed_06_demo_claims_v2.py"),
]


def _header(title: str) -> None:
    print(f"\n{'─' * 50}\n  {title}\n{'─' * 50}")

def _ok(msg: str)   -> None: print(f"  ✅ {msg}")
def _skip(msg: str) -> None: print(f"  ⏭  {msg}")
def _warn(msg: str) -> None: print(f"  ⚠️  {msg}")
def _err(msg: str)  -> None: print(f"  ❌ {msg}")


def run_seed(seed_name: str, seed_file: str, db) -> bool:
    module_path = os.path.join(SEEDS_DIR, seed_file)
    if not os.path.exists(module_path):
        _err(f"Fichier introuvable : {module_path}")
        return False
    try:
        spec = importlib.util.spec_from_file_location(seed_name, module_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        stats = mod.run(db)
        for k, v in stats.items():
            if isinstance(v, list) and v:
                _warn(f"{k}: {v}")
            elif isinstance(v, int) and v > 0:
                _ok(f"{k}: {v}")
            else:
                _skip(f"{k}: 0 (déjà présents)")
        return True
    except Exception as e:
        _err(f"Échec : {e}")
        traceback.print_exc()
        return False


def main(only: list[str] | None = None) -> None:
    print("\n" + "═" * 50)
    print("  🌱 MAKORA — Seeding de la base de données")
    print("═" * 50)

    _header("Étape 0 — Création des tables")
    Base.metadata.create_all(bind=engine)
    _ok(f"{len(Base.metadata.tables)} tables vérifiées / créées")

    db = SessionLocal()
    results: dict[str, bool] = {}

    try:
        for seed_name, seed_file in SEEDS:
            if only and not any(o in seed_name for o in only):
                continue
            _header(f"Seed : {seed_name}")
            t0 = time.time()
            results[seed_name] = run_seed(seed_name, seed_file, db)
            print(f"  ⏱  {time.time() - t0:.2f}s")
    finally:
        db.close()

    print("\n" + "═" * 50)
    print("  📊 Résumé")
    print("═" * 50)
    all_ok = all(results.values())
    for name, ok in results.items():
        print(f"  {'✅' if ok else '❌'}  {name}")

    if all_ok:
        print("\n  🎉 Seeding terminé avec succès\n")
    else:
        print("\n  ⚠️  Certains seeds ont échoué\n")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAKORA — Seed orchestrator")
    parser.add_argument("--only", nargs="+", default=None,
                        help="Ex: --only roles users")
    args = parser.parse_args()
    main(only=args.only)
