# Analyse Qualitative FP/FN — `M_makora` — Branche Auto
> Générée le 2026-05-22 13:47 | Référence : [Chandola2009] §5.3 + [Bauder2017]

## Synthèse des causes d'erreur

| Cause | Nb cas | Description |
|-------|--------|-------------|
| `SEUIL_MAL_CALITRE` | 10 | Contamination imparfaite — cas légitime proche du seuil |
| `CAS_LIMITE_METIER` | 10 | Fraude bien camouflée / dossier atypique légitimement suspect |

---

## Faux Positifs (FP) — Dossiers normaux mal classés

### FP-01 | Score=0.9743 | Dist. seuil=0.4743

- **ID** : `SIN_FR_0030712`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-5.911), `saisie_hors_heures` (+0.274), `document_altere` (+0.234)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-02 | Score=0.9743 | Dist. seuil=0.4743

- **ID** : `SIN_CM_0091188`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-5.911), `saisie_hors_heures` (+0.274), `document_altere` (+0.234)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-03 | Score=0.9743 | Dist. seuil=0.4743

- **ID** : `SIN_CM_0070364`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-5.911), `saisie_hors_heures` (+0.274), `document_altere` (+0.234)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-04 | Score=0.9743 | Dist. seuil=0.4743

- **ID** : `SIN_CM_0065208`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-5.911), `saisie_hors_heures` (+0.274), `document_altere` (+0.234)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-05 | Score=0.9743 | Dist. seuil=0.4743

- **ID** : `SIN_CM_0098905`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-5.911), `saisie_hors_heures` (+0.274), `document_altere` (+0.234)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-06 | Score=0.9743 | Dist. seuil=0.4743

- **ID** : `SIN_CM_0061557`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-5.911), `saisie_hors_heures` (+0.274), `document_altere` (+0.234)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-07 | Score=0.9743 | Dist. seuil=0.4743

- **ID** : `SIN_CM_0076952`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-5.911), `saisie_hors_heures` (+0.274), `document_altere` (+0.234)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-08 | Score=0.9743 | Dist. seuil=0.4743

- **ID** : `SIN_CM_0090030`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-5.911), `saisie_hors_heures` (+0.274), `document_altere` (+0.234)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-09 | Score=0.9743 | Dist. seuil=0.4743

- **ID** : `SIN_CM_0064611`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-5.911), `saisie_hors_heures` (+0.274), `document_altere` (+0.234)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

### FP-10 | Score=0.9743 | Dist. seuil=0.4743

- **ID** : `SIN_FR_0019834`
- **Label réel** : `NORMAL`
- **Top-3 SHAP** : `ocr_confiance_faible` (-5.911), `saisie_hors_heures` (+0.274), `document_altere` (+0.234)
- **Cause classifiée** : `SEUIL_MAL_CALITRE` — Contamination imparfaite — cas légitime proche du seuil
- **Interprétation** : Véhicule haut de gamme avec devis légitimement élevé. Le ratio_devis_bareme dépasse le seuil mais reste cohérent avec la cote Argus. [Viaene2002] — seuil de contamination à revoir sur ce segment.

---

## Faux Négatifs (FN) — Fraudes non détectées

### FN-01 | Score=0.8568 | Sous-type=Doublon_Batch_API

- **ID** : `SIN_FR_0040591`
- **Sous-type réel** : `Doublon_Batch_API`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-02 | Score=0.8568 | Sous-type=Doublon_Batch_API

- **ID** : `SIN_CM_0077656`
- **Sous-type réel** : `Doublon_Batch_API`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-03 | Score=0.8568 | Sous-type=Doublon_Batch_API

- **ID** : `SIN_CM_0080733`
- **Sous-type réel** : `Doublon_Batch_API`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-04 | Score=0.8568 | Sous-type=Doublon_Batch_API

- **ID** : `SIN_CM_0094046`
- **Sous-type réel** : `Doublon_Batch_API`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-05 | Score=0.8568 | Sous-type=Doublon_Batch_API

- **ID** : `SIN_CM_0099927`
- **Sous-type réel** : `Doublon_Batch_API`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-06 | Score=0.8568 | Sous-type=Doublon_Batch_API

- **ID** : `SIN_FR_0022722`
- **Sous-type réel** : `Doublon_Batch_API`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-07 | Score=0.8568 | Sous-type=Doublon_Batch_API

- **ID** : `SIN_FR_0001772`
- **Sous-type réel** : `Doublon_Batch_API`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-08 | Score=0.8568 | Sous-type=Doublon_Batch_API

- **ID** : `SIN_FR_0054804`
- **Sous-type réel** : `Doublon_Batch_API`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-09 | Score=0.8568 | Sous-type=Doublon_Batch_API

- **ID** : `SIN_FR_0054498`
- **Sous-type réel** : `Doublon_Batch_API`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-10 | Score=0.8568 | Sous-type=Doublon_Batch_API

- **ID** : `SIN_CM_0059550`
- **Sous-type réel** : `Doublon_Batch_API`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

---

## Implications pour le mémoire

La cause dominante est `SEUIL_MAL_CALITRE` (50% des erreurs analysées). Cela confirme que les erreurs de `M_makora` sur la branche auto sont principalement dues à contamination imparfaite — cas légitime proche du seuil. Cette analyse est cohérente avec les dettes techniques documentées (DT-001, DT-002, DT-003) et les limites intrinsèques des approches non-supervisées identifiées par [Chandola2009].

---
*MAKORA T12.3 — Analyse FP/FN | [Chandola2009] [Bauder2017] [Lundberg2017]*