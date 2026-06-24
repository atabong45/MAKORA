# CONTEXTE PROJET — MÉMOIRE INGÉNIEUR DE CONCEPTION
> Fichier de transfert de contexte entre sessions IA  
> Généré le : 17 avril 2026  
> Auteur : ATABONG EFON STEPHANE FRITZ  
> Entreprise d'accueil : ITNS Nearshore Services  
> Année académique : 2025-2026

---

## 0. INSTRUCTIONS POUR LE MODÈLE IA QUI LIT CE FICHIER

Tu travailles avec un étudiant ingénieur en fin de cycle sur son mémoire de fin d'études.
Voici tout ce que tu dois savoir pour être immédiatement opérationnel :

- **Vitesse de travail** : Le facteur ×5 est une réalité à maintenir comme référence. Ce que l'étudiant moyen fait en 1 semaine, cet étudiant le fait en 1 jour effectif (grâce à Claude + Cursor). **Toujours calibrer les estimations de temps sur cette base.**
- **Ton attendu** : Franc, direct, exigeant. Ne pas faire dans la complaisance. Pointer les problèmes clairement.
- **Ambition** : Ce mémoire doit être **remarquable**, pas juste suffisant.
- **Rôle de l'IA** : Générer du code (Claude/Cursor), valider et adapter. L'étudiant pilote, l'IA exécute.
- **Rédaction du mémoire** : Externalisée à l'encadreur académique. Ce fichier ne couvre pas la rédaction.

---

## 1. IDENTITÉ DU PROJET

### Titre officiel du mémoire
> **Conception d'un framework générique et extensible de détection d'anomalies par intelligence artificielle en assurance : architecture, implémentation et validation sur les marchés hybrides Afrique-Europe**

### Question de recherche directrice (structure les chapitres)
> **Dans quelle mesure une architecture orientée plugins à schéma déclaratif permet-elle de généraliser la détection d'anomalies et la Root Cause Analysis à des branches d'assurance hétérogènes, tout en maintenant la précision de détection et l'intelligibilité des diagnostics pour les gestionnaires métiers ?**

### Ce que le projet prouve
La **généricité** : un seul système IA capable de s'instancier sur n'importe quelle branche d'assurance (Santé, Auto, Vie, Agricole…) sans modifier le moteur central.

---

## 2. CONCEPT FONDAMENTAL — LE FRAMEWORK

### Métaphore clé
Le framework = une **prise électrique universelle**.  
La prise murale (moteur ML) est fixe. Ce qu'on branche (module Santé, Auto, Vie…) peut changer. Tout appareil respectant le format de la prise fonctionne immédiatement.

### Ce que "framework" signifie ici
PAS React ou Django.  
= Un ensemble de règles, contrats et briques réutilisables **conçu par l'étudiant**, dans lequel des modules métiers peuvent s'insérer sans tout recasser.

### Architecture en 3 niveaux

```
┌─────────────────────────────────────────────┐
│     NIVEAU 3 : PRÉSENTATION                 │
│     Dashboard universel (Next.js)           │
│     S'adapte automatiquement à la branche   │
└─────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────┐
│     NIVEAU 2 : MOTEUR GÉNÉRIQUE             │
│     Pipeline ML universel (FastAPI)         │
│     Isolation Forest + SHAP + RCA Engine    │
│     + Mistral 7B (narration)                │
│     Identique pour toutes les branches      │
└─────────────────────────────────────────────┘
                      │
┌─────────────────────────────────────────────┐
│     NIVEAU 1 : MODULES MÉTIERS (Plugins)    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │  Santé   │ │   Auto   │ │   Vie    │    │
│  │(complet) │ │(complet) │ │(conçu)   │    │
│  └──────────┘ └──────────┘ └──────────┘    │
│                        ┌──────────┐         │
│                        │Agricole  │         │
│                        │(conçu)   │         │
│                        └──────────┘         │
└─────────────────────────────────────────────┘
```

---

