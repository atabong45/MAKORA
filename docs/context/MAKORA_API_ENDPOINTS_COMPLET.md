# MAKORA — Rapport Complet des Endpoints API
## Phase 3 · Référence d'implémentation exhaustive
> Généré le : 30 mai 2026  
> Auteur : ATABONG EFON STEPHANE FRITZ  
> Basé sur : `MAKORA_DATABASE_SCHEMA.md` v1.0 (34 tables) + `API_CONTRACTS.md` Phase 0 + Analyse d'écart  
> Statut : **APPROUVÉ POUR IMPLÉMENTATION**

---

## 1. SYNTHÈSE EXÉCUTIVE

| Indicateur | Valeur |
|---|---|
| **Total endpoints définis** | **115** |
| Endpoints couverts par API_CONTRACTS.md Phase 0 | 7 (6%) |
| Endpoints ajoutés par ce rapport | 108 (94%) |
| Routers (fichiers FastAPI) | **17** |
| Tables DB couvertes | **34 / 34** (100%) |
| Endpoints d'écriture (POST/PATCH/DELETE) | 53 |
| Endpoints de lecture (GET) | 62 |

### Analyse d'écart — Domaines non couverts initialement

| Domaine DB | Tables | Couverture avant | Après |
|---|---|---|---|
| IAM | 6 tables | 80% | ✅ 100% |
| **Référentiels Métier** | 8 tables | **0%** | ✅ 100% |
| **Sinistres & Documents** | 4 tables | **0%** | ✅ 100% |
| Pipeline ML | 5 tables | 20% | ✅ 100% |
| **HITL — Escalades** | 2 tables | **50%** | ✅ 100% |
| **Graphe de Fraude** | 2 tables | **0%** | ✅ 100% |
| Monitoring & Drift | 3 tables | 40% | ✅ 100% |
| **Réentraînement** | 1 table | **0%** | ✅ 100% |
| Audit & Config | 4 tables | 30% | ✅ 100% |

### Convention de lecture

| Symbole | Signification |
|---|---|
| 🔒 | Authentification JWT requise |
| 🌐 | Endpoint public (pas de token) |
| 🔴 CRITIQUE | Bloquant — à implémenter en premier |
| 🟠 HAUTE | Nécessaire au MVP |
| 🟡 MOYENNE | Fonctionnalité secondaire |
| `G` | Rôle gestionnaire |
| `A` | Rôle auditeur |
| `ADM` | Rôle administrateur |
| `E` | Rôle expert_metier |

---

## 2. ROUTER `auth` — `/api/v1/auth`
> **Tables :** `users`, `sessions`  
> **Middleware :** RateLimitMiddleware (login : 5 req/min/IP)  
> **Note :** Pas d'auto-inscription — comptes créés par admin uniquement.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 1 | `POST` | `/auth/login` | Connexion → access_token (JWT 15min) + refresh_token (SHA-256 DB) | 🌐 | — | 🔴 |
| 2 | `POST` | `/auth/logout` | Révocation refresh_token (DELETE sessions row) | 🔒 | all | 🔴 |
| 3 | `POST` | `/auth/refresh` | Renouveler access_token via refresh_token valide | 🌐 | — | 🔴 |
| 4 | `POST` | `/auth/forgot-password` | Demander reset — retourne JWT 30min (prototype sans SMTP) | 🌐 | — | 🟠 |
| 5 | `POST` | `/auth/reset-password` | Réinitialiser mdp via token JWT 30min → révoque toutes sessions | 🌐 | — | 🟠 |
| 6 | `POST` | `/auth/change-password` | Changer son propre mdp (vérifie ancien) → révoque autres sessions | 🔒 | all | 🟠 |
| 7 | `GET`  | `/auth/me` | Profil de l'utilisateur connecté + rôles + permissions | 🔒 | all | 🔴 |
| 8 | `PATCH` | `/auth/me` | Modifier nom et email de son propre profil | 🔒 | all | 🟠 |
| 9 | `GET`  | `/auth/sessions` | Lister ses sessions actives (IP, user-agent, expires_at) | 🔒 | all | 🟡 |
| 10 | `DELETE` | `/auth/sessions/{session_id}` | Révoquer une session spécifique (logout distant) | 🔒 | all | 🟡 |

