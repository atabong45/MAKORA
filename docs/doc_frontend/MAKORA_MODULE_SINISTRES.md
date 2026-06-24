# MAKORA — Module Sinistres — Spécification d'implémentation
> **Document :** MAKORA_MODULE_SINISTRES.md  
> **Chantier :** 2 — Zoom module  
> **Date :** Juin 2026  
> **Auteur :** ATABONG EFON STEPHANE FRITZ  
> **Rôles concernés :** G (Gestionnaire) · A (Auditeur) · ADM (Administrateur)  
> **Pages :** 7 · **Endpoints :** 17 · **Priorité :** 🔴 FE-4

---

## Vue d'ensemble du module

Le module Sinistres est le cœur opérationnel de MAKORA. C'est ici que le cycle de vie d'un dossier d'assurance est géré, de la saisie manuelle jusqu'à la décision finale. Toutes les autres fonctionnalités (audit, escalades, graphe de fraude) sont des branches issues de ce module.

### Cycle de vie d'un sinistre

```
DRAFT
  ↓ POST /claims/{id}/submit
SUBMITTED  (pipeline MAKORA déclenché automatiquement)
  ↓ résultat disponible
OPEN       (décision humaine HITL en attente)
  ↓ POST /audit/{analysis_id}/decision
CLOSED     (CONFIRMED ou REJECTED)
```

### Pages du module

| # | Route | Titre | Rôles | Priorité |
|---|---|---|---|---|
| 1 | `/claims` | Liste des sinistres | G, A, ADM | 🔴 |
| 2 | `/claims/new` | Nouveau sinistre | G, ADM | 🔴 |
| 3 | `/claims/[id]` | Détail sinistre | G, A, ADM | 🔴 |
| 4 | `/claims/[id]/edit` | Modifier sinistre | G, ADM | 🟠 |
| 5 | `/claims/[id]/documents` | Documents & OCR | G, A, ADM | 🟠 |
| 6 | `/claims/[id]/lines` | Lignes de détail | G, A, ADM | 🟠 |
| 7 | `/claims/analyses` | Historique runs | G, A, ADM | 🟠 |

### Endpoints API du module

| # | Méthode | Chemin | Rôles | Priorité |
|---|---|---|---|---|
| 23 | GET | `/claims/` | G, A, ADM | 🔴 |
| 24 | POST | `/claims/` | G, ADM | 🔴 |
| 25 | GET | `/claims/{claim_id}` | G, A, ADM | 🔴 |
| 26 | PATCH | `/claims/{claim_id}` | G, ADM | 🟠 |
| 27 | POST | `/claims/{claim_id}/submit` | G, ADM | 🔴 |
| 28 | GET | `/claims/{claim_id}/lines` | G, A, ADM | 🟠 |
| 29 | POST | `/claims/{claim_id}/lines` | G, ADM | 🟠 |
| 30 | PATCH | `/claims/{claim_id}/lines/{line_id}` | G, ADM | 🟡 |
| 31 | DELETE | `/claims/{claim_id}/lines/{line_id}` | G, ADM | 🟡 |
| 32 | GET | `/claims/{claim_id}/documents` | G, A, ADM | 🟠 |
| 33 | POST | `/claims/{claim_id}/documents` | G, ADM | 🟠 |
| 34 | GET | `/claims/{claim_id}/documents/{doc_id}` | G, A, ADM | 🟡 |
| 35 | GET | `/claims/{claim_id}/documents/{doc_id}/download` | G, A, ADM | 🟠 |
| 36 | DELETE | `/claims/{claim_id}/documents/{doc_id}` | ADM | 🟡 |
| 37 | POST | `/claims/{claim_id}/ocr/run` | G, ADM | 🟠 |
| 38 | GET | `/claims/{claim_id}/ocr` | G, A, ADM | 🟠 |
| 39 | GET | `/claims/{claim_id}/analyses` | G, A, ADM | 🟠 |

---

## Page 1 — Liste des sinistres (`/claims`)

### Rôles : G · A · ADM

### Layout

```
┌─────────────────────────────────────────────────────┐
│ Titre "Sinistres"  + [+ Nouveau sinistre] (G/ADM)    │
├─────────────────────────────────────────────────────┤
│ Barre de filtres (branche, statut, score, dates)    │
│ Champ de recherche libre (ID, police)               │
├─────────────────────────────────────────────────────┤
│ Tableau paginé (20 lignes/page, triable)            │
├─────────────────────────────────────────────────────┤
│ Pagination                                           │
└─────────────────────────────────────────────────────┘
```

