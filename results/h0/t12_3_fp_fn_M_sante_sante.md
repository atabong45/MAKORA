# Analyse Qualitative FP/FN — `M_sante` — Branche Sante
> Générée le 2026-05-22 13:47 | Référence : [Chandola2009] §5.3 + [Bauder2017]

## Synthèse des causes d'erreur

| Cause | Nb cas | Description |
|-------|--------|-------------|
| `SEUIL_MAL_CALITRE` | 10 | Contamination imparfaite — cas légitime proche du seuil |
| `CAS_LIMITE_METIER` | 10 | Fraude bien camouflée / dossier atypique légitimement suspect |

---

## Faux Positifs (FP) — Dossiers normaux mal classés

### FP-01 | Score=0.5058 | Dist. seuil=0.0058

- **ID** : `f6d2fac2081e11fb`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `saisie_hors_heures` (-2.490), `nb_sinistres_meme_iban` (-0.713), `montant_normalise_log` (-0.316)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Praticien à volume de facturation élevé mais conforme à la mercuriale CIMA. L'IF détecte la densité de sinistres, pas la fraude elle-même. [Bauder2017] — DT-002 : historique_ratio_praticien stateless.

### FP-02 | Score=0.5059 | Dist. seuil=0.0059

- **ID** : `47143e749a710767`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `saisie_hors_heures` (-2.450), `flag_weekend_care` (-0.862), `delai_soin_depot_anormal` (-0.591)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Praticien à volume de facturation élevé mais conforme à la mercuriale CIMA. L'IF détecte la densité de sinistres, pas la fraude elle-même. [Bauder2017] — DT-002 : historique_ratio_praticien stateless.

### FP-03 | Score=0.5059 | Dist. seuil=0.0059

- **ID** : `744fdc966e6538ef`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `flag_weekend_care` (-1.104), `nb_sinistres_meme_iban` (-0.851), `delai_soin_depot_anormal` (-0.627)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Praticien à volume de facturation élevé mais conforme à la mercuriale CIMA. L'IF détecte la densité de sinistres, pas la fraude elle-même. [Bauder2017] — DT-002 : historique_ratio_praticien stateless.

### FP-04 | Score=0.5059 | Dist. seuil=0.0059

- **ID** : `5c08bd3cfd58475b`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `flag_weekend_care` (-1.104), `nb_sinistres_meme_iban` (-0.851), `delai_soin_depot_anormal` (-0.627)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Praticien à volume de facturation élevé mais conforme à la mercuriale CIMA. L'IF détecte la densité de sinistres, pas la fraude elle-même. [Bauder2017] — DT-002 : historique_ratio_praticien stateless.

### FP-05 | Score=0.5059 | Dist. seuil=0.0059

- **ID** : `8758cfdf23631b4e`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `historique_ratio_praticien` (-1.413), `nb_sinistres_meme_iban` (-1.279), `ratio_prix_mercuriale` (-0.750)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Praticien à volume de facturation élevé mais conforme à la mercuriale CIMA. L'IF détecte la densité de sinistres, pas la fraude elle-même. [Bauder2017] — DT-002 : historique_ratio_praticien stateless.

### FP-06 | Score=0.5059 | Dist. seuil=0.0059

- **ID** : `9dd1367827d1e628`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `nb_sinistres_meme_iban` (-1.581), `historique_ratio_praticien` (-1.081), `ratio_prix_mercuriale` (-0.743)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Praticien à volume de facturation élevé mais conforme à la mercuriale CIMA. L'IF détecte la densité de sinistres, pas la fraude elle-même. [Bauder2017] — DT-002 : historique_ratio_praticien stateless.

### FP-07 | Score=0.5061 | Dist. seuil=0.0061

- **ID** : `dffa79241be70141`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `praticien_hors_agrement` (-3.600), `delai_soin_depot_anormal` (-0.453), `flag_weekend_care` (+0.277)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Praticien à volume de facturation élevé mais conforme à la mercuriale CIMA. L'IF détecte la densité de sinistres, pas la fraude elle-même. [Bauder2017] — DT-002 : historique_ratio_praticien stateless.

### FP-08 | Score=0.5063 | Dist. seuil=0.0063

- **ID** : `ca63c4f27f41b1ff`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `saisie_hors_heures` (-2.487), `historique_ratio_praticien` (-0.834), `ratio_prix_mercuriale` (-0.427)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Praticien à volume de facturation élevé mais conforme à la mercuriale CIMA. L'IF détecte la densité de sinistres, pas la fraude elle-même. [Bauder2017] — DT-002 : historique_ratio_praticien stateless.

### FP-09 | Score=0.5063 | Dist. seuil=0.0063

