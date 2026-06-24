# RESEARCH_PROTOCOL.md
## MAKORA Framework — Protocole de Recherche & Consignes de Rigueur Scientifique
> **Statut :** Document de référence — obligatoire avant toute phase de développement  
> **Auteur :** ATABONG EFON STEPHANE FRITZ  
> **Version :** v1.0 — Mai 2026  
> **Portée :** S'applique à toutes les phases (P0 → P4) sans exception

---

## 0. PHILOSOPHIE DIRECTRICE

Ce projet n'est pas un projet de développement logiciel avec un rapport en annexe.  
C'est **un travail de recherche appliquée dont le code est la preuve empirique**.

Chaque décision technique doit être :
1. **Ancrée dans l'état de l'art** — citée avec un papier de référence
2. **Justifiée par rapport aux alternatives** — pourquoi X et pas Y ?
3. **Mesurée et documentée** — les affirmations sans chiffres ne valent rien
4. **Honnête sur ses limites** — les meilleures contributions scientifiques assument leurs bornages

La rigueur n'est pas une contrainte administrative. C'est ce qui transforme un prototype en contribution.

---

## 1. PROTOCOLE DE FIN DE PHASE

### 1.1 Obligation — Livrable de phase (PHASE_REPORT)

**À la fin de chaque phase de développement (P1, P2, P3, P4), la production d'un fichier `PHASE_X_REPORT.md` est OBLIGATOIRE avant de passer à la phase suivante.**

Ce fichier documente exactement ce qui a été fait, ce qui a changé, et ce que les résultats signifient scientifiquement. Il alimente directement les chapitres du mémoire.

### 1.2 Structure du PHASE_X_REPORT.md

```markdown
# PHASE_X_REPORT.md
## MAKORA — Rapport de Phase X : [Nom de la phase]
> Date de complétion : JJ/MM/AAAA
> Durée effective : X jours

---

## 1. CE QUI A ÉTÉ IMPLÉMENTÉ

### 1.1 Composants livrés
| Composant | Fichier(s) | Statut | Tests |
|---|---|---|---|
| Ex : Pipeline ETL | core/pipeline.py | ✅ Complet | 12/12 tests OK |

### 1.2 Fonctionnalités validées
- [ ] Description précise de chaque fonctionnalité avec son critère d'acceptation

### 1.3 Ce qui n'a PAS été implémenté (et pourquoi)
> Documenter explicitement les renoncements. Un renoncement justifié est une décision de recherche.

---

## 2. DÉCISIONS PRISES DURANT CETTE PHASE

### 2.1 Décisions techniques nouvelles
| # | Décision | Alternative écartée | Justification |
|---|---|---|---|
| D-XX | ... | ... | ... |

### 2.2 ADR créés ou modifiés
> Lister les ADR avec leur numéro et statut.

### 2.3 Écarts par rapport à la conception initiale
> Tout écart par rapport aux documents de Phase 0 doit être documenté ici avec justification.
> Un écart non documenté = dette de conception.

---

## 3. RÉSULTATS EXPÉRIMENTAUX

### 3.1 Métriques de performance
| Métrique | Valeur obtenue | Seuil cible | Statut |
|---|---|---|---|
| F1-score | ... | ≥ 0.80 | ✅ / ❌ |
| Précision | ... | ... | ... |
| Rappel | ... | ... | ... |
| Temps inférence (médiane) | ... | < 2s | ... |

### 3.2 Comparaison avec l'état de l'art
> Comparer les résultats obtenus avec les benchmarks publiés dans la littérature.
> Exemple : "Liu et al. (2008) rapportent un AUC de 0.87 sur KDD Cup 1999 avec IF.
> Notre implémentation sur le dataset Santé obtient un AUC de X."

### 3.3 Analyse des faux positifs / faux négatifs
> Non optionnel. Analyser qualitativement 5-10 cas mal classés.
> Pourquoi le modèle s'est-il trompé ? Que dit cela sur ses limites ?

---

## 4. MISES À JOUR DES FICHIERS CONTEXTE

### 4.1 Fichiers modifiés cette phase
| Fichier | Nature de la modification |
|---|---|
| MASTER_CONTEXT.md | Mise à jour statut phases |
| MODULE_X.md | ... |

### 4.2 Nouveaux fichiers créés
> Lister avec description.

---

## 5. DETTE TECHNIQUE ET LIMITES IDENTIFIÉES

> Documenter sans complaisance ce qui est imparfait, approximatif, ou qui devra être
> revisité. Un mémoire qui documente ses limites est plus crédible qu'un mémoire
> qui prétend tout résoudre.

---

## 6. PROCHAINE PHASE — AJUSTEMENTS

> En quoi ce qui a été appris cette phase modifie-t-il le plan de la phase suivante ?
```