**Schéma JWT :**
```
Login → { access_token: JWT(15min), refresh_token: opaque→SHA256 en sessions }
Refresh → vérifie sessions.expires_at + is_revoked=false → nouveau access_token
Logout → sessions.is_revoked = true (révocation explicite, access_token expire naturellement)
```

---

## 3. ROUTER `users` — `/api/v1/users`
> **Tables :** `users`, `user_roles`, `roles`, `sessions`  
> **Accès :** Administrateur uniquement  
> **Règle :** Soft-delete exclusivement (`is_active=false`) — conformité audit trail.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 11 | `GET`   | `/users/` | Lister utilisateurs (filtres: is_active, role, search) — paginated | 🔒 | ADM | 🟠 |
| 12 | `POST`  | `/users/` | Créer un compte utilisateur avec rôle initial | 🔒 | ADM | 🔴 |
| 13 | `GET`   | `/users/{user_id}` | Détail utilisateur + rôles + nombre sessions actives | 🔒 | ADM | 🟠 |
| 14 | `PATCH` | `/users/{user_id}` | Modifier full_name, email, is_active | 🔒 | ADM | 🟠 |
| 15 | `DELETE` | `/users/{user_id}` | Désactiver compte (is_active=false) + révocation sessions | 🔒 | ADM | 🟠 |
| 16 | `POST`  | `/users/{user_id}/reactivate` | Réactiver un compte désactivé | 🔒 | ADM | 🟡 |
| 17 | `PATCH` | `/users/{user_id}/password` | Forcer reset mdp + révocation sessions de cet utilisateur | 🔒 | ADM | 🟠 |
| 18 | `POST`  | `/users/{user_id}/roles` | Assigner un rôle (granted_by = admin courant) | 🔒 | ADM | 🔴 |
| 19 | `DELETE` | `/users/{user_id}/roles/{role_id}` | Retirer un rôle (protection : dernier rôle admin système) | 🔒 | ADM | 🟠 |

---

## 4. ROUTER `roles` — `/api/v1/roles`
> **Tables :** `roles`, `permissions`, `role_permissions`  
> **Note :** Lecture seule en V1 — 4 rôles fixes seeded en Phase 0.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 20 | `GET` | `/roles/` | Lister les 4 rôles avec description | 🔒 | ADM | 🟠 |
| 21 | `GET` | `/roles/{role_id}` | Détail rôle + liste complète des permissions associées | 🔒 | ADM | 🟡 |
| 22 | `GET` | `/roles/permissions` | Lister toutes les permissions (resource × action) | 🔒 | ADM | 🟡 |

---

