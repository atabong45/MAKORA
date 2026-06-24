# MAKORA — Guide de Corrections Frontend/API
> **Fichier :** `FRONTEND_API_CORRECTIONS.md` v1.0  
> **Date :** 31 mai 2026  
> **Auteur :** ATABONG EFON STEPHANE FRITZ  
> **Objet :** Transformer un frontend écrit avec `MAKORA_FRONTEND_DESIGN_SYSTEM.md` v1.0 en une  
> application 100 % fonctionnelle avec l'API réelle (schémas Pydantic v2 + routers FastAPI Phase 3).  
> **Source de vérité API :** `api/schemas/*.py` + `api/routers/*.py` + `project_context.txt`

---

## TABLEAU DE PRIORITÉ — VUE D'ENSEMBLE

| Priorité | Fichier frontend à corriger | Nature de la divergence | Impact si non corrigé |
|---|---|---|---|
| 🔴 **BLOQUANT** | `src/types/common.types.ts` | `items` → `results`, champ `pages` inexistant | Toutes les listes = tableau vide |
| 🔴 **BLOQUANT** | `src/types/api/claims.types.ts` | Type `Claim` entièrement erroné | Sinistres non affichables |
| 🔴 **BLOQUANT** | `src/services/claims.service.ts` | `get(id)` envoie UUID au lieu de `claim_id` string | 404 sur tout accès sinistre |
| 🔴 **BLOQUANT** | `src/validators/claims.validators.ts` | Champ `source_flux` obligatoire absent | 422 à toute création |
| 🔴 **BLOQUANT** | `src/types/api/analysis.types.ts` | Structure `Analysis` erronée | Audit inaffichable |
| 🔴 **BLOQUANT** | `src/services/audit.service.ts` | Ancien endpoint `validate` vs nouveau `decision` | Décisions impossibles |
| 🟠 **IMPORTANT** | `src/types/api/claims.types.ts` | `ClaimLine` — 4 noms de champs incorrects | Tableau lignes cassé |
| 🟠 **IMPORTANT** | `src/types/api/claims.types.ts` | `DocumentMeta` + `OcrResult` — champs différents | Documents/OCR cassés |
| 🟠 **IMPORTANT** | `src/types/api/escalation.types.ts` | `reason`→`motif_escalade`, `resolution`→`resolution_note` | Escalades non créables |
| 🟠 **IMPORTANT** | `src/services/models.service.ts` | `ModelRegisterRequest` — 2 champs required manquants | 422 à l'enregistrement modèle |
| 🟠 **IMPORTANT** | `src/services/claims.service.ts` | Filtres `is_anomaly`, `score_min`, `search`, `branch` non reconnus | Filtres silencieux |
| 🟡 **MINEUR** | `src/services/admin.service.ts` | URL `/admin/system` existe mais `/admin/activity-log` mal nommé | Page admin dégradée |
| 🟡 **MINEUR** | `src/services/apiClient.ts` | URL refresh à vérifier | Refresh token peut échouer |

---

## SECTION 1 — CORRECTIONS DES TYPES TYPESCRIPT

### 1.1 `src/types/common.types.ts` 🔴 BLOQUANT

**Problème :** `PaginatedResponse` utilise `items` alors que tous les routers retournent `results`. Le champ `pages` n'existe pas dans l'API.

```typescript
// ❌ AVANT (Design System v1.0)
export interface PaginatedResponse<T> {
  items: T[];        // ← FAUX — le backend retourne "results"
  total: number;
  page: number;
  page_size: number;
  pages: number;     // ← INEXISTANT dans le backend
}

// ✅ APRÈS (conforme api/schemas/common.py)
export interface PaginatedResponse<T> {
  results: T[];      // ← champ réel du backend
  total: number;
  page: number;
  page_size: number;
  // "pages" supprimé — calculer côté frontend si besoin : Math.ceil(total / page_size)
}

// Helper à ajouter dans src/lib/utils.ts
export function getTotalPages(total: number, pageSize: number): number {
  return Math.ceil(total / pageSize);
}
```

**Impact cascade :** Tous les hooks qui lisent `response.data.items` doivent passer à `response.data.results`.

---

### 1.2 `src/types/api/claims.types.ts` — Type `Claim` 🔴 BLOQUANT

**Problème :** Le type `Claim` du design system reflète une ancienne version de l'API. Le `ClaimResponse` Pydantic réel est significativement différent.

```typescript
// ❌ AVANT (Design System v1.0)
export interface Claim {
  id: string;
  claim_reference: string;   // ← FAUX — s'appelle claim_id
  branch: Branch;            // ← FAUX — s'appelle branch_code (string)
  insured_hash: string;      // ← ABSENT du ClaimResponse
  contract_id: string;       // ← ABSENT du ClaimResponse
  status: ClaimStatus;       // ← FAUX — s'appelle statut
  date_soin: string;
  montant_total: number;     // ← FAUX — s'appelle montant_facture
  description?: string;      // ← ABSENT du ClaimResponse
  is_anomaly: boolean | null;    // ← ABSENT du ClaimResponse (dans Analysis)
  anomaly_score: number | null;  // ← ABSENT du ClaimResponse (dans Analysis)
  created_at: string;
  updated_at: string;
}

// ✅ APRÈS (conforme api/schemas/claims.py → ClaimResponse)
export interface Claim {
  id: string;                          // UUID interne (pour navigation React)
  claim_id: string;                    // ID métier "SIN-SANTE-XXXXXXXX" — utiliser pour les appels API
  branch_code: string | null;          // "sante" | "auto" | "vie" | "agricole"
  source_flux: 'structured' | 'documentary' | 'batch';
  montant_facture: number | null;      // Montant en devise d'origine
  devise: string | null;               // "XAF" par défaut
  montant_xaf: number | null;          // Montant converti en XAF
  date_soin: string | null;            // Format ISO "YYYY-MM-DD"
  date_declaration: string | null;     // Format ISO "YYYY-MM-DD"
  statut: ClaimStatus;                 // "DRAFT" | "SUBMITTED" | "OPEN" | "CLOSED"
  created_at: string;
  updated_at: string;
}

// Type ClaimStatus inchangé
export type ClaimStatus = 'DRAFT' | 'SUBMITTED' | 'OPEN' | 'CLOSED';
```

