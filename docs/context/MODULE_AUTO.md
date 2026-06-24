# MODULE_AUTO.md
## MAKORA Framework — Module Auto (Branche Assurance Automobile)
> Statut : ✅ Implémentation complète — Phase 2 terminée
> Version YAML : 1.1.0 | Version classe : v1.0
> Dernière mise à jour : 22 mai 2026 — Session IV

---

## 1. IDENTITÉ DU MODULE

| Champ | Valeur |
|---|---|
| **branch** | `auto` |
| **version YAML** | `1.1.0` |
| **Marchés couverts** | France (flux numérique JSON/CSV) + Cameroun (flux scan documentaire) |
| **Dataset** | 100 000 lignes — 100 000 IDs uniques |
| **Features calculées** | 18 (auto.yaml v1.1.0) |
| **Règles RCA** | 9 (auto.yaml) |
| **Graphe activé** | Oui — Louvain sur graphe garage↔assuré [Blondel2008] |
| **Drift configuré** | Oui — PSI sur `Batch_Date` [Gama2014] |
| **Mercuriale** | `bareme_asac_auto.yaml` — 28 codes, devise XAF, tolérance ±10% |

---

## 2. MÉTRIQUES RÉELLES — PHASE 2

### 2.1 Modèle spécialisé M_auto (IF classique)

| Métrique | Valeur | Seuil cible | Statut |
|---|---|---|---|
| F1-score | **0.2654** | ≥ 0.20 (non-supervisé) | ✅ |
| IC 95% F1 | [0.241–0.288] | — | ✅ |
| Précision (PPV) | 0.289 | — | mesuré |
| Rappel (TPR) | 0.246 | — | mesuré |
| AUC-ROC | 0.684 | > 0.60 | ✅ |
| MCC | 0.197 | > 0.10 | ✅ |
| FPR | 0.075 | < 0.10 | ✅ |
| Temps entraînement | 2.8s | < 30s | ✅ |
| Contamination calibrée | 0.080 | ≈ taux réel 8.0% | ✅ |

### 2.2 Modèle générique M_makora (sur test Auto)

| Métrique | Valeur | Comparaison M_auto |
|---|---|---|
| F1-score | 0.2482 | Δ = -0.0172 (−1.72%) |
| IC 95% F1 | [0.223–0.273] | — |
| AUC-ROC | 0.609 | − |
| MCC | 0.192 | -0.005 (quasi-identique) |
| FPR | 0.051 | -0.024 (M_makora moins de FP) |

**Verdict H0 Auto :** Δ=+1.72% → 🏆 GÉNÉRICITÉ_SANS_COÛT [Caruana1997]
M_makora rivalise quasi-parfaitement avec le spécialisé sur la branche Auto.

### 2.3 Challengers testés (Auto)

| Algorithme | F1 | AUC | Note |
|---|---|---|---|
| IF classique | 0.2654 | 0.684 | ✅ **PRODUCTION** |
| IF max_features=0.7 | 0.2759 | 0.686 | Challenger |
| EIF [Hariri2019] | 0.2858 | 0.698 | Non persistable joblib |
| LOF k=20 | 0.2916 | 0.654 | Non scalable |
| **LOF k=50** | **0.3316** | **0.685** | ⚠️ Meilleur F1 mais O(n²·k) |
| OC-SVM SGD | 0.1481 | 0.375 | ❌ AUC < 0.5, FPR=1.0 |

**Note LOF k=50 :** surpasse IF sur Auto — fraudes auto forment des clusters denses
locaux (staging, collusion garage-expert). Écarté en production pour raisons de
scalabilité. Documenté dans le mémoire (ch.5) comme résultat remarquable.

---

## 3. SPÉCIFICITÉS MÉTIER AUTO

### 3.1 Ce qui change par rapport au module Santé

| Concept Santé | Équivalent Auto |
|---|---|
| Acte médical | Rapport d'expertise véhicule |
| Praticien | Garagiste / Expert automobile |
| Mercuriale CIMA santé | Barème légal indemnités auto (ASAC Auto) |
| Ordonnance | Constat amiable |
| Cachet humide sur facture | Rapport d'expertise signé + tampon garage |
| Upcoding | Surfacturation réparation (`ratio_devis_bareme`) |
| Phantom billing | Sinistre fictif (accident fabriqué) |

### 3.2 Contexte camerounais — Flux Auto

| Flux | France | Cameroun |
|---|---|---|
| Format entrée | JSON/CSV numérique | Scan devis + rapport expertise papier |
| Référentiel prix | Argus + barème indemnités légales | **Barème ASAC Auto** (28 codes, XAF) |
| Devise | EUR | **XAF** |
| Document clé | Constat amiable numérique + rapport expertise | Constat papier + PV de police |
| Expertise | Obligatoire si > 5 000 EUR | Obligatoire si > 500 000 XAF |