### Colonnes du tableau

| Colonne | Source | Format | Notes |
|---|---|---|---|
| ID Sinistre | `claim_reference` | Mono · lien vers `/claims/[id]` | Cliquable |
| Branche | `branch` | `<BranchPill>` | SANTÉ bleu info / AUTO or |
| Assuré | `insured_hash` | Mono · tronqué à 12 chars | Pseudonymisé |
| Date soin | `date_soin` | DD/MM/YYYY | `DATE_FORMAT` |
| Montant | `montant_total` | `formatXAF()` | Aligné droite |
| Statut | `statut` | `<StatusBadge>` | DRAFT/SUBMITTED/OPEN/CLOSED |
| Score IF | `score` | `<ScoreBadge>` | Null si non analysé |
| Anomalie | `is_anomaly` | Icône ⚠ ou vide | Seulement si true |
| Décision | `decision` | `<DecisionBadge>` | `—` si null |
| Actions | — | Boutons contextuels | Voir infra |

### Boutons d'action par ligne (contextuels)

```typescript
// Logique de rendu des boutons
const actions = (claim: ClaimListItem) => [
  { label: 'Voir', icon: 'eye', href: `/claims/${claim.id}`, always: true },
  {
    label: 'Analyser', icon: 'player-play',
    action: () => submitClaim(claim.id),
    show: claim.statut === 'DRAFT' && hasPermission('claims:submit')
  },
  {
    label: 'Décider', icon: 'gavel',
    href: `/audit/${claim.latest_analysis_id}`,
    show: claim.statut === 'OPEN' && hasPermission('audit:decide')
  },
];
```

### Filtres disponibles

```typescript
interface ClaimsFilters {
  branch?: 'SANTE' | 'AUTO';
  statut?: 'DRAFT' | 'SUBMITTED' | 'OPEN' | 'CLOSED';
  score_min?: number;          // 0.0 → 1.0, slider
  is_anomaly?: boolean;        // toggle
  date_soin_from?: string;     // ISO date
  date_soin_to?: string;       // ISO date
  search?: string;             // claim_reference ou numéro police
  page?: number;
  page_size?: number;          // défaut: 20
}
```

### Endpoints consommés

- `GET /claims/` — avec tous les filtres en query params
- `POST /claims/{claim_id}/submit` — bouton Analyser inline

### UX décisions

- Le bouton `+ Nouveau sinistre` n'est affiché que si `hasPermission('claims:write')` (G/ADM).
- Les filtres sont persistés dans l'URL (query params) pour que le lien soit partageable.
- État vide contextuel : *"Aucun sinistre ne correspond aux filtres sélectionnés."* avec bouton "Réinitialiser les filtres".
- La pagination affiche le total : *"234 sinistres · Page 1/12"*.

---

## Page 2 — Nouveau sinistre (`/claims/new`)

### Rôles : G · ADM

### Layout — Wizard à 3 étapes

```
┌─────────────────────────────────────────────────────┐
│ Titre "Nouveau sinistre"  breadcrumb: Sinistres > + │
├─────────────────────────────────────────────────────┤
│ Stepper : [1 Infos générales] [2 Lignes] [3 Docs]  │
├─────────────────────────────────────────────────────┤
│ Contenu de l'étape active                           │
├─────────────────────────────────────────────────────┤
│ [Précédent]                  [Suivant / Enregistrer] │
└─────────────────────────────────────────────────────┘
```

### Étape 1 — Informations générales

Champs requis, validation Zod au submit de l'étape.

```typescript
// Validator étape 1 (src/lib/validators/claims.validators.ts)
const step1Schema = z.object({
  branch: z.enum(['SANTE', 'AUTO']),
  numero_police: z.string().min(1, 'Numéro de police requis'),
  date_soin: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Format YYYY-MM-DD'),
  description: z.string().optional(),
});
```

**Comportement clé :** Le sinistre est créé en base (POST /claims) dès la validation de l'étape 1, pas au submit final. Cela protège contre la perte de données. L'ID DRAFT apparaît dans l'URL dès l'étape 2.

### Étape 2 — Lignes de détail (conditionnel selon branche)

