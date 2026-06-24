# ARCHITECTURE.md
## MAKORA Framework — Décisions d'architecture et ADR
> Ne pas redébattre les décisions marquées ✅ ACCEPTÉE sans raison technique majeure.
> Toute nouvelle décision architecturale doit être ajoutée ici comme ADR.
> Dernière mise à jour : 22 mai 2026 — Phase 2 terminée (Session IV)

---

## 1. STRUCTURE DES DOSSIERS DU PROJET

```
makora/
│
├── context/                          ← Fichiers contexte IA
│
├── core/                             ← Kernel MAKORA (JAMAIS modifier pour un module)
│   ├── pipeline.py                   ← Orchestrateur 9 étapes — COMPLET ✅
│   ├── base_module.py                ← Interface BaseModule — Plugin Contract — COMPLET ✅
│   ├── plugin_registry.py            ← PluginRegistry + discover() — COMPLET ✅
│   ├── mapping_engine.py             ← Couche mapping colonnes (lit YAML) — COMPLET ✅
│   ├── schema_validator.py           ← Validation Pydantic — COMPLET ✅
│   ├── normalizer.py                 ← XAF→EUR, log-transform, encodage — COMPLET ✅
│   ├── detector.py                   ← Isolation Forest + Strategy Pattern — COMPLET ✅
│   ├── explainer.py                  ← SHAP TreeExplainer — COMPLET ✅
│   ├── rca/
│   │   └── engine.py                 ← RCAEngine Chain of Responsibility — COMPLET ✅
│   ├── graph_engine.py               ← NetworkX + Louvain — COMPLET ✅ (Phase 2 Bloc C)
│   ├── llm/
│   │   └── narrator.py               ← Qwen 2.5:7b via Ollama + fallback — COMPLET ✅
│   ├── drift_monitor.py              ← PSI drift monitoring — COMPLET ✅ (Phase 2 Bloc D)
│   ├── audit_logger.py               ← Journal décisions immuable — STUB ⚠️
│   ├── mercuriale/                   ← MercurialeLoader (CIMA + ASAC) — COMPLET ✅
│   └── ingestion/
│       └── structured_reader.py      ← Lecteur CSV/JSON/Parquet — COMPLET ✅
│
├── modules/                          ← Plugins métiers
│   ├── sante/
│   │   ├── sante.yaml                ← v0.4.0 — 17 features, 16 règles RCA ✅
│   │   ├── sante_module.py           ← SanteModule(BaseModule) ✅
│   │   ├── features.py               ← Features principales ✅
│   │   ├── features_ext.py           ← Features complémentaires ✅
│   │   └── features_reseau.py        ← Features graphe ✅
│   ├── auto/
│   │   ├── auto.yaml                 ← v1.1.0 — 18 features, 9 règles RCA ✅
│   │   ├── auto_module.py            ← AutoModule(BaseModule) ✅
│   │   ├── features.py               ← Features principales ✅
│   │   └── features_reseau.py        ← Features graphe ✅
│   ├── vie/
│   │   ├── vie.yaml                  ← Conception seulement ⚙️
│   │   └── README.md
│   └── agricole/
│       ├── agricole.yaml             ← Conception seulement ⚙️
│       └── README.md
│
├── api/                              ← FastAPI — À implémenter Phase 3
│   ├── main.py                       ← VIDE ❌
│   ├── routers/
│   │   ├── analyze.py                ← VIDE ❌
│   │   ├── audit.py                  ← VIDE ❌
│   │   ├── drift.py                  ← VIDE ❌
│   │   └── modules.py                ← VIDE ❌
│   └── schemas/                      ← VIDE ❌
│
├── data/
│   ├── raw/                          ← gitignored
│   ├── processed/
│   │   ├── sante/dataset_sante_v1.parquet   ✅ 140 225 lignes
│   │   └── auto/dataset_auto_v1.parquet     ✅ 100 000 lignes
│   ├── splits/
│   │   ├── sante/{train,val,test}.parquet   ✅ IMMUTABLES
│   │   └── auto/{train,val,test}.parquet    ✅ IMMUTABLES
│   ├── models/
│   │   ├── sante/production/if_classic_model.joblib  ✅ PRODUCTION
│   │   ├── auto/production/if_classic_model.joblib   ✅ PRODUCTION
│   │   └── h0/{M_sante_sante, M_auto_auto, M_makora}.joblib ✅ H0
│   └── referentials/
│       ├── bareme_asac_auto.yaml     ✅ 28 codes XAF
│       └── mercuriale_cima.yaml      ✅ santé
│
├── results/
│   ├── sante/                        ✅ Métriques + SHAP + LIME + learning curves
│   ├── auto/                         ✅ Métriques + SHAP + LIME + learning curves
│   ├── h0/                           ✅ T12.1/T12.2/T12.3 — rapports Markdown
│   └── figures/                      ✅ PCA 2D, SHAP summary, learning curves
│
├── frontend/                         ← Next.js — À implémenter Phase 3
│
├── tests/
│   ├── unit/                         ✅ ~400+ tests
│   ├── integration/                  ✅ ~60 tests
│   ├── contract/                     ✅ Isolation Kernel/Module préservée
│   └── fixtures/                     ✅ datasets synthétiques
│
└── scripts/                          ✅ T10.x + T12.x + T13.x + T15.x
```

