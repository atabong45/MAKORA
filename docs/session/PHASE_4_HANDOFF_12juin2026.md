# MAKORA — Handoff Phase 4 (Gestion des sinistres)

**État au :** 12 juin 2026 — 11h30  
**Auteur :** ATABONG EFON STEPHANE FRITZ  
**Sources :** PHASE_4_BUGS_REPORT.md · PHASE_4_PLANNING_v2.md · session 11-12 juin 2026

---

## 1. ÉTAT GÉNÉRAL

La Phase 4 couvre le cycle de vie complet des sinistres : `DRAFT → SUBMITTED → OPEN → CLOSED`.

**Résultat de la session 11-12 juin :**

- Pipeline IA **fonctionnelle** en production : claim `SIN-SANTE-2026-Q4EYHI` passé `OPEN` en DB, `score=0.2172`, `shap=True`, `temps=617ms` ✅
- 8 bugs résolus dans cette session
- 2 dettes techniques nouvelles identifiées
- **Problème frontend restant** : statut DB dit `OPEN` mais badge UI affiche encore "Soumis" — cause : pas de polling dans `useClaim`

---

## 2. BUGS RÉSOLUS — HISTORIQUE COMPLET

| ID                   | Sévérité | Description                              | Correction appliquée                                                                                                          |
| -------------------- | -------- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| **WIZARD-01**        | 🔴       | Transition étape 1→2 bloquée             | `getattr` défensif sur `latest_anomaly_score` + `useEffect(create.isSuccess)`                                                 |
| **WIZARD-02**        | 🟠       | Devise en saisie libre                   | `<select>` [XAF\|EUR]                                                                                                         |
| **WIZARD-03**        | 🟠       | BranchSelector non répercuté dans wizard | `useEffect([initialBranch])` + `form.setValue`                                                                                |
| **B-DOC-01**         | 🔴       | Upload PDF → 500 silencieux              | `AliasChoices("uploaded_at","created_at")` dans `DocumentMeta` Pydantic                                                       |
| **B-DET-01/05**      | 🟠       | Toasts rouges sur fiche détail           | Même cause que B-DOC-01                                                                                                       |
| **B-DASH-DETAIL-01** | 🔴       | Clic dashboard → page 404                | `r.id` (UUID) → `r.claim_id` (string) dans `DashboardClaimsWidget.tsx` et `DashboardLiveFeed.tsx`                             |
| **B-OCR-ROUTER-01**  | 🟠       | GET /claims/{id}/ocr → 500               | `doc_svc.get_ocr_results` → `doc_svc.list_ocr_results` dans router                                                            |
| **B-DOC-ROUTER-01**  | 🟠       | Download document → 500                  | `doc_svc.download_document` → `doc_svc.get_document_bytes` dans router                                                        |
| **B-AI-NEW-01**      | 🔴       | Pipeline IA non câblée au submit         | `run_pipeline_for_claim()` background task + `claim_to_dossier_dict()` + monkey-patch features + `shap_background.npy` généré |

**Corrections secondaires dans B-AI-NEW-01 :**

- `PluginRegistry` vide → import conditionnel dans `_build_pipeline` avant `PluginRegistry.get(branch)`
- `module = PluginRegistry.get(branch)()` → `module = PluginRegistry.get(branch)(config_path=yaml_path)`
- Mismatch 20 vs 17 features → `module.get_feature_names = lambda fn=feature_names: list(fn)` après restriction
- `shap_background.npy` Santé (50×17) et Auto (50×21) régénérés via `scripts/generate_shap_background.py v2`

---

## 3. BUGS ACTIFS — CLASSÉS PAR SPRINT

### 🔴 Sprint 3A — Frontend polling (BLOQUANT UX, ~2h)

#### B-POLL-NEW-01 — Badge "Soumis" figé après soumission

**Symptôme :** DB `claims.statut = 'OPEN'` mais badge UI affiche encore "Soumis" indéfiniment. Le stepper ne se met pas à jour, le spinner "Analyse en cours..." ne disparaît jamais sans refresh manuel.  
**Cause :** `useClaim(id)` n'a pas de `refetchInterval`. Après le submit, le frontend ne repoll pas le backend.  
**Fix :** Dans `src/hooks/claims/claims.hooks.ts`, activer le polling conditionnel :

```typescript
useQuery({
  queryKey: CLAIMS_KEYS.detail(id),
  queryFn: () => claimsApi.getClaim(id),
  refetchInterval: (query) =>
    query.state.data?.statut === "SUBMITTED" ? 3000 : false,
});
```

**Arrêter** le polling dès `statut !== 'SUBMITTED'`. 3000ms = tolérance d'affichage acceptable (pipeline DIF ~600ms).

---

### 🔴 Sprint 3B — Phase 4 Lot 2 : onglets fiche détail (BLOQUANT démo)

#### B-LOT2-01 — Onglet "Analyse IA" vide

**Symptôme :** L'onglet existe mais n'affiche ni score, ni SHAP top-3, ni narration RCA.  
**Cause :** Composant `ClaimAnalysisTab.tsx` non implémenté (Phase 4 Lot 2 pending). Les données existent en DB (`GET /claims/{id}/analyses` retourne 200 avec contenu).  
**À implémenter :**

- Score DIF avec jauge (0–1, seuil 0.349775 Santé / 0.341498 Auto)
- Badge anomalie / normal
- Top-3 features SHAP (barchart horizontal `recharts`)
- RCA catégorie + confidence (quand disponible)
- Narration DeepSeek (quand disponible)
- Lien vers `AnalysisRun` (date, durée, model_version)

#### B-LOT2-02 — Onglet "Documents" — pas de bouton "Ajouter" post-soumission

**Symptôme :** Sur fiche détail d'un claim OPEN, impossible d'ajouter un document supplémentaire.  
**Cause :** Bouton absent du composant. Le backend accepte les uploads sur OPEN.  
**Fix :** Ajouter bouton upload conditionnel (`statut !== 'CLOSED'`).

#### B-LOT2-03 — Formulaire d'édition du sinistre absent

**Symptôme :** Pas de formulaire PATCH sur la fiche détail (modifier montant, date, etc.).  
**Cause :** Phase 4 Lot 2 non implémenté.  
**Backend :** `PATCH /claims/{claim_id}` fonctionne pour `DRAFT` et `OPEN`.

#### B-LOT2-04 — Bouton de décision gestionnaire absent

**Symptôme :** Pas de bouton "Accepter" / "Rejeter" sur la fiche détail OPEN pour passer à CLOSED.  
**Backend :** Endpoint `POST /claims/{id}/close` à vérifier ou créer.

---

### 🟠 Sprint 4 — Jointure mercuriale (IMPACT ML DIRECT)

#### B-LIN-01 / B-LIN-06 — `prix_ref` et `ratio_prix` toujours NULL

**Symptôme :** Colonnes Prix réf. et Ratio CIMA affichent `—` dans l'onglet Lignes.  
**Cause :** `add_line()` n'interroge pas `reference_prices`. `prix_ref = NULL` → `ratio_prix_mercuriale = 0` → RCA rule `RCA_SURF_001` ne se déclenche jamais → `rca=—` → LLM narrator désactivé → narration absente.  
**Chaîne de dépendance :** B-LIN-01 → rca=False → llm=False → onglet Analyse IA incomplet.  
**Fix dans `claim_crud_service.add_line()` :**

```python
from core.db.models.referentiels import ReferencePrice
ref = db.query(ReferencePrice).filter(
    ReferencePrice.code_acte == data.code_acte,
    ReferencePrice.branch_id == claim.branch_id,
).first()
if ref:
    line.prix_ref = ref.prix_unitaire
    if data.montant_ligne and ref.prix_unitaire > 0:
        line.ratio_prix = data.montant_ligne / ref.prix_unitaire
```

**Référence :** [Bauder2017] — `ratio_prix_mercuriale > 1.5` est la règle `RCA_SURF_001`.

#### B-LIN-04 — Placeholder code ASAC trompeur

**Symptôme :** Formulaire affiche `ex: A0101` — aucun code réel ne suit ce format.  
**Fix :** Remplacer par `ex: CONS_GEN` dans `SanteLineFields.tsx`.

#### B-LIN-05 — Champ quantité absent de l'UI

**Symptôme :** Backend accepte `quantite` (défaut 1) mais le champ n'existe pas en frontend.  
**Fix :** Ajouter `<Input type="number" name="quantite" defaultValue={1} min={1} />` dans `SanteLineFields.tsx` et `AutoLineFields.tsx`.

---

### 🟠 Sprint 5 — OCR

#### B-OCR-NEW-01 — `run_ocr()` non implémenté

**Symptôme :** POST `/claims/{id}/ocr/run` ne fait rien (docstring vide).  
**Architecture décidée :** PaddleOCR + Tesseract → DeepSeek arbitrage/structuration JSON.  
**Sortie attendue :** `{montant, devise, date_soin, code_acte, nom_praticien, etablissement, presence_cachet, flag_altere, score_confiance}`.  
**Côté frontend :** Bouton "Lancer OCR" dans `ClaimDocumentsPanel.tsx` + affichage résultat.  
**ADR-018 à rédiger** : expliquer abandon Ollama, justifier DeepSeek en arbitre, documenter compromis vitesse/précision sur documents camerounais dégradés.

