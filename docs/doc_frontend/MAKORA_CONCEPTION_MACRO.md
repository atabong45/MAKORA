# MAKORA — Conception Frontend — Vue Macroscopique
> **Document :** MAKORA_CONCEPTION_MACRO.md  
> **Chantier :** 1 — Vue d'ensemble  
> **Date :** Juin 2026  
> **Auteur :** ATABONG EFON STEPHANE FRITZ  
> **Stack :** Next.js 14 · TypeScript · Shadcn/ui · Tailwind CSS · TanStack Query · Zustand

---

## 1. Contexte et objectif du refactoring

Le frontend existant est architecturalement solide (Next.js App Router, RBAC complet, séparation des couches, services API typés) mais souffre d'une absence totale d'UX : accumulation de fonctionnalités sans hiérarchie visuelle, thème sombre inadapté à un usage professionnel de jour, internationalisation absente.

**Ce qu'on conserve intégralement :**
- Architecture Next.js App Router (groupes `(auth)` et `(app)`)
- Middleware RBAC à 5 niveaux
- Tous les services API, hooks TanStack Query, stores Zustand
- Types TypeScript et validateurs Zod
- Séparation `components/common`, `components/features`, `lib/`, `hooks/`

**Ce qu'on refactorise complètement :**
- Tous les composants visuels (Shadcn reskin)
- Design system (tokens couleurs, typographie, espacements)
- Sidebar, topbar, AppShell
- Layouts de page, formulaires, tableaux, états empty/loading/error

**Ce qu'on ajoute :**
- Thème clair par défaut + thème sombre (toggle persisté localStorage)
- i18n FR/EN via `next-intl` (français par défaut)
- Command palette `Cmd+K`
- Onboarding guidé (premier login)
- Pages explicatives (À propos de MAKORA)
- Raccourcis clavier cohérents

---

## 2. Design System

### 2.1 Palette de couleurs

| Token | Valeur | Usage |
|---|---|---|
| `--color-navy` | `#1B3C6E` | Sidebar, éléments actifs, boutons primaires |
| `--color-gold` | `#F0A500` | Logo MAKORA, items nav actifs, CTA accent |
| `--color-white` | `#FFFFFF` | Fond principal, cartes |
| `--color-bg-page` | `#F8F9FA` | Fond de page (hors cartes) |
| `--color-bg-subtle` | `#F1F3F5` | Fond champs, sections secondaires |
| `--color-border` | `#E9ECEF` | Bordures, séparateurs |
| `--color-text-primary` | `#1A1D23` | Titres, labels principaux |
| `--color-text-secondary` | `#6B7280` | Descriptions, métadonnées |
| `--color-danger` | `#E24B4A` | Anomalies, erreurs, alertes critiques |
| `--color-warning` | `#F59E0B` | Avertissements, score intermédiaire |
| `--color-success` | `#1D9E75` | Succès, décision saine, score bas |
| `--color-info` | `#3B82F6` | Informations, branche Santé |

**Règles de score IF (seuils `lib/constants.ts`) :**
- `score < 0.6` → vert (`--color-success`)
- `0.6 ≤ score < 0.8` → orange (`--color-warning`)
- `score ≥ 0.8` → rouge (`--color-danger`)

### 2.2 Typographie

| Police | Famille | Usage |
|---|---|---|
| IBM Plex Sans | `font-sans` | Corps, labels, tableaux, formulaires (400/500) |
| DM Serif Display | `font-display` | Titres de page H1, accroches éditoriales |
| JetBrains Mono | `font-mono` | IDs sinistres, scores IF, codes, montants XAF |

### 2.3 Thèmes

Le thème **clair est le défaut**. Le thème sombre est disponible via un toggle dans la topbar. Le choix est persisté dans `localStorage('makora-theme')` et appliqué via la classe `dark` sur `<html>`.

```css
/* Variables light (défaut) */
:root {
  --sidebar-bg: #1B3C6E;
  --sidebar-text: rgba(255,255,255,0.75);
  --sidebar-active: #F0A500;
  --card-bg: #FFFFFF;
  --page-bg: #F8F9FA;
}

/* Variables dark */
.dark {
  --sidebar-bg: #0D1F3C;
  --card-bg: #111827;
  --page-bg: #0A0E1A;
}
```

### 2.4 Composants clés Shadcn à customiser

- `<Button>` — variante `primary` avec `--color-navy`, variante `ghost` pour les icônes
- `<Badge>` — variants `branch-sante`, `branch-auto`, `status-draft`, `status-open`, `status-closed`, `score-high`, `score-med`, `score-low`
- `<Table>` — lignes hover, colonnes triables, pagination intégrée
- `<Skeleton>` — utilisé systématiquement pendant les états de chargement
- `<Toast>` — 4 variantes : info, success, warning, error

