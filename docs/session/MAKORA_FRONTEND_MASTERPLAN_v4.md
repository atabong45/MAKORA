# MAKORA — Plan Maître de Réalisation Frontend

> **Version :** 4.0 — 10 juin 2026
> **Statut :** Phases 1–4.5 ✅ · Phase 5 à démarrer
> **Auteur :** ATABONG EFON STEPHANE FRITZ
> **Projet :** `insurance-claim-audit-portal` — Next.js 14 App Router

---

## ═══════════════════════════════════════════════

## PARTIE A — PROMPT SYSTÈME POUR L'IA QUI CONTINUE

## ═══════════════════════════════════════════════

> **Ce bloc est conçu pour être collé en début de conversation dans une nouvelle session.**
> Il contient toutes les consignes, toute la philosophie, et l'état exact du projet.

```
TU CONTINUES LE DÉVELOPPEMENT DU FRONTEND DU PROJET MAKORA.

══════════════════════════════════════════════════
1. QU'EST-CE QUE MAKORA ?
══════════════════════════════════════════════════

MAKORA est un framework de détection de fraude en assurance (Santé + Auto)
dans le contexte camerounais. Ce n'est PAS un simple projet web — c'est
une thèse de mémoire dont le frontend est la preuve empirique de l'ensemble
du travail. L'application tourne en local sur l'ordinateur de l'étudiant
le jour de la soutenance.

Stack backend : FastAPI · PostgreSQL · Isolation Forest · SHAP · Qwen LLM (Ollama)
Stack frontend : Next.js 14 (App Router) · TypeScript · Shadcn/ui · Tailwind CSS
                 TanStack Query v5 · Zustand · React Hook Form + Zod · Axios · Sonner · D3.js

Rôles RBAC : Gestionnaire (G) · Auditeur (A) · Expert Métier (E) · Administrateur (ADM)
Monnaie : XAF (FCFA). Nomenclature médicale : ASAC (pas CCAM). Mercuriale : CIMA.

══════════════════════════════════════════════════
2. PHILOSOPHIE FONDAMENTALE — LES TROIS SOURCES
══════════════════════════════════════════════════

Pour implémenter chaque page ou composant, tu dois OBLIGATOIREMENT croiser
TROIS sources d'information simultanément. Ne jamais utiliser l'une sans
les deux autres.

SOURCE 1 — Les fichiers doc_frontend/ (Markdown)
  → C'est la SPÉCIFICATION UX. Elle dit :
    - Quoi afficher sur chaque page
    - Pour quel rôle
    - Quel endpoint API appeler
    - Quel workflow métier supporter
    - Quelles contraintes UX respecter (fil d'Ariane, cycle de vie, RBAC, etc.)
  Fichiers : MAKORA_CONCEPTION_MACRO.md, MAKORA_MODULE_DASHBOARD.md,
             MAKORA_MODULE_SINISTRES.md, MAKORA_MODULE_AUDIT.md,
             MAKORA_MODULE_FRAUDE.md, MAKORA_MODULE_ML.md,
             MAKORA_MODULE_CONFIGURATION.md, MAKORA_MODULE_RAPPORTS_ADMIN.md,
             MAKORA_API_ENDPOINTS_COMPLET_v2.md

SOURCE 2 — Le mock frontend (project_frontend_mock.txt)
  → C'est l'INSPIRATION VISUELLE ET INTERACTIVE. Il apporte :
    - Les animations (toasts temps réel, spinners, transitions de page)
    - Les patterns de charts Recharts (barres comparatives, jauge arc SVG, etc.)
    - Le graphe D3 force-directed avec nodes colorés par communauté
    - Les micro-interactions (hover states, boutons avec états loading/disabled)
    - Le pattern "Mode Présentation" (flèches directionnelles)
    - La densité d'information dans les tableaux
    - Les états empty/loading/error avec illustrations
  MAIS : ne pas copier son thème sombre slate-900 ni ses données hardcodées.

SOURCE 3 — Le frontend existant (project_frontend.txt)
  → C'est l'ARCHITECTURE À CONSERVER. Il fournit :
    - Les services API déjà typés (auth.service.ts, audit.service.ts, etc.)
    - Les hooks TanStack Query existants
    - Les stores Zustand (authStore, branchStore, uiStore, notificationStore)
    - Les types TypeScript et validateurs Zod
    - L'infrastructure RBAC (middleware, PermissionGuard, lib/rbac.ts)
    - La structure de dossiers (components/common, components/features, hooks/, etc.)

RÈGLE D'OR DE CROISEMENT :
  Le Markdown dit "afficher les lignes de sinistre avec les montants et
  l'écart mercuriale". Le mock montre comment faire un tableau dense avec
  badges colorés et hover. Le frontend existant a déjà un ClaimLinesTable
  stub. → Tu combines les trois pour produire quelque chose qui a la
  richesse UX du Markdown, la beauté visuelle du mock, et qui s'intègre
  dans l'architecture existante.

══════════════════════════════════════════════════
3. LE PROBLÈME CENTRAL QU'ON RÉSOUT
══════════════════════════════════════════════════

AVANT nos sessions :
  - Le projet existant avait une architecture solide MAIS zéro UX :
    pages sombres en slate-900/950, données hardcodées, pas de design
    system, pas de Shadcn, apiClient non câblé, pas de react-hook-form.

  - Le mock avait de beaux effets visuels MAIS zéro UX fonctionnelle :
    données simulées, pas de vrai API, pages isolées sans workflow.

  - Les Markdowns avaient une UX pensée et structurée MAIS pas de rendu
    visuel ni de code.

CE QU'ON FAIT : prendre la rigueur UX des Markdowns + la beauté visuelle
du mock + l'architecture du projet existant. Pas de copier-coller d'aucune
source. Synthèse des trois.

══════════════════════════════════════════════════
4. PRINCIPES UX NON-NÉGOCIABLES (depuis MAKORA_CONCEPTION_MACRO.md)
══════════════════════════════════════════════════

PRINCIPE 1 — Contexte toujours visible
  La branche active (Santé / Auto) est affichée EN PERMANENCE : dans la
  sidebar (BranchSelector), dans chaque PageHeader des modules sinistres/
  audit, dans chaque badge BranchPill sur les lignes de tableau.
  Un gestionnaire ne doit jamais se demander "sur quelle branche je suis ?"

PRINCIPE 2 — Score = couleur = urgence (UNIFORME sur toutes les pages)
  score < 0.6   → vert  (bg-green-50, text-green-700)   "Sain"
  0.6 ≤ s < 0.8 → orange (bg-amber-50, text-amber-700) "Suspect"
  score ≥ 0.8   → rouge  (bg-red-50, text-red-700)     "Frauduleux"
  Ces couleurs s'appliquent sur : badges, jauges, lignes de tableau,
  cartes KPI, toasts d'alerte. JAMAIS de code couleur différent ailleurs.

PRINCIPE 3 — Zéro clic orphelin
  Tout bouton qui déclenche une action asynchrone doit avoir :
  - Un état loading (spinner + texte "En cours…" + disabled)
  - Un toast sonner au succès (toast.success) et à l'erreur (toast.error)
  - Un état disabled pendant le chargement
  JAMAIS un bouton qui "disparaît" ou reste cliquable sans feedback.

PRINCIPE 4 — Fil d'Ariane métier
  Chaque page utilise <PageHeader> avec des breadcrumbs qui reflètent
  le contexte métier, pas juste l'URL.
  Ex: "Sinistres > SIN-2026-CM-01847 > Documents & OCR"
  Ex: "Audit > Analyse 4821 > SHAP Explorer"
  Le gestionnaire sait toujours OÙ il est et dans quel contexte.

PRINCIPE 5 — Explication avant décision (CRITIQUE pour l'audit HITL)
  Sur la page /audit/[analysis_id], les boutons CONFIRMER / REJETER /
  ESCALADER ne doivent être rendus actifs (non-disabled) que lorsque
  trois éléments sont chargés et visibles :
  1. Le score IF + jauge AnalysisScoreGauge
  2. Les top 3 features SHAP
  3. La catégorie RCA principale
  C'est une règle UX stricte, pas une suggestion.

PRINCIPE 6 — Adaptation par rôle (RBAC visuel, pas seulement technique)
  Le RBAC ne signifie pas seulement "cacher des routes". Il signifie adapter
  l'interface :
  - Un Gestionnaire voit "Mes sinistres" (filtrés sur son portefeuille)
  - Un Auditeur voit "File d'audit" en priorité dans son dashboard
  - Un Expert voit les widgets Drift + Modèles dans son dashboard
  - Un Admin voit tout, y compris les panneaux de gouvernance
  Les widgets du dashboard changent selon le rôle — voir MAKORA_MODULE_DASHBOARD.md.

PRINCIPE 7 — Empty states guidants (inspiré du mock)
  Quand une section est vide, afficher un <EmptyState> avec UNE action
  concrète :
  - /claims vide → "Aucun sinistre. [+ Créer un sinistre]"
  - /audit vide → "Aucune analyse en attente. Soumettez un sinistre."
  - /ml/drift stable → "✓ Toutes les branches sont stables."
  Jamais un état vide sans indication de ce qu'on peut faire.

PRINCIPE 8 — Toasts temps réel (inspiré du mock)
  Le mock a un système de toasts automatiques qui simule des détections
  en temps réel. Dans le vrai projet, ce pattern doit exister via polling
  ou WebSocket (selon disponibilité backend). À activer uniquement pour
  les rôles G et A. Utiliser sonner (toast.info) pour les notifications
  non-critiques, toast.warning pour les anomalies détectées.

══════════════════════════════════════════════════
5. DESIGN TOKENS MAKORA (déjà installés en Phase 1)
══════════════════════════════════════════════════

Couleurs (variables CSS dans globals.css) :
  --color-navy:   #1B3C6E  → Sidebar, boutons primaires
  --color-gold:   #F0A500  → Logo, items actifs nav, CTA accent
  --color-page:   #F8F9FA  → Fond de page
  --color-card:   #FFFFFF  → Fond des cartes
  --color-border: #E9ECEF  → Bordures, séparateurs

Polices (next/font déjà configuré dans root layout.tsx) :
  font-sans     : IBM Plex Sans    (corps, labels, tableaux, formulaires)
  font-display  : DM Serif Display (titres H1 de page uniquement)
  font-mono     : IBM Plex Mono    (IDs sinistres, scores IF, montants XAF)

Format monnaie : TOUJOURS formatXAF(montant) depuis lib/utils.ts
                 → "125 000 FCFA" (jamais EUR ni "F CFA" ni "XAF")
Format date    : formatDate(isoString) → "14/11/2025"

PSI Drift :
  PSI < 0.10  → stable  (vert)
  PSI 0.10–0.20 → warning (orange)
  PSI > 0.20  → critical (rouge)

══════════════════════════════════════════════════
6. RÈGLES DE CODE ABSOLUES
══════════════════════════════════════════════════

CONTRAINTE LIGNE : Aucun fichier > 400 lignes. Découper si nécessaire.
FETCH             : Jamais de fetch() ou axios direct dans une page/composant.
                   Toujours via hook TanStack Query.
FORMULAIRES       : react-hook-form + zod. Toujours valider côté client avant API.
TOASTS            : sonner exclusivement. toast.success / toast.error / toast.warning / toast.info
COMPOSANTS        : Shadcn/ui en premier. Composant custom seulement si Shadcn ne couvre pas.
LOGIQUE MÉTIER    : Jamais dans un composant visuel. → lib/utils.ts ou hooks.
TYPES             : TypeScript strict. Zéro `any` sans commentaire justificatif.
QUERY KEYS        : Centralisées dans [domain].keys.ts par domaine.
CONVENTIONS       : Pages: page.tsx | Composants: PascalCase | Hooks: camelCase
                   Services: camelCase | Validators: *.validators.ts
APOSTROPHES JSX   : Écrire &apos; ou {"texte"} — jamais d'apostrophe typographique nue.
CONTEXTE CM       : Codes ASAC (pas CCAM), mercuriale CIMA, XAF, régions Cameroun.

PLUGIN PATTERN FRONTEND (introduit en Phase 4.5b — INVIOLABLE) :
  Aucun composant hors de src/modules/ ne doit référencer les branches
  "sante" ou "auto" par leur nom littéral. Toute logique branche-spécifique
  passe par getModule(branch) depuis src/modules/registry.ts.
```

