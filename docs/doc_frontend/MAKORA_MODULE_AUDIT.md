# MAKORA — Module Audit & HITL — Spécification d'implémentation
> **Document :** MAKORA_MODULE_AUDIT.md
> **Chantier :** 2 — Zoom module
> **Date :** Juin 2026
> **Auteur :** ATABONG EFON STEPHANE FRITZ
> **Rôles concernés :** G · A · ADM (file + décision) — Escalades : A · ADM
> **Pages :** 5 · **Priorité :** 🟠 FE-5 / FE-6

> Conventions communes : voir `MAKORA_MODULE_DASHBOARD.md` (thème, XAF, dates, i18n, états, RBAC, accessibilité). Elles s'appliquent ici aussi.

---

## Vue d'ensemble du module

Le module Audit est le **cœur du workflow Human-in-the-Loop** de MAKORA. C'est ici que l'humain prend la décision finale sur chaque analyse signalée par l'IA. Le module incarne le principe directeur du projet : l'IA assiste, l'humain décide. Il englobe la file d'audit, la page de décision, l'explorateur SHAP, et le sous-domaine des escalades vers les auditeurs seniors.

### Cycle de vie d'une décision

```
Analyse OPEN (decision_status = PENDING)
  ├─► CONFIRMED   (fraude confirmée)        → claim CLOSED
  ├─► REJECTED    (non-fraude / faux positif) → claim CLOSED
  └─► ESCALATED   (escalade vers auditeur)   → crée une escalation
                      └─► PENDING → IN_PROGRESS → RESOLVED
```

> Note : la table `decisions` est immuable. On ne modifie jamais une décision, on en crée une nouvelle. La décision active est la plus récente.

### Pages du module

| # | Route | Titre | Rôles | Priorité |
|---|---|---|---|---|
| 1 | `/audit` | File d'audit | G, A, ADM | 🔴 |
| 2 | `/audit/[analysis_id]` | Décision HITL | G, A, ADM | 🔴 |
| 3 | `/audit/[analysis_id]/shap` | Explorateur SHAP | A, E, ADM | 🟠 |
| 4 | `/escalations` | File d'escalades | A, ADM | 🟠 |
| 5 | `/escalations/[id]` | Détail escalade | A, ADM | 🟠 |

---

## Page 1 — File d'audit (`/audit`)

### Rôles : G · A · ADM

### Layout

```
┌─────────────────────────────────────────────────────┐
│ Titre "File d'audit"                                 │
├─────────────────────────────────────────────────────┤
│ KPIs : [En attente] [Escaladées] [Décidées 24h] [%] │
├─────────────────────────────────────────────────────┤
│ Filtres : branche, decision_status, score, période   │
├─────────────────────────────────────────────────────┤
│ Tableau paginé des analyses en attente               │
└─────────────────────────────────────────────────────┘
```

### KPIs de la page

| KPI | Source |
|---|---|
| En attente | `audit/stats.pending` |
| Escaladées | `audit/stats.escalated` |
| Décidées aujourd'hui | `audit/stats.decided_today` |
| Taux de confirmation | `audit/stats.confirmation_rate` |

### Filtres

```typescript
interface AuditFilters {
  branch?: 'SANTE' | 'AUTO';
  decision_status?: 'PENDING' | 'CONFIRMED' | 'REJECTED' | 'ESCALATED';
  score_min?: number;       // slider 0-1
  date_from?: string;
  date_to?: string;
  page?: number;
}
```

### Colonnes du tableau

| Colonne | Source | Format |
|---|---|---|
| ID Sinistre | `claim_reference` | Mono · lien → `/claims/[id]` |
| Branche | `branch` | `<BranchPill>` |
| Score | `anomaly_score` | `<ScoreBadge>` + jauge mini |
| Catégorie RCA | `rca_category` | Texte |
| Date analyse | `created_at` | DD/MM/YYYY HH:mm |
| Décision actuelle | `decision_status` | `<DecisionBadge>` |
| Action | — | `Décider` → `/audit/[analysis_id]` |

### Endpoints consommés

- `GET /audit/` — liste filtrée
- `GET /audit/stats` — KPIs

### UX décisions

- Tri par défaut : score décroissant (les cas les plus suspects en haut).
- Les lignes `PENDING` à score ≥ 0.8 ont un liseré rouge discret pour attirer l'œil.
- État vide : *"Aucune analyse en attente de décision. Bon travail !"*

---

## Page 2 — Décision HITL (`/audit/[analysis_id]`)

### Rôles : G · A · ADM

### Layout — 3 colonnes

```
┌──────────────┬───────────────────┬──────────────────┐
│ Colonne 1    │  Colonne 2        │  Colonne 3       │
│ Contexte     │  Résultat IA      │  Décision        │
│ sinistre     │  (jauge, SHAP,    │  (3 boutons +    │
│              │   RCA, narration) │   motif)         │
└──────────────┴───────────────────┴──────────────────┘
```