### 3.3 Patterns de fraude couverts

| Pattern | Description | Feature discriminante | Règle RCA | Référence |
|---|---|---|---|---|
| **Staging accident** | Accident provoqué intentionnellement | `delai_declaration_anormal` court + `sinistre_nuit_sans_temoin` | `RCA_STAGING_001` | [Viaene2002] |
| **Inflation dommages** | Gonfler le montant des réparations | `ratio_devis_bareme > 1.3` | `RCA_INFLATE_001` | [Viaene2002] |
| **Surfacturation MO** | Main-d'œuvre facturée > barème | `ratio_mo_bareme > 1.3` | `RCA_MO_001` | [Subudhi2017] |
| **Véhicule sur-valorisé** | Valeur déclarée >> cote Argus | `vehicule_sur_value` | `RCA_VALSUR_001` | [Subudhi2017] |
| **Collusion garage-expert** | Expert valide systématiquement un seul garage | `expert_garage_correlation > 0.7` | `RCA_COLLUSION_001` | [Viaene2002] |
| **Doublon déclaration** | Même sinistre déclaré 2 fois | `flag_doublon_auto` | `RCA_DUP_001` | domaine |
| **Fraude documentaire** | Constat ou expertise falsifié | `document_altere` | `RCA_DOC_001` | domaine |
| **Concentration garage** | Un garage concentre des sinistres suspects | `concentration_garage > seuil` | `RCA_CONC_001` | [Jiang2014] |
| **Contrat récent** | Fraude à la souscription | `anciennete_contrat_courte` | `RCA_ANCT_001` | domaine |

---

## 4. FEATURES CALCULÉES PAR ENGINEER_FEATURES()

### 4.1 18 features (auto.yaml v1.1.0)

| Feature | Type | Calcul | Importance | Référence |
|---|---|---|---|---|
| `ratio_devis_bareme` | float | `Montant_Devis / Prix_Reference_Bareme` | CRITIQUE | [Viaene2002] |
| `ratio_mo_bareme` | float | `Cout_MO / MO_Reference_Bareme` | CRITIQUE | [Subudhi2017] |
| `concentration_garage` | float | Nb sinistres même garage / nb total assurés | CRITIQUE | [Jiang2014] |
| `expert_garage_correlation` | float | `nb_sinistres_paire / nb_sinistres_expert_total` | CRITIQUE | [Viaene2002] |
| `document_altere` | bool | `Flag_Document_Altere == True` | CRITIQUE | domaine |
| `flag_doublon_auto` | bool | Hash composite vu > 1 fois | CRITIQUE | domaine |
| `delai_declaration_anormal` | bool | `Delai_Declaration > 30 jours` | HAUTE | [Viaene2002] |
| `anciennete_contrat_courte` | bool | `Anciennete_Contrat < 90 jours` | HAUTE | domaine |
| `sinistre_nuit_sans_temoin` | bool | `Flag_Sinistre_Nuit AND Nb_Temoins == 0` | HAUTE | [Viaene2002] |
| `garage_non_agree` | bool | `NOT Garage_Agree` | HAUTE | domaine |
| `vehicule_sur_value` | bool | Valeur déclarée >> cote Argus (seuil YAML) | HAUTE | [Subudhi2017] |
| `ocr_confiance_faible` | bool | `Confiance_OCR_Glob < 0.5` | HAUTE | ADR-007 |
| `saisie_hors_heures` | bool | `Heure_Saisie < 7 OR > 20` | MOYENNE | domaine |
| `constat_manquant` | bool | `Flag_Constat_Present == False` | HAUTE | domaine |
| `expertise_manquante` | bool | `Flag_Expertise_Present == False` | HAUTE | domaine |
| `community_score_auto` | float | Score Louvain — communauté garage-assuré | HAUTE | [Blondel2008] |
| `ratio_devis_valeur_vehicule` | float | `Montant_Devis / Valeur_Vehicule` | HAUTE | [Subudhi2017] |
| `nb_sinistres_12m` | int | Sinistres assuré sur 12 mois | HAUTE | [Viaene2002] |

### 4.2 Délégation du calcul

- `modules/auto/features.py` — features principales (ratio_devis, ratio_mo, délai, flags)
- `modules/auto/features_reseau.py` — features graphe (community_score, flag_doublon, expert_garage_correlation)

### 4.3 Barème ASAC Auto

