# ML_PIPELINE_FEATURES.md

## MAKORA Framework — Features, SHAP, Bootstrap, État de l'art

> Suite de ML_PIPELINE.md — sections 5 à 10
> Dernière mise à jour : 06 juin 2026

---

## 5. FEATURES PAR MODULE

### 5.1 Santé — 17 features (sante.yaml v0.4.0)

| Feature                       | Type  | Calcul                                        | Importance | Référence     |
| ----------------------------- | ----- | --------------------------------------------- | ---------- | ------------- |
| `ratio_prix_mercuriale`       | float | `Montant_Facture / Prix_Reference_Mercuriale` | CRITIQUE   | [Bauder2017]  |
| `incoherence_sexe_acte`       | bool  | Règle métier : sexe vs code acte ASAC         | CRITIQUE   | [Bauder2017]  |
| `praticien_hors_agrement`     | bool  | `NOT Praticien_Actif`                         | CRITIQUE   | [Bauder2017]  |
| `document_altere` ★           | bool  | `Flag_Document_Altere == True`                | CRITIQUE   | [Bauder2017]  |
| `historique_ratio_praticien`  | float | Moyenne ratio 10 derniers dossiers praticien  | CRITIQUE   | [Bauder2017]  |
| `is_weekend_care`             | bool  | `Date_Soin.dayofweek >= 5`                    | HAUTE      | domaine       |
| `delai_soin_depot_anormal`    | bool  | `Delai_Soin_Depot > 30 jours`                 | HAUTE      | domaine       |
| `ocr_confiance_faible` ★      | bool  | `Score_Confiance_OCR_Glob < 0.5`              | HAUTE      | ADR-007       |
| `nb_sinistres_30j`            | int   | Sinistres assuré sur 30j glissants            | HAUTE      | [Bauder2017]  |
| `anciennete_contrat_courte` ★ | bool  | `Anciennete_Contrat < 90 jours`               | HAUTE      | domaine       |
| `saisie_hors_heures` ★        | bool  | `Heure_Saisie < 7 OR > 20`                    | MOYENNE    | domaine       |
| `montant_normalise_log`       | float | `log(Montant_EUR_Normalise + 1)`              | MOYENNE    | domaine       |
| `post_mortem_flag`            | bool  | `Date_Soin > Date_Deces`                      | CRITIQUE   | [Bauder2017]  |
| `document_age_anormal`        | bool  | Document > 180j avant soumission              | HAUTE      | domaine       |
| `praticien_concentration`     | float | `nb_sinistres_praticien / nb_total_batch`     | CRITIQUE   | [Jiang2014]   |
| `flag_doublon_sante`          | bool  | Hash composite dossier vu > 1 fois            | CRITIQUE   | domaine       |
| `community_score_sante`       | float | Score Louvain — communauté suspecte           | HAUTE      | [Blondel2008] |

_★ = feature commune Santé ∩ Auto — utilisée par M_makora_

### 5.2 Auto — 18 features (auto.yaml v1.1.0)

| Feature                       | Type  | Calcul                                   | Importance | Référence     |
| ----------------------------- | ----- | ---------------------------------------- | ---------- | ------------- |
| `ratio_devis_bareme`          | float | `Montant_Devis / Prix_Reference_Bareme`  | CRITIQUE   | [Viaene2002]  |
| `ratio_mo_bareme`             | float | `Cout_MO / MO_Reference_Bareme`          | CRITIQUE   | [Subudhi2017] |
| `delai_declaration_anormal`   | bool  | `Delai_Declaration > 30j`                | HAUTE      | [Viaene2002]  |
| `anciennete_contrat_courte` ★ | bool  | `Anciennete_Contrat < 90j`               | HAUTE      | domaine       |
| `sinistre_nuit_sans_temoin`   | bool  | `Flag_Sinistre_Nuit AND Nb_Temoins == 0` | HAUTE      | [Viaene2002]  |
| `document_altere` ★           | bool  | `Flag_Document_Altere == True`           | CRITIQUE   | domaine       |
| `garage_non_agree`            | bool  | `NOT Garage_Agree`                       | HAUTE      | domaine       |
| `vehicule_sur_value`          | bool  | Valeur déclarée >> cote Argus            | HAUTE      | [Subudhi2017] |
| `ocr_confiance_faible` ★      | bool  | `Confiance_OCR_Glob < 0.5`               | HAUTE      | ADR-007       |
| `saisie_hors_heures` ★        | bool  | `Heure_Saisie < 7 OR > 20`               | MOYENNE    | domaine       |
| `constat_manquant`            | bool  | `Flag_Constat_Present == False`          | HAUTE      | domaine       |
| `expertise_manquante`         | bool  | `Flag_Expertise_Present == False`        | HAUTE      | domaine       |
| `concentration_garage`        | float | Sinistres même garage / total assurés    | CRITIQUE   | [Jiang2014]   |
| `expert_garage_correlation`   | float | Paires expert↔garage sur sinistres       | CRITIQUE   | [Viaene2002]  |
| `flag_doublon_auto`           | bool  | Hash composite vu > 1 fois               | CRITIQUE   | domaine       |
| `community_score_auto`        | float | Score Louvain — communauté suspecte      | HAUTE      | [Blondel2008] |
| `ratio_devis_valeur_vehicule` | float | `Montant_Devis / Valeur_Vehicule`        | HAUTE      | [Subudhi2017] |
| `nb_sinistres_12m`            | int   | Sinistres assurés 12 mois                | HAUTE      | [Viaene2002]  |

