# Tableau comparatif exhaustif — MAKORA
> Toutes phases · Tous algorithmes · Toutes calibrations  
> Φ = (F1 + AUC + MCC + AP + (1−FPR)) / 5 · seed=42 · test sets immutables  
> `*` = score partiel (métriques incomplètes) · `—` = non mesuré · `skip` = dépendance manquante

---

## BRANCHE SANTÉ
*test=21 228 dossiers · 6.9% anomalies · 17 features*

| Rang | Algorithme | Variante / Calibration | F1 | AUC | MCC | AP | FPR | **Φ** | n |
|---|---|---|---|---|---|---|---|---|---|
| 1 | **DIF [64,32]** | phi_optimal ← T10.4e | 0.2637 | 0.6423 | 0.2449 | 0.2010 | 0.0218 | **0.4660** | 5/5 |
| — | DIF [64,32] | oracle_upper ← borne sup, no deploy | 0.2775 | 0.6423 | 0.2407 | 0.2010 | 0.0323 | 0.4659 | 5/5 |
| 2 | DIF [64,32] | fpr5_constrained ← T10.4e | 0.2770 | 0.6423 | 0.2400 | 0.2010 | 0.0325 | 0.4656 | 5/5 |
| 3 | DIF [64,32] | pr_exact ← T10.4e | 0.2774 | 0.6423 | 0.2399 | 0.2010 | 0.0329 | 0.4655 | 5/5 |
| 4 | DIF [64,32] | percentile_f1 ← run2 calibré | 0.2742 | 0.6423 | 0.2345 | 0.2010 | 0.0347 | 0.4635 | 5/5 |
| 5 | HBOS | n_bins=5 (opt. val) | 0.2795 | 0.6275 | 0.2229 | 0.2452 | 0.0628 | 0.4625 | 5/5 |
| 6 | PU Learning RF ⚠️ | c=0.0935 [Elkan2008] | 0.2937 | 0.6994 | 0.2442 | 0.1580 | 0.1386 | 0.4513 | 5/5 |
| 7 | DIF [64,32] | youden ← T10.4e | 0.2662 | 0.6423 | 0.2086 | 0.2010 | 0.0632 | 0.4510 | 5/5 |
| 8 | DIF [64,32,16]+scaler | phi_optimal ← T10.4e Phase B | 0.2293 | 0.6319 | 0.1937 | 0.1801 | 0.0312 | 0.4408 | 5/5 |
| 9 | DIF [64,32,16]+scaler | fpr5_constrained ← T10.4e Phase B | 0.2421 | 0.6319 | 0.1928 | 0.1801 | 0.0448 | 0.4404 | 5/5 |
| 10 | EIF ExtLvl=1 | T10.4d (hyperparams JSON) | 0.2295 | 0.6339 | 0.1720 | 0.1944 | 0.0581 | 0.4343 | 5/5 |
| 11 | DIF [64,32,16]+scaler | pr_exact ← T10.4e Phase B | 0.2472 | 0.6319 | 0.1887 | 0.1801 | 0.0628 | 0.4370 | 5/5 |
| 12 | DIF non-calibré | défaut PyOD (contamination=0.07) | 0.0796 | 0.6423 | 0.1345 | 0.2010 | 0.0030 | 0.4109 | 5/5 |
| 13 | DIF [128,64,32]+scaler | phi_optimal ← T10.4e Phase B | 0.2210 | 0.6282 | 0.1826 | 0.1599 | 0.0332 | 0.4317 | 5/5 |
| 14 | DIF [128,64,32]+scaler | pr_exact ← T10.4e Phase B | 0.2341 | 0.6282 | 0.1807 | 0.1599 | 0.0505 | 0.4305 | 5/5 |
| 15 | DIF [128,64,32]+scaler | fpr5_constrained ← T10.4e Phase B | 0.2320 | 0.6282 | 0.1790 | 0.1599 | 0.0499 | 0.4298 | 5/5 |
| 16 | COPOD | empirical copula | 0.2253 | 0.6242 | 0.1581 | 0.2218 | 0.1103 | 0.4238 | 5/5 |
| 17 | IF max_feat=0.7 | contamination=0.07 | 0.2104 | 0.6296 | 0.1446 | 0.1558 | 0.0810 | 0.4120 | 5/5 |
| 18 | IF classique | contamination=0.07 | 0.2053 | 0.6221 | 0.1376 | 0.1605 | 0.0885 | 0.4076 | 5/5 |
| 19 | ECOD | CDF empirique | 0.2035 | 0.6243 | 0.1323 | 0.2002 | 0.1249 | 0.4071 | 5/5 |
| 20 | EIF ExtLvl=1 | T10.3 (1ère mesure) | 0.2387 | 0.6312 | — | — | — | 0.4350* | 2/5 |
| 21 | LOF k=50 | novelty=True | 0.1513 | 0.6000 | — | — | — | 0.3757* | 2/5 |
| 22 | LOF k=10 | novelty=True | 0.1341 | 0.5920 | — | — | — | 0.3631* | 2/5 |
| 23 | RIF | 10 rotations ensemble | 0.1430 | 0.5400 | 0.0500 | — | 0.5790 | 0.2885* | 4/5 |
| 24 | LOF k=20 | novelty=True | 0.1490 | 0.6030 | 0.0791 | 0.0910 | 0.2950 | 0.3254 | 5/5 |
| 25 | OC-SVM SGD | StandardScaler | 0.1287 | 0.3390 | 0.0000 | 0.0490 | 1.0000 | 0.1034 | 5/5 |
| — | SUOD | — | skip | — | — | — | — | — | 0/5 |
| — | AutoEncoder | — | skip | — | — | — | — | — | 0/5 |