---

## 1. ÉTAT ACTUEL — CE QUI EST LIVRÉ

| Phase       | Contenu                                                              | Fichiers | Statut |
| ----------- | -------------------------------------------------------------------- | -------- | ------ |
| **Phase 1** | Design System · AppShell · Sidebar · Navbar · utils                  | 17       | ✅     |
| **Phase 2** | Auth · apiClient · login · forgot · reset                            | 5        | ✅     |
| **Phase 3** | DataTable · KpiCard · Badges · Gauge · DashboardOverview             | 8        | ✅     |
| **Phase 4** | Module Sinistres complet (7 pages · 9 composants)                    | ~30      | ✅     |
| **Phase 4.5** | Contexte branche global + Plugin Pattern frontend (22 fichiers)    | 22       | ✅     |
| **Total livré** |                                                                  | **~82**  |        |

---

## 2. RÈGLES DE CODE — RAPPEL ABSOLU

```
MAX 400 lignes par fichier — découper si nécessaire
FETCH : jamais direct → toujours via hook TanStack Query
FORMS : react-hook-form + zod, valider côté client avant API
TOASTS : sonner uniquement (toast.success / error / warning / info)
UI : Shadcn/ui en premier, custom seulement si Shadcn ne couvre pas
TYPES : TypeScript strict, zéro `any` sans justification
KEYS : centralisées dans [domain].keys.ts
MONNAIE : formatXAF() — jamais "EUR" ni "XAF" ni "F CFA"
RBAC : PermissionGuard, jamais logique branchée sur rôle dans le DOM
CONTEXTE CM : codes ASAC, mercuriale CIMA, XAF, régions Cameroun
PLUGIN PATTERN : getModule(branch) — jamais de comparaison "sante"/"auto" hors src/modules/
```

