# MAKORA — Rapport Complet des Endpoints API
## Phase 3 · Référence d'implémentation exhaustive · **v2.0**
> Généré le : 09 juin 2026
> Auteur : ATABONG EFON STEPHANE FRITZ
> Basé sur : audit code vs spec v1.0 (30 mai 2026) + code source Phase 3
> Statut : **RÉFÉRENCE OFFICIELLE — SYNCHRONISÉE AVEC LE CODE**

> **CHANGELOG v2.0** (diff vs v1.0 du 30 mai 2026) :
> - Synthèse corrigée : 115 → **118 endpoints** (erreur de comptage v1.0)
> - Admin #113 (`PATCH /admin/branches/{code}`) : marqué **NON IMPLÉMENTÉ** (DT-ADMIN-01)
> - Admin #114 `/toggle` → scindé en **#114a `/activate`** + **#114b `/deactivate`**
> - Admin #115 `/admin/system` → chemin réel : **`/admin/status`**
> - Reports #107 → scindé en **#107a** (métadonnées) + **#107b** (téléchargement binaire)
> - Tests `test_admin.py` : URLs et méthodes HTTP corrigées (voir section 22)

---

## 1. SYNTHÈSE EXÉCUTIVE

| Indicateur | Valeur |
|---|---|
| **Total endpoints implémentés** | **118** |
| Routers (fichiers FastAPI) | **17** |
| Tables DB couvertes | **34 / 34** (100%) |
| Endpoints d'écriture (POST/PATCH/DELETE) | 54 |
| Endpoints de lecture (GET) | 64 |
| Endpoints non implémentés (dette) | **1** (DT-ADMIN-01) |

### Répartition par router

| Router | Prefix | Spec v1.0 | Code réel | Écart |
|---|---|---|---|---|
| auth | `/api/v1/auth` | 10 | 10 | — |
| users | `/api/v1/users` | 9 | 9 | — |
| roles | `/api/v1/roles` | 3 | 3 | — |
| claims | `/api/v1/claims` | 17 | 17 | — |
| analyze | `/api/v1/analyze` | 4 | 4 | — |
| audit | `/api/v1/audit` | 6 | 6 | — |
| escalations | `/api/v1/escalations` | 6 | 6 | — |
| graph | `/api/v1/graph` | 4 | 4 | — |
| models | `/api/v1/models` | 7 | 7 | — |
| drift | `/api/v1/drift` | 5 | 5 | — |
| retraining | `/api/v1/retraining` | 6 | 6 | — |
| modules | `/api/v1/modules` | 10 | 10 | — |
| referentiels | `/api/v1/referentiels` | 13 | 13 | — |
| analytics | `/api/v1/analytics` | 5 | 5 | — |
| reports | `/api/v1/reports` | **5** | **6** | +1 (download scindé) |
| admin | `/api/v1/admin` | **6** | **6** | chemins modifiés |
| health | `/` | 1 | 1 | — |
| **TOTAL** | | **117** | **118** | **+1** |

### Conventions

| Symbole | Signification |
|---|---|
| 🔒 | JWT requis |
| 🌐 | Endpoint public |
| 🔴 CRITIQUE | Bloquant |
| 🟠 HAUTE | Nécessaire MVP |
| 🟡 MOYENNE | Secondaire |
| ⚠️ DT | Dette technique documentée |
| `G` | gestionnaire · `A` auditeur · `ADM` administrateur · `E` expert_metier |

---

