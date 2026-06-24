# MAKORA — Guide de configuration Claude par type de tâche
> Généré le 08 juin 2026 — Basé sur les modèles disponibles à cette date
> Projet : MAKORA — Framework générique de détection de fraude en assurance
> Responsable : ATABONG EFON STEPHANE FRITZ

---

## Contexte

Ce guide synthétise les recommandations de modèle et de niveau d'effort Claude
pour chaque type de tâche rencontré dans le projet MAKORA (Phase 2 terminée,
pipeline Kernel complet, prochaines étapes : validation expérimentale + rédaction mémoire).

### Rappel des modèles disponibles (juin 2026)

| Modèle | Analogie | Usage principal |
|---|---|---|
| **Haiku 4.5** | Stagiaire brillant | Rapide, économique, tâches simples et répétitives |
| **Sonnet 4.6** | Ingénieur senior | Meilleur rapport qualité/coût — cheval de bataille quotidien |
| **Opus 4.7** | Chercheur principal | Problèmes difficiles, nouvelles conceptions |
| **Opus 4.8** | Chercheur principal (+ honnêteté) | Mêmes cas que 4.7, + détection de bugs 4x améliorée |

### Rappel des niveaux d'effort (Opus 4.7 et 4.8 uniquement)

| Niveau | Description |
|---|---|
| **Low** | Réponse quasi-baseline, rapide et économique |
| **Medium** | Réflexion modérée — problèmes à quelques composantes |
| **High** | Défaut recommandé — knowledge work standard |
| **xhigh** | Raisonnement profond — problèmes complexes |
| **max** | Pensée maximale — réservé aux cas les plus exigeants |

> ⚠️ Sur Sonnet 4.6, le niveau d'effort n'est pas paramétrable — le modèle opère
> en mode "High" par défaut de manière implicite.

---

## Recommandations par type de tâche

---

### 🔵 Code backend classique (API FastAPI, routers, endpoints)

**Modèle :** Sonnet 4.6
**Effort :** High (défaut)

**Justification :**
Le code API est une tâche bien structurée et bien délimitée. Les endpoints MAKORA
sont définis dans `API_CONTRACTS.md` — il n'y a pas d'ambiguïté architecturale
à résoudre, seulement de l'implémentation propre.

Sonnet 4.6 livre 97-99% de la qualité d'Opus sur ce type de tâche à 40% du coût.

**Exemples concrets dans MAKORA :**
- Implémentation des routers `/api/v1/analyze`, `/api/v1/modules`
- Middleware d'authentification
- Schémas Pydantic des requêtes/réponses
- Gestionnaires d'erreurs HTTP

---

### 🔵 Code frontend (Next.js, composants UI)

**Modèle :** Sonnet 4.6
**Effort :** High (défaut)

**Justification :**
Même logique que le backend : tâche bien définie et structurée.
Sonnet 4.6 est excellent sur TypeScript/React/Next.js.

**Exemples concrets dans MAKORA :**
- Dashboard de visualisation des scores d'anomalie
- Composants de présentation des explications SHAP
- Interface de validation Human-in-the-Loop
- Tableaux de bord drift monitoring

---

### 🟠 Code ML — modification de composants Kernel existants

**Modèle :** Sonnet 4.6
**Effort :** High (défaut)

**Justification :**
Si l'architecture est déjà posée (`detector.py`, `explainer.py`, `pipeline.py`
tous marqués ✅ COMPLET), la modification reste guidée par le Plugin Contract.
Sonnet 4.6 est suffisant pour naviguer dans une structure bien définie.

**Exemples concrets dans MAKORA :**
- Ajout d'une stratégie LOF ou One-Class SVM dans `detector.py`
- Extension de `explainer.py` pour un nouveau type d'output SHAP
- Complétion du stub `audit_logger.py`
- Amélioration du `drift_monitor.py`

---

### 🟠 Code ML — nouvelle brique Kernel (conception + implémentation)

**Modèle :** Opus 4.7 ou Opus 4.8
**Effort :** High

**Justification :**
Quand tu conçois une brique inexistante, le risque architectural est élevé.
Un mauvais choix peut violer le Plugin Contract ou introduire un couplage
Kernel/Module. Opus 4.7/4.8 détecte ces problèmes là où Sonnet peut les laisser passer.

**Exemples concrets dans MAKORA :**
- Implémentation du module agricole (Phase 3 prévue)
- Nouvelle brique OCR multimodale
- Extension du `graph_engine.py` pour les réseaux bipartis

---

### 🔴 Tests unitaires et vérification de cohérence Kernel/Module

**Modèle :** Opus 4.8
**Effort :** High → xhigh

**Justification :**
Opus 4.8 est 4x moins susceptible de laisser passer une faille de code sans
la signaler. Pour les tests qui vérifient que `BaseModule` n'est jamais bypassé,
que le Kernel n'importe jamais un module métier par son nom concret, et que
les métriques (Precision, Recall, F1, AUC-ROC, MCC, FPR) sont toutes calculées —
l'honnêteté du modèle est critique.