---

## 2. PROTOCOLE DE MISE À JOUR DES FICHIERS CONTEXTE

### 2.1 Règle de synchronisation

**Tout changement de conception ou d'implémentation doit se refléter dans les fichiers contexte au plus tard à la fin de la phase où il se produit.**

Les fichiers contexte ne sont pas une documentation finale — ce sont des fichiers vivants qui reflètent l'état réel du projet à tout instant.

### 2.2 Responsabilité par fichier

| Fichier | Déclenché par | Fréquence minimale |
|---|---|---|
| `MASTER_CONTEXT.md` | Fin de chaque phase | 1× par phase |
| `ARCHITECTURE.md` | Tout nouvel ADR | Immédiatement |
| `MODULE_X.md` | Toute modification du module | Immédiatement |
| `ML_PIPELINE.md` | Tout changement de pipeline | Immédiatement |
| `API_CONTRACTS.md` | Tout changement d'endpoint | Immédiatement |
| `GLOSSAIRE.md` | Tout nouveau terme technique | En continu |

### 2.3 Ce qui doit changer dans MASTER_CONTEXT.md à chaque phase

- Statut des phases (🔄 → ✅)
- Statut des modules
- Dernière session / prochaine étape
- Toute décision figée nouvellement prise

---

## 3. PROTOCOLE DE RIGUEUR SCIENTIFIQUE

### 3.1 Règle des citations

**Toute affirmation non triviale dans le code, les commentaires, les documents de conception ou le rapport doit être soutenue par une référence.**

Format de citation dans les fichiers Markdown :
```
> [Liu2008] Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). Isolation forest.
> In 2008 eighth ieee international conference on data mining (pp. 413-422). IEEE.
```

Format dans le code Python :
```python
# Isolation Forest — Liu et al. (2008), ICDM
# Score normalisé : anomaly_score = 1 / (1 + exp(score_if * 10))
# Justification normalisation : Kriegel et al. (2011) §3.2
```

### 3.2 Papiers de référence fondamentaux — À lire et citer obligatoirement

#### Détection d'anomalies — Fondements

| Réf. | Papier | Pourquoi obligatoire |
|---|---|---|
| [Liu2008] | Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). **Isolation forest**. ICDM 2008. | Algorithme central de MAKORA |
| [Breunig2000] | Breunig, M. M. et al. (2000). **LOF: identifying density-based local outliers**. SIGMOD. | Algorithme de comparaison (LOF) |
| [Chandola2009] | Chandola, V., Banerjee, A., & Kumar, V. (2009). **Anomaly detection: A survey**. ACM Computing Surveys. | Référence encyclopédique — citer dans l'intro |
| [Pimentel2014] | Pimentel, M. A. et al. (2014). **A review of novelty detection**. Signal Processing. | Taxonomie des méthodes — état de l'art |
| [Goldstein2016] | Goldstein, M., & Uchida, S. (2016). **A comparative evaluation of unsupervised anomaly detection algorithms for multivariate data**. PLOS ONE. | Comparaison empirique IF vs LOF vs autres |

#### Explicabilité (XAI)

| Réf. | Papier | Pourquoi obligatoire |
|---|---|---|
| [Lundberg2017] | Lundberg, S. M., & Lee, S. I. (2017). **A unified approach to interpreting model predictions**. NeurIPS. | SHAP — fondement de toute la brique explicabilité |
| [Ribeiro2016] | Ribeiro, M. T. et al. (2016). **"Why should I trust you?" Explaining the predictions of any classifier**. KDD. | LIME — alternative à SHAP, citer pour comparaison |
| [Arrieta2020] | Arrieta, A. B. et al. (2020). **Explainable Artificial Intelligence (XAI): Concepts, taxonomies, opportunities and challenges**. Information Fusion. | Survey XAI — référence pour contextualiser SHAP |
| [Lundberg2020] | Lundberg, S. M. et al. (2020). **From local explanations to global understanding with explainable AI for trees**. Nature Machine Intelligence. | TreeExplainer — version avancée, justifie le choix |