_★ = feature commune Santé ∩ Auto — utilisée par M_makora_

### 5.3 Features communes M_makora (intersection Santé ∩ Auto)

4 features sur 35 totales = **11.4% de recouvrement — espace quasi-orthogonal**
[Caruana1997] prédit l'existence de structures latentes partagées dans les 4 features.

| Feature                     | Signification transverse                                    |
| --------------------------- | ----------------------------------------------------------- |
| `anciennete_contrat_courte` | Fraude à la souscription — signal universel toutes branches |
| `document_altere`           | Fraude documentaire — signal universel                      |
| `ocr_confiance_faible`      | Qualité doc suspecte — contexte camerounais flux papier     |
| `saisie_hors_heures`        | Comportement temporel anormal — signal universel SI         |

---

## 6. SHAP — EXPLICABILITÉ

### 6.1 Configuration actuelle — KernelSHAP [Lundberg2017]

DIF est un réseau neuronal : `shap.TreeExplainer` est inapplicable.
Migration vers `shap.KernelExplainer` documentée dans le code de `core/explainer.py`.

```python
# Chargement du background set (100 dossiers normaux du train — sauvegardés en .npy)
X_background = np.load("data/models/{branch}/shap_background.npy")

# Création de l'explainer (une fois à l'initialisation)
explainer = shap.KernelExplainer(
    model.decision_function,
    X_background,
    link="identity"
)

# Calcul SHAP sur un dossier anomalie
shap_values = explainer.shap_values(X_row, nsamples=100, l1_reg="aic")
# nsamples=100 : compromis vitesse/précision — ~1-3s par dossier
# Calculé UNIQUEMENT sur is_anomaly=True [BNF-06]
```

**Note latence :** KernelSHAP est ~20-50x plus lent que TreeExplainer.
Estimation : 1-3s par dossier anomalie (vs <50ms avec TreeExplainer).
Ce coût est acceptable car SHAP est calculé uniquement sur les anomalies
(~7-8% des dossiers). Documenter comme limite connue dans le mémoire.

### 6.2 Stabilité — τ Kendall [Kendall1938]

SHAP vs LIME convergent sur le ranking des features (τ > 0.7 sur 200 cas).
Rapport : `results/sante/convergence_report.json` + `results/auto/convergence_report.json`

### 6.3 Top features par branche (observations empiriques — IF Phase 2)

**Santé :** `ratio_prix_mercuriale` est la feature SHAP dominante sur ~60% des anomalies.
**Auto :** `ratio_devis_bareme` et `concentration_garage` co-dominent.
_Ces classements seront à re-vérifier avec DIF (architecture neuronale différente)._

---

## 7. APPRENTISSAGE VS INFÉRENCE

### 7.1 Mode entraînement (scripts T10.x)

```
Données train (70%)
    → apply_module() → engineer_features()
    → DIF(hidden_neurons=[64,32], contamination=c).fit(X_train)
    → Sauvegarder model.joblib
    → Générer X_background (100 normaux) → shap_background.npy
    → Calibrer seuil sur val set (phi_optimal / fpr5_constrained)
    → Hardcoder THRESHOLD dans DIFStrategy (pas en YAML)
```

