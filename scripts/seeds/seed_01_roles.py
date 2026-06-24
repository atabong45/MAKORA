"""
MODULE : scripts/seeds/seed_01_roles.py
DESCRIPTION : Seed des rôles et permissions RBAC MAKORA.

Rôles définis dans le CDC :
  - administrateur  : accès total
  - gestionnaire    : gestion sinistres
  - auditeur        : lecture + validation HITL
  - expert_metier   : modification YAML/règles RCA
  - data_scientist  : accès ML, modèles, drift

Idempotent : skip si déjà présent.
"""
from __future__ import annotations
import uuid
from sqlalchemy.orm import Session


ROLES = [
    {
        "name": "administrateur",
        "display_name": "Administrateur Système",
        "description": "Déploie les modèles, configure les modules, gère les utilisateurs.",
    },
    {
        "name": "gestionnaire",
        "display_name": "Gestionnaire de Sinistres",
        "description": "Analyse les dossiers, valide ou rejette les alertes IA.",
    },
    {
        "name": "auditeur",
        "display_name": "Auditeur / Responsable Anti-Fraude",
        "description": "Investigue les cas escaladés, exporte les rapports d'audit.",
    },
    {
        "name": "expert_metier",
        "display_name": "Expert Métier",
        "description": "Rédige et maintient les règles RCA dans les fichiers YAML.",
    },
    {
        "name": "data_scientist",
        "display_name": "Data Scientist",
        "description": "Accès ML, entraînement, drift monitoring, benchmarks.",
    },
]

# Matrice permissions : resource × action
PERMISSIONS = [
    # Sinistres
    ("claims",    "read",     "Lire les sinistres"),
    ("claims",    "create",   "Créer un sinistre"),
    ("claims",    "update",   "Modifier un sinistre"),
    ("claims",    "delete",   "Supprimer un sinistre"),
    ("claims",    "export",   "Exporter les sinistres"),
    # Analyses ML
    ("analyses",  "read",     "Lire les analyses"),
    ("analyses",  "create",   "Lancer une analyse"),
    ("analyses",  "export",   "Exporter les analyses"),
    # Décisions HITL
    ("decisions", "read",     "Lire les décisions"),
    ("decisions", "create",   "Créer une décision"),
    ("decisions", "validate", "Valider/invalider une décision"),
    # Modèles ML
    ("models",    "read",     "Lire les versions de modèles"),
    ("models",    "create",   "Enregistrer un modèle"),
    ("models",    "deploy",   "Déployer un modèle en production"),
    ("models",    "delete",   "Supprimer un modèle"),
    # Drift & Réentraînement
    ("drift",     "read",     "Lire les rapports de drift"),
    ("drift",     "create",   "Lancer un run de drift"),
    ("retraining","read",     "Lire les demandes de réentraînement"),
    ("retraining","create",   "Créer une demande de réentraînement"),
    ("retraining","update",   "Approuver/rejeter un réentraînement"),
    # Audit
    ("audit",     "read",     "Lire les logs d'audit"),
    ("audit",     "export",   "Exporter les logs d'audit"),
    # Utilisateurs & Rôles
    ("users",     "read",     "Lire les utilisateurs"),
    ("users",     "create",   "Créer un utilisateur"),
    ("users",     "update",   "Modifier un utilisateur"),
    ("users",     "delete",   "Désactiver un utilisateur"),
    # Modules & Référentiels
    ("modules",   "read",     "Lire les modules"),
    ("modules",   "update",   "Modifier la configuration d'un module"),
    ("referentiels", "read",  "Lire les référentiels"),
    ("referentiels", "create","Importer des données de référence"),
    # Analytics & Reports
    ("analytics", "read",     "Lire les analytics"),
    ("reports",   "read",     "Lire les rapports"),
    ("reports",   "create",   "Générer un rapport"),
    ("reports",   "export",   "Exporter un rapport"),
    # Admin système
    ("admin",     "read",     "Lire la configuration système"),
    ("admin",     "update",   "Modifier la configuration système"),
    ("graph",     "read",     "Lire le graphe de fraude"),
]

