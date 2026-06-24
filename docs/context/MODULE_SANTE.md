# MODULE_SANTE.md
## MAKORA Framework — Module Santé (Branche Assurance Maladie)
> Statut : ✅ Implémentation complète — Phase 2 terminée
> Version YAML : 0.4.0 | Version classe : v1.0
> Dernière mise à jour : 22 mai 2026 — Session IV

---

## 1. IDENTITÉ DU MODULE

| Champ | Valeur |
|---|---|
| **branch** | `sante` |
| **version YAML** | `0.4.0` |
| **Marchés couverts** | France (flux NOEMIE) + Cameroun (flux scan ASAC) |
| **Dataset** | 140 225 lignes — 38 663 IDs uniques |
| **Features calculées** | 17 (sante.yaml v0.4.0) |
| **Règles RCA** | 16 (sante.yaml) |
| **Graphe activé** | Oui — Louvain [Blondel2008] |
| **Drift configuré** | Oui — PSI sur `Batch_Date` [Gama2014] |

---

## 2. MÉTRIQUES RÉELLES — PHASE 2

### 2.1 Modèle spécialisé M_sante (IF classique)

| Métrique | Valeur | Seuil cible | Statut |
|---|---|---|---|
| F1-score | **0.2004** | ≥ 0.20 (non-supervisé) | ✅ |
| IC 95% F1 | [0.182–0.219] | — | ✅ |
| Précision (PPV) | 0.221 | — | mesuré |
| Rappel (TPR) | 0.184 | — | mesuré |
| AUC-ROC | 0.622 | > 0.60 | ✅ |
| Average Precision | mesuré | — | `results/sante/metrics_final.json` |
| MCC | 0.134 | > 0.10 | ✅ |
| FPR | 0.079 | < 0.10 | ✅ |
| Temps entraînement | 3.1s | < 30s | ✅ |
| Contamination calibrée | 0.068 | ≈ taux réel 6.83% | ✅ |

### 2.2 Modèle générique M_makora (sur test Santé)

| Métrique | Valeur | Comparaison M_sante |
|---|---|---|
| F1-score | 0.1554 | Δ = -0.0450 (−4.50%) |
| IC 95% F1 | [0.132–0.180] | — |
| AUC-ROC | 0.543 | − |
| **MCC** | **0.281** | **+0.147 — M_makora SUPÉRIEUR** |
| **FPR** | **0.000** | **0 faux positif sur 21 228 dossiers** |

**Verdict H0 Santé :** Δ=+4.50% → ✅ CONTRIBUTION_VALIDÉE [Caruana1997]

### 2.3 Challengers testés (Santé)

| Algorithme | F1 | AUC | Décision |
|---|---|---|---|
| IF classique | 0.2004 | 0.622 | ✅ **PRODUCTION** |
| IF max_features=0.7 | 0.2104 | 0.630 | Challenger |
| EIF [Hariri2019] | 0.2387 | 0.631 | Non persistable joblib |
| LOF k=50 | 0.1513 | 0.600 | Non scalable O(n²·k) |
| OC-SVM SGD | 0.1287 | 0.339 | ❌ AUC < 0.5, FPR=1.0 |

---

## 3. SPÉCIFICITÉS MÉTIER SANTÉ

### 3.1 Contexte camerounais

| Élément | France | Cameroun | Impact sur features |
|---|---|---|---|
| Nomenclature actes | CCAM | **ASAC** | `Code_Acte` mappé via `source_mappings` |
| Référentiel prix | NGAP/CCAM | **Mercuriale CIMA** | `ratio_prix_mercuriale` = Montant / Prix_ASAC |
| Devise | EUR | **XAF** | Conversion BEAC dans normalizer.py |
| Document source | Feuille soins numérique | **Scan papier** | `ocr_confiance_faible` activé |
| Cachet validation | Signature électronique | **Cachet humide** | Impact OCR documenté — taux erreur ~15% |
| Flux données | NOEMIE JSON | Scan + extraction OCR | `source_mappings: noemie_api / scan_cm` |

### 3.2 Patterns de fraude couverts