## 2. ROUTER `auth` — `/api/v1/auth`

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 1 | `POST` | `/auth/login` | Connexion → access_token JWT 15min + refresh_token | 🌐 | — | 🔴 |
| 2 | `POST` | `/auth/logout` | Révocation refresh_token | 🔒 | all | 🔴 |
| 3 | `POST` | `/auth/refresh` | Renouveler access_token | 🌐 | — | 🔴 |
| 4 | `POST` | `/auth/forgot-password` | Demander reset — JWT 30min | 🌐 | — | 🟠 |
| 5 | `POST` | `/auth/reset-password` | Réinitialiser mdp via token → révoque sessions | 🌐 | — | 🟠 |
| 6 | `POST` | `/auth/change-password` | Changer son propre mdp (vérifie ancien) | 🔒 | all | 🟠 |
| 7 | `GET` | `/auth/me` | Profil connecté + rôles + permissions | 🔒 | all | 🔴 |
| 8 | `PATCH` | `/auth/me` | Modifier nom et email | 🔒 | all | 🟠 |
| 9 | `GET` | `/auth/sessions` | Lister ses sessions actives | 🔒 | all | 🟡 |
| 10 | `DELETE` | `/auth/sessions/{session_id}` | Révoquer une session distante | 🔒 | all | 🟡 |

---

## 3. ROUTER `users` — `/api/v1/users`

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 11 | `GET` | `/users/` | Lister utilisateurs (filtres: is_active, role, search) | 🔒 | ADM | 🟠 |
| 12 | `POST` | `/users/` | Créer compte avec rôle initial | 🔒 | ADM | 🔴 |
| 13 | `GET` | `/users/{user_id}` | Détail + rôles + nb sessions actives | 🔒 | ADM | 🟠 |
| 14 | `PATCH` | `/users/{user_id}` | Modifier full_name, email, is_active | 🔒 | ADM | 🟠 |
| 15 | `DELETE` | `/users/{user_id}` | Soft-delete (is_active=false) + révocation sessions | 🔒 | ADM | 🟠 |
| 16 | `POST` | `/users/{user_id}/reactivate` | Réactiver compte | 🔒 | ADM | 🟡 |
| 17 | `PATCH` | `/users/{user_id}/password` | Forcer reset mdp admin | 🔒 | ADM | 🟠 |
| 18 | `POST` | `/users/{user_id}/roles` | Assigner un rôle | 🔒 | ADM | 🔴 |
| 19 | `DELETE` | `/users/{user_id}/roles/{role_id}` | Retirer un rôle | 🔒 | ADM | 🟠 |

---

## 4. ROUTER `roles` — `/api/v1/roles`

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 20 | `GET` | `/roles/` | Lister les 4 rôles | 🔒 | ADM | 🟠 |
| 21 | `GET` | `/roles/{role_id}` | Détail rôle + permissions | 🔒 | ADM | 🟡 |
| 22 | `GET` | `/roles/permissions` | Toutes les permissions | 🔒 | ADM | 🟡 |

---

