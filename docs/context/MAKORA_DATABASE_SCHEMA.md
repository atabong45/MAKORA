# MAKORA — Schéma de Base de Données Complet
> Version : 1.0 — Post-audit critique, important et mineur  
> Date : 30 mai 2026  
> Auteur : ATABONG EFON STEPHANE FRITZ  
> Technologie : PostgreSQL 15+ avec SQLAlchemy ORM  
> Total : 34 tables réparties en 8 domaines fonctionnels

---

## Conventions de lecture

| Symbole | Signification |
|---|---|
| `PK` | Clé primaire |
| `FK` | Clé étrangère |
| `UNIQUE` | Contrainte d'unicité |
| `NOT NULL` | Valeur obligatoire |
| `NULLABLE` | Valeur optionnelle |
| `GEN` | Colonne générée automatiquement par PostgreSQL |
| `DEFAULT` | Valeur par défaut |
| `CHECK` | Contrainte de validation |

**Types utilisés :**
- `UUID` — identifiant unique universel (clé primaire systématique)
- `VARCHAR(n)` — chaîne de longueur maximale n
- `TEXT` — chaîne sans limite de longueur
- `FLOAT` — nombre décimal double précision
- `INTEGER` — entier 32 bits
- `BIGINT` — entier 64 bits
- `BOOLEAN` — vrai/faux
- `DATE` — date sans heure
- `TIMESTAMP WITH TIME ZONE` — horodatage UTC
- `JSONB` — JSON binaire indexable PostgreSQL

**Règle UUID :** toutes les clés primaires sont des UUID v4 générés côté application. Jamais d'auto-increment entier — garantit l'unicité en cas de fusion de bases ou migration.

**Règle horodatage :** toutes les colonnes `created_at` et `updated_at` sont `TIMESTAMP WITH TIME ZONE DEFAULT now()`. Le timezone est toujours UTC.

---

## DOMAINE 1 — IAM (Identity & Access Management)
> 6 tables — gestion des utilisateurs, rôles, permissions et sessions

---

### Table `users`
**Rôle :** Stocke tous les utilisateurs du système. Un utilisateur peut être gestionnaire, auditeur, administrateur ou expert métier selon les rôles qui lui sont assignés.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `username` | VARCHAR(50) | UNIQUE, NOT NULL | Identifiant de connexion (alphanumérique, sans espace) |
| `email` | VARCHAR(255) | UNIQUE, NOT NULL | Adresse email professionnelle |
| `password_hash` | VARCHAR(255) | NOT NULL | Hash bcrypt du mot de passe (jamais le mot de passe en clair) |
| `full_name` | VARCHAR(255) | NOT NULL | Nom complet affiché dans l'interface |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | Compte actif ou suspendu |
| `last_login` | TIMESTAMP WITH TIME ZONE | NULLABLE | Dernière connexion réussie |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de création du compte |
| `updated_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Dernière modification |

**Index :** `idx_users_email` sur `email`, `idx_users_username` sur `username`  
**Notes :** La désactivation d'un compte se fait via `is_active = false`, jamais par suppression (conformité audit trail).

---

### Table `roles`
**Rôle :** Définit les rôles disponibles dans le système. Les rôles sont fixes et correspondent aux acteurs du CDC.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `name` | VARCHAR(50) | UNIQUE, NOT NULL | Nom technique (ex : `gestionnaire`, `auditeur`, `administrateur`, `expert_metier`) |
| `display_name` | VARCHAR(100) | NOT NULL | Nom affiché dans l'interface |
| `description` | TEXT | NULLABLE | Description du rôle et de ses responsabilités |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de création |

**Valeurs initiales (seed) :**
```
gestionnaire    → Gestionnaire de Sinistres
auditeur        → Auditeur / Responsable Anti-Fraude
administrateur  → Administrateur Système
expert_metier   → Expert Métier (rédacteur YAML)
```

---

### Table `permissions`
**Rôle :** Liste exhaustive des permissions disponibles dans le système. Chaque permission est définie par une ressource et une action.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `code` | VARCHAR(100) | UNIQUE, NOT NULL | Code technique (ex : `claims:read`, `analyses:create`, `models:deploy`) |
| `resource` | VARCHAR(50) | NOT NULL | Ressource concernée (`claims`, `analyses`, `decisions`, `models`, `drift`, `audit`, `users`, `modules`) |
| `action` | VARCHAR(50) | NOT NULL | Action autorisée (`read`, `create`, `update`, `delete`, `export`, `deploy`, `validate`) |
| `description` | TEXT | NULLABLE | Description humaine de ce que permet cette permission |

**Contrainte :** UNIQUE sur `(resource, action)`.

---

### Table `user_roles`
**Rôle :** Table de jonction entre utilisateurs et rôles. Un utilisateur peut avoir plusieurs rôles.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `user_id` | UUID | FK → users.id, NOT NULL | Utilisateur concerné |
| `role_id` | UUID | FK → roles.id, NOT NULL | Rôle attribué |
| `granted_by` | UUID | FK → users.id, NOT NULL | Utilisateur ayant accordé ce rôle |
| `granted_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date d'attribution |

**Clé primaire composée :** `(user_id, role_id)`  
**Notes :** Le premier utilisateur administrateur est créé via un script de bootstrap au démarrage — il se "s'auto-accorde" le rôle.

---

### Table `role_permissions`
**Rôle :** Table de jonction entre rôles et permissions. Définit ce que chaque rôle peut faire.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `role_id` | UUID | FK → roles.id, NOT NULL | Rôle concerné |
| `permission_id` | UUID | FK → permissions.id, NOT NULL | Permission accordée |

**Clé primaire composée :** `(role_id, permission_id)`

---