### Colonne 1 — Contexte sinistre

- Résumé : branche, assuré pseudonymisé, montant total, date soin
- Lignes de détail avec ratio mercuriale surligné (`<ClaimLinesTable>` compact)
- Documents joints (miniatures cliquables → drawer de prévisualisation)

### Colonne 2 — Résultat IA

- **Jauge de score** : arc SVG animé 0→1, zones colorées (vert/orange/rouge selon `SCORE_THRESHOLDS`)
- **Top 3 SHAP** : barres horizontales, nom de feature + valeur + direction (positive = aggrave)
- **Catégorie RCA** : badge "Fraude Intentionnelle / Upcoding" + niveau de confiance
- **Narration LLM** : carte à fond distinct, texte français généré par Mistral 7B, icône "Généré par IA" visible
- Lien `Voir toutes les valeurs SHAP →` `/audit/[id]/shap`

### Colonne 3 — Décision

Trois boutons distincts et explicites :

| Bouton | Couleur | decision | Motif | Rôle |
|---|---|---|---|---|
| ✓ Rejeter (non-fraude) | Vert | REJECTED | Optionnel | G, A, ADM |
| ⚠ Confirmer la fraude | Rouge | CONFIRMED | Obligatoire | G, A, ADM |
| ↑ Escalader à un auditeur | Violet | ESCALATED | Obligatoire + sélecteur auditeur | G (vers A) |

- Modale de confirmation avant soumission.
- Historique des décisions précédentes sur cette analyse affiché en bas (si redécision).

> **Attention sémantique :** "Rejeter" = rejeter l'alerte (le dossier est sain). "Confirmer" = confirmer la fraude. Le libellé complet entre parenthèses est obligatoire pour éviter toute ambiguïté.

### Endpoints consommés

- `GET /audit/{analysis_id}` — données analyse complètes
- `GET /claims/{claim_id}` — contexte sinistre
- `GET /claims/{claim_id}/lines` — lignes
- `GET /claims/{claim_id}/documents` — documents
- `POST /audit/{analysis_id}/decision` — enregistrer la décision
- `GET /audit/{analysis_id}/decisions` — historique des décisions
- `POST /escalations/` — créer escalade (depuis le bouton Escalader)

---

## Page 3 — Explorateur SHAP (`/audit/[analysis_id]/shap`)

### Rôles : A · E · ADM

### Layout

```
┌─────────────────────────────────────────────────────┐
│ Graphique waterfall (toutes les features)            │
├─────────────────────────────────────────────────────┤
│ Tableau complet : feature | value | SHAP | direction │
└─────────────────────────────────────────────────────┘
```

### Graphique waterfall

- Barres horizontales pour **toutes** les features
- Couleur **positive (bleu info)** = augmente le score d'anomalie
- Couleur **négative (or)** = réduit le score d'anomalie
- Valeur SHAP en mono à droite de chaque barre
- Valeur réelle de la feature entre parenthèses sous le nom

### Tableau complet

| Colonne | Source |
|---|---|
| Feature name | `feature_name` |
| Feature value | `feature_value` |
| SHAP value | `shap_value` |
| Direction | `direction` (positive/negative) |
| Rang | `rank` (1 = plus contributif) |

### Endpoint consommé

- `GET /audit/{analysis_id}/shap`

### UX décisions

- Le waterfall est trié par valeur absolue de SHAP décroissante.
- Rendu Recharts (BarChart horizontal). Page technique destinée aux auditeurs/experts — on assume un niveau de lecture data.

---

## Page 4 — File d'escalades (`/escalations`)

### Rôles : A · ADM

### Layout — Sous-onglets

```
┌─────────────────────────────────────────────────────┐
│ Onglets : [En attente] [Mes escalades] [Toutes (ADM)]│
├─────────────────────────────────────────────────────┤
│ Tableau des escalades                                │
└─────────────────────────────────────────────────────┘
```

### Sous-onglets

| Onglet | Contenu | Endpoint |
|---|---|---|
| En attente | Non assignées | `GET /escalations/pending` |
| Mes escalades | Assignées à l'utilisateur courant | `GET /escalations/?assigned_to=me` |
| Toutes | ADM seulement | `GET /escalations/` |

### Colonnes

| Colonne | Source |
|---|---|
| ID Escalade | `id` (mono) |
| Analyse liée | `analysis_id` → `/audit/[id]` |
| Motif | `motif_escalade` |
| Créé par | `created_by_hash` |
| Assigné à | `assigned_to_hash` ou "—" |
| Statut | `statut` (PENDING / IN_PROGRESS / RESOLVED) |
| Date | `created_at` |
| Actions | `S'assigner` · `Résoudre` |

