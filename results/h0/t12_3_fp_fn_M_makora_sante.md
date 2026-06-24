# Analyse Qualitative FP/FN — `M_makora` — Branche Sante
> Générée le 2026-05-22 13:47 | Référence : [Chandola2009] §5.3 + [Bauder2017]

## Synthèse des causes d'erreur

| Cause | Nb cas | Description |
|-------|--------|-------------|
| `CAS_LIMITE_METIER` | 10 | Fraude bien camouflée / dossier atypique légitimement suspect |

---

## Faux Positifs (FP) — Dossiers normaux mal classés

---

## Faux Négatifs (FN) — Fraudes non détectées

### FN-01 | Score=0.5913 | Sous-type=Détournement RIB

- **ID** : `9e1f48aded12a238`
- **Sous-type réel** : `Détournement RIB`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-02 | Score=0.5913 | Sous-type=Hors Garantie

- **ID** : `5304f6e381c4a328`
- **Sous-type réel** : `Hors Garantie`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-03 | Score=0.5913 | Sous-type=Erreur de saisie

- **ID** : `7ad776993f00b311`
- **Sous-type réel** : `Erreur de saisie`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-04 | Score=0.5913 | Sous-type=Absence cachet

- **ID** : `749b2c6c049ab78d`
- **Sous-type réel** : `Absence cachet`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-05 | Score=0.5913 | Sous-type=Erreur conversion

- **ID** : `46a9887efd9c6f49`
- **Sous-type réel** : `Erreur conversion`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-06 | Score=0.5913 | Sous-type=Hors Garantie

- **ID** : `6e4a6165a3be1069`
- **Sous-type réel** : `Hors Garantie`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-07 | Score=0.5913 | Sous-type=Hors Garantie

- **ID** : `f64a0bdc234d731b`
- **Sous-type réel** : `Hors Garantie`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-08 | Score=0.5913 | Sous-type=Dérive Nomenclature

- **ID** : `477564ed30280f93`
- **Sous-type réel** : `Dérive Nomenclature`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-09 | Score=0.5913 | Sous-type=Schema Drift

- **ID** : `e93dd6dbce9ac3e5`
- **Sous-type réel** : `Schema Drift`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

### FN-10 | Score=0.5913 | Sous-type=RAS

- **ID** : `e004b45dc5c475c5`
- **Sous-type réel** : `RAS`
- **Top-3 SHAP** : `saisie_hors_heures` (-4.235), `document_altere` (-0.348), `anciennete_contrat_courte` (-0.101)
- **Cause classifiée** : `CAS_LIMITE_METIER` — Fraude bien camouflée / dossier atypique légitimement suspect
- **Interprétation** : Fraude camouflée : le dossier respecte formellement les contraintes métier. Détectable uniquement avec un historique inter-batches [DT-002].

---

## Implications pour le mémoire

La cause dominante est `CAS_LIMITE_METIER` (100% des erreurs analysées). Cela confirme que les erreurs de `M_makora` sur la branche sante sont principalement dues à fraude bien camouflée / dossier atypique légitimement suspect. Cette analyse est cohérente avec les dettes techniques documentées (DT-001, DT-002, DT-003) et les limites intrinsèques des approches non-supervisées identifiées par [Chandola2009].

---
*MAKORA T12.3 — Analyse FP/FN | [Chandola2009] [Bauder2017] [Lundberg2017]*