- **ID** : `632ea1dd9df25c84`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `historique_ratio_praticien` (-1.756), `nb_sinistres_meme_iban` (-1.109), `ratio_prix_mercuriale` (-0.842)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Praticien à volume de facturation élevé mais conforme à la mercuriale CIMA. L'IF détecte la densité de sinistres, pas la fraude elle-même. [Bauder2017] — DT-002 : historique_ratio_praticien stateless.

### FP-10 | Score=0.5063 | Dist. seuil=0.0063

- **ID** : `2b984aac34cd2988`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `saisie_hors_heures` (-2.602), `flag_weekend_care` (-1.016), `nb_sinistres_meme_iban` (+0.285)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Praticien à volume de facturation élevé mais conforme à la mercuriale CIMA. L'IF détecte la densité de sinistres, pas la fraude elle-même. [Bauder2017] — DT-002 : historique_ratio_praticien stateless.

---

## Faux Négatifs (FN) — Fraudes non détectées

### FN-01 | Score=0.4999 | Sous-type=Omission pathologie

- **ID** : `e57776ffc75d2931`
- **Sous-type réel** : `Omission pathologie`
- **Top-3 SHAP** : `historique_ratio_praticien` (-2.002), `community_score_sante` (-1.909), `flag_weekend_care` (+0.313)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-02 | Score=0.5002 | Sous-type=Hors Garantie

- **ID** : `b42afa01cddf7ecf`
- **Sous-type réel** : `Hors Garantie`
- **Top-3 SHAP** : `saisie_hors_heures` (-2.517), `delai_soin_depot_anormal` (-0.610), `nb_sinistres_meme_iban` (+0.320)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-03 | Score=0.4995 | Sous-type=RAS

- **ID** : `fa9eaf0c652bab4b`
- **Sous-type réel** : `RAS`
- **Top-3 SHAP** : `historique_ratio_praticien` (-1.680), `community_score_sante` (-1.495), `delai_soin_depot_anormal` (-0.513)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-04 | Score=0.5010 | Sous-type=RAS

- **ID** : `dfe81aeb989e1dd5`
- **Sous-type réel** : `RAS`
- **Top-3 SHAP** : `nb_sinistres_30j_assure` (-2.251), `ratio_prix_mercuriale` (-0.683), `historique_ratio_praticien` (-0.621)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-05 | Score=0.5014 | Sous-type=RAS

- **ID** : `5ddfe2590611f124`
- **Sous-type réel** : `RAS`
- **Top-3 SHAP** : `nb_sinistres_meme_iban` (-1.374), `flag_weekend_care` (-1.054), `delai_soin_depot_anormal` (-0.557)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-06 | Score=0.5014 | Sous-type=Prêt de carte

- **ID** : `12245ed2b0565813`
- **Sous-type réel** : `Prêt de carte`
- **Top-3 SHAP** : `saisie_hors_heures` (-2.502), `flag_weekend_care` (-0.926), `nb_sinistres_meme_iban` (+0.282)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-07 | Score=0.4980 | Sous-type=Doublon Technique

- **ID** : `6f434ac8f1ef8d3b`
- **Sous-type réel** : `Doublon Technique`
- **Top-3 SHAP** : `flag_doublon_sante` (-3.172), `ratio_prix_mercuriale` (-0.777), `nb_sinistres_meme_iban` (+0.306)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-08 | Score=0.5020 | Sous-type=Hors Garantie

- **ID** : `a163acb978aba2d8`
- **Sous-type réel** : `Hors Garantie`
- **Top-3 SHAP** : `saisie_hors_heures` (-2.464), `flag_weekend_care` (-1.004), `historique_ratio_praticien` (-0.284)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-09 | Score=0.5020 | Sous-type=Erreur de saisie

- **ID** : `27f46f6969e44854`
- **Sous-type réel** : `Erreur de saisie`
- **Top-3 SHAP** : `flag_weekend_care` (-0.963), `montant_normalise_log` (-0.924), `ratio_prix_mercuriale` (-0.808)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-10 | Score=0.4978 | Sous-type=Doublon Technique

- **ID** : `4848790b5fc4427d`
- **Sous-type réel** : `Doublon Technique`
- **Top-3 SHAP** : `flag_doublon_sante` (-2.851), `flag_weekend_care` (-0.746), `praticien_concentration` (-0.254)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

---

## Implications pour le mémoire

La cause dominante est `SEUIL_MAL_CALITRE` (50% des erreurs analysées). Cela confirme que les erreurs de `M_sante` sur la branche sante sont principalement dues à contamination imparfaite — cas légitime proche du seuil. Cette analyse est cohérente avec les dettes techniques documentées (DT-001, DT-002, DT-003) et les limites intrinsèques des approches non-supervisées identifiées par [Chandola2009].

---
*MAKORA T12.3 — Analyse FP/FN | [Chandola2009] [Bauder2017] [Lundberg2017]*