### Table `sessions`
**Rôle :** Stocke les refresh tokens JWT actifs. Implémente le pattern JWT + refresh token (Option C retenue). Le token d'accès (15 min) est stateless. Le refresh token (7 jours) est stocké ici pour permettre la révocation.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique de la session |
| `user_id` | UUID | FK → users.id, NOT NULL | Utilisateur propriétaire |
| `refresh_token_hash` | VARCHAR(255) | UNIQUE, NOT NULL | Hash SHA-256 du refresh token (jamais le token en clair) |
| `ip_address` | VARCHAR(45) | NULLABLE | IP de connexion (IPv4 ou IPv6) |
| `user_agent` | VARCHAR(500) | NULLABLE | Navigateur/client utilisé |
| `is_revoked` | BOOLEAN | NOT NULL, DEFAULT false | Token révoqué (logout, suspension) |
| `expires_at` | TIMESTAMP WITH TIME ZONE | NOT NULL | Expiration du refresh token |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de création |

**Index :** `idx_sessions_token_hash` sur `refresh_token_hash`, `idx_sessions_user_id` sur `user_id`  
**Nettoyage :** Un job cron supprime les sessions expirées toutes les 24h.

---

## DOMAINE 2 — Référentiels Métier
> 8 tables — entités du domaine assurance

---

### Table `branches`
**Rôle :** Référentiel des branches d'assurance supportées par MAKORA. Chaque branche correspond à un module plugin.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `code` | VARCHAR(20) | UNIQUE, NOT NULL | Code technique (`sante`, `auto`, `vie`, `agricole`) |
| `display_name` | VARCHAR(100) | NOT NULL | Nom affiché (ex : "Assurance Santé") |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | Module chargé et opérationnel |
| `contamination_threshold` | FLOAT | NOT NULL, CHECK > 0 AND < 0.5 | Seuil contamination Isolation Forest validé en Phase 2 |
| `anomaly_score_alert` | FLOAT | NOT NULL, DEFAULT 0.65 | Score déclenchant une alerte |
| `anomaly_score_block` | FLOAT | NOT NULL, DEFAULT 0.90 | Score déclenchant un blocage |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de création |

**Valeurs initiales :**
```
sante    → contamination=0.068, active=true
auto     → contamination=0.080, active=true
vie      → contamination=0.080, active=false  (conception seulement)
agricole → contamination=0.080, active=false  (conception seulement)
```

---

### Table `insureds`
**Rôle :** Assurés pseudonymisés. Jamais de données nominatives — uniquement le hash de l'identifiant source.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant interne MAKORA |
| `id_hash` | VARCHAR(64) | UNIQUE, NOT NULL | SHA-256 tronqué à 16 chars de l'ID source + sel |
| `region` | VARCHAR(100) | NULLABLE | Région de résidence |
| `pays` | VARCHAR(10) | NOT NULL, DEFAULT 'CM' | Code pays (CM, FR) |
| `age` | INTEGER | NULLABLE, CHECK >= 0 AND <= 120 | Âge à la souscription |
| `sexe` | VARCHAR(1) | NULLABLE, CHECK IN ('M','F') | Sexe déclaré |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de création |

**Notes pseudonymisation :** `id_hash = SHA256(SECRET_SALT + id_source)[:16]`. Le sel est en variable d'environnement, jamais en base ni en Git.

---

### Table `contracts`
**Rôle :** Polices d'assurance liant un assuré à une branche.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `insured_id` | UUID | FK → insureds.id, NOT NULL | Assuré titulaire |
| `branch_id` | UUID | FK → branches.id, NOT NULL | Branche d'assurance |
| `police_number` | VARCHAR(100) | UNIQUE, NOT NULL | Numéro de police pseudonymisé |
| `type_contrat` | VARCHAR(50) | NOT NULL | Type (RC, Tous Risques, Santé Individuelle, etc.) |
| `date_souscription` | DATE | NOT NULL | Date de souscription |
| `date_resiliation` | DATE | NULLABLE | Date de résiliation (null = contrat actif) |
| `anciennete_jours` | INTEGER | GEN | Calculé : `CURRENT_DATE - date_souscription` |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | Contrat en cours de validité |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date d'enregistrement |

**Index :** `idx_contracts_insured` sur `insured_id`, `idx_contracts_branch` sur `branch_id`

---

### Table `practitioners`
**Rôle :** Praticiens médicaux pour la branche Santé. Pseudonymisés.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `id_hash` | VARCHAR(64) | UNIQUE, NOT NULL | Hash pseudonymisé de l'ID praticien source |
| `specialite` | VARCHAR(100) | NULLABLE | Spécialité médicale |
| `region` | VARCHAR(100) | NULLABLE | Région d'exercice |
| `pays` | VARCHAR(10) | NOT NULL, DEFAULT 'CM' | Pays d'exercice |
| `agrement_cima` | BOOLEAN | NULLABLE | Agréé CIMA (contexte camerounais) |
| `ratio_prix_moyen` | FLOAT | NULLABLE | Ratio prix moyen historique (mis à jour par batch) |
| `nb_sinistres_total` | INTEGER | NOT NULL, DEFAULT 0 | Nombre total de sinistres impliquant ce praticien |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de création |

---

### Table `garages`
**Rôle :** Garages et réparateurs pour la branche Auto. Pseudonymisés.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `id_hash` | VARCHAR(64) | UNIQUE, NOT NULL | Hash pseudonymisé de l'ID garage source |
| `nom` | VARCHAR(255) | NULLABLE | Nom du garage |
| `type_garage` | VARCHAR(50) | NULLABLE | Agréé constructeur / Indépendant / Non agréé |
| `ville` | VARCHAR(100) | NULLABLE | Ville d'implantation |
| `pays` | VARCHAR(10) | NOT NULL, DEFAULT 'CM' | Pays |
| `agrement_cima` | BOOLEAN | NULLABLE | Agréé CIMA (contexte camerounais) |
| `ratio_devis_moyen` | FLOAT | NULLABLE | Ratio devis/barème moyen historique |
| `nb_sinistres_total` | INTEGER | NOT NULL, DEFAULT 0 | Nombre total de sinistres impliquant ce garage |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de création |