## 5. ROUTER `claims` — `/api/v1/claims`
> Cycle de vie : `DRAFT → SUBMITTED → OPEN → CLOSED`

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 23 | `GET` | `/claims/` | Lister sinistres (filtres: branch_code, statut, date_from/to) | 🔒 | G, A, ADM | 🔴 |
| 24 | `POST` | `/claims/` | Créer sinistre (statut=DRAFT) | 🔒 | G, ADM | 🔴 |
| 25 | `GET` | `/claims/{claim_id}` | Détail complet + contrat lié + lignes count | 🔒 | G, A, ADM | 🔴 |
| 26 | `PATCH` | `/claims/{claim_id}` | Modifier (seulement DRAFT ou OPEN) | 🔒 | G, ADM | 🟠 |
| 27 | `POST` | `/claims/{claim_id}/submit` | DRAFT → SUBMITTED → déclenche pipeline DIF | 🔒 | G, ADM | 🔴 |
| 28 | `GET` | `/claims/{claim_id}/lines` | Lister lignes de détail | 🔒 | G, A, ADM | 🟠 |
| 29 | `POST` | `/claims/{claim_id}/lines` | Ajouter une ligne | 🔒 | G, ADM | 🟠 |
| 30 | `PATCH` | `/claims/{claim_id}/lines/{line_id}` | Modifier ligne (DRAFT uniquement) | 🔒 | G, ADM | 🟡 |
| 31 | `DELETE` | `/claims/{claim_id}/lines/{line_id}` | Supprimer ligne (DRAFT uniquement) | 🔒 | G, ADM | 🟡 |
| 32 | `GET` | `/claims/{claim_id}/documents` | Lister documents attachés | 🔒 | G, A, ADM | 🟠 |
| 33 | `POST` | `/claims/{claim_id}/documents` | Uploader document (PDF/JPG/PNG, max 50MB) | 🔒 | G, ADM | 🟠 |
| 34 | `GET` | `/claims/{claim_id}/documents/{doc_id}` | Métadonnées (SHA-256, mime_type, size) | 🔒 | G, A, ADM | 🟡 |
| 35 | `GET` | `/claims/{claim_id}/documents/{doc_id}/download` | Télécharger fichier binaire (streaming) | 🔒 | G, A, ADM | 🟠 |
| 36 | `DELETE` | `/claims/{claim_id}/documents/{doc_id}` | Supprimer document (DRAFT uniquement) | 🔒 | ADM | 🟡 |
| 37 | `POST` | `/claims/{claim_id}/ocr/run` | Déclencher OCR (PaddleOCR + Tesseract + LLM) | 🔒 | G, ADM | 🟠 |
| 38 | `GET` | `/claims/{claim_id}/ocr` | Résultat OCR (confiance, montant, flag_altere) | 🔒 | G, A, ADM | 🟠 |
| 39 | `GET` | `/claims/{claim_id}/analyses` | Historique analyses ML sur ce sinistre | 🔒 | G, A, ADM | 🟠 |

---

## 6. ROUTER `analyze` — `/api/v1/analyze`

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 40 | `POST` | `/analyze/` | Batch JSON → DIF score (brut PyOD) + SHAP + RCA | 🔒 | G, A, ADM | 🔴 |
| 41 | `POST` | `/analyze/upload` | CSV/JSON/PDF multipart (max 50MB) | 🔒 | G, A, ADM | 🟠 |
| 42 | `GET` | `/analyze/runs/{run_id}` | Résultats session (statut, nb_dossiers, nb_anomalies) | 🔒 | G, A, ADM | 🟠 |
| 43 | `GET` | `/analyze/runs` | Historique sessions (filtres: branch, date) | 🔒 | G, A, ADM | 🟡 |

> **Note critique** : `anomaly_score` est une valeur brute PyOD [Xu2023] — PAS bornée [0,1].
> Valeur typique ~0.35. Ne pas ajouter de contrainte `le=1` sur le schéma `AnalysisResult`.

---

## 7. ROUTER `audit` — `/api/v1/audit`

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 44 | `GET` | `/audit/` | Lister analyses (filtres: branch, decision_status, score_min, date) | 🔒 | G, A, ADM | 🔴 |
| 45 | `GET` | `/audit/{analysis_id}` | Détail : score + SHAP top3 + RCA + narration LLM | 🔒 | G, A, ADM | 🔴 |
| 46 | `POST` | `/audit/{analysis_id}/decision` | Enregistrer CONFIRMED/REJECTED/ESCALATED | 🔒 | G, A | 🔴 |
| 47 | `GET` | `/audit/{analysis_id}/decisions` | Historique décisions (immuable) | 🔒 | A, ADM | 🟠 |
| 48 | `GET` | `/audit/{analysis_id}/shap` | Valeurs SHAP complètes (toutes features) | 🔒 | G, A, ADM | 🟠 |
| 49 | `GET` | `/audit/stats` | Stats agrégées dashboard | 🔒 | all | 🔴 |

---

## 8. ROUTER `escalations` — `/api/v1/escalations`

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 50 | `POST` | `/escalations/` | Créer escalade (motif obligatoire) | 🔒 | G | 🟠 |
| 51 | `GET` | `/escalations/` | Lister escalades | 🔒 | A, ADM | 🟠 |
| 52 | `GET` | `/escalations/{escalation_id}` | Détail + analyse + historique | 🔒 | A, ADM | 🟠 |
| 53 | `PATCH` | `/escalations/{escalation_id}/assign` | Assigner à un auditeur | 🔒 | A, ADM | 🟠 |
| 54 | `PATCH` | `/escalations/{escalation_id}/resolve` | Clore avec note (RESOLVED) | 🔒 | A | 🟠 |
| 55 | `GET` | `/escalations/pending` | File d'attente non assignées | 🔒 | A, ADM | 🟡 |

