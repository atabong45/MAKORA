# IC_BOOTSTRAP_RESULTATS.md
## MAKORA — Intervalles de Confiance Bootstrap 95%
> T-05 · n=1000 · seed=42 · α=0.05 · [Efron1979]
> Métrique principale : MCC [Chicco2020]
> Généré le 07 juin 2026

---

## Branche Santé
*test=21 228 · 6.9% anomalies · 17 features · classé MCC ↓*
*PU Learning exclu (semi-supervisé — avantage informationnel non comparable)*

| Modèle | MCC | IC 95% MCC | F1 | IC 95% F1 | FPR | Statut |
|---|---|---|---|---|---|---|
| **DIF [64,32] phi_optimal** | **0.2446** | **[0.2186–0.2698]** | 0.2632 | [0.2389–0.2869] | 0.0218 | ★ PROD |
| DIF [64,32] fpr5_constrained | 0.2396 | [0.2155–0.2643] | 0.2766 | [0.2528–0.3004] | 0.0325 | candidat |
| HBOS n_bins=5 | 0.2229 | [0.2015–0.2448] | 0.2794 | [0.2591–0.2998] | 0.0628 | candidat |
| COPOD empirique | 0.1578 | [0.1397–0.1757] | 0.2251 | [0.2087–0.2421] | 0.1103 | candidat |
| IF max_feat=0.7 | 0.1410 | [0.1214–0.1587] | 0.2056 | [0.1872–0.2229] | 0.0747 | candidat |
| **IF classique** *(baseline)* | 0.1331 | [0.1141–0.1516] | 0.1997 | [0.1822–0.2170] | 0.0809 | baseline réf. |
| ECOD CDF | 0.1321 | [0.1148–0.1495] | 0.2033 | [0.1875–0.2189] | 0.1249 | candidat |
| LOF k=20 | 0.0647 | [0.0485–0.0812] | 0.1489 | [0.1352–0.1630] | 0.1561 | ❌ O(n²k) |
| OC-SVM SGD | −0.0383 | [−0.0489–−0.0279] | 0.0433 | [0.0339–0.0534] | 0.0936 | ❌ écarté |

### Significativité statistique — DIF vs IF classique (Santé)

IC DIF phi_optimal : [0.2186–0.2698]
IC IF classique   : [0.1141–0.1516]
→ Les intervalles ne se chevauchent pas → amélioration statistiquement significative [Efron1979]

---

## Branche Auto
*test=15 000 · 8.0% anomalies · 18 features · classé MCC ↓*
*PU Learning exclu (semi-supervisé — avantage informationnel non comparable)*

| Modèle | MCC | IC 95% MCC | F1 | IC 95% F1 | FPR | Statut |
|---|---|---|---|---|---|---|
| **DIF [64,32] fpr5_constrained** | **0.2227** | **[0.1974–0.2495]** | 0.2765 | [0.2529–0.3015] | 0.0479 | ★ PROD |
| DIF [64,32] phi_optimal | 0.2231 | [0.1988–0.2491] | 0.2820 | [0.2586–0.3073] | 0.0555 | candidat |
| LOF k=20 | 0.2217 | [0.2002–0.2444] | 0.2916 | [0.2707–0.3117] | 0.1037 | ❌ O(n²k) |
| ECOD CDF | 0.2013 | [0.1802–0.2217] | 0.2729 | [0.2535–0.2907] | 0.1477 | candidat |
| HBOS n_bins=5 | 0.2004 | [0.1784–0.2221] | 0.2730 | [0.2527–0.2929] | 0.1076 | candidat |
| **IF classique** *(baseline)* | 0.1926 | [0.1698–0.2156] | 0.2649 | [0.2440–0.2862] | 0.0938 | baseline réf. |
| IF max_feat=0.7 | 0.1875 | [0.1653–0.2103] | 0.2610 | [0.2406–0.2818] | 0.0990 | candidat |
| COPOD empirique | 0.1767 | [0.1576–0.1960] | 0.2503 | [0.2332–0.2657] | 0.1920 | candidat |
| OC-SVM SGD ⚠ | 0.2523 | [0.2263–0.2782] | 0.1294 | [0.1051–0.1538] | 0.0000 | ❌ écarté |

### Note OC-SVM Auto — résultat trompeur à documenter

MCC=0.2523 avec F1=0.1294 et FPR=0.000 : le modèle ne prédit que 83 anomalies
sur 15 000 dossiers. MCC élevé = artefact (nombreux vrais négatifs, quasi-rien prédit).
Ce n'est pas un bon modèle — c'est un modèle qui ne prédit presque rien.
À documenter comme résultat négatif honnête [Chandola2009].

### Significativité statistique — DIF vs IF classique (Auto)

IC DIF fpr5_constrained : [0.1974–0.2495]
IC IF classique         : [0.1698–0.2156]
→ Les intervalles se chevauchent légèrement → amélioration présente mais moins tranchée qu'en Santé

---

## Récapitulatif — Modèles production et gain vs baseline

| Branche | Modèle PROD | MCC PROD | IC 95% | MCC baseline IF | IC 95% | Chevauchement IC |
|---|---|---|---|---|---|---|
| Santé | DIF [64,32] phi_optimal | 0.2446 | [0.2186–0.2698] | 0.1331 | [0.1141–0.1516] | **Non** → significatif |
| Auto | DIF [64,32] fpr5_constrained | 0.2227 | [0.1974–0.2495] | 0.1926 | [0.1698–0.2156] | Partiel → tendance |

---

## Notes méthodologiques

- Bootstrap percentile [2.5, 97.5] — [Efron1979] The Annals of Statistics
- Métrique principale MCC — [Chicco2020] BMC Genomics : robuste aux classes déséquilibrées
- EIF exclu : modèle non persistable (ADR-010), IC non calculables
- PU Learning exclu de la comparaison : avantage informationnel (labels pseudo) [Elkan2008]
- Warnings sklearn "InconsistentVersionWarning" (1.8.0 → 1.5.2) : sans impact sur les métriques,
  les modèles IF/LOF/OC-SVM ont été entraînés sur sklearn 1.8.0 et évalués sur 1.5.2

---

*T-05 · MAKORA · ATABONG EFON STEPHANE FRITZ · ENSPY/UY1 · 07 juin 2026*