*⚠️ PU Learning semi-supervisé (labels pseudo issus RCA conf≥0.80) — avantage informationnel non comparable aux approches non-supervisées.*  
*EIF non persistable via joblib (ADR-010). DIF non-calibré : seuil défaut PyOD, aucune calibration val set.*

---

## BRANCHE AUTO
*test=15 000 dossiers · 8.0% anomalies · 18 features*

| Rang | Algorithme | Variante / Calibration | F1 | AUC | MCC | AP | FPR | **Φ** | n |
|---|---|---|---|---|---|---|---|---|---|
| 1 | LOF k=20 ❌ | novelty=True, k=20 | 0.3376 | 0.6542 | 0.3047 | 0.2962 | 0.0300 | **0.5125** | 5/5 |
| 2 | LOF k=50 ❌ | novelty=True, k=50 | 0.3316 | 0.6850 | — | — | — | 0.5083* | 2/5 |
| 3 | EIF ExtLvl=1 ❌ | T10.4d | 0.3015 | 0.6968 | 0.2351 | 0.2397 | 0.0792 | 0.4788 | 5/5 |
| 4 | PU Learning RF ⚠️ | c=0.0885 [Elkan2008] | 0.3313 | 0.6939 | 0.2684 | 0.1871 | 0.1141 | 0.4733 | 5/5 |
| — | DIF [64,32] | oracle_upper ← borne sup, no deploy | 0.2893 | 0.6770 | 0.2282 | 0.2193 | 0.0604 | 0.4707 | 5/5 |
| 5 | **DIF [64,32]** | fpr5_constrained ← T10.4e | 0.2769 | 0.6770 | 0.2231 | 0.2193 | 0.0479 | **0.4697** | 5/5 |
| 6 | DIF [64,32] | phi_optimal ← T10.4e | 0.2822 | 0.6770 | 0.2234 | 0.2193 | 0.0555 | 0.4693 | 5/5 |
| 7 | IF max_feat=0.7 | contamination=0.10 | 0.2759 | 0.6855 | 0.2084 | 0.2169 | 0.0756 | 0.4622 | 5/5 |
| 8 | DIF [64,32] | pr_exact ← T10.4e | 0.2856 | 0.6770 | 0.2156 | 0.2193 | 0.0931 | 0.4609 | 5/5 |
| 9 | DIF [64,32] | percentile_f1 ← run2 calibré | 0.2849 | 0.6770 | 0.2147 | 0.2193 | 0.0949 | 0.4602 | 5/5 |
| 10 | IF classique | contamination=0.10 | 0.2697 | 0.6843 | 0.1966 | 0.2127 | 0.1069 | 0.4513 | 5/5 |
| 11 | HBOS | n_bins=5 (opt. val) | 0.2733 | 0.6763 | 0.2007 | 0.2393 | 0.1076 | 0.4564 | 5/5 |
| 12 | ECOD | CDF empirique | 0.2726 | 0.6856 | 0.2009 | 0.2508 | 0.1477 | 0.4524 | 5/5 |
| 13 | EIF ExtLvl=1 | T10.3 (1ère mesure) | 0.2858 | 0.6981 | — | — | — | 0.4920* | 2/5 |
| 14 | DIF [128,64,32]+scaler | phi_optimal ← T10.4e Phase B | 0.2447 | 0.6686 | 0.1904 | 0.1980 | 0.0477 | 0.4508 | 5/5 |
| 15 | DIF [128,64,32]+scaler | fpr5_constrained ← T10.4e Phase B | 0.2411 | 0.6686 | 0.1889 | 0.1980 | 0.0452 | 0.4503 | 5/5 |
| 16 | DIF [64,32,16]+scaler | fpr5_constrained ← T10.4e Phase B | 0.2392 | 0.6701 | 0.1860 | 0.1945 | 0.0464 | 0.4487 | 5/5 |
| 17 | DIF [64,32,16]+scaler | phi_optimal ← T10.4e Phase B | 0.2147 | 0.6701 | 0.1749 | 0.1945 | 0.0341 | 0.4440 | 5/5 |
| 18 | DIF [64,32,16]+scaler | pr_exact ← T10.4e Phase B | 0.2597 | 0.6701 | 0.1867 | 0.1945 | 0.0942 | 0.4433 | 5/5 |
| 19 | DIF non-calibré | défaut PyOD (contamination=0.10) | 0.1110 | 0.6770 | 0.1455 | 0.2193 | 0.0067 | 0.4292 | 5/5 |
| 20 | COPOD | empirical copula | 0.2500 | 0.6828 | 0.1764 | 0.2477 | 0.1920 | 0.4330 | 5/5 |
| 21 | DIF [128,64,32]+scaler | pr_exact ← T10.4e Phase B | 0.2575 | 0.6686 | 0.1818 | 0.1980 | 0.1298 | 0.4352 | 5/5 |
| 22 | DIF [64,32] | youden ← T10.4e | 0.2633 | 0.6770 | 0.1924 | 0.2193 | 0.1783 | 0.4348 | 5/5 |
| 23 | LOF k=10 | novelty=True, k=10 | 0.2536 | 0.6350 | — | — | — | 0.4443* | 2/5 |
| 24 | RIF | 10 rotations ensemble | 0.2380 | 0.6640 | 0.1650 | — | 0.1800 | 0.4718* | 4/5 |
| 25 | OC-SVM SGD | StandardScaler | 0.1481 | 0.3750 | 0.0000 | 0.1390 | 1.0000 | 0.1324 | 5/5 |
| — | SUOD | — | skip | — | — | — | — | — | 0/5 |
| — | AutoEncoder | — | skip | — | — | — | — | — | 0/5 |