---

### Table `employers`
**Rôle :** Employeurs des assurés (branche Santé). Utilisé pour détecter la collusion par groupe d'entreprise.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `id_hash` | VARCHAR(64) | UNIQUE, NOT NULL | Hash pseudonymisé de l'ID employeur source |
| `secteur` | VARCHAR(100) | NULLABLE | Secteur d'activité |
| `region` | VARCHAR(100) | NULLABLE | Région du siège |
| `nb_assures` | INTEGER | NOT NULL, DEFAULT 0 | Nombre d'assurés liés à cet employeur |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de création |

---

### Table `insured_employers`
**Rôle :** Table de jonction entre assurés et employeurs. Conserve l'historique des employeurs successifs.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `insured_id` | UUID | FK → insureds.id, NOT NULL | Assuré concerné |
| `employer_id` | UUID | FK → employers.id, NOT NULL | Employeur concerné |
| `date_debut` | DATE | NOT NULL | Date de début du lien |
| `date_fin` | DATE | NULLABLE | Date de fin (null = lien actif) |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | Lien actif actuellement |

**Index :** `idx_insured_employers_insured` sur `insured_id`

---

### Table `reference_prices`
**Rôle :** Mercuriales de référence pour le calcul du ratio prix. Source : ASAC (Cameroun), CCAM (France), Argus (Auto).

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `branch_id` | UUID | FK → branches.id, NOT NULL | Branche concernée |
| `code_acte` | VARCHAR(50) | NOT NULL | Code de l'acte (ASAC, CCAM ou code réparation) |
| `libelle` | TEXT | NULLABLE | Description de l'acte |
| `nomenclature` | VARCHAR(20) | NOT NULL | Source (`ASAC`, `CCAM`, `ARGUS`, `CIMA`) |
| `prix_ref_xaf` | FLOAT | NULLABLE | Prix de référence en XAF |
| `prix_ref_eur` | FLOAT | NULLABLE | Prix de référence en EUR |
| `devise_principale` | VARCHAR(5) | NOT NULL | Devise principale (`XAF` ou `EUR`) |
| `valid_from` | DATE | NOT NULL | Début de validité du tarif |
| `valid_to` | DATE | NULLABLE | Fin de validité (null = tarif actuel) |
| `source_document` | VARCHAR(255) | NULLABLE | Référence du document officiel source |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date d'import |

**Index :** `idx_ref_prices_code_acte` sur `(branch_id, code_acte)`, `idx_ref_prices_valid` sur `(code_acte, valid_from, valid_to)`  
**Notes :** Plusieurs prix peuvent coexister pour un même code (historique). La version active est celle dont `valid_to IS NULL` ou `valid_to >= CURRENT_DATE`.

---

## DOMAINE 3 — Sinistres & Documents
> 4 tables — le cœur du domaine métier

---

### Table `claims`
**Rôle :** Dossiers sinistres. Table centrale du domaine métier. Un sinistre passe par plusieurs états depuis sa création jusqu'à sa clôture.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant interne |
| `claim_id` | VARCHAR(100) | UNIQUE, NOT NULL | Identifiant métier (ex : `SIN_2025_CM_00842`) |
| `contract_id` | UUID | FK → contracts.id, NULLABLE | Contrat associé (null si contrat non retrouvé) |
| `branch_id` | UUID | GEN, NOT NULL | Dérivé de `contracts.branch_id` — colonne générée |
| `source_flux` | VARCHAR(20) | NOT NULL, CHECK IN ('structured','documentary','batch') | Origine du dossier |
| `montant_facture` | FLOAT | NULLABLE | Montant déclaré en devise d'origine |
| `devise` | VARCHAR(5) | NULLABLE, DEFAULT 'XAF' | Devise (`XAF`, `EUR`) |
| `montant_xaf` | FLOAT | NULLABLE | Montant converti en XAF (calculé par le normalizer) |
| `date_soin` | DATE | NULLABLE | Date des soins ou du sinistre |
| `date_declaration` | DATE | NULLABLE | Date de déclaration à l'assureur |
| `date_saisie` | DATE | NULLABLE | Date de saisie dans le système |
| `heure_saisie` | INTEGER | NULLABLE, CHECK >= 0 AND <= 23 | Heure de saisie |
| `statut` | VARCHAR(20) | NOT NULL, DEFAULT 'DRAFT' | État administratif : `DRAFT`, `SUBMITTED`, `OPEN`, `CLOSED` |
| `created_by` | UUID | FK → users.id, NULLABLE | Utilisateur créateur (null si import automatique) |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de création |
| `updated_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Dernière modification |

**Cycle de vie `statut` :**
```
DRAFT     → Le gestionnaire a commencé la saisie, pas encore soumis
SUBMITTED → Soumis à l'analyse IA
OPEN      → Analyse terminée, décision humaine en attente ou en cours
CLOSED    → Décision finale prise (CONFIRMED ou REJECTED)
```

**Index :** `idx_claims_claim_id` sur `claim_id`, `idx_claims_branch` sur `branch_id`, `idx_claims_statut` sur `statut`, `idx_claims_date_soin` sur `date_soin`

---

### Table `claim_lines`
**Rôle :** Lignes de détail d'un sinistre. Pour la Santé : actes médicaux. Pour l'Auto : postes de réparation.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `claim_id` | UUID | FK → claims.id, NOT NULL | Sinistre parent |
| `code_acte` | VARCHAR(50) | NULLABLE | Code de l'acte (ASAC, CCAM, code réparation) |
| `libelle` | TEXT | NULLABLE | Description de la ligne |
| `montant_ligne` | FLOAT | NULLABLE | Montant facturé pour cette ligne |
| `prix_ref` | FLOAT | NULLABLE | Prix de référence mercuriale au moment de la liquidation |
| `ratio_prix` | FLOAT | NULLABLE | `montant_ligne / prix_ref` — calculé à l'ingestion |
| `quantite` | INTEGER | NULLABLE, DEFAULT 1 | Quantité d'actes ou de pièces |
| `praticien_id_hash` | VARCHAR(64) | NULLABLE | Hash du praticien (référence souple vers practitioners.id_hash) |
| `garage_id_hash` | VARCHAR(64) | NULLABLE | Hash du garage (référence souple vers garages.id_hash) |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de création |

**Notes :** Les références vers `practitioners` et `garages` sont intentionnellement souples (pas de FK formelle) car un praticien peut apparaître dans un sinistre sans avoir de fiche dans la table. L'enrichissement est asynchrone.

---

### Table `claim_documents`
**Rôle :** Documents justificatifs attachés à un sinistre (factures scannées, constats, expertises).

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `claim_id` | UUID | FK → claims.id, NOT NULL | Sinistre parent |
| `filename` | VARCHAR(255) | NOT NULL | Nom de fichier original |
| `file_path` | VARCHAR(500) | NOT NULL | Chemin relatif au volume `./data/documents/` |
| `mime_type` | VARCHAR(100) | NOT NULL | Type MIME (`application/pdf`, `image/jpeg`, etc.) |
| `file_size_bytes` | BIGINT | NOT NULL | Taille en octets |
| `hash_sha256` | VARCHAR(64) | NOT NULL | Hash SHA-256 du fichier pour intégrité |
| `document_type` | VARCHAR(50) | NULLABLE | Type métier (`facture`, `constat`, `expertise`, `ordonnance`) |
| `uploaded_by` | UUID | FK → users.id, NULLABLE | Utilisateur ayant uploadé (null si import automatique) |
| `uploaded_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date d'upload |