#### Détection de fraude en assurance

| Réf. | Papier | Pourquoi obligatoire |
|---|---|---|
| [Bauder2017] | Bauder, R. A., & Khoshgoftaar, T. M. (2017). **Medicare fraud detection using machine learning methods**. ICMLA 2017. | Référence principale fraude santé ML |
| [Viaene2002] | Viaene, S. et al. (2002). **A comparison of state-of-the-art classification techniques for expert automobile insurance fraud detection**. Journal of Risk and Insurance. | Fraude auto — à citer dans module Auto |
| [Subudhi2017] | Subudhi, S., & Panigrahi, S. (2017). **Use of optimized Fuzzy C-Means clustering and supervised classifiers for automobile insurance fraud detection**. Journal of King Saud University. | Méthodes non-supervisées en assurance auto |
| [Li2008] | Li, J. et al. (2008). **A framework for fraud detection in health insurance claims using data mining**. WKDD 2008. | Framework générique fraude santé — proximité avec MAKORA |
| [Liu2015] | Liu, Y. et al. (2015). **Fraud detection from tainted data**. KDD 2015. | Détection avec données partiellement labelisées |
| [Herland2018] | Herland, M. et al. (2018). **A review of data mining using big data in health informatics**. JBHI. | Contexte big data santé |

#### Analyse de graphes — Détection de fraude en réseau

| Réf. | Papier | Pourquoi obligatoire |
|---|---|---|
| [Blondel2008] | Blondel, V. D. et al. (2008). **Fast unfolding of communities in large networks**. Journal of Statistical Mechanics. | Algorithme Louvain — justifie le choix pour NetworkX |
| [Savage2014] | Savage, D. et al. (2014). **Anomaly detection in online social networks**. Social Networks. | Détection anomalies graphes — contextualisation |
| [Jiang2014] | Jiang, C. et al. (2014). **Catchsync: catching synchronized behavior in large directed graphs**. KDD. | Fraude coordonnée — motivation brique graphe |

#### LLM et narration automatique

| Réf. | Papier | Pourquoi obligatoire |
|---|---|---|
| [Jiang2023] | Jiang, A. Q. et al. (2023). **Mistral 7B**. arXiv:2310.06825. | Papier officiel Mistral 7B — obligatoire |
| [Wei2022] | Wei, J. et al. (2022). **Chain-of-thought prompting elicits reasoning in large language models**. NeurIPS. | Justifie la stratégie de prompt engineering |
| [Guo2023] | Guo, T. (2023). **Large language models are human-level prompt engineers**. ICLR. | Fondement du prompt engineering RCA |

#### Architecture logicielle et frameworks ML

| Réf. | Papier | Pourquoi obligatoire |
|---|---|---|
| [Sculley2015] | Sculley, D. et al. (2015). **Hidden technical debt in machine learning systems**. NeurIPS. | Justifie l'architecture propre et modulaire |
| [Amershi2019] | Amershi, S. et al. (2019). **Software engineering for machine learning: a case study**. ICSE. | Pratiques ingénierie ML — justifie Plugin Contract |
| [Paleyes2022] | Paleyes, A. et al. (2022). **Challenges in deploying machine learning: a survey of case studies**. ACM Computing Surveys. | Déploiement ML — contexte applicatif |

#### Drift monitoring

| Réf. | Papier | Pourquoi obligatoire |
|---|---|---|
| [Gama2014] | Gama, J. et al. (2014). **A survey on concept drift adaptation**. ACM Computing Surveys. | Fondements drift monitoring |
| [Webb2016] | Webb, G. I. et al. (2016). **Characterizing concept drift**. Data Mining and Knowledge Discovery. | PSI et métriques drift — justifie le choix PSI |

### 3.3 Comment intégrer les citations dans le code

Chaque module et chaque brique du Kernel doit avoir en en-tête :