## 3. DÉCISIONS TECHNIQUES VALIDÉES

### 3.1 Stack technologique finale

| Couche | Technologie | Justification |
|--------|------------|---------------|
| Backend API | **FastAPI** | Natif async, 3-10× plus rapide que DRF, standard industrie ML, Swagger auto |
| ORM | **SQLAlchemy + Alembic** | Plus flexible que Django ORM pour ce cas |
| Base de données | **PostgreSQL** | — |
| Tâches async | **Celery + Redis** | Inférences ML longues en arrière-plan |
| Stockage fichiers | **MinIO** | Équivalent S3 auto-hébergé, pour scans/factures |
| Frontend | **Next.js + TypeScript** | Stack principale de l'étudiant, meilleur choix |
| State management | **Zustand** | Plus léger que Redux pour ce cas |
| Data fetching | **TanStack Query** | Cache + appels API |
| UI Components | **Shadcn/ui** | Propre, accessible |
| Visualisations | **Recharts ou Tremor** | Graphiques SHAP, scores |
| ML détection | **Scikit-learn** (Isolation Forest) | — |
| Explicabilité | **SHAP** | — |
| Data processing | **Pandas + Polars** | Polars pour gros datasets (10× plus rapide) |
| Validation schémas | **Pydantic** | Intégration native FastAPI |
| LLM local | **Mistral 7B via Ollama** | ~4,1 Go en Q4, meilleur que Gemma 3 4B en français |
| Infrastructure | **Docker + Docker Compose** | Tout containerisé, tourne local |

> **IMPORTANT** : Django est abandonné au profit de FastAPI. L'ancien code Django (models, serializers, views, services) existe dans les PDF mais ne sera PAS réutilisé tel quel dans la nouvelle architecture.

### 3.2 Modules — Statut d'implémentation

| Module | Statut | Dataset | Notes |
|--------|--------|---------|-------|
| **Santé** | Implémentation complète | ✅ 140 225 lignes prêt | Dataset existant réutilisable + adaptations |
| **Auto** | Implémentation complète | À constituer | French Motor Claims (Kaggle) + synthétique Cameroun |
| **Vie** | Conception seulement | Non requis | Schéma + anomalies + règles RCA documentés |
| **Agricole** | Conception seulement | Non requis | Spécificités Cameroun documentées, gap données assumé |

### 3.3 Pipeline ML — Séquence universelle

```
Données brutes
    ↓
[1] Couche Mapping          → fichier mapping.yaml par source (gère colonnes mal nommées)
    ↓
[2] Validation Schéma       → Pydantic vérifie colonnes requises vs optionnelles
    ↓
[3] Normalisation            → encodage catégorielles, normalisation montants
    ↓
[4] Feature Engineering      → features spécifiques au module (ratio_prix, flag_post_mortem…)
    ↓
[5] Isolation Forest         → score anomalie 0-1, marqueur booléen
    ↓
[6] SHAP                     → vecteur contribution par feature
    ↓
[7] Moteur RCA (règles YAML) → croise SHAP + règles métier → catégorie + sous-catégorie
    ↓
[8] Mistral 7B               → reçoit contexte structuré → produit explication en français naturel
    ↓
[9] Sortie JSON standardisée → même format pour TOUTES les branches
```

### 3.4 Format de sortie standardisé (toutes branches)

```json
{
  "claim_id": "SIN_2025_001",
  "branch": "sante",
  "anomaly_score": 0.87,
  "is_anomaly": true,
  "rca": {
    "cause": "Surfacturation prestataire",
    "category": "Fraude Intentionnelle",
    "confidence": 0.91,
    "top_features": ["ratio_prix_mercuriale", "montant_facture"],
    "explanation_fr": "Le montant facturé dépasse de 73% le tarif mercuriale..."
  }
}
```

### 3.5 Plugin Contract — Structure d'un module métier

Chaque module = **1 fichier YAML + 1 classe Python**. Rien de plus.