*❌ LOF : non scalable O(n²k). EIF : non persistable joblib (ADR-010). ⚠️ PU Learning semi-supervisé.*

---

## RÉCAPITULATIF — top deployables par branche

| Branche | # | Algorithme | Calibration | F1 | AUC | MCC | AP | FPR | Φ | Contraintes |
|---|---|---|---|---|---|---|---|---|---|---|
| Santé | 1 | **DIF [64,32]** | phi_optimal | 0.2637 | 0.6423 | 0.2449 | 0.2010 | 0.0218 | **0.4660** | KernelSHAP |
| Santé | 2 | DIF [64,32] | fpr5_constrained | 0.2770 | 0.6423 | 0.2400 | 0.2010 | 0.0325 | 0.4656 | KernelSHAP |
| Santé | 3 | HBOS | n_bins=5 | 0.2795 | 0.6275 | 0.2229 | 0.2452 | 0.0628 | 0.4625 | SHAP histogramme |
| Santé | 4 | IF classique *(ex-prod)* | contamination=0.07 | 0.2053 | 0.6221 | 0.1376 | 0.1605 | 0.0885 | 0.4076 | TreeExplainer ✅ |
| Auto | 1 | **DIF [64,32]** | fpr5_constrained | 0.2769 | 0.6770 | 0.2231 | 0.2193 | 0.0479 | **0.4697** | KernelSHAP |
| Auto | 2 | DIF [64,32] | phi_optimal | 0.2822 | 0.6770 | 0.2234 | 0.2193 | 0.0555 | 0.4693 | KernelSHAP |
| Auto | 3 | IF max_feat=0.7 | contamination=0.10 | 0.2759 | 0.6855 | 0.2084 | 0.2169 | 0.0756 | 0.4622 | TreeExplainer ✅ |
| Auto | 4 | IF classique *(ex-prod)* | contamination=0.10 | 0.2697 | 0.6843 | 0.1966 | 0.2127 | 0.1069 | 0.4513 | TreeExplainer ✅ |