### Actions

- `S'assigner` → `PATCH /escalations/{id}/assign`
- `Résoudre` → modal avec `resolution_note` → `PATCH /escalations/{id}/resolve`

### Endpoints consommés

- `GET /escalations/`
- `GET /escalations/pending`

---

## Page 5 — Détail escalade (`/escalations/[id]`)

### Rôles : A · ADM

### Layout

```
┌─────────────────────────────────────────────────────┐
│ En-tête : ID escalade · statut · dates               │
├─────────────────────────────────────────────────────┤
│ Contexte complet : sinistre + analyse + décision préc.│
├─────────────────────────────────────────────────────┤
│ Motif de l'escalade                                  │
├─────────────────────────────────────────────────────┤
│ Note de résolution (si résolue) OU formulaire        │
└─────────────────────────────────────────────────────┘
```

### Fonctionnalités

- Contexte complet : rappel du sinistre, du résultat d'analyse, de la décision précédente qui a mené à l'escalade
- Motif de l'escalade (`motif_escalade`)
- Si statut RESOLVED : affiche `resolution_note` + qui a résolu + quand
- Si statut PENDING/IN_PROGRESS : formulaire de résolution (textarea `resolution_note` obligatoire) + bouton "Résoudre"

### Endpoints consommés

- `GET /escalations/{id}`
- `PATCH /escalations/{id}/assign`
- `PATCH /escalations/{id}/resolve`

> **Mapping API à respecter** (cf. corrections backend) : `motif_escalade` (pas `reason`), `resolution_note` (pas `resolution`), `statut` (pas `status`), valeurs `PENDING` / `IN_PROGRESS` / `RESOLVED`.

---

## Composants à créer pour ce module

| Composant | Chemin | Pages |
|---|---|---|
| `<AuditQueueTable>` | `features/audit/AuditQueueTable.tsx` | `/audit` |
| `<AuditStatsBar>` | `features/audit/AuditStatsBar.tsx` | `/audit` |
| `<ScoreGauge>` | `features/audit/ScoreGauge.tsx` | `/audit/[id]` |
| `<ShapBarChart>` | `features/audit/ShapBarChart.tsx` | `/audit/[id]` + shap |
| `<ShapWaterfall>` | `features/audit/ShapWaterfall.tsx` | `/audit/[id]/shap` |
| `<LlmNarration>` | `features/audit/LlmNarration.tsx` | `/audit/[id]` |
| `<RcaBadge>` | `features/audit/RcaBadge.tsx` | `/audit/[id]` |
| `<DecisionPanel>` | `features/audit/DecisionPanel.tsx` | `/audit/[id]` |
| `<DecisionHistory>` | `features/audit/DecisionHistory.tsx` | `/audit/[id]` |
| `<EscalationModal>` | `features/escalations/EscalationModal.tsx` | `/audit/[id]` + claims |
| `<EscalationsTable>` | `features/escalations/EscalationsTable.tsx` | `/escalations` |
| `<EscalationCard>` | `features/escalations/EscalationCard.tsx` | `/escalations/[id]` |
| `<DecisionBadge>` | `common/DecisionBadge.tsx` | partout |

---

## Query keys

```typescript
export const AUDIT_KEYS = {
  all: ['audit'] as const,
  list: (f: AuditFilters) => [...AUDIT_KEYS.all, 'list', f] as const,
  detail: (id: string) => [...AUDIT_KEYS.all, 'detail', id] as const,
  shap: (id: string) => [...AUDIT_KEYS.all, 'shap', id] as const,
  decisions: (id: string) => [...AUDIT_KEYS.all, 'decisions', id] as const,
  stats: () => [...AUDIT_KEYS.all, 'stats'] as const,
};
export const ESCALATIONS_KEYS = {
  all: ['escalations'] as const,
  list: () => [...ESCALATIONS_KEYS.all, 'list'] as const,
  pending: () => [...ESCALATIONS_KEYS.all, 'pending'] as const,
  detail: (id: string) => [...ESCALATIONS_KEYS.all, 'detail', id] as const,
};
```

---

## Flux de navigation

```
/claims/[id] ──(Prendre une décision)──► /audit/[analysis_id]
/claims/analyses ─────────────────────► /audit/[analysis_id]
/dashboard (widget audit) ────────────► /audit
/audit ───────────────────────────────► /audit/[analysis_id]
/audit/[analysis_id] ──(Voir SHAP)─────► /audit/[analysis_id]/shap
/audit/[analysis_id] ──(Escalader)─────► crée escalation → /escalations/[id]
/escalations ─────────────────────────► /escalations/[id]
```

---

*MAKORA_MODULE_AUDIT.md — Juin 2026 — ATABONG EFON STEPHANE FRITZ*
