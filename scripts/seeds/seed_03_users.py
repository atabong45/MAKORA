"""
MODULE : scripts/seeds/seed_03_users.py
DESCRIPTION : Seed des utilisateurs de démo MAKORA.

Utilisateurs créés :
  - admin          : administrateur système (mot de passe : Admin1234!)
  - gestionnaire1  : gestionnaire sinistres (mot de passe : Test1234!)
  - auditeur1      : auditeur anti-fraude   (mot de passe : Test1234!)
  - expert1        : expert métier YAML     (mot de passe : Test1234!)
  - datascientist1 : data scientist ML      (mot de passe : Test1234!)

Note bcrypt : utilisation directe de la lib bcrypt (pas passlib)
pour éviter l'incompatibilité bcrypt>=4.0 / passlib 1.7.4.

Idempotent : skip si username déjà présent.
"""
from __future__ import annotations
import uuid
import bcrypt
from sqlalchemy.orm import Session


DEMO_USERS = [
    {
        "username":  "admin",
        "email":     "admin@makora.cm",
        "password":  "Admin1234!",
        "full_name": "Administrateur MAKORA",
        "role":      "administrateur",
    },
    {
        "username":  "gestionnaire1",
        "email":     "gest1@makora.cm",
        "password":  "Test1234!",
        "full_name": "Jean-Pierre Gestionnaire",
        "role":      "gestionnaire",
    },
    {
        "username":  "auditeur1",
        "email":     "audit1@makora.cm",
        "password":  "Test1234!",
        "full_name": "Marie Auditrice",
        "role":      "auditeur",
    },
    {
        "username":  "expert1",
        "email":     "expert1@makora.cm",
        "password":  "Test1234!",
        "full_name": "Paul Expert Metier",
        "role":      "expert_metier",
    },
    {
        "username":  "datascientist1",
        "email":     "ds1@makora.cm",
        "password":  "Test1234!",
        "full_name": "Alice Data Scientist",
        "role":      "data_scientist",
    },
]


def _hash_password(plain: str) -> str:
    """Hash bcrypt direct — compatible bcrypt >= 4.0."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def run(db: Session) -> dict:
    from core.db.models.iam import User, Role, UserRole

    stats = {"created": 0, "skipped": 0, "role_missing": []}

    role_map = {r.name: r for r in db.query(Role).all()}

    for data in DEMO_USERS:
        existing = db.query(User).filter(User.username == data["username"]).first()
        if existing:
            stats["skipped"] += 1
            continue

        user = User(
            id=uuid.uuid4(),
            username=data["username"],
            email=data["email"],
            full_name=data["full_name"],
            password_hash=_hash_password(data["password"]),
            is_active=True,
        )
        db.add(user)
        db.flush()

        role = role_map.get(data["role"])
        if role:
            if data["role"] == "administrateur":
                granted_by = user.id
            else:
                admin = db.query(User).filter(User.username == "admin").first()
                granted_by = admin.id if admin else user.id

            db.add(UserRole(
                user_id=user.id,
                role_id=role.id,
                granted_by=granted_by,
            ))
        else:
            stats["role_missing"].append(data["role"])

        stats["created"] += 1

    db.commit()
    return stats


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from core.db.base import SessionLocal
    db = SessionLocal()
    try:
        stats = run(db)
        print(f"Utilisateurs crees  : {stats['created']}")
        print(f"Deja presents       : {stats['skipped']}")
        if stats["role_missing"]:
            print(f"Roles manquants : {stats['role_missing']}")
    finally:
        db.close()