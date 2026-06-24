# ARCHITECTURE & PLUGIN CONTRACT
## MAKORA Framework — Document de référence technique
### Multimodal Anomaly Kernel for Operational Risk Analysis

---

| Champ | Valeur |
|---|---|
| **Auteur** | ATABONG EFON STEPHANE FRITZ |
| **Entreprise d'accueil** | ITNS Nearshore Services |
| **Version** | v1.0 — Phase 0 |
| **Date** | 17 avril 2026 |
| **Statut** | Document de référence — à mettre à jour à chaque ADR |
| **Dépendances** | CDC Non-Technique v1.0, Fichiers Contexte IA Phase 0 |

---

## TABLE DES MATIÈRES

1. [Vue d'ensemble architecturale](#1-vue-densemble-architecturale)
2. [Structure des dossiers du projet](#2-structure-des-dossiers-du-projet)
3. [Le Kernel MAKORA — Architecture détaillée](#3-le-kernel-makora--architecture-détaillée)
4. [Le Plugin Contract — Spécification formelle](#4-le-plugin-contract--spécification-formelle)
5. [Le Pipeline de traitement — Flux complet](#5-le-pipeline-de-traitement--flux-complet)
6. [La Brique d'Analyse de Graphe](#6-la-brique-danalyse-de-graphe)
7. [Le Format de Sortie Standardisé](#7-le-format-de-sortie-standardisé)
8. [Architecture Decision Records (ADR)](#8-architecture-decision-records-adr)
9. [Stratégie d'évolution — Gouvernance des extensions](#9-stratégie-dévolution--gouvernance-des-extensions)
10. [Diagrammes d'architecture](#10-diagrammes-darchitecture)
11. [Contraintes d'architecture non-négociables](#11-contraintes-darchitecture-non-négociables)

---

## 1. VUE D'ENSEMBLE ARCHITECTURALE

### 1.1 Le concept fondateur

MAKORA repose sur une conviction architecturale unique : **la logique de détection d'anomalies est universelle ; seule la connaissance métier varie d'une branche à l'autre**.

Cette conviction se traduit par une séparation stricte en trois niveaux :

```
┌──────────────────────────────────────────────────────────────────────┐
│  NIVEAU 3 — PRÉSENTATION                                             │
│  Dashboard Next.js                                                   │
│  Interface universelle — s'adapte dynamiquement à la branche active  │
│  Visualisation SHAP · Diagnostic RCA · Narration · Validation human  │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ REST API (FastAPI)
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│  NIVEAU 2 — KERNEL GÉNÉRIQUE (immuable)                              │
│                                                                      │
│  ┌───────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │  ETL      │  │Isolation │  │  SHAP    │  │   Moteur RCA       │  │
│  │ Pipeline  │→ │ Forest   │→ │Explainer │→ │  (règles YAML)     │  │
│  │(mapping + │  │(+compare │  │(top 3    │  │  catégorie +       │  │
│  │ normaliz.)│  │ algo)    │  │ features)│  │  sous-catégorie    │  │
│  └───────────┘  └──────────┘  └──────────┘  └────────────────────┘  │
│                                                        │             │
│  ┌──────────────────────────┐  ┌────────────────────────────────┐   │
│  │  Analyse de Graphe       │  │   Mistral 7B (Ollama local)    │   │
│  │  NetworkX + Louvain      │  │   Narration française RCA      │   │
│  │  (brique optionnelle)    │  │   + fallback template          │   │
│  └──────────────────────────┘  └────────────────────────────────┘   │
│                                                                      │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │  Drift Monitor  │  │  Audit Logger  │  │  Schema Validator    │  │
│  │  PSI par feature│  │  (immuable)    │  │  Pydantic v2         │  │
│  └─────────────────┘  └────────────────┘  └──────────────────────┘  │
│                                                                      │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │ Plugin Contract
                                 │ (1 YAML + 1 classe Python)
┌────────────────────────────────▼─────────────────────────────────────┐
│  NIVEAU 1 — MODULES MÉTIERS (Plugins)                                │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │    SANTÉ     │  │     AUTO     │  │     VIE      │               │
│  │  Complet V1  │  │  Complet V1  │  │  Conception  │               │
│  │ FR + CM      │  │ FR + CM      │  │  seulement   │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│                             ┌──────────────┐                         │
│                             │   AGRICOLE   │                         │
│                             │  Conception  │                         │
│                             │  seulement   │                         │
│                             └──────────────┘                         │
└──────────────────────────────────────────────────────────────────────┘
```

### 1.2 Le Cycle d'Adaptation MAKORA

Chaque dossier traité traverse trois phases du cycle MAKORA :

**Phase 1 — Exposition**
Le Kernel reçoit un flux de données inconnu. Il ne sait pas encore si c'est un dossier Santé ou Auto, numérique ou documentaire. Il détecte le type de flux et charge le module approprié via le Plugin Contract.

**Phase 2 — Rotation (Analyse Multimodale)**
Le Kernel active toutes ses briques simultanément : normalisation, feature engineering via le module, détection ML, explicabilité SHAP, analyse de graphe si activée, diagnostic RCA via les règles YAML du module, narration LLM.

**Phase 3 — Adaptation (RCA)**
Le Kernel produit un diagnostic complet. Il ne se contente pas de lever une alerte — il identifie la logique de l'anomalie, la classe dans la taxonomie des 4 catégories et produit une explication actionnnable en français. Chaque décision humaine (validation/rejet) renforce la boucle de rétroaction.

### 1.3 Propriétés architecturales garanties

| Propriété | Définition | Comment elle est garantie |
|---|---|---|
| **Généricité** | Un seul moteur pour toutes les branches | Interface `BaseModule` — le Kernel ne connaît pas les modules concrets |
| **Extensibilité** | Ajouter une branche sans modifier le Kernel | Plugin Contract strictement validé au chargement |
| **Explicabilité** | Toute décision IA est justifiée | SHAP obligatoire + moteur RCA + narration LLM |
| **Traçabilité** | Journal de décisions immuable | `audit_logger.py` — chaque sortie JSON est persistée |
| **Robustesse** | Pas de crash sur données imparfaites | Mode dégradé heuristique + fallback narration |
| **Reproductibilité** | Résultats identiques à chaque exécution | `random_state=42` universel + modèles `.joblib` versionnés |

---

## 2. STRUCTURE DES DOSSIERS DU PROJET

```
makora/
│
├── context/                          ← Fichiers contexte IA (13 fichiers)
│   ├── MASTER_CONTEXT.md
│   ├── ARCHITECTURE.md
│   ├── PLUGIN_CONTRACT.md
│   ├── MODULE_SANTE.md
│   ├── MODULE_AUTO.md
│   ├── MODULE_VIE.md
│   ├── MODULE_AGRICOLE.md
│   ├── DATASET_SANTE_GUIDE.md
│   ├── ML_PIPELINE.md
│   ├── GRAPH_ANALYSIS.md
│   ├── LLM_PROMPTS.md
│   ├── API_CONTRACTS.md
│   └── GLOSSAIRE.md
│
├── core/                             ← Kernel MAKORA (NE JAMAIS MODIFIER pour un module)
│   ├── __init__.py
│   ├── base_module.py                ← Interface Plugin Contract Python
│   ├── pipeline.py                   ← Orchestrateur principal
│   ├── ingestion/
│   │   ├── router.py                 ← Détection type flux + routing
│   │   ├── structured_reader.py      ← Lecture CSV/JSON
│   │   └── documentary_reader.py     ← Pipeline OCR (Tesseract + OpenCV)
│   ├── mapping_engine.py             ← Harmonisation colonnes (lit YAML source_mappings)
│   ├── schema_validator.py           ← Validation Pydantic v2
│   ├── normalizer.py                 ← Devises, encodage catégorielles
│   ├── detector.py                   ← Isolation Forest + comparaison algorithmes
│   ├── explainer.py                  ← SHAP TreeExplainer
│   ├── rca_engine.py                 ← Moteur règles YAML → diagnostic
│   ├── graph_engine.py               ← NetworkX + Louvain (brique optionnelle)
│   ├── llm_narrator.py               ← Mistral 7B via Ollama + fallback
│   ├── drift_monitor.py              ← PSI par feature
│   └── audit_logger.py              ← Journal de décisions immuable
│
├── modules/                          ← Plugins métiers (1 dossier par branche)
│   ├── sante/
│   │   ├── sante.yaml               ← Plugin Contract déclaratif
│   │   ├── sante_module.py          ← class SanteModule(BaseModule)
│   │   └── README.md
│   ├── auto/
│   │   ├── auto.yaml
│   │   ├── auto_module.py
│   │   └── README.md
│   ├── vie/
│   │   ├── vie.yaml                 ← Conception seulement
│   │   └── README.md
│   └── agricole/
│       ├── agricole.yaml            ← Conception seulement
│       └── README.md
│
├── api/                              ← FastAPI endpoints
│   ├── main.py                      ← Entry point + lifespan
│   ├── routers/
│   │   ├── analyze.py               ← POST /api/v1/analyze
│   │   ├── audit.py                 ← GET/POST /api/v1/audit
│   │   ├── drift.py                 ← GET /api/v1/drift/status
│   │   └── modules.py               ← GET /api/v1/modules
│   └── schemas/                     ← Pydantic models API (requêtes + réponses)
│       ├── analyze_schema.py
│       ├── audit_schema.py
│       └── drift_schema.py
│
├── data/
│   ├── raw/                         ← Données brutes sources (.gitignored)
│   ├── processed/                   ← Datasets Parquet finalisés
│   │   ├── dataset_sante_v1.parquet
│   │   └── dataset_sante_test_fixe.parquet
│   ├── models/                      ← Fichiers .joblib versionnés + checksums SHA-256
│   │   └── makora_sante_v1.0.joblib
│   └── referentials/                ← Mercuriale CIMA, CCAM, ASAC (YAML/JSON)
│       ├── mercuriale_cima.yaml
│       ├── ccam_codes.json
│       └── taux_change_eur_xaf.json
│
├── frontend/                        ← Next.js dashboard (Phase 3)
│   ├── pages/
│   ├── components/
│   └── package.json
│
├── tests/
│   ├── unit/
│   │   ├── test_base_module.py
│   │   ├── test_rca_engine.py
│   │   ├── test_normalizer.py
│   │   └── test_plugin_contract.py
│   ├── integration/
│   │   ├── test_pipeline_sante.py
│   │   └── test_pipeline_auto.py
│   └── fixtures/
│       └── dataset_test_1000.parquet  ← FIXE — ne jamais modifier
│
├── scripts/
│   ├── inject_anomalies.py          ← Moteur d'injection des 23 scénarios
│   └── benchmark_algorithms.py      ← Comparaison IF vs LOF vs SVM vs Autoencoder
│
├── docker-compose.yml
├── requirements.txt
├── pyproject.toml
└── README.md
```

---

## 3. LE KERNEL MAKORA — ARCHITECTURE DÉTAILLÉE

### 3.1 Principe d'isolation du Kernel

Le Kernel est le cœur immuable de MAKORA. Il obéit à une règle absolue :

> **Le Kernel ne connaît jamais un module concret. Il ne reçoit que des instances de `BaseModule`.**

Concrètement, `pipeline.py` ne contient jamais `from modules.sante import SanteModule`. Il reçoit une instance de `BaseModule` en paramètre, et appelle uniquement les méthodes définies dans l'interface. C'est ce qui garantit la généricité.

```python
# core/pipeline.py — CORRECT
def run(module: BaseModule, data_path: Path) -> dict:
    features = module.get_feature_names()        # ✅ Appel interface
    df = module.engineer_features(df_normalized) # ✅ Appel interface
    rules = module.get_rca_rules()               # ✅ Appel interface

# core/pipeline.py — INTERDIT
from modules.sante.sante_module import SanteModule  # ❌ Import direct
if module.branch == "sante":                         # ❌ Logique conditionnelle sur la branche
    do_sante_specific_thing()
```

### 3.2 Description de chaque brique du Kernel

#### `router.py` — Routeur d'ingestion
Détecte le type de flux entrant (structuré vs documentaire) en fonction de l'extension du fichier. Route vers `structured_reader.py` (CSV/JSON) ou `documentary_reader.py` (PDF/image).

```
Entrée  : chemin fichier
Sortie  : DataFrame brut + métadonnées source (type, nom_source)
```

#### `documentary_reader.py` — Pipeline OCR
Traite les documents physiques scannés. Étapes : prétraitement image (OpenCV : débruitage, binarisation, correction perspective) → OCR (Tesseract) → extraction structurée (montants, dates, codes via regex + zones de confiance) → détection cachet humide → analyse EXIF (logiciels de retouche).

```
Entrée  : fichier PDF/image
Sortie  : DataFrame structuré + métadonnées OCR (scores de confiance, flags)
```

#### `mapping_engine.py` — Harmonisation des colonnes
Renomme les colonnes selon le mapping déclaré dans le YAML du module (`source_mappings`). Gère les colonnes manquantes non-obligatoires (remplissage par NaN).

```
Entrée  : DataFrame brut + mapping dict (depuis YAML)
Sortie  : DataFrame avec colonnes au format schéma universel
```

#### `schema_validator.py` — Validation Pydantic
Vérifie que le DataFrame contient toutes les colonnes obligatoires (`input_schema.required`) avec les bons types. Produit une liste d'erreurs structurées en cas d'échec.

```
Entrée  : DataFrame + module (pour extraire le schéma)
Sortie  : (is_valid: bool, errors: list[str])
```

#### `normalizer.py` — Normalisation universelle
Applique les transformations universelles indépendantes du module : conversion de devises XAF → EUR, encodage des variables catégorielles binaires (Sexe M/F → 0/1, Source API/Scan → 0/1), log-transform sur les montants.

```
Entrée  : DataFrame après validation
Sortie  : DataFrame normalisé
```

#### `detector.py` — Détection ML
Entraîne ou charge l'Isolation Forest du module. Calcule le score d'anomalie normalisé [0, 1] pour chaque dossier. Contient également le protocole de comparaison des algorithmes (IF, LOF, One-Class SVM).

```
Entrée  : DataFrame features + module (pour contamination)
Sortie  : anomaly_score (float), is_anomaly (bool) par dossier
```

**Normalisation du score Isolation Forest :**
```
score_if ∈ [-0.5, 0.5]  →  score_makora ∈ [0, 1]
score_makora = 1 / (1 + exp(score_if × 10))
Plus score_makora est élevé → plus le dossier est anormal
```

#### `explainer.py` — SHAP TreeExplainer
Calcule les valeurs SHAP pour chaque dossier marqué anomalie. Retourne les top 3 features contributrices avec leur valeur SHAP et leur direction (positive = contribue à l'anomalie, négative = contribue à la normalité).

```
Entrée  : modèle IF + DataFrame features
Sortie  : top_3_features par dossier (nom, shap_value, direction)
```

#### `rca_engine.py` — Moteur de règles RCA
Croise les valeurs SHAP (quelles features sont anormales ?) avec les règles YAML du module (ces features anormales correspondent à quel type d'anomalie ?). Retourne le premier diagnostic RCA dont toutes les conditions sont satisfaites.

```
Entrée  : valeurs features + règles YAML (depuis module.get_rca_rules())
Sortie  : category, subcategory, rule_id, confidence
```

#### `graph_engine.py` — Analyse de graphe (optionnelle)
Activée si `module.is_graph_enabled() == True`. Construit un graphe bipartite entre entités (assurés, praticiens, employeurs), applique l'algorithme de détection de communautés Louvain, retourne les communautés suspectes et les flags par nœud.

```
Entrée  : DataFrame + config graphe (depuis module.get_graph_config())
Sortie  : graph_anomaly_flag par dossier + community_id + métriques
```

#### `llm_narrator.py` — Narration Mistral 7B
Reçoit le contexte structuré du diagnostic (score, top 3 SHAP, RCA) et produit une explication en français naturel via Mistral 7B (Ollama local). Si Ollama est indisponible, bascule sur une narration template-based construite à partir du diagnostic RCA structuré.

```
Entrée  : contexte dict (claim_id, branch, score, top_features, rca)
Sortie  : explanation_fr (string, 3-5 phrases)
```

#### `drift_monitor.py` — Monitoring de la dérive
Calcule le PSI (Population Stability Index) pour chaque feature surveillée, en comparant la distribution courante (fenêtre de 30 jours) avec la distribution de référence (fenêtre d'entraînement de 90 jours). Déclenche des alertes selon les seuils configurés dans le YAML.

```
PSI < 0.10  → STABLE
0.10 ≤ PSI < 0.20  → WARNING
PSI ≥ 0.20  → CRITICAL (réentraînement recommandé)
```

#### `audit_logger.py` — Journal de décisions
Persiste chaque sortie JSON complète de MAKORA dans un journal immuable (append-only). Associe les décisions humaines (validation/rejet) à chaque dossier. Permet de reconstituer intégralement la chaîne de décision IA pour n'importe quel dossier.

---

## 4. LE PLUGIN CONTRACT — SPÉCIFICATION FORMELLE

### 4.1 Définition

Le Plugin Contract est le **contrat formel** qui lie un module métier au Kernel MAKORA. Il se compose de deux parties indissociables :

1. **Un fichier YAML déclaratif** — lisible par un expert métier non-développeur
2. **Une classe Python** héritant de `BaseModule` — le point d'extension contrôlé

La validation du contrat est effectuée **au chargement du module** (fail fast). Si le YAML est invalide ou si la classe ne respecte pas l'interface, le système refuse de démarrer.

### 4.2 Interface `BaseModule` — Spécification complète

```python
# core/base_module.py

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional
import pandas as pd
import yaml


class BaseModule(ABC):
    """
    Interface Plugin Contract de MAKORA.
    Toute classe héritant de BaseModule est un module valide.

    Règle d'or :
    - Le Kernel appelle UNIQUEMENT les méthodes définies ici.
    - Un module ne modifie JAMAIS les fichiers du core/.
    """

    def __init__(self, config_path: Path):
        with open(config_path, encoding="utf-8") as f:
            self.config = yaml.safe_load(f)
        self.branch: str = self.config["branch"]
        self.version: str = self.config["version"]
        self.thresholds: dict = self.config["thresholds"]
        self._validate_contract()

    # ----------------------------------------------------------------
    # MÉTHODES ABSTRAITES — TOUTES OBLIGATOIRES
    # ----------------------------------------------------------------

    @abstractmethod
    def get_feature_names(self) -> list[str]:
        """
        Retourne la liste ordonnée des noms de features que ce module
        calcule et que l'Isolation Forest doit recevoir.

        Contrat :
        - Toutes les features retournées ici doivent être calculées
          par engineer_features().
        - L'ordre doit être stable entre les appels.
        """
        pass

    @abstractmethod
    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule toutes les features dérivées spécifiques à ce module.

        Contrat :
        - Reçoit le DataFrame normalisé (schéma universel).
        - Retourne le DataFrame ENRICHI avec les features calculées.
        - NE MODIFIE PAS les colonnes existantes (uniquement ajout).
        - Gère les valeurs manquantes (pas de NaN dans les features ML).
        """
        pass

    @abstractmethod
    def get_rca_rules(self) -> list[dict]:
        """
        Retourne les règles RCA du fichier YAML.

        Contrat :
        - Retourne self.config["rca_rules"]
        - L'ordre des règles = ordre de priorité (première règle matchée = diagnostic retenu)
        """
        pass

    @abstractmethod
    def validate_input(self, df: pd.DataFrame) -> tuple[bool, list[str]]:
        """
        Valide que le DataFrame entrant contient les colonnes requises.

        Retourne :
        - (True, []) si le DataFrame est valide
        - (False, ["col_manquante_1", "col_manquante_2"]) si invalide
        """
        pass

    # ----------------------------------------------------------------
    # MÉTHODES CONCRÈTES — NE PAS SURCHARGER SAUF RAISON DOCUMENTÉE
    # ----------------------------------------------------------------

    def get_contamination(self) -> float:
        """Proportion estimée d'anomalies dans ce module."""
        return float(self.thresholds["contamination"])

    def get_anomaly_threshold(self) -> float:
        """Seuil de score au-delà duquel un dossier est marqué anomalie."""
        return float(self.thresholds["anomaly_score_alert"])

    def is_graph_enabled(self) -> bool:
        """True si la brique d'analyse de graphe est activée pour ce module."""
        return self.config.get("graph_analysis", {}).get("enabled", False)

    def get_graph_config(self) -> Optional[dict]:
        """Retourne la configuration de la brique graphe, ou None."""
        return self.config.get("graph_analysis")

    def get_drift_config(self) -> dict:
        """Retourne la configuration du drift monitoring."""
        return self.config.get("drift_monitoring", {})

    def get_source_mapping(self, source_name: str) -> dict:
        """Retourne le mapping de colonnes pour une source donnée."""
        return self.config.get("source_mappings", {}).get(source_name, {})

    def get_drift_features(self) -> list[str]:
        """Retourne la liste des features à surveiller pour le drift."""
        return self.config.get("drift_monitoring", {}).get("features_to_monitor", [])

    # ----------------------------------------------------------------
    # VALIDATION INTERNE — NE PAS SURCHARGER
    # ----------------------------------------------------------------

    def _validate_contract(self) -> None:
        """
        Vérifie que le YAML respecte le Plugin Contract minimal.
        Appelé automatiquement dans __init__. Fail fast.
        """
        required_keys = [
            "branch", "version", "features",
            "rca_rules", "thresholds", "input_schema"
        ]
        missing = [k for k in required_keys if k not in self.config]
        if missing:
            raise ValueError(
                f"Plugin Contract violation — module '{self.config.get('branch', 'INCONNU')}' : "
                f"clés YAML manquantes : {missing}"
            )

        required_thresholds = ["contamination", "anomaly_score_alert"]
        missing_t = [t for t in required_thresholds if t not in self.thresholds]
        if missing_t:
            raise ValueError(
                f"Plugin Contract violation — thresholds manquants : {missing_t}"
            )

    def __repr__(self) -> str:
        return f"<MAKORAModule branch='{self.branch}' version='{self.version}'>"
```

### 4.3 Structure du fichier YAML — Spécification exhaustive

```yaml
# ====================================================================
# PLUGIN CONTRACT — Fichier YAML d'un module MAKORA
# Tous les champs marqués REQUIS sont validés au chargement.
# Les champs OPTIONNEL peuvent être omis.
# ====================================================================

# --- SECTION 1 : MÉTADONNÉES ---
branch: "sante"                          # REQUIS — identifiant unique, snake_case
version: "1.0.0"                         # REQUIS — semver
description: "Module Santé MAKORA"      # REQUIS
author: "ATABONG EFON STEPHANE FRITZ"   # REQUIS
market: ["FR", "CM"]                    # REQUIS — codes ISO 3166-1 alpha-2

# --- SECTION 2 : SEUILS DE DÉTECTION ---
thresholds:
  contamination: 0.08           # REQUIS — float (0.0, 0.5) — proportion estimée anomalies
  anomaly_score_alert: 0.70     # REQUIS — float [0.0, 1.0] — seuil de déclenchement alerte
  min_features_required: 5      # OPTIONNEL — nb min features non-nulles (défaut: 3)

# --- SECTION 3 : SCHÉMA DES DONNÉES ENTRANTES ---
input_schema:
  required:                     # REQUIS — liste des colonnes obligatoires
    - name: "ID_Sinistre"
      type: "string"            # string | float | integer | date | boolean
      description: "Identifiant unique du dossier"
    - name: "Montant_Facture"
      type: "float"
      description: "Montant total facturé en devise locale"
    - name: "Code_Acte"
      type: "string"
      description: "Code acte CCAM (FR) ou ASAC (CM)"
    - name: "Devise"
      type: "string"
      description: "EUR ou XAF"
    # ... colonnes spécifiques au module

  optional:                     # OPTIONNEL — colonnes non-obligatoires
    - name: "Score_Confiance_OCR_Glob"
      type: "float"
      description: "Score de confiance OCR global [0.0, 1.0]"
    # ...

# --- SECTION 4 : MAPPING DES SOURCES ---
# Permet de renommer les colonnes mal nommées selon la source.
source_mappings:
  noemie_api:                   # OPTIONNEL — une entrée par source connue
    "montant": "Montant_Facture"
    "code_acte": "Code_Acte"
  kaggle_healthcare:
    "ClaimAmount": "Montant_Facture"
    "ProcedureCode": "Code_Acte"

# --- SECTION 5 : FEATURES À CALCULER ---
# Chaque feature ici DOIT être produite par engineer_features().
features:                       # REQUIS — liste non-vide
  - name: "ratio_prix_mercuriale"
    type: "float"
    description: "Montant_Facture_EUR / Prix_Reference_Mercuriale"
    required_columns: ["Montant_EUR_Normalise", "Prix_Reference_Mercuriale"]
    importance: "critique"      # critique | haute | moyenne | faible
    null_strategy: "fill_one"   # fill_zero | fill_one | fill_median | drop

  - name: "is_weekend_care"
    type: "boolean"
    description: "True si Date_Soin est samedi ou dimanche"
    required_columns: ["Date_Soin"]
    importance: "haute"
    null_strategy: "fill_zero"

  - name: "incoherence_sexe_acte"
    type: "integer"
    description: "1 si incohérence biologique sexe/acte détectée"
    required_columns: ["Sexe_Assure", "Code_Acte"]
    importance: "critique"
    null_strategy: "fill_zero"

  # ... toutes les features du module

# --- SECTION 6 : RÈGLES RCA ---
# Ordre = priorité. Première règle matchée = diagnostic retenu.
rca_rules:                      # REQUIS — liste non-vide
  - id: "RCA_SURF_001"          # REQUIS — identifiant unique dans ce module
    name: "Surfacturation Prestataire"
    category: "Fraude Intentionnelle"
    subcategory: "Surfacturation Prestataire"
    conditions:                 # REQUIS — liste de conditions
      - feature: "ratio_prix_mercuriale"
        operator: "gt"          # gt | lt | gte | lte | eq | ne
        threshold: 1.5
      - feature: "historique_ratio_praticien"
        operator: "gt"
        threshold: 1.3
    logic: "AND"                # AND | OR
    confidence_base: 0.85       # float [0.0, 1.0]
    message_template: >         # OPTIONNEL — template pour narration fallback
      Le montant facturé dépasse le tarif de référence de {deviation}%.
      Comportement systématique observé sur {nb_dossiers} dossiers récents.

  - id: "RCA_PRET_CARTE_001"
    name: "Prêt de Carte / Usurpation d'Identité"
    category: "Fraude Intentionnelle"
    subcategory: "Usurpation Identité"
    conditions:
      - feature: "incoherence_sexe_acte"
        operator: "eq"
        threshold: 1
    logic: "AND"
    confidence_base: 0.90
    message_template: >
      Incohérence biologique détectée entre le sexe de l'assuré
      et l'acte médical facturé.

  # Règle par défaut — TOUJOURS en dernière position
  - id: "RCA_DEFAULT"
    name: "Anomalie Non Classifiée"
    category: "Indéterminé"
    subcategory: "Aucune règle déclenchée"
    conditions:
      - feature: "anomaly_score_raw"
        operator: "gt"
        threshold: 0.0          # Toujours vrai — catch-all
    logic: "AND"
    confidence_base: 0.50

# --- SECTION 7 : ANALYSE DE GRAPHE (OPTIONNEL) ---
graph_analysis:
  enabled: true                 # OPTIONNEL — défaut false
  node_entities:                # Colonnes qui deviennent des nœuds
    - "ID_Praticien"
    - "ID_Assure"
    - "ID_Employeur"
  edge_weight: "Montant_EUR_Normalise"
  community_algorithm: "louvain"   # louvain | girvan_newman
  min_community_size: 3            # Taille minimum pour analyser une communauté
  suspicious_density_threshold: 0.5
  anomaly_threshold_degree: 10     # Degré minimum pour alerte réseau

# --- SECTION 8 : DRIFT MONITORING ---
drift_monitoring:
  reference_window_days: 90     # REQUIS si section présente
  alert_window_days: 30
  features_to_monitor:          # REQUIS si section présente
    - "ratio_prix_mercuriale"
    - "Montant_EUR_Normalise"
    - "Score_Confiance_OCR_Glob"
  psi_thresholds:
    warning: 0.10
    critical: 0.20
```

### 4.4 Checklist de validation d'un nouveau module

Avant de déclarer un module prêt pour intégration :

```
□ Le fichier YAML contient toutes les clés REQUIS
□ La classe Python hérite de BaseModule
□ Les 4 méthodes abstraites sont toutes implémentées
□ validate_input() vérifie toutes les colonnes REQUIS du YAML
□ engineer_features() ne modifie aucune colonne existante
□ Toutes les features listées dans features[] sont calculées par engineer_features()
□ Toutes les conditions des règles RCA font référence à des features existantes
□ Une règle RCA par défaut (catch-all) est en dernière position
□ _validate_contract() passe sans exception au chargement
□ Un test unitaire valide le chargement du module (import + instanciation + validate_contract)
□ Un test d'intégration valide le pipeline complet sur 10 dossiers de test
□ Le README.md du module est rempli (schéma, anomalies couvertes, métriques obtenues)
□ Zéro import du module dans les fichiers core/
```

---

## 5. LE PIPELINE DE TRAITEMENT — FLUX COMPLET

### 5.1 Vue séquentielle

```
┌─────────────────────────────────────────────────────────────┐
│  ENTRÉE : fichier CSV/JSON ou PDF/image + branche           │
└──────────────────────────────┬──────────────────────────────┘
                               │
              ┌────────────────▼────────────────┐
              │  [1] ROUTER                     │
              │  Détection type flux            │
              │  structured → structured_reader │
              │  documentary → ocr_pipeline     │
              └────────────────┬────────────────┘
                               │ DataFrame brut
              ┌────────────────▼────────────────┐
              │  [2] MAPPING ENGINE             │
              │  Harmonisation noms colonnes    │
              │  (YAML source_mappings)         │
              └────────────────┬────────────────┘
                               │ DataFrame mappé
              ┌────────────────▼────────────────┐
              │  [3] SCHEMA VALIDATOR           │
              │  Pydantic v2                    │
              │  Colonnes requises + types      │
              │  ✗ → Rejet avec erreurs JSON    │
              └────────────────┬────────────────┘
                               │ DataFrame validé
              ┌────────────────▼────────────────┐
              │  [4] NORMALIZER                 │
              │  Conversion devises XAF→EUR     │
              │  Encodage catégorielles         │
              │  Log-transform montants         │
              └────────────────┬────────────────┘
                               │ DataFrame normalisé
              ┌────────────────▼────────────────┐
              │  [5] FEATURE ENGINEERING        │
              │  module.engineer_features(df)   │
              │  Features spécifiques au module │
              └────────────────┬────────────────┘
                               │ DataFrame enrichi
         ┌─────────────────────┼──────────────────────┐
         │                     │                      │
┌────────▼───────┐  ┌──────────▼──────────┐  ┌───────▼────────┐
│  [6] DÉTECTION │  │ [6b] GRAPHE         │  │  Autres        │
│  Isolation     │  │ NetworkX + Louvain  │  │  algorithmes   │
│  Forest        │  │ (si graph_enabled)  │  │  (comparaison) │
└────────┬───────┘  └──────────┬──────────┘  └───────┬────────┘
         │                     │                      │
         └─────────────────────┼──────────────────────┘
                               │ scores + flags
              ┌────────────────▼────────────────┐
              │  [7] SHAP EXPLAINER             │
              │  Top 3 features contributrices  │
              │  (uniquement si is_anomaly)     │
              └────────────────┬────────────────┘
                               │ shap_top_3
              ┌────────────────▼────────────────┐
              │  [8] MOTEUR RCA                 │
              │  SHAP + règles YAML             │
              │  → catégorie + sous-catégorie   │
              │  → confidence + rule_id         │
              └────────────────┬────────────────┘
                               │ diagnostic RCA structuré
              ┌────────────────▼────────────────┐
              │  [9] LLM NARRATOR               │
              │  Mistral 7B (Ollama)            │
              │  → explication française 3-5 ph │
              │  Fallback template si KO        │
              └────────────────┬────────────────┘
                               │ explanation_fr
              ┌────────────────▼────────────────┐
              │  [10] ASSEMBLAGE SORTIE JSON    │
              │  Format standardisé MAKORA      │
              │  (identique tous modules)       │
              └────────────────┬────────────────┘
                               │ JSON complet
              ┌────────────────▼────────────────┐
              │  [11] AUDIT LOGGER              │
              │  Persistance immuable           │
              │  Horodatage + version modèle    │
              └────────────────┬────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────┐
│  SORTIE : JSON standardisé MAKORA + log audit               │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Gestion des erreurs et modes dégradés

| Situation | Comportement | Code |
|---|---|---|
| Fichier format invalide | Rejet propre → JSON erreur `FILE_FORMAT_INVALID` | 400 |
| Colonnes requises manquantes | Rejet → JSON erreur avec liste colonnes manquantes | 422 |
| Score OCR < 0.30 | Document retourné → RCA `QUALITE_DOCUMENT_INSUFFISANTE` | 200 |
| Modèle ML non chargé | Mode heuristique (seuils fixes sur features critiques) | 200 |
| Ollama non disponible | Narration fallback template-based | 200 |
| Taux change EUR/XAF indisponible | Taux fallback 655.957 + flag `taux_fallback: true` | 200 |
| Valeurs manquantes features | Imputation selon `null_strategy` du YAML | 200 |

---

## 6. LA BRIQUE D'ANALYSE DE GRAPHE

### 6.1 Justification de son intégration en V1

La fraude en réseau (collusion prestataire-assuré, réseaux de soins fantômes) est **structurellement invisible** à l'analyse individuelle des dossiers par l'Isolation Forest. Un praticien qui facture exactement 1.49× la mercuriale sur chaque dossier ne déclenchera aucune alerte IF — mais une analyse de ses relations avec un groupe d'assurés concentrés révèle immédiatement le schéma de collusion.

L'analyse de graphe est donc une brique complémentaire et non concurrente de l'IF.

### 6.2 Architecture du graphe

**Nœuds**

| Type | Identifiant | Attributs portés |
|---|---|---|
| Assuré | `ID_Assure` | Âge, sexe, région, nombre de sinistres |
| Praticien | `ID_Praticien` | Spécialité, région, ratio prix moyen |
| Établissement | `ID_Etablissement` | Type, région |
| Employeur | `ID_Employeur` | Secteur (si disponible) |

**Arêtes**

| Type | Entre | Poids |
|---|---|---|
| `A_CONSULTE` | Assuré → Praticien | Nombre de consultations |
| `FACTURE_PAR` | Dossier → Praticien | Montant facturé EUR |
| `EMPLOYE_PAR` | Assuré → Employeur | — |

**Détection de communautés suspectes**

Une communauté est marquée suspecte si :
- Taille ≥ `min_community_size` (config YAML)
- Densité ≥ `suspicious_density_threshold` (config YAML, défaut 0.5)
- Poids moyen des arêtes statistiquement anormal (> 2σ de la distribution globale)

### 6.3 Intégration dans le pipeline

La brique graphe est **optionnelle et non-bloquante**. Si elle est désactivée ou en erreur, le pipeline continue sans elle. Son résultat enrichit le champ `graph_analysis` de la sortie JSON (nullable).

```python
# core/pipeline.py — intégration graphe

graph_result = None
if module.is_graph_enabled():
    try:
        graph_config = module.get_graph_config()
        G = graph_engine.build_bipartite_graph(df, graph_config)
        communities = graph_engine.detect_suspicious_communities(G)
        df = graph_engine.compute_node_anomaly_flags(df, communities)
        graph_result = graph_engine.format_graph_output(communities, df)
    except Exception as e:
        logger.warning(f"Brique graphe KO : {e}. Pipeline continue sans graphe.")
        graph_result = {"error": str(e), "enabled": True, "executed": False}
```

---

## 7. LE FORMAT DE SORTIE STANDARDISÉ

Ce format est **immuable**. Tout ajout de champ doit être **optionnel (nullable)** pour ne pas casser les modules existants. Cette règle est non-négociable (cf. ADR-005).

```json
{
  "claim_id": "SIN_2025_CM_00842",
  "branch": "sante",
  "anomaly_score": 0.87,
  "is_anomaly": true,
  "processing_time_ms": 1243,

  "rca": {
    "category": "Fraude Intentionnelle",
    "subcategory": "Surfacturation Prestataire",
    "confidence": 0.91,
    "rule_triggered": "RCA_SURF_001",
    "top_features": [
      {
        "name": "ratio_prix_mercuriale",
        "shap_value": 0.312,
        "direction": "positive",
        "value": 1.81
      },
      {
        "name": "historique_ratio_praticien",
        "shap_value": 0.187,
        "direction": "positive",
        "value": 1.64
      },
      {
        "name": "montant_facture",
        "shap_value": 0.094,
        "direction": "positive",
        "value": 18500.0
      }
    ],
    "explanation_fr": "Le montant facturé pour cette consultation cardiologique (18 500 XAF) dépasse de 81% le tarif de référence de la Mercuriale CIMA. Ce dépassement est observé sur 8 des 10 derniers dossiers de ce praticien, ce qui pourrait indiquer une surfacturation systématique. Un contrôle approfondi de l'activité de ce prestataire est recommandé avant tout nouveau remboursement."
  },

  "graph_analysis": {
    "enabled": true,
    "executed": true,
    "community_id": 7,
    "community_size": 12,
    "community_density": 0.73,
    "is_suspicious_community": true,
    "rca_graph": {
      "category": "Fraude Intentionnelle",
      "subcategory": "Fraude en Réseau / Collusion",
      "explanation_fr": "Ce praticien appartient à une communauté de 12 entités avec une densité de transactions anormalement élevée."
    }
  },

  "audit": {
    "timestamp": "2025-11-14T09:23:41Z",
    "model_version": "makora-sante-v1.0",
    "model_checksum": "sha256:a3f2...",
    "decision": "PENDING",
    "validated_by": null,
    "validated_at": null,
    "motif": null
  }
}
```

---

## 8. ARCHITECTURE DECISION RECORDS (ADR)

### ADR-001 — Isolation Forest comme algorithme de base
**Statut :** ✅ ACCEPTÉE | **Date :** 17 avril 2026

**Contexte :** Choix de l'algorithme principal de détection.

**Décision :** Isolation Forest (Liu et al., 2008) comme algorithme de référence.

**Justification :**
- Non-supervisé : pas besoin de labels fiables en production réelle
- Compatible SHAP TreeExplainer nativement (critère éliminatoire)
- Robuste sur données hétérogènes et de taille moyenne
- Standard académique reconnu et citable

**Conséquences :** Une comparaison formelle sera conduite (IF vs LOF vs One-Class SVM vs Autoencoder si temps disponible) sur le dataset Santé. L'IF reste l'algorithme de référence sauf si un challenger le surpasse significativement sur F1 ET maintient la compatibilité SHAP.

**Limite documentée :** L'IF perd en pertinence au-delà de ~20 features hétérogènes. Le nombre de features par module doit rester dans cette limite.

---

### ADR-002 — Plugin Contract = YAML + classe Python
**Statut :** ✅ ACCEPTÉE | **Date :** 17 avril 2026

**Contexte :** Comment formaliser le contrat d'un module ?

**Décision :** 1 fichier YAML déclaratif + 1 classe Python héritant de `BaseModule`.

**Justification :**
- YAML : lisible et modifiable par un expert métier sans développeur
- Python : point d'extension contrôlé, vérifié à la compilation
- Validation fail-fast au chargement : impossible de démarrer avec un module invalide
- Zéro modification du Kernel pour ajouter un module

**Conséquences :** Tout expert métier peut modifier les règles RCA en éditant le YAML. Tout développeur peut ajouter un module en < 50 lignes Python.

---

### ADR-003 — Mistral 7B local via Ollama
**Statut :** ✅ ACCEPTÉE | **Date :** 17 avril 2026

**Contexte :** Quel LLM pour la narration RCA en français ?

**Décision :** Mistral 7B via Ollama, exécution 100% locale.

**Justification :**
- Open source, pas de coût d'API
- Données sensibles restent en local
- Performances suffisantes pour narration structurée contrainte
- Mode dégradé template-based si Ollama indisponible

**Conséquences :** Latence ~5-10s par narration. Grille d'évaluation anti-hallucination obligatoire sur 5 critères.

---

### ADR-004 — Analyse de graphe en V1 comme brique optionnelle
**Statut :** ✅ ACCEPTÉE | **Date :** 17 avril 2026

**Contexte :** La fraude en réseau est invisible à l'IF individuel.

**Décision :** NetworkX + Louvain comme brique optionnelle du Kernel, activable par `graph_analysis.enabled: true` dans le YAML.

**Justification :**
- La fraude en réseau est un vecteur majeur non couvrable par l'IF seul
- L'architecture optionnelle garantit que les modules sans graphe (Vie, Agricole) ne sont pas impactés
- Fail-safe : une erreur dans la brique graphe ne bloque pas le reste du pipeline

**Conséquences :** Le dataset doit contenir des identifiants relationnels stables. Le résultat graphe enrichit le champ `graph_analysis` nullable de la sortie JSON.

---

### ADR-005 — Format de sortie JSON immuable
**Statut :** ✅ ACCEPTÉE | **Date :** 17 avril 2026

**Contexte :** Le dashboard Next.js doit fonctionner avec tous les modules sans adaptation.

**Décision :** Format de sortie JSON strictement standardisé. Tout nouveau champ doit être nullable.

**Justification :**
- Un dashboard universel ne peut exister que si le contrat de données est fixe
- Les champs nullables permettent l'évolution sans breaking change

**Règle :** Modifier le format de sortie = ADR obligatoire.

---

### ADR-006 — Comparaison formelle des algorithmes
**Statut :** ✅ ACCEPTÉE | **Date :** 17 avril 2026

**Contexte :** Le jury demandera "pourquoi IF et pas autre chose ?"

**Décision :** Comparaison formelle en Phase 1 sur le dataset Santé : IF, LOF, One-Class SVM (+ Autoencoder si temps disponible).

**Critères d'évaluation :**

| Critère | Poids | Note |
|---|---|---|
| F1-score | Élevé | Métrique principale |
| Précision | Élevé | |
| Rappel | Élevé | |
| Compatibilité SHAP | **Éliminatoire** | Sans SHAP → disqualifié |
| Temps entraînement | Moyen | |
| Temps inférence | Moyen | |

**Livrable :** Tableau comparatif dans le rapport de validation finale (Phase 4).

---

### ADR-007 — Stratégie d'évolution en 3 niveaux
**Statut :** ✅ ACCEPTÉE | **Date :** 17 avril 2026

**Contexte :** Comment gérer les ajouts futurs sans déstabiliser le Kernel ?

**Décision :**

| Niveau | Type d'évolution | Impact Kernel | Processus |
|---|---|---|---|
| **1** | Modifier une règle RCA ou un seuil | Aucun | Éditer YAML uniquement |
| **2** | Nouveau module métier | Aucun | Créer YAML + classe Python |
| **3** | Nouvelle capacité algorithmique | Extension contrôlée | ADR obligatoire avant code |

**Règle :** Toute évolution Niveau 3 → ADR dans ce document AVANT toute ligne de code.

---

## 9. STRATÉGIE D'ÉVOLUTION — GOUVERNANCE DES EXTENSIONS

### 9.1 Processus d'ajout d'un nouveau module (Niveau 2)

```
1. Créer modules/nouveau_module/
2. Écrire nouveau_module.yaml (respecter Plugin Contract — section 4.3)
3. Écrire nouveau_module_module.py (hériter BaseModule — section 4.2)
4. Passer la checklist de validation (section 4.4)
5. Rédiger le README.md du module
6. Exécuter les tests unitaires et d'intégration
7. Mettre à jour MASTER_CONTEXT.md (statut module)
```

Durée estimée pour un développeur maîtrisant le framework : **2-4 heures**.

### 9.2 Processus d'extension du Kernel (Niveau 3)

```
1. Rédiger l'ADR dans ce document (section 8)
   → Contexte, décision, justification, conséquences
2. Valider l'ADR (auto-validation pour ce projet)
3. Implémenter la brique dans core/nouvelle_brique.py
4. Ajouter le champ nullable dans le format de sortie JSON (ADR-005)
5. Ajouter les tests unitaires de la nouvelle brique
6. Vérifier que tous les tests existants passent (non-régression)
7. Mettre à jour ARCHITECTURE.md
```

### 9.3 Exemples d'évolutions futures catégorisées

| Évolution | Niveau | Justification |
|---|---|---|
| Ajouter un seuil de surfacturation Auto | 1 | Modification YAML uniquement |
| Créer le module Micro-Assurance | 2 | Nouveau YAML + classe Python |
| Module Vie en production | 2 | Nouveau YAML + classe Python + dataset |
| Détection fraude réseau Auto | 2 | Activer `graph_analysis: enabled: true` dans auto.yaml |
| Ajouter un Autoencoder comme alternative à l'IF | 3 | Modification de `detector.py` → ADR requis |
| Intégration NLP sur ordonnances manuscrites | 3 | Nouvelle brique Kernel → ADR requis |
| Réentraînement automatique sur feedback | 3 | Modification du cycle de vie du modèle → ADR requis |

---

## 10. DIAGRAMMES D'ARCHITECTURE

### 10.1 Diagramme de contexte système

```
                    ┌─────────────────────────────────┐
                    │                                 │
  ┌───────────────┐ │         MAKORA FRAMEWORK        │ ┌──────────────────┐
  │  Gestionnaire │◄├── Dashboard Next.js             │ │  Système source  │
  │  de sinistres │ │   (alertes + diagnostics)       │ │  (API / Scanner) │
  └───────────────┘ │                                 │ └────────┬─────────┘
                    │                                 │          │ CSV/JSON
  ┌───────────────┐ │   ┌─────────────────────────┐  │          │ PDF/Image
  │    Auditeur   │◄├── │     Kernel MAKORA        │◄─┼──────────┘
  └───────────────┘ │   │  (pipeline ML + RCA)     │  │
                    │   └─────────────────────────┘  │
  ┌───────────────┐ │              ▲                  │ ┌──────────────────┐
  │ Administrateur│─┼──────────────┤                  │ │  Mistral 7B      │
  └───────────────┘ │         Plugin Contract         │ │  (Ollama local)  │
                    │              │                  │ └──────────────────┘
  ┌───────────────┐ │   ┌──────────┴──────────┐       │
  │ Expert métier │─┼──►│   Modules Métiers   │       │
  │ (YAML editor) │ │   │ Santé | Auto | ...  │       │
  └───────────────┘ │   └─────────────────────┘       │
                    │                                 │
                    └─────────────────────────────────┘
```

### 10.2 Diagramme de séquence — Analyse d'un dossier

```
Client      API FastAPI    Pipeline     Module      Detector    RCA Engine    LLM
  │               │            │           │             │            │         │
  │─POST /analyze─►            │           │             │            │         │
  │               │─run(module)─►          │             │            │         │
  │               │            │─engineer──►             │            │         │
  │               │            │  features  ◄────────────│            │         │
  │               │            │───────────────detect───►│            │         │
  │               │            │◄──────────score─────────│            │         │
  │               │            │───────────────shap──────►            │         │
  │               │            │◄──────────top_3──────────────────────│         │
  │               │            │───────────────────────apply_rules────►         │
  │               │            │◄──────────────────────────rca_result─│         │
  │               │            │────────────────────────────────────narrate────►│
  │               │            │◄───────────────────────────────────explanation─│
  │               │◄──JSON─────│           │             │            │         │
  │◄──200 JSON────│            │           │             │            │         │
```

---

## 11. CONTRAINTES D'ARCHITECTURE NON-NÉGOCIABLES

Ces règles ne peuvent pas être violées, même pour une bonne raison apparente. Toute exception nécessite un ADR Niveau 3 et une justification explicite.

```
RÈGLE 1 — ISOLATION DU KERNEL
Le Kernel (core/) ne contient aucun import direct d'un module métier.
Il reçoit uniquement des instances de BaseModule.
Violation détectable : grep -r "from modules" core/

RÈGLE 2 — IMMUABILITÉ DU FORMAT DE SORTIE
Le format JSON de sortie est fixe. Tout nouveau champ est nullable.
Modifier un champ existant = ADR obligatoire.

RÈGLE 3 — RÈGLES RCA DANS LE YAML, PAS DANS LE CODE
Aucune logique de classification RCA dans les fichiers Python.
Les conditions if/else métier appartiennent au YAML.
Violation : logique de type "if ratio > 1.5: category = 'Fraude'" dans un .py

RÈGLE 4 — EXTENSION KERNEL = ADR D'ABORD
Toute nouvelle brique dans core/ nécessite un ADR validé avant la première ligne de code.

RÈGLE 5 — RANDOM_STATE = 42 PARTOUT
Tout algorithme aléatoire utilise random_state=42 pour la reproductibilité.

RÈGLE 6 — DONNÉES RÉELLES HORS DU DÉPÔT
Aucune donnée patient réelle dans le repo Git.
Le .gitignore exclut data/raw/ et tout fichier *.parquet non-synthétique.

RÈGLE 7 — COMPATIBILITÉ SHAP NON-NÉGOCIABLE
Tout algorithme de détection ajouté doit avoir un explainer SHAP fonctionnel.
Sans explicabilité SHAP → non éligible comme algorithme MAKORA.
```

---

*Fin du document — Architecture & Plugin Contract v1.0*
*Prochaine mise à jour : fin Phase 1 (après implémentation module Santé complet)*
*Maintenu par : ATABONG EFON STEPHANE FRITZ*