**Si branche = SANTÉ :**
```typescript
interface SanteLine {
  code_acte: string;       // Code ASAC — lookup mercuriale
  libelle?: string;        // Auto-complété depuis le code
  praticien_id_hash: string;
  montant_ligne: number;   // en XAF
  quantite: number;        // défaut: 1
}
```

**Si branche = AUTO :**
```typescript
interface AutoLine {
  poste_reparation: string;
  garage_id_hash: string;
  montant_ligne: number;   // montant devis en XAF
}
```

Tableau éditable inline : ajout, suppression de lignes. Validation par ligne (montant > 0, code_acte requis).

### Étape 3 — Documents

- Drag & drop zone (PDF, JPG, PNG — max 50 MB par fichier)
- Limite : 10 documents par sinistre
- Option "Déclencher OCR" apparaît après chaque upload
- Liste des documents ajoutés avec : nom, taille, icône type, bouton supprimer

### Boutons de sortie

| Bouton | Action |
|---|---|
| Enregistrer en brouillon | Reste sur DRAFT, redirect vers `/claims/[id]` |
| Enregistrer & Soumettre | POST /submit → SUBMITTED → redirect `/claims/[id]` |
| Annuler | Modale confirmation, supprime le DRAFT si vide |

### Endpoints consommés (ordre du wizard)

1. `POST /claims/` — création DRAFT (étape 1 validée)
2. `GET /referentiels/prices/{branch}` — lookup mercuriale pour autocomplete
3. `POST /claims/{id}/lines` — chaque ligne (étape 2)
4. `POST /claims/{id}/documents` — chaque fichier (étape 3)
5. `POST /claims/{id}/ocr/run` — optionnel (étape 3)
6. `POST /claims/{id}/submit` — bouton final

---

## Page 3 — Détail sinistre (`/claims/[id]`)

### Rôles : G · A · ADM

### Layout

```
┌─────────────────────────────────────────────────────┐
│ En-tête : ID · Branche · Statut · Score · Montant   │
│ Actions contextuelles (selon statut + rôle)          │
├─────────────────────────────────────────────────────┤
│ Onglets : Résumé | Analyse IA | Lignes | Docs | Histo│
├─────────────────────────────────────────────────────┤
│ Contenu de l'onglet actif                           │
└─────────────────────────────────────────────────────┘
```

### En-tête — Composition

```typescript
// Composant ClaimHeader
interface ClaimHeaderProps {
  claim_reference: string;   // "SIN_2025_CM_00842" — mono
  branch: 'SANTE' | 'AUTO';  // BranchPill
  statut: ClaimStatus;       // StatusBadge
  score?: number;            // ScoreBadge — null si non analysé
  is_anomaly?: boolean;      // Icône ⚠ si true
  montant_total: number;     // formatXAF()
  date_soin: string;         // DD/MM/YYYY
  insured_hash: string;      // pseudonymisé
  numero_police: string;
}
```

### Actions contextuelles

```typescript
const contextualActions = (claim: ClaimDetail, permissions: Permission[]) => [
  {
    label: 'Modifier',
    icon: 'pencil',
    href: `/claims/${claim.id}/edit`,
    show: claim.statut === 'DRAFT' && permissions.includes('claims:write')
  },
  {
    label: 'Analyser',
    icon: 'player-play',
    action: () => submitClaim(claim.id),
    show: claim.statut === 'DRAFT' && permissions.includes('claims:submit')
  },
  {
    label: 'Prendre une décision',
    icon: 'gavel',
    href: `/audit/${claim.latest_analysis_id}`,
    show: claim.statut === 'OPEN' && permissions.includes('audit:decide'),
    variant: 'primary'
  },
  {
    label: 'Escalader',
    icon: 'arrow-up',
    action: () => openEscalationModal(claim.id),
    show: claim.statut === 'OPEN' && permissions.includes('escalations:create')
  },
];
```

### Onglet Résumé

- Score IF (jauge circulaire animée, couleur selon seuil)
- Catégorie RCA principale (badge)
- Narration LLM Mistral 7B (bloc texte avec icône modèle)
- Métadonnées : date analyse, durée pipeline, modèle utilisé

### Onglet Analyse IA

- Top 3 features SHAP (barres horizontales avec label + valeur)
- Lien "Voir toutes les features SHAP" → `/audit/[analysis_id]/shap`
- Verdict du modèle avec niveau de confiance
- Catégories RCA détectées (upcoding, unbundling, phantom billing…)

