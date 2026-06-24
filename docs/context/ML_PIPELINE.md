# ML_PIPELINE.md

## MAKORA Framework — Pipeline ML détaillé

> Dernière mise à jour : 06 juin 2026 — Phase 2 finalisée + migration DIF
> Statut : ✅ Pipeline complet · Modèle de production : Deep Isolation Forest [Xu2023]

---

## 1. VUE D'ENSEMBLE DU PIPELINE

Le pipeline MAKORA est une séquence de 9 étapes universelles, indépendantes de la
branche d'assurance. Seule l'étape 4 (Feature Engineering) délègue au module métier.

```
Données brutes (CSV/JSON/PDF)
    │
    ▼ Étape 1 — Mapping colonnes
    │  MappingEngine lit source_mappings du YAML
    │  Renomme les colonnes source → schéma universel
    │
    ▼ Étape 2 — Validation schéma
    │  SchemaValidator (Pydantic) vérifie colonnes requises
    │  Retourne (True, []) ou (False, [erreurs])
    │
    ▼ Étape 3 — Normalisation
    │  XAF → EUR (taux BEAC), log-transform montants
    │  Encodage catégorielles (Sexe M/F → 0/1)
    │
    ▼ Étape 4a — Feature Engineering (via module)
    │  module.engineer_features(df) → DataFrame enrichi
    │  Délègue au SanteModule ou AutoModule via BaseModule
    │
    ▼ Étape 4b — Injection scores graphe (si activé)
    │  graph_engine.inject_scores(df) si module.is_graph_enabled()
    │  Ajoute community_score + flag_doublon dans df
    │
    ▼ Étape 5 — Extraction matrice features
    │  X = df[module.get_feature_names()].fillna(0).astype(float32)
    │
    ▼ Étape 6 — Détection ML (Deep Isolation Forest)
    │  dif.predict(X) → labels {-1, +1}
    │  dif.decision_function(X) → scores bruts
    │  Seuil calibré hardcodé par branche (phi_optimal / fpr5_constrained)
    │
    ▼ Étape 7 — Explicabilité SHAP
    │  KernelExplainer(dif.decision_function, X_background).shap_values(X_row)
    │  Calculé uniquement sur les dossiers is_anomaly=True (optimisation)
    │  X_background = 100 dossiers normaux du train set (sauvegardés en .npy)
    │
    ▼ Étape 8 — Moteur RCA
    │  RCAEngine.evaluate(features, rules) → diagnostic structuré
    │  Pattern Chain of Responsibility — première règle matchée
    │
    ▼ Étape 9 — Narration LLM
       LLMNarrator.narrate(contexte) → explication FR naturelle
       Fallback template si Ollama indisponible
       Sortie : MAKORAOutput (JSON standardisé)
```

---

## 2. ALGORITHMES COMPARÉS — RÉSULTATS PHASE 2 COMPLÈTE

### 2.1 Protocole de comparaison [Goldstein2016] + [ADR-006]

- Split fixe 70/15/15 — seed=42 — niveau IDs uniques (anti-fuite)
- Évaluation sur test set IMMUTABLE uniquement
- Métrique principale : **MCC [Chicco2020]** — robuste aux classes déséquilibrées
- FPR comme contrainte disjonctive de déploiement [Bauder2017]
- IC bootstrap MCC : n=1000 répétitions, α=0.05 [Efron1979]
- Candidats IC : 10 meilleurs par famille (DIF ×2, HBOS, IF×2, COPOD, ECOD, EIF, LOF, OC-SVM)

### 2.2 Résultats — Branche Santé

Dataset : 140 225 lignes — 38 663 IDs uniques — 6.83% anomalies
Split test : 21 228 lignes — ~6.9% anomalies — IMMUTABLE