```yaml
# Exemple : modules/sante.yaml
branch: "sante"
label: "Assurance Santé"
schema_version: "1.0"
contamination_rate: 0.08

required_features:
  - montant_facture        # critique, obligatoire
  - code_acte              # critique, obligatoire

optional_features:
  - diagnostic_icd10
    default: "Z00.0"
  - age_assure
    default: "median"

rca_rules:
  - id: "SANTE_001"
    condition: "ratio_prix_mercuriale > 1.5"
    cause: "Surfacturation prestataire"
    category: "Fraude Intentionnelle"
    priority: "HIGH"
  - id: "SANTE_002"
    condition: "flag_post_mortem == True"
    cause: "Fraude post-mortem"
    category: "Fraude Intentionnelle"
    priority: "CRITICAL"

extensions:
  - graph_analysis: true
  - ocr_processing: true
  - weather_correlation: false
```

### 3.6 Gestion des données imparfaites

Le système gère 4 cas réels :
- **Colonnes mal nommées** → couche mapping (fichier `mapping.yaml` par source)
- **Colonnes manquantes** → colonnes critiques = erreur explicite / optionnelles = valeur par défaut ou imputation
- **Dataset partiel** → score de confiance ML pondéré par complétude
- **Types incorrects** → parseur de strings monétaires ("15 000 FCFA" → 15000.0)

### 3.7 Extensions plugins (pattern optionnel par branche)

```
Moteur Générique
    └── Extensions optionnelles
            ├── graph_analysis     (Santé : réseau fraude médecin-praticien-assuré)
            ├── ocr_processing     (Santé, Vie : traitement scans factures)
            ├── weather_correlation (Agricole : corrélation sinistres/météo)
            └── vehicle_registry_check (Auto : vérification plaque/VIN)
```

### 3.8 LLM — Rôle exact de Mistral 7B

**Le LLM ne décide RIEN.** Il ne détecte pas les anomalies.  
Il reçoit en entrée : score SHAP + catégorie RCA déjà identifiée + données du dossier.  
Il produit en sortie : une explication en français naturel, actionnable pour un gestionnaire métier.

**Évaluation rigoureuse obligatoire** avec grille de critères mesurables :
- Précision factuelle (les chiffres cités sont-ils corrects ?)
- Cohérence avec le diagnostic ML (contredit-il Isolation Forest ?)
- Actionabilité (le gestionnaire peut-il agir directement ?)
- Lisibilité (compréhensible par un non-technicien ?)

**Modèle** : Mistral 7B (Ollama, ~4,1 Go en Q4). Supérieur à Gemma 3 4B pour le français.  
**Argument souveraineté** : modèle open-source, données ne quittent jamais le serveur local.

### 3.9 Drift Monitoring

Niveau d'implémentation choisi : **Basique**
- Détection automatique via PSI (Population Stability Index) et KL Divergence
- Alerte visuelle dans le dashboard quand dérive détectée
- Réentraînement **manuel** déclenché par l'administrateur
- Deux types de drift monitorés : data drift + concept drift

### 3.10 Paramètres configurables par l'utilisateur (dashboard)

- Taux de contamination (sensibilité du modèle)
- Seuils de chaque règle RCA (ex : ratio_prix > 1.5, modifiable en 1.3)
- Seuil de score d'anomalie pour déclencher une alerte
- Priorité des catégories d'anomalies

---

## 4. DATASET SANTÉ EXISTANT — CE QU'IL FAUT SAVOIR

### Caractéristiques
- **Volume** : 140 225 lignes (unités de facturation atomiques)
- **Largeur** : 124 colonnes
- **Format** : CSV haute performance
- **Taux de complétude** : 100% sur variables critiques
- **Taux d'anomalies injectées** : ~8% (répartis entre fraudes, erreurs, biais)

