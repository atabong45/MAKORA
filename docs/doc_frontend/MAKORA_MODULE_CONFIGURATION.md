# MAKORA — Module Configuration — Spécification d'implémentation
> **Document :** MAKORA_MODULE_CONFIGURATION.md
> **Chantier :** 2 — Zoom module
> **Date :** Juin 2026
> **Auteur :** ATABONG EFON STEPHANE FRITZ
> **Rôles concernés :** ADM (modification) · A · E (consultation) · G (mercuriale lecture)
> **Pages :** 9 · **Priorité :** 🟠 FE-9
> **Contexte CM :** nomenclature ASAC, mercuriale CIMA, cachet humide, OCR

> Conventions communes : voir `MAKORA_MODULE_DASHBOARD.md`.

---

## Vue d'ensemble du module

Le module Configuration regroupe tout ce qui paramètre le comportement de MAKORA sans toucher au code : les plugins métiers (config YAML par branche), les règles RCA, les référentiels (praticiens, garages, mercuriale CIMA), et les outils d'ingestion (import batch, pipeline OCR). C'est ici que se matérialise la **généricité du framework** : ajouter une branche ou ajuster un seuil se fait par configuration, pas par développement.

> **Principe architectural à respecter dans l'UI** : la configuration manipule des plugins déclaratifs. L'interface ne doit jamais laisser entendre que le Kernel connaît une branche concrète — elle présente les branches comme des modules interchangeables enregistrés dans le registry.

### Pages du module

| # | Route | Titre | Rôles | Priorité |
|---|---|---|---|---|
| 1 | `/config/modules` | Modules actifs | A, E, ADM | 🟠 |
| 2 | `/config/modules/[branch]` | Config YAML branche | E, ADM | 🟠 |
| 3 | `/config/modules/[branch]/rules` | Règles RCA | A, E, ADM | 🟠 |
| 4 | `/config/referentiels` | Hub référentiels | G, A, E, ADM | 🟡 |
| 5 | `/config/referentiels/practitioners` | Praticiens | A, ADM | 🟠 |
| 6 | `/config/referentiels/practitioners/[id]` | Fiche praticien | A, ADM | 🟡 |
| 7 | `/config/referentiels/garages` | Garages | A, ADM | 🟠 |
| 8 | `/config/referentiels/garages/[id]` | Fiche garage | A, ADM | 🟡 |
| 9 | `/config/referentiels/prices` | Mercuriale CIMA | G, A, E, ADM | 🟠 |

> Note : l'import batch (`/config/batch`) et le pipeline OCR (`/config/ocr`) sont des outils transverses présents dans la nav Configuration mais détaillés dans leurs sous-sections respectives ci-dessous.

---

## Page 1 — Modules actifs (`/config/modules`)

### Rôles : A · E · ADM

### Layout

Tableau des plugins métiers chargés.

### Tableau

| Colonne | Source |
|---|---|
| Branche | `<BranchPill>` |
| Statut | LOADED / NOT_LOADED |
| Version | mono |
| Graph enabled | ✓ / ✗ |
| Dernier reload | date |
| Actions | `Hot-reload` (ADM) · `Voir config` |

### Actions

- `Hot-reload` (ADM) → `POST /modules/{branch}/reload`
- `Voir config` → `/config/modules/[branch]`

### Endpoint consommé

- `GET /modules/`

### UX décisions

- Présenter aussi les branches en *concept seulement* (Vie, Agricole) avec un badge "Conception" pour montrer l'extensibilité du framework — argument fort pour le mémoire.

---

## Page 2 — Config YAML branche (`/config/modules/[branch]`)

### Rôles : E (consultation) · ADM (modification)

### Layout

```
┌──────────────────────┬──────────────────────────────┐
│ Panneau gauche        │  Panneau droit               │
│ Config active (JSON)  │  Historique snapshots         │
│ + seuils éditables    │  (rollback possible)          │
└──────────────────────┴──────────────────────────────┘
```

### Panneau gauche — Config active

- Affichage JSON lisible de la config parsée (`<JsonViewer>`)
- Champs éditables (ADM) pour les seuils :
  - `contamination` (slider 0.01–0.30)
  - `anomaly_score_alert` (slider)
  - `anomaly_score_block` (slider, validation : block > alert)