---

## 2. RÈGLE ABSOLUE — ISOLATION KERNEL / MODULES

```
Le Kernel ne doit JAMAIS importer un module métier par son nom concret.
Il ne connaît les modules QUE via BaseModule et PluginRegistry.

✅ CORRECT :
    module = PluginRegistry.get("sante")(config_path=yaml_path)
    df_eng = module.engineer_features(df)

❌ INTERDIT :
    from modules.sante.sante_module import SanteModule
    from modules.auto import auto_module
```

Vérifié automatiquement par `tests/contract/` (analyse AST).

---

## 3. HIÉRARCHIE DES NIVEAUX D'ABSTRACTION

```
NIVEAU 0 — Interfaces abstraites (base_module.py)
    ↓ implémentées par
NIVEAU 1 — Modules métiers (sante_module.py, auto_module.py)
    ↓ orchestrés par
NIVEAU 2 — Kernel (pipeline.py, detector.py, explainer.py, rca/engine.py...)
    ↓ exposés par
NIVEAU 3 — API (FastAPI routers) — Phase 3
    ↓ consommés par
NIVEAU 4 — Frontend (Next.js) — Phase 3
```

---

## 4. PATTERNS OBLIGATOIRES

| Pattern | Où utilisé | Justification |
|---|---|---|
| **Strategy Pattern** | `detector.py` — IF/LOF/OC-SVM interchangeables | Swap d'algorithme sans modifier le pipeline [GoF1994] |
| **Plugin Registry** | `plugin_registry.py` | Découverte dynamique des modules — découplage fort |
| **Chain of Responsibility** | `rca/engine.py` | Règles RCA priorisées — première règle matchée [GoF1994] |
| **Model Card** | `data/models/*/production/model_card.json` | Documentation [Amershi2019] |

---

## 5. ARCHITECTURE DECISION RECORDS (ADR)

### ADR-001 — Isolation Forest comme algorithme de détection de base
**Statut :** ✅ ACCEPTÉE — CONFIRMÉE Phase 2
**Décision :** IF classique [Liu2008] retenu en production.
**Justification :** Non-supervisé (labels rares en contexte africain), compatible SHAP TreeExplainer, joblib, scalable O(n log n).
**Résultats :** F1=0.2004 Santé / F1=0.2654 Auto sur test sets immutables.
**Note Phase 2 :** EIF [Hariri2019] surpasse IF (F1=0.239/0.286) mais non persistable.
IF max_features=0.7 légèrement supérieur (F1=0.210/0.276) mais choix IF classique maintenu pour stabilité SHAP.