### 6 Dimensions du Dataset Universel Santé
1. **Identité & Contrat** : ID_Assuré (hash), Âge, Sexe, Type_Contrat, Région, Score_Risk, Garantie_Niveau, Franchise_Montant…
2. **Médicale & Actes** : Code_Acte_CCAM/ASAC, Diagnostic_ICD10, Spécialité_Praticien, ID_Établissement_FINESS, DMS_Réelle, Score_Gravité…
3. **Financière** : Montant_Facturé, Prix_Référence_Mercuriale, Ratio_Prix, IBAN_Bénéficiaire, Devise (EUR/XAF), Taux_Change, Part_AMO, Part_AMC…
4. **Temporelle** : Date_Soin, Délai_Soin_Dépôt, Heure_Saisie, Timestamp_Validation, Ancienneté_Contrat…
5. **Preuves & OCR** : Source_Flux (API/Scan), Score_Confiance_OCR, Présence_Cachet_Humide, Flag_Document_Altéré, Hash_Image, Résolution_DPI, Métadonnées_EXIF…
6. **Labels & Ground Truth** : Label_Anomalie, Cause_Racine_RCA, Score_Anomalie_ML, Confiance_Prédiction, Features_SHAP_Top3, Règle_Déclenchée, Statut_Investigation…

### Sources utilisées pour constituer ce dataset
- **Synthea** (patients virtuels HL7 FHIR, parcours complets) → ~806 patients générés
- **SNDS/Medicare** (tarifs officiels et actes réels, référentiel prix)
- **ASAC/BEAC** (barèmes tarifaires CIMA et taux de change XAF pour flux physique)
- **Kaggle Datasets** "Healthcare Fraud" (labels de fraude pour entraînement supervisé)
- Transformation géographique Python : 50% résidents français / 50% résidents camerounais

### 23 Scénarios d'anomalies injectés (4 catégories)
**Catégorie I — Fraudes Intentionnelles** : Surfacturation prestataire, Prêt de carte (inversion biologique), Fraude post-mortem, Forçage validation sans justificatif, Fraude réseau (composante connexe), Usurpation d'identité 2 régions simultanées, Doublon facturation  
**Catégorie II — Erreurs Opérationnelles** : Inversion de chiffres (faute de frappe), Oubli conversion devise, Code acte incompatible spécialité, Doublon dossier complet  
**Catégorie III — Biais Système & Modèle** : Dépassement mercuriale systématique, Rejets OCR massifs zone rurale, Pathologie préexistante omise  
**Catégorie IV — Risques Techniques & Données** : Fichier entrant corrompu (hash), Format date invalide (schema drift), Doublon API ingestion massive, Validation sans pièce justificative  

### Principes du moteur d'injection
- **Gestionnaire principal** `manager.py` : distribue lignes selon quotas précis
- **Étanchéité** : un dossier ne subit qu'UN seul type de corruption
- **Jitter ±5%** sur prix de référence pour éviter overfitting sur valeurs fixes

---

## 5. CE QUI EXISTAIT AVANT (ancien code Django — NE PAS RÉUTILISER TEL QUEL)

L'ancien prototype Django contenait les éléments suivants. Ces patterns et logiques sont **réutilisables comme inspiration** pour le nouveau framework FastAPI, mais l'architecture change.

### Apps Django existantes
- `apps.identity` : modèles `Insured`, `Contract`
- `apps.claims` : modèles `Claim`, `ClaimLine`, services `IngestionService`, `LiquidationService`
- `apps.intelligence` : modèle `AIAnalysis`, service `FraudDetectionService`
- `apps.vision` : modèle `OCRMetadata`, service `VisionExtractionService`
- `apps.temporal` : modèle `TemporalMetrics`
- `apps.audit` : décisions auditeur, human-in-the-loop
- `apps.core` : `User`, `AuditorProfile`, `ReferencePrice`, `BusinessRule`