## 5. ROUTER `claims` — `/api/v1/claims`
> **Tables :** `claims`, `claim_lines`, `claim_documents`, `ocr_extractions`  
> **Note :** Table centrale du domaine métier. Cycle de vie : `DRAFT → SUBMITTED → OPEN → CLOSED`  
> **Entièrement absent du plan initial.**

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 23 | `GET`    | `/claims/` | Lister sinistres (filtres: branch, statut, date_soin, is_anomaly, score_min) | 🔒 | G, A, ADM | 🔴 |
| 24 | `POST`   | `/claims/` | Créer un sinistre manuellement (statut=DRAFT) | 🔒 | G, ADM | 🔴 |
| 25 | `GET`    | `/claims/{claim_id}` | Détail complet d'un sinistre + contrat lié + lignes count | 🔒 | G, A, ADM | 🔴 |
| 26 | `PATCH`  | `/claims/{claim_id}` | Modifier un sinistre (autorisé seulement si DRAFT ou OPEN) | 🔒 | G, ADM | 🟠 |
| 27 | `POST`   | `/claims/{claim_id}/submit` | Soumettre à l'analyse IA : DRAFT → SUBMITTED → déclenche pipeline | 🔒 | G, ADM | 🔴 |
| 28 | `GET`    | `/claims/{claim_id}/lines` | Lister les lignes de détail (actes médicaux ou postes réparation) | 🔒 | G, A, ADM | 🟠 |
| 29 | `POST`   | `/claims/{claim_id}/lines` | Ajouter une ligne (code_acte, montant, quantité) | 🔒 | G, ADM | 🟠 |
| 30 | `PATCH`  | `/claims/{claim_id}/lines/{line_id}` | Modifier une ligne (seulement si claim DRAFT) | 🔒 | G, ADM | 🟡 |
| 31 | `DELETE` | `/claims/{claim_id}/lines/{line_id}` | Supprimer une ligne (seulement si claim DRAFT) | 🔒 | G, ADM | 🟡 |
| 32 | `GET`    | `/claims/{claim_id}/documents` | Lister les documents attachés (factures, constats, expertises) | 🔒 | G, A, ADM | 🟠 |
| 33 | `POST`   | `/claims/{claim_id}/documents` | Uploader un document (PDF/JPG/PNG — max 50MB) | 🔒 | G, ADM | 🟠 |
| 34 | `GET`    | `/claims/{claim_id}/documents/{doc_id}` | Métadonnées d'un document (hash SHA-256, mime_type, size) | 🔒 | G, A, ADM | 🟡 |
| 35 | `GET`    | `/claims/{claim_id}/documents/{doc_id}/download` | Télécharger le fichier binaire (streaming) | 🔒 | G, A, ADM | 🟠 |
| 36 | `DELETE` | `/claims/{claim_id}/documents/{doc_id}` | Supprimer un document (seulement si claim DRAFT) | 🔒 | ADM | 🟡 |
| 37 | `POST`   | `/claims/{claim_id}/ocr/run` | Déclencher OCR sur un document (PaddleOCR + Tesseract + LLM) | 🔒 | G, ADM | 🟠 |
| 38 | `GET`    | `/claims/{claim_id}/ocr` | Récupérer résultat OCR (score_confiance, montant extrait, flag_altere) | 🔒 | G, A, ADM | 🟠 |
| 39 | `GET`    | `/claims/{claim_id}/analyses` | Historique des analyses ML lancées sur ce sinistre | 🔒 | G, A, ADM | 🟠 |

**Cycle de vie `statut` :**
```
DRAFT     → Saisie en cours (POST /claims + POST /lines + POST /documents)
SUBMITTED → POST /{claim_id}/submit → pipeline MAKORA déclenché automatiquement
OPEN      → Résultat disponible → décision gestionnaire en attente
CLOSED    → POST /audit/{claim_id}/decision CONFIRMED ou REJECTED
```

---

## 6. ROUTER `analyze` — `/api/v1/analyze`
> **Tables :** `analysis_runs`, `analyses`, `claims`, `branches`, `model_versions`  
> **Note :** Endpoints originaux CDC Phase 0 — enrichis avec batch tracking et historique.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 40 | `POST`  | `/analyze/` | Analyser batch JSON → MAKORAOutput complet (score + SHAP + RCA) | 🔒 | G, A, ADM | 🔴 |
| 41 | `POST`  | `/analyze/upload` | Analyser fichier CSV/JSON/PDF (multipart, max 50MB) | 🔒 | G, A, ADM | 🟠 |
| 42 | `GET`   | `/analyze/runs/{run_id}` | Résultats d'une session d'analyse (statut + nb_dossiers + nb_anomalies) | 🔒 | G, A, ADM | 🟠 |
| 43 | `GET`   | `/analyze/runs` | Historique des sessions d'analyse (paginated, filtres branch/date) | 🔒 | G, A, ADM | 🟡 |

---

## 7. ROUTER `audit` — `/api/v1/audit`
> **Tables :** `analyses`, `decisions`, `audit_logs`  
> **Note :** Human-in-the-loop (BF-08). `core/audit_logger.py` (DT-AUDIT) doit être implémenté ici.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 44 | `GET`   | `/audit/` | Lister analyses avec filtres (branch, decision_status, score_min, date) | 🔒 | G, A, ADM | 🔴 |
| 45 | `GET`   | `/audit/{analysis_id}` | Détail complet : score + SHAP top3 + RCA + narration LLM | 🔒 | G, A, ADM | 🔴 |
| 46 | `POST`  | `/audit/{analysis_id}/decision` | Enregistrer décision CONFIRMED/REJECTED/ESCALATED + motif | 🔒 | G, A | 🔴 |
| 47 | `GET`   | `/audit/{analysis_id}/decisions` | Historique des décisions sur cette analyse (immuable) | 🔒 | A, ADM | 🟠 |
| 48 | `GET`   | `/audit/{analysis_id}/shap` | Valeurs SHAP complètes (toutes features, pas seulement top 3) | 🔒 | G, A, ADM | 🟠 |
| 49 | `GET`   | `/audit/stats` | Stats agrégées dashboard (taux anomalie, répartition décisions, top RCA) | 🔒 | all | 🔴 |