---

### ADR-002 — Plugin Contract = YAML déclaratif + classe Python
**Statut :** ✅ ACCEPTÉE — CONFIRMÉE Phase 2
**Décision :** 1 fichier YAML + 1 classe héritant de `BaseModule`.
**Résultats Phase 2 :** Deux modules complets (Santé 17 features + Auto 18 features) implémentés sans modification du Kernel. Isolation vérifiée par `tests/contract/`.

---

### ADR-003 — Qwen 2.5:7b via Ollama (local)
**Statut :** ✅ ACCEPTÉE
**Note :** Le mémoire et les prompts référencent Mistral 7B [Jiang2023] comme référence académique. L'implémentation utilise Qwen 2.5:7b pour ses meilleures performances en français et JSON structuré.
**Fallback :** template-based si Ollama indisponible — non-bloquant.

---

### ADR-004 — Analyse de graphe en V1 comme brique optionnelle
**Statut :** ✅ ACCEPTÉE — IMPLÉMENTÉE Phase 2 (Bloc C)
**Implémentation :** NetworkX + Louvain [Blondel2008] + fallback `greedy_modularity`.
**Décision Bloc C — MAD vs mean+std :** seuil de suspicion basé sur médiane + MAD [Rousseeuw1993] — mean+std biaise le seuil sur les outliers eux-mêmes (biais auto-exclusion démontré sur fixtures). `weight_sigma_threshold` externalisé dans YAML (défaut 2.0).
**Tests :** 21/21 — Santé + Auto.

---

### ADR-005 — Format de sortie `MAKORAOutput` standardisé
**Statut :** ✅ ACCEPTÉE — CONFIRMÉE Phase 2
**Décision :** `MAKORAOutput` dataclass immuable avec champs nullable.
**Garantit :** le dashboard Phase 3 fonctionne avec n'importe quel module sans adaptation.

---

### ADR-006 — Comparaison IF, LOF, OC-SVM sur splits identiques
**Statut :** ✅ ACCEPTÉE — ✅ EXÉCUTÉE Phase 2 (T10.3 + T10.4 + T10.7)
**Résultats :** Tableau comparatif complet avec IC bootstrap + McNemar.
Voir `ML_PIPELINE.md §2` + `results/*/t10_7_comparative_table.json`.

---

### ADR-007 — PaddleOCR = moteur OCR principal
**Statut :** ✅ ACCEPTÉE
**Justification :** Meilleure précision sur documents dégradés (cachet humide, papier froissé) [Li2022].
Tesseract reste en fallback (ADR-008).

---

### ADR-008 — OCR dual + arbitrage LLM ; si LLM KO → échec propre
**Statut :** ✅ ACCEPTÉE
**Justification :** Les regex hardcodées sont trop fragiles sur les documents camerounais manuscrits. "Primum non nocere" — un résultat absent > un résultat erroné.

---

### ADR-009 — Cycle ML différé après Phase 2
**Statut :** ✅ ACCEPTÉE — ✅ CLÔTURÉE Phase 2
**Justification :** L'expérience H0 nécessitait les deux modules entraînés simultanément [Caruana1997].
**Résultat :** H0 conduite — Δ Santé=+4.50% (CONTRIBUTION_VALIDÉE) / Δ Auto=+1.72% (GÉNÉRICITÉ_SANS_COÛT).

---

### ADR-010 (nouveau Phase 2) — IF classique retenu en production vs EIF
**Statut :** ✅ ACCEPTÉE — Phase 2 Session II
**Contexte :** EIF [Hariri2019] surpasse IF classique (F1 +3.4pts Santé, +1.6pts Auto) mais incompatible joblib (Cython `__cinit__` non-picklable).
**Décision :** IF classique en production, EIF documenté comme challenger dans le mémoire (ch.5).
**Alternative écartée :** IF max_features=0.7 (légèrement supérieur mais moins stable en SHAP).

---