```python
"""
MODULE : core/detector.py
DESCRIPTION : Détection d'anomalies par Isolation Forest

RÉFÉRENCES ACADÉMIQUES :
- [Liu2008] Liu et al. (2008). Isolation Forest. ICDM 2008.
  → Algorithme principal. Complexité O(n log n), isolation par partitionnement aléatoire.
- [Goldstein2016] Goldstein & Uchida (2016). Comparative evaluation of
  unsupervised anomaly detection algorithms. PLOS ONE.
  → Justifie la sélection IF comme baseline sur données mixtes.

DÉCISIONS DE CONCEPTION :
- Contamination par défaut : 0.08 (8%) — justifié par la littérature sur la fraude
  en assurance santé (Bauder & Khoshgoftaar, 2017 : taux fraude estimé 3-10%)
- Comparaison formelle IF vs LOF vs One-Class SVM : voir ADR-006
"""
```

---

## 4. PROTOCOLE DE GÉNÉRALISATION ET MODULARITÉ

### 4.1 Principe — Séparation stricte des niveaux d'abstraction

Le code MAKORA respecte impérativement la hiérarchie suivante :

```
NIVEAU 0 — Interfaces abstraites (base_module.py)
    ↓ implémentées par
NIVEAU 1 — Modules métiers (sante_module.py, auto_module.py)
    ↓ orchestrés par
NIVEAU 2 — Kernel (pipeline.py, detector.py, explainer.py...)
    ↓ exposés par
NIVEAU 3 — API (FastAPI routers)
    ↓ consommés par
NIVEAU 4 — Frontend (Next.js)
```

**Règle d'or :** aucun import descendant. Le Kernel ne connaît jamais un module métier par son nom concret — seulement via `BaseModule`.

### 4.2 Critères de généralisation — checklist par composant

Avant de considérer un composant comme "générique", vérifier :

```
□ Le composant fonctionne-t-il sans connaître la branche d'assurance ?
□ Le comportement est-il entièrement configurable via le YAML du module ?
□ L'ajout d'un nouveau module nécessite-t-il de modifier ce composant ? (réponse attendue : NON)
□ Le composant a-t-il été testé avec au moins 2 modules différents ?
□ Les paramètres hardcodés ont-ils été externalisés en configuration ?
```

### 4.3 Renforcement de la modularité — améliorations à intégrer

Ces points vont au-delà de la conception Phase 0 et renforcent la contribution scientifique :

#### 4.3.1 Stratégie de détection pluggable

Au lieu d'Isolation Forest hardcodé dans `detector.py`, implémenter une interface `DetectorStrategy` :

```python
# core/detector_strategy.py
from abc import ABC, abstractmethod
import numpy as np

class DetectorStrategy(ABC):
    """
    Interface pour toute stratégie de détection d'anomalies.
    Pattern Strategy (GoF) — permet de swapper l'algorithme sans modifier le pipeline.
    Référence : Amershi et al. (2019) — Software Engineering for ML.
    """
    @abstractmethod
    def fit(self, X: np.ndarray) -> None: ...

    @abstractmethod
    def score(self, X: np.ndarray) -> np.ndarray: ...

    @abstractmethod
    def get_name(self) -> str: ...

class IsolationForestStrategy(DetectorStrategy):
    """[Liu2008] — Stratégie principale."""
    ...

class LOFStrategy(DetectorStrategy):
    """[Breunig2000] — Stratégie de comparaison."""
    ...
```

Avantage académique : permet la **comparaison formelle des algorithmes** (ADR-006) en swappant la stratégie, pas en réécrivant le pipeline.

#### 4.3.2 Registre de modules (Plugin Registry)

```python
# core/plugin_registry.py
class PluginRegistry:
    """
    Registre centralisé des modules MAKORA disponibles.
    Implémente le pattern Registry (Fowler, 2002).
    Permet la découverte dynamique des modules sans modification du Kernel.
    """
    _registry: dict[str, type[BaseModule]] = {}

    @classmethod
    def register(cls, branch: str):
        """Décorateur d'enregistrement."""
        def decorator(module_class):
            cls._registry[branch] = module_class
            return module_class
        return decorator

    @classmethod
    def get(cls, branch: str) -> BaseModule:
        if branch not in cls._registry:
            raise ModuleNotFoundError(f"No module registered for branch '{branch}'")
        return cls._registry[branch]()
```

Usage :
```python
@PluginRegistry.register("sante")
class SanteModule(BaseModule):
    ...
```

#### 4.3.3 Feature store par module

Chaque module déclare ses features dans le YAML **avec leur type, source et méthode de calcul** :