---

## 3. Principes UX fondamentaux

1. **Sobriété** — Chaque élément affiché a une raison d'être. Les KPI sont visibles en 3 secondes. L'information dense est repliable (accordéon, drawer, onglets).

2. **Contexte camerounais visible** — Montants en XAF par défaut (format `Intl.NumberFormat('fr-CM', {style:'currency', currency:'XAF'})`). Codes ASAC (pas CCAM). Mercuriale CIMA référencée. Régions Cameroun dans les filtres.

3. **Thème clair professionnel** — L'application est utilisée en environnement de bureau, souvent projetée. Le fond blanc/gris clair avec le navy et l'or donne une identité premium sobre.

4. **RBAC silencieux** — La sidebar ne montre pas les items inaccessibles. Un item non autorisé est retiré, pas grisé. Les pages protégées retournent un 403 soigné avec explication contextuelle.

5. **États soignés systématiquement** — Skeleton loaders pour tous les tableaux/cartes. Messages empty state contextuels ("Aucun sinistre en attente pour la branche Santé"). Confirmation avant toute action destructive.

6. **i18n natif** — Toutes les chaînes passent par `next-intl`. Fichiers `fr.json` et `en.json`. Switch accessible depuis la topbar et le profil.

7. **Accessibilité de base** — Labels sur tous les inputs. Focus visible. `aria-label` sur les boutons icônes. Contrastes WCAG AA minimum.

---

## 4. Architecture des rôles (RBAC)

### 4.1 Les 4 rôles

| Code | Nom affiché | Mission principale |
|---|---|---|
| `G` | Gestionnaire de sinistres | Saisit, traite, soumet les sinistres au quotidien |
| `A` | Auditeur / Anti-fraude | Valide les alertes IA, résout les escalades, exporte |
| `E` | Expert métier | Surveille les modèles ML, drift, réentraînement |
| `ADM` | Administrateur système | Accès total, déploiement, configuration |

### 4.2 Matrice d'accès par module

| Module | G | A | E | ADM |
|---|:---:|:---:|:---:|:---:|
| Dashboard | ✅ | ✅ | ✅ | ✅ |
| Sinistres — liste & détail | ✅ | ✅ | ❌ | ✅ |
| Sinistres — créer / modifier | ✅ | ❌ | ❌ | ✅ |
| Sinistres — soumettre analyse | ✅ | ❌ | ❌ | ✅ |
| Audit — file décisions | ✅ | ✅ | ❌ | ✅ |
| Audit — prendre décision | ✅ | ✅ | ❌ | ✅ |
| Escalades — créer | ✅ | ❌ | ❌ | ✅ |
| Escalades — traiter / résoudre | ❌ | ✅ | ❌ | ✅ |
| Graphe de fraude | ❌ | ✅ | ❌ | ✅ |
| Analytics SHAP globales | ❌ | ✅ | ✅ | ✅ |
| Performances modèles | ❌ | ❌ | ✅ | ✅ |
| Drift monitoring | ❌ | ✅ | ✅ | ✅ |
| Drift — déclencher calcul | ❌ | ❌ | ✅ | ✅ |
| Modèles — catalogue | ❌ | ❌ | ✅ | ✅ |
| Modèles — déployer | ❌ | ❌ | ❌ | ✅ |
| Réentraînement — demander | ❌ | ❌ | ✅ | ✅ |
| Réentraînement — approuver | ❌ | ❌ | ❌ | ✅ |
| Config modules YAML | ❌ | ✅ (lecture) | ✅ (lecture) | ✅ |
| Référentiels / Mercuriale | ✅ (lecture) | ✅ (lecture) | ✅ | ✅ |
| Rapports export | ❌ | ✅ | ❌ | ✅ |
| Gestion utilisateurs & rôles | ❌ | ❌ | ❌ | ✅ |
| Configuration système | ❌ | ❌ | ❌ | ✅ |
| Journal activité | ❌ | ❌ | ❌ | ✅ |

---

## 5. Navigation globale

### 5.1 Structure AppShell

```
AppShell
├── <Sidebar>          — fixe desktop (w-64), drawer mobile
│   ├── Logo MAKORA + version
│   ├── Sélecteur de branche (Santé / Auto / Toutes)
│   ├── <SidebarNav>   — items filtrés par rôle
│   └── Footer         — statut système + version
└── <TopBar>           — h-16, sticky
    ├── Breadcrumb     — MAKORA > Section > Page
    ├── Sélecteur de branche (dupliqué, visible desktop)
    ├── <CommandPalette trigger>   — Cmd+K
    ├── <NotificationBell>         — selon rôle
    ├── Toggle i18n (FR/EN)
    ├── Toggle thème (☀/🌙)
    └── <UserMenu>     — avatar, nom, rôle, déconnexion
```