# Matrice rôle → permissions accordées
ROLE_PERMISSIONS: dict[str, list[tuple[str, str]]] = {
    "administrateur": [
        # Accès total
        ("claims", "read"), ("claims", "create"), ("claims", "update"),
        ("claims", "delete"), ("claims", "export"),
        ("analyses", "read"), ("analyses", "create"), ("analyses", "export"),
        ("decisions", "read"), ("decisions", "create"), ("decisions", "validate"),
        ("models", "read"), ("models", "create"), ("models", "deploy"), ("models", "delete"),
        ("drift", "read"), ("drift", "create"),
        ("retraining", "read"), ("retraining", "create"), ("retraining", "update"),
        ("audit", "read"), ("audit", "export"),
        ("users", "read"), ("users", "create"), ("users", "update"), ("users", "delete"),
        ("modules", "read"), ("modules", "update"),
        ("referentiels", "read"), ("referentiels", "create"),
        ("analytics", "read"),
        ("reports", "read"), ("reports", "create"), ("reports", "export"),
        ("admin", "read"), ("admin", "update"),
        ("graph", "read"),
    ],
    "gestionnaire": [
        ("claims", "read"), ("claims", "create"), ("claims", "update"),
        ("analyses", "read"), ("analyses", "create"),
        ("decisions", "read"), ("decisions", "create"),
        ("audit", "read"),
        ("referentiels", "read"),
        ("analytics", "read"),
        ("reports", "read"),
        ("graph", "read"),
    ],
    "auditeur": [
        ("claims", "read"), ("claims", "export"),
        ("analyses", "read"), ("analyses", "export"),
        ("decisions", "read"), ("decisions", "validate"),
        ("audit", "read"), ("audit", "export"),
        ("referentiels", "read"),
        ("analytics", "read"),
        ("reports", "read"), ("reports", "create"), ("reports", "export"),
        ("graph", "read"),
    ],
    "expert_metier": [
        ("claims", "read"),
        ("analyses", "read"),
        ("decisions", "read"),
        ("modules", "read"), ("modules", "update"),
        ("referentiels", "read"), ("referentiels", "create"),
        ("analytics", "read"),
        ("reports", "read"),
    ],
    "data_scientist": [
        ("claims", "read"),
        ("analyses", "read"), ("analyses", "create"),
        ("models", "read"), ("models", "create"), ("models", "deploy"),
        ("drift", "read"), ("drift", "create"),
        ("retraining", "read"), ("retraining", "create"),
        ("analytics", "read"),
        ("reports", "read"),
        ("graph", "read"),
    ],
}


def run(db: Session) -> dict:
    from core.db.models.iam import Permission, Role, RolePermission

    stats = {"roles": 0, "permissions": 0, "role_permissions": 0}

    # 1. Permissions
    perm_map: dict[tuple, Permission] = {}
    for resource, action, description in PERMISSIONS:
        existing = db.query(Permission).filter(
            Permission.resource == resource,
            Permission.action == action,
        ).first()
        if not existing:
            p = Permission(
                id=uuid.uuid4(),
                code=f"{resource}:{action}",
                resource=resource,
                action=action,
                description=description,
            )
            db.add(p)
            db.flush()
            stats["permissions"] += 1
            perm_map[(resource, action)] = p
        else:
            perm_map[(resource, action)] = existing

    # 2. Rôles
    role_map: dict[str, Role] = {}
    for role_data in ROLES:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            r = Role(id=uuid.uuid4(), **role_data)
            db.add(r)
            db.flush()
            stats["roles"] += 1
            role_map[role_data["name"]] = r
        else:
            role_map[role_data["name"]] = existing

    # 3. Matrice rôle × permissions
    for role_name, perms in ROLE_PERMISSIONS.items():
        role = role_map.get(role_name)
        if not role:
            continue
        for resource, action in perms:
            perm = perm_map.get((resource, action))
            if not perm:
                continue
            existing_rp = db.query(RolePermission).filter(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == perm.id,
            ).first()
            if not existing_rp:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))
                stats["role_permissions"] += 1

    db.commit()
    return stats


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from core.db.base import SessionLocal
    db = SessionLocal()
    try:
        stats = run(db)
        print(f"✅ Rôles : {stats['roles']} insérés")
        print(f"✅ Permissions : {stats['permissions']} insérées")
        print(f"✅ Matrice rôle×permissions : {stats['role_permissions']} liens")
    finally:
        db.close()