---

## 3. PHASE 4 — MODULE SINISTRES ✅

**Référence spec :** `MAKORA_MODULE_SINISTRES.md`
**Statut :** Terminée · typecheck OK · smoke tests validés

### Pages livrées

| Route                    | Statut |
| ------------------------ | ------ |
| `/claims`                | ✅     |
| `/claims/new`            | ✅     |
| `/claims/[id]`           | ✅     |
| `/claims/[id]/edit`      | ✅     |
| `/claims/[id]/documents` | ✅     |
| `/claims/[id]/lines`     | ✅     |
| `/claims/analyses`       | ✅     |

---

## 3bis. PHASE 4.5 — CONTEXTE DE BRANCHE + ARCHITECTURE MODULAIRE ✅

> **Statut :** ✅ Terminée — 10 juin 2026
> **Métriques de clôture :** `npx tsc --noEmit` → 0 erreur · ratio généricité = **95 %** (cible ≥ 90 %)
> **Référence spec :** `MAKORA_FRONTEND_MASTERPLAN_PHASE_4_5.md`
> **Rapport 4.5a :** `PHASE_4_5a_REPORT.md` · **Rapport 4.5b :** `PHASE_4_5b_REPORT.md`

### Contexte

La Phase 4 livrait une application multi-branche fonctionnelle mais avec deux incohérences structurelles : le `BranchSelector` global n'était pas écouté par toutes les pages, et les composants génériques contenaient des `if (branch === 'sante')` — exactement ce que le Plugin Pattern backend interdit côté Kernel. La Phase 4.5 traite les deux.