```yaml
features:
  - name: ratio_prix_mercuriale
    type: float
    source: computed          # computed | raw | external
    formula: "Montant_Facture / Prix_Reference_Mercuriale"
    null_strategy: median     # comment gérer les valeurs manquantes
    reference: "Mercuriale CIMA §4.2"   # ← référence réglementaire
    anomaly_direction: high   # high | low | both
    literature_basis: "Bauder & Khoshgoftaar (2017) — ratio comme feature discriminante"
```

Ce niveau de déclaration renforce la traçabilité scientifique de chaque feature.

---

## 5. PROTOCOLE DE DÉTECTION DES ANOMALIES — ANCRAGE DANS L'ÉTAT DE L'ART

### 5.1 Taxonomie des anomalies à respecter

La cartographie des anomalies de MAKORA doit être alignée avec la taxonomie académique standard :

| Type MAKORA | Correspondance littérature | Référence |
|---|---|---|
| Fraude Intentionnelle (Cat. I) | *Point anomaly* + *Contextual anomaly* | [Chandola2009] §3.1 |
| Erreurs Opérationnelles (Cat. II) | *Point anomaly* (non-intentionnel) | [Chandola2009] §3.1 |
| Biais Système (Cat. III) | *Collective anomaly* | [Chandola2009] §3.2 |
| Risques Techniques (Cat. IV) | *Concept drift* | [Gama2014] |

**Obligation :** le chapitre "Conception" du mémoire doit poser cette taxonomie avant d'introduire MAKORA.

### 5.2 Protocoles de détection réels en assurance — ce que l'état de l'art utilise

Pour renforcer la crédibilité du projet, MAKORA doit s'inscrire explicitement dans ces protocoles :

#### 5.2.1 Protocole SIU (Special Investigation Unit) — standard industrie

Les SIU sont les unités anti-fraude des compagnies d'assurance. Leur protocole de travail est :

1. **Screening automatique** — règles heuristiques simples (seuils, listes noires) → MAKORA y contribue via les règles YAML
2. **Scoring ML** — algorithme de détection d'anomalies → MAKORA : Isolation Forest
3. **Investigation humaine** — dossiers marqués examinés par un enquêteur → MAKORA : Human-in-the-loop + dashboard
4. **Décision et reporting** — validation, rejet, transmission aux autorités → MAKORA : Audit Logger

**Documenter explicitement que MAKORA couvre les étapes 2 et 3 de ce protocole.**

#### 5.2.2 Cycle de vie réel d'un sinistre — 7 étapes

```
[1] SOUSCRIPTION          → Vérification identité, cohérence du risque déclaré
       ↓
[2] GESTION DES PRIMES    → Prélèvements, suivi des impayés
       ↓
[3] DÉCLARATION           → Réception du sinistre (API NOEMIE / scan documentaire)
       ↓
[4] INSTRUCTION           → Vérification pièces, calcul remboursement
       ↓ ← POINT D'INJECTION MAKORA (détection principale)
[5] LIQUIDATION           → Validation du montant remboursable
       ↓ ← POINT D'INJECTION MAKORA (scoring final avant paiement)
[6] RÈGLEMENT             → Paiement de l'indemnité
       ↓
[7] CLÔTURE / RECOURS     → Archivage, contestations
```

**MAKORA intervient principalement en étapes 4 et 5.** Documenter cela précisément dans le mémoire avec référence aux protocoles ACFE.

#### 5.2.3 Les patterns de fraude réels en assurance santé (à couvrir)

Ces patterns sont documentés dans la littérature et doivent être adressés dans les règles YAML :

| Pattern | Description | Feature discriminante | Référence |
|---|---|---|---|
| **Upcoding** | Coder un acte plus cher que celui réalisé | `ratio_prix_mercuriale` élevé | [Bauder2017] |
| **Unbundling** | Décomposer un acte global en actes séparés | Nombre élevé d'actes par visite | [Bauder2017] |
| **Phantom billing** | Facturer des actes non réalisés | `is_weekend_care` + praticien suspect | [Bauder2017] |
| **Collusion réseau** | Assuré + prestataire complices | Degré du nœud dans le graphe | [Jiang2014] |
| **Identity theft** | Prêt ou vol de carte d'assuré | Géolocalisation incohérente | [Liu2015] |
| **Duplicate billing** | Facturer deux fois le même acte | Hash du dossier + timestamp | Standard SIU |