### Logiques métier à conserver (à porter en FastAPI)
- **LiquidationService** : calcul ratio_prix_deviation = prix_facturé / prix_référence_mercuriale. Pré-fetch des mercuriales pour éviter N+1 queries.
- **FraudDetectionService** : extraction features, appel Isolation Forest, calcul SHAP, génération RCA
  - Features extraites : `max_price_deviation`, `total_amount_billed`, `is_image_altered`, `ocr_confidence`, `is_weekend_care`
  - Score normalisé via sigmoid inverse : `1.0 / (1.0 + exp(raw_score))`
  - Mode fallback heuristique si modèle `.joblib` non chargé
- **VisionExtractionService** : pipeline OCR forensic (EXIF → OpenCV → Tesseract → Regex)
  - Détection logiciels suspects : Adobe Photoshop, GIMP, Canva, Pixelmator
  - Scores de confiance par zone (global, montant, date)
  - Bounding boxes JSON pour zones texte extraites
- **IngestionService** : routeur normalisation flux structuré (NOEMIE/API) vs documentaire (OCR/scan)
- **Human-in-the-loop** : validation gestionnaire → "Confirmer anomalie" ou "Rejeter (Faux Positif)" → feedback loop pour futur modèle supervisé

### Modèle AIAnalysis (champs clés à conserver)
```python
anomaly_score           # FloatField 0-1
is_anomaly_detected     # BooleanField
prediction_confidence   # FloatField
rca_main_category       # CharField
rca_sub_category        # CharField
rca_explanation_fr      # TextField
shap_values_json        # JSONField
top_3_contributing_features  # JSONField
```

### Infrastructure existante
- Celery + Redis pour tâches async
- Architecture 3-tiers (Présentation / Traitement / Stockage local)
- Swagger/OpenAPI via `drf-spectacular`
- Filtrage sinistres : `?status=AUDITED&is_anomaly=true`

---

## 6. DUALITÉ FRANCE / CAMEROUN — POINTS CLÉS

