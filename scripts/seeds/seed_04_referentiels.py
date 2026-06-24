"""
MODULE : scripts/seeds/seed_04_referentiels.py
DESCRIPTION : Seed de la mercuriale de référence CIMA (prix de base).

Contexte camerounais :
  - Nomenclature ASAC (santé) et CIMA (auto)
  - Devise principale : XAF (1 EUR = 655.957 XAF)

Modèle ReferencePrice :
  - branch_id    : UUID FK → branches.id
  - code_acte    : str
  - prix_ref_xaf : float
  - prix_ref_eur : float

Idempotent : skip si (branch_id, code_acte) déjà présent.
"""
from __future__ import annotations
import uuid
from sqlalchemy.orm import Session


PRICES_SANTE = [
    ("ASAC_C_001", "Consultation generaliste",         5_000,    7.62),
    ("ASAC_C_002", "Consultation specialiste",        10_000,   15.24),
    ("ASAC_C_003", "Consultation urgence",            15_000,   22.87),
    ("ASAC_B_001", "Bilan biologique standard",       20_000,   30.49),
    ("ASAC_B_002", "Numeration formule sanguine NFS",  8_000,   12.20),
    ("ASAC_B_003", "Glycemie a jeun",                  3_000,    4.57),
    ("ASAC_I_001", "Radiographie thoracique",         25_000,   38.11),
    ("ASAC_I_002", "Echographie abdominale",          45_000,   68.60),
    ("ASAC_I_003", "Scanner cerebral",               150_000,  228.67),
    ("ASAC_P_001", "Hospitalisation jour chambre std",30_000,   45.73),
]

PRICES_AUTO = [
    ("CIMA_MO_001", "Main oeuvre carrosserie heure",   15_000,   22.87),
    ("CIMA_MO_002", "Main oeuvre mecanique heure",     12_000,   18.29),
    ("CIMA_PI_001", "Pare-brise standard remplacement",120_000, 182.94),
    ("CIMA_PI_002", "Retroviseur exterieur remplacement",35_000, 53.36),
    ("CIMA_EX_001", "Expertise vehicule rapport complet",50_000, 76.22),
]


def run(db: Session) -> dict:
    from core.db.models.referentiels import Branch, ReferencePrice

    stats = {"sante": 0, "auto": 0, "skipped": 0}
    valid_from = __import__("datetime").date(2025, 1, 1)

    # Récupérer les UUIDs des branches
    branch_sante = db.query(Branch).filter(Branch.code == "sante").first()
    branch_auto  = db.query(Branch).filter(Branch.code == "auto").first()

    if not branch_sante or not branch_auto:
        raise RuntimeError("Branches sante/auto introuvables — lancez seed_02_branches.py d'abord")

    # Actes santé
    for code_acte, libelle, prix_xaf, prix_eur in PRICES_SANTE:
        existing = db.query(ReferencePrice).filter(
            ReferencePrice.branch_id == branch_sante.id,
            ReferencePrice.code_acte == code_acte,
        ).first()
        if existing:
            stats["skipped"] += 1
            continue
        db.add(ReferencePrice(
            id=uuid.uuid4(),
            branch_id=branch_sante.id,
            code_acte=code_acte,
            libelle=libelle,
            prix_ref_xaf=prix_xaf,
            prix_ref_eur=prix_eur,
            nomenclature="ASAC",
            valid_from=valid_from,
            devise_principale="XAF",
        ))
        stats["sante"] += 1

    # Barèmes auto
    for code_acte, libelle, prix_xaf, prix_eur in PRICES_AUTO:
        existing = db.query(ReferencePrice).filter(
            ReferencePrice.branch_id == branch_auto.id,
            ReferencePrice.code_acte == code_acte,
        ).first()
        if existing:
            stats["skipped"] += 1
            continue
        db.add(ReferencePrice(
            id=uuid.uuid4(),
            branch_id=branch_auto.id,
            code_acte=code_acte,
            libelle=libelle,
            prix_ref_xaf=prix_xaf,
            prix_ref_eur=prix_eur,
            nomenclature="CIMA",
            valid_from=valid_from,
            devise_principale="XAF",
        ))
        stats["auto"] += 1

    db.commit()
    return stats


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from core.db.base import SessionLocal
    db = SessionLocal()
    try:
        stats = run(db)
        print(f"Prix sante (ASAC) : {stats['sante']} inseres")
        print(f"Prix auto  (CIMA) : {stats['auto']} inseres")
        print(f"Deja presents     : {stats['skipped']}")
    finally:
        db.close()