```yaml
# bareme_asac_auto.yaml — 28 codes, devise XAF
# Chargé par MercurialeLoader au démarrage du module
# Tolérance ±10% avant flag
Exemples :
  CARROSSERIE_001 : 150 000 XAF  # Réparation aile
  MOTEUR_001      : 450 000 XAF  # Révision moteur
  PARE_BRISE_001  : 80 000  XAF  # Remplacement pare-brise
  # ... 25 autres codes
```

**Dégradation gracieuse :** si le barème est absent, `ratio_devis_bareme`
utilise `Montant_Reference_Bareme` si disponible, sinon retourne NaN + log warning.
Le pipeline ne crashe jamais sur l'absence du barème [Sculley2015].

---

## 5. RÈGLES RCA (9 règles — auto.yaml)

| Rule ID | Priorité | Catégorie | Sous-catégorie | Feature(s) cibles | Confiance |
|---|---|---|---|---|---|
| `RCA_DOC_001` | 1 | Fraude | Fraude documentaire | `document_altere` | 0.90 |
| `RCA_DUP_001` | 1 | Fraude | Doublon déclaration | `flag_doublon_auto` | 0.92 |
| `RCA_COLLUSION_001` | 2 | Fraude | Collusion garage-expert | `expert_garage_correlation > 0.7` | 0.85 |
| `RCA_CONC_001` | 2 | Fraude | Concentration garage | `concentration_garage > seuil` | 0.80 |
| `RCA_INFLATE_001` | 2 | Fraude | Surfacturation réparation | `ratio_devis_bareme > 1.3` | 0.82 |
| `RCA_MO_001` | 3 | Fraude | Surfacturation main-d'œuvre | `ratio_mo_bareme > 1.3` | 0.78 |
| `RCA_STAGING_001` | 3 | Fraude | Staging accident | `sinistre_nuit_sans_temoin + delai_court` | 0.75 |
| `RCA_VALSUR_001` | 3 | Fraude | Véhicule sur-valorisé | `vehicule_sur_value` | 0.72 |
| `RCA_ANCT_001` | 4 | Risque | Contrat récent | `anciennete_contrat_courte` | 0.50 |

---

## 6. SOURCES DU DATASET

| Source | Lignes | Rôle | Statut |
|---|---|---|---|
| **French Motor Claims (Kaggle)** | base | Sinistres automobile France | ✅ |
| **Synthétique Cameroun** | enrichissement | Patterns fraude XAF + ASAC Auto | ✅ Généré |
| **Moteur injection anomalies** | 23 scénarios | Labels injectés (~8.0% anomalies) | ✅ |

### Split final

| Split | Lignes | IDs uniques | Taux anomalies | Statut |
|---|---|---|---|---|
| Train | 70 000 | 70 000 | ~8.0% | ✅ |
| Val | 15 000 | 15 000 | ~8.0% | ✅ |
| **Test** | **15 000** | **15 000** | **~8.0%** | **✅ IMMUTABLE** |

---

## 7. ANALYSE FP/FN (T12.3)

### 7.1 M_auto — 10 FP + 10 FN analysés

**FP dominants :** `SEUIL_MAL_CALITRE` (100%)
Véhicules haut de gamme avec devis légitimement élevé — ratio_devis_bareme
dépasse le seuil mais reste cohérent avec la cote Argus. Le modèle ne dispose
pas du contexte de gamme véhicule. [Viaene2002]

**FN dominants :** `CAS_LIMITE_METIER` (100%)
Collusion garage-expert avec dossiers formellement corrects — `expert_garage_correlation`
trop faible si collusion récente (fenêtre batch courte). Staging accidents bien préparés
avec témoins et délai de déclaration conforme.

### 7.2 M_makora sur Auto — 10 FP + 10 FN

FPR=0.051 (vs 0.075 pour M_auto) — M_makora génère moins de faux positifs.
Même cause FN : `CAS_LIMITE_METIER`.

---

## 8. CONTRAINTES D'ARCHITECTURE

- `AutoModule` hérite de `BaseModule` et est enregistré via `@PluginRegistry.register("auto")`
- Le Kernel ne fait jamais `from modules.auto import AutoModule` — il passe par `PluginRegistry.get("auto")`
- `validate_input()` vérifie uniquement les colonnes CRITIQUES (celles sans lesquelles aucune feature ne peut être calculée)
- `engineer_features()` applique une dégradation gracieuse sur chaque feature — jamais de crash

---

*Fin du fichier MODULE_AUTO.md*
*Références : [Viaene2002] [Subudhi2017] [Jiang2014] [Blondel2008] [Liu2008] [Caruana1997]*
