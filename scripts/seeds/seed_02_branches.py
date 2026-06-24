"""
MODULE : scripts/seeds/seed_02_branches.py
DESCRIPTION : Seed des branches d'assurance MAKORA.

Seuils contamination issus de l'expérience H0 Phase 2 :
  - sante    : 0.068 (validé sur dataset_sante_v1)
  - auto     : 0.080 (validé sur dataset_auto_v1)
  - vie      : 0.080 (conception seulement — Phase 4)
  - agricole : 0.080 (conception seulement — Phase 4)

Référence : [Bauder2017] taux fraude estimé 3-10% en assurance.
Idempotent : skip si déjà présent.
"""
from __future__ import annotations
import uuid
from sqlalchemy.orm import Session


BRANCHES = [
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


def run(db: Session) -> dict:
    from core.db.models.referentiels import Branch

    stats = {"branches": 0, "skipped": 0}
    existing_codes = {b.code for b in db.query(Branch).all()}

    for data in BRANCHES:
        if data["code"] in existing_codes:
            stats["skipped"] += 1
            continue
        branch = Branch(id=uuid.uuid4(), **data)
        db.add(branch)
        stats["branches"] += 1

    db.commit()
    return stats


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from core.db.base import SessionLocal
    db = SessionLocal()
    try:
        stats = run(db)
        print(f"✅ Branches : {stats['branches']} insérées, {stats['skipped']} déjà présentes")
    finally:
        db.close()