**Impacts dans les composants :**
- `claim.claim_reference` → `claim.claim_id`
- `claim.branch` → `claim.branch_code`
- `claim.status` → `claim.statut`
- `claim.montant_total` → `claim.montant_facture`
- `claim.is_anomaly` → N/A (lire depuis l'analyse associée)
- `claim.anomaly_score` → N/A (lire depuis l'analyse associée)

---

### 1.3 `src/types/api/claims.types.ts` — Type `ClaimCreate` 🔴 BLOQUANT

```typescript
// ❌ AVANT (Design System — envoyait Partial<Claim>)
// Le service envoyait des champs du vieux type Claim — aucun ne correspond

// ✅ APRÈS (conforme api/schemas/claims.py → ClaimCreate)
export interface ClaimCreate {
  claim_id: string;                                                    // REQUIRED — ex: "SIN-SANTE-2026-0042"
  branch_code: 'sante' | 'auto' | 'vie' | 'agricole';                 // REQUIRED
  source_flux: 'structured' | 'documentary' | 'batch';                 // REQUIRED — défaut: "structured"
  montant_facture?: number;
  devise?: string;                                                     // défaut: "XAF"
  date_soin?: string;                                                  // "YYYY-MM-DD"
  date_declaration?: string;                                           // "YYYY-MM-DD"
}

export interface ClaimUpdate {
  montant_facture?: number;
  devise?: string;
  date_soin?: string;
  date_declaration?: string;
  // Note : branch_code et claim_id ne sont PAS modifiables via PATCH
}
```

---

### 1.4 `src/types/api/claims.types.ts` — Type `ClaimLine` 🟠 IMPORTANT

```typescript
// ❌ AVANT (Design System v1.0)
export interface ClaimLine {
  id: string;
  claim_id: string;
  code_acte: string;
  libelle: string;
  quantite: number;
  montant_unitaire: number;   // ← FAUX — s'appelle montant_ligne
  montant_total: number;      // ← FAUX — champ inexistant
  prix_reference: number | null;  // ← FAUX — s'appelle prix_ref
  ecart_mercuriale: number | null; // ← FAUX — s'appelle ratio_prix
}

// ✅ APRÈS (conforme api/schemas/claims.py → ClaimLineResponse)
export interface ClaimLine {
  id: string;                      // UUID
  claim_id: string;                // UUID du sinistre
  code_acte: string | null;
  libelle: string | null;
  montant_ligne: number | null;    // Montant pour cette ligne
  quantite: number;                // Défaut: 1
  praticien_id_hash: string | null; // Nouveau champ
  garage_id_hash: string | null;   // Nouveau champ
  prix_ref: number | null;         // Prix de référence mercuriale (ex-prix_reference)
  ratio_prix: number | null;       // Ratio facturé/référence (ex-ecart_mercuriale)
  created_at: string;
}

// Pour la création
export interface ClaimLineCreate {
  code_acte?: string;
  libelle?: string;
  montant_ligne?: number;
  quantite?: number;
  praticien_id_hash?: string;
  garage_id_hash?: string;
}
```

**Impacts dans les composants :**
- `line.montant_unitaire` → `line.montant_ligne`
- `line.ecart_mercuriale` → `line.ratio_prix`
- `line.prix_reference` → `line.prix_ref`
- Supprimer `line.montant_total` (n'existe pas)

---

### 1.5 `src/types/api/claims.types.ts` — `DocumentMeta` et `OcrResult` 🟠 IMPORTANT

```typescript
// ❌ AVANT — DocumentMeta
export interface ClaimDocument {
  id: string;
  claim_id: string;
  filename: string;
  mime_type: string;
  size_bytes: number;       // ← FAUX
  sha256_hash: string;      // ← FAUX
  uploaded_at: string;
}

// ✅ APRÈS (conforme api/schemas/claims.py → DocumentMeta)
export interface ClaimDocument {
  id: string;                       // UUID
  claim_id: string;                 // UUID
  filename: string;
  mime_type: string;
  file_size_bytes: number;          // ex-size_bytes
  document_type: string | null;     // Nouveau champ
  hash_sha256: string;              // ex-sha256_hash (ordre inversé)
  uploaded_at: string;
}

// ❌ AVANT — OcrExtraction (très incomplet)
export interface OcrExtraction {
  id: string;
  document_id: string;
  score_confiance: number;      // ← FAUX
  montant_extrait: number | null;
  flag_altere: boolean;
  extracted_text: string;       // ← ABSENT
  processed_at: string;         // ← FAUX — s'appelle created_at
}

// ✅ APRÈS (conforme api/schemas/claims.py → OcrResult)
export interface OcrResult {
  id: string;                        // UUID
  document_id: string;               // UUID
  score_confiance_global: number;    // ex-score_confiance
  score_confiance_montant: number;   // Nouveau
  montant_extrait: number | null;
  devise_extraite: string | null;    // Nouveau
  date_soin_extraite: string | null; // Nouveau — "YYYY-MM-DD"
  code_acte_extrait: string | null;  // Nouveau
  presence_cachet: boolean;          // Nouveau — important contexte CM
  flag_altere: boolean;
  logiciel_retouche: string | null;  // Nouveau
  success: boolean;                  // Nouveau
  error_code: string | null;         // Nouveau
  llm_backend_used: string;          // Nouveau — "ollama/mistral7b" etc.
  created_at: string;                // ex-processed_at
  // SUPPRIMÉ : extracted_text (non retourné par l'API)
}
```

---

### 1.6 `src/types/api/analysis.types.ts` — Types Analysis et SHAP 🔴 BLOQUANT

L'API expose **deux structures distinctes** selon le contexte — liste vs détail. Le design system n'en avait qu'une, incorrecte.

```typescript
// ✅ Structure 1 — Item de liste (GET /audit/ — AuditListItem)
export interface AuditListItem {
  analysis_id: string;          // UUID — utiliser pour naviguer vers le détail
  claim_id: string | null;      // ID métier du sinistre lié (string, pas UUID)
  branch: string | null;        // "sante" | "auto"
  anomaly_score: number;
  is_anomaly: boolean;
  rca_category: string | null;
  rca_subcategory: string | null;
  decision_status: DecisionStatus;
  created_at: string;
  // ABSENT dans la liste : run_id, model_version_id, rca_confidence, llm_narration, shap_top3
}

// ✅ Structure 2 — Détail complet (GET /audit/{analysis_id} — AnalysisResult)
export interface AnalysisResult {
  analysis_id: string | null;   // UUID
  claim_id: string;             // ID métier
  branch: string;               // "sante" | "auto"
  anomaly_score: number;
  is_anomaly: boolean;
  processing_time_ms: number | null;
  rca: RcaResult | null;        // Contient SHAP + narration
  graph_analysis: Record<string, unknown> | null;
  decision_status: DecisionStatus;
}

// ✅ Structure RCA — rca.top_features remplace l'ancien shap_top3
export interface RcaResult {
  category: string | null;
  subcategory: string | null;
  confidence: number | null;
  rule_triggered: string | null;
  top_features: ShapFeatureSummary[];  // Équivalent de l'ancien shap_top3
  explanation_fr: string | null;       // Narration LLM (ex-llm_narration au top-level)
}

// ✅ SHAP dans le contexte RCA (rca.top_features) — usage: page audit/{id} et décision HITL
export interface ShapFeatureSummary {
  name: string;         // ex-feature_name (NOM DIFFÉRENT)
  shap_value: number;
  direction: string;    // "positive" | "negative"
  rank: number;
  // ABSENT : feature_value (disponible uniquement via GET /audit/{id}/shap)
}

// ✅ SHAP complet (GET /audit/{analysis_id}/shap) — usage: page /audit/[id]/shap
export interface ShapContributionFull {
  id: string;                    // UUID (nouveau)
  feature_name: string;          // Même nom que dans Design System
  shap_value: number;
  feature_value: number | null;  // Disponible ici seulement
  direction: string;
  rank: number;                  // Nouveau
}

// ✅ Décision
export type DecisionStatus = 'PENDING' | 'CONFIRMED' | 'REJECTED' | 'ESCALATED';

export interface DecisionCreate {
  decision: 'CONFIRMED' | 'REJECTED' | 'ESCALATED';
  motif: string | null;
  // NOTE : gestionnaire_id ne doit PAS être envoyé — extrait du JWT côté backend
}

export interface DecisionResponse {
  id: string;              // UUID
  analysis_id: string;     // UUID
  decision: string;
  motif: string | null;
  gestionnaire_id: string; // UUID (ex-decided_by)
  created_at: string;
}
```

**Règle de migration dans les composants :**
- `analysis.shap_top3` → `analysis.rca?.top_features ?? []`
- `analysis.llm_narration` → `analysis.rca?.explanation_fr ?? null`
- `analysis.rca_confidence` → `analysis.rca?.confidence ?? null`
- `shap.feature_name` (dans top_features) → `shap.name`
- `analysis.id` (liste) → `analysis.analysis_id`

---

### 1.7 `src/types/api/escalation.types.ts` — Types Escalade 🟠 IMPORTANT

```typescript
// ❌ AVANT (Design System — champs supposés)
// (les noms exacts n'étaient pas tous définis mais les corrections ci-dessous s'appliquent)

// ✅ APRÈS (conforme api/schemas/escalations.py)
export interface EscalationCreate {
  analysis_id: string;    // UUID de l'analyse à escalader (REQUIRED)
  motif_escalade: string; // ex-"reason" — REQUIRED, non optionnel
}

export interface EscalationAssign {
  assigned_to: string;    // UUID de l'auditeur
}

export interface EscalationResolve {
  resolution_note: string; // ex-"resolution" — REQUIRED à la résolution
}

export interface Escalation {
  id: string;              // UUID
  analysis_id: string;     // UUID
  escalated_by: string;    // UUID
  assigned_to: string | null;
  motif_escalade: string;  // ex-"reason" / "motif"
  statut: 'PENDING' | 'IN_PROGRESS' | 'RESOLVED';  // ex-"status"
  resolution_note: string | null;   // ex-"resolution"
  created_at: string;
  assigned_at: string | null;       // Nouveau
  resolved_at: string | null;       // Nouveau
}
```

---

### 1.8 `src/types/api/governance.types.ts` — Modèles ML 🟠 IMPORTANT

```typescript
// ✅ ModelRegisterRequest (conforme api/schemas/governance.py)
export interface ModelRegisterRequest {
  branch_code: string;         // REQUIRED
  algorithm: string;           // ex: "isolation_forest" — défaut OK
  version_tag: string;         // REQUIRED ex: "v1.2.0"
  file_path: string;           // REQUIRED — chemin joblib sur le serveur
  contamination: number;       // REQUIRED — ex: 0.08
  feature_names: string[];     // REQUIRED — liste des features utilisées
  f1_score?: number;
  auc_roc?: number;
  mcc?: number;
  fpr?: number;
  train_size?: number;
}

// ✅ ModelVersionResponse — tous les champs
export interface ModelVersion {
  id: string;               // UUID
  branch_id: string;        // UUID (pas branch_code string)
  algorithm: string;
  version_tag: string;
  contamination: number;
  f1_score: number | null;
  auc_roc: number | null;
  precision_ppv: number | null;
  recall_tpr: number | null;
  fpr: number | null;
  mcc: number | null;
  train_size: number | null;
  trained_at: string;
  created_at: string;
}

// ✅ DeployRequest
export interface DeployRequest {
  model_version_id: string;   // UUID
  deployment_notes?: string;
}
```

---

### 1.9 `src/types/api/referentiels.types.ts` — Référentiels 🟠 IMPORTANT

```typescript
// ✅ ReferencePriceImport (POST /referentiels/prices)
export interface ReferencePriceImport {
  branch_code: string;         // ex-"branch" — REQUIRED
  code_acte: string;           // REQUIRED
  libelle?: string;
  nomenclature: string;        // REQUIRED — "ASAC" | "CCAM" | "ARGUS"
  prix_ref_xaf?: number;
  prix_ref_eur?: number;
  devise_principale?: string;  // défaut "XAF"
  valid_from: string;          // REQUIRED — "YYYY-MM-DD"
  source_document?: string;
}

// ✅ ReferencePriceResponse
export interface ReferencePrice {
  id: string;            // UUID
  branch_id: string;     // UUID
  code_acte: string;
  libelle: string | null;
  nomenclature: string;
  prix_ref_xaf: number | null;
  prix_ref_eur: number | null;
  devise_principale: string;
  valid_from: string;
  valid_to: string | null;
  source_document: string | null;
}
```

---

## SECTION 2 — CORRECTIONS DES SERVICES API

### 2.1 `src/services/claims.service.ts` 🔴 BLOQUANT

```typescript
// ❌ AVANT — Problèmes multiples
export interface ClaimsFilters {
  branch?: string;       // ← mauvais nom de paramètre
  status?: string;       // ← mauvais nom de paramètre
  is_anomaly?: boolean;  // ← filtre inexistant côté backend
  score_min?: number;    // ← filtre inexistant côté backend
  search?: string;       // ← filtre inexistant côté backend
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

// get(id) envoyait l'UUID interne — le router attend le claim_id métier (string)
get: (id: string) => apiClient.get<Claim>(`/claims/${id}`),

// create envoyait Partial<Claim> — le schema ClaimCreate est différent
create: (data: Partial<Claim>) => apiClient.post<Claim>('/claims/', data),

// ✅ APRÈS — claims.service.ts corrigé
export interface ClaimsFilters {
  branch_code?: string;         // ex-"branch"
  statut?: ClaimStatus;         // ex-"status"
  date_from?: string;           // "YYYY-MM-DD"
  date_to?: string;             // "YYYY-MM-DD"
  page?: number;
  page_size?: number;
  // SUPPRIMÉS : is_anomaly (non supporté), score_min (non supporté), search (non supporté)
}

export const claimsService = {
  list: (filters: ClaimsFilters) =>
    apiClient.get<PaginatedResponse<Claim>>('/claims/', { params: filters }),

  // CORRECTION CRITIQUE : passer claim_id (string métier), PAS l'UUID interne
  get: (claimId: string) =>
    apiClient.get<Claim>(`/claims/${claimId}`),

  // CORRECTION : typage correct ClaimCreate
  create: (data: ClaimCreate) =>
    apiClient.post<Claim>('/claims/', data),

  // CORRECTION : typage correct ClaimUpdate (4 champs seulement)
  update: (claimId: string, data: ClaimUpdate) =>
    apiClient.patch<Claim>(`/claims/${claimId}`, data),

  // submit utilise claim_id métier aussi
  submit: (claimId: string) =>
    apiClient.post(`/claims/${claimId}/submit`),

  getLines: (claimId: string) =>
    apiClient.get<ClaimLine[]>(`/claims/${claimId}/lines`),

  addLine: (claimId: string, data: ClaimLineCreate) =>
    apiClient.post<ClaimLine>(`/claims/${claimId}/lines`, data),

  updateLine: (claimId: string, lineId: string, data: Partial<ClaimLineCreate>) =>
    apiClient.patch<ClaimLine>(`/claims/${claimId}/lines/${lineId}`, data),

  deleteLine: (claimId: string, lineId: string) =>
    apiClient.delete(`/claims/${claimId}/lines/${lineId}`),

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

  // OCR — body avec document_id
  runOcr: (claimId: string, docId: string) =>
    apiClient.post(`/claims/${claimId}/ocr/run`, { document_id: docId }),

  getOcrResults: (claimId: string) =>
    apiClient.get<OcrResult[]>(`/claims/${claimId}/ocr`),

  getAnalyses: (claimId: string) =>
    apiClient.get(`/claims/${claimId}/analyses`),
};
```

**Règle dans les hooks :** Les hooks qui reçoivent un objet `Claim` doivent extraire `claim.claim_id` (string métier) pour tout appel API, et `claim.id` (UUID) pour les clés React/TanStack Query.

```typescript
// Exemple dans useClaimLines.ts
export function useClaimLines(claim: Claim | undefined) {
  return useQuery({
    queryKey: CLAIMS_KEYS.lines(claim?.id ?? ''),  // UUID pour la query key
    queryFn: () => claimsService.getLines(claim!.claim_id),  // claim_id métier pour l'API
    enabled: !!claim,
  });
}
```

---

### 2.2 `src/services/audit.service.ts` 🔴 BLOQUANT

```typescript
// ❌ AVANT — Problèmes multiples
// 1. L'ancien API_CONTRACTS.md avait POST /audit/{claim_id}/validate
//    → Le nouveau router utilise POST /audit/{analysis_id}/decision
// 2. AuditFilters utilisait "branch" et "is_anomaly" comme filtres

export interface AuditFilters {
  branch?: string;
  decision_status?: DecisionStatus;
  score_min?: number;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

// ✅ APRÈS (conforme api/routers/audit.py)
export interface AuditFilters {
  branch?: string;               // Supporté côté backend
  decision_status?: DecisionStatus;
  score_min?: number;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export const auditService = {
  list: (filters: AuditFilters) =>
    apiClient.get<PaginatedResponse<AuditListItem>>('/audit/', { params: filters }),

  getStats: () =>
    apiClient.get('/audit/stats'),

  getAnalysis: (analysisId: string) =>
    apiClient.get<AnalysisResult>(`/audit/${analysisId}`),

  // CORRECTION CRITIQUE : endpoint /decision (pas /validate)
  createDecision: (analysisId: string, data: DecisionCreate) =>
    apiClient.post<DecisionResponse>(`/audit/${analysisId}/decision`, data),

  getDecisionHistory: (analysisId: string) =>
    apiClient.get<DecisionResponse[]>(`/audit/${analysisId}/decisions`),

  getShapValues: (analysisId: string) =>
    apiClient.get<ShapContributionFull[]>(`/audit/${analysisId}/shap`),
};
```

---

### 2.3 `src/services/escalations.service.ts` 🟠 IMPORTANT

```typescript
// ✅ APRÈS (conforme api/routers/escalations.py)
export const escalationsService = {
  list: (params?: { statut?: string; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<Escalation>>('/escalations/', { params }),

  getPending: (params?: { page?: number; page_size?: number }) =>
    apiClient.get<PaginatedResponse<Escalation>>('/escalations/pending', { params }),

  get: (escalationId: string) =>
    apiClient.get<Escalation>(`/escalations/${escalationId}`),

  // CORRECTION : body = EscalationCreate avec motif_escalade (pas reason)
  create: (data: EscalationCreate) =>
    apiClient.post<Escalation>('/escalations/', data),

  assign: (escalationId: string, data: EscalationAssign) =>
    apiClient.patch<Escalation>(`/escalations/${escalationId}/assign`, data),

  // CORRECTION : body = EscalationResolve avec resolution_note (pas resolution)
  resolve: (escalationId: string, data: EscalationResolve) =>
    apiClient.patch<Escalation>(`/escalations/${escalationId}/resolve`, data),
};
```

---

### 2.4 `src/services/models.service.ts` 🟠 IMPORTANT

```typescript
// ✅ APRÈS — champs required ajoutés dans ModelRegisterRequest
export const modelsService = {
  list: (params?: { branch?: string; algorithm?: string }) =>
    apiClient.get<PaginatedResponse<ModelVersion>>('/models/', { params }),

  get: (modelId: string) =>
    apiClient.get<ModelVersion>(`/models/${modelId}`),

  // CORRECTION : file_path et feature_names sont REQUIRED
  register: (data: ModelRegisterRequest) =>
    apiClient.post<ModelVersion>('/models/register', data),

  getCurrentForBranch: (branch: string) =>
    apiClient.get<ModelVersion>(`/models/branch/${branch}/current`),

  getHistoryForBranch: (branch: string) =>
    apiClient.get<ModelVersion[]>(`/models/branch/${branch}/history`),

  deploy: (data: DeployRequest) =>
    apiClient.post('/models/deploy', data),

  getDeployments: () =>
    apiClient.get('/models/deployments'),
};
```

---

### 2.5 `src/services/admin.service.ts` 🟡 MINEUR

```typescript
// Note : /admin/system EXISTE (endpoint #115) — pas de correction URL nécessaire
// Vérifier le nom exact de l'endpoint journal d'activité

// ✅ APRÈS
export const adminService = {
  getBranches: () =>
    apiClient.get('/admin/branches'),

  getBranch: (code: string) =>
    apiClient.get(`/admin/branches/${code}`),

  updateBranch: (code: string, data: unknown) =>
    apiClient.patch(`/admin/branches/${code}`, data),

  toggleBranch: (code: string) =>
    apiClient.patch(`/admin/branches/${code}/toggle`),

  getSystemStatus: () =>
    apiClient.get('/admin/system'),       // ✅ Endpoint EXISTS (#115)

  getActivityLog: (params?: unknown) =>
    apiClient.get('/admin/activity-log', { params }),  // ✅ Endpoint EXISTS (#116)
};
```

---

### 2.6 `src/services/apiClient.ts` 🟡 MINEUR (vérification refresh)

```typescript
// Vérifier que l'URL de refresh est correcte
// ✅ L'endpoint est POST /auth/refresh (pas /auth/refresh-token)
// La réponse retourne { access_token: string } — un seul champ

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      try {
        const refreshToken = useAuthStore.getState().refreshToken;
        // ✅ URL correcte : /api/v1/auth/refresh
        const { data } = await axios.post(
          `${process.env.NEXT_PUBLIC_API_URL}/auth/refresh`,
          { refresh_token: refreshToken }
        );
        // data.access_token — le refresh_token n'est PAS renouvelé à cette étape
        useAuthStore.getState().setTokens(data.access_token, refreshToken!);
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

---

## SECTION 3 — CORRECTIONS DES VALIDATORS ZOD

### 3.1 `src/lib/validators/claims.validators.ts` 🔴 BLOQUANT

```typescript
import { z } from 'zod';

// ✅ Schema ClaimCreate — source_flux OBLIGATOIRE (cause 422 si absent)
export const claimCreateSchema = z.object({
  claim_id: z.string().min(3, 'ID sinistre requis'),
  branch_code: z.enum(['sante', 'auto', 'vie', 'agricole'], {
    errorMap: () => ({ message: 'Branche invalide' }),
  }),
  source_flux: z.enum(['structured', 'documentary', 'batch'], {
    errorMap: () => ({ message: 'Source flux requise' }),
  }),
  montant_facture: z.number().positive().optional(),
  devise: z.string().default('XAF'),
  date_soin: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  date_declaration: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
});

// ✅ Schema ClaimUpdate — seulement les 4 champs patchables
export const claimUpdateSchema = z.object({
  montant_facture: z.number().positive().optional(),
  devise: z.string().optional(),
  date_soin: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
  date_declaration: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).optional(),
});

export type ClaimCreateInput = z.infer<typeof claimCreateSchema>;
export type ClaimUpdateInput = z.infer<typeof claimUpdateSchema>;
```

### 3.2 `src/lib/validators/escalations.validators.ts` 🟠 IMPORTANT

```typescript
import { z } from 'zod';

export const escalationCreateSchema = z.object({
  analysis_id: z.string().uuid('ID analyse invalide'),
  motif_escalade: z.string().min(10, 'Motif trop court (10 caractères minimum)'),
  // SUPPRIMÉ : "reason" — le champ s'appelle motif_escalade
});

export const escalationResolveSchema = z.object({
  resolution_note: z.string().min(5, 'Note de résolution requise'),
  // SUPPRIMÉ : "resolution" — le champ s'appelle resolution_note
});
```

### 3.3 `src/lib/validators/models.validators.ts` 🟠 IMPORTANT

```typescript
import { z } from 'zod';

export const modelRegisterSchema = z.object({
  branch_code: z.enum(['sante', 'auto']),
  algorithm: z.enum(['isolation_forest', 'lof', 'one_class_svm']).default('isolation_forest'),
  version_tag: z.string().min(1),
  file_path: z.string().min(1, 'Chemin du fichier modèle requis'),  // REQUIRED — était absent
  contamination: z.number().min(0).max(0.5),
  feature_names: z.array(z.string()).min(1, 'Au moins une feature requise'),  // REQUIRED — était absent
  f1_score: z.number().min(0).max(1).optional(),
  auc_roc: z.number().min(0).max(1).optional(),
  mcc: z.number().min(-1).max(1).optional(),
  fpr: z.number().min(0).max(1).optional(),
  train_size: z.number().int().positive().optional(),
});
```

---

## SECTION 4 — CORRECTIONS DANS LES COMPOSANTS

### 4.1 `ClaimsTable.tsx` — Colonnes à corriger

```typescript
// ❌ AVANT                       ✅ APRÈS
// row.claim_reference         → row.claim_id
// row.branch                  → row.branch_code
// row.status                  → row.statut
// row.montant_total            → row.montant_facture
// row.is_anomaly               → (lire depuis analyse associée, pas depuis Claim)
// row.anomaly_score            → (lire depuis analyse associée)
// row.insured_hash             → SUPPRIMER (non retourné)
// row.description              → SUPPRIMER (non retourné)

// Exemple de colonne corrigée :
const columns: Column<Claim>[] = [
  {
    key: 'claim_id',       // ex-claim_reference
    header: 'Référence',
    render: (row) => <span className="font-mono text-sm">{row.claim_id}</span>,
  },
  {
    key: 'branch_code',    // ex-branch
    header: 'Branche',
    render: (row) => <BranchPill branch={row.branch_code as Branch} />,
  },
  {
    key: 'statut',         // ex-status
    header: 'Statut',
    render: (row) => <ClaimStatusBadge status={row.statut} />,
  },
  {
    key: 'montant_facture', // ex-montant_total
    header: 'Montant',
    render: (row) => <CurrencyDisplay amount={row.montant_facture} />,
  },
];
```

### 4.2 `ClaimLinesTable.tsx` — Colonnes à corriger

```typescript
// ❌ AVANT                       ✅ APRÈS
// line.montant_unitaire        → line.montant_ligne
// line.montant_total           → SUPPRIMER (n'existe pas)
// line.prix_reference          → line.prix_ref
// line.ecart_mercuriale        → line.ratio_prix

// Le composant RatioBadge doit utiliser line.ratio_prix
```

### 4.3 `DocumentCard.tsx` — Champs à corriger

```typescript
// ❌ AVANT                       ✅ APRÈS
// doc.size_bytes               → doc.file_size_bytes
// doc.sha256_hash              → doc.hash_sha256
```

### 4.4 `OcrResultCard.tsx` — Champs à corriger

```typescript
// ❌ AVANT                       ✅ APRÈS
// ocr.score_confiance          → ocr.score_confiance_global
// ocr.extracted_text           → SUPPRIMER (non retourné)
// ocr.processed_at             → ocr.created_at

// Nouveaux champs à afficher :
// ocr.presence_cachet          → Badge "Cachet présent / absent"
// ocr.score_confiance_montant  → Confiance spécifique au montant extrait
// ocr.llm_backend_used         → Info technique (tooltip)
// ocr.logiciel_retouche        → ⚠️ alerte si non null
```

### 4.5 `AuditTable.tsx` — Champs à corriger

```typescript
// ❌ AVANT (utilisait Analysis)  ✅ APRÈS (utilise AuditListItem)
// analysis.id                  → analysis.analysis_id
// analysis.branch              → analysis.branch (identique, ok)
// analysis.shap_top3           → ABSENT dans la liste (disponible seulement dans le détail)
// analysis.llm_narration       → ABSENT dans la liste
// analysis.rca_confidence      → ABSENT dans la liste
```

### 4.6 `DecisionPanel.tsx` — Corrections critiques

```typescript
// ❌ AVANT (utilisait /audit/{claim_id}/validate)
// ✅ APRÈS : utiliser auditService.createDecision(analysis_id, data)
// L'analysis_id vient de l'URL : /audit/[analysis_id]

// Pour afficher le contexte SHAP dans le panel :
// analysis.rca?.top_features (pas analysis.shap_top3)
// analysis.rca?.explanation_fr (pas analysis.llm_narration)
// analysis.rca?.confidence (pas analysis.rca_confidence)

// Dans ShapBarChart : props feature.name (pas feature.feature_name)
// feature_value absent dans top_features → ne pas afficher
```

### 4.7 `EscalationModal.tsx` — Champs à corriger

```typescript
// Corps du formulaire de création :
const payload: EscalationCreate = {
  analysis_id: analysisId,    // UUID
  motif_escalade: motifValue, // ex-reason / ex-motif
};

// Corps du formulaire de résolution :
const payload: EscalationResolve = {
  resolution_note: noteValue, // ex-resolution
};
```

### 4.8 `EscalationCard.tsx` / `EscalationsTable.tsx`

```typescript
// ❌ AVANT                        ✅ APRÈS
// escalation.reason             → escalation.motif_escalade
// escalation.resolution         → escalation.resolution_note
// escalation.status             → escalation.statut
// ('OPEN' | 'CLOSED' | ...)     → 'PENDING' | 'IN_PROGRESS' | 'RESOLVED'
```

---

## SECTION 5 — CORRECTIONS RBAC ET NAVIGATION

### 5.1 Notification Bell — `NotificationBell.tsx`

```typescript
// ❌ AVANT : cloche appelait GET /escalations/pending pour TOUS les rôles
// ✅ APRÈS : /escalations/pending requiert rôle auditeur ou administrateur
// Les gestionnaires N'ONT PAS accès à cet endpoint → HTTP 403

// Solution : conditionner l'appel selon le rôle
const canSeeEscalations = hasPermission(roles, 'escalations:resolve');

// Pour les gestionnaires, ne montrer que le compteur drift
const { data: driftStatus } = useQuery({
  queryKey: ['drift', 'status'],
  queryFn: () => driftService.getStatus(),
  enabled: hasPermission(roles, 'drift:read'),
});
```

### 5.2 `useClaim` — Paramètre correct

```typescript
// ❌ AVANT
export function useClaim(id: string) {
  return useQuery({
    queryKey: CLAIMS_KEYS.detail(id),
    queryFn: () => claimsService.get(id).then(r => r.data),
    // "id" était l'UUID interne → 404
  });
}

// ✅ APRÈS — distinguer UUID (query key) et claim_id (appel API)
export function useClaim(claim_id: string) {
  return useQuery({
    queryKey: CLAIMS_KEYS.detail(claim_id),
    queryFn: () => claimsService.get(claim_id).then(r => r.data),
    enabled: !!claim_id,
    // claim_id = "SIN-SANTE-XXXXXXXX" (string métier)
  });
}

// Dans la page /claims/[id]/page.tsx, params.id = claim_id métier (pas UUID)
// Configurer les routes Next.js pour que le paramètre dynamique soit le claim_id
```

---

## SECTION 6 — TABLEAU RÉCAPITULATIF COMPLET

| Fichier | Ligne/Champ | Ancien | Nouveau | Priorité |
|---|---|---|---|---|
| `common.types.ts` | `PaginatedResponse.items` | `items: T[]` | `results: T[]` | 🔴 |
| `common.types.ts` | `PaginatedResponse.pages` | `pages: number` | **Supprimer** | 🔴 |
| `claims.types.ts` | `Claim.claim_reference` | `claim_reference` | `claim_id` | 🔴 |
| `claims.types.ts` | `Claim.branch` | `branch: Branch` | `branch_code: string` | 🔴 |
| `claims.types.ts` | `Claim.status` | `status` | `statut` | 🔴 |
| `claims.types.ts` | `Claim.montant_total` | `montant_total` | `montant_facture` | 🔴 |
| `claims.types.ts` | `Claim.is_anomaly` | présent | **Supprimer** (dans Analysis) | 🟠 |
| `claims.types.ts` | `Claim.anomaly_score` | présent | **Supprimer** (dans Analysis) | 🟠 |
| `claims.types.ts` | `Claim.insured_hash` | présent | **Supprimer** | 🟠 |
| `claims.types.ts` | `Claim.contract_id` | présent | **Supprimer** | 🟠 |
| `claims.types.ts` | `Claim.description` | présent | **Supprimer** | 🟡 |
| `claims.types.ts` | `ClaimCreate` | `Partial<Claim>` | `ClaimCreate` complet | 🔴 |
| `claims.types.ts` | `ClaimLine.montant_unitaire` | `montant_unitaire` | `montant_ligne` | 🟠 |
| `claims.types.ts` | `ClaimLine.montant_total` | présent | **Supprimer** | 🟠 |
| `claims.types.ts` | `ClaimLine.prix_reference` | `prix_reference` | `prix_ref` | 🟠 |
| `claims.types.ts` | `ClaimLine.ecart_mercuriale` | `ecart_mercuriale` | `ratio_prix` | 🟠 |
| `claims.types.ts` | `DocumentMeta.size_bytes` | `size_bytes` | `file_size_bytes` | 🟠 |
| `claims.types.ts` | `DocumentMeta.sha256_hash` | `sha256_hash` | `hash_sha256` | 🟠 |
| `claims.types.ts` | `OcrExtraction.score_confiance` | `score_confiance` | `score_confiance_global` | 🟠 |
| `claims.types.ts` | `OcrExtraction.extracted_text` | présent | **Supprimer** | 🟠 |
| `claims.types.ts` | `OcrExtraction.processed_at` | `processed_at` | `created_at` | 🟡 |
| `analysis.types.ts` | `Analysis` | Structure plate | `AuditListItem` + `AnalysisResult` | 🔴 |
| `analysis.types.ts` | `Analysis.shap_top3` | top-level | `rca.top_features` | 🔴 |
| `analysis.types.ts` | `Analysis.llm_narration` | top-level | `rca.explanation_fr` | 🔴 |
| `analysis.types.ts` | `ShapContribution.feature_name` | `feature_name` | `name` (dans top_features) | 🔴 |
| `escalation.types.ts` | `EscalationCreate.reason` | `reason` | `motif_escalade` | 🟠 |
| `escalation.types.ts` | `EscalationResolve.resolution` | `resolution` | `resolution_note` | 🟠 |
| `escalation.types.ts` | `Escalation.status` | `status` | `statut` | 🟠 |
| `escalation.types.ts` | `Escalation.reason` | `reason` | `motif_escalade` | 🟠 |
| `escalation.types.ts` | `Escalation.resolution` | `resolution` | `resolution_note` | 🟠 |
| `governance.types.ts` | `ModelRegisterRequest.file_path` | absent | **Ajouter** (REQUIRED) | 🟠 |
| `governance.types.ts` | `ModelRegisterRequest.feature_names` | absent | **Ajouter** (REQUIRED) | 🟠 |
| `claims.service.ts` | `get(id)` | UUID interne | `claim_id` string métier | 🔴 |
| `claims.service.ts` | `list()` — `branch` | `branch` | `branch_code` | 🟠 |
| `claims.service.ts` | `list()` — `status` | `status` | `statut` | 🟠 |
| `claims.service.ts` | `list()` — `is_anomaly` | présent | **Supprimer** | 🟠 |
| `claims.service.ts` | `list()` — `score_min` | présent | **Supprimer** | 🟠 |
| `claims.service.ts` | `list()` — `search` | présent | **Supprimer** | 🟠 |
| `audit.service.ts` | `validate()` endpoint | `/audit/{id}/validate` | `/audit/{id}/decision` | 🔴 |
| `claims.validators.ts` | `source_flux` | absent | **Ajouter** (REQUIRED enum) | 🔴 |
| `escalations.validators.ts` | `motif_escalade` | `reason` | `motif_escalade` | 🟠 |
| `escalations.validators.ts` | `resolution_note` | `resolution` | `resolution_note` | 🟠 |

---

## SECTION 7 — MAPPING NAVIGATION SINISTRES

Les routes dynamiques Next.js doivent être configurées avec le `claim_id` métier (pas l'UUID) :

```
/claims/[id]                → params.id = claim_id métier (ex: "SIN-SANTE-2026-0042")
/claims/[id]/lines          → params.id = claim_id métier
/claims/[id]/documents      → params.id = claim_id métier
/audit/[analysis_id]        → params.analysis_id = UUID (format "xxxxxxxx-xxxx-...")
/audit/[analysis_id]/shap   → params.analysis_id = UUID
/escalations/[id]           → params.id = UUID escalade
```

**Dans le `ClaimsTable` :**
```typescript
// ✅ Navigation vers le détail — utiliser claim_id string
router.push(`/claims/${row.claim_id}`);

// ✅ Navigation vers l'audit — utiliser analysis_id UUID
router.push(`/audit/${analysis.analysis_id}`);
```

---

## SECTION 8 — NOTES CONTEXTE CAMEROUNAIS

Ces corrections sont spécifiques au contexte africain/camerounais de MAKORA :

1. **Cachet humide** : Le champ `ocr.presence_cachet` (boolean) est critique. Afficher un badge "Cachet présent ✓ / absent ⚠️" sur `OcrResultCard`. En contexte CM, l'absence de cachet augmente le risque de fraude documentaire.

2. **`logiciel_retouche`** : Si non null, afficher une alerte "Document potentiellement retouché avec [logiciel]" (rouge).

3. **Devise XAF** : `claim.montant_facture` est en devise d'origine, `claim.montant_xaf` est le montant converti. Afficher `montant_xaf` dans les tableaux de comparaison pour cohérence, `montant_facture + devise` dans les formulaires de saisie.

4. **Nomenclature ASAC** : Dans les formulaires de lignes (ClaimLineEditor), le champ `code_acte` doit référencer l'ASAC pour les sinistres `branch_code = "sante"` — appel `GET /referentiels/prices/sante?code_acte=...` pour validation.

5. **`ratio_prix`** (ex-`ecart_mercuriale`) : Ratio `montant_facturé / prix_ref`. Un ratio > 1.30 déclenche l'alerte mercuriale (`RATIO_THRESHOLDS.warning`). Afficher avec le composant `<RatioBadge>`.

---

*MAKORA_FRONTEND_CORRECTIONS.md v1.0 — 31 mai 2026*  
*ATABONG EFON STEPHANE FRITZ*  
*Couvre : 13 fichiers à corriger · 45 divergences documentées · 8 sections*
