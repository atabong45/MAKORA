# MAKORA — Système de Conception Frontend Complet
> **Document :** MAKORA_FRONTEND_DESIGN_SYSTEM.md v1.0  
> **Date :** 31 mai 2026  
> **Auteur :** ATABONG EFON STEPHANE FRITZ  
> **Périmètre :** Architecture UI complète, design system, structure Next.js, mapping endpoints, RBAC visuel  
> **Stack :** Next.js 14 (App Router) · TypeScript · TanStack Query · Zustand · Shadcn/ui · Tailwind CSS

---

## TABLE DES MATIÈRES

1. [Principes directeurs UX](#1-principes-directeurs-ux)
2. [Système de Design — Tokens et Charte Visuelle](#2-système-de-design--tokens-et-charte-visuelle)
3. [Rôles et matrice d'accès RBAC](#3-rôles-et-matrice-daccès-rbac)
4. [Navigation globale — Navbar & Sidebar](#4-navigation-globale--navbar--sidebar)
5. [Inventaire exhaustif des pages](#5-inventaire-exhaustif-des-pages)
6. [Détail de chaque page et ses fonctionnalités](#6-détail-de-chaque-page-et-ses-fonctionnalités)
7. [Mapping complet Endpoints ↔ Pages](#7-mapping-complet-endpoints--pages)
8. [Architecture du code Next.js](#8-architecture-du-code-nextjs)
9. [Structure des dossiers](#9-structure-des-dossiers)
10. [Types TypeScript fondamentaux](#10-types-typescript-fondamentaux)
11. [Services API — organisation](#11-services-api--organisation)
12. [Hooks personnalisés — inventaire](#12-hooks-personnalisés--inventaire)
13. [Composants réutilisables — inventaire](#13-composants-réutilisables--inventaire)
14. [Gestion d'état global — Zustand stores](#14-gestion-détat-global--zustand-stores)
15. [Système de routage et protection des routes](#15-système-de-routage-et-protection-des-routes)
16. [Onboarding et prise en main](#16-onboarding-et-prise-en-main)
17. [Contraintes et standards de code](#17-contraintes-et-standards-de-code)

---

## 1. PRINCIPES DIRECTEURS UX

### 1.1 Philosophie générale

MAKORA est un outil professionnel de détection de fraude destiné à des **gestionnaires de sinistres, auditeurs et administrateurs** travaillant dans des compagnies d'assurance camerounaises/africaines. L'interface doit refléter :

- **Autorité et confiance** — les décisions prises ici ont des conséquences financières et légales
- **Clarté opérationnelle** — un gestionnaire doit pouvoir traiter un dossier sans se perdre
- **Guidage progressif** — l'IA explique ses décisions, elle ne cache pas
- **Efficacité dense** — les tableaux de bord affichent beaucoup d'information sans surcharger

### 1.2 Les 5 principes UX non-négociables

| # | Principe | Traduction concrète |
|---|---|---|
| 1 | **Contexte toujours visible** | Le nom de la branche active (Santé / Auto) est toujours affiché en haut |
| 2 | **Score = couleur = urgence** | Un code couleur uniforme (vert/orange/rouge) pour les scores de risque sur TOUTES les pages |
| 3 | **Zéro clic orphelin** | Chaque action a un retour visuel immédiat (toast, spinner, état désactivé) |
| 4 | **Fil d'Ariane métier** | Toujours savoir : on est sur quel sinistre / quelle analyse / quel modèle |
| 5 | **Explication avant décision** | Avant tout bouton CONFIRMER/REJETER, le score + SHAP + RCA sont toujours visibles |

### 1.3 Niveaux d'information par profil

| Rôle | Posture | Focus principal | Ce qu'il ne doit pas voir |
|---|---|---|---|
| **Gestionnaire** | Opérationnel — traite des dossiers | Liste sinistres, résultat analyse, décision | Drift, modèles, réentraînement, users |
| **Auditeur** | Analytique — valide et escalade | Files d'escalade, graphe fraude, stats SHAP | Gestion users, config technique |
| **Expert Métier** | Technique-métier | Modèles, drift, règles RCA, performances | Gestion users, sinistres individuels |
| **Administrateur** | Gouvernance totale | Tout, + config système + users | Rien |

---

## 2. SYSTÈME DE DESIGN — TOKENS ET CHARTE VISUELLE

### 2.1 Palette de couleurs

La charte MAKORA s'appuie sur **bleu roi + dorés** — associés à l'autorité, la précision et la valeur en Afrique subsaharienne.

```typescript
// design-tokens.ts — à placer dans /src/styles/tokens.ts

export const MAKORA_COLORS = {
  // Primaires — Bleu Roi
  primary: {
    50:  '#EEF4FF',
    100: '#D9E8FF',
    200: '#B3D1FF',
    300: '#7DB3FF',
    400: '#4090FF',
    500: '#1A6EF5',   // ← Bleu roi principal
    600: '#1558D6',
    700: '#1043A8',
    800: '#0D307A',
    900: '#091F52',
    950: '#050E2B',
  },

  // Secondaires — Or / Doré
  gold: {
    50:  '#FFFBEB',
    100: '#FEF3C7',
    200: '#FDE68A',
    300: '#FCD34D',
    400: '#FBBF24',
    500: '#D4A017',   // ← Or principal (texte sur fond sombre)
    600: '#B7860F',
    700: '#926A0A',
    800: '#6B4E07',
    900: '#3D2D03',
  },

  // Neutrals — Ardoise profonde (pas de gris neutres banaux)
  slate: {
    50:  '#F8FAFC',
    100: '#F1F5F9',
    200: '#E2E8F0',
    300: '#CBD5E1',
    400: '#94A3B8',
    500: '#64748B',
    600: '#475569',
    700: '#334155',
    800: '#1E293B',
    900: '#0F172A',
    950: '#020617',
  },

  // Sémantiques — Statuts
  risk: {
    safe:     '#16A34A',  // Vert — score < seuil alert
    warning:  '#D97706',  // Ambre — score entre alert et block
    critical: '#DC2626',  // Rouge — score > seuil block
    unknown:  '#6B7280',  // Gris — pas encore analysé
  },

  // Décisions HITL
  decision: {
    confirmed: '#DC2626',  // Fraude confirmée — rouge
    rejected:  '#16A34A',  // Rejeté (non fraude) — vert
    escalated: '#7C3AED',  // Escaladé — violet
    pending:   '#D97706',  // En attente — ambre
  },

  // Drift PSI
  drift: {
    stable:   '#16A34A',  // PSI < 0.10
    warning:  '#D97706',  // PSI 0.10–0.20
    critical: '#DC2626',  // PSI > 0.20
  },
} as const;
```

### 2.2 Typographie

```typescript
// typography.ts
// Police principale : IBM Plex Sans (sérieux, africaine via IBM Research Africa, lisible)
// Police de données : IBM Plex Mono (tableaux, scores, codes)
// Police d'accentuation : Playfair Display (titres de section, éléments à forte valeur)

export const TYPOGRAPHY = {
  fontFamily: {
    sans:    '"IBM Plex Sans", "Noto Sans", system-ui, sans-serif',
    mono:    '"IBM Plex Mono", "JetBrains Mono", monospace',
    display: '"Playfair Display", Georgia, serif',
  },
  fontSize: {
    xs:   '0.75rem',   // 12px — labels, badges
    sm:   '0.875rem',  // 14px — texte secondaire, tableaux
    base: '1rem',      // 16px — texte courant
    lg:   '1.125rem',  // 18px — titres de carte
    xl:   '1.25rem',   // 20px — titres de section
    '2xl':'1.5rem',    // 24px — titres de page
    '3xl':'1.875rem',  // 30px — KPIs dashboard
    '4xl':'2.25rem',   // 36px — scores principaux
  },
} as const;
```

### 2.3 Thème global CSS — variables Tailwind

```css
/* globals.css — variables CSS MAKORA */
:root {
  --makora-bg-primary:    #0F172A;   /* slate-950 — fond principal (dark by default) */
  --makora-bg-surface:    #1E293B;   /* slate-800 — cartes, sidebars */
  --makora-bg-elevated:   #334155;   /* slate-700 — menus, popovers */
  --makora-border:        #475569;   /* slate-600 — séparateurs */
  
  --makora-text-primary:  #F8FAFC;   /* slate-50 */
  --makora-text-secondary:#94A3B8;   /* slate-400 */
  --makora-text-muted:    #64748B;   /* slate-500 */

  --makora-accent-blue:   #1A6EF5;   /* bleu roi */
  --makora-accent-blue-light: #4090FF;
  --makora-accent-gold:   #D4A017;   /* or */
  --makora-accent-gold-light: #FBBF24;

  --makora-radius-sm:  4px;
  --makora-radius-md:  8px;
  --makora-radius-lg:  12px;
  --makora-radius-xl:  16px;

  --makora-shadow-card: 0 4px 24px rgba(0, 0, 0, 0.4);
  --makora-shadow-elevated: 0 8px 40px rgba(0, 0, 0, 0.6);
}
```

### 2.4 Composants visuels signature

| Composant | Description visuelle |
|---|---|
| **Score Badge** | Cercle de 48px, fond coloré selon risque, score en mono-gras |
| **Risk Gauge** | Arc SVG semi-circulaire, aiguille animée, trois zones colorées |
| **SHAP Bar Chart** | Barres horizontales bicolores (pos/neg), feature name en mono |
| **Branch Pill** | Pill colorée avec icône, `SANTÉ` en bleu, `AUTO` en doré |
| **Anomaly Flag** | Triangle exclamation animé, rouge pulsant si score > block |
| **Decision Badge** | Pill arrondie avec icône — CONFIRMÉ/REJETÉ/ESCALADÉ/EN ATTENTE |

---

## 3. RÔLES ET MATRICE D'ACCÈS RBAC

### 3.1 Les 4 rôles

```
gestionnaire    → G    — traite les sinistres au quotidien
auditeur        → A    — valide, escalade, analyse les fraudes
expert_metier   → E    — surveille les modèles ML et drift
administrateur  → ADM  — gouvernance totale
```

### 3.2 Matrice d'accès par grande section

| Section | G | A | E | ADM |
|---|:---:|:---:|:---:|:---:|
| Dashboard global | ✅ | ✅ | ✅ | ✅ |
| Sinistres — liste & détail | ✅ | ✅ | ❌ | ✅ |
| Sinistres — créer / modifier | ✅ | ❌ | ❌ | ✅ |
| Sinistres — soumettre analyse | ✅ | ❌ | ❌ | ✅ |
| Audit — file de décisions | ✅ | ✅ | ❌ | ✅ |
| Audit — prendre une décision | ✅ | ✅ | ❌ | ✅ |
| Escalades — créer | ✅ | ❌ | ❌ | ✅ |
| Escalades — traiter / résoudre | ❌ | ✅ | ❌ | ✅ |
| Graphe de fraude | ❌ | ✅ | ❌ | ✅ |
| Analyses — historique runs | ✅ | ✅ | ❌ | ✅ |
| Analytics SHAP | ❌ | ✅ | ✅ | ✅ |
| Analytics performances | ❌ | ❌ | ✅ | ✅ |
| Drift monitoring | ❌ | ✅ | ✅ | ✅ |
| Drift — déclencher calcul | ❌ | ❌ | ✅ | ✅ |
| Modèles — catalogue | ❌ | ❌ | ✅ | ✅ |
| Modèles — déployer | ❌ | ❌ | ❌ | ✅ |
| Réentraînement — demander | ❌ | ❌ | ✅ | ✅ |
| Réentraînement — approuver | ❌ | ❌ | ❌ | ✅ |
| Modules YAML — consulter | ❌ | ✅ | ✅ | ✅ |
| Modules YAML — modifier | ❌ | ❌ | ❌ | ✅ |
| Référentiels — praticiens/garages | ❌ | ✅ | ❌ | ✅ |
| Référentiels — mercuriale | ✅ | ✅ | ✅ | ✅ |
| Référentiels — importer mercuriale | ❌ | ❌ | ✅ | ✅ |
| Rapports — export | ❌ | ✅ | ❌ | ✅ |
| Gestion utilisateurs | ❌ | ❌ | ❌ | ✅ |
| Gestion rôles | ❌ | ❌ | ❌ | ✅ |
| Config système | ❌ | ❌ | ❌ | ✅ |
| Journal activité système | ❌ | ❌ | ❌ | ✅ |

### 3.3 Logique de garde côté frontend

```typescript
// src/lib/rbac.ts
export type Role = 'gestionnaire' | 'auditeur' | 'expert_metier' | 'administrateur';

export type Permission =
  | 'claims:read' | 'claims:write' | 'claims:submit'
  | 'audit:read' | 'audit:decide'
  | 'escalations:create' | 'escalations:resolve'
  | 'graph:read'
  | 'analytics:shap' | 'analytics:performance'
  | 'drift:read' | 'drift:run'
  | 'models:read' | 'models:deploy'
  | 'retraining:request' | 'retraining:approve'
  | 'modules:read' | 'modules:write'
  | 'referentiels:read' | 'referentiels:write'
  | 'reports:export'
  | 'users:manage'
  | 'admin:system';

export const ROLE_PERMISSIONS: Record<Role, Permission[]> = {
  gestionnaire: [
    'claims:read', 'claims:write', 'claims:submit',
    'audit:read', 'audit:decide',
    'escalations:create',
    'referentiels:read',
  ],
  auditeur: [
    'claims:read',
    'audit:read', 'audit:decide',
    'escalations:resolve',
    'graph:read',
    'analytics:shap',
    'drift:read',
    'modules:read',
    'referentiels:read',
    'reports:export',
  ],
  expert_metier: [
    'analytics:shap', 'analytics:performance',
    'drift:read', 'drift:run',
    'models:read',
    'retraining:request',
    'modules:read',
    'referentiels:read', 'referentiels:write',
  ],
  administrateur: [
    'claims:read', 'claims:write', 'claims:submit',
    'audit:read', 'audit:decide',
    'escalations:create', 'escalations:resolve',
    'graph:read',
    'analytics:shap', 'analytics:performance',
    'drift:read', 'drift:run',
    'models:read', 'models:deploy',
    'retraining:request', 'retraining:approve',
    'modules:read', 'modules:write',
    'referentiels:read', 'referentiels:write',
    'reports:export',
    'users:manage',
    'admin:system',
  ],
};

export function hasPermission(userRoles: Role[], permission: Permission): boolean {
  return userRoles.some(role =>
    ROLE_PERMISSIONS[role]?.includes(permission)
  );
}
```

---

## 4. NAVIGATION GLOBALE — NAVBAR & SIDEBAR

### 4.1 Structure de la Navbar (TopBar)

La navbar est une **barre horizontale fixe en haut** (hauteur 64px), sur fond `slate-900` avec bordure dorée inférieure subtile (1px gold-500 à 30% opacité).

```
┌──────────────────────────────────────────────────────────────────────────────────────┐
│  [Logo MAKORA]  [Branch Selector]          [Search]    [Notifications]  [User Menu]  │
│  M◈AKORA        [◉ SANTÉ ▾] [○ AUTO]       🔍          🔔 (3)           [Avatar ▾]   │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

**Composants de la navbar :**

| Élément | Description | API consommée |
|---|---|---|
| **Logo MAKORA** | M◈AKORA en Playfair Display, lien vers `/dashboard` | — |
| **Branch Selector** | Pills cliquables SANTÉ / AUTO. Mémorisé dans Zustand. Filtre toute l'app | `GET /modules/` — statut modules |
| **Search global** | `Cmd+K` — recherche sinistres par ID, assuré, praticien | `GET /claims/?search=` |
| **Notifications** | Badge numéroté — escalades en attente + drift alerts | `GET /escalations/pending` + `GET /drift/status` |
| **User Menu** | Avatar + nom + rôle + liens Profil / Changer mdp / Déconnexion | `GET /auth/me`, `POST /auth/logout` |

### 4.2 Structure de la Sidebar (navigation latérale)

La sidebar est **fixe à gauche**, largeur 240px (rétractable à 60px — icônes seules). Fond `slate-900`. Section `border-r` avec `gold-500` à 20% opacité.

La sidebar est **dynamique selon le rôle** : les sections auxquelles l'utilisateur n'a pas accès sont absentes (non cachées, absentes — principe d'affordance).

```
┌─────────────────────────┐
│  ▸ TABLEAU DE BORD      │  → /dashboard              (tous)
│                         │
│  ▸ SINISTRES            │  → visible si claims:read
│    ├ Tous les sinistres │  → /claims
│    ├ Nouveau sinistre   │  → /claims/new             (claims:write)
│    └ Analyses en cours  │  → /claims/analyses
│                         │
│  ▸ AUDIT & DÉCISIONS    │  → visible si audit:read
│    ├ File d'audit       │  → /audit
│    └ Escalades          │  → /escalations
│                         │
│  ▸ ANALYSE DE FRAUDE    │  → visible si graph:read OU analytics:shap
│    ├ Graphe de fraude   │  → /fraud/graph            (graph:read)
│    ├ Analytiques SHAP   │  → /fraud/analytics        (analytics:shap)
│    └ Distrib. RCA       │  → /fraud/rca              (analytics:shap)
│                         │
│  ▸ GOUVERNANCE ML       │  → visible si models:read OU drift:read
│    ├ Modèles            │  → /ml/models              (models:read)
│    ├ Drift Monitor      │  → /ml/drift               (drift:read)
│    └ Réentraînement     │  → /ml/retraining          (retraining:request)
│                         │
│  ▸ CONFIGURATION        │  → visible si modules:read OU referentiels:read
│    ├ Modules & Règles   │  → /config/modules         (modules:read)
│    └ Référentiels       │  → /config/referentiels    (referentiels:read)
│                         │
│  ▸ RAPPORTS             │  → visible si reports:export
│    └ Exports            │  → /reports                (reports:export)
│                         │
│  ▸ ADMINISTRATION       │  → visible si users:manage OU admin:system
│    ├ Utilisateurs       │  → /admin/users            (users:manage)
│    ├ Rôles              │  → /admin/roles            (users:manage)
│    └ Système            │  → /admin/system           (admin:system)
│                         │
│  ─────────────────────  │
│  [Health indicator]     │  → dot vert/rouge — /health
└─────────────────────────┘
```

### 4.3 Sidebar par rôle — ce qui est visible

| Section sidebar | G | A | E | ADM |
|---|:---:|:---:|:---:|:---:|
| Tableau de bord | ✅ | ✅ | ✅ | ✅ |
| Sinistres | ✅ | ✅ | ❌ | ✅ |
| → Nouveau sinistre | ✅ | ❌ | ❌ | ✅ |
| Audit & Décisions | ✅ | ✅ | ❌ | ✅ |
| → Escalades | ✅ (créer) | ✅ (résoudre) | ❌ | ✅ |
| Analyse de fraude | ❌ | ✅ | ✅ | ✅ |
| → Graphe de fraude | ❌ | ✅ | ❌ | ✅ |
| → Analytiques SHAP | ❌ | ✅ | ✅ | ✅ |
| Gouvernance ML | ❌ | ✅ (drift) | ✅ | ✅ |
| → Modèles | ❌ | ❌ | ✅ | ✅ |
| → Drift Monitor | ❌ | ✅ | ✅ | ✅ |
| → Réentraînement | ❌ | ❌ | ✅ | ✅ |
| Configuration | ❌ | ✅ | ✅ | ✅ |
| Rapports | ❌ | ✅ | ❌ | ✅ |
| Administration | ❌ | ❌ | ❌ | ✅ |

---

## 5. INVENTAIRE EXHAUSTIF DES PAGES

### 5.1 Récapitulatif — 42 pages / vues

| # | Route Next.js | Titre | Rôles | Section sidebar |
|---|---|---|---|---|
| 1 | `/` | Redirection → login ou dashboard | — | — |
| 2 | `/login` | Connexion | Public | — |
| 3 | `/forgot-password` | Mot de passe oublié | Public | — |
| 4 | `/reset-password` | Réinitialiser le mot de passe | Public | — |
| 5 | `/dashboard` | Tableau de bord global | Tous | Tableau de bord |
| 6 | `/claims` | Liste des sinistres | G, A, ADM | Sinistres |
| 7 | `/claims/new` | Nouveau sinistre | G, ADM | Sinistres |
| 8 | `/claims/[id]` | Détail sinistre | G, A, ADM | Sinistres |
| 9 | `/claims/[id]/edit` | Modifier sinistre (DRAFT) | G, ADM | Sinistres |
| 10 | `/claims/[id]/documents` | Documents & OCR | G, A, ADM | Sinistres |
| 11 | `/claims/[id]/lines` | Lignes de détail | G, A, ADM | Sinistres |
| 12 | `/claims/analyses` | Historique runs d'analyse | G, A, ADM | Sinistres |
| 13 | `/audit` | File d'audit (décisions en attente) | G, A, ADM | Audit & Décisions |
| 14 | `/audit/[analysis_id]` | Détail analyse — décision HITL | G, A, ADM | Audit & Décisions |
| 15 | `/audit/[analysis_id]/shap` | Valeurs SHAP complètes | G, A, ADM | Audit & Décisions |
| 16 | `/escalations` | Liste des escalades | A, ADM | Audit & Décisions |
| 17 | `/escalations/[id]` | Détail escalade | A, ADM | Audit & Décisions |
| 18 | `/fraud/graph` | Graphe de communautés de fraude | A, ADM | Analyse de fraude |
| 19 | `/fraud/graph/[community_id]` | Détail communauté | A, ADM | Analyse de fraude |
| 20 | `/fraud/analytics` | Analytiques SHAP globales | A, E, ADM | Analyse de fraude |
| 21 | `/fraud/rca` | Distribution des catégories RCA | A, ADM | Analyse de fraude |
| 22 | `/ml/models` | Catalogue des modèles ML | E, ADM | Gouvernance ML |
| 23 | `/ml/models/[model_id]` | Fiche détaillée d'un modèle | E, ADM | Gouvernance ML |
| 24 | `/ml/models/compare` | Comparaison inter-modèles | E, ADM | Gouvernance ML |
| 25 | `/ml/drift` | Dashboard drift — toutes branches | A, E, ADM | Gouvernance ML |
| 26 | `/ml/drift/[branch]` | Drift détaillé par branche | A, E, ADM | Gouvernance ML |
| 27 | `/ml/drift/[branch]/[report_id]` | Détail rapport drift | E, ADM | Gouvernance ML |
| 28 | `/ml/retraining` | Demandes de réentraînement | E, ADM | Gouvernance ML |
| 29 | `/ml/retraining/new` | Nouvelle demande | E, ADM | Gouvernance ML |
| 30 | `/ml/retraining/[id]` | Détail demande | E, ADM | Gouvernance ML |
| 31 | `/config/modules` | Modules actifs & statuts | A, E, ADM | Configuration |
| 32 | `/config/modules/[branch]` | Config YAML d'une branche | E, ADM | Configuration |
| 33 | `/config/modules/[branch]/rules` | Règles RCA de la branche | A, E, ADM | Configuration |
| 34 | `/config/referentiels` | Hub référentiels | G, A, E, ADM | Configuration |
| 35 | `/config/referentiels/practitioners` | Liste des praticiens | A, ADM | Configuration |
| 36 | `/config/referentiels/practitioners/[id]` | Fiche praticien | A, ADM | Configuration |
| 37 | `/config/referentiels/garages` | Liste des garages | A, ADM | Configuration |
| 38 | `/config/referentiels/garages/[id]` | Fiche garage | A, ADM | Configuration |
| 39 | `/config/referentiels/prices` | Mercuriales ASAC/CIMA | G, A, E, ADM | Configuration |
| 40 | `/reports` | Hub exports & rapports | A, ADM | Rapports |
| 41 | `/admin/users` | Gestion des utilisateurs | ADM | Administration |
| 42 | `/admin/users/[id]` | Profil utilisateur (admin) | ADM | Administration |
| 43 | `/admin/roles` | Rôles et permissions | ADM | Administration |
| 44 | `/admin/system` | État du système + logs | ADM | Administration |
| 45 | `/profile` | Mon profil (tous) | Tous | (lien user menu) |
| 46 | `/profile/security` | Sécurité — sessions actives | Tous | (lien user menu) |
| 47 | `/unauthorized` | 403 — accès refusé | Tous | — |
| 48 | `/not-found` | 404 | Tous | — |

---

## 6. DÉTAIL DE CHAQUE PAGE ET SES FONCTIONNALITÉS

---

### PAGE 01 — Login (`/login`)

**Rôle :** Point d'entrée unique. Pas d'auto-inscription (comptes créés par admin).

**Layout :** Full-screen splitté — gauche 40% dark avec logo + tagline, droite 60% formulaire.

**Composants :**
- Logo MAKORA en grand (Playfair Display)
- Tagline : *"Détection de fraude intelligente pour l'assurance africaine"*
- `<LoginForm>` : champs username + password, bouton Se connecter
- Lien "Mot de passe oublié ?" → `/forgot-password`
- Indicateur Health API (petit dot vert/rouge en bas de page)

**Endpoints consommés :**
- `POST /auth/login` — authentification + récupération tokens
- `GET /health` — indicateur état API visible sur la page de login

**Comportements :**
- Redirection automatique vers `/dashboard` si déjà connecté (token valide)
- Message d'erreur spécifique : compte inactif / identifiants invalides
- Verrouillage visuel après 5 tentatives (rate limit backend)
- Persist du `access_token` en mémoire + `refresh_token` en cookie httpOnly

---

### PAGE 02 — Mot de passe oublié (`/forgot-password`)

**Endpoints :** `POST /auth/forgot-password`

**Fonctionnalités :** Saisie email → toast "Un email a été envoyé si ce compte existe" (prototype sans SMTP réel — afficher le token en dev)

---

### PAGE 03 — Réinitialiser le mot de passe (`/reset-password`)

**Endpoints :** `POST /auth/reset-password`

**Fonctionnalités :** Formulaire new password + confirmation. Token JWT 30min en query param. Validation complexité côté client.

---

### PAGE 04 — Dashboard Global (`/dashboard`)

**Rôle :** Vue d'ensemble de l'activité MAKORA. Première page vue après connexion. Personnalisée par rôle.

**Layout :** Grille de KPIs en haut, puis widgets selon le rôle.

**Section KPIs — top row (4 cartes)**
```
┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
│  Sinistres     │  │  Taux anomalie │  │  Décisions     │  │  Drift status  │
│  analysés      │  │  global        │  │  en attente    │  │  SANTÉ / AUTO  │
│  [1 247]       │  │  [8.3%]        │  │  [34]          │  │  ● STABLE      │
│  ↑ +12 / 24h   │  │  ↑ +0.4%       │  │  ↑ urgent: 5   │  │  ● WARNING     │
└────────────────┘  └────────────────┘  └────────────────┘  └────────────────┘
```

**Widgets par rôle :**

| Widget | G | A | E | ADM |
|---|:---:|:---:|:---:|:---:|
| Sinistres récents (tableau 5 lignes) | ✅ | ✅ | ❌ | ✅ |
| File d'audit (5 dernières en attente) | ✅ | ✅ | ❌ | ✅ |
| Escalades non assignées (badge) | ❌ | ✅ | ❌ | ✅ |
| Top 5 features SHAP du mois | ❌ | ✅ | ✅ | ✅ |
| Drift PSI par branche (gauge) | ❌ | ✅ | ✅ | ✅ |
| Performances modèles actifs | ❌ | ❌ | ✅ | ✅ |
| Activité système | ❌ | ❌ | ❌ | ✅ |

**Endpoints consommés :**
- `GET /analytics/dashboard` — KPIs globaux
- `GET /claims/?page=1&page_size=5&sort=created_at` — sinistres récents
- `GET /audit/?decision_status=PENDING&page_size=5` — file d'audit
- `GET /escalations/pending` — escalades non assignées
- `GET /analytics/shap/top-features` — top features
- `GET /drift/status` — statut drift toutes branches
- `GET /analytics/models/performance` — métriques modèles
- `GET /reports/stats/global` — stats globales

---

### PAGE 05 — Liste des sinistres (`/claims`)

**Rôle :** Vue principale du gestionnaire. Tableau paginé, filtrable, triable.

**Layout :** Barre de filtres en haut + tableau principal + pagination.

**Filtres disponibles :**
- Branch (SANTÉ / AUTO / Toutes)
- Statut (DRAFT / SUBMITTED / OPEN / CLOSED)
- Score min (slider 0–1)
- Is anomaly (toggle)
- Plage de dates (`date_soin_from` / `date_soin_to`)
- Recherche libre (ID sinistre, numéro police)

**Colonnes du tableau :**

| Colonne | Description |
|---|---|
| ID Sinistre | `claim_reference` en mono — cliquable → `/claims/[id]` |
| Branche | Branch pill (SANTÉ bleu / AUTO doré) |
| Assuré | `insured_hash` pseudonymisé |
| Date soin | Format DD/MM/YYYY |
| Montant | En XAF, format milliers |
| Statut | Badge coloré |
| Score | Score Badge (si analysé) — cercle coloré |
| Anomalie | `⚠` si `is_anomaly=true` |
| Décision | Decision Badge ou `—` |
| Actions | Boutons contextuels |

**Boutons d'action par ligne :**
- `Voir` → `/claims/[id]`
- `Analyser` (si DRAFT) → déclenche `POST /claims/[id]/submit`
- `Décider` (si OPEN + rôle G/A) → `/audit/[analysis_id]`

**Bouton global :** `+ Nouveau sinistre` (visible si `claims:write`)

**Endpoints consommés :**
- `GET /claims/` (avec tous les filtres supportés)
- `POST /claims/{claim_id}/submit` — depuis le tableau

---

### PAGE 06 — Nouveau sinistre (`/claims/new`)

**Rôle :** Formulaire de saisie d'un sinistre (statut DRAFT).

**Layout :** Formulaire en deux colonnes, wizard à 3 étapes.

**Étape 1 — Informations générales**
- Branche (SANTÉ / AUTO) — sélecteur obligatoire → détermine les champs suivants
- Numéro de police (lookup `GET /referentiels/prices/{branch}`)
- Date du sinistre
- Description libre

**Étape 2 — Lignes de détail** (conditionnel selon branche)
- *Branche SANTÉ :* code acte ASAC, praticien, montant, quantité
- *Branche AUTO :* poste de réparation, garage, montant devis
- Tableau éditable de lignes — `POST /claims/{id}/lines`

**Étape 3 — Documents**
- Upload drag & drop (PDF, JPG, PNG — max 50MB)
- Liste des documents ajoutés avec statut
- Option "Déclencher OCR" sur upload

**Bouton final :** `Enregistrer & Soumettre à l'analyse` → `POST /claims/{id}/submit`

**Endpoints consommés :**
- `POST /claims/` — création
- `POST /claims/{id}/lines` — lignes
- `POST /claims/{id}/documents` — documents
- `POST /claims/{id}/ocr/run` — OCR optionnel
- `POST /claims/{id}/submit` — soumission

---

### PAGE 07 — Détail sinistre (`/claims/[id]`)

**Rôle :** Vue maître du sinistre. Toutes les informations + résultat analyse + historique.

**Layout :** En-tête avec infos clés + onglets.

**En-tête :**
```
[ID SINISTRE SIN_2025_CM_00842]  [Branch: ◉ SANTÉ]  [Statut: OPEN]
Assuré: ASS_XXXX — Police P-2024-001 — Date: 12/03/2025
Montant total: 485 000 XAF                [Score: ●0.78 CRITIQUE]
```

**Onglets :**

| Onglet | Contenu | Endpoints |
|---|---|---|
| **Résumé** | Score + RCA + narration LLM | `GET /claims/{id}` |
| **Analyse IA** | SHAP top 3, jauge, narration complète | `GET /claims/{id}/analyses` |
| **Lignes** | Tableau actes/postes avec écart mercuriale | `GET /claims/{id}/lines` |
| **Documents** | Galerie docs + résultat OCR | `GET /claims/{id}/documents`, `GET /claims/{id}/ocr` |
| **Historique** | Timeline des analyses et décisions | `GET /claims/{id}/analyses`, `GET /audit/{id}/decisions` |

**Actions contextuelles (selon statut + rôle) :**
- `Modifier` (si DRAFT + claims:write) → `/claims/[id]/edit`
- `Analyser` (si DRAFT) → `POST /claims/{id}/submit`
- `Prendre une décision` (si OPEN + audit:decide) → `/audit/[analysis_id]`
- `Escalader` (si OPEN + escalations:create) → modal escalade

---

### PAGE 08 — Détail sinistre — Documents & OCR (`/claims/[id]/documents`)

**Rôle :** Gestion documentaire complète d'un sinistre.

**Layout :** Galerie à gauche + panneau détail à droite.

**Fonctionnalités :**
- Upload nouveaux documents (drag & drop, si DRAFT)
- Prévisualisation PDF/image en modal
- Résultats OCR : `score_confiance`, `montant_extrait`, `flag_altere`
- Badge "Document potentiellement altéré" si `flag_altere=true` (warning orange)
- Déclencher analyse OCR sur un document

**Endpoints :**
- `GET /claims/{id}/documents`
- `POST /claims/{id}/documents`
- `GET /claims/{id}/documents/{doc_id}`
- `GET /claims/{id}/documents/{doc_id}/download`
- `DELETE /claims/{id}/documents/{doc_id}` (ADM seulement)
- `POST /claims/{id}/ocr/run`
- `GET /claims/{id}/ocr`

---

### PAGE 09 — File d'audit (`/audit`)

**Rôle :** Vue principale de l'auditeur et du gestionnaire. Analyses en attente de décision humaine.

**Layout :** Tableau paginé + filtres + stats en haut.

**KPIs de la page :**
```
[En attente: 34]  [Escaladées: 7]  [Décidées aujourd'hui: 12]  [Taux confirmation: 61%]
```

**Filtres :**
- Branch (SANTÉ / AUTO)
- `decision_status` : PENDING / CONFIRMED / REJECTED / ESCALATED
- Score minimum (slider)
- Période

**Colonnes :**
- ID Sinistre (lien)
- Branche pill
- Score + jauge mini
- Catégorie RCA principale
- Date d'analyse
- Décision actuelle / badge
- `Décider` → `/audit/[analysis_id]`

**Endpoints :**
- `GET /audit/` (tous filtres)
- `GET /audit/stats`

---

### PAGE 10 — Décision HITL (`/audit/[analysis_id]`)

**Rôle :** Page centrale du workflow humain. Le gestionnaire/auditeur voit TOUT avant de décider.

**Layout :** 3 colonnes — infos sinistre | analyse IA | décision.

**Colonne 1 — Contexte sinistre**
- Résumé sinistre (branche, assuré pseudonymisé, montant, date)
- Lignes de détail avec écarts mercuriale surlignés
- Documents joints (miniatures cliquables)

**Colonne 2 — Résultat IA**
- **Score gauge animé** (arc SVG, 0–1, zones colorées)
- **Top 3 SHAP** : barres horizontales avec nom de feature + valeur + direction
- **Catégorie RCA** : badge "Fraude Intentionnelle / Upcoding" avec confiance
- **Narration LLM** : texte explicatif en français généré par Mistral 7B
  - Affiché en carte avec fond légèrement différent
  - Icône "Généré par IA" clairement visible
- Lien `Voir toutes les valeurs SHAP →` `/audit/[id]/shap`

**Colonne 3 — Décision**
- Trois boutons distincts :
  - `✗ Rejeter` (vert — non fraude) — demande un motif (textarea optionnel)
  - `✓ Confirmer fraude` (rouge) — demande un motif (textarea obligatoire)
  - `↑ Escalader à un auditeur` (violet) — demande motif + sélecteur auditeur (G seulement)
- Confirmation modale avant soumission
- Historique des décisions précédentes sur cette analyse (si redécision)

**Endpoints :**
- `GET /audit/{analysis_id}` — données complètes
- `GET /claims/{claim_id}` — contexte sinistre
- `GET /claims/{claim_id}/lines`
- `GET /claims/{claim_id}/documents`
- `POST /audit/{analysis_id}/decision` — enregistrer décision
- `GET /audit/{analysis_id}/decisions` — historique
- `POST /escalations/` — créer escalade (G)

---

### PAGE 11 — SHAP Détail (`/audit/[analysis_id]/shap`)

**Rôle :** Visualisation technique complète des valeurs SHAP pour les auditeurs et experts.

**Layout :** Graphique waterfall en haut + tableau complet en bas.

**Graphique waterfall :**
- Barres horizontales pour TOUTES les features
- Couleur positive (bleu) = augmente le score anomalie
- Couleur négative (or) = réduit le score anomalie
- Valeur SHAP en mono à droite de chaque barre
- Valeur de la feature en parenthèse sous le nom

**Tableau complet :**
- Feature name | Feature value | SHAP value | Direction

**Endpoint :** `GET /audit/{analysis_id}/shap`

---

### PAGE 12 — Liste escalades (`/escalations`)

**Rôle :** Vue des auditeurs — file d'attente des cas escaladés.

**Sous-onglets :**
- `En attente` (non assignées) — `GET /escalations/pending`
- `Mes escalades` (assignées à moi)
- `Toutes` (ADM seulement)

**Colonnes :**
- ID Escalade | Analyse liée | Motif | Créé par | Assigné à | Statut | Date | Actions

**Actions :**
- `S'assigner` → `PATCH /escalations/{id}/assign`
- `Résoudre` → modal avec note → `PATCH /escalations/{id}/resolve`

**Endpoints :**
- `GET /escalations/`
- `GET /escalations/pending`

---

### PAGE 13 — Détail escalade (`/escalations/[id]`)

**Fonctionnalités :**
- Contexte complet (sinistre + analyse + décision précédente)
- Motif de l'escalade
- Note de résolution (si résolue)
- Formulaire de résolution

**Endpoints :**
- `GET /escalations/{id}`
- `PATCH /escalations/{id}/assign`
- `PATCH /escalations/{id}/resolve`

---

### PAGE 14 — Graphe de fraude (`/fraud/graph`)

**Rôle :** Visualisation des communautés suspectes détectées par l'algorithme Louvain [Blondel2008].

**Layout :** Panneau gauche (liste communautés) + zone centrale (graphe interactif) + panneau droit (détail sélection).

**Panneau gauche — liste communautés :**
- Filtres : branche, is_suspicious, taille minimum
- Tableau : ID | Taille | Densité | Score suspicion | Raison
- Clic → sélectionne dans le graphe

**Zone centrale — graphe interactif :**
- Rendu D3.js ou Sigma.js (force-directed layout)
- Nœuds colorés par type (assuré = bleu, praticien = or, garage = vert)
- Arêtes d'épaisseur proportionnelle au nombre de sinistres liés
- Nœuds centraux (`is_central=true`) mis en avant (plus grands)
- Zoom / pan / sélection

**Panneau droit — détail sélection :**
- Si communauté sélectionnée : densité, modularité, suspicion_score, raison
- Si nœud sélectionné : type, hash, node_score, nombre de liens

**Endpoints :**
- `GET /graph/communities` (filtres)
- `GET /graph/communities/{id}`
- `GET /graph/communities/{id}/members`

---

### PAGE 15 — Détail communauté (`/fraud/graph/[community_id]`)

**Rôle :** Analyse approfondie d'une communauté suspecte spécifique.

**Layout :** En-tête + métriques + liste membres + sinistres liés.

**Métriques :**
- Suspicion score (grande jauge)
- Densité du graphe (progress bar)
- Modularité (valeur numérique)
- Raison (texte)

**Tableau membres :**
- Type nœud | Hash pseudonymisé | Score nœud | Rôle central | Nombre sinistres

**Endpoints :**
- `GET /graph/communities/{id}`
- `GET /graph/communities/{id}/members`

---

### PAGE 16 — Analytiques SHAP (`/fraud/analytics`)

**Rôle :** Compréhension des drivers de fraude — quelles features expliquent le plus les anomalies.

**Layout :** Sélecteur de branche en haut + 3 graphiques.

**Graphique 1 — Top 10 features globales**
- Bar chart horizontal (Recharts)
- Valeur SHAP moyenne par feature
- Période configurable (30j / 90j / 1an)

**Graphique 2 — Comparaison SANTÉ vs AUTO**
- Side-by-side bar chart
- Les mêmes features sur les deux branches pour comparer

**Graphique 3 — Évolution temporelle top 3**
- Line chart, une ligne par feature
- Montre si les patterns de fraude évoluent

**Endpoints :**
- `GET /analytics/shap/top-features`
- `GET /analytics/shap/top-features/{branch}`

---

### PAGE 17 — Distribution RCA (`/fraud/rca`)

**Rôle :** Comprendre quels types de fraude sont détectés.

**Layout :** Pie chart principal + tableau de détail.

**Graphiques :**
- Donut chart : répartition par catégorie RCA principale
- Bar chart : répartition par sous-catégorie
- Top 5 règles les plus déclenchées

**Endpoints :**
- `GET /analytics/rca/distribution`
- `GET /modules/rca-rules/stats`

---

### PAGE 18 — Catalogue des modèles (`/ml/models`)

**Rôle :** Vue de gouvernance ML — tous les modèles entraînés.

**Layout :** Filtres + tableau + bouton "Déployer" (ADM).

**Filtres :** branche, algorithme (IF / LOF / SVM)

**Colonnes :**
- ID | Branche | Algorithme | Version | F1 | AUC | MCC | FPR | Statut | Déployé en prod

**Statut :** Badge `EN PRODUCTION` (or) / `ARCHIVÉ` (gris) / `CANDIDAT` (bleu)

**Actions :**
- `Voir fiche` → `/ml/models/[id]`
- `Déployer` (ADM seulement) → modal confirmation → `POST /models/deploy`

**Endpoints :**
- `GET /models/`
- `GET /models/branch/{branch}/current`
- `POST /models/deploy` (ADM)

---

### PAGE 19 — Fiche modèle (`/ml/models/[model_id]`)

**Rôle :** Model card complète.

**Layout :** En-tête + métriques + features + historique déploiements.

**Sections :**

**Métriques** :
- Precision | Recall | F1 | AUC-ROC | Average Precision | FPR | MCC
- Visualisées comme jauge ou progress bar avec seuil cible indiqué

**Features** :
- Liste des features utilisées avec type et importance relative

**Courbes** (si disponible) :
- ROC Curve (Recharts AreaChart)
- Precision-Recall Curve

**Paramètres** :
- Contamination | Algorithme | `random_state` | Version

**Historique déploiements** :
- Timeline des fois où ce modèle a été actif

**Endpoints :**
- `GET /models/{model_id}`
- `GET /models/deployments`

---

### PAGE 20 — Comparaison modèles (`/ml/models/compare`)

**Rôle :** Tableau comparatif — c'est la page qui valide empiriquement H0 du mémoire.

**Layout :** Sélecteur de modèles à comparer + tableau + graphique radar.

**Tableau comparatif :**
```
                  │ M_sante (IF) │ M_auto (IF) │ M_makora (MAKORA) │
──────────────────┼──────────────┼─────────────┼───────────────────┤
F1 (Santé)        │    0.76      │    0.41     │       0.74        │
F1 (Auto)         │    0.38      │    0.79     │       0.75        │
AUC-ROC           │    0.84      │    0.87     │       0.86        │
MCC               │    0.71      │    0.73     │       0.72        │
Δ vs spécialisé   │     ref      │    ref      │    [-2%, +2%]     │
```

**Graphique radar :** 5 axes — F1, AUC, MCC, 1-FPR, AP

**Endpoint :**
- `GET /analytics/models/performance`

---

### PAGE 21 — Dashboard Drift (`/ml/drift`)

**Rôle :** Surveillance de la dérive des données — toutes branches.

**Layout :** Statuts globaux + tableau branches.

**Statuts globaux :**
```
[SANTÉ : ● STABLE]   [AUTO : ● WARNING — PSI 0.14]
```

**Tableau par branche :**
- Branche | PSI Global | Statut | Nb features dégradées | Dernier rapport | Actions

**Actions :**
- `Voir détail` → `/ml/drift/[branch]`
- `Déclencher calcul` (E, ADM) → `POST /drift/run/{branch}`

**Endpoints :**
- `GET /drift/status`

---

### PAGE 22 — Drift par branche (`/ml/drift/[branch]`)

**Rôle :** Analyse détaillée de la dérive pour une branche.

**Layout :** En-tête + métriques + tableau features + historique.

**En-tête :**
- Branch pill + statut global + PSI global + recommandation

**Tableau features :**
- Feature name | PSI | Statut (STABLE/WARNING/CRITICAL) | Évolution (sparkline)
- Tri par PSI décroissant
- Features CRITICAL surlignées en rouge

**Historique (line chart) :**
- PSI global dans le temps (30 derniers rapports)

**Bouton :** `Demander un réentraînement` → `POST /retraining/`

**Endpoints :**
- `GET /drift/status/{branch}`
- `GET /drift/history/{branch}`

---

### PAGE 23 — Détail rapport drift (`/ml/drift/[branch]/[report_id]`)

**Fonctionnalités :**
- PSI de CHAQUE feature à la date de ce rapport
- Comparaison avec rapport précédent
- Recommandation affichée

**Endpoint :**
- `GET /drift/reports/{report_id}`

---

### PAGE 24 — Demandes de réentraînement (`/ml/retraining`)

**Rôle :** Cycle de vie des demandes de réentraînement modèle.

**Onglets :**
- `En attente` (PENDING) | `Approuvées` (APPROVED) | `Terminées` (DONE) | `Rejetées` (REJECTED)

**Colonnes :**
- ID | Branche | Motif | Lié à drift report | Demandé par | Date | Statut | Actions

**Actions (ADM) :**
- `Approuver` → `PATCH /retraining/{id}/approve`
- `Rejeter` → `PATCH /retraining/{id}/reject` + motif
- `Marquer terminé` → `PATCH /retraining/{id}/complete` + lier nouveau modèle

**Bouton :** `+ Nouvelle demande` (E, ADM) → `/ml/retraining/new`

**Endpoints :**
- `GET /retraining/`
- `PATCH /retraining/{id}/approve`
- `PATCH /retraining/{id}/reject`
- `PATCH /retraining/{id}/complete`

---

### PAGE 25 — Nouvelle demande de réentraînement (`/ml/retraining/new`)

**Formulaire :**
- Branche (sélecteur)
- Motif (textarea obligatoire)
- Drift report lié (optionnel — autocomplete depuis `GET /drift/history/{branch}`)

**Endpoint :** `POST /retraining/`

---

### PAGE 26 — Modules actifs (`/config/modules`)

**Rôle :** Vue d'ensemble des plugins métiers chargés.

**Tableau :**
- Branche | Statut (LOADED/NOT_LOADED) | Version | Graph enabled | Dernier reload | Actions

**Actions (ADM) :**
- `Hot-reload` → `POST /modules/{branch}/reload`
- `Voir config` → `/config/modules/[branch]`

**Endpoints :**
- `GET /modules/`

---

### PAGE 27 — Config YAML d'une branche (`/config/modules/[branch]`)

**Rôle :** Consultation et modification de la configuration YAML active.

**Layout :** Panneau gauche (config active) + panneau droit (historique snapshots).

**Panneau gauche :**
- Affichage JSON de la config parsée (readable)
- Champs éditables pour les seuils :
  - `contamination` (slider 0.01–0.30)
  - `anomaly_score_alert` (slider)
  - `anomaly_score_block` (slider, validation > alert)
- Bouton `Sauvegarder` → `PATCH /modules/{branch}/config`

**Panneau droit — Historique snapshots :**
- Tableau : ID | Hash | Date | `Activer` (rollback)
- `GET /modules/{branch}/configs`
- `POST /modules/{branch}/configs/{id}/activate` (rollback)

**Endpoints :**
- `GET /modules/{branch}`
- `GET /modules/{branch}/config`
- `PATCH /modules/{branch}/config` (ADM)
- `GET /modules/{branch}/configs`
- `GET /modules/{branch}/configs/{id}`
- `POST /modules/{branch}/configs/{id}/activate` (ADM)

---

### PAGE 28 — Règles RCA d'une branche (`/config/modules/[branch]/rules`)

**Rôle :** Visualisation des règles RCA actives — compréhensible par les experts métiers.

**Layout :** Filtres + tableau des règles.

**Filtres :** catégorie, sous-catégorie, confiance minimum

**Tableau :**
- Rule ID | Catégorie | Sous-catégorie | Confiance base | Priorité | Logique (AND/OR) | Conditions

**Accordéon conditions :**
- Clic sur une ligne → expand les conditions de déclenchement (feature, opérateur, seuil)

**Endpoints :**
- `GET /modules/{branch}/rca-rules`
- `GET /modules/rca-rules/stats`

---

### PAGE 29 — Hub référentiels (`/config/referentiels`)

**Rôle :** Point d'entrée vers tous les référentiels métiers.

**Layout :** 4 cartes navigables.

```
┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
│   Praticiens      │  │    Garages        │  │   Mercuriale      │  │    Assurés        │
│   médicaux        │  │    réparateurs    │  │   ASAC/CIMA       │  │   (pseudonymisés) │
│   [1 234]         │  │    [456]          │  │    Active v3.2    │  │    via sinistres  │
│   → Voir liste    │  │    → Voir liste   │  │    → Consulter    │  │    → Via audit    │
└───────────────────┘  └───────────────────┘  └───────────────────┘  └───────────────────┘
```

---

### PAGE 30 — Liste des praticiens (`/config/referentiels/practitioners`)

**Rôle :** Surveillance des praticiens — repérer les prestataires à fort ratio de fraude.

**Filtres :** pays, spécialité, agrément CIMA, ratio prix minimum

**Colonnes :**
- ID | Spécialité | Pays | Agrément CIMA | Ratio prix moyen | Nb sinistres | Score suspicion implicite

**Indicateur de risque :** ratio_prix_moyen coloré (vert < 1.1, orange 1.1–1.3, rouge > 1.3)

**Endpoints :**
- `GET /referentiels/practitioners`

---

### PAGE 31 — Fiche praticien (`/config/referentiels/practitioners/[id]`)

**Rôle :** Profil complet d'un praticien avec historique sinistres.

**Sections :**
- Informations (spécialité, pays, agrément)
- Indicateurs : ratio_prix_moyen, nb_sinistres_total
- Historique sinistres (tableau paginé)

**Endpoints :**
- `GET /referentiels/practitioners/{id}`
- `GET /referentiels/practitioners/{id}/claims`

---

### PAGE 32 — Liste des garages (`/config/referentiels/garages`)

**Rôle :** Surveillance des garages réparateurs (branche Auto).

**Colonnes :**
- ID | Type garage | Ville | Agrément CIMA | Ratio devis moyen | Nb sinistres

**Endpoints :**
- `GET /referentiels/garages`

---

### PAGE 33 — Fiche garage (`/config/referentiels/garages/[id]`)

**Endpoints :**
- `GET /referentiels/garages/{id}`
- `GET /referentiels/garages/{id}/claims`

---

### PAGE 34 — Mercuriales ASAC/CIMA (`/config/referentiels/prices`)

**Rôle :** Consultation des prix de référence — outil quotidien du gestionnaire et de l'auditeur.

**Layout :** Sélecteur de branche + recherche par code acte + tableau.

**Recherche :** code acte ASAC (Santé) ou code poste (Auto)

**Colonnes :**
- Code acte | Libellé | Prix de référence (XAF) | Date vigueur | Version mercuriale

**Bouton (ADM, E) :** `Importer nouvelle mercuriale` → upload YAML/CSV → `POST /referentiels/prices`

**Endpoints :**
- `GET /referentiels/prices/{branch}`
- `GET /referentiels/prices/{branch}/{code_acte}`
- `POST /referentiels/prices` (ADM, E)

---

### PAGE 35 — Hub rapports (`/reports`)

**Rôle :** Génération et téléchargement de rapports exports.

**Layout :** Formulaire de génération + liste exports précédents.

**Formulaire de génération :**
- Type de rapport :
  - `audit_decisions` — décisions HITL sur une période
  - `anomaly_summary` — résumé des anomalies détectées
  - `drift_history` — historique drift
  - `community_fraud` — rapport fraude en réseau
- Format : CSV / XLSX / JSON
- Période (date_from / date_to)
- Branche (optionnel — toutes ou spécifique)

**Historique exports :**
- Tableau : ID | Type | Format | Statut (PENDING/READY/FAILED) | Date | Télécharger

**Endpoints :**
- `POST /reports/export`
- `GET /reports/exports/{export_id}`
- `GET /reports/exports`
- `GET /reports/stats/global`
- `GET /reports/stats/{branch}`

---

### PAGE 36 — Gestion des utilisateurs (`/admin/users`)

**Rôle :** Administration — CRUD utilisateurs.

**Tableau :**
- Avatar | Nom | Username | Email | Rôles (pills) | Statut | Dernière connexion | Actions

**Actions :**
- `Voir profil` → `/admin/users/[id]`
- `Désactiver` → `DELETE /users/{id}` (soft)
- `Réinitialiser mdp` → `PATCH /users/{id}/password`

**Bouton :** `+ Créer un utilisateur` → modal formulaire

**Filtres :** is_active, rôle, recherche

**Endpoints :**
- `GET /users/`
- `POST /users/`
- `PATCH /users/{id}`
- `DELETE /users/{id}`
- `POST /users/{id}/reactivate`
- `POST /users/{id}/roles`
- `DELETE /users/{id}/roles/{role_id}`

---

### PAGE 37 — Profil utilisateur admin (`/admin/users/[id]`)

**Sections :**
- Informations personnelles (éditable)
- Rôles assignés (gérer depuis ici)
- Sessions actives
- Historique activité (depuis `audit_logs`)

**Endpoints :**
- `GET /users/{id}`
- `PATCH /users/{id}`
- `PATCH /users/{id}/password`
- `POST /users/{id}/roles`
- `DELETE /users/{id}/roles/{role_id}`

---

### PAGE 38 — Rôles et permissions (`/admin/roles`)

**Rôle :** Lecture seule en V1 — visualiser les rôles et leurs permissions.

**Layout :** 4 cartes — une par rôle.

**Chaque carte :**
- Nom du rôle + description
- Liste des permissions groupées par domaine (IAM / Claims / Audit / ML / Admin)
- Nombre d'utilisateurs ayant ce rôle

**Endpoints :**
- `GET /roles/`
- `GET /roles/{role_id}`
- `GET /roles/permissions`

---

### PAGE 39 — État du système (`/admin/system`)

**Rôle :** Monitoring technique pour l'administrateur.

**Layout :** Grille de statuts services + journal d'activité.

**Statuts services :**
```
[API FastAPI]      ● UP — 99.8% uptime
[Ollama (Mistral)] ● UP — Mistral 7B chargé
[PostgreSQL]       ● UP — latency 12ms
[Redis/Celery]     ● UP — 0 tâches en file
[Modèles ML]       ● SANTÉ v1.2 actif | ● AUTO v1.0 actif
```

**Configuration branches (table éditable) :**
- Branche | Contamination | Score alert | Score block | Statut | Actions (`PATCH /admin/branches/{code}`)
- Toggle activer/désactiver branche

**Journal d'activité système :**
- Tableau : User | Action | Resource | Date
- Filtres : user, action, resource, date

**Endpoints :**
- `GET /admin/system`
- `GET /admin/branches`
- `GET /admin/branches/{code}`
- `PATCH /admin/branches/{code}`
- `PATCH /admin/branches/{code}/toggle`
- `GET /admin/activity-log`
- `GET /health`

---

### PAGE 40 — Mon profil (`/profile`)

**Sections :**
- Informations personnelles (nom, email) — `PATCH /auth/me`
- Mes rôles (lecture seule)
- Changer mon mot de passe — `POST /auth/change-password`

**Endpoints :**
- `GET /auth/me`
- `PATCH /auth/me`
- `POST /auth/change-password`

---

### PAGE 41 — Sécurité — Sessions (`/profile/security`)

**Rôle :** Visualiser et révoquer les sessions actives.

**Tableau :**
- IP | User-Agent | Créée le | Expire le | `Révoquer`

**Endpoints :**
- `GET /auth/sessions`
- `DELETE /auth/sessions/{session_id}`

---

### PAGE 42 — Historique des runs d'analyse (`/claims/analyses`)

**Rôle :** Vue macroscopique sur les sessions d'analyse batch.

**Colonnes :**
- Run ID | Branche | Nb dossiers | Nb anomalies | Taux anomalie | Date | Statut

**Lien :** vers `/fraud/graph/[run_id]` pour voir les communautés d'un run

**Endpoints :**
- `GET /analyze/runs`
- `GET /analyze/runs/{run_id}`

---

## 7. MAPPING COMPLET ENDPOINTS ↔ PAGES

### 7.1 Vérification couverture complète — 117 endpoints

| # | Endpoint | Page(s) qui le consomme(nt) |
|---|---|---|
| 1 | POST /auth/login | `/login` |
| 2 | POST /auth/logout | `<UserMenu>` (navbar) |
| 3 | POST /auth/refresh | `apiClient` (intercepteur auto) |
| 4 | POST /auth/forgot-password | `/forgot-password` |
| 5 | POST /auth/reset-password | `/reset-password` |
| 6 | POST /auth/change-password | `/profile` |
| 7 | GET /auth/me | `<AppShell>` (layout global) |
| 8 | PATCH /auth/me | `/profile` |
| 9 | GET /auth/sessions | `/profile/security` |
| 10 | DELETE /auth/sessions/{id} | `/profile/security` |
| 11 | GET /users/ | `/admin/users` |
| 12 | POST /users/ | `/admin/users` (modal) |
| 13 | GET /users/{id} | `/admin/users/[id]` |
| 14 | PATCH /users/{id} | `/admin/users/[id]` |
| 15 | DELETE /users/{id} | `/admin/users` |
| 16 | POST /users/{id}/reactivate | `/admin/users/[id]` |
| 17 | PATCH /users/{id}/password | `/admin/users/[id]` |
| 18 | POST /users/{id}/roles | `/admin/users/[id]` |
| 19 | DELETE /users/{id}/roles/{role_id} | `/admin/users/[id]` |
| 20 | GET /roles/ | `/admin/roles` |
| 21 | GET /roles/{role_id} | `/admin/roles` |
| 22 | GET /roles/permissions | `/admin/roles` |
| 23 | GET /claims/ | `/claims`, `/dashboard` |
| 24 | POST /claims/ | `/claims/new` |
| 25 | GET /claims/{id} | `/claims/[id]`, `/audit/[id]` |
| 26 | PATCH /claims/{id} | `/claims/[id]/edit` |
| 27 | POST /claims/{id}/submit | `/claims/[id]`, `/claims` |
| 28 | GET /claims/{id}/lines | `/claims/[id]`, `/audit/[id]` |
| 29 | POST /claims/{id}/lines | `/claims/new`, `/claims/[id]/lines` |
| 30 | PATCH /claims/{id}/lines/{line_id} | `/claims/[id]/lines` |
| 31 | DELETE /claims/{id}/lines/{line_id} | `/claims/[id]/lines` |
| 32 | GET /claims/{id}/documents | `/claims/[id]/documents`, `/audit/[id]` |
| 33 | POST /claims/{id}/documents | `/claims/[id]/documents`, `/claims/new` |
| 34 | GET /claims/{id}/documents/{doc_id} | `/claims/[id]/documents` |
| 35 | GET /claims/{id}/documents/{doc_id}/download | `/claims/[id]/documents` |
| 36 | DELETE /claims/{id}/documents/{doc_id} | `/claims/[id]/documents` |
| 37 | POST /claims/{id}/ocr/run | `/claims/[id]/documents` |
| 38 | GET /claims/{id}/ocr | `/claims/[id]/documents` |
| 39 | GET /claims/{id}/analyses | `/claims/[id]` (onglet Historique) |
| 40 | POST /analyze/ | usage interne pipeline |
| 41 | POST /analyze/upload | usage interne pipeline |
| 42 | GET /analyze/runs/{run_id} | `/claims/analyses` |
| 43 | GET /analyze/runs | `/claims/analyses` |
| 44 | GET /audit/ | `/audit` |
| 45 | GET /audit/{analysis_id} | `/audit/[id]` |
| 46 | POST /audit/{analysis_id}/decision | `/audit/[id]` |
| 47 | GET /audit/{analysis_id}/decisions | `/audit/[id]` |
| 48 | GET /audit/{analysis_id}/shap | `/audit/[id]/shap` |
| 49 | GET /audit/stats | `/audit`, `/dashboard` |
| 50 | POST /escalations/ | `/audit/[id]` (modal) |
| 51 | GET /escalations/ | `/escalations` |
| 52 | GET /escalations/{id} | `/escalations/[id]` |
| 53 | PATCH /escalations/{id}/assign | `/escalations`, `/escalations/[id]` |
| 54 | PATCH /escalations/{id}/resolve | `/escalations/[id]` |
| 55 | GET /escalations/pending | `/escalations`, `/dashboard`, navbar |
| 56 | GET /graph/communities | `/fraud/graph` |
| 57 | GET /graph/communities/{id} | `/fraud/graph/[id]` |
| 58 | GET /graph/communities/{id}/members | `/fraud/graph/[id]` |
| 59 | GET /graph/runs/{run_id}/communities | `/claims/analyses` |
| 60 | GET /models/ | `/ml/models` |
| 61 | GET /models/{model_id} | `/ml/models/[id]` |
| 62 | POST /models/register | usage interne post-training |
| 63 | GET /models/branch/{branch}/history | `/ml/models/[id]` |
| 64 | GET /models/branch/{branch}/current | `/ml/models`, `/dashboard` |
| 65 | POST /models/deploy | `/ml/models` (ADM) |
| 66 | GET /models/deployments | `/ml/models/[id]` |
| 67 | GET /drift/status | `/ml/drift`, `/dashboard`, navbar |
| 68 | GET /drift/status/{branch} | `/ml/drift/[branch]` |
| 69 | GET /drift/history/{branch} | `/ml/drift/[branch]` |
| 70 | GET /drift/reports/{report_id} | `/ml/drift/[branch]/[report_id]` |
| 71 | POST /drift/run/{branch} | `/ml/drift` |
| 72 | POST /retraining/ | `/ml/retraining/new` |
| 73 | GET /retraining/ | `/ml/retraining` |
| 74 | GET /retraining/{id} | `/ml/retraining/[id]` |
| 75 | PATCH /retraining/{id}/approve | `/ml/retraining` (ADM) |
| 76 | PATCH /retraining/{id}/reject | `/ml/retraining` (ADM) |
| 77 | PATCH /retraining/{id}/complete | `/ml/retraining` (ADM) |
| 78 | GET /modules/ | `/config/modules`, `/dashboard`, navbar |
| 79 | GET /modules/{branch} | `/config/modules/[branch]` |
| 80 | POST /modules/{branch}/reload | `/config/modules` |
| 81 | GET /modules/{branch}/config | `/config/modules/[branch]` |
| 82 | PATCH /modules/{branch}/config | `/config/modules/[branch]` |
| 83 | GET /modules/{branch}/configs | `/config/modules/[branch]` |
| 84 | GET /modules/{branch}/configs/{id} | `/config/modules/[branch]` |
| 85 | POST /modules/{branch}/configs/{id}/activate | `/config/modules/[branch]` |
| 86 | GET /modules/{branch}/rca-rules | `/config/modules/[branch]/rules` |
| 87 | GET /modules/rca-rules/stats | `/fraud/rca` |
| 88 | GET /referentiels/practitioners | `/config/referentiels/practitioners` |
| 89 | GET /referentiels/practitioners/{id} | `/config/referentiels/practitioners/[id]` |
| 90 | GET /referentiels/practitioners/{id}/claims | `/config/referentiels/practitioners/[id]` |
| 91 | GET /referentiels/garages | `/config/referentiels/garages` |
| 92 | GET /referentiels/garages/{id} | `/config/referentiels/garages/[id]` |
| 93 | GET /referentiels/garages/{id}/claims | `/config/referentiels/garages/[id]` |
| 94 | GET /referentiels/prices/{branch} | `/config/referentiels/prices`, `/claims/new` |
| 95 | GET /referentiels/prices/{branch}/{code} | `/config/referentiels/prices` |
| 96 | POST /referentiels/prices | `/config/referentiels/prices` |
| 97 | GET /referentiels/insureds/{hash} | `/audit/[id]` (contexte) |
| 98 | GET /referentiels/insureds/{hash}/claims | `/audit/[id]` |
| 99 | GET /referentiels/employers/{id} | `/config/referentiels` |
| 100 | GET /referentiels/employers/{id}/insureds | `/config/referentiels` |
| 101 | GET /analytics/dashboard | `/dashboard` |
| 102 | GET /analytics/shap/top-features | `/fraud/analytics` |
| 103 | GET /analytics/shap/top-features/{branch} | `/fraud/analytics` |
| 104 | GET /analytics/rca/distribution | `/fraud/rca` |
| 105 | GET /analytics/models/performance | `/ml/models/compare` |
| 106 | POST /reports/export | `/reports` |
| 107 | GET /reports/exports/{id} | `/reports` |
| 108 | GET /reports/exports | `/reports` |
| 109 | GET /reports/stats/global | `/dashboard`, `/reports` |
| 110 | GET /reports/stats/{branch} | `/reports` |
| 111 | GET /admin/branches | `/admin/system` |
| 112 | GET /admin/branches/{code} | `/admin/system` |
| 113 | PATCH /admin/branches/{code} | `/admin/system` |
| 114 | PATCH /admin/branches/{code}/toggle | `/admin/system` |
| 115 | GET /admin/system | `/admin/system` |
| 116 | GET /admin/activity-log | `/admin/system` |
| 117 | GET /health | `/login`, navbar `<HealthDot>` |

**✅ Couverture : 117/117 endpoints consommés (100%)**

---

## 8. ARCHITECTURE DU CODE NEXT.JS

### 8.1 Choix structurants

| Décision | Choix | Justification |
|---|---|---|
| Router | **App Router** (Next.js 14) | Server Components, layouts imbriqués, meilleur pour l'auth |
| Fetching | **TanStack Query v5** | Cache, invalidation, loading/error states automatiques |
| State global | **Zustand** | Léger, sans boilerplate, adapté à l'auth + branch selector |
| UI Components | **Shadcn/ui** | Accessible, customisable, pas de lock-in |
| Forms | **React Hook Form + Zod** | Validation typée, performances |
| Charts | **Recharts** | Compatible React, SSR-safe |
| Graphe | **D3.js** (force-directed) | Seule lib suffisamment flexible pour le graphe de fraude |
| HTTP Client | **Axios** (avec intercepteurs) | Gestion centralisée des tokens + refresh |
| Notifications | **Sonner** (toasts) | Léger, beau, compatible Shadcn |
| Icons | **Lucide React** | Cohérent avec Shadcn |

### 8.2 Règle des 500 lignes

**Chaque fichier DOIT respecter ≤ 500 lignes.** Stratégies de découpage :
- Une page complexe → `page.tsx` (orchestration) + composants dans `/components/features/`
- Un service → découpage par domaine fonctionnel
- Un type complexe → découpage en fichiers thématiques

---

## 9. STRUCTURE DES DOSSIERS

```
frontend/
├── src/
│   ├── app/                          ← Next.js App Router
│   │   ├── (auth)/                   ← Groupe sans layout principal
│   │   │   ├── login/
│   │   │   │   └── page.tsx
│   │   │   ├── forgot-password/
│   │   │   │   └── page.tsx
│   │   │   └── reset-password/
│   │   │       └── page.tsx
│   │   ├── (app)/                    ← Groupe avec layout principal (sidebar + navbar)
│   │   │   ├── layout.tsx            ← AppShell (vérifie auth, charge user)
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx
│   │   │   ├── claims/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── new/
│   │   │   │   │   └── page.tsx
│   │   │   │   ├── analyses/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx
│   │   │   │       ├── edit/
│   │   │   │       │   └── page.tsx
│   │   │   │       ├── documents/
│   │   │   │       │   └── page.tsx
│   │   │   │       └── lines/
│   │   │   │           └── page.tsx
│   │   │   ├── audit/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [analysis_id]/
│   │   │   │       ├── page.tsx
│   │   │   │       └── shap/
│   │   │   │           └── page.tsx
│   │   │   ├── escalations/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       └── page.tsx
│   │   │   ├── fraud/
│   │   │   │   ├── graph/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── [community_id]/
│   │   │   │   │       └── page.tsx
│   │   │   │   ├── analytics/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── rca/
│   │   │   │       └── page.tsx
│   │   │   ├── ml/
│   │   │   │   ├── models/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   ├── compare/
│   │   │   │   │   │   └── page.tsx
│   │   │   │   │   └── [model_id]/
│   │   │   │   │       └── page.tsx
│   │   │   │   ├── drift/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── [branch]/
│   │   │   │   │       ├── page.tsx
│   │   │   │   │       └── [report_id]/
│   │   │   │   │           └── page.tsx
│   │   │   │   └── retraining/
│   │   │   │       ├── page.tsx
│   │   │   │       ├── new/
│   │   │   │       │   └── page.tsx
│   │   │   │       └── [id]/
│   │   │   │           └── page.tsx
│   │   │   ├── config/
│   │   │   │   ├── modules/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── [branch]/
│   │   │   │   │       ├── page.tsx
│   │   │   │   │       └── rules/
│   │   │   │   │           └── page.tsx
│   │   │   │   └── referentiels/
│   │   │   │       ├── page.tsx
│   │   │   │       ├── practitioners/
│   │   │   │       │   ├── page.tsx
│   │   │   │       │   └── [id]/
│   │   │   │       │       └── page.tsx
│   │   │   │       ├── garages/
│   │   │   │       │   ├── page.tsx
│   │   │   │       │   └── [id]/
│   │   │   │       │       └── page.tsx
│   │   │   │       └── prices/
│   │   │   │           └── page.tsx
│   │   │   ├── reports/
│   │   │   │   └── page.tsx
│   │   │   ├── admin/
│   │   │   │   ├── users/
│   │   │   │   │   ├── page.tsx
│   │   │   │   │   └── [id]/
│   │   │   │   │       └── page.tsx
│   │   │   │   ├── roles/
│   │   │   │   │   └── page.tsx
│   │   │   │   └── system/
│   │   │   │       └── page.tsx
│   │   │   └── profile/
│   │   │       ├── page.tsx
│   │   │       └── security/
│   │   │           └── page.tsx
│   │   ├── unauthorized/
│   │   │   └── page.tsx
│   │   ├── not-found.tsx
│   │   ├── error.tsx
│   │   └── layout.tsx                ← Root layout (fonts, providers)
│   │
│   ├── components/
│   │   ├── ui/                       ← Shadcn/ui (jamais modifiés directement)
│   │   │   ├── button.tsx
│   │   │   ├── card.tsx
│   │   │   ├── dialog.tsx
│   │   │   ├── table.tsx
│   │   │   ├── badge.tsx
│   │   │   ├── input.tsx
│   │   │   ├── select.tsx
│   │   │   ├── tabs.tsx
│   │   │   ├── toast.tsx
│   │   │   └── ...
│   │   │
│   │   ├── layout/                   ← Composants de structure
│   │   │   ├── AppShell.tsx          ← Layout principal (sidebar + navbar + outlet)
│   │   │   ├── Navbar.tsx            ← Barre horizontale top
│   │   │   ├── Sidebar.tsx           ← Navigation latérale RBAC-aware
│   │   │   ├── SidebarItem.tsx       ← Item individuel sidebar
│   │   │   ├── BranchSelector.tsx    ← Sélecteur SANTÉ/AUTO
│   │   │   ├── NotificationBell.tsx  ← Cloche + dropdown
│   │   │   ├── UserMenu.tsx          ← Avatar + menu profil/logout
│   │   │   ├── HealthDot.tsx         ← Indicateur santé API
│   │   │   ├── GlobalSearch.tsx      ← Cmd+K search
│   │   │   └── PageHeader.tsx        ← En-tête de page avec breadcrumb
│   │   │
│   │   ├── features/                 ← Composants métiers réutilisables
│   │   │   ├── claims/
│   │   │   │   ├── ClaimsTable.tsx
│   │   │   │   ├── ClaimCard.tsx
│   │   │   │   ├── ClaimStatusBadge.tsx
│   │   │   │   ├── ClaimForm.tsx
│   │   │   │   ├── ClaimLineEditor.tsx
│   │   │   │   ├── ClaimLinesTable.tsx
│   │   │   │   ├── ClaimFilters.tsx
│   │   │   │   └── SubmitClaimButton.tsx
│   │   │   ├── analysis/
│   │   │   │   ├── AnalysisScoreGauge.tsx    ← Arc SVG animé
│   │   │   │   ├── AnalysisScoreBadge.tsx    ← Petit badge score
│   │   │   │   ├── ShapBarChart.tsx          ← Barres SHAP top 3
│   │   │   │   ├── ShapWaterfallChart.tsx    ← Waterfall SHAP complet
│   │   │   │   ├── RcaCategoryBadge.tsx
│   │   │   │   ├── LlmNarration.tsx          ← Carte narration IA
│   │   │   │   └── DecisionPanel.tsx         ← Panneau 3 boutons HITL
│   │   │   ├── documents/
│   │   │   │   ├── DocumentUploader.tsx      ← Drag & drop
│   │   │   │   ├── DocumentGallery.tsx
│   │   │   │   ├── DocumentCard.tsx
│   │   │   │   ├── OcrResultCard.tsx
│   │   │   │   └── DocumentViewer.tsx        ← Modal prévisualisation
│   │   │   ├── audit/
│   │   │   │   ├── AuditTable.tsx
│   │   │   │   ├── AuditFilters.tsx
│   │   │   │   ├── DecisionHistory.tsx
│   │   │   │   └── EscalationModal.tsx
│   │   │   ├── escalations/
│   │   │   │   ├── EscalationsTable.tsx
│   │   │   │   ├── EscalationCard.tsx
│   │   │   │   └── EscalationResolveForm.tsx
│   │   │   ├── graph/
│   │   │   │   ├── FraudGraphCanvas.tsx      ← D3.js force graph
│   │   │   │   ├── CommunityList.tsx
│   │   │   │   ├── CommunityCard.tsx
│   │   │   │   └── CommunityMembersTable.tsx
│   │   │   ├── models/
│   │   │   │   ├── ModelCatalogTable.tsx
│   │   │   │   ├── ModelMetricsCard.tsx
│   │   │   │   ├── ModelCompareTable.tsx
│   │   │   │   ├── ModelRadarChart.tsx
│   │   │   │   └── DeployModelModal.tsx
│   │   │   ├── drift/
│   │   │   │   ├── DriftStatusCard.tsx
│   │   │   │   ├── DriftFeatureTable.tsx
│   │   │   │   ├── DriftHistoryChart.tsx     ← Line chart PSI
│   │   │   │   └── PsiStatusBadge.tsx
│   │   │   ├── modules/
│   │   │   │   ├── ModuleStatusCard.tsx
│   │   │   │   ├── ModuleConfigForm.tsx
│   │   │   │   ├── ConfigSnapshotList.tsx
│   │   │   │   └── RcaRulesTable.tsx
│   │   │   ├── referentiels/
│   │   │   │   ├── PractitionerTable.tsx
│   │   │   │   ├── GarageTable.tsx
│   │   │   │   ├── PriceTable.tsx
│   │   │   │   └── RatioBadge.tsx
│   │   │   ├── analytics/
│   │   │   │   ├── ShapTopFeaturesChart.tsx
│   │   │   │   ├── ShapBranchCompareChart.tsx
│   │   │   │   ├── ShapTrendChart.tsx
│   │   │   │   └── RcaDistributionChart.tsx
│   │   │   ├── reports/
│   │   │   │   ├── ExportReportForm.tsx
│   │   │   │   └── ExportHistoryTable.tsx
│   │   │   └── admin/
│   │   │       ├── UserTable.tsx
│   │   │       ├── UserCreateModal.tsx
│   │   │       ├── RoleCard.tsx
│   │   │       ├── SystemStatusGrid.tsx
│   │   │       ├── BranchConfigTable.tsx
│   │   │       └── ActivityLogTable.tsx
│   │   │
│   │   └── common/                   ← Composants génériques
│   │       ├── DataTable.tsx         ← Table générique paginée + triable
│   │       ├── FilterBar.tsx         ← Barre de filtres générique
│   │       ├── KpiCard.tsx           ← Carte KPI dashboard
│   │       ├── LoadingSkeleton.tsx   ← Squelettes de chargement
│   │       ├── EmptyState.tsx        ← État vide illustré
│   │       ├── ErrorState.tsx        ← État erreur avec retry
│   │       ├── ConfirmDialog.tsx     ← Dialogue de confirmation générique
│   │       ├── Pagination.tsx        ← Contrôles pagination
│   │       ├── BranchPill.tsx        ← SANTÉ/AUTO pill réutilisable
│   │       ├── RiskBadge.tsx         ← Badge score risque (couleur)
│   │       ├── CurrencyDisplay.tsx   ← Formatage XAF
│   │       ├── DateDisplay.tsx       ← Formatage date DD/MM/YYYY
│   │       ├── CopyButton.tsx        ← Copier dans presse-papier
│   │       ├── JsonViewer.tsx        ← Affichage JSON lisible
│   │       └── PageBreadcrumb.tsx    ← Fil d'Ariane
│   │
│   ├── services/                     ← Couche appels API (axios)
│   │   ├── apiClient.ts              ← Instance axios + intercepteurs auth
│   │   ├── auth.service.ts           ← Endpoints /auth
│   │   ├── users.service.ts          ← Endpoints /users + /roles
│   │   ├── claims.service.ts         ← Endpoints /claims
│   │   ├── analyze.service.ts        ← Endpoints /analyze
│   │   ├── audit.service.ts          ← Endpoints /audit
│   │   ├── escalations.service.ts    ← Endpoints /escalations
│   │   ├── graph.service.ts          ← Endpoints /graph
│   │   ├── models.service.ts         ← Endpoints /models
│   │   ├── drift.service.ts          ← Endpoints /drift
│   │   ├── retraining.service.ts     ← Endpoints /retraining
│   │   ├── modules.service.ts        ← Endpoints /modules
│   │   ├── referentiels.service.ts   ← Endpoints /referentiels
│   │   ├── analytics.service.ts      ← Endpoints /analytics
│   │   ├── reports.service.ts        ← Endpoints /reports
│   │   ├── admin.service.ts          ← Endpoints /admin
│   │   └── health.service.ts         ← Endpoint /health
│   │
│   ├── hooks/                        ← React hooks personnalisés
│   │   ├── auth/
│   │   │   ├── useAuth.ts            ← Accès user courant + rôles
│   │   │   ├── useLogin.ts           ← Mutation login
│   │   │   ├── useLogout.ts          ← Mutation logout
│   │   │   └── usePermission.ts      ← hasPermission() hook
│   │   ├── claims/
│   │   │   ├── useClaims.ts          ← Query liste sinistres
│   │   │   ├── useClaim.ts           ← Query sinistre unique
│   │   │   ├── useCreateClaim.ts     ← Mutation créer
│   │   │   ├── useUpdateClaim.ts     ← Mutation modifier
│   │   │   ├── useSubmitClaim.ts     ← Mutation soumettre
│   │   │   ├── useClaimLines.ts      ← Query + mutations lignes
│   │   │   └── useClaimDocuments.ts  ← Query + mutations docs
│   │   ├── audit/
│   │   │   ├── useAuditQueue.ts      ← Query file d'audit
│   │   │   ├── useAnalysis.ts        ← Query analyse unique
│   │   │   ├── useDecision.ts        ← Mutation décision
│   │   │   └── useShapValues.ts      ← Query SHAP complet
│   │   ├── escalations/
│   │   │   ├── useEscalations.ts
│   │   │   ├── useEscalation.ts
│   │   │   ├── useCreateEscalation.ts
│   │   │   ├── useAssignEscalation.ts
│   │   │   └── useResolveEscalation.ts
│   │   ├── graph/
│   │   │   ├── useFraudCommunities.ts
│   │   │   ├── useCommunity.ts
│   │   │   └── useCommunityMembers.ts
│   │   ├── ml/
│   │   │   ├── useModels.ts
│   │   │   ├── useModel.ts
│   │   │   ├── useDeployModel.ts
│   │   │   ├── useDriftStatus.ts
│   │   │   ├── useDriftBranch.ts
│   │   │   ├── useDriftReport.ts
│   │   │   ├── useTriggerDrift.ts
│   │   │   ├── useRetrainingRequests.ts
│   │   │   └── useRetrainingActions.ts
│   │   ├── config/
│   │   │   ├── useModules.ts
│   │   │   ├── useModuleConfig.ts
│   │   │   ├── usePractitioners.ts
│   │   │   ├── useGarages.ts
│   │   │   └── useReferencePrices.ts
│   │   ├── analytics/
│   │   │   ├── useDashboardStats.ts
│   │   │   ├── useShapTopFeatures.ts
│   │   │   ├── useRcaDistribution.ts
│   │   │   └── useModelsPerformance.ts
│   │   ├── reports/
│   │   │   └── useExports.ts
│   │   ├── admin/
│   │   │   ├── useUsers.ts
│   │   │   ├── useUserActions.ts
│   │   │   ├── useRoles.ts
│   │   │   ├── useSystemStatus.ts
│   │   │   └── useBranchConfig.ts
│   │   └── common/
│   │       ├── usePagination.ts      ← État pagination réutilisable
│   │       ├── useFilters.ts         ← État filtres avec URL sync
│   │       ├── useDebounce.ts        ← Debounce pour recherche
│   │       ├── useLocalStorage.ts    ← Persistence locale
│   │       └── useHealthCheck.ts     ← Polling /health
│   │
│   ├── stores/                       ← Zustand stores
│   │   ├── authStore.ts              ← user, roles, tokens
│   │   ├── branchStore.ts            ← branche active SANTÉ/AUTO
│   │   ├── uiStore.ts                ← sidebar collapsed, theme
│   │   └── notificationStore.ts      ← notifications non lues
│   │
│   ├── types/                        ← Types TypeScript
│   │   ├── api/
│   │   │   ├── auth.types.ts
│   │   │   ├── claims.types.ts
│   │   │   ├── analysis.types.ts
│   │   │   ├── audit.types.ts
│   │   │   ├── escalation.types.ts
│   │   │   ├── graph.types.ts
│   │   │   ├── models.types.ts
│   │   │   ├── drift.types.ts
│   │   │   ├── retraining.types.ts
│   │   │   ├── modules.types.ts
│   │   │   ├── referentiels.types.ts
│   │   │   ├── analytics.types.ts
│   │   │   ├── reports.types.ts
│   │   │   └── admin.types.ts
│   │   ├── common.types.ts           ← PaginatedResponse, ApiError, etc.
│   │   └── rbac.types.ts             ← Role, Permission
│   │
│   ├── lib/
│   │   ├── rbac.ts                   ← hasPermission, ROLE_PERMISSIONS
│   │   ├── utils.ts                  ← cn(), formatXAF(), formatDate()
│   │   ├── constants.ts              ← BASE_URL, SCORE_THRESHOLDS, etc.
│   │   ├── queryClient.ts            ← Configuration TanStack Query
│   │   └── validators/               ← Schémas Zod par domaine
│   │       ├── auth.validators.ts
│   │       ├── claims.validators.ts
│   │       └── ...
│   │
│   ├── styles/
│   │   ├── globals.css               ← Variables CSS MAKORA
│   │   └── tokens.ts                 ← Design tokens TypeScript
│   │
│   └── middleware.ts                 ← Middleware Next.js (protection routes)
│
├── public/
│   ├── favicon.ico
│   └── logo.svg
├── tailwind.config.ts
├── next.config.ts
├── tsconfig.json
└── package.json
```

---

## 10. TYPES TYPESCRIPT FONDAMENTAUX

```typescript
// src/types/common.types.ts

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface ApiError {
  error: string;
  message: string;
  timestamp: string;
  request_id: string;
}

export type Branch = 'sante' | 'auto';
export type BranchDisplay = 'SANTÉ' | 'AUTO';

export interface SelectOption {
  value: string;
  label: string;
}
```

```typescript
// src/types/api/claims.types.ts

export type ClaimStatus = 'DRAFT' | 'SUBMITTED' | 'OPEN' | 'CLOSED';

export interface Claim {
  id: string;
  claim_reference: string;
  branch: Branch;
  insured_hash: string;
  contract_id: string;
  status: ClaimStatus;
  date_soin: string;
  montant_total: number;
  description?: string;
  is_anomaly: boolean | null;
  anomaly_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface ClaimLine {
  id: string;
  claim_id: string;
  code_acte: string;
  libelle: string;
  quantite: number;
  montant_unitaire: number;
  montant_total: number;
  prix_reference: number | null;
  ecart_mercuriale: number | null;
}

export interface ClaimDocument {
  id: string;
  claim_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;
  sha256_hash: string;
  uploaded_at: string;
}

export interface OcrExtraction {
  id: string;
  document_id: string;
  score_confiance: number;
  montant_extrait: number | null;
  flag_altere: boolean;
  extracted_text: string;
  processed_at: string;
}
```

```typescript
// src/types/api/analysis.types.ts

export type DecisionStatus = 'PENDING' | 'CONFIRMED' | 'REJECTED' | 'ESCALATED';

export interface Analysis {
  id: string;
  claim_id: string;
  run_id: string;
  branch: Branch;
  model_version_id: string;
  anomaly_score: number;
  is_anomaly: boolean;
  rca_category: string;
  rca_subcategory: string;
  rca_confidence: number;
  llm_narration: string | null;
  decision_status: DecisionStatus;
  shap_top3: ShapContribution[];
  created_at: string;
}

export interface ShapContribution {
  feature_name: string;
  feature_value: number | string;
  shap_value: number;
  direction: 'positive' | 'negative';
}

export interface Decision {
  id: string;
  analysis_id: string;
  decided_by: string;
  decision: 'CONFIRMED' | 'REJECTED' | 'ESCALATED';
  motif: string | null;
  created_at: string;
}
```

---

## 11. SERVICES API — ORGANISATION

```typescript
// src/services/apiClient.ts
// Règle : ce fichier ne dépasse pas 80 lignes

import axios from 'axios';
import { useAuthStore } from '@/stores/authStore';

export const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1',
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
});

// Intercepteur requête — injecte le token
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().accessToken;
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Intercepteur réponse — gère le refresh automatique
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refreshToken = useAuthStore.getState().refreshToken;
        const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken });
        useAuthStore.getState().setTokens(data.access_token, refreshToken);
        return apiClient(original);
      } catch {
        useAuthStore.getState().logout();
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);
```

```typescript
// src/services/claims.service.ts  (exemple de service structuré)

import { apiClient } from './apiClient';
import type { Claim, ClaimLine, ClaimDocument, OcrExtraction } from '@/types/api/claims.types';
import type { PaginatedResponse } from '@/types/common.types';

export interface ClaimsFilters {
  branch?: string;
  status?: string;
  is_anomaly?: boolean;
  score_min?: number;
  date_from?: string;
  date_to?: string;
  search?: string;
  page?: number;
  page_size?: number;
}

export const claimsService = {
  list: (filters: ClaimsFilters) =>
    apiClient.get<PaginatedResponse<Claim>>('/claims/', { params: filters }),

  get: (id: string) =>
    apiClient.get<Claim>(`/claims/${id}`),

  create: (data: Partial<Claim>) =>
    apiClient.post<Claim>('/claims/', data),

  update: (id: string, data: Partial<Claim>) =>
    apiClient.patch<Claim>(`/claims/${id}`, data),

  submit: (id: string) =>
    apiClient.post(`/claims/${id}/submit`),

  // --- Lignes ---
  getLines: (claimId: string) =>
    apiClient.get<ClaimLine[]>(`/claims/${claimId}/lines`),

  addLine: (claimId: string, data: Partial<ClaimLine>) =>
    apiClient.post<ClaimLine>(`/claims/${claimId}/lines`, data),

  updateLine: (claimId: string, lineId: string, data: Partial<ClaimLine>) =>
    apiClient.patch<ClaimLine>(`/claims/${claimId}/lines/${lineId}`, data),

  deleteLine: (claimId: string, lineId: string) =>
    apiClient.delete(`/claims/${claimId}/lines/${lineId}`),

  // --- Documents ---
  getDocuments: (claimId: string) =>
    apiClient.get<ClaimDocument[]>(`/claims/${claimId}/documents`),

  uploadDocument: (claimId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return apiClient.post<ClaimDocument>(`/claims/${claimId}/documents`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  downloadDocument: (claimId: string, docId: string) =>
    apiClient.get(`/claims/${claimId}/documents/${docId}/download`, { responseType: 'blob' }),

  deleteDocument: (claimId: string, docId: string) =>
    apiClient.delete(`/claims/${claimId}/documents/${docId}`),

  // --- OCR ---
  runOcr: (claimId: string, docId: string) =>
    apiClient.post(`/claims/${claimId}/ocr/run`, { document_id: docId }),

  getOcrResult: (claimId: string) =>
    apiClient.get<OcrExtraction[]>(`/claims/${claimId}/ocr`),
};
```

---

## 12. HOOKS PERSONNALISÉS — INVENTAIRE

```typescript
// src/hooks/claims/useClaims.ts  (exemple structurel)

import { useQuery, keepPreviousData } from '@tanstack/react-query';
import { claimsService, type ClaimsFilters } from '@/services/claims.service';

export const CLAIMS_KEYS = {
  all: ['claims'] as const,
  list: (filters: ClaimsFilters) => [...CLAIMS_KEYS.all, 'list', filters] as const,
  detail: (id: string) => [...CLAIMS_KEYS.all, 'detail', id] as const,
};

export function useClaims(filters: ClaimsFilters) {
  return useQuery({
    queryKey: CLAIMS_KEYS.list(filters),
    queryFn: () => claimsService.list(filters).then(r => r.data),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  });
}

export function useClaim(id: string) {
  return useQuery({
    queryKey: CLAIMS_KEYS.detail(id),
    queryFn: () => claimsService.get(id).then(r => r.data),
    enabled: !!id,
  });
}
```

```typescript
// src/hooks/auth/usePermission.ts

import { useAuthStore } from '@/stores/authStore';
import { hasPermission, type Permission } from '@/lib/rbac';

export function usePermission(permission: Permission): boolean {
  const roles = useAuthStore(state => state.roles);
  return hasPermission(roles, permission);
}

// Usage : const canDecide = usePermission('audit:decide');
```

---

## 13. COMPOSANTS RÉUTILISABLES — INVENTAIRE

### 13.1 `<DataTable>` — Le composant le plus réutilisé

```typescript
// src/components/common/DataTable.tsx
// Usage : chaque liste de l'application utilise ce composant

interface Column<T> {
  key: keyof T | string;
  header: string;
  render?: (row: T) => React.ReactNode;
  sortable?: boolean;
  width?: string;
}

interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  loading?: boolean;
  pagination?: {
    page: number;
    total: number;
    pageSize: number;
    onPageChange: (page: number) => void;
  };
  onRowClick?: (row: T) => void;
  emptyMessage?: string;
  rowClassName?: (row: T) => string;
}
```

### 13.2 `<AnalysisScoreGauge>` — Le composant signature

Jauge en arc SVG semi-circulaire. Zones colorées (vert/orange/rouge). Aiguille animée CSS. Score numérique au centre. Seuils configurables via props.

### 13.3 `<RiskBadge>` — Omniprésent

```typescript
interface RiskBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}
// Rendu : cercle coloré + score en mono
// Couleur auto selon SCORE_THRESHOLDS (constants.ts)
```

### 13.4 `<BranchPill>` — Présent sur chaque ligne de tableau

```typescript
interface BranchPillProps {
  branch: Branch;
  size?: 'sm' | 'md';
}
// SANTÉ → fond bleu-roi, texte blanc
// AUTO → fond doré, texte slate-900
```

### 13.5 `<DecisionBadge>` — File d'audit

```typescript
type DecisionStatus = 'PENDING' | 'CONFIRMED' | 'REJECTED' | 'ESCALATED';
// Mapping couleur + icône selon le statut
```

---

## 14. GESTION D'ÉTAT GLOBAL — ZUSTAND STORES

```typescript
// src/stores/authStore.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Role } from '@/types/rbac.types';

interface User {
  id: string;
  username: string;
  full_name: string;
  email: string;
}

interface AuthState {
  user: User | null;
  roles: Role[];
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;

  setUser: (user: User, roles: Role[]) => void;
  setTokens: (access: string, refresh: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      roles: [],
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      setUser: (user, roles) => set({ user, roles, isAuthenticated: true }),
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      logout: () => set({ user: null, roles: [], accessToken: null, refreshToken: null, isAuthenticated: false }),
    }),
    {
      name: 'makora-auth',
      partialize: (state) => ({
        refreshToken: state.refreshToken,  // seul le refresh token est persisté
      }),
    }
  )
);
```

```typescript
// src/stores/branchStore.ts

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Branch } from '@/types/common.types';

interface BranchState {
  activeBranch: Branch | 'all';
  setActiveBranch: (branch: Branch | 'all') => void;
}

export const useBranchStore = create<BranchState>()(
  persist(
    (set) => ({
      activeBranch: 'all',
      setActiveBranch: (activeBranch) => set({ activeBranch }),
    }),
    { name: 'makora-branch' }
  )
);
```

---

## 15. SYSTÈME DE ROUTAGE ET PROTECTION DES ROUTES

### 15.1 Middleware Next.js

```typescript
// src/middleware.ts

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const PUBLIC_ROUTES = ['/login', '/forgot-password', '/reset-password'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Routes publiques — toujours accessibles
  if (PUBLIC_ROUTES.some(r => pathname.startsWith(r))) {
    return NextResponse.next();
  }

  // Vérifier présence du token (le vrai RBAC est côté API + layout)
  const token = request.cookies.get('makora-auth-token');
  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
};
```

### 15.2 Guard composant RBAC

```typescript
// src/components/common/PermissionGuard.tsx

import { usePermission } from '@/hooks/auth/usePermission';
import type { Permission } from '@/lib/rbac';

interface Props {
  permission: Permission;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export function PermissionGuard({ permission, fallback = null, children }: Props) {
  const allowed = usePermission(permission);
  return allowed ? <>{children}</> : <>{fallback}</>;
}

// Usage :
// <PermissionGuard permission="audit:decide">
//   <DecisionPanel />
// </PermissionGuard>
```

### 15.3 Layout AppShell avec RBAC

```typescript
// src/app/(app)/layout.tsx — vérification auth + chargement user
// Ce layout entoure TOUTES les pages authentifiées

// Logique :
// 1. Appel GET /auth/me pour valider token et charger les rôles
// 2. Si erreur 401 → redirect /login
// 3. Stocker user + roles dans authStore
// 4. Rendre <AppShell> avec sidebar filtrée selon les rôles
```

### 15.4 Hiérarchie des protections

```
middleware.ts          ← Niveau 1 : token présent ou non
app/(app)/layout.tsx   ← Niveau 2 : token valide (GET /auth/me) + rôles chargés
<Sidebar>              ← Niveau 3 : items visibles selon rôle
<PermissionGuard>      ← Niveau 4 : composants/boutons visibles selon permission
API backend (RBAC)     ← Niveau 5 : validation finale — HTTP 403 si unauthorized
```

---

## 16. ONBOARDING ET PRISE EN MAIN

### 16.1 Premier login — Guided Tour

Au premier accès (détecté via `localStorage.getItem('makora-tour-done')`), un composant `<GuidedTour>` s'active. Il utilise une overlay avec un spotlight sur les éléments clés :

1. **Step 1** — "Bienvenue dans MAKORA. Voici le sélecteur de branche : cliquez ici pour basculer entre Santé et Auto."
2. **Step 2** — "La sidebar liste toutes vos fonctionnalités. Votre rôle determine ce que vous voyez."
3. **Step 3** — "Le dashboard résume l'activité en temps réel."
4. **Step 4** — (selon rôle G) "Commencez par créer un sinistre ici."
   - (selon rôle A) "Votre file d'audit vous attend ici."
   - (selon rôle E) "Surveillez le drift des modèles depuis ici."

### 16.2 Tooltips contextuels

Sur les éléments complexes (score anomalie, valeurs SHAP), un `?` au survol affiche une explication simple :

- Score anomalie : *"Score entre 0 et 1. Au-dessus de 0.7, le dossier est considéré anormal par le modèle."*
- SHAP value : *"Cette valeur indique l'impact de cette caractéristique sur le score. Positif = augmente le risque."*
- PSI : *"Population Stability Index. Mesure si les données récentes ressemblent aux données d'entraînement du modèle."*

### 16.3 Empty states guidants

Quand une section est vide, le `<EmptyState>` affiche une action guidante :

- `/claims` vide → "Aucun sinistre. Créez votre premier sinistre → [+ Nouveau sinistre]"
- `/audit` vide → "Aucune analyse en attente. Soumettez un sinistre pour lancer l'analyse IA."
- `/ml/drift` stable → "✓ Toutes les branches sont stables. Aucune action requise."

### 16.4 Indicateurs de progression (workflow sinistre)

Sur `/claims/[id]`, un stepper visuel montre le cycle de vie :

```
① DRAFT  →  ② SUBMITTED  →  ③ OPEN  →  ④ CLOSED
   (vous)       (pipeline)     (vous)      (vous)
```

---

## 17. CONTRAINTES ET STANDARDS DE CODE

### 17.1 Règles absolues

| Règle | Détail |
|---|---|
| **≤ 500 lignes par fichier** | Découper si dépassement. Les pages sont des orchestrateurs légers. |
| **Séparation service / hook / composant** | Un service ne contient pas de logique React. Un hook ne fait pas d'appels axios directs. |
| **Typage strict** | `strict: true` dans tsconfig. Aucun `any` sans justification commentée. |
| **Query keys centralisées** | Un fichier `[domain].keys.ts` par domaine pour TanStack Query. |
| **Nommage cohérent** | Services : `claimsService.list()`. Hooks : `useClaims()`. Composants : `<ClaimsTable>`. |
| **Aucune logique métier dans les composants** | Les calculs (écart mercuriale, couleur du score) sont dans `lib/utils.ts`. |
| **Formulaires validés côté client avec Zod** | Avant tout appel API — les validators sont dans `/lib/validators/`. |
| **Gestion d'erreur uniformisée** | Les hooks exposent `{ data, isLoading, error }`. Les composants affichent `<ErrorState>` si `error`. |
| **Pas de fetch direct dans les composants** | Toujours passer par un hook TanStack Query. |
| **Accessibilité** | Utiliser les composants Shadcn qui sont ARIA-compliant. Labels sur tous les inputs. |

### 17.2 Convention de nommage des query keys

```typescript
// Chaque domaine a ses clés centralisées
export const CLAIMS_KEYS = {
  all: ['claims'] as const,
  list: (filters: ClaimsFilters) => [...CLAIMS_KEYS.all, 'list', filters] as const,
  detail: (id: string) => [...CLAIMS_KEYS.all, 'detail', id] as const,
  lines: (id: string) => [...CLAIMS_KEYS.all, 'lines', id] as const,
  documents: (id: string) => [...CLAIMS_KEYS.all, 'documents', id] as const,
  analyses: (id: string) => [...CLAIMS_KEYS.all, 'analyses', id] as const,
};
```

### 17.3 Constantes globales

```typescript
// src/lib/constants.ts

export const SCORE_THRESHOLDS = {
  alert: 0.6,   // jaune
  block: 0.8,   // rouge
} as const;

export const PAGINATION_DEFAULTS = {
  page: 1,
  pageSize: 20,
} as const;

export const PSI_THRESHOLDS = {
  stable:  0.10,
  warning: 0.20,
} as const;

export const RATIO_THRESHOLDS = {
  ok:      1.10,
  warning: 1.30,
} as const;

export const CURRENCY = 'XAF' as const;
export const DATE_FORMAT = 'DD/MM/YYYY' as const;
```

---

## ANNEXE A — Récapitulatif des 48 pages

| # | Route | Titre court | Rôles | Endpoints clés |
|---|---|---|---|---|
| 1 | `/` | Redirect | — | — |
| 2 | `/login` | Connexion | Public | #1, #117 |
| 3 | `/forgot-password` | Mot de passe oublié | Public | #4 |
| 4 | `/reset-password` | Réinitialiser mdp | Public | #5 |
| 5 | `/dashboard` | Tableau de bord | Tous | #49, #67, #101, #109 |
| 6 | `/claims` | Liste sinistres | G,A,ADM | #23, #27 |
| 7 | `/claims/new` | Nouveau sinistre | G,ADM | #24,#29,#33,#37,#27 |
| 8 | `/claims/[id]` | Détail sinistre | G,A,ADM | #25,#28,#32,#39 |
| 9 | `/claims/[id]/edit` | Modifier sinistre | G,ADM | #26 |
| 10 | `/claims/[id]/documents` | Documents & OCR | G,A,ADM | #32-#38 |
| 11 | `/claims/[id]/lines` | Lignes de détail | G,A,ADM | #28-#31 |
| 12 | `/claims/analyses` | Historique runs | G,A,ADM | #42,#43,#59 |
| 13 | `/audit` | File d'audit | G,A,ADM | #44, #49 |
| 14 | `/audit/[id]` | Décision HITL | G,A,ADM | #45,#46,#47,#50 |
| 15 | `/audit/[id]/shap` | SHAP complet | G,A,ADM | #48 |
| 16 | `/escalations` | Escalades | A,ADM | #51,#55 |
| 17 | `/escalations/[id]` | Détail escalade | A,ADM | #52,#53,#54 |
| 18 | `/fraud/graph` | Graphe fraude | A,ADM | #56,#57,#58 |
| 19 | `/fraud/graph/[id]` | Communauté | A,ADM | #57,#58 |
| 20 | `/fraud/analytics` | Analytiques SHAP | A,E,ADM | #102,#103 |
| 21 | `/fraud/rca` | Distribution RCA | A,ADM | #104,#87 |
| 22 | `/ml/models` | Catalogue modèles | E,ADM | #60,#64,#65 |
| 23 | `/ml/models/[id]` | Fiche modèle | E,ADM | #61,#63,#66 |
| 24 | `/ml/models/compare` | Comparaison | E,ADM | #105 |
| 25 | `/ml/drift` | Dashboard drift | A,E,ADM | #67,#71 |
| 26 | `/ml/drift/[branch]` | Drift branche | A,E,ADM | #68,#69 |
| 27 | `/ml/drift/[branch]/[id]` | Rapport drift | E,ADM | #70 |
| 28 | `/ml/retraining` | Réentraînements | E,ADM | #73,#75,#76,#77 |
| 29 | `/ml/retraining/new` | Nouvelle demande | E,ADM | #72 |
| 30 | `/ml/retraining/[id]` | Détail demande | E,ADM | #74 |
| 31 | `/config/modules` | Modules actifs | A,E,ADM | #78,#80 |
| 32 | `/config/modules/[branch]` | Config YAML | E,ADM | #79,#81,#82,#83,#84,#85 |
| 33 | `/config/modules/[branch]/rules` | Règles RCA | A,E,ADM | #86,#87 |
| 34 | `/config/referentiels` | Hub référentiels | G,A,E,ADM | #99,#100 |
| 35 | `/config/referentiels/practitioners` | Praticiens | A,ADM | #88 |
| 36 | `/config/referentiels/practitioners/[id]` | Fiche praticien | A,ADM | #89,#90 |
| 37 | `/config/referentiels/garages` | Garages | A,ADM | #91 |
| 38 | `/config/referentiels/garages/[id]` | Fiche garage | A,ADM | #92,#93 |
| 39 | `/config/referentiels/prices` | Mercuriale | G,A,E,ADM | #94,#95,#96 |
| 40 | `/reports` | Exports | A,ADM | #106,#107,#108,#109,#110 |
| 41 | `/admin/users` | Gestion users | ADM | #11,#12,#15,#16 |
| 42 | `/admin/users/[id]` | Profil user admin | ADM | #13,#14,#17,#18,#19 |
| 43 | `/admin/roles` | Rôles | ADM | #20,#21,#22 |
| 44 | `/admin/system` | Système | ADM | #111-#116, #117 |
| 45 | `/profile` | Mon profil | Tous | #7,#8,#6 |
| 46 | `/profile/security` | Sessions | Tous | #9,#10 |
| 47 | `/unauthorized` | 403 | Tous | — |
| 48 | `/not-found` | 404 | Tous | — |

---

## ANNEXE B — Prochaines étapes recommandées

Après validation de ce document, l'ordre d'implémentation frontend suggéré :

| Phase FE | Contenu | Priorité |
|---|---|---|
| **FE-1** | Scaffolding Next.js + design tokens + AppShell + auth stores + middleware | 🔴 |
| **FE-2** | Pages auth (login, forgot, reset) + apiClient + auth service/hooks | 🔴 |
| **FE-3** | Dashboard + composants communs (DataTable, KpiCard, BranchPill, RiskBadge) | 🔴 |
| **FE-4** | Module Sinistres complet (list, new, detail, documents, lines) | 🔴 |
| **FE-5** | Module Audit + SHAP + HITL Decision Panel | 🟠 |
| **FE-6** | Module Escalades | 🟠 |
| **FE-7** | Graphe de fraude (D3.js) + analytics + RCA | 🟠 |
| **FE-8** | Gouvernance ML (modèles, drift, réentraînement) | 🟠 |
| **FE-9** | Configuration (modules YAML, référentiels, mercuriale) | 🟠 |
| **FE-10** | Rapports exports | 🟡 |
| **FE-11** | Administration (users, roles, system) | 🟠 |
| **FE-12** | Profil + sécurité + guided tour | 🟡 |
| **FE-13** | Tests E2E (Playwright) | 🟡 |

---

*MAKORA_FRONTEND_DESIGN_SYSTEM.md v1.0 — 31 mai 2026*  
*ATABONG EFON STEPHANE FRITZ*  
*48 pages · 117 endpoints couverts · 4 rôles · Architecture Next.js 14 App Router*