### ADR-011 (nouveau Phase 2) — MAD pour seuil suspicion graphe
**Statut :** ✅ ACCEPTÉE — Phase 2 Session III (Bloc C)
**Contexte :** Calcul du seuil de communauté suspecte dans `graph_engine.py`.
**Décision :** `médiane + k × MAD` au lieu de `mean + k × std`. [Rousseeuw1993]
**Justification empirique :** mean+std biaise le seuil au-dessus des outliers eux-mêmes (biais d'auto-exclusion démontré sur fixtures Louvain). MAD résistant aux outliers.
**Paramètre :** `weight_sigma_threshold` externalisé dans YAML (défaut 2.0).

---

### ADR-012 (nouveau Phase 2) — M_makora = intersection 4 features communes
**Statut :** ✅ ACCEPTÉE — Phase 2 Session IV (Bloc E)
**Contexte :** Construction du dataset d'entraînement M_makora pour H0.
**Décision :** Intersection Santé ∩ Auto = 4 features comportementales transverses.
**Alternative écartée :** Union avec imputation (espaces incompatibles — XAF vs EUR, ratios vs montants absolus).
**Justification :** [Caruana1997] — le transfert multi-tâche requiert un espace de features partagé. Les 4 features communes (`anciennete_contrat_courte`, `document_altere`, `ocr_confiance_faible`, `saisie_hors_heures`) sont des signaux comportementaux universels.
**Amélioration future :** créer `modules/shared/common_features.yaml` pour éviter que la liste soit hardcodée dans les scripts.

---

## 6. DÉCISIONS D'IMPLÉMENTATION (IMP)

| ID | Décision | Justification |
|---|---|---|
| IMP-001 | Imports via `from core.xxx` | Structure Docker `/app/core/` |
| IMP-002 | Tests via Docker | Incompatibilité ABI NumPy 2.x vs scipy/sklearn Anaconda |
| IMP-003 | `pytest.ini` sans `--cov` | Bug pytest-cov + Anaconda |
| IMP-004 | `Detector` prend une instance de stratégie | Inversion de dépendance |
| IMP-005 | Tests E2E : entraînement sur données normales uniquement | Non-supervisé : contamination au scoring, pas à l'entraînement |
| IMP-006 | `SanteModule.__init__` accepte `config_path=None` | Compatibilité tests contractuels |
| IMP-007 | Règle 400 lignes — tout fichier > 400 lignes → délégation | Évite les God Objects |
| IMP-008 | `INSURANCE_DOMAIN_CONTEXT.md` fourni avant feature engineering | Ancrage réalité métier |
| IMP-009 | `MercurialeLoader` = composant dédié `core/mercuriale/` | Séparation responsabilités |
| IMP-010 | Contexte domaine = fichier Markdown uniquement | Pas d'assertions dans le code de production |
| IMP-011 | Normalisation par branche avant concat M_makora | Évite biais d'échelle XAF vs EUR |
| IMP-012 | Contamination M_makora = moyenne pondérée par taille | Équilibre contribution des deux branches |

---

## 7. CONTRAINTES D'ARCHITECTURE NON-NÉGOCIABLES

1. **Zéro import de module métier dans le Kernel.** Jamais `from modules.sante import SanteModule`.
2. **Le format de sortie JSON `MAKORAOutput` est immuable.** Ajouts = champs nullables uniquement.
3. **Toute extension Kernel = ADR d'abord.** Pas une ligne de code Kernel sans ADR validé.
4. **Les règles RCA sont dans le YAML, jamais dans le code Python du Kernel.**
5. **Les paramètres ML (contamination, seuils) sont dans les YAML, jamais hardcodés.**
6. **PHASE_X_REPORT.md obligatoire avant passage à la phase suivante.**

---

*Fin du fichier ARCHITECTURE.md*
*Références : [GoF1994] [Liu2008] [Hariri2019] [Blondel2008] [Rousseeuw1993]*
*[Sculley2015] [Caruana1997] [Amershi2019] [Jiang2023]*
