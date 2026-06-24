# EDA — Détectabilité des scénarios (SANTE)
> seed=42 · KS p < 0.05 ET |d| > 0.3 [Kolmogorov1933, Cohen1988]

## Synthèse

| Décision | Nb | % |
|---|---|---|
| ✅ **Go** ≥ 2 features | 11 | 50% |
| ⚠️ **Warn** 1 feature | 8 | 36% |
| ❌ **No-go** 0 feature | 3 | 14% |
| **Total** | **22** | 100% |

## Détail par scénario

| Scénario | Catégorie | n | Décision | Feature clé | |d| | Commentaire |
|---|---|---|---|---|---|---|
| Anomalie Benford | INCONNU | 408 | ✅ go | ratio_prix_mercuriale | 1.091 | 0.0000 |
| Biais Sélection OCR | INCONNU | 32 | ✅ go | nb_sinistres_30j_assure | 0.957 | 0.0000 |
| Absence cachet | INCONNU | 349 | ✅ go | ocr_confiance_faible | 1.392 | 0.0000 |
| Biais Tarification | INCONNU | 15 | ✅ go | ratio_prix_mercuriale | 0.967 | 0.0066 |
| Doublon Technique | INCONNU | 205 | ✅ go | flag_doublon_sante | 13.524 | 0.0000 |
| Détournement RIB | INCONNU | 407 | ✅ go | community_score_sante | 0.492 | 0.0001 |
| Erreur conversion | INCONNU | 345 | ✅ go | ratio_prix_mercuriale | 2.863 | 0.0000 |
| Forçage validation | INCONNU | 408 | ✅ go | saisie_hors_heures | 4.660 | 0.0000 |
| Hors Garantie | INCONNU | 673 | ✅ go | nb_sinistres_30j_assure | 0.876 | 0.0000 |
| Soumission multiple | INCONNU | 204 | ✅ go | flag_doublon_sante | 13.524 | 0.0000 |
| Surfacturation pure | INCONNU | 408 | ✅ go | community_score_sante | 0.648 | 0.0000 |
| Dérive Nomenclature | INCONNU | 421 | ⚠️ warn | ratio_prix_mercuriale | 2.535 | 0.0000 |
| Nomadisme médical | INCONNU | 408 | ⚠️ warn | community_score_sante | 0.676 | 0.0000 |
| Omission pathologie | INCONNU | 408 | ⚠️ warn | community_score_sante | 0.609 | 0.0000 |
| Panne Service OCR | INCONNU | 197 | ⚠️ warn | montant_normalise_log | 1.107 | 0.0000 |
| Prêt de carte | INCONNU | 408 | ⚠️ warn | community_score_sante | 0.626 | 0.0000 |
| Soin Post-Mortem | INCONNU | 408 | ⚠️ warn | community_score_sante | 0.575 | 0.0000 |
| Unbundling | FRAUDE | 408 | ⚠️ warn | community_score_sante | 0.621 | 0.0000 |
| Upcoding | FRAUDE | 408 | ⚠️ warn | community_score_sante | 0.648 | 0.0000 |
| Erreur codification | INCONNU | 673 | ❌ no-go | flag_doublon_sante | 0.148 | — |
| Erreur de saisie | INCONNU | 673 | ❌ no-go | ratio_prix_mercuriale | 0.260 | — |
| Schema Drift | INCONNU | 421 | ❌ no-go | flag_doublon_sante | 0.148 | — |

## ⚠️ Scénarios No-Go — À documenter dans le mémoire

Ces 3 scénario(s) ne présentent aucun signal dans les features V1. Isolation Forest ne peut pas les détecter en mode tabulaire non-supervisé. → Section **'Limites du modèle'** du mémoire.

- **Erreur codification** (INCONNU, n=673)
  0/17 features discriminantes (critère : p < 0.05, |d| > 0.3). IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire.

- **Erreur de saisie** (INCONNU, n=673)
  0/17 features discriminantes (critère : p < 0.05, |d| > 0.3). IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire.

- **Schema Drift** (INCONNU, n=421)
  0/17 features discriminantes (critère : p < 0.05, |d| > 0.3). IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire.

---
*MAKORA T10.1 EDA · sante · Réf : [Kolmogorov1933] [Cohen1988] [Chandola2009]*