---

### 🟠 Sprint 6 — UX lignes (autocomplete & sélecteurs)

#### B-LIN-NEW-01 — Code ASAC en saisie libre

**Symptôme :** `<input type="text">` libre pour le code ASAC. Un gestionnaire ne connaît pas les codes par cœur.  
**Fix :** Combobox shadcn/ui interrogeant `GET /referentiels/prices/sante?q=...`. Afficher `CONS_GEN — Consultation générale — 15 000 XAF`. Pré-remplir `prix_ref` à la sélection.  
**Résout aussi :** B-LIN-04 (placeholder) et facilite B-LIN-01 (prix_ref pré-rempli).

#### B-LIN-NEW-02 — Hash praticien/garage en saisie libre

**Symptôme :** Champ "ID praticien (hash)" demande 64 caractères SHA-256. Inutilisable par un opérateur.  
**Fix :** Remplacer par sélecteur via `GET /referentiels/practitioners` (Santé) ou `GET /referentiels/garages` (Auto). Hash rempli automatiquement à la sélection.

---

### 🟡 Sprint 7 — i18n + Thème sombre

#### B-I18N-NEW-01 — Strings français hardcodées dans tous les composants Phase 4

**Fix :** Compléter `messages/fr.json` namespace `claims:`, remplacer strings par `useTranslations('claims')`.

#### B-THEME-NEW-01 — Couleurs hardcodées cassent le mode sombre

**Diagnostic :**

```bash
grep -rn '#[A-Fa-f0-9]\{6\}' src/app/\(app\)/claims/ --include="*.tsx"
```

**Fix :** Remplacer `#E9ECEF`, `#1B3C6E`, `#B91C1C`, etc. par variables CSS Tailwind/shadcn.

---

### 🟠 Sprint 8 — Imports batch + politique documentaire

#### B-IMP-NEW-01 — Pas d'import batch

**Symptôme :** Création uniquement ligne-par-ligne. Inadapté pour flux NOEMIE/CIMA réels.  
**À créer :** `POST /claims/import` (CSV/Excel/Parquet) + page `/claims/import` avec preview + rapport (N créés / N rejetés / N doublons).  
**Référence :** [Sculley2015] — pipeline dépendant de saisie manuelle = pipeline jungle.

#### B-DOC-03 — Soumission sans document selon source_flux

**Décision Option A validée :** `source_flux=documentary` → 1 facture obligatoire; `structured` → libre.  
**Fix :** Désactiver bouton "Soumettre" si `source_flux === 'documentary'` et `documents.length === 0`. + Règle de validation dans `submit_claim()` backend.

#### B-DOC-02 — Zone drop sans bouton fallback visible

**Fix :** Confirmer que le clic sur la zone déclenche un `<input type="file">` caché. Si non, ajouter bouton "Parcourir…" explicite.

---

### 🟡 Sprint 9 — Vérifications résiduelles

| ID              | Description                                                            | Action                                       |
| --------------- | ---------------------------------------------------------------------- | -------------------------------------------- |
| NAV-01          | EmptyState générique pour 404/403/réseau                               | Tester `/claims/inexistant`                  |
| RUNS-01         | Colonne branche vide sur `/claims/analyses`                            | Retester maintenant que pipeline tourne      |
| RUNS-02         | Durée "60m 0s" fixe sur tous les runs                                  | Corriger seed fixtures `seed_05` / `seed_06` |
| WIZARD-04       | Validation Zod étape 1 non testée                                      | Soumettre avec champs manquants/invalides    |
| B-NODE-GRAPH-01 | `NodeDetailPanel.tsx` — `node.id` au lieu de `node.claim_id` dans href | Fix lors du sprint graphe (Phase 6)          |

---

## 4. DETTE TECHNIQUE

| ID                           | Sévérité | Description                                                                                                                                                                                                                                              | Fix recommandé                                                                                                                                                                |
| ---------------------------- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **DT-FEATURES-01**           | 🟠       | Monkey-patch `module.get_feature_names` pour 20→17 features. Solution fragile : un redémarrage vide le cache, le patch se réapplique, mais tout changement dans `sante_module.py` peut casser silencieusement.                                           | Soit mettre à jour `sante.yaml` pour ne lister que les 17 features du modèle, soit réentraîner le DIF avec les 20 features actuelles (± 5 min, nouveau threshold à calibrer). |
| **DT-MODEL-TRACEABILITY-01** | 🟡       | `AnalysisRun.model_version_id` pointe sur ModelVersion avec `algorithm='isolation_forest'` (créé par seed_05) alors que le modèle exécuté est DIF.                                                                                                       | Créer une ModelVersion DIF correcte avec `file_path='data/models/sante/dif_model.joblib'` et les vraies métriques (Φ=0.4660, threshold=0.349775).                             |
| **DT-RCA-MISSING-01**        | 🟠       | `rca=False` sur tous les claims créés manuellement car `prix_ref=NULL`. La chaîne RCA → LLM → narration est entièrement dépendante du fix B-LIN-01.                                                                                                      | Résoudre B-LIN-01 en priorité (Sprint 4).                                                                                                                                     |
| **DT-SHAP-BACKGROUND-01**    | 🟡       | `shap_background.npy` Santé shape (50,17) générés depuis le training set. Si le module est mis à jour et que le DIF est ré-entraîné, le background doit être régénéré manuellement.                                                                      | Documenter la procédure dans un `README.md` dans `data/models/`.                                                                                                              |
| **DT-CLAIM-LATEST-01**       | 🟡       | `Claim` n'a pas de colonnes `latest_anomaly_score` / `latest_is_anomaly` en base — ces champs sont injectés dynamiquement via `_enrich_with_latest_analysis()`. Si un endpoint accède au Claim sans passer par `get_claim()`, ces champs seront absents. | Documenter l'invariant : tout accès à `ClaimResponse` DOIT passer par `claim_crud_service.get_claim()`.                                                                       |
| **DT-OCR-STUB-01**           | 🟠       | `run_ocr()` dans `claim_document_service.py` est un stub vide. Tout appel à `POST /claims/{id}/ocr/run` ne fait rien sans erreur visible.                                                                                                                | Implémenter Sprint 5 ou retourner explicitement HTTP 501 Not Implemented en attendant.                                                                                        |
| **DT-MODEL-CACHE-01**        | 🟡       | `_PIPELINE_CACHE` est vide au démarrage. Le premier appel à `_get_pipeline()` charge les modèles DIF (~300 Mo) à la demande, introduisant une latence ~5-8s sur la première soumission après redémarrage.                                                | Préchauffer le cache au startup via un `@app.on_event("startup")` qui appelle `_get_pipeline("sante")` et `_get_pipeline("auto")` en tâche de fond.                           |

---

## 5. PLAN DÉTAILLÉ — SPRINTS ORDONNÉS

### Sprint 3 — Finir Phase 4 Lot 1 restant + Lot 2 essentiel (PRIORITÉ 1)

**Objectif :** L'utilisateur peut soumettre, voir le résultat de l'analyse, et prendre une décision. C'est le cœur du mémoire.

| Tâche                                                    | Fichier(s)                       | Effort |
| -------------------------------------------------------- | -------------------------------- | ------ |
| B-POLL-NEW-01 — Polling `useClaim` conditionnel          | `claims.hooks.ts`                | 30 min |
| B-LOT2-01 — Onglet "Analyse IA" (score + SHAP + RCA)     | `ClaimAnalysisTab.tsx` (à créer) | 1.5 j  |
| B-LOT2-02 — Bouton upload document sur fiche OPEN        | `ClaimDocumentsPanel.tsx`        | 1h     |
| B-LOT2-04 — Boutons décision (Accepter/Rejeter → CLOSED) | `ClaimLifecycleActions.tsx`      | 3h     |
| B-LOT2-03 — Formulaire édition (optionnel pour démo)     | `ClaimEditForm.tsx`              | 1j     |

**Critère de succès :** soumettre → stepper passe OPEN automatiquement → onglet Analyse IA affiche score + SHAP → bouton Accepter/Rejeter visible.

---

### Sprint 4 — Jointure mercuriale (PRIORITÉ 2 — impact ML)

**Objectif :** `prix_ref` et `ratio_prix` calculés à l'ingestion → RCA se déclenche → LLM narre → onglet Analyse IA complet.

| Tâche                                                     | Fichier                                     | Effort |
| --------------------------------------------------------- | ------------------------------------------- | ------ |
| B-LIN-01/06 — Jointure `ReferencePrice` dans `add_line()` | `claim_crud_service.py`                     | 2h     |
| B-LIN-04 — Placeholder `ex: A0101` → `ex: CONS_GEN`       | `SanteLineFields.tsx`                       | 15 min |
| B-LIN-05 — Champ quantité                                 | `SanteLineFields.tsx`, `AutoLineFields.tsx` | 30 min |
| Vérifier que RCA + LLM s'activent après le fix            | Test UI                                     | 30 min |