### 4.5a — Contexte de branche actif ✅

Le `BranchSelector` est devenu la source de vérité unique. Quand une branche est sélectionnée, l'application entière bascule en mode contextuel : listes filtrées, colonnes "Branche" masquées, formulaires pré-remplis et verrouillés, sous-titre discret sur les sinistres cross-contexte.

**Fichiers livrés :**

| Fichier | Action |
|---|---|
| `src/hooks/common/useActiveBranchFilter.ts` | CRÉER — hook centralisé |
| `src/app/(app)/claims/page.tsx` | REFACTOR — câblage contexte |
| `src/components/features/claims/ClaimFilters.tsx` | Prop `branchLocked` |
| `src/components/features/claims/ClaimsTable.tsx` | Prop `hideBranchColumn` |
| `src/app/(app)/claims/new/page.tsx` | Props `initialBranch` |
| `src/components/features/claims/ClaimForm.tsx` | Props `initialBranch` + `lockBranch` |
| `src/components/features/claims/ClaimFormStep1.tsx` | CRÉER — extrait de ClaimForm |
| `src/app/(app)/claims/analyses/page.tsx` | Suppression filtre local |
| `src/app/(app)/claims/[id]/page.tsx` | Sous-titre cross-contexte |

### 4.5b — Plugin Pattern frontend ✅