**Exemples concrets dans MAKORA :**
- Tests de non-régression du Plugin Contract
- Tests de généricité (le pipeline fonctionne sans connaître la branche)
- Tests des métriques d'évaluation (protocole 70/15/15, seed=42)
- Tests de l'expérience centrale H0 (M_sante vs M_auto vs M_makora)

---

### 🔴 Réflexion et conception (nouveaux ADR, choix algorithmiques)

**Modèle :** Opus 4.8
**Effort :** xhigh

**Justification :**
C'est exactement le cas d'usage pour lequel la réflexion profonde a été conçue.
Quand tu dois choisir entre Isolation Forest, LOF et One-Class SVM, justifier
une décision d'architecture, ou évaluer si un nouveau pattern de fraude est
couvrable par le Kernel actuel — tu as besoin de raisonnement profond, pas de
rapidité.

**Exemples concrets dans MAKORA :**
- Rédaction d'un nouvel ADR (Architecture Decision Record)
- Choix du modèle de drift monitoring (PSI vs KS test vs ADWIN)
- Évaluation de la contribution africaine (ASAC vs CCAM, impact XAF sur les features)
- Protocole de validation de l'hypothèse H0

---

### 🟡 Planification de travail (sessions, phases, roadmap)

**Modèle :** Sonnet 4.6
**Effort :** High (défaut)

**Justification :**
La planification demande de la cohérence avec tout le contexte du projet,
mais pas de raisonnement profond. Sonnet 4.6 avec le system prompt MAKORA
chargé est suffisant pour générer un plan de session, une checklist de phase,
ou une roadmap de sprint.

**Exemples concrets dans MAKORA :**
- Plan de la session de travail du jour
- Checklist pré-PHASE_X_REPORT.md
- Organisation des tâches restantes (Phase 3 et 4)
- Priorisation de la dette technique identifiée

---

### 🔴 Rédaction du mémoire (chapitres, sections scientifiques)

**Modèle :** Opus 4.8
**Effort :** xhigh → max

**Justification :**
C'est la tâche la plus exigeante intellectuellement de tout le projet.
Tu as besoin que le modèle :
- Comprenne les nuances entre [Liu2008] et [Chandola2009]
- Construise une argumentation cohérente et non circulaire
- Cite honnêtement les limites sans les minimiser
- Sache dire "nous n'avons pas trouvé de travaux africains sur ce point"
  plutôt qu'inventer des références

Opus 4.8 "signale correctement quand les données manquent au lieu de fournir
des conclusions plausibles mais incorrectes" — qualité indispensable pour un mémoire.

**Exemples concrets dans MAKORA :**
- Chapitre 2 — État de l'art (détection d'anomalies, fraude assurance, XAI)
- Chapitre 3 — Contribution africaine (ASAC, CIMA, XAF, contexte camerounais)
- Chapitre 4 — Architecture et conception (à partir des diagrammes UML)
- Chapitre 5 — Résultats expérimentaux (tableaux comparatifs IF/LOF/OCSVM)
- Analyse qualitative des faux positifs / faux négatifs

---

## Tableau récapitulatif

| Tâche | Modèle | Effort | Raison principale |
|---|---|---|---|
| API FastAPI / routers | Sonnet 4.6 | High (défaut) | Tâche bien définie, excellent rapport coût/perf |
| Frontend Next.js | Sonnet 4.6 | High (défaut) | Idem |
| Code ML — Kernel existant | Sonnet 4.6 | High | Architecture déjà posée et documentée |
| Code ML — Nouvelle brique | Opus 4.7/4.8 | High | Risque architectural élevé |
| Tests & vérification Kernel | Opus 4.8 | High → xhigh | Honnêteté critique sur les violations du Contract |
| Conception / ADR | Opus 4.8 | xhigh | Raisonnement profond nécessaire |
| Planification | Sonnet 4.6 | High | Cohérence contexte, pas de profondeur requise |
| Rédaction mémoire | Opus 4.8 | xhigh → max | Rigueur scientifique, honnêteté des citations |

---

## Conseil pratique

Dans claude.ai, le sélecteur de modèle et le curseur d'effort sont visibles
dans la barre latérale. Tu peux switcher en cours de session selon la tâche du moment,
sans changer de conversation ni recharger le contexte.

**Règle empirique simple :**
> Si la tâche a une bonne réponse évidente → Sonnet 4.6
> Si la tâche implique un jugement architectural ou scientifique → Opus 4.8 xhigh

---

*Document généré le 08 juin 2026*
*Projet MAKORA — ATABONG EFON STEPHANE FRITZ*
*À mettre à jour si de nouveaux modèles sont publiés*
