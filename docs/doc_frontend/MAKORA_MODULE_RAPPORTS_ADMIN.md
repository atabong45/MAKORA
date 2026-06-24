# MAKORA — Modules Rapports & Administration — Spécification d'implémentation
> **Document :** MAKORA_MODULE_RAPPORTS_ADMIN.md
> **Chantier :** 2 — Zoom module
> **Date :** Juin 2026
> **Auteur :** ATABONG EFON STEPHANE FRITZ
> **Rôles concernés :** Rapports : A · ADM — Administration : ADM uniquement
> **Pages :** 6 · **Priorité :** 🟡 FE-10 / 🟠 FE-11

> Conventions communes : voir `MAKORA_MODULE_DASHBOARD.md`.

---

## Vue d'ensemble

Ce fichier couvre deux modules de gouvernance regroupés car peu volumineux : **Rapports** (génération d'exports pour les auditeurs) et **Administration** (gestion des utilisateurs, rôles, et système — réservée à l'admin).

### Pages

| # | Module | Route | Titre | Rôles |
|---|---|---|---|---|
| 1 | Rapports | `/reports` | Hub rapports & exports | A, ADM |
| 2 | Admin | `/admin/users` | Gestion utilisateurs | ADM |
| 3 | Admin | `/admin/users/[id]` | Profil utilisateur admin | ADM |
| 4 | Admin | `/admin/roles` | Rôles & permissions | ADM |
| 5 | Admin | `/admin/system` | État du système | ADM |
| 6 | Admin | `/admin/logs` | Journal d'activité | ADM |

---

# MODULE RAPPORTS

## Page 1 — Hub rapports & exports (`/reports`)

### Rôles : A · ADM

### Rôle métier

Générer et télécharger des rapports d'export pour analyse externe, reporting, ou archivage. Les exports sont générés en tâche de fond (BackgroundTask) pour gérer les gros volumes.

### Layout

```
┌─────────────────────────────────────────────────────┐
│ Formulaire de génération                             │
├─────────────────────────────────────────────────────┤
│ Historique des exports (avec statut + téléchargement)│
└─────────────────────────────────────────────────────┘
```

### Formulaire de génération

| Champ | Valeurs |
|---|---|
| Type de rapport | `audit_decisions` · `anomaly_summary` · `drift_history` · `community_fraud` |
| Format | CSV · XLSX · JSON |
| Période | date_from / date_to |
| Branche | Toutes ou spécifique (optionnel) |
| Décision (filtre) | optionnel — PENDING/CONFIRMED/REJECTED/ESCALATED |

### Historique des exports

| Colonne | Source |
|---|---|
| ID | `id` |
| Type | `report_type` |
| Format | `file_format` |
| Statut | PENDING / GENERATING / READY / FAILED |
| Lignes | `row_count` |
| Date | `created_at` |
| Action | `Télécharger` (si READY) |

### Endpoints consommés

- `POST /reports/export` — crée la demande (202 Accepted, génération async)
- `GET /reports/exports` — liste des exports de l'utilisateur
- `GET /reports/exports/{export_id}` — statut d'un export (polling)
- `GET /reports/exports/{export_id}/download` — téléchargement
- `GET /reports/stats/global` — stats globales

### UX décisions

- L'export est asynchrone : afficher le statut `GENERATING` avec polling toutes les 3s jusqu'à `READY` ou `FAILED`.
- Bouton "Télécharger" désactivé tant que l'export n'est pas READY.
- Un export n'est visible que par l'utilisateur qui l'a demandé (`requested_by`).

### Composants

| Composant | Chemin |
|---|---|
| `<ExportReportForm>` | `features/reports/ExportReportForm.tsx` |
| `<ExportHistoryTable>` | `features/reports/ExportHistoryTable.tsx` |

---

# MODULE ADMINISTRATION

> Toutes les pages sont réservées au rôle ADM. La sidebar masque entièrement la section pour les autres rôles.

## Page 2 — Gestion des utilisateurs (`/admin/users`)

### Rôles : ADM

### Layout

Filtres + tableau + bouton "Créer un utilisateur".

### Filtres

`is_active` · rôle · recherche libre (nom, email, username).

### Colonnes

| Colonne | Source |
|---|---|
| Avatar | initiales |
| Nom | `full_name` |
| Username | `username` (mono) |
| Email | `email` |
| Rôles | pills |
| Statut | actif / suspendu |
| Dernière connexion | `last_login` |
| Actions | `Voir` · `Désactiver` · `Réinitialiser mdp` |

### Actions

- `Voir profil` → `/admin/users/[id]`
- `Désactiver` → `DELETE /users/{id}` (soft delete, `is_active=false`)
- `Réactiver` → `POST /users/{id}/reactivate`
- `Réinitialiser mdp` → `PATCH /users/{id}/password`
- `+ Créer un utilisateur` → modal formulaire → `POST /users/`

### Endpoints consommés