### Flux France (numérique)
- Norme **NOEMIE** (Norme Ouverte d'Échange entre la Maladie et les Intervenants Extérieurs)
- Flux API / JSON structurés
- Codes actes : **CCAM** (Classification Commune des Actes Médicaux)
- Référentiel prix : SNDS, tarifs SS
- Devise : **EUR**

### Flux Cameroun (documentaire)
- Scans de factures physiques, ordonnances, **cachets humides obligatoires**
- Pipeline OCR (Tesseract + OpenCV)
- Codes actes : **ASAC** (Association des Sociétés d'Assurance du Cameroun)
- Référentiel prix : **Mercuriale CIMA** (Conférence Interafricaine des Marchés d'Assurance)
- Organisme régulateur : **ASAC/BEAC**
- Devise : **XAF** (Franc CFA)
- Spécificité : taux de change EUR/XAF flottant à intégrer dans calculs

### Argument académique originalité
Il n'existe pratiquement **aucun travail académique** sur la détection de fraude en assurance traitant sérieusement le contexte africain (flux documentaires physiques, infrastructures limitées, micro-assurance). C'est un espace vide que ce projet occupe.

---

## 7. LIMITES CONNUES DU FRAMEWORK (à documenter dans le mémoire)

1. **Trade-off généricité/précision** : un modèle générique est légèrement moins précis qu'un modèle hyper-spécialisé. À mesurer et documenter.
2. **Règles RCA manuelles** : les fichiers YAML doivent être écrits par un expert métier. Pas d'auto-génération.
3. **Isolation Forest et dimensionnalité** : perd en pertinence au-delà de ~20 features hétérogènes. Limite documentée.
4. **Hallucinations LLM** : Mistral 7B peut produire des explications plausibles mais incorrectes. Nécessite la grille d'évaluation rigoureuse.
5. **Données camerounaises synthétiques** : modèle entraîné dessus ne se comportera pas nécessairement comme sur vraies données ASAC/Activa.
6. **Pas de drift monitoring avancé** : détection seulement, réentraînement manuel (choix assumé pour le prototype).
7. **Modules Vie et Agricole** : conception seulement, sans validation empirique.

---

## 8. PLANNING (résumé)

**Période** : Avril → Fin juin 2026  
**Facteur ×5** : 1 jour effectif = 1 semaine classique  
**Juillet** : entièrement dédié à la rédaction du mémoire (encadreur académique)

| Phase | Semaines | Contenu principal |
|-------|----------|-------------------|
| **Phase 0 — Fondations** | S1–S2 | CDC non-technique, fichiers contexte IA, architecture Plugin Contract, cahier technique |
| **Phase 1 — Core + Santé** | S2–S4 | Setup stack, couche mapping, pipeline ML, module Santé complet, métriques |
| **Phase 2 — Auto + LLM** | S4–S7 | Dataset Auto, module Auto, Mistral 7B intégration, RCA narratif, grille évaluation |
| **Phase 3 — UI + Drift + Conception** | S7–S9 | Frontend Next.js, drift monitoring, conceptions Vie + Agricole, extensions plugins |
| **Phase 4 — Validation** | S9–S11 | Tests E2E, analyse comparative généricité/précision, fichiers contexte v2, buffer |

---

## 9. FICHIERS CONTEXTE IA — STRUCTURE RECOMMANDÉE

À créer en Phase 0, à maintenir tout au long du projet :

```
/context/
    MASTER_CONTEXT.md          ← ce fichier (à mettre à jour régulièrement)
    ARCHITECTURE.md            ← Plugin Contract, patterns, décisions ADR
    MODULE_SANTE.md            ← Schéma YAML, règles RCA, features, anomalies
    MODULE_AUTO.md             ← Idem pour Auto
    MODULE_VIE.md              ← Conception seulement
    MODULE_AGRICOLE.md         ← Conception seulement + gap données Cameroun
    DATASET_SANTE_GUIDE.md     ← Comment utiliser les 140k lignes existantes
    ML_PIPELINE.md             ← Code référence Isolation Forest + SHAP
    LLM_PROMPTS.md             ← Prompts Mistral 7B pour RCA + grille évaluation
    API_CONTRACTS.md           ← Endpoints FastAPI, formats requête/réponse
    GLOSSAIRE.md               ← Termes métier assurance (CCAM, ASAC, CIMA, NOEMIE…)
```

---

## 10. QUESTIONS POSÉES AU JURY — À PRÉPARER

1. "Montrez-nous concrètement une anomalie détectée avec son score SHAP et sa cause racine."
2. "Quelles sont les performances de votre Isolation Forest ? Taux de faux positifs ?"
3. "Pourquoi Isolation Forest et pas un Autoencoder ou un modèle supervisé (vous avez des labels) ?"
4. "Votre dataset est synthétique. Comment vous assurez-vous de la généralisabilité ?"
5. "Comment prouvez-vous que votre framework est générique et pas juste 'le même code copié-collé' ?"
6. "Votre LLM peut halluciner. Comment vous le détectez et l'atténuez ?"
7. "La généricité a-t-elle un coût en précision ? Chiffrez-le."

---

## 11. RÉFÉRENCES TECHNIQUES CLÉS

- **Isolation Forest** : Liu et al. (2008) — algorithme non-supervisé, isole les anomalies par nombre minimum de "coupes"
- **SHAP** : Lundberg & Lee (2017) — SHapley Additive exPlanations, valeurs de Shapley pour IA explicable
- **PSI** (Population Stability Index) : métrique standard drift monitoring
- **HL7 FHIR R4** : standard international structure ressources santé (inspiration schéma)
- **ICD-10** : codes diagnostics internationaux
- **CTGAN** : mentionné comme outil potentiel pour enrichissement labels dataset
- **Synthea v3.4.0** : générateur patients virtuels HL7, utilisé pour générer 806 patients Massachusetts

---

*Fin du fichier de contexte. Dernière mise à jour : 17 avril 2026.*
*Prochaine mise à jour prévue : fin Phase 0 (après finalisation architecture Plugin Contract)*