- Bouton `Sauvegarder` → `PATCH /modules/{branch}/config`

### Panneau droit — Historique snapshots

- Tableau : ID | Hash | Date | `Activer` (rollback)
- Permet de revenir à une config précédente

### Endpoints consommés

- `GET /modules/{branch}` · `GET /modules/{branch}/config`
- `PATCH /modules/{branch}/config` (ADM)
- `GET /modules/{branch}/configs` · `GET /modules/{branch}/configs/{id}`
- `POST /modules/{branch}/configs/{id}/activate` (ADM)

### UX décisions

- Toute modification de seuil affiche un avertissement : *"Ce changement affectera toutes les analyses futures de la branche."*
- Validation côté client : `block > alert` strictement, contamination dans [0.01, 0.30].

---

## Page 3 — Règles RCA (`/config/modules/[branch]/rules`)

### Rôles : A · E · ADM

### Layout

Filtres + tableau des règles avec accordéon de conditions.

### Filtres

Catégorie · sous-catégorie · confiance minimum.

### Tableau

| Colonne | Source |
|---|---|
| Rule ID | mono |
| Catégorie | texte |
| Sous-catégorie | texte |
| Confiance base | 0-1 |
| Priorité | entier |
| Logique | AND / OR |

### Accordéon

Clic sur une règle → expand les conditions de déclenchement (feature, opérateur, seuil).

### Endpoints consommés

- `GET /modules/{branch}/rca-rules`
- `GET /modules/rca-rules/stats`

### UX décisions

- Page conçue pour être **lisible par un expert métier non technique**. Les conditions sont présentées en langage proche du métier : *"si ratio_prix_mercuriale > 1.30 ET présence_cachet = faux"*.

---

## Page 4 — Hub référentiels (`/config/referentiels`)

### Rôles : G · A · E · ADM

### Layout

4 cartes navigables : Praticiens · Garages · Mercuriale · Assurés (via audit). Chaque carte affiche un compteur et un lien.

---

## Page 5 — Liste des praticiens (`/config/referentiels/practitioners`)

### Rôles : A · ADM

### Rôle métier

Repérer les prestataires à fort ratio de fraude.

### Filtres

Pays · spécialité · agrément CIMA · ratio prix minimum.

### Colonnes

| Colonne | Source | Indicateur |
|---|---|---|
| ID | hash | mono |
| Spécialité | texte | |
| Pays | texte | |
| Agrément CIMA | ✓ / ✗ | |
| Ratio prix moyen | valeur | `<RatioBadge>` (vert < 1.1, orange 1.1-1.3, rouge > 1.3) |
| Nb sinistres | entier | |

### Endpoint consommé

- `GET /referentiels/practitioners`

---

## Page 6 — Fiche praticien (`/config/referentiels/practitioners/[id]`)

### Rôles : A · ADM

### Sections

- Informations (spécialité, pays, agrément)
- Indicateurs : ratio_prix_moyen, nb_sinistres_total
- Historique des sinistres (tableau paginé, liens vers `/claims/[id]`)

### Endpoints consommés

- `GET /referentiels/practitioners/{id}`
- `GET /referentiels/practitioners/{id}/claims`

---

## Page 7 — Liste des garages (`/config/referentiels/garages`)

### Rôles : A · ADM

### Rôle métier

Surveillance des garages réparateurs (branche Auto).

### Colonnes

ID | Type garage | Ville | Agrément CIMA | Ratio devis moyen (`<RatioBadge>`) | Nb sinistres.

### Endpoint consommé

- `GET /referentiels/garages`

---

## Page 8 — Fiche garage (`/config/referentiels/garages/[id]`)

### Rôles : A · ADM

### Sections

- Informations (type, ville, agrément)
- Indicateurs : ratio_devis_moyen, nb_sinistres_total
- Historique des sinistres (paginé)

### Endpoints consommés

- `GET /referentiels/garages/{id}`
- `GET /referentiels/garages/{id}/claims`

---

## Page 9 — Mercuriale CIMA (`/config/referentiels/prices`)

### Rôles : G · A · E · ADM (lecture) — ADM · E (import)

### Rôle métier