- `GET /users/` · `POST /users/` · `PATCH /users/{id}` · `DELETE /users/{id}`
- `POST /users/{id}/reactivate` · `POST /users/{id}/roles` · `DELETE /users/{id}/roles/{role_id}`

### UX décisions

- **Jamais de suppression dure** : la désactivation passe par `is_active=false` (conformité audit trail). L'UI parle de "désactiver" / "réactiver", jamais de "supprimer".
- Confirmation obligatoire avant désactivation.

---

## Page 3 — Profil utilisateur admin (`/admin/users/[id]`)

### Rôles : ADM

### Sections

- Informations personnelles (éditable)
- Rôles assignés (ajout/retrait depuis ici)
- Sessions actives de l'utilisateur
- Historique d'activité (depuis `audit_logs`)

### Endpoints consommés

- `GET /users/{id}` · `PATCH /users/{id}` · `PATCH /users/{id}/password`
- `POST /users/{id}/roles` · `DELETE /users/{id}/roles/{role_id}`

---

## Page 4 — Rôles & permissions (`/admin/roles`)

### Rôles : ADM

> Lecture seule en V1 — visualiser les rôles et leurs permissions (les rôles sont fixes, définis dans le seed).

### Layout

4 cartes — une par rôle (G, A, E, ADM).

### Contenu de chaque carte

- Nom du rôle + description
- Liste des permissions groupées par domaine (IAM / Claims / Audit / ML / Admin)
- Nombre d'utilisateurs ayant ce rôle

### Endpoints consommés

- `GET /roles/` · `GET /roles/{role_id}` · `GET /roles/permissions`

---

## Page 5 — État du système (`/admin/system`)

### Rôles : ADM

### Rôle métier

Monitoring technique de l'infrastructure et configuration des branches.

### Layout

Grille de statuts services + configuration branches + lien journal.

### Statuts services

| Service | Indicateur |
|---|---|
| API FastAPI | ● UP — uptime % |
| Ollama (Mistral) | ● UP — Mistral 7B chargé |
| PostgreSQL | ● UP — latency ms |
| Redis/Celery | ● UP — tâches en file |
| Modèles ML | SANTÉ vX actif · AUTO vX actif |

### Configuration branches (table éditable)

| Colonne | Source |
|---|---|
| Branche | code |
| Contamination | éditable |
| Score alert | éditable |
| Score block | éditable |
| Statut | actif / inactif |
| Actions | `PATCH /admin/branches/{code}` · toggle |

### Endpoints consommés

- `GET /admin/system` · `GET /health`
- `GET /admin/branches` · `GET /admin/branches/{code}`
- `PATCH /admin/branches/{code}` · `PATCH /admin/branches/{code}/toggle`

---

## Page 6 — Journal d'activité (`/admin/logs`)

### Rôles : ADM

### Layout

Filtres + tableau d'audit immuable.

### Filtres

User · action · resource · plage de dates.

### Colonnes

User | Action | Resource | Date.

### Endpoint consommé

- `GET /admin/activity-log`

### UX décisions

- Le journal est **immuable** (Row Level Security côté PostgreSQL). L'UI ne propose aucune action de modification — lecture seule stricte.

---

## Composants à créer pour l'administration

| Composant | Chemin |
|---|---|
| `<UserTable>` | `features/admin/UserTable.tsx` |
| `<UserCreateModal>` | `features/admin/UserCreateModal.tsx` |
| `<UserDetailPanel>` | `features/admin/UserDetailPanel.tsx` |
| `<RoleCard>` | `features/admin/RoleCard.tsx` |
| `<SystemStatusGrid>` | `features/admin/SystemStatusGrid.tsx` |
| `<BranchConfigTable>` | `features/admin/BranchConfigTable.tsx` |
| `<ActivityLogTable>` | `features/admin/ActivityLogTable.tsx` |

---

## Query keys

```typescript
export const REPORTS_KEYS = {
  all: ['reports'] as const,
  exports: () => [...REPORTS_KEYS.all, 'exports'] as const,
  export: (id: string) => [...REPORTS_KEYS.all, 'export', id] as const,
};
export const ADMIN_KEYS = {
  all: ['admin'] as const,
  users: (f: object) => [...ADMIN_KEYS.all, 'users', f] as const,
  user: (id: string) => [...ADMIN_KEYS.all, 'user', id] as const,
  roles: () => [...ADMIN_KEYS.all, 'roles'] as const,
  system: () => [...ADMIN_KEYS.all, 'system'] as const,
  branches: () => [...ADMIN_KEYS.all, 'branches'] as const,
  logs: (f: object) => [...ADMIN_KEYS.all, 'logs', f] as const,
};
```

---

## Flux de navigation

```
/dashboard (widget activité ADM) ──► /admin/system
/admin/users ──► /admin/users/[id]
/admin/system ──► /admin/logs
/reports ──(export prêt)──► téléchargement fichier
```

---

*MAKORA_MODULE_RAPPORTS_ADMIN.md — Juin 2026 — ATABONG EFON STEPHANE FRITZ*