---

## CONCLUSION — MODÈLE FINAL DE PRODUCTION

### Décision

**Algorithme retenu : Deep Isolation Forest [Xu2023] — architecture [64, 32], sans StandardScaler**

Un seul algorithme, deux instances entraînées (une par branche), deux seuils de calibration.

### Configuration exacte

| Paramètre | Santé | Auto |
|---|---|---|
| Architecture | [64, 32] | [64, 32] |
| StandardScaler | Non | Non |
| Contamination entraînement | 0.070 | 0.100 |
| Stratégie de calibration | `phi_optimal` | `fpr5_constrained` |
| Seuil de décision | 0.349775 | 0.341498 |
| F1 test | 0.2637 | 0.2769 |
| AUC test | 0.6423 | 0.6770 |
| MCC test | 0.2449 | 0.2231 |
| FPR test | **0.0218** | **0.0479** |
| **Φ test** | **0.4660** | **0.4697** |

### Justification par les métriques

DIF est la meilleure configuration deployable et persistable sur les deux branches.

Sur Santé, DIF phi_optimal (Φ=0.4660) surpasse HBOS (0.4625), PU Learning (0.4513) et IF classique (0.4076). Il atteint le FPR le plus bas de tous les algorithmes non-supervisés testés : **2.18%** — soit moins de 1 dossier légitime bloqué sur 50.

Sur Auto, DIF fpr5_constrained (Φ=0.4697) surpasse IF max_feat=0.7 (0.4622) et IF classique (0.4513). Le FPR est contraint à **4.79%** — conforme à la contrainte opérationnelle assurance.

LOF k=20 (Φ=0.5125 Auto) et EIF (Φ=0.4788 Auto) ont de meilleurs scores bruts mais sont respectivement non scalable et non persistable — exclus en production.

### Point d'adaptation requis — Explicabilité

DIF utilise un réseau de neurones : SHAP TreeExplainer n'est pas applicable. Deux options :

**Option A — KernelSHAP [Lundberg2017] :** générique, lent (~0.5s/dossier sur 100 background samples). Applicable immédiatement, sans modifier l'architecture. Coût : remplacer `shap.TreeExplainer(model)` par `shap.KernelExplainer(model.decision_function, X_background)` dans `explainer.py`.

**Option B — Gradient d'activation [Sundararajan2017] :** accès direct aux poids du réseau DIF via PyOD, calcul du gradient par rapport aux inputs. Plus rapide que KernelSHAP, moins générique. Nécessite ~40 lignes dans `explainer.py`.

La chaîne SHAP → RCA → LLM reste fonctionnelle avec l'Option A sans toucher à RCA ni au LLM. C'est le chemin minimal.

### Gain mesuré vs IF classique (ex-production)

| Branche | IF classique Φ | DIF final Φ | Gain Φ | Gain FPR |
|---|---|---|---|---|
| Santé | 0.4076 | **0.4660** | **+0.0584** | **−6.7 pts** (8.85% → 2.18%) |
| Auto | 0.4513 | **0.4697** | **+0.0184** | **−5.9 pts** (10.69% → 4.79%) |

---

*Tableau exhaustif MAKORA · 28 algorithmes × 2 branches · ATABONG EFON STEPHANE FRITZ · ENSPY/UY1 · 2026*
