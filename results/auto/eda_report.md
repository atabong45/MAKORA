# EDA — Détectabilité des scénarios (AUTO)
> seed=42 · KS p < 0.05 ET |d| > 0.3 [Kolmogorov1933, Cohen1988]

## Synthèse

| Décision | Nb | % |
|---|---|---|
| ✅ **Go** ≥ 2 features | 13 | 43% |
| ⚠️ **Warn** 1 feature | 8 | 27% |
| ❌ **No-go** 0 feature | 9 | 30% |
| **Total** | **30** | 100% |

## Détail par scénario

| Scénario | Catégorie | n | Décision | Feature clé | |d| | Commentaire |
|---|---|---|---|---|---|---|
| Falsification_Constat | FRAUDE | 213 | ✅ go | ocr_confiance_faible | 2.767 | 0.0000 |
| Collusion_Garage_Assure | FRAUDE | 213 | ✅ go | expertise_manquante | 1.162 | 0.0000 |
| Constat_Retroactif | FRAUDE | 213 | ✅ go | ocr_confiance_faible | 1.682 | 0.0000 |
| Pieces_Non_Montees | FRAUDE | 213 | ✅ go | ratio_devis_bareme | 3.840 | 0.0000 |
| Staging_Accident | FRAUDE | 214 | ✅ go | constat_manquant | 2.661 | 0.0000 |
| Vol_Fictif | FRAUDE | 214 | ✅ go | delai_declaration_anormal | 11.356 | 0.0000 |
| Antidatage_Contrat | FRAUDE | 214 | ✅ go | anciennete_contrat_courte | 13.546 | 0.0000 |
| Multi_Sinistres | FRAUDE | 214 | ✅ go | nb_sinistres_12m | 5.392 | 0.0000 |
| Oubli_Conversion_XAF_EUR | ERREUR_OP | 190 | ✅ go | vehicule_sur_value | 19.391 | 0.0000 |
| Pieces_Reemploi | FRAUDE | 213 | ✅ go | ratio_devis_bareme | 3.816 | 0.0000 |
| Recyclage_Numerique | FRAUDE | 213 | ✅ go | ocr_confiance_faible | 1.850 | 0.0000 |
| Surfacturation | FRAUDE | 213 | ✅ go | ratio_devis_bareme | 1.244 | 0.0000 |
| Vehicule_Sur_Value | FRAUDE | 214 | ✅ go | expertise_manquante | 1.065 | 0.0000 |
| Benford_Deviation | FRAUDE | 213 | ⚠️ warn | community_score_auto | 0.454 | 0.0438 |
| Biais_OCR_Rural | BIAIS | 240 | ⚠️ warn | ocr_confiance_faible | 6.975 | 0.0000 |
| Corruption_Hash | TECHNIQUE | 300 | ⚠️ warn | ocr_confiance_faible | 1.602 | 0.0000 |
| Erreur_Bareme_MO | ERREUR_OP | 400 | ⚠️ warn | ratio_devis_bareme | 1.160 | 0.0000 |
| Erreur_Codification_Reparation | ERREUR_OP | 400 | ⚠️ warn | ratio_devis_bareme | 0.431 | 0.0000 |
| Expert_Corrompu | FRAUDE | 213 | ⚠️ warn | community_score_auto | 0.467 | 0.0297 |
| Faux_Conducteur | FRAUDE | 213 | ⚠️ warn | community_score_auto | 0.626 | 0.0000 |
| Rejet_OCR_Matriciel | BIAIS | 240 | ⚠️ warn | ocr_confiance_faible | 6.975 | 0.0000 |
| Biais_Geographique_BonusMalus | BIAIS | 240 | ❌ no-go | nb_sinistres_12m | 0.103 | — |
| Derive_Bareme_Inflation | BIAIS | 240 | ❌ no-go | garage_concentration_score | 0.119 | — |
| Derive_Nomenclature | TECHNIQUE | 300 | ❌ no-go | ratio_devis_bareme | 0.131 | — |
| Double_Declaration | ERREUR_OP | 400 | ❌ no-go | ratio_mo_reference | 0.095 | — |
| Doublon_Batch_API | TECHNIQUE | 300 | ❌ no-go | ocr_confiance_faible | 0.287 | — |
| Inversion_Montant | ERREUR_OP | 400 | ❌ no-go | sinistre_nuit_sans_temoin | 0.085 | — |
| Schema_Drift_Dates | TECHNIQUE | 300 | ❌ no-go | ocr_confiance_faible | 0.287 | — |
| Sinistre_Hors_Garantie | ERREUR_OP | 400 | ❌ no-go | ocr_confiance_faible | 0.051 | — |
| Surestimation_Expert | BIAIS | 240 | ❌ no-go | ratio_mo_reference | 0.185 | — |

## ⚠️ Scénarios No-Go — À documenter dans le mémoire

Ces 9 scénario(s) ne présentent aucun signal dans les features V1. Isolation Forest ne peut pas les détecter en mode tabulaire non-supervisé. → Section **'Limites du modèle'** du mémoire.

- **Biais_Geographique_BonusMalus** (BIAIS, n=240)
  0/18 features discriminantes (critère : p < 0.05, |d| > 0.3). IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire.

- **Derive_Bareme_Inflation** (BIAIS, n=240)
  0/18 features discriminantes (critère : p < 0.05, |d| > 0.3). IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire.

- **Derive_Nomenclature** (TECHNIQUE, n=300)
  0/18 features discriminantes (critère : p < 0.05, |d| > 0.3). IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire.

- **Double_Declaration** (ERREUR_OP, n=400)
  0/18 features discriminantes (critère : p < 0.05, |d| > 0.3). IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire.

- **Doublon_Batch_API** (TECHNIQUE, n=300)
  0/18 features discriminantes (critère : p < 0.05, |d| > 0.3). IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire.

- **Inversion_Montant** (ERREUR_OP, n=400)
  0/18 features discriminantes (critère : p < 0.05, |d| > 0.3). IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire.

- **Schema_Drift_Dates** (TECHNIQUE, n=300)
  0/18 features discriminantes (critère : p < 0.05, |d| > 0.3). IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire.

- **Sinistre_Hors_Garantie** (ERREUR_OP, n=400)
  0/18 features discriminantes (critère : p < 0.05, |d| > 0.3). IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire.

- **Surestimation_Expert** (BIAIS, n=240)
  0/18 features discriminantes (critère : p < 0.05, |d| > 0.3). IF ne détectera pas ce scénario. ❌ → Documenter comme limite mémoire.

---
*MAKORA T10.1 EDA · auto · Réf : [Kolmogorov1933] [Cohen1988] [Chandola2009]*