**Index :** `idx_claim_documents_claim` sur `claim_id`  
**Notes :** `file_path` est relatif — ex : `sante/2026/05/SIN_2025_CM_00842_facture.pdf`. Le préfixe absolu est en variable d'environnement `MAKORA_DOCUMENTS_PATH`.

---

### Table `ocr_extractions`
**Rôle :** Résultats du pipeline OCR documentaire (dual PaddleOCR + Tesseract + LLM). Preuve forensique immuable.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `document_id` | UUID | FK → claim_documents.id, NOT NULL | Document source |
| `score_confiance_global` | FLOAT | NOT NULL, CHECK >= 0 AND <= 1 | Score de confiance moyen global |
| `score_confiance_montant` | FLOAT | NOT NULL, CHECK >= 0 AND <= 1 | Score de confiance sur le token montant |
| `montant_extrait` | FLOAT | NULLABLE | Montant extrait par le LLM |
| `devise_extraite` | VARCHAR(5) | NULLABLE | Devise extraite (normalisée en XAF) |
| `date_soin_extraite` | DATE | NULLABLE | Date de soin extraite (format YYYY-MM-DD) |
| `code_acte_extrait` | VARCHAR(50) | NULLABLE | Code ASAC ou CCAM extrait |
| `nom_praticien_extrait` | VARCHAR(255) | NULLABLE | Nom du praticien tel qu'extrait |
| `etablissement_extrait` | VARCHAR(255) | NULLABLE | Établissement tel qu'extrait |
| `presence_cachet` | BOOLEAN | NOT NULL, DEFAULT false | Cachet humide détecté (HSV OpenCV) |
| `flag_altere` | BOOLEAN | NOT NULL, DEFAULT false | Document retouché (EXIF Photoshop/GIMP/etc.) |
| `logiciel_retouche` | VARCHAR(100) | NULLABLE | Nom du logiciel de retouche détecté |
| `hash_image` | VARCHAR(64) | NOT NULL | SHA-256 de l'image originale |
| `llm_backend_used` | VARCHAR(50) | NOT NULL | Backend LLM utilisé (`deepseek`, `ollama`) |
| `paddle_text_length` | INTEGER | NULLABLE | Longueur du texte extrait par PaddleOCR |
| `tesseract_text_length` | INTEGER | NULLABLE | Longueur du texte extrait par Tesseract |
| `success` | BOOLEAN | NOT NULL | Pipeline OCR terminé avec succès |
| `error_code` | VARCHAR(50) | NULLABLE | Code erreur si `success=false` (`QUALITE_INSUFFISANTE`, `LLM_KO`, etc.) |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Horodatage forensique de l'extraction |

**Notes d'immuabilité :** Aucune UPDATE n'est autorisée sur cette table après création. Les corrections se font par insertion d'une nouvelle ligne (re-OCR).

---

## DOMAINE 4 — Pipeline ML
> 4 tables — versioning des modèles et résultats d'analyse

---

### Table `model_versions`
**Rôle :** Catalogue de tous les modèles ML entraînés. Ne contient pas d'indicateur de production — c'est la table `production_deployments` qui gère ça.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `branch_id` | UUID | FK → branches.id, NOT NULL | Branche concernée |
| `algorithm` | VARCHAR(50) | NOT NULL | Algorithme (`isolation_forest`, `lof`, `ocsvm`) |
| `version_tag` | VARCHAR(50) | NOT NULL | Tag de version (ex : `v1.0.0`, `M_sante_phase2`) |
| `file_path` | VARCHAR(500) | NOT NULL | Chemin relatif vers le fichier `.joblib` |
| `feature_names` | JSONB | NOT NULL | Liste des features utilisées à l'entraînement |
| `contamination` | FLOAT | NOT NULL | Contamination utilisée à l'entraînement |
| `f1_score` | FLOAT | NULLABLE | F1-score sur le test set |
| `auc_roc` | FLOAT | NULLABLE | AUC-ROC sur le test set |
| `precision_ppv` | FLOAT | NULLABLE | Précision (PPV) |
| `recall_tpr` | FLOAT | NULLABLE | Rappel (TPR) |
| `fpr` | FLOAT | NULLABLE | False Positive Rate |
| `mcc` | FLOAT | NULLABLE | Matthews Correlation Coefficient |
| `train_size` | INTEGER | NULLABLE | Nombre de lignes d'entraînement |
| `trained_at` | TIMESTAMP WITH TIME ZONE | NOT NULL | Date d'entraînement |
| `created_by` | UUID | FK → users.id, NULLABLE | Administrateur ayant déclenché l'entraînement |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date d'enregistrement |