### 7.2 Mode inférence (API Phase 3)

```
Données nouvelles
    → apply_module() → engineer_features()
    → DIF.decision_function(X)
    → score >= THRESHOLD_BRANCHE → is_anomaly
    → KernelSHAP (si anomalie) → top-3 features
    → RCA + LLM → MAKORAOutput
```

---

## 8. BOOTSTRAP IC — PROTOCOLE T-05

IC bootstrap à calculer pour les 10 meilleurs candidats par famille [Efron1979].

```python
# bootstrap_ci.py — à lancer via Docker
# Modèles candidats Santé (10 modèles) :
CANDIDATES_SANTE = [
    "dif_phi_optimal",       # ★ PROD
    "dif_fpr5",              # candidat
    "pu_rf",                 # semi-sup
    "hbos_n5",               # candidat
    "if_maxfeat07",          # candidat
    "if_classic",            # baseline réf
    "copod",                 # candidat
    "ecod",                  # candidat
    "lof_k20",               # non-scalable
    "ocsvm",                 # écarté
]
# Même liste pour Auto (DIF fpr5 ★ PROD à la place de phi_optimal)

# Temps estimé : ~30s/modèle × 10 modèles × 2 branches = ~10 min total
# n=1000 répétitions, seed=42, alpha=0.05 [Efron1979]
# Métriques : MCC (principale), F1, AUC, AP, FPR
```

---

## 9. COMPARAISON AVEC L'ÉTAT DE L'ART

| Référence       | Dataset            | Méthode      | F1 / AUC            | Notre résultat DIF           | Écart justifié                           |
| --------------- | ------------------ | ------------ | ------------------- | ---------------------------- | ---------------------------------------- |
| [Liu2008]       | KDD Cup 1999       | IF           | AUC=0.87            | AUC=0.642/0.677              | Fraudes assurance ≠ intrusions réseau    |
| [Bauder2017]    | Medicare fraud     | RF supervisé | F1=0.78–0.84        | F1=0.264/0.277               | Supervisé vs non-supervisé               |
| [Goldstein2016] | 10 benchmarks      | IF vs LOF    | IF > LOF haute dim. | Confirmé Santé, inversé Auto | Auto : clusters locaux [Breunig2000]     |
| [Subudhi2017]   | Auto insurance     | SVM+NB       | F1=0.71 (supervisé) | F1=0.277 (non-supervisé)     | Labels absents contexte africain         |
| [Xu2023]        | Anomaly benchmarks | DIF          | AUC=0.85 avg        | AUC=0.642/0.677              | Données fraude assurance plus difficiles |

---

## 10. FICHIERS DE RÉFÉRENCE

| Fichier                                             | Contenu                                      |
| --------------------------------------------------- | -------------------------------------------- |
| `data/models/sante/dif_model.joblib`                | Modèle DIF production Santé                  |
| `data/models/auto/dif_model.joblib`                 | Modèle DIF production Auto                   |
| `data/models/sante/shap_background.npy`             | Background set KernelSHAP Santé              |
| `data/models/auto/shap_background.npy`              | Background set KernelSHAP Auto               |
| `data/models/sante/if_classic_model.joblib`         | IF classique baseline                        |
| `data/models/auto/if_classic_model.joblib`          | IF classique baseline                        |
| `data/models/h0/M_makora.joblib`                    | Modèle générique H0 (IF)                     |
| `results/sante/t10_4e_dif_calibration_results.json` | Résultats 6 calibrations DIF Santé           |
| `results/auto/t10_4e_dif_calibration_results.json`  | Résultats 6 calibrations DIF Auto            |
| `results/h0/t12_2_delta_results.json`               | Δ F1 H0 avec IF                              |
| `results/h0/t12_3_fp_fn_all.json`                   | Analyse qualitative FP/FN                    |
| `results/bootstrap_ci_candidates.json`              | IC bootstrap 10 candidats _(à générer T-05)_ |

---

_Fin du fichier ML_PIPELINE.md_
_Références : [Liu2008] [Xu2023] [Hariri2019] [Breunig2000] [Schölkopf2001]_
_[Caruana1997] [Lundberg2017] [Goldstein2016] [Bauder2017] [Gama2014]_
_[Sculley2015] [Chicco2020] [Efron1979] [Davis2006]_