#### 5.2.4 Les patterns de fraude réels en assurance auto

| Pattern | Description | Feature discriminante | Référence |
|---|---|---|---|
| **Staging accidents** | Accident provoqué intentionnellement | Délai déclaration très court | [Viaene2002] |
| **Inflation des dégâts** | Gonfler le montant des réparations | `ratio_cout_reparation_valeur_vehicule` | [Viaene2002] |
| **Faux témoins** | Réseau de témoins liés | Graphe de cooccurrence | [Subudhi2017] |
| **Kilométrage frauduleux** | Déclarer un kilométrage anormal | `delta_kilometrage_annuel` | [Subudhi2017] |

---

## 6. PROTOCOLE D'ÉVALUATION SCIENTIFIQUE

### 6.1 Métriques obligatoires — non-négociables

Pour chaque module implémenté, les métriques suivantes DOIVENT être calculées et documentées :

```python
# Métriques principales
- Precision (Positive Predictive Value)
- Recall (Sensitivity / True Positive Rate)
- F1-score (harmonic mean)
- AUC-ROC (Area Under the ROC Curve)
- Average Precision (AP) — plus robuste que AUC sur données déséquilibrées
- False Positive Rate (FPR) — critique en contexte opérationnel

# Métriques secondaires
- Matthews Correlation Coefficient (MCC) — robuste aux classes déséquilibrées
- Contamination calibration error — écart entre contamination estimée et réelle
```

**Référence pour le choix des métriques :** Davis & Goadrich (2006). The relationship between Precision-Recall and ROC curves. ICML.

### 6.2 Protocole de validation expérimentale

```
1. SPLIT FIXE DES DONNÉES
   - Train : 70% (apprentissage du modèle)
   - Validation : 15% (tuning des hyperparamètres)
   - Test : 15% FIXE, JAMAIS TOUCHÉ jusqu'à l'évaluation finale
   - Seed fixé : random_state=42 (reproductibilité)

2. INJECTION DE LABELS (dataset non-supervisé → évaluation supervisée)
   - Utiliser CTGAN ou règles heuristiques pour injecter ~8% d'anomalies connues
   - Documenter la méthode d'injection dans DATASET_SANTE_GUIDE.md

3. CROSS-VALIDATION (si dataset suffisant)
   - StratifiedKFold(n_splits=5) pour préserver la distribution des anomalies

4. COMPARAISON FORMELLE (ADR-006)
   - Tester IF, LOF, One-Class SVM sur les mêmes splits
   - Tableau comparatif avec intervalles de confiance (bootstrap)

5. ANALYSE D'ERREUR QUALITATIVE
   - Examiner manuellement les 20 plus gros faux positifs
   - Examiner manuellement les 20 plus gros faux négatifs
   - Formuler des hypothèses sur les causes d'erreur
```

### 6.3 Preuve de généricité — protocole spécifique

**C'est l'expérience centrale du mémoire.** Elle doit être conduite avec soin.

```
HYPOTHÈSE NULL (H0) :
"Un modèle spécialisé (entraîné uniquement sur Santé) 
 n'est pas significativement plus précis qu'un modèle générique 
 MAKORA (entraîné sur Santé + Auto conjointement)."

PROTOCOLE :
1. Entraîner M_sante  : Isolation Forest sur dataset Santé uniquement
2. Entraîner M_auto   : Isolation Forest sur dataset Auto uniquement
3. Entraîner M_makora : MAKORA sur Santé + Auto (pipeline générique)
4. Évaluer les 3 modèles sur le test set Santé → comparer F1
5. Évaluer les 3 modèles sur le test set Auto → comparer F1
6. Calculer le delta de performance : Δ = F1(M_spécialisé) - F1(M_makora)
7. Interpréter : si Δ < 5%, la généricité ne coûte pas cher en précision

RÉSULTAT ATTENDU (hypothèse de travail) :
Δ ∈ [2%, 7%] — trade-off généricité/précision documenté et acceptable

RÉFÉRENCE : 
Le trade-off généricité/spécialisation est documenté dans :
Caruana, R. (1997). Multitask learning. Machine Learning, 28(1), 41-75.
```

---

## 7. PROTOCOLE DE DOCUMENTATION DU CONTEXTE AFRICAIN

### 7.1 Positionnement dans la littérature