---

### Table `production_deployments`
**Rôle :** Gère quel modèle est en production pour chaque branche. Conserve l'historique complet des déploiements — on peut savoir quel modèle était actif à une date précise.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `branch_id` | UUID | FK → branches.id, NOT NULL | Branche concernée |
| `model_version_id` | UUID | FK → model_versions.id, NOT NULL | Modèle déployé |
| `deployed_by` | UUID | FK → users.id, NOT NULL | Administrateur ayant déployé |
| `deployed_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de déploiement |
| `replaced_at` | TIMESTAMP WITH TIME ZONE | NULLABLE | Date de remplacement par un autre modèle (null = actif) |
| `deployment_notes` | TEXT | NULLABLE | Notes de déploiement |

**Contrainte d'unicité partielle :** `UNIQUE (branch_id) WHERE replaced_at IS NULL` — un seul modèle actif par branche à tout moment.  
**Requête pour obtenir le modèle actif :**
```sql
SELECT model_version_id FROM production_deployments
WHERE branch_id = $1 AND replaced_at IS NULL;
```

---

### Table `analysis_runs`
**Rôle :** Représente une session de détection complète — un batch de dossiers analysés ensemble. Permet de lier les communautés de graphe à leur contexte d'analyse.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `branch_id` | UUID | FK → branches.id, NOT NULL | Branche analysée |
| `model_version_id` | UUID | FK → model_versions.id, NOT NULL | Modèle utilisé |
| `run_type` | VARCHAR(20) | NOT NULL, CHECK IN ('single','batch','reanalysis') | Type de run |
| `nb_dossiers` | INTEGER | NOT NULL, DEFAULT 0 | Nombre de dossiers dans ce run |
| `nb_anomalies` | INTEGER | NOT NULL, DEFAULT 0 | Nombre d'anomalies détectées |
| `graph_enabled` | BOOLEAN | NOT NULL, DEFAULT false | Analyse de graphe activée pour ce run |
| `started_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Début du run |
| `completed_at` | TIMESTAMP WITH TIME ZONE | NULLABLE | Fin du run (null si en cours) |
| `triggered_by` | UUID | FK → users.id, NULLABLE | Utilisateur déclencheur (null si automatique) |

---

### Table `analyses`
**Rôle :** Résultats du pipeline MAKORA pour chaque dossier analysé. Table centrale des résultats IA.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `claim_id` | UUID | FK → claims.id, NOT NULL | Sinistre analysé |
| `run_id` | UUID | FK → analysis_runs.id, NOT NULL | Session d'analyse parente |
| `branch_id` | UUID | FK → branches.id, NOT NULL | Branche |
| `model_version_id` | UUID | FK → model_versions.id, NOT NULL | Modèle utilisé |
| `ocr_extraction_id` | UUID | FK → ocr_extractions.id, NULLABLE | Résultat OCR associé (null si flux structuré) |
| `fraud_community_id` | UUID | FK → fraud_communities.id, NULLABLE | Communauté de fraude détectée (null si aucune) |
| `anomaly_score` | FLOAT | NOT NULL, CHECK >= 0 AND <= 1 | Score d'anomalie normalisé |
| `is_anomaly` | BOOLEAN | NOT NULL | True si score >= seuil de la branche |
| `detector_name` | VARCHAR(50) | NOT NULL | Nom de l'algorithme (`isolation_forest`, `lof`) |
| `rca_category` | VARCHAR(100) | NULLABLE | Catégorie RCA (`Fraude Intentionnelle`, etc.) |
| `rca_subcategory` | VARCHAR(200) | NULLABLE | Sous-catégorie RCA |
| `rca_confidence` | FLOAT | NULLABLE, CHECK >= 0 AND <= 1 | Confiance du diagnostic RCA |
| `rca_rule_id` | VARCHAR(50) | NULLABLE | Identifiant de la règle RCA déclenchée |
| `explanation_fr` | TEXT | NULLABLE | Narration LLM en français |
| `decision_status` | VARCHAR(20) | NOT NULL, DEFAULT 'PENDING' | Décision humaine : `PENDING`, `CONFIRMED`, `REJECTED`, `ESCALATED` |
| `processing_time_ms` | FLOAT | NULLABLE | Temps de traitement en millisecondes |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Horodatage de l'analyse |

**Index :** `idx_analyses_claim` sur `claim_id`, `idx_analyses_branch_status` sur `(branch_id, decision_status)`, `idx_analyses_is_anomaly` sur `is_anomaly`, `idx_analyses_created_at` sur `created_at`

---