Aucun composant hors de `src/modules/` ne référence plus les branches par leur nom. L'architecture `src/modules/` réplique au frontend le même Plugin Pattern que le Kernel backend Python.

**Architecture déployée :**

```
src/modules/
├── types.ts          ← Interface BranchModule (pillStyle, lineItemsLabel, lineDescription…)
├── registry.ts       ← getModule() · listModules() · isKnownBranch()
├── sante/
│   ├── sante.module.tsx     ← Assemblage + claimLineSanteSchema
│   ├── SanteLineFields.tsx  ← Champs ASAC + praticien_id_hash
│   └── SanteOcrIndicators.tsx
└── auto/
    ├── auto.module.tsx      ← Assemblage + claimLineAutoSchema
    ├── AutoLineFields.tsx   ← Champs libellé poste + garage_id_hash
    └── AutoOcrIndicators.tsx
```

**Composants génériques refactorés :** `ClaimLineEditor`, `OcrResultCard`, `ClaimLinesTable`, `ClaimFormStep1`, `BranchPill`.

**Corrections techniques notables :**
- Modules renommés `.ts → .tsx` (JSX dans `extraLineColumns.render`)
- `getClaimLineSchema` typé `z.ZodType<ClaimLineInput, ClaimLineInput>` pour aligner zodResolver v5 (Zod 4 / @hookform/resolvers 5)
- `source_flux` ajouté au `claimCreateSchema` ; `.default()` retirés (input ≠ output cassait zodResolver)
- `AutoOcrIndicators.tsx` créé (indicateur auto : cachet neutre, focus retouche photo)

**Argument mémoire :**
- *"Le Plugin Pattern du Kernel Python se propage jusqu'à la couche présentation. 95 % du code frontend est branche-agnostique (mesuré par `scripts/count-module-loc.sh`). L'ajout d'une branche 'Vie' ne nécessite que la création d'un dossier `src/modules/vie/` — aucun composant existant à modifier."*

### Smoke tests Phase 4.5 (à valider visuellement)

| # | Scénario | Attendu |
|---|---|---|
| S1 | BranchSelector → Santé, aller sur `/claims` | Liste filtrée Santé, colonne Branche masquée, titre "Sinistres · Santé" |
| S2 | BranchSelector → Auto, aller sur `/claims/new` | Wizard ouvert sur Auto, champ branche verrouillé |
| S3 | Créer sinistre Santé, ajouter ligne | Label "Code ASAC" affiché (depuis module), validation bloque si vide |
| S4 | Créer sinistre Auto, ajouter ligne | Label "Libellé poste" affiché (depuis module Auto) |
| S5 | OCR sur sinistre Santé | Bloc "Lecture Santé" fond navy, alerte cachet absent |
| S6 | OCR sur sinistre Auto | Bloc "Lecture Auto" fond gold, cachet absent = neutre |
| S7 | Contexte Auto, ouvrir sinistre Santé | Bandeau ambre cross-contexte via `getModule().meta.displayName` |

---

## 4. PHASE 5 — AUDIT HITL + ESCALADES 🟠

**Référence spec :** `MAKORA_MODULE_AUDIT.md`
**Inspiration visuelle :** mock `AnomalyDetail.tsx` (decision panel + SHAP bars)
**Note Phase 4.5 :** `DecisionPanel` consommera `branchModule.fraudPatterns` depuis la registry — aucune modification de `src/modules/` nécessaire.

### Pages à créer

| Route                       | Description                                             | Rôles       |
| --------------------------- | ------------------------------------------------------- | ----------- |
| `/audit`                    | File d'audit — analyses PENDING                         | A · ADM     |
| `/audit/[analysis_id]`      | Page de décision HITL (CONFIRMER / REJETER / ESCALADER) | A · ADM     |
| `/audit/[analysis_id]/shap` | Explorateur SHAP (features détaillées)                  | A · E · ADM |
| `/escalations`              | File escalades                                          | A · ADM     |
| `/escalations/[id]`         | Détail escalade + résolution                            | A · ADM     |