**Critère de succès :** créer sinistre avec code `CONS_GEN`, montant `25 000 XAF` → `prix_ref = 15 000` → `ratio_prix = 1.67` → après soumission, onglet Analyse IA affiche RCA catégorie "SURFACTURATION" + narration DeepSeek.

---

### Sprint 5 — OCR

**Objectif :** Upload d'une facture → OCR → champs pré-remplis.

| Tâche                                                              | Fichier                     | Effort |
| ------------------------------------------------------------------ | --------------------------- | ------ |
| Rédiger ADR-018 (PaddleOCR + Tesseract + DeepSeek, abandon Ollama) | `context/ARCHITECTURE.md`   | 1h     |
| Implémenter `run_ocr()` PaddleOCR → Tesseract → DeepSeek arbitrage | `claim_document_service.py` | 2j     |
| Persister `OcrExtraction` avec hash image SHA-256                  | `claim_document_service.py` | 1h     |
| Frontend : bouton "Lancer OCR" + polling + affichage résultat JSON | `ClaimDocumentsPanel.tsx`   | 1j     |

**Critère de succès :** upload facture Santé scannée → clic "Lancer OCR" → résultat `{montant, date_soin, code_acte, presence_cachet}` affiché en < 20s.

---

### Sprint 6 — UX lignes

| Tâche                                          | Fichier                                     | Effort |
| ---------------------------------------------- | ------------------------------------------- | ------ |
| B-LIN-NEW-01 — Combobox autocomplete code ASAC | `SanteLineFields.tsx`, `AutoLineFields.tsx` | 1j     |
| B-LIN-NEW-02 — Sélecteur praticien/garage      | `SanteLineFields.tsx`, `AutoLineFields.tsx` | 1.5j   |

---

### Sprint 7 — i18n + Thème sombre

| Tâche                                                          | Fichier                                | Effort |
| -------------------------------------------------------------- | -------------------------------------- | ------ |
| B-I18N-NEW-01 — Compléter messages/fr.json namespace `claims:` | `messages/fr.json`, `messages/en.json` | 2h     |
| B-I18N-NEW-01 — Remplacer strings durs dans composants Phase 4 | Tous les `.tsx` Phase 4                | 4h     |
| B-THEME-NEW-01 — Audit et remplacement couleurs hardcodées     | Tous les `.tsx` Phase 4                | 2h     |

---

### Sprint 8 — Import batch + finitions

| Tâche                                                            | Fichier                                  | Effort |
| ---------------------------------------------------------------- | ---------------------------------------- | ------ |
| B-IMP-NEW-01 — Endpoint `POST /claims/import`                    | `api/routers/claims.py`, nouveau service | 2j     |
| B-IMP-NEW-01 — Page `/claims/import` frontend                    | `app/(app)/claims/import/page.tsx`       | 1j     |
| B-DOC-03 — Validation soumission sans document selon source_flux | `claim_crud_service.py`, wizard étape 3  | 1h     |
| B-DOC-02 — Bouton "Parcourir" fallback visible                   | Composant upload                         | 30 min |

---

### Sprint 9 — Vérifications + dettes techniques

| Tâche                                                                                     | Effort       |
| ----------------------------------------------------------------------------------------- | ------------ |
| DT-FEATURES-01 — Mise à jour `sante.yaml` pour aligner 17 features OU ré-entraînement DIF | 1h ou 30 min |
| DT-MODEL-TRACEABILITY-01 — Créer ModelVersion DIF correcte en DB                          | 30 min       |
| DT-MODEL-CACHE-01 — Préchauffage cache pipeline au startup                                | 30 min       |
| NAV-01 — EmptyState 404/403                                                               | 30 min       |
| RUNS-01/02 — Fix seed fixtures durée/branche                                              | 1h           |
| WIZARD-04 — Validation Zod étape 1                                                        | 30 min       |

---

## 6. ÉTAT DES FICHIERS PRODUITS — SESSION 11-12 JUIN

| Fichier                                                       | Destination | Statut actuel                                                                                          |
| ------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------ |
| `api/services/analyze_service.py`                             | En place    | ✅ Avec `run_pipeline_for_claim`, fix `config_path`, fix `PluginRegistry`, fix monkey-patch features   |
| `api/services/claim_crud_service.py`                          | En place    | ✅ Avec `claim_to_dossier_dict`, `submit_claim` modifié, `get_claim` enrichi                           |
| `api/routers/claims.py`                                       | En place    | ✅ Avec `BackgroundTasks`, fix `list_ocr_results`, fix `get_document_bytes`, fix `run_ocr` Query param |
| `scripts/generate_shap_background.py`                         | En place    | ✅ v2 avec restriction DIF features                                                                    |
| `data/models/sante/shap_background.npy`                       | Généré      | ✅ shape=(50,17)                                                                                       |
| `data/models/auto/shap_background.npy`                        | Généré      | ✅ shape=(50,21)                                                                                       |
| `src/components/features/dashboard/DashboardClaimsWidget.tsx` | En place    | ✅                                                                                                     |
| `src/components/features/dashboard/DashboardLiveFeed.tsx`     | En place    | ✅                                                                                                     |

---

## 7. CHECKLIST ÉTAT PIPELINE IA

```bash
# Confirmer pipeline OK
docker compose exec api python -c "
from api.services.analyze_service import _get_pipeline
p = _get_pipeline('sante')
print('sante:', p)
p = _get_pipeline('auto')
print('auto:', p)
"
# Attendu : shap=True pour les deux

# Confirmer analyse en DB pour un claim soumis
docker compose exec postgres psql -U makora -d makora -c "
SELECT c.claim_id, c.statut, a.anomaly_score, a.is_anomaly, a.processing_time_ms
FROM claims c
JOIN analyses a ON a.claim_id = c.id
ORDER BY c.created_at DESC LIMIT 5;
"
```

---

## 8. DIAGNOSTIC SQL DE RÉFÉRENCE

```sql
-- Vue d'ensemble Phase 4
SELECT c.statut, COUNT(*) AS n, COUNT(a.id) AS n_analyses
FROM claims c
LEFT JOIN analyses a ON a.claim_id = c.id
GROUP BY c.statut ORDER BY c.statut;

-- Détail analyses récentes
SELECT c.claim_id, c.statut, a.anomaly_score, a.is_anomaly,
       a.rca_category, a.processing_time_ms, ar.completed_at
FROM claims c
LEFT JOIN analyses a ON a.claim_id = c.id
LEFT JOIN analysis_runs ar ON ar.id = a.run_id
ORDER BY c.created_at DESC LIMIT 10;

-- Vérifier features mismatch résolu
SELECT mv.version_tag, mv.algorithm, mv.feature_names
FROM model_versions mv
JOIN branches b ON b.id = mv.branch_id
WHERE b.code = 'sante';
```

---

## 9. CONVENTION DE CONTINUATION

**Pour reprendre dans une nouvelle conversation :**

1. Fournir ce document (`PHASE_4_HANDOFF_12juin2026.md`)
2. Fournir `RESEARCH_PROTOCOL.md` (instructions système MAKORA)
3. Signaler que `project_context.txt`, `project_frontend.txt`, `project_frontend_mock.txt` sont dans la PK du projet
4. Priorité d'attaque : **Sprint 3 en premier** (polling + Lot 2 Analyse IA tab) car c'est ce que le jury verra à la soutenance

**Règles absolues :**

- Deux phases : conception → validation → implémentation. Jamais de code sans plan validé.
- Pas de tests automatisés (décision du 11 juin). Tests UI manuels avec checklist uniquement.
- Toute modification de `analyze_service.py` doit préserver le monkey-patch DT-FEATURES-01 jusqu'à résolution propre.
- `claims.py` router livré en remplacement complet, pas en patch.

---

_MAKORA — ATABONG EFON STEPHANE FRITZ — Mémoire fin d'études ENSPY/UY1, soutenance juillet 2026_

---

## 🔄 SESSION 12 JUIN 2026 — APRÈS-MIDI : SPRINTS 3A + 4 LIVRÉS

**Tokens restants en fin de session :** faible — Sprint 3B reporté à la session suivante.

### Sprint 3A — Polling fiche détail ✅

| Item              | Fichier                            | Patch                                                                                                                             |
| ----------------- | ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| **B-POLL-NEW-01** | `src/hooks/claims/claims.hooks.ts` | Ajout `refetchInterval` conditionnel sur `useClaim` : 3 000 ms tant que `query.state.data?.statut === "SUBMITTED"`, `false` sinon |

### Sprint 4 — Jointure mercuriale + UX lignes ✅