---

## 9. ROUTER `graph` — `/api/v1/graph`
> Référence : [Blondel2008] Louvain community detection.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 56 | `GET` | `/graph/communities` | Lister communautés suspectes (filtres: branch, is_suspicious, size_min) | 🔒 | A, ADM | 🟠 |
| 57 | `GET` | `/graph/communities/{community_id}` | Détail : densité, modularité, suspicion_score | 🔒 | A, ADM | 🟠 |
| 58 | `GET` | `/graph/communities/{community_id}/members` | Membres (type, hash, node_score, is_central) | 🔒 | A, ADM | 🟠 |
| 59 | `GET` | `/graph/runs/{run_id}/communities` | Communautés d'une session d'analyse | 🔒 | A, ADM | 🟡 |

---

## 10. ROUTER `models` — `/api/v1/models`

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 60 | `GET` | `/models/` | Catalogue modèles (filtres: branch, algorithm) | 🔒 | ADM, E | 🟠 |
| 61 | `GET` | `/models/{model_id}` | Détail : F1/AUC/MCC/FPR + feature_names | 🔒 | ADM, E | 🟠 |
| 62 | `POST` | `/models/register` | Enregistrer nouveau modèle post-training | 🔒 | ADM | 🟠 |
| 63 | `GET` | `/models/branch/{branch}/history` | Historique modèles pour une branche | 🔒 | ADM, E | 🟡 |
| 64 | `GET` | `/models/branch/{branch}/current` | Modèle en production | 🔒 | ADM, E, A | 🟠 |
| 65 | `POST` | `/models/deploy` | Déployer en production | 🔒 | ADM | 🟠 |
| 66 | `GET` | `/models/deployments` | Historique déploiements | 🔒 | ADM | 🟡 |

---

## 11. ROUTER `drift` — `/api/v1/drift`
> Référence : [Gama2014]. PSI seuils : STABLE<0.10 < WARNING<0.20 ≤ CRITICAL.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 67 | `GET` | `/drift/status` | Statut drift toutes branches (PSI global) | 🔒 | A, ADM, E | 🔴 |
| 68 | `GET` | `/drift/status/{branch}` | Statut drift détaillé : PSI par feature | 🔒 | A, ADM, E | 🟠 |
| 69 | `GET` | `/drift/history/{branch}` | Chronologie rapports drift | 🔒 | ADM, E | 🟠 |
| 70 | `GET` | `/drift/reports/{report_id}` | Détail rapport : drift_feature_metrics | 🔒 | ADM, E | 🟡 |
| 71 | `POST` | `/drift/run/{branch}` | Déclencher calcul PSI manuel | 🔒 | ADM, E | 🟠 |

---

## 12. ROUTER `retraining` — `/api/v1/retraining`

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 72 | `POST` | `/retraining/` | Créer demande (motif obligatoire) | 🔒 | ADM, E | 🟠 |
| 73 | `GET` | `/retraining/` | Lister demandes (filtres: branch, status) | 🔒 | ADM, E | 🟠 |
| 74 | `GET` | `/retraining/{request_id}` | Détail : raison, drift_report lié, statut | 🔒 | ADM, E | 🟡 |
| 75 | `PATCH` | `/retraining/{request_id}/approve` | Approuver (PENDING → APPROVED) | 🔒 | ADM | 🟠 |
| 76 | `PATCH` | `/retraining/{request_id}/reject` | Rejeter avec motif | 🔒 | ADM | 🟠 |
| 77 | `PATCH` | `/retraining/{request_id}/complete` | Marquer terminé + lier new_model_version_id | 🔒 | ADM | 🟡 |