| Pattern | Description | Feature discriminante principale | Règle RCA | Référence |
|---|---|---|---|---|
| **Upcoding** | Coder un acte plus cher que réalisé | `ratio_prix_mercuriale` > 1.5 | `RCA_SURF_001` | [Bauder2017] |
| **Unbundling** | Décomposer un acte global en actes séparés | Nb actes élevé + montant total > seuil | `RCA_UNBUNDLE_001` | [Bauder2017] |
| **Phantom billing** | Facturer des actes non réalisés | `praticien_hors_agrement` + `post_mortem_flag` | `RCA_GHOST_001` | [Bauder2017] |
| **Prêt de carte** | Utiliser la carte d'un autre assuré | `incoherence_sexe_acte` | `RCA_USURP_001` | domaine |
| **Fraude post-mortem** | Soins sur patient décédé | `post_mortem_flag` | `RCA_DEAD_001` | [Bauder2017] |
| **Doublon facturation** | Facturer deux fois le même acte | `flag_doublon_sante` | `RCA_DUP_001` | domaine |
| **Fraude documentaire** | Document scanné altéré (Photoshop EXIF) | `document_altere` | `RCA_DOC_001` | domaine |
| **Collusion réseau** | Praticien + assuré complices | `community_score_sante` + `praticien_concentration` | `RCA_RESEAU_001` | [Jiang2014] |

---

## 4. FEATURES CALCULÉES PAR ENGINEER_FEATURES()

### 4.1 Features principales (17 features — sante.yaml v0.4.0)

| Feature | Type | Calcul | Importance | Dette |
|---|---|---|---|---|
| `ratio_prix_mercuriale` | float | `Montant_Facture / Prix_Reference_Mercuriale` | CRITIQUE | **DT-001** : colonne pré-calculée |
| `incoherence_sexe_acte` | bool | Sexe assuré vs liste `_ACTES_FEMININS/_MASCULINS` | CRITIQUE | DT-003 : liste incomplète |
| `praticien_hors_agrement` | bool | `NOT Praticien_Actif` | CRITIQUE | — |
| `document_altere` | bool | `Flag_Document_Altere == True` | CRITIQUE | — |
| `historique_ratio_praticien` | float | Moyenne `ratio_prix_mercuriale` des 10 derniers dossiers | CRITIQUE | **DT-002** : stateless |
| `post_mortem_flag` | bool | `Date_Soin > Date_Deces` | CRITIQUE | — |
| `is_weekend_care` | bool | `Date_Soin.dayofweek >= 5` | HAUTE | — |
| `delai_soin_depot_anormal` | bool | `Delai_Soin_Depot > 30 jours` | HAUTE | — |
| `ocr_confiance_faible` | bool | `Score_Confiance_OCR_Glob < 0.5` | HAUTE | — |
| `nb_sinistres_30j` | int | Nb sinistres de l'assuré sur 30j glissants | HAUTE | — |
| `anciennete_contrat_courte` | bool | `Anciennete_Contrat < 90 jours` | HAUTE | — |
| `saisie_hors_heures` | bool | `Heure_Saisie < 7 OR > 20` | MOYENNE | — |
| `montant_normalise_log` | float | `log(Montant_EUR_Normalise + 1)` | MOYENNE | — |
| `document_age_anormal` | bool | Document soumis > 180j après soin | HAUTE | — |
| `praticien_concentration` | float | `nb_sinistres_praticien / nb_total_batch` | CRITIQUE | DT-002 |
| `flag_doublon_sante` | bool | Hash composite vu > 1 fois | CRITIQUE | — |
| `community_score_sante` | float | Score Louvain — densité communauté | HAUTE | — |

### 4.2 Délégation du calcul

Les features sont réparties en 3 fichiers Python pour respecter la règle IMP-007 (< 400 lignes) :
- `modules/sante/features.py` — features principales (ratio, historique, flags)
- `modules/sante/features_ext.py` — features complémentaires (post_mortem, document_age)
- `modules/sante/features_reseau.py` — features graphe (community_score, flag_doublon, praticien_concentration)

---

## 5. RÈGLES RCA (16 règles — sante.yaml)

Pattern Chain of Responsibility [GoF1994] — première règle matchée retournée.