### Onglet Lignes

- Reprend le composant `<ClaimLinesTable>` (même que `/claims/[id]/lines`)
- Lien "Voir en plein écran" → `/claims/[id]/lines`

### Onglet Documents

- Reprend `<DocumentGallery>` (même que `/claims/[id]/documents`)
- Résumé OCR : N documents · N analysés · N alertes
- Lien "Voir tous les documents" → `/claims/[id]/documents`

### Onglet Historique

- Timeline verticale des événements :
  - Créé le XX/XX/XXXX par [user_hash]
  - Soumis à l'analyse le XX/XX/XXXX
  - Résultat disponible — Score 0.78
  - Décision : CONFIRMÉ par [user_hash] le XX/XX/XXXX
  - Escalade créée le XX/XX/XXXX
  - Escalade résolue le XX/XX/XXXX

### Endpoints consommés

- `GET /claims/{claim_id}` — en-tête + données générales
- `GET /claims/{claim_id}/analyses` — onglets Analyse IA + Historique
- `GET /claims/{claim_id}/lines` — onglet Lignes
- `GET /claims/{claim_id}/documents` — onglet Documents
- `GET /claims/{claim_id}/ocr` — indicateurs OCR dans onglet Documents
- `POST /claims/{claim_id}/submit` — bouton Analyser

---

## Page 4 — Modifier sinistre (`/claims/[id]/edit`)

### Rôles : G · ADM

### Condition d'accès

La page redirige vers `/claims/[id]` avec un toast d'erreur si `statut ∉ ['DRAFT', 'OPEN']`.

### Layout

Même structure que le wizard `/claims/new` mais en mode édition. Pré-rempli avec les valeurs actuelles.

### Champs éditables selon statut

| Champ | DRAFT | OPEN |
|---|---|---|
| Branche | ❌ (figé après création) | ❌ |
| Numéro de police | ✅ | ❌ |
| Date du sinistre | ✅ | ❌ |
| Description | ✅ | ✅ |
| Lignes (ajout/modif/suppression) | ✅ | ❌ |
| Documents (ajout) | ✅ | ❌ |
| Documents (suppression) | ADM seulement | ❌ |

### Endpoints consommés

- `GET /claims/{claim_id}` — pré-remplissage
- `PATCH /claims/{claim_id}` — sauvegarde description / date / police
- `PATCH /claims/{claim_id}/lines/{line_id}` — modifier ligne (DRAFT)
- `DELETE /claims/{claim_id}/lines/{line_id}` — supprimer ligne (DRAFT)
- `POST /claims/{claim_id}/lines` — ajouter ligne (DRAFT)

### UX décisions

- Bouton "Sauvegarder" → PATCH + toast succès + redirect `/claims/[id]`
- Bouton "Annuler" → confirm si modifié, sinon redirect direct
- Les champs non éditables sont affichés en lecture seule avec fond gris (`bg-subtle`)

---

## Page 5 — Documents & OCR (`/claims/[id]/documents`)

### Rôles : G · A · ADM

### Layout

```
┌─────────────────────────────────────────────────────┐
│ Titre "Documents"  + [Uploader] (DRAFT + G/ADM)     │
├──────────────────────┬──────────────────────────────┤
│ Galerie (grille 3    │  Panneau détail du doc       │
│ colonnes)            │  sélectionné :               │
│                      │  - Prévisualisation          │
│ [Doc1] [Doc2] [Doc3] │  - Métadonnées               │
│ [Doc4] [Doc5]        │  - Résultats OCR             │
│                      │  - [Télécharger] [OCR] [Suppr]│
└──────────────────────┴──────────────────────────────┘
```

### Carte de document dans la galerie

```typescript
interface DocumentCardProps {
  filename: string;
  mime_type: string;           // icône PDF / image
  file_size_bytes: number;     // formatBytes()
  document_type: string | null;
  hash_sha256: string;         // tronqué à 12 chars, mono
  uploaded_at: string;
  ocr?: OcrResult | null;      // null si OCR pas encore lancé
}
// Indicateurs visuels sur la carte :
// - Badge vert "OCR ✓" si ocr.success === true
// - Badge orange "OCR ⚠" si ocr.flag_altere === true
// - Badge gris "Pas d'OCR" si ocr === null
```

### Panneau de résultats OCR — Champs affichés