### 5.2 Items sidebar par rôle

**Tous les rôles :**
- Dashboard (`/dashboard`)

**G + A + ADM :**
- Sinistres (`/claims`) + sous-nav : Liste, Nouveau (G/ADM), Historique analyses

**A + ADM :**
- Audit & Décisions (`/audit`) + sous-nav : File, Escalades

**A + E + ADM :**
- Analyse de fraude (`/fraud`) + sous-nav : Graphe, Analytics, RCA (A/ADM)

**E + A + ADM :**
- Gouvernance ML (`/ml`) + sous-nav : Modèles, Drift, Réentraînement

**E + ADM :**
- Configuration (`/config`) + sous-nav : Modules, Référentiels, Import, OCR

**ADM uniquement :**
- Administration (`/admin`) + sous-nav : Utilisateurs, Rôles, Système, Journal

**Tous :**
- Mon profil (`/profile`) — en bas de sidebar ou topbar

### 5.3 Raccourcis clavier

| Touche | Action |
|---|---|
| `Cmd/Ctrl + K` | Ouvre la command palette |
| `D` | Navigue vers Dashboard |
| `S` | Navigue vers Sinistres |
| `A` | Navigue vers Audit |
| `G` | Navigue vers Graphe de fraude |
| `Échap` | Ferme la palette / modale active |
| `→ / ←` | Navigation entre onglets de la page active |

---

## 6. Inventaire des 48 pages

### 6.1 Authentification (public)

| # | Route | Titre | Rôles |
|---|---|---|---|
| 1 | `/login` | Connexion | Public |
| 2 | `/forgot-password` | Mot de passe oublié | Public |
| 3 | `/reset-password` | Réinitialiser | Public |

### 6.2 Module Dashboard

| # | Route | Titre | Rôles |
|---|---|---|---|
| 4 | `/dashboard` | Tableau de bord global | Tous |

### 6.3 Module Sinistres

| # | Route | Titre | Rôles |
|---|---|---|---|
| 5 | `/claims` | Liste des sinistres | G, A, ADM |
| 6 | `/claims/new` | Nouveau sinistre | G, ADM |
| 7 | `/claims/[id]` | Détail sinistre | G, A, ADM |
| 8 | `/claims/[id]/edit` | Modifier sinistre | G, ADM |
| 9 | `/claims/[id]/documents` | Documents & OCR | G, A, ADM |
| 10 | `/claims/[id]/lines` | Lignes de détail | G, A, ADM |
| 11 | `/claims/analyses` | Historique runs | G, A, ADM |

### 6.4 Module Audit & HITL

| # | Route | Titre | Rôles |
|---|---|---|---|
| 12 | `/audit` | File d'audit | G, A, ADM |
| 13 | `/audit/[analysis_id]` | Décision HITL | G, A, ADM |
| 14 | `/audit/[analysis_id]/shap` | SHAP explorer | A, E, ADM |
| 15 | `/escalations` | File d'escalades | A, ADM |
| 16 | `/escalations/[id]` | Détail escalade | A, ADM |

### 6.5 Module Analyse de fraude

| # | Route | Titre | Rôles |
|---|---|---|---|
| 17 | `/fraud/graph` | Graphe communautés | A, ADM |
| 18 | `/fraud/graph/[community_id]` | Détail communauté | A, ADM |
| 19 | `/fraud/analytics` | Analytics SHAP globales | A, E, ADM |
| 20 | `/fraud/rca` | Distribution RCA | A, ADM |

### 6.6 Module Gouvernance ML

| # | Route | Titre | Rôles |
|---|---|---|---|
| 21 | `/ml/models` | Catalogue modèles | E, ADM |
| 22 | `/ml/models/[id]` | Fiche modèle | E, ADM |
| 23 | `/ml/models/compare` | Comparaison modèles | E, ADM |
| 24 | `/ml/drift` | Dashboard drift | A, E, ADM |
| 25 | `/ml/drift/[branch]` | Drift par branche | A, E, ADM |
| 26 | `/ml/drift/[branch]/[report_id]` | Détail rapport drift | E, ADM |
| 27 | `/ml/retraining` | Demandes réentraînement | E, ADM |
| 28 | `/ml/retraining/new` | Nouvelle demande | E, ADM |
| 29 | `/ml/retraining/[id]` | Détail demande | E, ADM |

### 6.7 Module Configuration

