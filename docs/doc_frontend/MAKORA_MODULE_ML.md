# MAKORA — Module Gouvernance ML — Spécification d'implémentation
> **Document :** MAKORA_MODULE_ML.md
> **Chantier :** 2 — Zoom module
> **Date :** Juin 2026
> **Auteur :** ATABONG EFON STEPHANE FRITZ
> **Rôles concernés :** E · ADM (modèles, réentraînement) — A · E · ADM (drift)
> **Pages :** 9 · **Priorité :** 🟠 FE-8
> **Références scientifiques :** [Liu2008] IF · [Gama2014] drift · [Caruana1997] multitask (H0) · [Amershi2019] SE for ML

> Conventions communes : voir `MAKORA_MODULE_DASHBOARD.md`.

---

## Vue d'ensemble du module

Le module Gouvernance ML est le **tableau de bord du data scientist et de l'administrateur ML**. Il couvre tout le cycle de vie des modèles : catalogue, fiches détaillées, comparaison (qui valide empiriquement l'hypothèse H0 du mémoire), surveillance du drift des données, et gestion des demandes de réentraînement. C'est ici que se matérialise la contribution scientifique du projet.

> **Page clé pour le mémoire** : `/ml/models/compare` valide l'hypothèse H0 (un modèle générique MAKORA n'est pas significativement moins précis qu'un modèle spécialisé). Δ visé ∈ [2%, 7%].

### Cycle de vie d'un modèle

```
CANDIDAT (entraîné, non déployé)
  └─► EN PRODUCTION (déployé par ADM)
        └─► ARCHIVÉ (remplacé par un nouveau modèle)
```

### Cycle de vie d'une demande de réentraînement

```
PENDING ──► APPROVED ──► DONE
   └──────► REJECTED
```

### Pages du module

| # | Route | Titre | Rôles | Priorité |
|---|---|---|---|---|
| 1 | `/ml/models` | Catalogue modèles | E, ADM | 🟠 |
| 2 | `/ml/models/[model_id]` | Fiche modèle | E, ADM | 🟠 |
| 3 | `/ml/models/compare` | Comparaison (H0) | E, ADM | 🟠 |
| 4 | `/ml/drift` | Dashboard drift | A, E, ADM | 🟠 |
| 5 | `/ml/drift/[branch]` | Drift par branche | A, E, ADM | 🟠 |
| 6 | `/ml/drift/[branch]/[report_id]` | Détail rapport drift | E, ADM | 🟡 |
| 7 | `/ml/retraining` | Demandes réentraînement | E, ADM | 🟠 |
| 8 | `/ml/retraining/new` | Nouvelle demande | E, ADM | 🟡 |
| 9 | `/ml/retraining/[id]` | Détail demande | E, ADM | 🟡 |

---

## Page 1 — Catalogue des modèles (`/ml/models`)

### Rôles : E · ADM

### Layout

Filtres + tableau + bouton "Déployer" (ADM).

### Filtres

- Branche (SANTÉ / AUTO)
- Algorithme (IF / LOF / SVM)

### Colonnes

| Colonne | Source | Format |
|---|---|---|
| ID | `model_id` | Mono |
| Branche | `branch` | `<BranchPill>` |
| Algorithme | `algorithm` | Texte (IF / LOF / SVM) |
| Version | `version` | Mono |
| F1 | `metrics.f1` | 2 décimales |
| AUC | `metrics.auc_roc` | 2 décimales |
| MCC | `metrics.mcc` | 2 décimales |
| FPR | `metrics.fpr` | 2 décimales |
| Statut | `status` | Badge EN PRODUCTION / ARCHIVÉ / CANDIDAT |

### Actions

- `Voir fiche` → `/ml/models/[id]`
- `Déployer` (ADM seulement) → modal de confirmation → `POST /models/deploy`

### Endpoints consommés

- `GET /models/`
- `GET /models/branch/{branch}/current`
- `POST /models/deploy` (ADM)

### UX décisions