| Champ OCR | Label affiché | Format |
|---|---|---|
| `score_confiance_global` | Confiance globale | Jauge + % |
| `score_confiance_montant` | Confiance montant | Jauge + % |
| `montant_extrait` | Montant extrait | XAF |
| `date_soin_extraite` | Date extraite | DD/MM/YYYY |
| `code_acte_extrait` | Code acte | Mono |
| `presence_cachet` | Cachet humide | ✓ Présent / ✗ Absent |
| `flag_altere` | Altération détectée | Badge rouge si true |
| `logiciel_retouche` | Logiciel détecté | Nom ou "Aucun" |
| `llm_backend_used` | Modèle OCR | ex: "ollama/mistral7b" |

> **Contexte CM :** `presence_cachet = false` sur une ordonnance est un signal fort de fraude en contexte camerounais. Ce champ doit être mis en évidence visuellement (icône cachet + tooltip explicatif).

### Endpoints consommés

- `GET /claims/{id}/documents` — liste galerie
- `POST /claims/{id}/documents` — upload (DRAFT, multipart/form-data)
- `GET /claims/{id}/documents/{doc_id}/download` — téléchargement streaming
- `DELETE /claims/{id}/documents/{doc_id}` — suppression (ADM, DRAFT)
- `POST /claims/{id}/ocr/run` — déclenche OCR (G/ADM)
- `GET /claims/{id}/ocr` — récupère tous les résultats OCR

---

## Page 6 — Lignes de détail (`/claims/[id]/lines`)

### Rôles : G · A · ADM

### Layout

```
┌─────────────────────────────────────────────────────┐
│ Titre "Lignes"  + [+ Ajouter une ligne] (DRAFT)     │
├─────────────────────────────────────────────────────┤
│ Tableau des lignes (colonnes selon branche)          │
├─────────────────────────────────────────────────────┤
│ Total : N lignes · Montant total : XXX XAF           │
└─────────────────────────────────────────────────────┘
```

### Colonnes Santé

| Colonne | Source | Format |
|---|---|---|
| Code ASAC | `code_acte` | Mono |
| Libellé acte | `libelle` | Texte |
| Praticien | `praticien_id_hash` | Mono tronqué |
| Quantité | `quantite` | Entier |
| Montant ligne | `montant_ligne` | `formatXAF()` |
| Prix réf. CIMA | `prix_ref` | `formatXAF()` |
| Ratio prix | `ratio_prix` | `<RatioBadge>` |
| Actions | — | Modifier / Supprimer (DRAFT) |

### Colonnes Auto

| Colonne | Source | Format |
|---|---|---|
| Poste | `libelle` | Texte |
| Garage | `garage_id_hash` | Mono tronqué |
| Montant devis | `montant_ligne` | `formatXAF()` |
| Prix réf. CIMA | `prix_ref` | `formatXAF()` |
| Ratio prix | `ratio_prix` | `<RatioBadge>` |
| Actions | — | Modifier / Supprimer (DRAFT) |

### Composant RatioBadge

```typescript
// src/components/features/claims/RatioBadge.tsx
const RatioBadge = ({ ratio }: { ratio: number }) => {
  if (ratio <= RATIO_THRESHOLDS.ok)       return <Badge variant="success">×{ratio.toFixed(2)} ✓</Badge>;
  if (ratio <= RATIO_THRESHOLDS.warning)  return <Badge variant="warning">×{ratio.toFixed(2)} ⚠</Badge>;
  return <Badge variant="danger">×{ratio.toFixed(2)} 🚨</Badge>;
};
// Seuils : ok ≤ 1.10 | warning ≤ 1.30 | danger > 1.30
```

### Endpoints consommés

- `GET /claims/{id}/lines` — tableau complet
- `POST /claims/{id}/lines` — ajouter ligne (DRAFT)
- `PATCH /claims/{id}/lines/{line_id}` — modifier ligne (DRAFT)
- `DELETE /claims/{id}/lines/{line_id}` — supprimer ligne (DRAFT)

---

## Page 7 — Historique des runs d'analyse (`/claims/analyses`)

### Rôles : G · A · ADM

### Layout

```
┌─────────────────────────────────────────────────────┐
│ KPIs : [En attente] [Complétés] [Taux anomalie]     │
├─────────────────────────────────────────────────────┤
│ Filtres : branche, statut run, is_anomaly, dates    │
├─────────────────────────────────────────────────────┤
│ Tableau des runs d'analyse (paginé)                 │
└─────────────────────────────────────────────────────┘
```