---

## 8. ROUTER `escalations` — `/api/v1/escalations`
> **Tables :** `escalations`, `analyses`, `decisions`  
> **Entièrement absent du plan initial. Correspond à BF-08 du CDC.**

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 50 | `POST`  | `/escalations/` | Créer une escalade (gestionnaire → auditeur, motif obligatoire) | 🔒 | G | 🟠 |
| 51 | `GET`   | `/escalations/` | Lister escalades (auditeur : les siennes + non assignées ; admin : toutes) | 🔒 | A, ADM | 🟠 |
| 52 | `GET`   | `/escalations/{escalation_id}` | Détail escalade + analyse liée + historique | 🔒 | A, ADM | 🟠 |
| 53 | `PATCH` | `/escalations/{escalation_id}/assign` | Assigner une escalade à un auditeur (ou auto-assignation) | 🔒 | A, ADM | 🟠 |
| 54 | `PATCH` | `/escalations/{escalation_id}/resolve` | Clore l'escalade avec note de résolution (RESOLVED) | 🔒 | A | 🟠 |
| 55 | `GET`   | `/escalations/pending` | Escalades non assignées (file d'attente auditeur) | 🔒 | A, ADM | 🟡 |

---

## 9. ROUTER `graph` — `/api/v1/graph`
> **Tables :** `fraud_communities`, `community_members`, `analysis_runs`  
> **Référence :** [Blondel2008] Louvain. **Entièrement absent du plan initial.**

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 56 | `GET`   | `/graph/communities` | Lister communautés suspectes (filtres: branch, is_suspicious, size_min) | 🔒 | A, ADM | 🟠 |
| 57 | `GET`   | `/graph/communities/{community_id}` | Détail communauté : densité, modularité, suspicion_score, reason | 🔒 | A, ADM | 🟠 |
| 58 | `GET`   | `/graph/communities/{community_id}/members` | Membres de la communauté (type, hash, node_score, is_central) | 🔒 | A, ADM | 🟠 |
| 59 | `GET`   | `/graph/runs/{run_id}/communities` | Toutes communautés détectées lors d'une session d'analyse | 🔒 | A, ADM | 🟡 |

---

## 10. ROUTER `models` — `/api/v1/models`
> **Tables :** `model_versions`, `production_deployments`, `branches`  
> **20% couvert initialement. Ajoute la gouvernance complète du cycle modèle.**

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 60 | `GET`   | `/models/` | Catalogue de tous les modèles entraînés (filtres: branch, algorithm) | 🔒 | ADM, E | 🟠 |
| 61 | `GET`   | `/models/{model_id}` | Détail : métriques F1/AUC/MCC/FPR + feature_names + contamination | 🔒 | ADM, E | 🟠 |
| 62 | `POST`  | `/models/register` | Enregistrer un nouveau modèle (post-training) dans le catalogue | 🔒 | ADM | 🟠 |
| 63 | `GET`   | `/models/branch/{branch}/history` | Historique des modèles entraînés pour une branche | 🔒 | ADM, E | 🟡 |
| 64 | `GET`   | `/models/branch/{branch}/current` | Modèle actuellement en production pour cette branche | 🔒 | ADM, E, A | 🟠 |
| 65 | `POST`  | `/models/deploy` | Déployer un modèle en production (maj production_deployments) | 🔒 | ADM | 🟠 |
| 66 | `GET`   | `/models/deployments` | Historique complet des déploiements (quel modèle était actif quand) | 🔒 | ADM | 🟡 |

---

## 11. ROUTER `drift` — `/api/v1/drift`
> **Tables :** `drift_reports`, `drift_feature_metrics`, `branches`  
> **Référence :** [Gama2014]. PSI seuils : STABLE<0.10 < WARNING<0.20 ≤ CRITICAL.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 67 | `GET`   | `/drift/status` | Statut drift de toutes les branches actives (PSI global) | 🔒 | A, ADM, E | 🔴 |
| 68 | `GET`   | `/drift/status/{branch}` | Statut drift détaillé : PSI par feature + recommandation | 🔒 | A, ADM, E | 🟠 |
| 69 | `GET`   | `/drift/history/{branch}` | Chronologie des rapports drift pour une branche | 🔒 | ADM, E | 🟠 |
| 70 | `GET`   | `/drift/reports/{report_id}` | Détail rapport : drift_feature_metrics pour chaque feature | 🔒 | ADM, E | 🟡 |
| 71 | `POST`  | `/drift/run/{branch}` | Déclencher calcul PSI manuel (fenêtres configurables) | 🔒 | ADM, E | 🟠 |

---

## 12. ROUTER `retraining` — `/api/v1/retraining`
> **Table :** `retraining_requests`, `drift_reports`, `model_versions`  
> **Entièrement absent du plan initial. Complète la boucle gouvernance ML.**

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 72 | `POST`  | `/retraining/` | Créer demande de réentraînement (motif obligatoire, lié éventuellement à un drift report) | 🔒 | ADM, E | 🟠 |
| 73 | `GET`   | `/retraining/` | Lister demandes (filtres: branch, status) | 🔒 | ADM, E | 🟠 |
| 74 | `GET`   | `/retraining/{request_id}` | Détail : raison, drift_report lié, statut, approuvé par | 🔒 | ADM, E | 🟡 |
| 75 | `PATCH` | `/retraining/{request_id}/approve` | Approuver la demande (PENDING → APPROVED) | 🔒 | ADM | 🟠 |
| 76 | `PATCH` | `/retraining/{request_id}/reject` | Rejeter la demande avec motif | 🔒 | ADM | 🟠 |
| 77 | `PATCH` | `/retraining/{request_id}/complete` | Marquer terminé + lier new_model_version_id (DONE) | 🔒 | ADM | 🟡 |

---

## 13. ROUTER `modules` — `/api/v1/modules`
> **Tables :** `branches`, `module_configs`, `rca_rule_snapshots`  
> **Enrichi : versioning config YAML + consultation règles RCA.**

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 78 | `GET`   | `/modules/` | Lister modules et statut (LOADED/NOT_LOADED, version, graph_enabled) | 🔒 | A, ADM, E | 🔴 |
| 79 | `GET`   | `/modules/{branch}` | Détail module : model card + résumé config YAML active | 🔒 | ADM, E | 🟠 |
| 80 | `POST`  | `/modules/{branch}/reload` | Hot-reload sans redémarrer l'API (via PluginRegistry) | 🔒 | ADM | 🟠 |
| 81 | `GET`   | `/modules/{branch}/config` | Lire configuration YAML active (parsée en JSON) | 🔒 | ADM, E | 🟠 |
| 82 | `PATCH` | `/modules/{branch}/config` | Modifier seuils (contamination, anomaly_score_alert) → snapshot + reload | 🔒 | ADM | 🟠 |
| 83 | `GET`   | `/modules/{branch}/configs` | Lister snapshots YAML versionnés (module_configs) | 🔒 | ADM, E | 🟡 |
| 84 | `GET`   | `/modules/{branch}/configs/{config_id}` | Détail snapshot : yaml_content + yaml_hash + date | 🔒 | ADM, E | 🟡 |
| 85 | `POST`  | `/modules/{branch}/configs/{config_id}/activate` | Activer un ancien snapshot (rollback config) | 🔒 | ADM | 🟡 |
| 86 | `GET`   | `/modules/{branch}/rca-rules` | Lister les règles RCA de la config active (depuis rca_rule_snapshots) | 🔒 | ADM, E | 🟠 |
| 87 | `GET`   | `/modules/rca-rules/stats` | Quelle règle déclenche le plus d'anomalies (statistique globale) | 🔒 | A, ADM, E | 🟡 |

---

## 14. ROUTER `referentiels` — `/api/v1/referentiels`
> **Tables :** `practitioners`, `garages`, `employers`, `insureds`, `contracts`, `reference_prices`  
> **Entièrement absent du plan initial. Référentiels pseudonymisés — lecture dominante.**

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 88 | `GET`   | `/referentiels/practitioners` | Lister praticiens (filtres: pays, specialite, agrement_cima, ratio_min) | 🔒 | A, ADM | 🟠 |
| 89 | `GET`   | `/referentiels/practitioners/{id}` | Détail praticien : spécialité, ratio_prix_moyen, nb_sinistres_total | 🔒 | A, ADM | 🟠 |
| 90 | `GET`   | `/referentiels/practitioners/{id}/claims` | Sinistres impliquant ce praticien (paginated) | 🔒 | A, ADM | 🟡 |
| 91 | `GET`   | `/referentiels/garages` | Lister garages (filtres: ville, type_garage, agrement_cima, ratio_min) | 🔒 | A, ADM | 🟠 |
| 92 | `GET`   | `/referentiels/garages/{id}` | Détail garage : type, ratio_devis_moyen, nb_sinistres_total | 🔒 | A, ADM | 🟠 |
| 93 | `GET`   | `/referentiels/garages/{id}/claims` | Sinistres impliquant ce garage (paginated) | 🔒 | A, ADM | 🟡 |
| 94 | `GET`   | `/referentiels/prices/{branch}` | Mercuriale active pour une branche (ASAC/CCAM/ARGUS) | 🔒 | G, A, ADM, E | 🟠 |
| 95 | `GET`   | `/referentiels/prices/{branch}/{code_acte}` | Prix de référence pour un acte spécifique (historique inclus) | 🔒 | G, A, ADM | 🟠 |
| 96 | `POST`  | `/referentiels/prices` | Importer une nouvelle mercuriale (admin — upload YAML/CSV) | 🔒 | ADM, E | 🟠 |
| 97 | `GET`   | `/referentiels/insureds/{id_hash}` | Profil assuré pseudonymisé (région, âge, sexe, contrats) | 🔒 | A, ADM | 🟡 |
| 98 | `GET`   | `/referentiels/insureds/{id_hash}/claims` | Sinistres de cet assuré (pour détecter fréquence anormale) | 🔒 | A, ADM | 🟠 |
| 99 | `GET`   | `/referentiels/employers/{id}` | Détail employeur (secteur, nb_assurés liés) | 🔒 | A, ADM | 🟡 |
| 100 | `GET`  | `/referentiels/employers/{id}/insureds` | Assurés liés à cet employeur (collusion par groupe) | 🔒 | A, ADM | 🟡 |

---

## 15. ROUTER `analytics` — `/api/v1/analytics`
> **Tables :** `shap_contributions`, `analyses`, `decisions`, `analysis_runs`, `branches`  
> **Entièrement absent. Alimente le dashboard Next.js avec données pré-agrégées.**

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 101 | `GET`  | `/analytics/dashboard` | Stats globales dashboard : taux anomalie, décisions, drift status | 🔒 | all | 🔴 |
| 102 | `GET`  | `/analytics/shap/top-features` | Top 10 features les plus prédictives (toutes branches, période) | 🔒 | A, ADM, E | 🟠 |
| 103 | `GET`  | `/analytics/shap/top-features/{branch}` | Top features par branche (compare Santé vs Auto) | 🔒 | A, ADM, E | 🟠 |
| 104 | `GET`  | `/analytics/rca/distribution` | Distribution catégories RCA déclenchées (pie chart data) | 🔒 | A, ADM | 🟠 |
| 105 | `GET`  | `/analytics/models/performance` | Tableau comparatif métriques (F1, AUC, MCC, FPR) — références H0 | 🔒 | ADM, E | 🟡 |

---

## 16. ROUTER `reports` — `/api/v1/reports`
> **Tables :** `export_reports`, `analyses`, `decisions`, `audit_logs`  
> **Implémente BF-10 du CDC non-technique.**

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 106 | `POST`  | `/reports/export` | Générer export (type: audit_decisions/anomaly_summary/drift_history/community_fraud, format: csv/xlsx/json) | 🔒 | A, ADM | 🟠 |
| 107 | `GET`   | `/reports/exports/{export_id}` | Télécharger fichier généré (streaming, lien expirant 1h) | 🔒 | A, ADM | 🟠 |
| 108 | `GET`   | `/reports/exports` | Mes exports générés (statut PENDING/GENERATING/READY/FAILED) | 🔒 | A, ADM | 🟡 |
| 109 | `GET`   | `/reports/stats/global` | Stats globales toutes branches (total dossiers, anomaly_rate, time_series) | 🔒 | all | 🔴 |
| 110 | `GET`   | `/reports/stats/{branch}` | Stats détaillées par branche (métriques + FP/FN rate + RCA distribution) | 🔒 | G, A, ADM | 🟠 |

---

## 17. ROUTER `admin` — `/api/v1/admin`
> **Tables :** `branches`, `audit_logs`  
> **Accès :** Administrateur uniquement.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 111 | `GET`   | `/admin/branches` | Lister branches avec config complète (contamination, seuils) | 🔒 | ADM | 🟠 |
| 112 | `GET`   | `/admin/branches/{code}` | Détail branche + module_status + drift_status courant | 🔒 | ADM | 🟠 |
| 113 | `PATCH` | `/admin/branches/{code}` | Modifier seuils (alert < block validé) → hot-reload déclenché | 🔒 | ADM | 🟠 |
| 114 | `PATCH` | `/admin/branches/{code}/toggle` | Activer/désactiver branche (protection : dernière active) | 🔒 | ADM | 🟡 |
| 115 | `GET`   | `/admin/system` | État système : DB latency, Ollama, modèles joblib, uptime | 🔒 | ADM | 🟠 |
| 116 | `GET`   | `/admin/activity-log` | Journal audit système (filtres: user, action, resource, date) | 🔒 | ADM | 🟡 |

---

## 18. ROUTER `health` — `/api/v1/health`
> **Tables :** aucune (healthcheck infra)  
> **Public.** Déjà spécifié dans API_CONTRACTS.md Phase 0.

| # | Méthode | Chemin | Description | Auth | Rôles | Priorité |
|---|---|---|---|---|---|---|
| 117 | `GET` | `/health` | Statut service : version, ollama, modules_loaded, uptime | 🌐 | — | 🔴 |

---

## 19. COUCHES TRANSVERSALES (Middleware & Dependencies)
> À implémenter **avant** tous les routers — bloc F1.

| Composant | Fichier | Description | Obligatoire |
|---|---|---|---|
| `JWTAuthMiddleware` | `api/deps/auth.py` | Valide access_token JWT, injecte `CurrentUser` dans la requête | ✅ CRITIQUE |
| `RBACDependency` | `api/deps/rbac.py` | Vérifie les rôles requis — `require_roles([...])` → HTTP 403 | ✅ CRITIQUE |
| `AuditLogMiddleware` | `api/middleware/audit.py` | Log toutes mutations (POST/PATCH/DELETE) dans `audit_logs` — résout DT-AUDIT | ✅ CRITIQUE |
| `RateLimitMiddleware` | `api/middleware/rate_limit.py` | 5 req/min/IP sur /login, 100 req/min sur reste — via `slowapi` | ✅ HAUTE |
| `CORSMiddleware` | `api/main.py` | CORS depuis `localhost:3000` + domaine prod | ✅ HAUTE |
| `ErrorHandler` | `api/middleware/errors.py` | Format unifié `{error, message, timestamp}` sur toutes exceptions | ✅ CRITIQUE |
| `PaginationDep` | `api/deps/pagination.py` | Params `page` + `page_size` (max 200) réutilisables par tous routers | ✅ HAUTE |

### Format réponse erreur unifié
```json
{
  "error": "CLAIM_NOT_FOUND",
  "message": "Le sinistre 'SIN_2025_CM_00842' n'existe pas.",
  "timestamp": "2026-05-30T10:00:00Z",
  "request_id": "req_7f8a3b2c"
}
```

### Codes HTTP utilisés

| Code | Signification |
|---|---|
| `200` | Succès lecture / action |
| `201` | Ressource créée (POST) |
| `400` | Requête invalide (branch inconnue, champ manquant) |
| `401` | Token manquant ou expiré |
| `403` | Rôle insuffisant |
| `404` | Ressource non trouvée |
| `409` | Conflit (ex: username déjà pris, modèle déjà déployé) |
| `413` | Fichier trop volumineux (> 50MB) |
| `422` | Erreur validation Pydantic |
| `503` | Modèle ML non chargé / Ollama indisponible |

---

## 20. ORDRE D'IMPLÉMENTATION — 8 BLOCS

| Bloc | Contenu | Fichiers cibles | Priorité |
|---|---|---|---|
| **F1** | Infrastructure API | `api/main.py`, `api/deps/auth.py`, `api/deps/rbac.py`, `api/middleware/`, `api/schemas/common.py` | 🔴 |
| **F2** | IAM complet | `api/routers/auth.py`, `api/routers/users.py`, `api/routers/roles.py`, `api/schemas/iam.py` | 🔴 |
| **F3** | Sinistres + Analyse + Audit | `api/routers/claims.py`, `api/routers/analyze.py`, `api/routers/audit.py`, `core/audit_logger.py` **(DT-AUDIT)** | 🔴 |
| **F4** | HITL complet | `api/routers/escalations.py`, `api/schemas/escalations.py` | 🟠 |
| **F5** | ML Governance | `api/routers/models.py`, `api/routers/drift.py`, `api/routers/retraining.py`, `api/routers/modules.py` | 🟠 |
| **F6** | Graphe + Référentiels | `api/routers/graph.py`, `api/routers/referentiels.py` | 🟠 |
| **F7** | Analytics + Reports + Admin | `api/routers/analytics.py`, `api/routers/reports.py`, `api/routers/admin.py` | 🟠 |
| **F8** | Tests API complets | `tests/api/test_auth.py`, `tests/api/test_claims.py`, `tests/api/test_audit.py`, `...` (17 fichiers) | 🔴 |

**Règle de découpage :** chaque router > 150 lignes est découpé en `{router}_service.py` (logique) + `{router}_router.py` (FastAPI) — conforme IMP-007 (fichiers ≤ 400 lignes).

---

## 21. FICHIERS À METTRE À JOUR

| Fichier | Action | Motif |
|---|---|---|
| `API_CONTRACTS.md` | Remplacement complet | 93% d'endpoints non documentés en Phase 0 |
| `ARCHITECTURE.md` | Ajouter ADR-013 (routers structure) | 17 routers vs 4 prévus |
| `SESSION_STATE.md` | Mettre à jour "prochaine action" | Phase 3 Bloc F1 démarre |
| `HANDOFF.md` | Ajouter v7 fin Phase 3 | Passation future |

---

## ANNEXE — Récapitulatif par table DB

| Table | Router(s) qui l'utilisent | Endpoints couverts |
|---|---|---|
| `users` | auth, users | #1-19 |
| `roles` | auth, users, roles | #1, #18-22 |
| `permissions` | roles | #22 |
| `user_roles` | users | #18-19 |
| `role_permissions` | roles | #21 |
| `sessions` | auth | #1-3, #9-10 |
| `branches` | admin, modules, drift, models, referentiels | #60-117 |
| `insureds` | referentiels | #97-98 |
| `contracts` | referentiels, claims | #25 |
| `practitioners` | referentiels | #88-90 |
| `garages` | referentiels | #91-93 |
| `employers` | referentiels | #99-100 |
| `insured_employers` | referentiels | #100 |
| `reference_prices` | referentiels | #94-96 |
| `claims` | claims, analyze, audit | #23-39, #40, #44 |
| `claim_lines` | claims | #28-31 |
| `claim_documents` | claims | #32-36 |
| `ocr_extractions` | claims | #37-38 |
| `model_versions` | models | #60-66 |
| `production_deployments` | models | #64-66 |
| `analysis_runs` | analyze, graph | #40-43, #59 |
| `analyses` | analyze, audit, analytics | #40-48, #101-104 |
| `shap_contributions` | audit, analytics | #48, #102-103 |
| `decisions` | audit | #46-47 |
| `escalations` | escalations | #50-55 |
| `fraud_communities` | graph | #56-59 |
| `community_members` | graph | #58-59 |
| `drift_reports` | drift | #67-71 |
| `drift_feature_metrics` | drift | #70 |
| `retraining_requests` | retraining | #72-77 |
| `audit_logs` | admin | #116 |
| `export_reports` | reports | #106-108 |
| `module_configs` | modules | #83-85 |
| `rca_rule_snapshots` | modules | #86-87 |

**Total : 34/34 tables couvertes par au moins un endpoint.** ✅

---

*MAKORA_API_ENDPOINTS_COMPLET.md — v1.0*  
*Généré le 30 mai 2026 — Phase 3, avant implémentation*  
*ATABONG EFON STEPHANE FRITZ*  
*Ce document remplace et étend API_CONTRACTS.md Phase 0.*