- Statut `EN PRODUCTION` en or (cohérent avec l'identité MAKORA), `CANDIDAT` en bleu, `ARCHIVÉ` en gris.
- Le déploiement est une action sensible : modal de confirmation explicite mentionnant la branche et la version qui sera remplacée.

---

## Page 2 — Fiche modèle (`/ml/models/[model_id]`)

### Rôles : E · ADM

### Layout

En-tête + métriques + features + courbes + paramètres + historique déploiements.

### Sections

**Métriques** (toutes obligatoires — standard non négociable du projet) :
Precision · Recall · F1 · AUC-ROC · Average Precision · FPR · MCC. Visualisées en jauge/progress bar avec le seuil cible indiqué (F1 ≥ 0.70).

**Features** : liste des features utilisées avec type et importance relative.

**Courbes** (si disponibles) : ROC Curve + Precision-Recall Curve (Recharts AreaChart).

**Paramètres** : contamination · algorithme · `random_state` (42) · version.

**Historique déploiements** : timeline des périodes où ce modèle a été actif en production.

### Endpoints consommés

- `GET /models/{model_id}`
- `GET /models/deployments`

---

## Page 3 — Comparaison modèles / Validation H0 (`/ml/models/compare`)

### Rôles : E · ADM

> **C'est la page la plus importante du mémoire.** Elle prouve empiriquement que le modèle générique MAKORA tient face aux modèles spécialisés.

### Layout

Sélecteur de modèles + tableau comparatif + graphique radar.

### Tableau comparatif

| Métrique | M_sante (IF) | M_auto (IF) | M_makora |
|---|---|---|---|
| F1 (Santé) | 0.76 | 0.41 | 0.74 |
| F1 (Auto) | 0.38 | 0.79 | 0.75 |
| AUC-ROC | 0.84 | 0.87 | 0.86 |
| MCC | 0.71 | 0.73 | 0.72 |
| Average Precision | 0.68 | 0.71 | 0.70 |
| Δ vs spécialisé | ref | ref | [-2%, +2%] |

### Graphique radar

5 axes : F1 · AUC · MCC · (1 − FPR) · AP. Une série par modèle (M_sante, M_auto, M_makora).

### Endpoint consommé

- `GET /analytics/models/performance`

### UX décisions

- Mettre en évidence la ligne `Δ vs spécialisé` : si Δ ∈ [2%, 7%] → encadré vert "Trade-off généricité/précision validé".
- Inclure une note méthodologique : split 70/15/15, seed 42, intervalles de confiance bootstrap.

---

## Page 4 — Dashboard drift (`/ml/drift`)

### Rôles : A · E · ADM

### Layout

Statuts globaux par branche + tableau.

### Statuts globaux

Pastilles : `SANTÉ : ● STABLE` / `AUTO : ● WARNING — PSI 0.14`. Seuils PSI : stable < 0.10, warning < 0.20, critical ≥ 0.20.

### Tableau par branche

| Colonne | Source |
|---|---|
| Branche | `<BranchPill>` |
| PSI Global | valeur + couleur |
| Statut | STABLE / WARNING / CRITICAL |
| Nb features dégradées | entier |
| Dernier rapport | date |
| Actions | `Voir détail` · `Déclencher calcul` (E/ADM) |

### Endpoints consommés

- `GET /drift/status`
- `POST /drift/run/{branch}` (E, ADM)

---

## Page 5 — Drift par branche (`/ml/drift/[branch]`)

### Rôles : A · E · ADM

### Layout

En-tête + tableau features + historique (line chart).

### En-tête

Branch pill + statut global + PSI global + recommandation textuelle.

### Tableau des features

| Colonne | Source |
|---|---|
| Feature name | `feature_name` |
| PSI | valeur |
| Statut | STABLE / WARNING / CRITICAL |
| Évolution | sparkline |

Trié par PSI décroissant. Features CRITICAL surlignées en rouge.

### Historique

Line chart : PSI global sur les 30 derniers rapports.

### Bouton

`Demander un réentraînement` → `POST /retraining/` (préremplit la branche).

### Endpoints consommés

- `GET /drift/status/{branch}`
- `GET /drift/history/{branch}`

---

## Page 6 — Détail rapport drift (`/ml/drift/[branch]/[report_id]`)

### Rôles : E · ADM

### Fonctionnalités

- PSI de chaque feature à la date de ce rapport
- Comparaison avec le rapport précédent (delta par feature)
- Recommandation affichée

### Endpoint consommé

- `GET /drift/reports/{report_id}`

---

## Page 7 — Demandes de réentraînement (`/ml/retraining`)

### Rôles : E · ADM

### Layout — Onglets par statut

`En attente (PENDING)` · `Approuvées (APPROVED)` · `Terminées (DONE)` · `Rejetées (REJECTED)`.

### Colonnes

| Colonne | Source |
|---|---|
| ID | `id` |
| Branche | `<BranchPill>` |
| Motif | `motif` |
| Lié à drift report | `drift_report_id` ou "—" |
| Demandé par | `requested_by_hash` |
| Date | `created_at` |
| Statut | badge |
| Actions | selon rôle |

### Actions (ADM)

- `Approuver` → `PATCH /retraining/{id}/approve`
- `Rejeter` → `PATCH /retraining/{id}/reject` + motif
- `Marquer terminé` → `PATCH /retraining/{id}/complete` + lier le nouveau modèle

### Bouton

`+ Nouvelle demande` (E, ADM) → `/ml/retraining/new`.

### Endpoints consommés

- `GET /retraining/`
- `PATCH /retraining/{id}/approve`
- `PATCH /retraining/{id}/reject`
- `PATCH /retraining/{id}/complete`

---

## Page 8 — Nouvelle demande (`/ml/retraining/new`)

### Rôles : E · ADM

### Formulaire

- Branche (sélecteur, obligatoire)
- Motif (textarea, obligatoire)
- Drift report lié (optionnel — autocomplete depuis `GET /drift/history/{branch}`)

### Endpoint consommé

- `POST /retraining/`

---

## Page 9 — Détail demande (`/ml/retraining/[id]`)

### Rôles : E · ADM

### Fonctionnalités

- Contexte complet : branche, motif, drift report lié, demandeur, dates
- Historique des transitions de statut (timeline)
- Actions de décision (ADM) si statut PENDING

### Endpoint consommé

- `GET /retraining/{id}`

---

## Composants à créer pour ce module

| Composant | Chemin |
|---|---|
| `<ModelCatalogTable>` | `features/ml/ModelCatalogTable.tsx` |
| `<ModelCard>` | `features/ml/ModelCard.tsx` |
| `<MetricGauge>` | `features/ml/MetricGauge.tsx` |
| `<RocCurveChart>` | `features/ml/RocCurveChart.tsx` |
| `<DeployModelModal>` | `features/ml/DeployModelModal.tsx` |
| `<ModelCompareTable>` | `features/ml/ModelCompareTable.tsx` |
| `<ModelRadarChart>` | `features/ml/ModelRadarChart.tsx` |
| `<DriftStatusGrid>` | `features/drift/DriftStatusGrid.tsx` |
| `<DriftFeatureTable>` | `features/drift/DriftFeatureTable.tsx` |
| `<DriftHistoryChart>` | `features/drift/DriftHistoryChart.tsx` |
| `<PsiStatusBadge>` | `features/drift/PsiStatusBadge.tsx` |
| `<RetrainingTable>` | `features/ml/RetrainingTable.tsx` |
| `<RetrainingForm>` | `features/ml/RetrainingForm.tsx` |

---

## Query keys

```typescript
export const ML_KEYS = {
  all: ['ml'] as const,
  models: (f: object) => [...ML_KEYS.all, 'models', f] as const,
  model: (id: string) => [...ML_KEYS.all, 'model', id] as const,
  compare: () => [...ML_KEYS.all, 'compare'] as const,
  driftStatus: () => [...ML_KEYS.all, 'drift-status'] as const,
  driftBranch: (b: string) => [...ML_KEYS.all, 'drift', b] as const,
  driftReport: (id: string) => [...ML_KEYS.all, 'drift-report', id] as const,
  retraining: (status?: string) => [...ML_KEYS.all, 'retraining', status] as const,
};
```

---

## Flux de navigation

```
/dashboard (widgets E) ──► /ml/drift  /ml/models
/ml/models ──► /ml/models/[id]
/ml/models ──► /ml/models/compare   (validation H0)
/ml/drift ──► /ml/drift/[branch] ──► /ml/drift/[branch]/[report_id]
/ml/drift/[branch] ──(Demander réentraînement)──► /ml/retraining/new
/ml/retraining ──► /ml/retraining/[id]
/ml/retraining ──► /ml/retraining/new
```

---

*MAKORA_MODULE_ML.md — Juin 2026 — ATABONG EFON STEPHANE FRITZ*