### Composants à créer

| Composant        | Chemin                              | Notes                                  |
| ---------------- | ----------------------------------- | -------------------------------------- |
| `AuditQueue`     | `features/audit/AuditQueue.tsx`     | DataTable filtrable par branche/score  |
| `DecisionPanel`  | `features/audit/DecisionPanel.tsx`  | **CRITIQUE** — voir Principe 5         |
| `ShapChart`      | `features/audit/ShapChart.tsx`      | Barres bicolores rouge/vert triées abs |
| `RcaSummary`     | `features/audit/RcaSummary.tsx`     | Catégorie + texte LLM                  |
| `EscalationCard` | `features/audit/EscalationCard.tsx` | Statut + priorité + assignation        |
| `audit.keys.ts`  | `hooks/audit/audit.keys.ts`         |                                        |

### ⚠️ RÈGLE PRINCIPE 5 — DecisionPanel (INVIOLABLE)

Les boutons CONFIRMER / REJETER / ESCALADER restent **disabled** tant que les 3 éléments suivants ne sont pas tous chargés ET visibles :

1. Score IF + jauge `AnalysisScoreGauge`
2. Top 3 features SHAP (`ShapChart`)
3. Catégorie RCA principale (`RcaSummary`)

### Endpoints consommés

```
GET /api/v1/analyses → file d'audit (PENDING)
GET /api/v1/analyses/{id} → détail analyse
POST /api/v1/analyses/{id}/decision → décision (CONFIRM/REJECT/ESCALATE)
GET /api/v1/analyses/{id}/shap → features SHAP
GET /api/v1/analyses/{id}/rca → résultat RCA
GET /api/v1/escalations → liste escalades
GET /api/v1/escalations/{id} → détail
PATCH /api/v1/escalations/{id} → mise à jour statut
```

**Estimation : ~6 fichiers · ~1 400 lignes**

---

## 5. PHASE 6 — GRAPHE FRAUDE + ANALYTICS 🟠

**Référence spec :** `MAKORA_MODULE_FRAUDE.md`
**Inspiration visuelle :** mock `NetworkGraph.tsx` (D3 force-directed déjà implémenté)

### Pages à créer

| Route                         | Description                                    | Rôles       |
| ----------------------------- | ---------------------------------------------- | ----------- |
| `/fraud/graph`                | Graphe de communautés D3 (3 panneaux)          | A · ADM     |
| `/fraud/graph/[community_id]` | Détail communauté (membres + score suspicion)  | A · ADM     |
| `/fraud/analytics`            | Analytics SHAP globales (heatmap + importance) | A · E · ADM |
| `/fraud/rca`                  | Distribution RCA par type de fraude            | A · ADM     |

### Composants à créer

| Composant         | Chemin                               | Notes                                  |
| ----------------- | ------------------------------------ | -------------------------------------- |
| `NetworkGraph`    | `features/fraud/NetworkGraph.tsx`    | D3 force-directed — reskin thème clair |
| `CommunityList`   | `features/fraud/CommunityList.tsx`   | Panneau gauche — liste filtrée         |
| `NodeDetailPanel` | `features/fraud/NodeDetailPanel.tsx` | Panneau droit — détail sélection       |
| `ShapHeatmap`     | `features/fraud/ShapHeatmap.tsx`     | Recharts ou D3                         |
| `RcaDistribution` | `features/fraud/RcaDistribution.tsx` | Recharts PieChart ou BarChart          |

### Spécificités D3 NetworkGraph

- Nœuds : assuré = bleu · praticien = or · garage = vert
- Arêtes : épaisseur ∝ nombre de sinistres liés
- Hubs centraux (`is_central=true`) : plus grands, halo discret
- Interactions : zoom, pan, sélection nœud, sélection communauté
- Perf : charger initialement uniquement `is_suspicious=true`

### Endpoints consommés

```
GET /api/v1/graph/communities
GET /api/v1/graph/communities/{id}
GET /api/v1/graph/communities/{id}/members
GET /api/v1/analytics/shap/global
GET /api/v1/analytics/rca/distribution
```

**Estimation : ~5 fichiers · ~1 200 lignes**

---

## 6. PHASE 7 — GOUVERNANCE ML 🟠