---

## 13. ROUTER `modules` — `/api/v1/modules`

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 78 | `GET` | `/modules/` | Lister modules et statut (LOADED/NOT_LOADED) | 🔒 | A, ADM, E | 🔴 |
| 79 | `GET` | `/modules/{branch}` | Détail : model card + résumé config YAML | 🔒 | ADM, E | 🟠 |
| 80 | `POST` | `/modules/{branch}/reload` | Hot-reload via PluginRegistry | 🔒 | ADM | 🟠 |
| 81 | `GET` | `/modules/{branch}/config` | Config YAML active (parsée JSON) | 🔒 | ADM, E | 🟠 |
| 82 | `PATCH` | `/modules/{branch}/config` | Modifier seuils → snapshot + reload | 🔒 | ADM | 🟠 |
| 83 | `GET` | `/modules/{branch}/configs` | Lister snapshots YAML versionnés | 🔒 | ADM, E | 🟡 |
| 84 | `GET` | `/modules/{branch}/configs/{config_id}` | Détail snapshot : yaml_content + hash | 🔒 | ADM, E | 🟡 |
| 85 | `POST` | `/modules/{branch}/configs/{config_id}/activate` | Rollback config | 🔒 | ADM | 🟡 |
| 86 | `GET` | `/modules/{branch}/rca-rules` | Règles RCA de la config active | 🔒 | ADM, E | 🟠 |
| 87 | `GET` | `/modules/rca-rules/stats` | Quelle règle déclenche le plus d'anomalies | 🔒 | A, ADM, E | 🟡 |

---

## 14. ROUTER `referentiels` — `/api/v1/referentiels`
> Référentiels pseudonymisés. Nomenclature ASAC, prix en XAF [CIMA].

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 88 | `GET` | `/referentiels/practitioners` | Lister praticiens (filtres: pays, specialite, agrement_cima) | 🔒 | A, ADM | 🟠 |
| 89 | `GET` | `/referentiels/practitioners/{id}` | Détail : ratio_prix_moyen, nb_sinistres | 🔒 | A, ADM | 🟠 |
| 90 | `GET` | `/referentiels/practitioners/{id}/claims` | Sinistres impliquant ce praticien | 🔒 | A, ADM | 🟡 |
| 91 | `GET` | `/referentiels/garages` | Lister garages (filtres: ville, type, agrement_cima) | 🔒 | A, ADM | 🟠 |
| 92 | `GET` | `/referentiels/garages/{id}` | Détail : ratio_devis_moyen, nb_sinistres | 🔒 | A, ADM | 🟠 |
| 93 | `GET` | `/referentiels/garages/{id}/claims` | Sinistres impliquant ce garage | 🔒 | A, ADM | 🟡 |
| 94 | `GET` | `/referentiels/prices/{branch}` | Mercuriale active ASAC/CIMA | 🔒 | G, A, ADM, E | 🟠 |
| 95 | `GET` | `/referentiels/prices/{branch}/{code_acte}` | Prix référence acte spécifique | 🔒 | G, A, ADM | 🟠 |
| 96 | `POST` | `/referentiels/prices` | Importer nouvelle mercuriale (YAML/CSV) | 🔒 | ADM, E | 🟠 |
| 97 | `GET` | `/referentiels/insureds/{id_hash}` | Profil assuré pseudonymisé | 🔒 | A, ADM | 🟡 |
| 98 | `GET` | `/referentiels/insureds/{id_hash}/claims` | Sinistres de cet assuré | 🔒 | A, ADM | 🟠 |
| 99 | `GET` | `/referentiels/employers/{id}` | Détail employeur (secteur, nb_assurés) | 🔒 | A, ADM | 🟡 |
| 100 | `GET` | `/referentiels/employers/{id}/insureds` | Assurés liés (collusion par groupe) | 🔒 | A, ADM | 🟡 |

---