### Colonnes du tableau

| Colonne | Source | Format |
|---|---|---|
| ID Run | `analysis_id` | Mono tronqué · cliquable → `/audit/[id]` |
| Sinistre | `claim_reference` | Mono · lien → `/claims/[id]` |
| Branche | `branch` | `<BranchPill>` |
| Score IF | `score` | `<ScoreBadge>` |
| Catégorie RCA | `rca_category` | Texte |
| Anomalie | `is_anomaly` | Icône ⚠ ou ✓ |
| Statut run | `run_status` | Badge PENDING/COMPLETED/FAILED |
| Date | `created_at` | DD/MM/YYYY HH:mm |
| Voir | — | Lien → `/audit/[analysis_id]` |

### Endpoints consommés

- `GET /audit/` — tous les runs filtrables
- `GET /audit/stats` — KPIs en tête de page

---

## Composants à créer pour ce module

| Composant | Chemin | Réutilisé dans |
|---|---|---|
| `<ClaimsTable>` | `features/claims/ClaimsTable.tsx` | `/claims` |
| `<ClaimHeader>` | `features/claims/ClaimHeader.tsx` | `/claims/[id]` |
| `<ClaimCard>` | `features/claims/ClaimCard.tsx` | `/claims/[id]` |
| `<ClaimWizard>` | `features/claims/ClaimWizard.tsx` | `/claims/new` |
| `<ClaimLineEditor>` | `features/claims/ClaimLineEditor.tsx` | wizard étape 2 + `/edit` |
| `<ClaimLinesTable>` | `features/claims/ClaimLinesTable.tsx` | `/claims/[id]` + `/lines` |
| `<DocumentGallery>` | `features/documents/DocumentGallery.tsx` | `/claims/[id]` + `/documents` |
| `<DocumentCard>` | `features/documents/DocumentCard.tsx` | galerie |
| `<OcrResultPanel>` | `features/documents/OcrResultPanel.tsx` | panneau détail doc |
| `<BranchPill>` | `common/BranchPill.tsx` | partout |
| `<ScoreBadge>` | `common/ScoreBadge.tsx` | partout |
| `<StatusBadge>` | `common/StatusBadge.tsx` | partout |
| `<RatioBadge>` | `features/claims/RatioBadge.tsx` | lignes |
| `<DecisionBadge>` | `common/DecisionBadge.tsx` | tableau + détail |
| `<SubmitClaimButton>` | `features/claims/SubmitClaimButton.tsx` | `/claims/[id]` + liste |
| `<EscalationModal>` | `features/escalations/EscalationModal.tsx` | `/claims/[id]` |

---

## Query keys (TanStack Query)

```typescript
// src/hooks/claims/claims.keys.ts
export const CLAIMS_KEYS = {
  all: ['claims'] as const,
  list: (filters: ClaimsFilters) => [...CLAIMS_KEYS.all, 'list', filters] as const,
  detail: (id: string) => [...CLAIMS_KEYS.all, 'detail', id] as const,
  lines: (id: string) => [...CLAIMS_KEYS.all, 'lines', id] as const,
  documents: (id: string) => [...CLAIMS_KEYS.all, 'documents', id] as const,
  ocr: (id: string) => [...CLAIMS_KEYS.all, 'ocr', id] as const,
  analyses: (id: string) => [...CLAIMS_KEYS.all, 'analyses', id] as const,
};
```

---

## Flux de navigation complet

```
/claims  ──────────────────────────────► /claims/new
   │                                          │
   │ (clic sur ligne)                   (POST /claims)
   ▼                                          │
/claims/[id]  ◄───────────────────────────────
   │    │    │    │    │
   │    │    │    │    └──► /claims/[id]/documents
   │    │    │    └───────► /claims/[id]/lines
   │    │    └────────────► /claims/[id]/edit
   │    └─────────────────► /audit/[analysis_id]
   │                             └──► /audit/[analysis_id]/shap
   └─ modal Escalader ──────────► /escalations/[id]

/claims/analyses ──────────────► /audit/[analysis_id]
```

---

*MAKORA_MODULE_SINISTRES.md — Juin 2026 — ATABONG EFON STEPHANE FRITZ*