**Référence spec :** `MAKORA_MODULE_ML.md`
**Note :** La page `/ml/models/compare` est la preuve empirique de H0 — traiter en priorité.

### Pages à créer

| Route                   | Description                                        | Rôles   |
| ----------------------- | -------------------------------------------------- | ------- |
| `/ml/models`            | Liste modèles déployés (IF/LOF/OC-SVM par branche) | E · ADM |
| `/ml/models/[model_id]` | Détail modèle (métriques + courbes ROC/PR)         | E · ADM |
| `/ml/models/compare`    | **Tableau H0** — comparaison IF vs LOF vs OC-SVM   | E · ADM |
| `/ml/drift`             | Dashboard drift toutes branches                    | E · ADM |
| `/ml/drift/[branch]`    | Détail drift par branche (PSI par feature)         | E · ADM |
| `/ml/retraining`        | Historique + déclenchement réentraînement          | ADM     |

### ⚠️ Page `/ml/models/compare` — CRITIQUE MÉMOIRE

Doit afficher :

- Sélecteur de modèles à comparer (multiselect)
- Tableau comparatif `M_sante | M_auto | M_makora` avec F1 · AUC · MCC · 1-FPR · AP et **Δ vs spécialisé** en dernière ligne
- Graphique radar (Recharts RadarChart) — 5 axes
- Badge coloré si Δ ∈ [2%, 7%] → `H0 VALIDÉE ✓` en vert

### Composants à créer

| Composant            | Chemin                               |
| -------------------- | ------------------------------------ |
| `ModelCard`          | `features/ml/ModelCard.tsx`          |
| `ModelMetricsPanel`  | `features/ml/ModelMetricsPanel.tsx`  |
| `ModelCompareTable`  | `features/ml/ModelCompareTable.tsx`  |
| `H0ValidatorBadge`   | `features/ml/H0ValidatorBadge.tsx`   |
| `DriftStatusGrid`    | `features/ml/DriftStatusGrid.tsx`    |
| `DriftFeatureTable`  | `features/ml/DriftFeatureTable.tsx`  |
| `RetrainingTimeline` | `features/ml/RetrainingTimeline.tsx` |

### Endpoints consommés

```
GET /api/v1/models
GET /api/v1/models/{id}
GET /api/v1/models/deployments
GET /api/v1/analytics/models/performance → données pour /compare
GET /api/v1/drift/status
GET /api/v1/drift/{branch}
POST /api/v1/drift/run/{branch}
GET /api/v1/retraining/history
POST /api/v1/retraining/trigger
```

**Estimation : ~7 fichiers · ~1 600 lignes**

---

## 7. PHASE 8 — CONFIGURATION 🟠

**Référence spec :** `MAKORA_MODULE_CONFIGURATION.md`

### Pages à créer

| Route                  | Description                              | Rôles   |
| ---------------------- | ---------------------------------------- | ------- |
| `/config/modules`      | Modules plugin enregistrés + YAML config | E · ADM |
| `/config/referentiels` | Nomenclatures ASAC + tarifs CIMA         | ADM     |
| `/config/mercuriale`   | Barèmes mercuriale (édition lignes)      | ADM     |

### Composants à créer

| Composant          | Chemin                                 |
| ------------------ | -------------------------------------- |
| `PluginModuleCard` | `features/config/PluginModuleCard.tsx` |
| `YamlEditor`       | `features/config/YamlEditor.tsx`       |
| `ReferentielTable` | `features/config/ReferentielTable.tsx` |
| `MercurialeEditor` | `features/config/MercurialeEditor.tsx` |

**Estimation : ~4 fichiers · ~900 lignes**

---

## 8. PHASE 9 — RAPPORTS + ADMINISTRATION 🟠

**Référence spec :** `MAKORA_MODULE_RAPPORTS_ADMIN.md`

### Pages à créer

| Route               | Description                         | Rôles   |
| ------------------- | ----------------------------------- | ------- |
| `/reports`          | Génération + historique exports     | A · ADM |
| `/admin/users`      | Liste utilisateurs + création modal | ADM     |
| `/admin/users/[id]` | Détail user + gestion rôles         | ADM     |
| `/admin/roles`      | Rôles + permissions                 | ADM     |
| `/admin/system`     | Statut système + métriques          | ADM     |
| `/admin/logs`       | Journal d'activité (lecture seule)  | ADM     |