## 15. ROUTER `analytics` — `/api/v1/analytics`

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 101 | `GET` | `/analytics/dashboard` | Stats globales dashboard | 🔒 | all | 🔴 |
| 102 | `GET` | `/analytics/shap/top-features` | Top 10 features prédictives (toutes branches) | 🔒 | A, ADM, E | 🟠 |
| 103 | `GET` | `/analytics/shap/top-features/{branch}` | Top features par branche | 🔒 | A, ADM, E | 🟠 |
| 104 | `GET` | `/analytics/rca/distribution` | Distribution catégories RCA (pie chart) | 🔒 | A, ADM | 🟠 |
| 105 | `GET` | `/analytics/models/performance` | Tableau métriques F1/AUC/MCC/FPR — H0 | 🔒 | ADM, E | 🟡 |

---

## 16. ROUTER `reports` — `/api/v1/reports`
> **⚠️ MISE À JOUR v2.0** : l'endpoint #107 est **scindé en deux** dans le code.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 106 | `POST` | `/reports/export` | Générer export async (csv/xlsx/json) — HTTP 202 | 🔒 | A, ADM | 🟠 |
| 107a | `GET` | `/reports/exports/{export_id}` | Métadonnées export (statut, created_at, size) | 🔒 | A, ADM | 🟠 |
| 107b | `GET` | `/reports/exports/{export_id}/download` | **Téléchargement binaire** (streaming Response) | 🔒 | A, ADM | 🟠 |
| 108 | `GET` | `/reports/exports` | Mes exports (statut PENDING/GENERATING/READY/FAILED) | 🔒 | A, ADM | 🟡 |
| 109 | `GET` | `/reports/stats/global` | Stats globales toutes branches | 🔒 | all | 🔴 |
| 110 | `GET` | `/reports/stats/{branch}` | Stats détaillées par branche | 🔒 | G, A, ADM | 🟠 |

> **Note d'implémentation** : dans `reports.py`, la route `GET /exports/{id}/download` est
> déclarée **avant** `GET /exports/{id}` pour éviter un conflit de routing FastAPI.

---

## 17. ROUTER `admin` — `/api/v1/admin`
> **⚠️ MISE À JOUR v2.0** : 3 chemins diffèrent de la spec v1.0.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 111 | `GET` | `/admin/branches` | Lister branches + config (contamination, seuils) | 🔒 | ADM | 🟠 |
| 112 | `GET` | `/admin/branches/{code}` | Détail branche complet | 🔒 | ADM | 🟠 |
| 113 | `PATCH` | `/admin/branches/{code}` | ~~Modifier seuils~~ **NON IMPLÉMENTÉ** — DT-ADMIN-01 | — | ADM | ⚠️ |
| 114a | `PATCH` | `/admin/branches/{code}/activate` | Activer branche (protection : dernière active) | 🔒 | ADM | 🟡 |
| 114b | `PATCH` | `/admin/branches/{code}/deactivate` | Désactiver branche | 🔒 | ADM | 🟡 |
| 115 | `GET` | `/admin/status` | État système : DB latency, modèles joblib, uptime | 🔒 | ADM | 🟠 |
| 116 | `GET` | `/admin/activity-log` | Journal audit système (filtres: user, action, date) | 🔒 | ADM | 🟡 |

