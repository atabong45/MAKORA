# MAKORA — Module Dashboard — Spécification d'implémentation
> **Document :** MAKORA_MODULE_DASHBOARD.md
> **Chantier :** 2 — Zoom module
> **Date :** Juin 2026
> **Auteur :** ATABONG EFON STEPHANE FRITZ
> **Rôles concernés :** Tous (G · A · E · ADM) — contenu adapté par rôle
> **Pages :** 1 · **Priorité :** 🔴 FE-3

---

## Conventions communes à tous les modules

> Ces conventions s'appliquent à ce fichier ET à tous les fichiers de module.

- **Thème** : clair par défaut (`--color-navy` = `#1B3C6E`, `--color-gold` = `#F0A500`). Thème sombre disponible.
- **Montants** : toujours `formatXAF()` → `Intl.NumberFormat('fr-CM', {style:'currency', currency:'XAF', maximumFractionDigits:0})`.
- **Dates** : format `DD/MM/YYYY` via `<DateDisplay>`.
- **i18n** : toute chaîne passe par `next-intl` (clés dans `fr.json` / `en.json`).
- **Données** : aucun `fetch` direct dans les composants — toujours via un hook TanStack Query.
- **Logique métier** : déportée dans `lib/utils.ts` (couleur du score, ratio mercuriale), jamais dans les composants.
- **États** : `<LoadingSkeleton>` pendant le chargement, `<EmptyState>` si vide, `<ErrorState>` (avec retry) si erreur.
- **RBAC** : items et boutons non autorisés sont retirés, pas grisés. Garde finale côté API (HTTP 403).
- **Accessibilité** : labels sur tous les inputs, `aria-label` sur boutons icônes, focus visible.

---

## Vue d'ensemble du module

Le Dashboard est la première page vue après connexion. C'est une **vue consolidée personnalisée par rôle** : les KPI sont communs, mais les widgets affichés dépendent des permissions de l'utilisateur connecté. Il sert de point de lancement vers les actions principales de chaque profil.

---

## Page 1 — Tableau de bord global (`/dashboard`)

### Rôles : Tous (contenu filtré par rôle)

### Layout

```
┌─────────────────────────────────────────────────────┐
│ Bandeau d'alerte (drift critique) — si applicable    │
├─────────────────────────────────────────────────────┤
│ Titre "Tableau de bord" + sélecteur de période       │
├─────────────────────────────────────────────────────┤
│ Grille KPI (4 cartes principales)                    │
├─────────────────────────────────────────────────────┤
│ Grille de widgets (selon rôle)                       │
└─────────────────────────────────────────────────────┘
```

### Section KPI — 4 cartes principales

| Carte | Source | Format | Tendance |
|---|---|---|---|
| Sinistres analysés | `GET /analytics/dashboard` | Entier | ↑ +12 / 24h |
| Taux d'anomalie global | `GET /analytics/dashboard` | Pourcentage 1 décimale | ↑ +0.4% |
| Décisions en attente | `GET /audit/stats` | Entier | Badge urgent si > 0 |
| Statut drift | `GET /drift/status` | Pastille STABLE/WARNING | Par branche |

```typescript
// Composant KpiCard (common/KpiCard.tsx)
interface KpiCardProps {
  icon: ReactNode;
  label: string;
  value: string;            // déjà formaté (round/toFixed)
  trend?: { value: string; direction: 'up' | 'down' | 'stable' };
  alert?: boolean;          // bordure orange si alerte
  highlight?: boolean;      // accent or si KPI phare
}
```

### Widgets par rôle

| Widget | G | A | E | ADM | Endpoint |
|---|:---:|:---:|:---:|:---:|---|
| Sinistres récents (5 lignes) | ✅ | ✅ | ❌ | ✅ | `GET /claims/?page_size=5&sort=created_at` |
| File d'audit (5 en attente) | ✅ | ✅ | ❌ | ✅ | `GET /audit/?decision_status=PENDING&page_size=5` |
| Escalades non assignées | ❌ | ✅ | ❌ | ✅ | `GET /escalations/pending` |
| Top 5 features SHAP du mois | ❌ | ✅ | ✅ | ✅ | `GET /analytics/shap/top-features` |
| Drift PSI par branche (jauge) | ❌ | ✅ | ✅ | ✅ | `GET /drift/status` |
| Performances modèles actifs | ❌ | ❌ | ✅ | ✅ | `GET /analytics/models/performance` |
| Activité système | ❌ | ❌ | ❌ | ✅ | `GET /reports/stats/global` |

### Bandeau d'alerte drift

Si une branche est en statut `CRITICAL`, un bandeau rouge apparaît en haut avec message contextuel et lien vers `/ml/drift/[branch]`. Fermable (non persistant — réapparaît au prochain chargement tant que le drift est critique).

### Sélecteur de période

Boutons : `7 derniers jours` · `30 jours` · `90 jours`. Optionnel : toggle "Comparer (T-1)" qui ajoute une série de comparaison sur les graphiques. Passé en query param `period_days`.

### Endpoints consommés

- `GET /analytics/dashboard` — KPI globaux
- `GET /claims/?page=1&page_size=5&sort=created_at` — sinistres récents
- `GET /audit/?decision_status=PENDING&page_size=5` — file d'audit
- `GET /escalations/pending` — escalades non assignées (A/ADM)
- `GET /analytics/shap/top-features` — top features (A/E/ADM)
- `GET /drift/status` — statut drift (A/E/ADM)
- `GET /analytics/models/performance` — métriques modèles (E/ADM)
- `GET /reports/stats/global` — stats globales (ADM)

### UX décisions

- **Personnalisation silencieuse** : un gestionnaire ne voit jamais les widgets ML, un expert métier ne voit jamais la file de sinistres. Chaque profil arrive sur un dashboard qui lui ressemble.
- **Pas de surcharge** : maximum 4 widgets visibles simultanément par rôle. Le reste est accessible via la navigation.
- **Action rapide** : chaque widget a un lien "Voir tout" vers sa page dédiée.
- **Toasts temps réel** (inspiré du mock) : notifications discrètes en bas à droite quand une nouvelle anomalie est détectée (via polling ou WebSocket selon disponibilité backend). À conditionner selon le rôle (G/A uniquement).

### Composants à créer

| Composant | Chemin |
|---|---|
| `<KpiCard>` | `common/KpiCard.tsx` |
| `<DashboardAlertBanner>` | `features/dashboard/DashboardAlertBanner.tsx` |
| `<RecentClaimsWidget>` | `features/dashboard/RecentClaimsWidget.tsx` |
| `<AuditQueueWidget>` | `features/dashboard/AuditQueueWidget.tsx` |
| `<EscalationsWidget>` | `features/dashboard/EscalationsWidget.tsx` |
| `<TopShapWidget>` | `features/dashboard/TopShapWidget.tsx` |
| `<DriftStatusWidget>` | `features/dashboard/DriftStatusWidget.tsx` |
| `<ModelPerfWidget>` | `features/dashboard/ModelPerfWidget.tsx` |
| `<PeriodSelector>` | `common/PeriodSelector.tsx` |

---

*MAKORA_MODULE_DASHBOARD.md — Juin 2026 — ATABONG EFON STEPHANE FRITZ*