| Rule ID | Priorité | Catégorie | Sous-catégorie | Feature(s) | Confiance |
|---|---|---|---|---|---|
| `RCA_GHOST_001` | 1 | Fraude | Phantom Billing Décès | `post_mortem_flag` | 0.99 |
| `RCA_DEAD_001` | 1 | Fraude | Phantom Billing Praticien | `praticien_hors_agrement` | 0.95 |
| `RCA_DOC_001` | 1 | Fraude | Fraude documentaire | `document_altere` | 0.90 |
| `RCA_DUP_001` | 1 | Fraude | Doublon facturation | `flag_doublon_sante` | 0.92 |
| `RCA_USURP_001` | 2 | Fraude | Usurpation identité | `incoherence_sexe_acte` | 0.85 |
| `RCA_SURF_001` | 2 | Fraude | Surfacturation Mercuriale | `ratio_prix_mercuriale > 1.5` | 0.88 |
| `RCA_RESEAU_001` | 2 | Fraude | Fraude en réseau | `community_score_sante > seuil` | 0.80 |
| `RCA_CONC_001` | 3 | Fraude | Concentration praticien | `praticien_concentration > 0.3` | 0.75 |
| `RCA_UNBUNDLE_001` | 3 | Fraude | Unbundling actes | nb actes élevé | 0.70 |
| `RCA_HIST_001` | 3 | Fraude | Historique ratio anormal | `historique_ratio_praticien > 1.3` | 0.72 |
| `RCA_OCR_001` | 4 | Erreur | Qualité OCR faible | `ocr_confiance_faible` | 0.60 |
| `RCA_DATE_001` | 4 | Erreur | Document périmé | `document_age_anormal` | 0.65 |
| `RCA_WE_001` | 5 | Biais | Soin weekend | `is_weekend_care` | 0.55 |
| `RCA_DELAI_001` | 5 | Biais | Dépôt tardif | `delai_soin_depot_anormal` | 0.55 |
| `RCA_NUIT_001` | 5 | Biais | Saisie hors heures | `saisie_hors_heures` | 0.50 |
| `RCA_ANCT_001` | 6 | Risque | Contrat récent | `anciennete_contrat_courte` | 0.45 |

---

## 6. SOURCES DU DATASET

| Source | Lignes | Rôle | Statut |
|---|---|---|---|
| **Synthea v3.4.0** | ~806 patients | Parcours soins complets HL7 FHIR | ✅ |
| **SNDS/Medicare** | Référentiel | Prix officiels actes FR | ✅ |
| **ASAC/BEAC** | Référentiel | Mercuriale CIMA + taux XAF | ✅ Synthétique |
| **Kaggle Healthcare Fraud** | Labels | Ground truth fraude | ✅ |
| **Moteur injection anomalies** | 23 scénarios | Labels injectés (~6.83% anomalies) | ✅ |

### Split final

| Split | Lignes | IDs uniques | Taux anomalies | Statut |
|---|---|---|---|---|
| Train | 98 012 | ~27 064 | ~6.8% | ✅ |
| Val | 20 985 | ~5 799 | ~6.9% | ✅ |
| **Test** | **21 228** | **~5 800** | **~6.9%** | **✅ IMMUTABLE** |

---

## 7. SOURCE MAPPINGS

### 7.1 `noemie_api` (flux France numérique)
Colonnes NOEMIE → colonnes schéma universel MAKORA.
Défini dans `sante.yaml` section `source_mappings.noemie_api`.

### 7.2 `scan_cm` (flux Cameroun documentaire)
Extraction OCR PaddleOCR → colonnes schéma universel.
Colonnes spécifiques : `Code_Acte` (ASAC), `Devise` (XAF), `ID_Praticien`.

---

## 8. ANALYSE FP/FN (T12.3)

### 8.1 M_sante — 10 FP + 10 FN analysés

**FP dominants :** `SEUIL_MAL_CALITRE` (100%)
Praticiens à volume de facturation élevé mais conforme à la mercuriale CIMA.
L'IF détecte la densité d'actes, pas la fraude elle-même. Lié à DT-002
(historique_ratio_praticien stateless). [Bauder2017]

**FN dominants :** `CAS_LIMITE_METIER` (100%)
Fraudes en réseau (collusion praticien-assuré) non détectables par features
tabulaires individuelles. Phantom billing sur actes formellement corrects.

### 8.2 M_makora sur Santé — 0 FP + 10 FN

M_makora n'a produit **aucun faux positif** sur 21 228 dossiers (FPR=0.000).
Comportement conservateur lié aux 4 features communes uniquement.

---

## 9. DETTE TECHNIQUE

| ID | Description | Impact | Traitement |
|---|---|---|---|
| DT-001 | `ratio_prix_mercuriale` utilise colonne `Prix_Reference_Mercuriale` pré-calculée — non reproductible sans MercurialeLoader | Élevé — feature CRITIQUE | Post-Phase 3 : MercurialeLoader.compute() sur Code_Acte |
| DT-002 | `historique_ratio_praticien` stateless — fenêtre = batch courant seulement | Moyen — FP sur prestataires légitimes haute activité | Post-Phase 3 : Redis/DuckDB fenêtre glissante |
| DT-003 | `_ACTES_FEMININS` / `_ACTES_MASCULINS` incomplets vs nomenclature ASAC complète | Moyen — FP sur actes de médecine générale non listés | Optionnel : enrichir liste ASAC |

---

*Fin du fichier MODULE_SANTE.md*
*Références : [Bauder2017] [Liu2008] [Jiang2014] [Blondel2008] [Caruana1997]*