| Famille | Algorithme · Calibration           | MCC        | F1     | AUC    | AP     | FPR        | IC 95% MCC        | Production         |
| ------- | ---------------------------------- | ---------- | ------ | ------ | ------ | ---------- | ----------------- | ------------------ |
| **DIF** | **DIF [64,32] — phi_optimal ★**    | **0.2449** | 0.2637 | 0.6423 | 0.2010 | **0.0218** | _à calculer T-05_ | ✅ **PROD**        |
| DIF     | DIF [64,32] — fpr5_constrained     | 0.2400     | 0.2770 | 0.6423 | 0.2010 | 0.0325     | _à calculer T-05_ | candidat           |
| PU Lrn  | PU RF c=0.0935 [Elkan2008] ⚠️      | 0.2442     | 0.2937 | 0.6994 | 0.1580 | 0.1386     | _à calculer T-05_ | semi-sup.          |
| HBOS    | HBOS n_bins=5 [Goldstein2012]      | 0.2229     | 0.2795 | 0.6275 | 0.2452 | 0.0628     | _à calculer T-05_ | candidat           |
| EIF     | EIF ExtLvl=1 [Hariri2019]          | 0.1720     | 0.2295 | 0.6339 | 0.1944 | 0.0581     | N/A               | ❌ non persistable |
| IF      | IF max_feat=0.7 [Liu2008]          | 0.1446     | 0.2104 | 0.6296 | 0.1558 | 0.0810     | _à calculer T-05_ | candidat           |
| IF      | IF classique [Liu2008] _(ex-prod)_ | 0.1376     | 0.2004 | 0.6221 | 0.1605 | 0.0885     | [0.110–0.161]     | baseline réf.      |
| COPOD   | COPOD empirique [Li2020]           | 0.1581     | 0.2253 | 0.6242 | 0.2218 | 0.1103     | _à calculer T-05_ | candidat           |
| ECOD    | ECOD CDF [Li2022]                  | 0.1323     | 0.2035 | 0.6243 | 0.2002 | 0.1249     | _à calculer T-05_ | candidat           |
| LOF     | LOF k=20 [Breunig2000]             | 0.0791     | 0.1490 | 0.6030 | 0.0910 | 0.2950     | _à calculer T-05_ | ❌ O(n²k)          |
| OC-SVM  | OC-SVM SGD [Schölkopf2001]         | 0.0000     | 0.1287 | 0.3390 | 0.0490 | 1.0000     | [0.000–0.000]     | ❌ écarté          |

_⚠️ PU Learning : avantage informationnel (labels pseudo) — non comparable aux non-supervisés._
_IC [0.110–0.161] IF classique = IC issu des résultats IF de la Phase 2 initiale._

### 2.3 Résultats — Branche Auto

Dataset : 100 000 lignes — 100 000 IDs uniques — 8.00% anomalies
Split test : 15 000 lignes — ~8.0% anomalies — IMMUTABLE

| Famille | Algorithme · Calibration             | MCC        | F1     | AUC    | AP     | FPR        | IC 95% MCC        | Production         |
| ------- | ------------------------------------ | ---------- | ------ | ------ | ------ | ---------- | ----------------- | ------------------ |
| LOF     | LOF k=20 [Breunig2000]               | 0.3047     | 0.3376 | 0.6542 | 0.2962 | 0.0300     | _à calculer T-05_ | ❌ O(n²k)          |
| EIF     | EIF ExtLvl=1 [Hariri2019]            | 0.2351     | 0.3015 | 0.6968 | 0.2397 | 0.0792     | N/A               | ❌ non persistable |
| **DIF** | **DIF [64,32] — fpr5_constrained ★** | **0.2231** | 0.2769 | 0.6770 | 0.2193 | **0.0479** | _à calculer T-05_ | ✅ **PROD**        |
| DIF     | DIF [64,32] — phi_optimal            | 0.2234     | 0.2822 | 0.6770 | 0.2193 | 0.0555     | _à calculer T-05_ | candidat           |
| PU Lrn  | PU RF c=0.0885 [Elkan2008] ⚠️        | 0.2684     | 0.3313 | 0.6939 | 0.1871 | 0.1141     | _à calculer T-05_ | semi-sup.          |
| IF      | IF max_feat=0.7 [Liu2008]            | 0.2084     | 0.2759 | 0.6855 | 0.2169 | 0.0756     | _à calculer T-05_ | candidat           |
| ECOD    | ECOD CDF [Li2022]                    | 0.2009     | 0.2726 | 0.6856 | 0.2508 | 0.1477     | _à calculer T-05_ | candidat           |
| IF      | IF classique [Liu2008] _(ex-prod)_   | 0.1966     | 0.2654 | 0.6843 | 0.2127 | 0.1069     | [0.168–0.227]     | baseline réf.      |
| COPOD   | COPOD empirique [Li2020]             | 0.1764     | 0.2500 | 0.6828 | 0.2477 | 0.1920     | _à calculer T-05_ | candidat           |
| HBOS    | HBOS n_bins=5 [Goldstein2012]        | 0.2007     | 0.2733 | 0.6763 | 0.2393 | 0.1076     | _à calculer T-05_ | candidat           |
| OC-SVM  | OC-SVM SGD [Schölkopf2001]           | 0.0000     | 0.1481 | 0.3750 | 0.1390 | 1.0000     | [0.000–0.000]     | ❌ écarté          |