### Composants à créer

| Composant           | Chemin                                   |
| ------------------- | ---------------------------------------- |
| `ReportExportPanel` | `features/reports/ReportExportPanel.tsx` |
| `UserTable`         | `features/admin/UserTable.tsx`           |
| `UserCreateModal`   | `features/admin/UserCreateModal.tsx`     |
| `UserDetailPanel`   | `features/admin/UserDetailPanel.tsx`     |
| `RoleCard`          | `features/admin/RoleCard.tsx`            |
| `SystemStatusGrid`  | `features/admin/SystemStatusGrid.tsx`    |
| `ActivityLogTable`  | `features/admin/ActivityLogTable.tsx`    |

**Estimation : ~7 fichiers · ~1 500 lignes**

---

## 9. PHASE 10 — PROFIL + PAGES SYSTÈME 🟡

| Route               | Description                   | Rôles | Notes               |
| ------------------- | ----------------------------- | ----- | ------------------- |
| `/profile`          | Mon profil + changement mdp   | Tous  |                     |
| `/profile/security` | Sessions actives + révocation | Tous  |                     |
| `/unauthorized`     | Page 403                      | Tous  | Simple · ~30 lignes |
| `/not-found`        | Page 404                      | Tous  | Simple · ~30 lignes |

**Estimation : ~4 fichiers · ~400 lignes**

---

## 10. RÉCAPITULATIF GLOBAL

| Phase       | Module                            | Pages        | Composants         | Statut      |
| ----------- | --------------------------------- | ------------ | ------------------ | ----------- |
| 1           | Design System + AppShell          | —            | 17                 | ✅          |
| 2           | Auth + apiClient                  | 3            | 5                  | ✅          |
| 3           | Primitives + Dashboard            | 1            | 8                  | ✅          |
| **4**       | **Sinistres**                     | **7**        | **9**              | ✅          |
| **4.5**     | **Contexte branche + Plugin Pattern** | —        | **~12 refactorés** | ✅          |
| **5**       | **Audit HITL + Escalades**        | **5**        | **6**              | 🟠 Next     |
| **6**       | **Fraude (Graphe + Analytics)**   | **4**        | **5**              | 🟠          |
| **7**       | **Gouvernance ML**                | **6**        | **7**              | 🟠          |
| **8**       | **Configuration**                 | **3**        | **4**              | 🟠          |
| **9**       | **Rapports + Admin**              | **6**        | **7**              | 🟠          |
| **10**      | **Profil + Système**              | **4**        | **4**              | 🟡          |
| **TOTAL**   |                                   | **39 pages** | **~72 composants** |             |

### Jalons critiques (ordre impératif)

```
┌─ [✅ FAIT] Phases 1–3 — Design System + Auth + Dashboard
├─ [✅ FAIT] Phase 4 — Module Sinistres — base opérationnelle complète
├─ [✅ FAIT] Phase 4.5 — Contexte branche + Plugin Pattern frontend
├─ [Phase 5 → MAINTENANT] Audit HITL — DecisionPanel (Principe 5 inviolable)
├─ [Phase 6] Graphe D3 — reskin thème clair depuis mock
├─ [Phase 7] ⭐ /ml/models/compare — PREUVE EMPIRIQUE H0 DU MÉMOIRE
├─ [Phase 8] Configuration YAML + mercuriale CIMA
├─ [Phase 9] Admin + Rapports
└─ [Phase 10] Profil + pages système
```

---

## 11. ORDRE D'IMPLÉMENTATION DANS CHAQUE PHASE

Règle à respecter dans chaque phase :

1. `[domain].keys.ts` — query keys
2. `[domain].validators.ts` — schémas Zod
3. Composants primitifs (cards, badges, tables)
4. Composants features (panels, forms)
5. Pages (page.tsx) — orchestration légère uniquement
6. Test smoke (ouvrir la page, vérifier loading/error/empty)

---

_MAKORA_FRONTEND_MASTERPLAN_v4.md — 10 juin 2026_
_ATABONG EFON STEPHANE FRITZ_
_État : Phases 1–4.5 terminées · ~82 fichiers · Phase 5 (Audit HITL) à démarrer_