| # | Route | Titre | Rôles |
|---|---|---|---|
| 30 | `/config/modules` | Modules actifs | A, E, ADM |
| 31 | `/config/modules/[branch]` | Config YAML branche | ADM |
| 32 | `/config/referentiels` | Référentiels | G, A, E, ADM |
| 33 | `/config/referentiels/practitioners` | Praticiens | A, ADM |
| 34 | `/config/referentiels/garages` | Garages | A, ADM |
| 35 | `/config/mercuriale` | Mercuriale CIMA | G, A, E, ADM |
| 36 | `/config/batch` | Import batch | G, ADM |
| 37 | `/config/ocr` | Pipeline OCR | G, ADM |

### 6.8 Module Rapports

| # | Route | Titre | Rôles |
|---|---|---|---|
| 38 | `/reports` | Rapports & exports | A, ADM |

### 6.9 Module Administration

| # | Route | Titre | Rôles |
|---|---|---|---|
| 39 | `/admin/users` | Gestion utilisateurs | ADM |
| 40 | `/admin/users/[id]` | Détail utilisateur | ADM |
| 41 | `/admin/roles` | Gestion rôles | ADM |
| 42 | `/admin/system` | Configuration système | ADM |
| 43 | `/admin/logs` | Journal activité | ADM |

### 6.10 Profil & Utilitaires

| # | Route | Titre | Rôles |
|---|---|---|---|
| 44 | `/profile` | Mon profil | Tous |
| 45 | `/profile/security` | Sessions actives | Tous |
| 46 | `/unauthorized` | 403 | Tous |
| 47 | `/not-found` | 404 | Tous |
| 48 | `/about` | À propos de MAKORA | Public / Tous |

---

## 7. Architecture technique de référence

### 7.1 Hiérarchie de protection des routes

```
middleware.ts          → Niveau 1 : token présent ou redirect /login
app/(app)/layout.tsx   → Niveau 2 : GET /auth/me valide + rôles chargés
<Sidebar>              → Niveau 3 : items filtrés selon rôle (items retirés, pas grisés)
<PermissionGuard>      → Niveau 4 : boutons/sections visibles selon permission
Backend RBAC           → Niveau 5 : HTTP 403 si non autorisé (validation finale)
```

### 7.2 Constantes globales (`src/lib/constants.ts`)

```typescript
export const SCORE_THRESHOLDS = { alert: 0.6, block: 0.8 } as const;
export const RATIO_THRESHOLDS = { ok: 1.10, warning: 1.30 } as const;
export const PSI_THRESHOLDS = { stable: 0.10, warning: 0.20 } as const;
export const CURRENCY = 'XAF' as const;
export const DATE_FORMAT = 'DD/MM/YYYY' as const;
export const PAGINATION_DEFAULTS = { page: 1, pageSize: 20 } as const;
```

### 7.3 Formatage des montants XAF

```typescript
// src/lib/formatters.ts
export const formatXAF = (amount: number): string =>
  new Intl.NumberFormat('fr-CM', {
    style: 'currency',
    currency: 'XAF',
    maximumFractionDigits: 0,
  }).format(amount);
// → "485 000 XAF"
```

### 7.4 Onboarding — Guided Tour

Au premier accès (flag `localStorage('makora-tour-done')` absent), un composant `<GuidedTour>` s'active avec overlay et spotlight :

1. Sélecteur de branche (Santé / Auto)
2. Structure de la sidebar selon le rôle
3. Dashboard — KPI et alertes
4. Action principale selon rôle (G: créer sinistre / A: file d'audit / E: drift)

---

## 8. Plan de réalisation recommandé

| Phase FE | Contenu | Priorité |
|---|---|---|
| FE-1 | Scaffolding design tokens + AppShell + auth stores + middleware | 🔴 |
| FE-2 | Pages auth (login, forgot, reset) + apiClient + auth hooks | 🔴 |
| FE-3 | Dashboard + composants communs (DataTable, KpiCard, BranchPill, ScoreBadge) | 🔴 |
| FE-4 | Module Sinistres complet (7 pages) | 🔴 |
| FE-5 | Module Audit + SHAP + HITL Decision Panel | 🟠 |
| FE-6 | Module Escalades | 🟠 |
| FE-7 | Graphe de fraude (D3.js) + Analytics + RCA | 🟠 |
| FE-8 | Gouvernance ML (modèles, drift, réentraînement) | 🟠 |
| FE-9 | Configuration (modules YAML, référentiels, mercuriale) | 🟠 |
| FE-10 | Rapports & exports | 🟡 |
| FE-11 | Administration (users, rôles, système) | 🟠 |
| FE-12 | Profil + sécurité + onboarding + à propos | 🟡 |
| FE-13 | Tests E2E Playwright | 🟡 |

---

*MAKORA_CONCEPTION_MACRO.md — Juin 2026 — ATABONG EFON STEPHANE FRITZ*
