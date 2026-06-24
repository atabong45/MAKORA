# MAKORA — Module Analyse de fraude — Spécification d'implémentation
> **Document :** MAKORA_MODULE_FRAUDE.md
> **Chantier :** 2 — Zoom module
> **Date :** Juin 2026
> **Auteur :** ATABONG EFON STEPHANE FRITZ
> **Rôles concernés :** A · ADM (graphe, RCA) — A · E · ADM (analytics SHAP)
> **Pages :** 4 · **Priorité :** 🟠 FE-7
> **Référence scientifique :** [Blondel2008] Louvain · [Jiang2014] CatchSync · [Lundberg2017] SHAP

> Conventions communes : voir `MAKORA_MODULE_DASHBOARD.md`.

---

## Vue d'ensemble du module

Le module Analyse de fraude offre la **vision macroscopique** de la fraude, par opposition au module Audit qui traite les dossiers un par un. Il répond à trois questions : *qui fraude ensemble ?* (graphe de communautés), *qu'est-ce qui trahit la fraude ?* (analytics SHAP), et *quels types de fraude détecte-t-on ?* (distribution RCA). C'est l'outil d'investigation stratégique de l'auditeur.

### Pages du module

| # | Route | Titre | Rôles | Priorité |
|---|---|---|---|---|
| 1 | `/fraud/graph` | Graphe de communautés | A, ADM | 🟠 |
| 2 | `/fraud/graph/[community_id]` | Détail communauté | A, ADM | 🟠 |
| 3 | `/fraud/analytics` | Analytics SHAP globales | A, E, ADM | 🟠 |
| 4 | `/fraud/rca` | Distribution RCA | A, ADM | 🟠 |

---

## Page 1 — Graphe de communautés (`/fraud/graph`)

### Rôles : A · ADM

### Layout — 3 panneaux

```
┌────────────┬──────────────────────┬────────────────┐
│ Panneau    │  Zone centrale       │  Panneau droit │
│ gauche     │  Graphe interactif   │  Détail        │
│ Liste      │  (force-directed)    │  sélection     │
│ communautés│                      │                │
└────────────┴──────────────────────┴────────────────┘
```

### Panneau gauche — Liste des communautés

- Filtres : branche, `is_suspicious`, taille minimum
- Tableau : ID | Taille | Densité | Score suspicion | Raison
- Clic sur une ligne → centre et surligne la communauté dans le graphe

### Zone centrale — Graphe interactif

- Rendu **D3.js** (force-directed layout) — bibliothèque déjà présente dans le mock
- Nœuds colorés par type : assuré = bleu, praticien = or, garage = vert
- Arêtes d'épaisseur proportionnelle au nombre de sinistres liés
- Nœuds centraux (`is_central = true`) affichés plus grands (hubs de fraude)
- Interactions : zoom, pan, sélection de nœud, sélection de communauté

### Panneau droit — Détail de la sélection

- Si **communauté** sélectionnée : densité, modularité, suspicion_score, raison
- Si **nœud** sélectionné : type, hash pseudonymisé, node_score, nombre de liens, lien "Voir la fiche" (→ praticien/garage)

### Endpoints consommés

- `GET /graph/communities` — liste filtrée
- `GET /graph/communities/{id}` — détail communauté
- `GET /graph/communities/{id}/members` — membres

### UX décisions

- **Performance** : le graphe peut être dense. Limiter le rendu initial aux communautés `is_suspicious=true`, charger le reste à la demande.
- **Lisibilité** : légende de couleurs toujours visible. Les hubs (`is_central`) ont un halo discret.
- État vide : *"Aucune communauté suspecte détectée pour les filtres actuels."*

---

## Page 2 — Détail communauté (`/fraud/graph/[community_id]`)

### Rôles : A · ADM

### Layout

```
┌─────────────────────────────────────────────────────┐
│ En-tête : ID communauté · branche · taille           │
├─────────────────────────────────────────────────────┤
│ Métriques : suspicion (jauge) · densité · modularité │
├─────────────────────────────────────────────────────┤
│ Tableau des membres                                  │
├─────────────────────────────────────────────────────┤
│ Sinistres liés à la communauté                       │
└─────────────────────────────────────────────────────┘
```

### Métriques

| Métrique | Format |
|---|---|
| Suspicion score | Grande jauge 0-1 |
| Densité du graphe | Progress bar |
| Modularité | Valeur numérique |
| Raison | Texte explicatif |

### Tableau des membres

| Colonne | Source |
|---|---|
| Type nœud | assuré / praticien / garage |
| Hash | pseudonymisé (mono) |
| Score nœud | `node_score` |
| Rôle central | ✓ si `is_central` |
| Nb sinistres | entier |

### Endpoints consommés

- `GET /graph/communities/{id}`
- `GET /graph/communities/{id}/members`

---