### Table `shap_contributions`
**Rôle :** Valeurs SHAP détaillées par feature et par analyse. Séparées de `analyses` pour permettre des requêtes analytiques (ex : "quelle feature déclenche le plus d'anomalies ?").

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `analysis_id` | UUID | FK → analyses.id, NOT NULL | Analyse parente |
| `feature_name` | VARCHAR(100) | NOT NULL | Nom de la feature |
| `shap_value` | FLOAT | NOT NULL | Valeur SHAP (positive = contribue à l'anomalie) |
| `feature_value` | FLOAT | NULLABLE | Valeur réelle de la feature pour ce dossier |
| `direction` | VARCHAR(10) | NOT NULL, CHECK IN ('positive','negative') | Direction de contribution |
| `rank` | INTEGER | NOT NULL, CHECK >= 1 | Rang parmi les features (1 = plus contributive) |

**Index :** `idx_shap_analysis` sur `analysis_id`, `idx_shap_feature` sur `feature_name`

---

## DOMAINE 5 — Human-in-the-Loop
> 2 tables — décisions et escalades

---

### Table `decisions`
**Rôle :** Décisions prises par les gestionnaires sur les analyses. Chaque décision est immuable — on n'édite pas, on crée une nouvelle décision si besoin.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `analysis_id` | UUID | FK → analyses.id, NOT NULL | Analyse concernée |
| `decision` | VARCHAR(20) | NOT NULL, CHECK IN ('CONFIRMED','REJECTED','ESCALATED') | Type de décision |
| `motif` | TEXT | NULLABLE | Justification libre du gestionnaire |
| `gestionnaire_id` | UUID | FK → users.id, NOT NULL | Gestionnaire décideur |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Horodatage de la décision |

**Notes :** Plusieurs décisions peuvent exister pour une même analyse (historique). La décision active est la plus récente. La mise à jour de `analyses.decision_status` est déclenchée par trigger après insertion dans `decisions`.

---

### Table `escalations`
**Rôle :** Dossiers escaladés à un auditeur senior pour investigation approfondie.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `analysis_id` | UUID | FK → analyses.id, NOT NULL | Analyse escaladée |
| `escalated_by` | UUID | FK → users.id, NOT NULL | Gestionnaire ayant escaladé |
| `assigned_to` | UUID | FK → users.id, NULLABLE | Auditeur assigné (null si non encore assigné) |
| `motif_escalade` | TEXT | NOT NULL | Raison de l'escalade |
| `statut` | VARCHAR(20) | NOT NULL, DEFAULT 'PENDING' | État : `PENDING`, `IN_PROGRESS`, `RESOLVED` |
| `resolution_note` | TEXT | NULLABLE | Conclusion de l'auditeur |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date d'escalade |
| `assigned_at` | TIMESTAMP WITH TIME ZONE | NULLABLE | Date d'assignation |
| `resolved_at` | TIMESTAMP WITH TIME ZONE | NULLABLE | Date de résolution |

---

## DOMAINE 6 — Graphe de Fraude
> 2 tables — détection de communautés suspectes

---

### Table `fraud_communities`
**Rôle :** Communautés d'entités suspectes détectées par l'algorithme Louvain [Blondel2008] durant un analysis_run.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `run_id` | UUID | FK → analysis_runs.id, NOT NULL | Session d'analyse ayant produit cette communauté |
| `branch_id` | UUID | FK → branches.id, NOT NULL | Branche concernée |
| `community_id_louvain` | INTEGER | NOT NULL | ID numérique attribué par Louvain (local au run) |
| `size` | INTEGER | NOT NULL, CHECK >= 2 | Nombre de nœuds dans la communauté |
| `density` | FLOAT | NOT NULL, CHECK >= 0 AND <= 1 | Densité du sous-graphe |
| `modularity` | FLOAT | NULLABLE | Score de modularité Louvain |
| `avg_weight` | FLOAT | NULLABLE | Poids moyen des arêtes |
| `is_suspicious` | BOOLEAN | NOT NULL | True si densité >= seuil YAML |
| `suspicion_score` | FLOAT | NOT NULL, CHECK >= 0 AND <= 1 | Score de suspicion normalisé [0,1] |
| `reason` | TEXT | NULLABLE | Explication de la suspicion |
| `detected_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Horodatage de détection |

---

### Table `community_members`
**Rôle :** Membres (nœuds) de chaque communauté de fraude détectée.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `community_id` | UUID | FK → fraud_communities.id, NOT NULL | Communauté parente |
| `entity_type` | VARCHAR(30) | NOT NULL, CHECK IN ('praticien','assure','garage','employeur') | Type d'entité |
| `entity_id_hash` | VARCHAR(64) | NOT NULL | Hash pseudonymisé de l'entité |
| `node_score` | FLOAT | NOT NULL, CHECK >= 0 AND <= 1 | Score individuel du nœud dans la communauté |
| `is_central` | BOOLEAN | NOT NULL, DEFAULT false | Nœud central de la communauté |

**Index :** `idx_community_members_community` sur `community_id`, `idx_community_members_entity` sur `(entity_type, entity_id_hash)`

---

## DOMAINE 7 — Monitoring & Gouvernance
> 3 tables — drift, réentraînement

---

### Table `drift_reports`
**Rôle :** Rapports PSI calculés périodiquement ou manuellement pour détecter le drift des données [Gama2014].

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `branch_id` | UUID | FK → branches.id, NOT NULL | Branche concernée |
| `status` | VARCHAR(10) | NOT NULL, CHECK IN ('STABLE','WARNING','CRITICAL') | Statut global PSI |
| `psi_max` | FLOAT | NOT NULL | PSI maximum parmi toutes les features |
| `n_features_analyzed` | INTEGER | NOT NULL | Nombre de features analysées |
| `n_features_warning` | INTEGER | NOT NULL, DEFAULT 0 | Features en WARNING (PSI 0.10-0.20) |
| `n_features_critical` | INTEGER | NOT NULL, DEFAULT 0 | Features en CRITICAL (PSI > 0.20) |
| `reference_window_days` | INTEGER | NOT NULL, DEFAULT 90 | Fenêtre de référence en jours |
| `current_window_days` | INTEGER | NOT NULL, DEFAULT 30 | Fenêtre courante en jours |
| `triggered_by` | UUID | FK → users.id, NULLABLE | Utilisateur déclencheur (null si cron automatique) |
| `computed_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Horodatage du calcul |

---

### Table `drift_feature_metrics`
**Rôle :** Détail PSI par feature pour chaque rapport de drift.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `report_id` | UUID | FK → drift_reports.id, NOT NULL | Rapport parent |
| `feature_name` | VARCHAR(100) | NOT NULL | Nom de la feature |
| `psi_value` | FLOAT | NOT NULL, CHECK >= 0 | Valeur PSI |
| `status` | VARCHAR(10) | NOT NULL, CHECK IN ('STABLE','WARNING','CRITICAL','UNKNOWN') | Statut de la feature |
| `n_reference` | INTEGER | NOT NULL | Nombre d'observations dans la fenêtre de référence |
| `n_current` | INTEGER | NOT NULL | Nombre d'observations dans la fenêtre courante |

**Index :** `idx_drift_feature_report` sur `report_id`

---

### Table `retraining_requests`
**Rôle :** Demandes de réentraînement d'un modèle, déclenchées manuellement ou automatiquement par un rapport de drift critique.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `branch_id` | UUID | FK → branches.id, NOT NULL | Branche concernée |
| `drift_report_id` | UUID | FK → drift_reports.id, NULLABLE | Rapport drift déclencheur (null si demande manuelle) |
| `reason` | TEXT | NOT NULL | Justification de la demande |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'PENDING' | État : `PENDING`, `APPROVED`, `IN_PROGRESS`, `DONE`, `REJECTED` |
| `requested_by` | UUID | FK → users.id, NOT NULL | Demandeur (administrateur ou système) |
| `approved_by` | UUID | FK → users.id, NULLABLE | Approbateur |
| `new_model_version_id` | UUID | FK → model_versions.id, NULLABLE | Nouveau modèle produit (renseigné après DONE) |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de la demande |
| `approved_at` | TIMESTAMP WITH TIME ZONE | NULLABLE | Date d'approbation |
| `completed_at` | TIMESTAMP WITH TIME ZONE | NULLABLE | Date de completion |

---

## DOMAINE 8 — Audit & Configuration
> 4 tables — traçabilité, exports, versioning YAML

---

### Table `audit_logs`
**Rôle :** Journal immuable de toutes les actions utilisateurs et système. Conformité CIMA (conservation 10 ans) et RGPD.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `user_id` | UUID | FK → users.id, NULLABLE | Utilisateur acteur (null si action système) |
| `action` | VARCHAR(100) | NOT NULL | Action effectuée (ex : `claim:created`, `analysis:run`, `decision:confirmed`) |
| `resource_type` | VARCHAR(50) | NOT NULL | Type de ressource (`claim`, `analysis`, `model`, `user`, `module`) |
| `resource_id` | VARCHAR(100) | NULLABLE | Identifiant de la ressource concernée |
| `payload` | JSONB | NULLABLE | Détails de l'action (valeurs avant/après pour les modifications) |
| `ip_address` | VARCHAR(45) | NULLABLE | Adresse IP de l'acteur |
| `result` | VARCHAR(10) | NOT NULL, CHECK IN ('SUCCESS','FAILURE') | Résultat de l'action |
| `error_message` | TEXT | NULLABLE | Message d'erreur si `result = FAILURE` |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Horodatage UTC |

**Politique d'immuabilité (Row Level Security PostgreSQL) :**
```sql
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY audit_insert_only ON audit_logs
  FOR INSERT TO makora_api_role WITH CHECK (true);
-- Aucune policy pour SELECT/UPDATE/DELETE → opérations bloquées par défaut
-- Seul le rôle superadmin peut lire pour les exports de conformité
```

**Index :** `idx_audit_user` sur `user_id`, `idx_audit_action` sur `action`, `idx_audit_created` sur `created_at`

---

### Table `export_reports`
**Rôle :** Rapports d'audit exportés par les auditeurs (UC-14). Stocke les métadonnées et le chemin relatif du fichier généré.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `requested_by` | UUID | FK → users.id, NOT NULL | Auditeur demandeur |
| `report_type` | VARCHAR(50) | NOT NULL | Type (`audit_decisions`, `anomaly_summary`, `drift_history`, `community_fraud`) |
| `branch_filter` | VARCHAR(20) | NULLABLE | Filtre branche appliqué |
| `decision_filter` | VARCHAR(20) | NULLABLE | Filtre décision appliqué |
| `date_from` | DATE | NULLABLE | Début de la période couverte |
| `date_to` | DATE | NULLABLE | Fin de la période couverte |
| `file_path` | VARCHAR(500) | NULLABLE | Chemin relatif au volume `./data/exports/` |
| `file_format` | VARCHAR(10) | NOT NULL, DEFAULT 'csv' | Format (`csv`, `xlsx`, `json`) |
| `row_count` | INTEGER | NULLABLE | Nombre de lignes dans le rapport |
| `status` | VARCHAR(20) | NOT NULL, DEFAULT 'PENDING' | État : `PENDING`, `GENERATING`, `READY`, `FAILED` |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de la demande |
| `completed_at` | TIMESTAMP WITH TIME ZONE | NULLABLE | Date de completion |

**Notes :** `file_path` est relatif — ex : `exports/2026/05/audit_sante_20260530.csv`. Le préfixe absolu est en variable d'environnement `MAKORA_DATA_PATH`.

---

### Table `module_configs`
**Rôle :** Snapshots versionnés du contenu YAML de chaque module. Permet de savoir quelle version de la configuration était active lors d'une analyse.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `branch_id` | UUID | FK → branches.id, NOT NULL | Branche concernée |
| `version_tag` | VARCHAR(50) | NOT NULL | Version du YAML (ex : `v0.4.0`) |
| `yaml_content` | TEXT | NOT NULL | Contenu complet du fichier YAML |
| `yaml_hash` | VARCHAR(64) | NOT NULL | SHA-256 du contenu YAML (vérification d'intégrité) |
| `is_active` | BOOLEAN | NOT NULL, DEFAULT true | Configuration actuellement chargée |
| `created_by` | UUID | FK → users.id, NULLABLE | Administrateur ayant chargé cette config |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date de chargement |

**Contrainte d'unicité partielle :** `UNIQUE (branch_id) WHERE is_active = true` — une seule config active par branche.

---

### Table `rca_rule_snapshots`
**Rôle :** Règles RCA extraites des snapshots YAML. Permet les requêtes analytiques sur les règles sans parser le YAML.

| Colonne | Type | Contrainte | Description |
|---|---|---|---|
| `id` | UUID | PK, NOT NULL | Identifiant unique |
| `module_config_id` | UUID | FK → module_configs.id, NOT NULL | Config YAML parente |
| `rule_id` | VARCHAR(50) | NOT NULL | Identifiant de la règle (ex : `RCA_SURF_001`) |
| `category` | VARCHAR(100) | NOT NULL | Catégorie (`Fraude Intentionnelle`, `Erreur Opérationnelle`, etc.) |
| `subcategory` | VARCHAR(200) | NOT NULL | Sous-catégorie |
| `conditions` | JSONB | NOT NULL | Conditions de déclenchement sérialisées |
| `confidence_base` | FLOAT | NOT NULL, CHECK >= 0 AND <= 1 | Confiance de base de la règle |
| `priority` | INTEGER | NOT NULL, CHECK >= 1 | Priorité d'évaluation |
| `logic` | VARCHAR(5) | NOT NULL, CHECK IN ('AND','OR') | Logique de combinaison des conditions |
| `created_at` | TIMESTAMP WITH TIME ZONE | NOT NULL, DEFAULT now() | Date d'extraction |

---

## Récapitulatif complet

| # | Domaine | Table | Rôle en une ligne |
|---|---|---|---|
| 1 | IAM | `users` | Utilisateurs du système |
| 2 | IAM | `roles` | Rôles disponibles |
| 3 | IAM | `permissions` | Permissions granulaires |
| 4 | IAM | `user_roles` | Attribution rôles aux utilisateurs |
| 5 | IAM | `role_permissions` | Attribution permissions aux rôles |
| 6 | IAM | `sessions` | Refresh tokens JWT |
| 7 | Référentiels | `branches` | Branches d'assurance MAKORA |
| 8 | Référentiels | `insureds` | Assurés pseudonymisés |
| 9 | Référentiels | `contracts` | Polices d'assurance |
| 10 | Référentiels | `practitioners` | Praticiens médicaux (Santé) |
| 11 | Référentiels | `garages` | Garages réparateurs (Auto) |
| 12 | Référentiels | `employers` | Employeurs des assurés |
| 13 | Référentiels | `insured_employers` | Historique employeurs par assuré |
| 14 | Référentiels | `reference_prices` | Mercuriales ASAC/CCAM/Argus |
| 15 | Sinistres | `claims` | Dossiers sinistres |
| 16 | Sinistres | `claim_lines` | Lignes de détail (actes/pièces) |
| 17 | Sinistres | `claim_documents` | Documents justificatifs |
| 18 | Sinistres | `ocr_extractions` | Résultats OCR forensiques immuables |
| 19 | Pipeline ML | `model_versions` | Catalogue des modèles entraînés |
| 20 | Pipeline ML | `production_deployments` | Historique des déploiements production |
| 21 | Pipeline ML | `analysis_runs` | Sessions d'analyse (batch ou single) |
| 22 | Pipeline ML | `analyses` | Résultats MAKORA par dossier |
| 23 | Pipeline ML | `shap_contributions` | Valeurs SHAP détaillées |
| 24 | HITL | `decisions` | Décisions gestionnaires |
| 25 | HITL | `escalations` | Escalades vers auditeurs |
| 26 | Graphe | `fraud_communities` | Communautés suspectes Louvain |
| 27 | Graphe | `community_members` | Membres des communautés |
| 28 | Monitoring | `drift_reports` | Rapports PSI globaux |
| 29 | Monitoring | `drift_feature_metrics` | PSI détaillé par feature |
| 30 | Monitoring | `retraining_requests` | Demandes de réentraînement |
| 31 | Audit | `audit_logs` | Journal immuable (RLS PostgreSQL) |
| 32 | Audit | `export_reports` | Rapports exportés |
| 33 | Config | `module_configs` | Snapshots YAML versionnés |
| 34 | Config | `rca_rule_snapshots` | Règles RCA extraites |

---

## Décisions d'architecture retenues

| Problème | Décision | Justification |
|---|---|---|
| Double statut sinistre/analyse | `claims.statut` (DRAFT→CLOSED) + `analyses.decision_status` (PENDING→CONFIRMED) | Deux concepts distincts |
| Lien analyses → claims | FK formelle UUID | Cohérence garantie par PostgreSQL |
| OCR dupliqué | FK `analyses.ocr_extraction_id → ocr_extractions.id` | Source unique de vérité |
| Graphe dupliqué | FK nullable `analyses.fraud_community_id → fraud_communities.id` | Source unique de vérité |
| Modèle production ambigu | Table `production_deployments` dédiée | Historique + unicité partielle |
| Lien communautés → analyses | Table `analysis_runs` intermédiaire | Batch ≠ dossier individuel |
| Employeurs sans lien assurés | Table `insured_employers` avec historique | Changements d'employeur possibles |
| Sessions vs JWT | JWT + refresh tokens dans `sessions` | Standard production, révocation possible |
| Cycle de vie sinistre | `DRAFT → SUBMITTED → OPEN → CLOSED` | Couvre saisie manuelle + import batch |
| `branch_id` redondant | Colonne générée depuis `contracts.branch_id` | Performance + cohérence automatique |
| Audit immuable | Row Level Security PostgreSQL | Plus robuste que trigger |
| Chemins fichiers fragiles | Chemins relatifs + variable d'environnement | Résistant aux reconfigurations Docker |

---

*MAKORA_DATABASE_SCHEMA.md — v1.0*  
*ATABONG EFON STEPHANE FRITZ — 30 mai 2026*
