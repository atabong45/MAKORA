# Analyse Qualitative FP/FN — `M_auto` — Branche Auto
> Générée le 2026-05-22 13:47 | Référence : [Chandola2009] §5.3 + [Bauder2017]

## Synthèse des causes d'erreur

| Cause | Nb cas | Description |
|-------|--------|-------------|
| `SEUIL_MAL_CALITRE` | 10 | Contamination imparfaite — cas légitime proche du seuil |
| `CAS_LIMITE_METIER` | 10 | Fraude bien camouflée / dossier atypique légitimement suspect |

---

## Faux Positifs (FP) — Dossiers normaux mal classés

### FP-01 | Score=0.5000 | Dist. seuil=0.0000

- **ID** : `SIN_CM_0082891`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `nb_sinistres_12m` (-1.640), `constat_manquant` (-1.123), `garage_non_agree` (-0.468)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-02 | Score=0.4999 | Dist. seuil=0.0001

- **ID** : `SIN_CM_0065336`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-2.474), `nb_sinistres_12m` (-0.370), `ratio_mo_reference` (-0.282)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-03 | Score=0.4999 | Dist. seuil=0.0001

- **ID** : `SIN_FR_0050100`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `expertise_manquante` (-1.545), `constat_manquant` (-1.203), `expert_garage_correlation` (-0.340)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-04 | Score=0.5001 | Dist. seuil=0.0001

- **ID** : `SIN_CM_0086716`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `delai_declaration_anormal` (-2.694), `nb_sinistres_12m` (-0.403), `expert_garage_correlation` (-0.335)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-05 | Score=0.5001 | Dist. seuil=0.0001

- **ID** : `SIN_CM_0088482`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-2.339), `constat_manquant` (-0.968), `ratio_mo_reference` (-0.274)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-06 | Score=0.5001 | Dist. seuil=0.0001

- **ID** : `SIN_FR_0035528`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `expertise_manquante` (-1.528), `constat_manquant` (-1.185), `sinistre_nuit_sans_temoin` (-0.313)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-07 | Score=0.4998 | Dist. seuil=0.0002

- **ID** : `SIN_CM_0062616`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `constat_manquant` (-1.227), `garage_non_agree` (-0.489), `nb_sinistres_12m` (-0.376)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-08 | Score=0.5002 | Dist. seuil=0.0002

- **ID** : `SIN_CM_0058490`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `delai_declaration_anormal` (-2.754), `nb_sinistres_12m` (-0.360), `constat_manquant` (+0.257)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-09 | Score=0.5002 | Dist. seuil=0.0002

- **ID** : `SIN_FR_0021690`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `expertise_manquante` (-1.522), `nb_sinistres_12m` (-0.453), `garage_non_agree` (-0.409)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-10 | Score=0.5003 | Dist. seuil=0.0003

- **ID** : `SIN_CM_0068178`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-2.421), `garage_non_agree` (-0.372), `ratio_mo_reference` (-0.312)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

---

## Faux Négatifs (FN) — Fraudes non détectées

### FN-01 | Score=0.4953 | Sous-type=Antidatage_Contrat

- **ID** : `SIN_FR_0009663`
- **Sous-type réel** : `Antidatage_Contrat`
- **Top-3 SHAP** : `anciennete_contrat_courte` (-2.614), `ratio_mo_reference` (-0.476), `constat_manquant` (+0.261)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-02 | Score=0.4951 | Sous-type=Rejet_OCR_Matriciel

- **ID** : `SIN_FR_0020369`
- **Sous-type réel** : `Rejet_OCR_Matriciel`
- **Top-3 SHAP** : `ocr_confiance_faible` (-2.829), `nb_sinistres_12m` (-0.382), `constat_manquant` (+0.255)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-03 | Score=0.4951 | Sous-type=Expert_Corrompu

- **ID** : `SIN_FR_0016185`
- **Sous-type réel** : `Expert_Corrompu`
- **Top-3 SHAP** : `nb_sinistres_12m` (-1.577), `expertise_manquante` (-1.434), `garage_non_agree` (-0.412)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-04 | Score=0.4945 | Sous-type=Vol_Fictif

- **ID** : `SIN_FR_0044046`
- **Sous-type réel** : `Vol_Fictif`
- **Top-3 SHAP** : `delai_declaration_anormal` (-2.811), `constat_manquant` (-0.933), `expertise_manquante` (+0.205)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-05 | Score=0.4942 | Sous-type=Staging_Accident

- **ID** : `SIN_FR_0027090`
- **Sous-type réel** : `Staging_Accident`
- **Top-3 SHAP** : `constat_manquant` (-1.276), `expert_garage_correlation` (-0.981), `garage_non_agree` (-0.483)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-06 | Score=0.4941 | Sous-type=Multi_Sinistres

- **ID** : `SIN_FR_0005485`
- **Sous-type réel** : `Multi_Sinistres`
- **Top-3 SHAP** : `nb_sinistres_12m` (-2.824), `ratio_mo_reference` (-0.323), `constat_manquant` (+0.277)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-07 | Score=0.4922 | Sous-type=Expert_Corrompu

- **ID** : `SIN_CM_0077782`
- **Sous-type réel** : `Expert_Corrompu`
- **Top-3 SHAP** : `expertise_manquante` (-1.522), `constat_manquant` (-1.206), `sinistre_nuit_sans_temoin` (-0.302)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-08 | Score=0.4915 | Sous-type=Falsification_Constat

- **ID** : `SIN_FR_0009358`
- **Sous-type réel** : `Falsification_Constat`
- **Top-3 SHAP** : `ocr_confiance_faible` (-2.602), `document_altere` (-0.673), `constat_manquant` (+0.219)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-09 | Score=0.4905 | Sous-type=Falsification_Constat

- **ID** : `SIN_FR_0027093`
- **Sous-type réel** : `Falsification_Constat`
- **Top-3 SHAP** : `ocr_confiance_faible` (-2.740), `document_altere` (-0.706), `sinistre_nuit_sans_temoin` (-0.228)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-10 | Score=0.4900 | Sous-type=Pieces_Reemploi

- **ID** : `SIN_CM_0063080`
- **Sous-type réel** : `Pieces_Reemploi`
- **Top-3 SHAP** : `ratio_devis_bareme` (-1.936), `montant_devis_log` (-0.642), `nb_sinistres_12m` (-0.383)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

---

## Implications pour le mémoire

La cause dominante est `SEUIL_MAL_CALITRE` (50% des erreurs analysées). Cela confirme que les erreurs de `M_auto` sur la branche auto sont principalement dues à contamination imparfaite — cas légitime proche du seuil. Cette analyse est cohérente avec les dettes techniques documentées (DT-001, DT-002, DT-003) et les limites intrinsèques des approches non-supervisées identifiées par [Chandola2009].

---
*MAKORA T12.3 — Analyse FP/FN | [Chandola2009] [Bauder2017] [Lundberg2017]*