> **DT-ADMIN-01** : `PATCH /admin/branches/{code}` (mise à jour thresholds atomique)
> n'est pas implémenté. Les seuils sont actuellement modifiables via
> `PATCH /modules/{branch}/config` (endpoint #82). Résoudre en Phase 4.

> **v1.0 → v2.0** :
> - `/admin/system` → `/admin/status` (chemin corrigé)
> - `/admin/branches/{code}/toggle` → scindé en `/activate` + `/deactivate`

---

## 18. ROUTER `health` — `/`
> Public. Pas de prefix `/api/v1`.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 117 | `GET` | `/health` | Statut : version, DB, uptime | 🌐 | — | 🔴 |

---

## 19. COUCHES TRANSVERSALES

| Composant | Fichier | Description |
|---|---|---|
| `JWTAuthMiddleware` | `api/deps/auth.py` | Valide access_token JWT |
| `RBACDependency` | `api/deps/rbac.py` | `require_roles([...])` → HTTP 403 |
| `AuditLogMiddleware` | `api/middleware/audit.py` | Log mutations dans `audit_logs` |
| `RateLimitMiddleware` | `api/middleware/rate_limit.py` | 5 req/min /login — no-op en TESTING |
| `ErrorHandler` | `api/middleware/errors.py` | Format unifié `{error, message, timestamp}` |

```json
{"error": "CLAIM_NOT_FOUND", "message": "...", "timestamp": "...", "request_id": "..."}
```

---

## 20. DETTE TECHNIQUE ACTIVE

| ID | Description | Impact | Priorité |
|---|---|---|---|
| DT-ADMIN-01 | `PATCH /admin/branches/{code}` non implémenté — modifier seuils passe par `/modules/{branch}/config` | Faible (workaround existe) | 🟡 Phase 4 |
| DT-001 | `ratio_prix_mercuriale` non reproductible sans MercurialeLoader | Élevé | 🟡 Post-Phase 3 |
| DT-002 | `historique_ratio_praticien` stateless | Moyen | 🟡 Post-Phase 3 |
| DT-SCHEMA | `AnalysisResult.anomaly_score` — vérifier absence de contrainte `le=1` | Élevé | 🔴 |
| DT-SHAP-BG | `shap_background.npy` absent → KernelSHAP dégradé | Moyen | 🟡 |

---

## 21. ANNEXE — Récapitulatif par table DB

| Table | Router(s) | Endpoints |
|---|---|---|
| `users`, `sessions` | auth, users | #1-19 |
| `roles`, `permissions`, `user_roles`, `role_permissions` | roles, users | #18-22 |
| `claims`, `claim_lines`, `claim_documents`, `ocr_extractions` | claims | #23-39 |
| `analysis_runs`, `analyses`, `shap_contributions` | analyze, audit, graph | #40-49, #56-59 |
| `decisions` | audit | #46-47 |
| `escalations` | escalations | #50-55 |
| `fraud_communities`, `community_members` | graph | #56-59 |
| `model_versions`, `production_deployments` | models | #60-66 |
| `drift_reports`, `drift_feature_metrics` | drift | #67-71 |
| `retraining_requests` | retraining | #72-77 |
| `branches`, `module_configs`, `rca_rule_snapshots` | modules, admin | #78-87, #111-116 |
| `practitioners`, `garages`, `employers`, `insureds`, `contracts`, `reference_prices` | referentiels | #88-100 |
| `export_reports` | reports | #106-110 |
| `audit_logs` | admin | #116 |

**Total : 34/34 tables couvertes.** ✅

---

## 22. CORRECTIONS TESTS (v2.0)

Les fichiers de test suivants contiennent des URLs ou méthodes HTTP incorrectes
vis-à-vis du code réel. Voir `tests/api/test_admin.py` corrigé (livré séparément).

| Test | Ancien (spec v1.0) | Correct (code réel) |
|---|---|---|
| `TestAdminSystemInfo.test_system_info_requires_auth` | GET `/admin/system-info` | GET `/admin/status` |
| `TestAdminSystemInfo.test_admin_url_discovery` | `/admin/system-info`, `/admin/config` | `/admin/status` |
| `TestBranchActivation.test_branch_activation_method_discovery` | POST `/activate` | PATCH `/activate` |
| `TestBranchActivation` | `/admin/branches/{code}/toggle` | `/admin/branches/{code}/activate` |

---

*MAKORA_API_ENDPOINTS_COMPLET_v2.md*
*Audit réalisé le 09 juin 2026 — ATABONG EFON STEPHANE FRITZ*
*Ce document remplace MAKORA_API_ENDPOINTS_COMPLET.md v1.0 du 30 mai 2026.*