_Observation Auto : LOF k=20 (MCC=0.305) et EIF (MCC=0.235) dépassent DIF en score brut mais sont respectivement O(n²k) non-scalable et non-persistable (ADR-010). DIF [64,32] est le meilleur algorithme deployable._

### 2.4 Décision de production — Justification multicritères

**Algorithme retenu : Deep Isolation Forest [Xu2023] — architecture [64, 32]**

Migration depuis IF classique (ex-production) documentée en ADR-013 (à rédiger).

| Critère            | DIF [64,32]       | IF classique     | EIF           | LOF k=20      | OC-SVM        |
| ------------------ | ----------------- | ---------------- | ------------- | ------------- | ------------- |
| MCC Santé / Auto   | **0.245 / 0.223** | 0.134 / 0.197    | 0.172 / 0.235 | 0.079 / 0.305 | 0.000 / 0.000 |
| FPR Santé / Auto   | **0.022 / 0.048** | 0.079 / 0.107    | 0.058 / 0.079 | 0.295 / 0.030 | 1.000 / 1.000 |
| KernelSHAP         | ✅                | ✅ TreeExplainer | ✅ KernelSHAP | ✅ KernelSHAP | ✅            |
| Persistance joblib | ✅                | ✅               | ❌ ADR-010    | ✅            | ✅            |
| Scalable > 100k    | ✅ O(n·d)         | ✅ O(n log n)    | ✅            | ❌ O(n²k)     | ✅ SGD        |
| Verdict            | ★ PRODUCTION      | Baseline réf.    | Challenger    | Écarté        | Écarté        |

Gain DIF vs IF classique ex-prod :

| Branche | Gain MCC      | Gain FPR                  |
| ------- | ------------- | ------------------------- |
| Santé   | +0.111 (+82%) | −5.7 pts (8.85% → 2.18%)  |
| Auto    | +0.026 (+13%) | −5.9 pts (10.69% → 4.79%) |

Référence : [Sculley2015] — le déploiement est une contrainte de premier ordre.
Référence : [Chicco2020] — MCC est la métrique la plus fiable sur données déséquilibrées.

---

## 3. EXPÉRIENCE H0 — RÉSULTATS AVEC IF (PHASE 2 INITIALE)

> **Note :** Ces résultats utilisent IF classique comme algorithme de base.
> La re-run avec DIF est planifiée en T-06 avant la présentation du 08 juin 2026.

### 3.1 Protocole [Caruana1997]

```
M_sante  = IF entraîné sur data/splits/sante/sante_train.parquet (98 012 lignes, 17 features)
M_auto   = IF entraîné sur data/splits/auto/auto_train.parquet   (70 000 lignes, 18 features)
M_makora = IF entraîné sur concat(sante_train + auto_train)      (168 012 lignes, 4 features communes)

Features communes M_makora — espace quasi-orthogonal (< 12% recouvrement) :
  - anciennete_contrat_courte   ← fraude souscription, universel
  - document_altere             ← fraude documentaire, universel
  - ocr_confiance_faible        ← qualité doc suspecte, contexte CM
  - saisie_hors_heures          ← comportement temporel, universel

Contamination M_makora = 0.073 (moyenne pondérée 0.068×98012 + 0.080×70000 / 168012)
```

### 3.2 Tableau comparatif H0 — IF classique

| Modèle                   | Branche éval. | F1     | IC 95% F1     | AUC   | MCC       | FPR       | Train time |
| ------------------------ | ------------- | ------ | ------------- | ----- | --------- | --------- | ---------- |
| M_sante (spécialisé)     | sante         | 0.2004 | [0.182–0.219] | 0.622 | 0.134     | 0.079     | 3.1s       |
| **M_makora (générique)** | sante         | 0.1554 | [0.132–0.180] | 0.543 | **0.281** | **0.000** | 2.5s       |
| M_auto (spécialisé)      | auto          | 0.2654 | [0.241–0.288] | 0.684 | 0.197     | 0.075     | 2.8s       |
| **M_makora (générique)** | auto          | 0.2482 | [0.223–0.273] | 0.609 | 0.192     | 0.051     | 2.5s       |

### 3.3 Verdict Δ F1 — IF classique