## Page 3 — Analytics SHAP globales (`/fraud/analytics`)

### Rôles : A · E · ADM

### Layout

```
┌─────────────────────────────────────────────────────┐
│ Sélecteur de branche + période (30j / 90j / 1an)     │
├─────────────────────────────────────────────────────┤
│ Graphique 1 : Top 10 features globales (bar h.)      │
├─────────────────────────────────────────────────────┤
│ Graphique 2 : Comparaison SANTÉ vs AUTO (side-by-side)│
├─────────────────────────────────────────────────────┤
│ Graphique 3 : Évolution temporelle top 3 (line)      │
└─────────────────────────────────────────────────────┘
```

### Graphiques

| # | Type | Contenu | Rôle analytique |
|---|---|---|---|
| 1 | Bar chart horizontal | Top 10 features par valeur SHAP moyenne | Quels signaux dominent |
| 2 | Bar chart côte-à-côte | Mêmes features sur SANTÉ vs AUTO | Comparer les branches |
| 3 | Line chart | Évolution des 3 top features | Détecter l'évolution des patterns |

### Endpoints consommés

- `GET /analytics/shap/top-features` — global
- `GET /analytics/shap/top-features/{branch}` — par branche

### UX décisions

- Période configurable, passée en query param `period_days`.
- Rendu Recharts. Tooltips détaillés au survol.
- Cette page est partagée avec l'expert métier (E) car elle éclaire les choix de feature engineering.

---

## Page 4 — Distribution RCA (`/fraud/rca`)

### Rôles : A · ADM

### Layout

```
┌─────────────────────────────────────────────────────┐
│ Donut : répartition par catégorie RCA principale     │
├─────────────────────────────────────────────────────┤
│ Bar chart : répartition par sous-catégorie           │
├─────────────────────────────────────────────────────┤
│ Top 5 règles RCA les plus déclenchées                │
└─────────────────────────────────────────────────────┘
```

### Graphiques

- **Donut** : catégories principales (Fraude Intentionnelle, Risque Technique…) avec % et valeurs
- **Bar chart** : sous-catégories (Surfacturation, Unbundling, Phantom billing, Staging accident…)
- **Top 5 règles** : tableau des règles RCA les plus déclenchées avec nombre d'occurrences

### Endpoints consommés

- `GET /analytics/rca/distribution`
- `GET /modules/rca-rules/stats`

### UX décisions

- Cette page raconte une histoire : *quels types de fraude MAKORA attrape-t-il le plus ?* Utile pour orienter les efforts d'investigation et pour le mémoire (preuve de couverture des patterns upcoding/unbundling/phantom billing).

---

## Composants à créer pour ce module

| Composant | Chemin | Pages |
|---|---|---|
| `<FraudGraph>` | `features/fraud/FraudGraph.tsx` | `/fraud/graph` |
| `<CommunityList>` | `features/fraud/CommunityList.tsx` | `/fraud/graph` |
| `<GraphNodeDetail>` | `features/fraud/GraphNodeDetail.tsx` | `/fraud/graph` |
| `<CommunityMetrics>` | `features/fraud/CommunityMetrics.tsx` | `/fraud/graph/[id]` |
| `<CommunityMembersTable>` | `features/fraud/CommunityMembersTable.tsx` | `/fraud/graph/[id]` |
| `<ShapTopFeaturesChart>` | `features/analytics/ShapTopFeaturesChart.tsx` | `/fraud/analytics` |
| `<ShapBranchCompareChart>` | `features/analytics/ShapBranchCompareChart.tsx` | `/fraud/analytics` |
| `<ShapTrendChart>` | `features/analytics/ShapTrendChart.tsx` | `/fraud/analytics` |
| `<RcaDistributionChart>` | `features/analytics/RcaDistributionChart.tsx` | `/fraud/rca` |

---

## Query keys

```typescript
export const FRAUD_KEYS = {
  all: ['fraud'] as const,
  communities: (f: object) => [...FRAUD_KEYS.all, 'communities', f] as const,
  community: (id: string) => [...FRAUD_KEYS.all, 'community', id] as const,
  members: (id: string) => [...FRAUD_KEYS.all, 'members', id] as const,
  shapTop: (branch?: string) => [...FRAUD_KEYS.all, 'shap-top', branch] as const,
  rcaDist: () => [...FRAUD_KEYS.all, 'rca-distribution'] as const,
};
```

---

## Flux de navigation

```
/dashboard (widget SHAP) ──────► /fraud/analytics
/fraud/graph ──(clic communauté)──► /fraud/graph/[community_id]
/fraud/graph/[id] ──(clic membre)──► /config/referentiels/practitioners/[id]
                                  └─► /config/referentiels/garages/[id]
```

---

*MAKORA_MODULE_FRAUDE.md — Juin 2026 — ATABONG EFON STEPHANE FRITZ*