Consultation des prix de référence — outil quotidien du gestionnaire et de l'auditeur. C'est le référentiel contre lequel chaque ligne de sinistre est comparée (ratio_prix).

### Layout

Sélecteur de branche + recherche par code acte + tableau.

### Colonnes

| Colonne | Source |
|---|---|
| Code acte | ASAC (Santé) / poste (Auto) |
| Libellé | texte |
| Prix de référence | `formatXAF()` |
| Date vigueur | date |
| Version mercuriale | mono |

### Bouton (ADM, E)

`Importer nouvelle mercuriale` → upload YAML/CSV → `POST /referentiels/prices`.

### Endpoints consommés

- `GET /referentiels/prices/{branch}`
- `GET /referentiels/prices/{branch}/{code_acte}`
- `POST /referentiels/prices` (ADM, E)

---

## Sous-section — Import batch (`/config/batch`)

### Rôles : G · ADM

### Rôle

Importer un lot de sinistres (CSV) et lancer une analyse de masse.

### Fonctionnalités

- Upload CSV (drag & drop)
- Mapping automatique des colonnes via le MappingEngine (Adapter pattern)
- Aperçu des premières lignes avant validation
- Lancement de l'analyse batch → suit la progression
- Résultats redirigés vers `/claims/analyses`

---

## Sous-section — Pipeline OCR (`/config/ocr`)

### Rôles : G · ADM

### Rôle

Visualiser et tester le pipeline OCR (spécifique au contexte camerounais).

### Fonctionnalités

- Upload d'un document de test
- Affichage des 7 étapes du pipeline : normalisation → preprocessing → Tesseract → extraction entités → détection cachet → analyse EXIF → assemblage
- Résultats : score confiance, entités extraites, présence cachet, flag altération, logiciel de retouche détecté

> **Contexte CM** : le `CachetDetector` (HSV) et l'`ExifAnalyzer` (logiciel de retouche) sont les composants spécifiques. Cette page est aussi un outil pédagogique pour démontrer la contribution africaine du projet.

---

## Composants à créer pour ce module

| Composant | Chemin |
|---|---|
| `<ModuleStatusCard>` | `features/modules/ModuleStatusCard.tsx` |
| `<ModuleConfigForm>` | `features/modules/ModuleConfigForm.tsx` |
| `<ConfigSnapshotList>` | `features/modules/ConfigSnapshotList.tsx` |
| `<RcaRulesTable>` | `features/modules/RcaRulesTable.tsx` |
| `<PractitionerTable>` | `features/referentiels/PractitionerTable.tsx` |
| `<GarageTable>` | `features/referentiels/GarageTable.tsx` |
| `<PriceTable>` | `features/referentiels/PriceTable.tsx` |
| `<MercurialeImportModal>` | `features/referentiels/MercurialeImportModal.tsx` |
| `<BatchImportWizard>` | `features/config/BatchImportWizard.tsx` |
| `<OcrPipelineViewer>` | `features/config/OcrPipelineViewer.tsx` |
| `<RatioBadge>` | `features/claims/RatioBadge.tsx` (réutilisé) |
| `<JsonViewer>` | `common/JsonViewer.tsx` |

---

## Query keys

```typescript
export const CONFIG_KEYS = {
  all: ['config'] as const,
  modules: () => [...CONFIG_KEYS.all, 'modules'] as const,
  moduleConfig: (b: string) => [...CONFIG_KEYS.all, 'config', b] as const,
  rcaRules: (b: string) => [...CONFIG_KEYS.all, 'rca-rules', b] as const,
  practitioners: (f: object) => [...CONFIG_KEYS.all, 'practitioners', f] as const,
  garages: (f: object) => [...CONFIG_KEYS.all, 'garages', f] as const,
  prices: (b: string) => [...CONFIG_KEYS.all, 'prices', b] as const,
};
```

---

## Flux de navigation

```
/config/modules ──► /config/modules/[branch] ──► /config/modules/[branch]/rules
/config/referentiels ──► /config/referentiels/practitioners ──► [id]
                     ──► /config/referentiels/garages ──► [id]
                     ──► /config/referentiels/prices
/config/batch ──(analyse lancée)──► /claims/analyses
```

---

*MAKORA_MODULE_CONFIGURATION.md — Juin 2026 — ATABONG EFON STEPHANE FRITZ*