| Branche | Δ F1    | Δ%     | Verdict                                   |
| ------- | ------- | ------ | ----------------------------------------- |
| Santé   | +0.0450 | +4.50% | ✅ **CONTRIBUTION_VALIDÉE** (Δ ∈ [2%,7%]) |
| Auto    | +0.0172 | +1.72% | 🏆 **GÉNÉRICITÉ_SANS_COÛT** (Δ < 2%)      |

H0 validée — l'architecture plugin générique maintient une précision acceptable.

### 3.4 Observation remarquable — MCC M_makora Santé

M_makora obtient MCC=0.281 vs M_sante MCC=0.134 malgré un F1 inférieur.
FPR=0.000 : zéro faux positif sur 21 228 dossiers. M_makora est ultra-conservateur
avec seulement 4 features communes. Dans un contexte opérationnel où un faux positif
signifie un assuré légitime bloqué (plainte, perte client), ce comportement peut être
préférable. [Bauder2017] documente ce trade-off en contexte assurance.

### 3.5 H0 avec DIF — À FAIRE (T-06)

```
Protocole identique, algorithme remplacé :
M_sante_dif  = DIF [64,32] entraîné sur sante_train (17 features)
M_auto_dif   = DIF [64,32] entraîné sur auto_train  (18 features)
M_makora_dif = DIF [64,32] entraîné sur concat (4 features communes)
               contamination = 0.073

Métriques à reporter : F1, IC 95% F1, AUC, MCC, FPR
Δ à calculer : Δ_F1 ET Δ_MCC (métrique principale)
Question ouverte : l'observation MCC_makora > MCC_spécialisé se confirme-t-elle avec DIF ?
Temps estimé : ~2h calcul + ~30min rédaction
```

---

## 4. HYPERPARAMÈTRES DE PRODUCTION

### 4.1 Deep Isolation Forest — paramètres validés [Xu2023]

```python
# Architecture et entraînement — identique Santé et Auto
DIF(
    hidden_neurons=[64, 32],    # Xu2023 — architecture baseline testée
    contamination=0.070,        # Santé : taux fraude réel ~6.83%
    random_state=42,            # Reproductibilité [Kohavi1995]
    device="cpu",               # Contrainte déploiement africain sans GPU
)
# Auto : contamination=0.100

# Seuils de décision calibrés — hardcodés dans DIFStrategy (pas en YAML)
THRESHOLD_SANTE = 0.349775   # Calibration phi_optimal sur val set
THRESHOLD_AUTO  = 0.341498   # Calibration fpr5_constrained sur val set

# Calibration du seuil — stratégie par branche [Davis2006]
# Santé → phi_optimal : maximise Φ=(F1+AUC+MCC+AP+(1-FPR))/5 sur val
# Auto  → fpr5_constrained : max F1 sous contrainte FPR ≤ 5%
```

### 4.2 Isolation Forest — paramètres Phase 2 initiale (baseline référence)

```python
# Branche Santé — ex-production, conservé comme baseline de comparaison
IsolationForest(
    n_estimators=200,       # Liu2008 : convergence > 100 arbres
    contamination=0.068,    # Calibré sur val set — taux réel ~6.83%
    max_features=1.0,
    random_state=42,
    n_jobs=-1,
)

# Branche Auto — ex-production
IsolationForest(
    n_estimators=200,
    contamination=0.080,
    max_features=1.0,
    random_state=42,
    n_jobs=-1,
)

# M_makora générique H0 (IF)
IsolationForest(
    n_estimators=200,
    contamination=0.073,    # Moyenne pondérée sante+auto
    max_features=1.0,
    random_state=42,
    n_jobs=-1,
)
```

### 4.3 Normalisation des scores DIF

```python
# DIF : decision_function() retourne des scores bruts (positif = normal)
# Le seuil de décision est fixe (calibré sur val set, hardcodé)
scores = model.decision_function(X)
y_pred = (scores >= threshold).astype(int)   # 1 = anomalie, 0 = normal
# Pas de normalisation [0,1] — le seuil brut est suffisant
```

### 4.4 Drift Monitor — seuils PSI [Gama2014]

```python
PSI_STABLE   = 0.10   # < 0.10 : distribution stable
PSI_WARNING  = 0.20   # [0.10, 0.20[ : changement notable
PSI_CRITICAL = 0.20   # ≥ 0.20 : dérive significative → réentraîner

REFERENCE_WINDOW_DAYS = 90
CURRENT_WINDOW_DAYS   = 30
N_BINS = 10                  # Standard industrie bancaire/assurance
```

---

---

_Suite dans ML_PIPELINE_FEATURES.md (sections 5-10)_