| Item                  | Fichier                                 | Patch                                                                   |
| --------------------- | --------------------------------------- | ----------------------------------------------------------------------- |
| **B-LIN-01/06**       | `api/services/claim_crud_service.py`    | Helper `_enrich_line_with_reference()` ajouté + appel dans `add_line()` |
| **DT-LINE-ENRICH-01** | `api/services/claim_crud_service.py`    | Même appel dans `update_line()` pour cohérence après modification       |
| **B-LIN-04**          | `src/modules/sante/SanteLineFields.tsx` | Placeholder `ex: A0101` → `ex: ASAC_C_001` (format réel en DB)          |
| **B-LIN-05**          | `src/modules/sante/SanteLineFields.tsx` | Champ Quantité ajouté avant le hash praticien                           |
| **B-LIN-05**          | `src/modules/auto/AutoLineFields.tsx`   | Champ Quantité ajouté avant le hash garage                              |

### Découvertes importantes vs handoff initial

1. **Le champ du modèle `ReferencePrice` est `prix_ref_xaf`**, pas `prix_unitaire` (le handoff matin était erroné — confirmé via `core/db/models/referentiels.py`)
2. **Les codes ASAC réels en DB sont au format `ASAC_C_001`**, pas `CONS_GEN` (confirmé via `seed_03_reference_prices.py`)
3. Conséquence : tout exemple de test/démo doit utiliser ces codes réels :
   - Santé : `ASAC_C_001` (Consultation généraliste, 5 000 XAF), `ASAC_C_002` (10 000), `ASAC_B_001` (Bilan biologique, 20 000), `ASAC_I_003` (Scanner cérébral, 150 000)
   - Auto : `CIMA_MO_001` (Main d'œuvre carrosserie, 15 000 XAF/h), `CIMA_PI_001` (Pare-brise, 120 000)

### Détail technique du fix B-LIN-01/06

Helper `_enrich_line_with_reference(db, branch_id, line)` :

- No-op silencieux si `code_acte` vide, si pas de `ReferencePrice` correspondant, ou si `prix_ref_xaf <= 0`
- Filtre de validité temporelle : `valid_from <= today` ET (`valid_to IS NULL` OU `valid_to >= today`)
- Tri par `valid_from DESC` pour prendre la version la plus récente en cas de versions multiples
- Si `montant_ligne > 0` → calcule `ratio_prix = round(montant_ligne / prix_ref_xaf, 3)`
- Si `montant_ligne` absent → remplit uniquement `prix_ref` (le calcul du ratio se fera au prochain update si le montant est saisi)

### Checklist de validation manuelle à exécuter à la reprise

1. **Polling** : soumettre un sinistre DRAFT → ouvrir DevTools Network → requêtes `GET /claims/{id}` toutes les ~3s → arrêt automatique dès statut `OPEN`
2. **Jointure mercuriale Santé** : créer ligne `code_acte=ASAC_C_001` montant `12 000` → vérifier `prix_ref=5000`, `ratio_prix=2.400` en DB
3. **Jointure mercuriale Auto** : créer ligne `code_acte=CIMA_MO_001` montant `30 000` → vérifier `prix_ref=15000`, `ratio_prix=2.000`
4. **Update cohérent** : modifier le montant via PATCH → `ratio_prix` recalculé
5. **Chaîne RCA → LLM** : soumettre un sinistre Santé avec ratio > 1.5 → vérifier en DB que `analyses.rca_category` est renseigné et `processing_time_ms` < 1000 ms

### Reste à faire — Sprint 3B (prochaine session, priorité haute)

| Tâche                                                                                           | Fichier                               | Effort                                                                 |
| ----------------------------------------------------------------------------------------------- | ------------------------------------- | ---------------------------------------------------------------------- |
| **B-LOT2-01** — Onglet "Analyse IA" complet (score, jauge, SHAP top-3, RCA, narration DeepSeek) | `ClaimAnalysisTab.tsx` (à créer)      | 1.5 j                                                                  |
| **B-LOT2-04** — Boutons Accepter / Rejeter → CLOSED                                             | `ClaimLifecycleActions.tsx` (à créer) | 3h — vérifier d'abord si `POST /claims/{id}/close` existe côté backend |
| **B-LOT2-02** — Bouton upload document sur fiche OPEN                                           | `ClaimDocumentsPanel.tsx`             | 1h                                                                     |
| **B-LOT2-03** — Formulaire d'édition PATCH (optionnel démo)                                     | `ClaimEditForm.tsx` (à créer)         | 1j                                                                     |

**Prérequis vérifié pour Sprint 3B :** la chaîne RCA + LLM est désormais débloquée côté backend grâce au Sprint 4, donc `ClaimAnalysisTab` aura toutes les données nécessaires (score DIF, SHAP, RCA catégorie, narration) une fois implémenté.

---

---

## 🔄 SESSION 12 JUIN 2026 — FIN DE JOURNÉE : BUGS DIAGNOSTIQUÉS

### Bugs identifiés — à traiter dans les prochains sprints

| ID                     | Sévérité | Symptôme                                                                        | Cause identifiée                                                                                                                                                                                                                                                                                              |
| ---------------------- | -------- | ------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **B-REDIRECT-NEW-01**  | 🔴       | Bouton "Prendre une décision" ne redirige pas vers `/audit/[id]`                | `latest_analysis_id` absent du `ClaimResponse` Pydantic. `_enrich_with_latest_analysis()` n'injecte pas ce champ → `latestAnalysisId` est toujours `null` → bouton `disabled`. Fix : ajouter `claim.latest_analysis_id = str(latest.id)` dans `claim_crud_service.py` + champ dans `ClaimResponse` + type TS. |
| **B-SHAP-NEW-01**      | 🟠       | Onglet "Analyse IA" — section SHAP affiche "Contributions SHAP non disponibles" | Les analyses existantes en DB ont `ShapContribution` vide. Les nouvelles analyses post-fix `shap_background.npy` devraient l'avoir. À confirmer sur un claim soumis APRÈS la session du 11 juin.                                                                                                              |
| **B-RCA-NEW-01**       | 🟠       | Onglet "Analyse IA" — section RCA affiche "Aucune règle RCA n'a matché"         | `ratio_prix_mercuriale` ≤ seuil → `RCA_SURF_001` ne se déclenche pas. À reproduire avec `code_acte=ASAC_C_001` montant `12 000` XAF (ratio 2.4 > seuil 1.5).                                                                                                                                                  |
| **B-NARRATION-NEW-01** | 🟠       | Onglet "Analyse IA" — section narration absente                                 | Dépend directement de B-RCA-NEW-01 : la narration DeepSeek n'est générée que si une règle RCA se déclenche.                                                                                                                                                                                                   |
| **B-OCR-NEW-01**       | 🟠       | Onglet "Documents" — bouton "Lancer OCR" absent sur claim OPEN                  | `DocCard` reçoit `canEdit={editable}` avec `editable = claim.statut === "DRAFT"`. Le bouton OCR est donc masqué sur OPEN. À décider : OCR autorisé sur OPEN ou DRAFT uniquement.                                                                                                                              |

### Décisions actées dans cette session

- `ClaimDecisionInline.tsx` annulé — breaks le workflow `/audit/[id]` prévu par le Principe 5
- B-LOT2-04 : résolu par le bouton "Prendre une décision" existant (une fois B-REDIRECT-NEW-01 fixé)
- B-LOT2-02 : `canUpload` défini dans `ClaimDocumentsPanel` mais UploadZone utilise encore `editable` — patch incomplet, 1 ligne à corriger
- B-LOT2-03 : skippé définitivement

### État Phase 4 — sprints restants

| Sprint   | Contenu                                      | Statut                             |
| -------- | -------------------------------------------- | ---------------------------------- |
| Sprint 6 | Combobox ASAC + sélecteur praticien/garage   | 🟠 À faire                         |
| Sprint 7 | i18n + thème sombre                          | 🔴 Bloquant (condition soutenance) |
| Sprint 8 | Import batch + finitions upload              | 🟠 À faire                         |
| Sprint 9 | Dettes techniques (features, cache, 404/403) | 🟡 À faire                         |

---

_Session 12 juin 2026 — fin journée_
_ATABONG EFON STEPHANE FRITZ_

---

## 🔄 SESSION 13 JUIN 2026 — SPRINT 7 : INTERNATIONALISATION (i18n) LIVRÉ

**Tokens restants en fin de session :** moyen — Sprint 3B reporté à la session suivante.

### Sprint 7 — i18n claims (26 fichiers) ✅

**Périmètre final :** i18n uniquement. Le thème sombre (dark mode) a été tenté puis **abandonné** — les composants devenaient méconnaissables. Décision de session figée : CSS vars et hex originaux intouchables.

**Livrable :** `sprint7_i18n.zip` — arborescence prête à écraser le code existant.

#### Composants modifiés (15)

| Composant               | Fichier                       | Strings traduites                                       |
| ----------------------- | ----------------------------- | ------------------------------------------------------- |
| `ClaimsTable`           | `components/features/claims/` | Headers colonnes, titres boutons actions                |
| `ClaimFilters`          | idem                          | Labels Branche/Statut/Dates, options statut, reset      |
| `ClaimStatusStepper`    | idem                          | Labels DRAFT/SUBMITTED/OPEN/CLOSED + hints              |
| `ClaimLinesTable`       | idem                          | Headers colonnes, deleteLine                            |
| `ClaimDetailHeader`     | idem                          | `form.fields.amount`, `ai.scoreSection`                 |
| `ClaimLifecycleActions` | idem                          | Tous les labels lifecycle                               |
| `ClaimHistoryTimeline`  | idem                          | Titres événements, empty state                          |
| `ClaimFormStep1`        | idem                          | Labels 7 champs, options sourceFlux, bouton submit      |
| `ClaimForm`             | idem                          | stepTitles, boutons nav, FinalActions                   |
| `ClaimSummaryTab`       | idem                          | Empty states, shapEmpty                                 |
| `ClaimAnalysisTab`      | idem                          | Tous les headers sections IA                            |
| `ClaimLineEditor`       | idem                          | Headers tableau, bouton Ajouter                         |
| `ClaimDocumentsPanel`   | idem                          | Zone upload, empty state                                |
| `ClaimDocumentUploader` | idem                          | Titre, description, zone upload, empty                  |
| `ClaimDecisionInline`   | idem                          | Labels légaux conservés en FR (non traduits — décision) |

#### Modules branche (2)

| Fichier                             | Décision                                                                       |
| ----------------------------------- | ------------------------------------------------------------------------------ |
| `modules/sante/SanteLineFields.tsx` | Labels ASAC/CIMA conservés en FR (nomenclature technique, hors périmètre i18n) |
| `modules/auto/AutoLineFields.tsx`   | Idem                                                                           |

#### Pages modifiées (7 → 4 lots)

| Page                             | Strings traduites                                             |
| -------------------------------- | ------------------------------------------------------------- |
| `claims/page.tsx`                | Titre contextuel, bouton Nouveau, breadcrumb                  |
| `claims/new/page.tsx`            | Titre, breadcrumbs                                            |
| `claims/[id]/page.tsx`           | Labels 5 onglets, liens plein écran, `page.notFound`          |
| `claims/[id]/edit/page.tsx`      | Breadcrumbs, `page.notFound`                                  |
| `claims/[id]/documents/page.tsx` | Titre, breadcrumbs, `page.notFound`                           |
| `claims/[id]/lines/page.tsx`     | Titre, breadcrumbs, `page.notFound`                           |
| `claims/analyses/page.tsx`       | Titre contextuel, headers colonnes, empty states, breadcrumbs |

#### Patches i18n (dans `_i18n_patches/` du zip)

| Fichier         | Action requise                                    |
| --------------- | ------------------------------------------------- |
| `patch_fr.json` | Merger le bloc `"claims"` dans `messages/fr.json` |
| `patch_en.json` | Merger le bloc `"claims"` dans `messages/en.json` |

---

### Erreurs TypeScript introduites et corrigées

| Erreur                                       | Cause                            | Fix                                         |
| -------------------------------------------- | -------------------------------- | ------------------------------------------- |
| `divideColor` not in CSSProperties           | Propriété CSS inventée           | Supprimée → `divide-[#E9ECEF]` en className |
| `claim` prop inexistante sur `OcrResultCard` | Prop inventée                    | Supprimée                                   |
| `lineLabels.libelleLabel` inexistant         | Propriété hors type `lineLabels` | Remplacé par `t("lines.columns.label")`     |
| `PermissionGuard` no default export          | Named export utilisé en default  | `import { PermissionGuard } from ...`       |

---

### Décisions de session

| #       | Décision                                               | Justification                                                                                                                                                                             |
| ------- | ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D-S7-01 | **Dark mode abandonné**                                | Après 3 tentatives, les composants devenaient méconnaissables. Le thème sombre nécessite une refonte UI dédiée (hors périmètre mémoire).                                                  |
| D-S7-02 | **Labels légaux non traduits** (`ClaimDecisionInline`) | "Confirmer la fraude", "Rejeter (non-fraude)" sont des termes contractuels MAKORA/CIMA. Pas de clés dans le patch i18n — conservés en français par sécurité sémantique.                   |
| D-S7-03 | **Nomenclatures ASAC/CIMA non traduites**              | "Code ASAC", "Libellé poste", etc. sont des identifiants techniques camerounais. La traduction littérale en anglais ("ASAC Code") serait trompeuse pour un auditeur local.                |
| D-S7-04 | **`tl` au lieu de `t` dans `claims/[id]/page.tsx`**    | Le variable d'itération `t` dans `tabs.map((t) => ...)` existait dans l'original. Renommé la fonction de traduction en `tl` pour éviter le conflit sans toucher à la structure originale. |

---

### État des sprints Phase 4 après cette session

| Sprint       | Contenu                                      | Statut                          |
| ------------ | -------------------------------------------- | ------------------------------- |
| Sprint 3A    | Polling `useClaim`                           | ✅ Livré session 12 juin AM     |
| Sprint 4     | Jointure mercuriale + UX lignes              | ✅ Livré session 12 juin AM     |
| **Sprint 7** | **i18n 26 fichiers claims**                  | **✅ Livré cette session**      |
| Sprint 3B    | ClaimAnalysisTab complet + B-REDIRECT-NEW-01 | 🔴 BLOQUANT démo — **prochain** |
| Sprint 6     | Combobox ASAC autocomplete                   | 🟠                              |
| Sprint 8     | Import batch + politique documentaire        | 🟠                              |
| Sprint 9     | Dettes techniques (features, cache, 404/403) | 🟡                              |

### Priorité session suivante

**Sprint 3B en premier** (🔴 BLOQUANT démo) :

1. `ClaimAnalysisTab` complet — connexion réelle à `GET /claims/{id}/analyses`
2. `B-REDIRECT-NEW-01` — fix redirection après création sinistre (étape 1 → étape 2 ne s'affiche pas)

---

_MAKORA — ATABONG EFON STEPHANE FRITZ — Session 13 juin 2026_

# MAKORA — Handoff Session 13 juin 2026 (v2 — fin de journée)

_ATABONG EFON STEPHANE FRITZ — Phase 4_

---

## ✅ LIVRÉ AUJOURD'HUI

| Fix                        | Fichier(s)                                        | Résultat                                           |
| -------------------------- | ------------------------------------------------- | -------------------------------------------------- |
| B-REDIRECT-NEW-01          | `claim_crud_service.py`, `claims.py` (schema)     | Bouton "Prendre une décision" (header) fonctionne  |
| B-LOT2-02                  | `ClaimDocumentsPanel.tsx`                         | Upload sur claims OPEN activé                      |
| ClaimDecisionInline        | `ClaimLifecycleActions.tsx`                       | Bloc "Décision rapide" supprimé                    |
| RCA + LLM activés          | `analyze_service.py` — `_build_pipeline()`        | `rca=True, llm=True` au démarrage                  |
| Option A : RCA tous claims | `core/pipeline.py` — `_build_outputs()`           | RCA évalué même sans anomalie DIF                  |
| Fix crash `explanation_fr` | `analyze_service.py` — `run_pipeline_for_claim()` | Background task ne crashe plus                     |
| Fix `rca_rule_id`          | idem                                              | Lit `rca.rule_id` au lieu de `rca.rules_triggered` |
| Fix endpoint analyses      | `api/routers/claims.py`                           | Structure `rca` imbriquée + SHAP `joinedload`      |
| Fix SHAP display           | `ClaimAnalysisTab.tsx` — `ShapTop3`               | Feature names + labels + barres depuis 0           |

---

## 🔴 BUG PRIORITAIRE — B-SHAP-LLM-01

### Symptôme

La narration DeepSeek ne contient pas les détails SHAP (quelle variable, quel ratio, quel impact).

### Cause confirmée

Option A a découplé **RCA** du flag `is_anomaly`. Mais le SHAP (étape 7 du pipeline) est **toujours conditionné à `is_anomaly=True`** — cette cohérence n'a pas été faite.

Pour les claims UI (score ~0.217 < seuil 0.349775) :

- `is_anomaly = False`
- → SHAP ne tourne pas → `shap_top_k = []`
- → DeepSeek reçoit `top_features: []`
- → Narration sans mention des variables contributives

### Ce que DeepSeek reçoit actuellement

```
- Score : 0.217
- Features SHAP : (non disponibles)   ← MANQUE
- RCA : Fraude Intentionnelle / Surfacturation / RCA_SURF_001 / 88%
```

### Fix à implémenter

Dans `core/pipeline.py` — `_step_shap_batch()` ou dans `_build_outputs()` :
étendre le calcul SHAP aux claims qui déclenchent une règle RCA, même si `is_anomaly=False`.
Condition suggérée : `is_anomaly[i] OR _rca_has_category`
(symétrique à ce qui a déjà été fait pour RCA + LLM avec Option A).

**Fichier :** `core/pipeline.py`
**Méthode :** `_step_shap_batch()` — paramètre `is_anomaly_mask`
**Note :** Vérifier d'abord si `Explainer.compute_batch_top_k()` accepte le masque modifié.

---

## ⚠️ POINT EN ATTENTE — `_rca_has_category` exclusion

Dans `core/pipeline.py` — `_build_outputs()`, le fix suivant a été planifié mais pas encore appliqué :

```python
# Exclure "Indéterminé" (valeur par défaut de RCAResult.indeterminate())
_INDETERMINATE = {"Indéterminé", "indeterminate", "", None}
_rca_has_category = (
    rca_result is not None
    and getattr(rca_result, "category", None) not in _INDETERMINATE
)
```

Sans ce patch, DeepSeek est appelé même quand aucune règle RCA n'a matché
(catégorie = "Indéterminé"), ce qui génère une narration inutile et coûte ~4s.

---

## 📋 ÉTAT SPRINTS PHASE 4

| Sprint                  | Contenu                                               | Statut      |
| ----------------------- | ----------------------------------------------------- | ----------- |
| 3A                      | Polling `useClaim`                                    | ✅          |
| 3B                      | Onglet Analyse IA                                     | ✅          |
| 4                       | Jointure mercuriale CIMA                              | ✅          |
| 7                       | i18n 26 fichiers                                      | ✅          |
| **B-SHAP-LLM-01**       | SHAP passé à DeepSeek même sur claims non-anomaliques | 🔴 **NEXT** |
| **`_rca_has_category`** | Patch exclusion "Indéterminé"                         | 🔴 **NEXT** |
| 6                       | Combobox ASAC autocomplete                            | 🟠          |
| 8                       | Import batch                                          | 🟠          |
| 9                       | DT-FEATURES-01 monkey-patch 20→17                     | 🟡          |

---

## 🏗️ ARCHITECTURE — CE QUI A CHANGÉ

### `core/pipeline.py` — `_build_outputs()`

```
AVANT : RCA + LLM → uniquement si is_anomaly=True
APRÈS : RCA → tous les claims
        LLM → si is_anomaly OU rca_category non "Indéterminé"
        SHAP → toujours uniquement is_anomaly=True  ← À CORRIGER (B-SHAP-LLM-01)
```

### `api/routers/claims.py` — `GET /claims/{id}/analyses`

```
AVANT : retourne champs plats (rca_category, explanation_fr...)
APRÈS : retourne { "rca": { "category", "subcategory", "top_features", "explanation_fr" } }
        Structure alignée sur AnalysisResult (analysis.types.ts)
```

---

## 🔧 COMMANDES UTILES SESSION SUIVANTE

```bash
# Vérifier compute_batch_top_k signature (pour B-SHAP-LLM-01)
docker compose exec api python -c "
import inspect
from core.explainer import Explainer
print(inspect.signature(Explainer.compute_batch_top_k))
"

# Vérifier RCAResult.indeterminate() catégorie
docker compose exec api python -c "
from core.data_models import RCAResult
r = RCAResult.indeterminate()
print('category:', repr(r.category))
"

# Re-analyser un claim seedé avec le pipeline complet
# (remplacer CLAIM_ID par le claim voulu)
docker compose exec api python -c "
# [script complet dans le handoff précédent]
"

# Vérifier SHAP en DB sur claims récents
docker compose exec postgres psql -U makora -d makora -c \"
SELECT c.claim_id, a.anomaly_score, a.rca_category,
       COUNT(s.id) AS nb_shap, LEFT(a.explanation_fr, 80) AS narration
FROM analyses a
JOIN claims c ON c.id = a.claim_id
LEFT JOIN shap_contributions s ON s.analysis_id = a.id
GROUP BY c.claim_id, a.id
ORDER BY a.created_at DESC LIMIT 5;
\"
```

---

_Session 13 juin 2026 — fin de journée_
_ATABONG EFON STEPHANE FRITZ_

---

## 🔄 SESSION 14 JUIN 2026 — B-SHAP-LLM-01 + B-LIN-NEW-01/02 + RUNS

### ✅ LIVRÉ AUJOURD'HUI

| Fix                     | Fichier(s)                                  | Résultat                                                                                                    |
| ----------------------- | ------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| **B-SHAP-LLM-01**       | `core/pipeline.py` — `_build_outputs()`     | SHAP rétroactif calculé pour claims RCA-triggered non-anomaliques → DeepSeek reçoit `top_features` peuplées |
| **`_rca_has_category`** | `core/pipeline.py` — `_build_outputs()`     | DeepSeek n'est plus appelé quand RCA = "Indéterminé" (~4s économisés)                                       |
| **B-LIN-NEW-01**        | `SanteLineFields.tsx`, `AutoLineFields.tsx` | Code ASAC/CIMA → Combobox référentiel (chargement à l'ouverture, filtre client-side)                        |
| **B-LIN-NEW-02**        | `SanteLineFields.tsx`, `AutoLineFields.tsx` | Praticien/Garage → Combobox référentiel (hash auto-rempli, affichage Spécialité/Ville + ✓ Agréé CIMA)       |

### 📁 NOUVEAUX FICHIERS CRÉÉS

```
src/hooks/referentiels/usePriceOptions.ts
src/hooks/referentiels/usePractitionerOptions.ts
src/hooks/referentiels/useGarageOptions.ts
src/components/common/ReferentielCombobox.tsx
```

### 🔧 PATCHES EN ATTENTE D'APPLICATION (fournis, pas encore déployés)

| ID                | Fichier                                   | Action                                                                                           |
| ----------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------ |
| **RUNS-01**       | `api/schemas/analyze.py`                  | Ajouter `branch_code: str \| None = None` dans `RunStatusResponse`                               |
| **RUNS-01**       | `api/services/analyze_service.py`         | Remplacer `list_runs()` par version avec `outerjoin(Branch)` retournant des dicts enrichis       |
| **RUNS-02**       | `scripts/seeds/seed_05_demo_claims.py`    | `completed_at = started_at + timedelta(minutes=3-7)` au lieu de `+1h`                            |
| **RUNS-02**       | `scripts/seeds/seed_06_demo_claims_v2.py` | Idem                                                                                             |
| **RUNS-02**       | SQL                                       | `UPDATE analysis_runs SET completed_at = started_at + INTERVAL '4 minutes 12 seconds' WHERE ...` |
| **i18n analyses** | —                                         | Clés déjà présentes dans `messages/fr.json` et `messages/en.json`. Redémarrage Next.js suffit.   |

---

## 📋 ÉTAT SPRINTS PHASE 4 — mis à jour

| Sprint              | Contenu                                 | Statut          |
| ------------------- | --------------------------------------- | --------------- |
| 3A                  | Polling `useClaim`                      | ✅              |
| 3B                  | Onglet Analyse IA                       | ✅              |
| 4                   | Jointure mercuriale CIMA                | ✅              |
| 7                   | i18n 26 fichiers                        | ✅              |
| B-SHAP-LLM-01       | SHAP rétroactif RCA                     | ✅              |
| `_rca_has_category` | Garde DeepSeek                          | ✅              |
| B-LIN-NEW-01        | Combobox ASAC/CIMA                      | ✅              |
| B-LIN-NEW-02        | Sélecteur praticien/garage              | ✅              |
| **RUNS-01**         | Colonne branche vide `/claims/analyses` | 🟡 Patch fourni |
| **RUNS-02**         | Durée "60m 0s" seeds                    | 🟡 Patch fourni |
| 6                   | Combobox ASAC (fait via LIN-NEW-01)     | ✅              |
| B-DOC-02            | Bouton "Parcourir" upload               | 🟠              |
| B-DOC-03            | Soumission sans doc (documentary)       | 🟠              |
| WIZARD-04           | Validation Zod étape 1                  | 🟠              |
| NAV-01              | EmptyState 404/403                      | 🟠              |
| 8                   | Import batch                            | 🟠              |

---

_Session 14 juin 2026 — ATABONG EFON STEPHANE FRITZ_

---

## 🔄 SESSION 15 JUIN 2026 — DETTES TECHNIQUES + RESET BD

### ✅ LIVRÉ AUJOURD'HUI

| Fix                       | Fichier(s)                                                     | Résultat                                                                                                                                |
| ------------------------- | -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **DT-MODEL-TRACEABILITY** | `scripts/seeds/seed_05_demo_claims.py`                         | `algorithm="dif"`, `version_tag="dif-v1.0.0-*"`, métriques DIF réelles, `detector_name="dif"`                                           |
| **DT-FEATURES-01**        | `modules/sante/sante.yaml` + `api/services/analyze_service.py` | Section `dif_production.feature_names` (17 features contractuelles) ; `_build_pipeline` lit YAML en priorité, fallback `[:N]` si absent |
| **DT-MODEL-CACHE-01**     | `api/main.py`                                                  | Préchauffage `_get_pipeline("sante"/"auto")` en thread daemon dans `lifespan`                                                           |
| **DT-OCR-STUB-01**        | `api/services/claim_document_service.py`                       | `run_ocr()` lève HTTP 501 explicite au lieu de silence total                                                                            |
| **BD Reset complète**     | Docker + seeds 01→06                                           | `docker compose down -v` + `python -m core.db.init_db` + seeds 02→06 relancés                                                           |

### 🚫 DÉCISIONS — NON IMPLÉMENTÉ

| ID            | Décision               | Justification                                                                                                                                                                                                                                                            |
| ------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **B-DOC-02**  | Abandonné              | La zone upload est un `<label>` HTML wrappant `<input type="file" hidden>` — clic natif fonctionne sans "Parcourir" explicite. Modification `editable → canUpload` dans `ClaimDocumentUploader.tsx` sans effet pratique : composant utilisé dans le wizard (DRAFT only). |
| **B-DOC-03**  | Reporté Phase 5        | OCR non implémenté → le pipeline DIF tourne sans les données documentaires. La validation créerait de la friction en démo sans bénéfice réel. Sera pertinente post-Sprint 5.                                                                                             |
| **WIZARD-04** | Déjà implémenté — test | `claimCreateSchema` + `zodResolver` en place. Tâche de vérification visuelle uniquement.                                                                                                                                                                                 |
| **NAV-01**    | Déjà implémenté — test | Pattern `if (error \|\| !claim) → <EmptyState>` présent sur toutes les sous-pages claims. Vérification visuelle uniquement.                                                                                                                                              |

### 📋 ÉTAT SPRINTS PHASE 4 — mis à jour

| Sprint              | Contenu                         | Statut         |
| ------------------- | ------------------------------- | -------------- |
| 3A                  | Polling `useClaim`              | ✅             |
| 3B                  | Onglet Analyse IA               | ✅             |
| 4                   | Jointure mercuriale CIMA        | ✅             |
| 6                   | Combobox ASAC/praticien/garage  | ✅             |
| 7                   | i18n 26 fichiers                | ✅             |
| B-SHAP-LLM-01       | SHAP rétroactif RCA             | ✅             |
| `_rca_has_category` | Garde DeepSeek                  | ✅             |
| B-LIN-NEW-01/02     | Combobox référentiels           | ✅             |
| RUNS-01/02          | Durée seeds + colonne branche   | ✅             |
| DT-\*               | 4 dettes techniques soldées     | ✅             |
| **Sprint 5**        | **OCR (B-OCR-NEW-01)**          | 🔴 **PENDING** |
| **Sprint 8**        | **Import batch (B-IMP-NEW-01)** | 🟠 **PENDING** |

### 🔴 SPRINTS RESTANTS PHASE 4

#### Sprint 5 — OCR (BLOQUANT pour flux documentaire)

Architecture validée : PaddleOCR → Tesseract → DeepSeek arbitrage/structuration.

| Tâche                                                                  | Fichier                     | Effort |
| ---------------------------------------------------------------------- | --------------------------- | ------ |
| ADR-018 — documenter choix PaddleOCR + DeepSeek, abandon Ollama        | `context/ARCHITECTURE.md`   | 1h     |
| `run_ocr()` — PaddleOCR extraction brute + Tesseract fallback          | `claim_document_service.py` | 2j     |
| Structuration JSON via DeepSeek + persistance `OcrExtraction` SHA-256  | `claim_document_service.py` | 1j     |
| Intégration pipeline : champs OCR → enrichissement claim avant DIF     | `analyze_service.py`        | 1j     |
| Frontend : polling résultat OCR + affichage dans `ClaimDocumentsPanel` | `ClaimDocumentsPanel.tsx`   | 1j     |

**Sortie attendue :** `{montant, devise, date_soin, code_acte, nom_praticien, etablissement, presence_cachet, flag_altere, score_confiance}`

**Note intégration pipeline :** les champs OCR (`presence_cachet`, `flag_altere`, `score_confiance`) doivent alimenter les features `document_altere` et `ocr_confiance_faible` du module Santé avant le passage au DIF. Cette intégration est nouvelle — elle n'est pas dans le handoff précédent et doit être planifiée dans `run_pipeline_for_claim()`.

#### Sprint 8 — Import batch

| Tâche                                                                      | Fichier                                   | Effort |
| -------------------------------------------------------------------------- | ----------------------------------------- | ------ |
| `POST /claims/import` — CSV/Excel/Parquet → N claims DRAFT                 | `api/routers/claims.py` + nouveau service | 2j     |
| Page `/claims/import` — preview + rapport N créés / N rejetés / N doublons | `app/(app)/claims/import/page.tsx`        | 1j     |

---

_Session 15 juin 2026 — ATABONG EFON STEPHANE FRITZ_

# MAKORA — Handoff Session Sprint 5 OCR (13 juin 2026)

---

## CONTEXTE GÉNÉRAL

**Projet :** MAKORA — framework générique de détection de fraude en assurance (mémoire de fin d'études ENSPY/UY1, soutenance juillet 2026).
**Responsable :** ATABONG EFON STEPHANE FRITZ
**Session couverte :** Planification, conception et implémentation partielle du Sprint 5 (OCR).

---

## CE QUI A ÉTÉ PLANIFIÉ ET CONÇU

### Architecture OCR décidée

**Flux nominal :**

```
[DRAFT] Upload (1 doc max) → Lancer OCR (manuel) → Submit
    → pipeline DIF lit le dernier OCR en DB → OPEN

[OPEN] Lancer OCR (re-run) → bouton "Re-analyser"
    → pipeline DIF re-lit le nouvel OCR → nouvelles analyses
```

**5 décisions architecturales figées (D-S5-01 à D-S5-05) :**

- OCR autorisé sur DRAFT + OPEN (pas DRAFT seulement)
- OCR synchrone (retour direct, pas de 202 + polling)
- `paddle_text_length` / `tesseract_text_length` laissés NULL (non exposés par `OCRResult`)
- Sémantique "remplace" : avant tout nouvel OCR, l'extraction précédente du document est supprimée
- Seuil `ocr_confiance_faible = 0.60` pour l'injection dans le pipeline DIF
- 1 document maximum par sinistre

---

## CE QUI A ÉTÉ LIVRÉ

### Lot 1 — Backend (3 fichiers)

**1. `api/services/claim_document_service.py` — REMPLACEMENT COMPLET**

- `upload_document()` : validations ajoutées — statuts DRAFT+OPEN, 1 doc max par claim (HTTP 400 si doc déjà présent)
- `delete_document()` : étendu à DRAFT+OPEN (était DRAFT seulement)
- `list_ocr_results()` : `.order_by(OcrExtraction.created_at.desc())` ajouté
- `run_ocr()` : implémentation complète (remplace le stub HTTP 501)
  - Instancie `DocumentaryReader` depuis `core.ingestion.documentary_reader`
  - Supprime l'OcrExtraction précédente pour ce document (sémantique "remplace")
  - Appelle `reader.process(abs_path)` → `OCRResult`
  - Mappe `OCRResult` → `OcrExtraction` (attention : noms de champs différents : `montant_facture` → `montant_extrait`, `devise` → `devise_extraite`, etc.)
  - `reader.backend.name` utilisé pour `llm_backend_used`
  - Persiste et retourne l'`OcrExtraction`

**2. `api/services/analyze_service.py` — 2 PATCHES TEXTUELS (non confirmés appliqués)**

Ces deux patches ont été fournis comme instructions textuelles uniquement, pas comme fichier généré. Statut d'application inconnu.

_Insertion A — helper avant `run_pipeline_for_claim()` :_

```python
def _get_latest_ocr_for_claim(db: Session, claim) -> "OcrExtraction | None":
    # Retourne le dernier OcrExtraction success=True pour le claim
    # Référence [Bauder2017]
    doc_ids = [d.id for d in claim.documents]
    if not doc_ids: return None
    return db.query(OcrExtraction)
        .filter(...document_id.in_(doc_ids), success==True)
        .order_by(created_at.desc()).first()
```

_Insertion B — dans `run_pipeline_for_claim()`, entre création AnalysisRun (step 5) et exécution pipeline (step 6) :_

```python
ocr = _get_latest_ocr_for_claim(db, claim)
if ocr:
    dossier["document_altere"] = ocr.flag_altere
    dossier["ocr_confiance_faible"] = ocr.score_confiance_global < 0.60
```

**3. `api/routers/claims.py` — 1 ENDPOINT AJOUTÉ (version buguée appliquée)**

L'endpoint `POST /{claim_id}/reanalyze` a été ajouté mais contient un bug confirmé (traceback visible) : `claim_to_dossier_dict(claim)` sans `db`. La version corrigée a été fournie en texte mais **n'a pas encore été appliquée**.

### Lot 2 — Frontend (3 fichiers livrés)

**`ClaimDocumentsPanel.tsx` — PATCH CIBLÉ appliqué**

- `canOcr = statut === "DRAFT" || statut === "OPEN"` (nouvelle variable)
- `canUpload = canOcr && !docsLoading && documents.length === 0` (contrainte 1 doc max)
- `UploadZone` : condition `editable` → `canUpload` (fix B-LOT2-02 incomplet)
- `DocCard` : `canEdit={editable}` → `canEdit={canOcr}`
- Bouton "Re-analyser" ajouté (gold `#F0A500`), conditionnel sur `canReanalyze = hasOcr && statut === "OPEN"`
- Map restructuré en bloc pour extraire `hasOcrForDoc` par document

Correction supplémentaire : l'outer `<button>` de `DocCard` doit être changé en `<div role="button" tabIndex={0}>` (bug HTML : `<button>` ne peut pas contenir des `<button>`).

**`useClaimMutations.ts` — PATCH (ajout `useReanalyze`)**

- `mutationFn: () => claimsService.reanalyze(claimId).then(r => r.data)`
- `onSuccess` : invalide `CLAIMS_KEYS.detail(claimUuid)` immédiatement + `CLAIMS_KEYS.all` après 3s

**`claims.service.ts` — PATCH (ajout `reanalyze`)**

- `reanalyze: (claimId) => apiClient.post<{ message: string }>(`/claims/${claimId}/reanalyze`)`

### Autre correction (claim_crud_service.py)

`claim_to_dossier_dict()` a reçu 6 features DIF dérivées par défaut dans les blocs `sante` et `auto`. Ce patch a été fourni comme texte lors du diagnostic du bug pipeline 17 features. Statut d'application : confirmé appliqué (pipeline fonctionne après).

---

## BUGS RENCONTRÉS, DIAGNOSTIQUÉS ET CORRIGÉS

### Bug 1 — Pipeline bloqué en SUBMITTED (critique, résolu)

**Symptôme :** Claims restent en `SUBMITTED` indéfiniment. Frontend poll toutes les 3s sans fin.
**Cause :** `claim_to_dossier_dict()` retourne 10 colonnes brutes. Le feature engineering en dérive 11 des 17 features DIF. Les 6 manquantes (`flag_weekend_care`, `flag_doublon_sante`, `community_score_sante`, `montant_normalise_log`, `delai_soin_depot_anormal`, `praticien_concentration`) sont "ignorées" (droppées). Le `MinMaxScaler` reçoit 11 au lieu de 17 → crash silencieux → background task échoue → statut reste SUBMITTED.
**Fix :** Ajout de 6 valeurs par défaut calculées dans `claim_to_dossier_dict()` pour les branches `sante` et `auto`.
**Statut :** ✅ Résolu et confirmé (score=0.2172 Santé, score=0.2174 Auto visibles dans les logs).

### Bug 2 — OCR 422 Unprocessable Entity (résolu)

**Symptôme :** `POST /claims/{id}/ocr/run` retourne 422 avec `query.doc_id: Field required`.
**Cause :** Double mismatch : frontend envoyait `{ document_id: docId }` en body, backend attend `doc_id` comme query parameter.
**Fix dans `claims.service.ts`:**

```typescript
// AVANT
runOcr: (claimId, docId) =>
  apiClient.post(`/claims/${claimId}/ocr/run`, { document_id: docId });
// APRÈS
runOcr: (claimId, docId) =>
  apiClient.post(`/claims/${claimId}/ocr/run`, null, {
    params: { doc_id: docId },
  });
```

**Statut :** ✅ Résolu, confirmé dans les logs (`ocr/run?doc_id=...`).

### Bug 3 — `<button>` nested (résolu partiellement)

**Symptôme :** Console React : `<button> cannot contain a nested <button>`.
**Cause :** `DocCard` est un `<button>` (sélection) qui contient les boutons OCR/Re-analyser/Supprimer.
**Fix :** Changer l'outer `<button>` de `DocCard` en `<div role="button" tabIndex={0} onKeyDown={...}>`.
**Statut :** ✅ Fix fourni en texte, à appliquer manuellement.

### Bug 4 — PDF_PROTEGE (partiellement résolu)

**Symptôme :** OCR retourne `success=False, score=0.00, error=PDF_PROTEGE`.
**Cause :** `poppler-utils` absent du container Docker. `pdf2image` ne peut pas convertir le PDF en image.
**Fix :**

```bash
# Temporaire (ne persiste pas après rebuild)
docker compose exec api bash -c "apt-get update -q && apt-get install -y poppler-utils -q"
# Permanent : ajouter dans le Dockerfile
RUN apt-get update && apt-get install -y poppler-utils
```

**Statut :** ⚠️ Installé temporairement, non permanent. À ajouter au Dockerfile. Le PDF de test (facture camerounaise réaliste) a été généré et livré (`facture_test_ocr_sante.pdf`).

### Bug 5 — Reanalyze 500 (confirmé, non encore résolu)

**Symptôme :** `POST /claims/{id}/reanalyze` retourne 500.
**Traceback confirmé :** `TypeError: claim_to_dossier_dict() missing 1 required positional argument: 'claim'`
**Cause :** Version lot 1 de l'endpoint appelle `claim_svc.claim_to_dossier_dict(claim)` sans passer `db` en premier argument.
**Fix fourni (à appliquer) :** Remplacer le corps de `reanalyze_claim` dans `api/routers/claims.py` par la version qui :

1. Interroge la branche explicitement via `db.query(BranchModel)` avant le commit
2. Appelle `claim_svc.claim_to_dossier_dict(db, claim)` avec `db`
3. Construit `branch_code` et `dossier` **avant** `db.commit()` (évite claim bloqué si erreur)
   **Statut :** 🔴 Non résolu. Fix précis fourni en texte dans la session.

---

## HYPOTHÈSES EXPLORÉES ET REJETÉES

- **ModelVersion absente** → vérifiée, présente en DB (`dif-v1.0.0-sante` et `dif-v1.0.0-auto`). Rejetée comme cause du blocage SUBMITTED.
- **Import `DocumentaryReader` crashant au démarrage** → vérifié via `python -c "from api.services import claim_document_service; print('Import OK')"`. Rejeté.
- **OCR asynchrone (202 + polling)** → évalué et rejeté en faveur du synchrone (plus simple, acceptable en démo).
- **Dark mode** → tenté lors du Sprint 7 (i18n), abandonné définitivement (composants méconnaissables). Décision figée.
- **Limiter l'OCR au statut DRAFT uniquement** → rejeté, étendu à DRAFT+OPEN pour valeur forensique sur claims ouverts.

---

## ÉTAT ACTUEL — CE QUI FONCTIONNE

| Fonctionnalité                               | Statut                                                        |
| -------------------------------------------- | ------------------------------------------------------------- |
| Pipeline DIF (submit → OPEN)                 | ✅ Fonctionne — score=0.2172 Santé, 0.2174 Auto               |
| Upload document (1 doc max, DRAFT+OPEN)      | ✅                                                            |
| Bouton "Lancer OCR" visible sur DRAFT+OPEN   | ✅                                                            |
| Appel OCR endpoint (200 OK)                  | ✅                                                            |
| OCR réussi sur PDF réel                      | ⚠️ Dépend de poppler dans Dockerfile                          |
| Affichage résultat OCR dans `OcrResultCard`  | ✅ (success=False affiché correctement)                       |
| Bouton "Re-analyser" visible (OPEN + hasOcr) | ✅                                                            |
| Endpoint reanalyze (POST /reanalyze)         | 🔴 500 — fix disponible non appliqué                          |
| Injection features OCR dans pipeline DIF     | ⚠️ Patch analyze_service.py fourni mais non confirmé appliqué |

---

## PLAN IMMÉDIAT — CE QUI RESTE À FAIRE

**Priorité 1 — Fix reanalyze (5 min) :**
Appliquer dans `api/routers/claims.py` la version corrigée de `reanalyze_claim` (fournie textuellement en session). La seule ligne critique : `claim_svc.claim_to_dossier_dict(db, claim)` + construction `branch_code` et `dossier` avant `db.commit()`.

**Priorité 2 — Dockerfile (2 min) :**
Ajouter `RUN apt-get update && apt-get install -y poppler-utils` dans le Dockerfile de l'API pour rendre poppler permanent.

**Priorité 3 — Patches analyze_service.py (vérifier) :**
Confirmer que les deux insertions textuelles ont été appliquées :

- Helper `_get_latest_ocr_for_claim(db, claim)`
- Bloc d'enrichissement OCR dans `run_pipeline_for_claim()` (entre step 5 et step 6)

**Priorité 4 — Retirer l'early-exit dans documentary_reader.py :**
Supprimer le bloc `if score_global < _SCORE_MIN: return OCRResult(...)` pour que DeepSeek soit toujours appelé même sur texte vide.

**Priorité 5 — Renforcer le prompt dans core/llm/prompts.py :**
Ajouter dans `OCR_EXTRACTION_PROMPT` (constante string) : "Si les deux textes OCR sont vides ou illisibles, retourner tous les champs à null. Ne pas inventer de valeurs."

**Priorité 6 — Test end-to-end :**
Uploader `facture_test_ocr_sante.pdf` (livré), lancer OCR, vérifier que DeepSeek extrait : `montant=37500`, `date=2026-06-13`, `code_acte=ASAC_C_001`, `praticien=NKOA Marie-Claire`, `etablissement=Clinique Sainte-Marie`, `presence_cachet=true`.

---

## FICHIERS DE RÉFÉRENCE IMPORTANTS

- `PHASE_4_HANDOFF_12juin2026.md` — historique complet des bugs et décisions des sessions précédentes
- `MAKORA_FRONTEND_MASTERPLAN_v4.md` — plan global des phases
- Import path confirmé : `from core.ingestion.documentary_reader import DocumentaryReader`
- Prompt OCR : `core/llm/prompts.py` → constante `OCR_EXTRACTION_PROMPT`
- Seuils DIF calibrés (immuables) : Santé `0.349775`, Auto `0.341498`