Le gap académique sur la détection de fraude en assurance en Afrique subsaharienne est réel. Mais pour le documenter rigoureusement, il faut :

1. **Conduire une revue systématique** (même légère) : chercher sur Google Scholar, IEEE Xplore, ACM DL avec les termes "insurance fraud detection Africa", "anomaly detection insurance developing countries", "CIMA insurance fraud"
2. **Documenter l'absence** : "Nous avons identifié X papiers sur la fraude en assurance, dont Y traitent du contexte africain, dont Z utilisent des méthodes ML"
3. **Ne pas affirmer l'inexistence** : affirmer "aucun travail" est risqué. Affirmer "nous n'avons pas trouvé de travail traitant X" est défendable.

### 7.2 Ce qui doit être documenté sur le contexte camerounais

Pour que la contribution africaine soit réelle et non cosmétique :

```
À documenter dans MODULE_SANTE.md et MODULE_AUTO.md :

□ Différences structurelles entre nomenclature ASAC et CCAM
□ Impact du cachet humide sur la pipeline OCR (taux d'erreur, stratégies)
□ Spécificités de la Mercuriale CIMA vs SNDS français
□ Conversion EUR/XAF et son impact sur les features de prix
□ Taux de fraude documentaire estimé (scans altérés) — source ASAC si disponible
□ Différences dans les patterns de fraude (micro-assurance vs assurance classique)
```

---

## 8. OÙ PLACER CE FICHIER ET COMMENT L'UTILISER

### 8.1 Emplacement dans le projet

```
makora/
└── context/
    ├── MASTER_CONTEXT.md          ← À donner en premier à toute session IA
    ├── RESEARCH_PROTOCOL.md       ← CE FICHIER — à donner en second
    ├── ARCHITECTURE.md
    ├── ...
```

**Ce fichier se place dans `context/` au même niveau que `MASTER_CONTEXT.md`.**  
Il doit être référencé dans `MASTER_CONTEXT.md` dans la section "Fichiers contexte disponibles".

### 8.2 Quand le lire / le donner à une session IA

| Situation | Action |
|---|---|
| Début d'une nouvelle phase | Donner `MASTER_CONTEXT.md` + `RESEARCH_PROTOCOL.md` |
| Implémentation d'un nouveau composant | Rappeler la section 4 (modularité) et 3.3 (citations dans le code) |
| Rédaction d'un rapport de phase | Utiliser le template section 1.2 |
| Mise à jour des fichiers contexte | Suivre le protocole section 2 |
| Évaluation des métriques | Suivre le protocole section 6 |
| Rédaction du chapitre état de l'art | Utiliser les tableaux section 3.2 |

### 8.3 Ligne d'ajout dans MASTER_CONTEXT.md

Dans la section "Fichiers contexte disponibles" de `MASTER_CONTEXT.md`, ajouter :

```markdown
| `RESEARCH_PROTOCOL.md` | Protocole de rigueur scientifique, citations obligatoires, templates de phase | Toujours — surtout en début de phase et lors de la rédaction |
```

---

## 9. CHECKLIST GLOBALE — AVANT SOUTENANCE

Ces points doivent tous être vrais le jour de la soutenance :

```
□ Chaque algorithme utilisé est cité avec son papier original
□ Chaque décision architecturale a un ADR avec justification
□ La comparaison IF vs LOF vs One-Class SVM est documentée avec métriques
□ L'expérience de généricité (H0) a été conduite et le delta Δ est chiffré
□ Au moins 5 cas de faux positifs sont analysés qualitativement
□ Les limites du système sont documentées dans le rapport (pas cachées)
□ Le protocole SIU est mentionné et MAKORA est positionné dedans
□ Les patterns de fraude réels (upcoding, phantom billing...) sont couverts par les règles YAML
□ La contribution africaine est documentée avec des éléments concrets (pas juste affirmée)
□ Chaque PHASE_X_REPORT.md est rédigé et cohérent avec le code
□ Les fichiers contexte sont à jour (dernière mise à jour = fin Phase 4)
□ Un mode dégradé fonctionnel existe si Ollama tombe en soutenance
```

---

*Fin du document — RESEARCH_PROTOCOL.md v1.0*  
*Prochain révision : fin Phase 1 (après validation des premiers résultats expérimentaux)*  
*Document maintenu par : ATABONG EFON STEPHANE FRITZ*
