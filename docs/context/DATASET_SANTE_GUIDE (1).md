# DATASET_SANTE_GUIDE.md
## MAKORA Framework — Guide d'utilisation du Dataset Santé (UNITY)
> Dataset : ~140 000 lignes — Format CSV
> Pipeline : UNITY (Synthea + ASAC/BEAC + Kaggle Healthcare Fraud)
> Anomalies injectées : 30 scénarios (Cat I à IV), 8% du dataset
> Dernière mise à jour : 16 mai 2026 — Session C

---

## 1. LOCALISATION ET CHARGEMENT

```
data/processed/
├── dataset_sante_v1.csv              ← dataset complet (~140k lignes)
└── dataset_sante_test_fixe.csv       ← split test fixe (NE JAMAIS TOUCHER)
```

```python
import pandas as pd

df      = pd.read_csv("data/processed/dataset_sante_v1.csv")
df_test = pd.read_csv("data/processed/dataset_sante_test_fixe.csv")

print(f"Shape complet : {df.shape}")
print(f"Shape test    : {df_test.shape}")
print(df["Label_Anomalie"].value_counts())
```

---

## 2. STATISTIQUES DU DATASET

| Caractéristique | Valeur |
|---|---|
| **Total lignes** | ~140 000 |
| **Taux anomalies global** | ~8% (~11 200 anomalies) |
| **Répartition FR/CM** | ~50% / ~50% |
| **Répartition flux** | ~50% API / ~50% Scan |
| **Période couverte** | 2021–2025 |
| **Colonnes totales** | ~115 |
| **Test fixe** | 20% stratifié, seed=42 |

### Distribution par catégorie d'anomalie

| Catégorie | Label | Proportion anomalies | ~Nb lignes |
|---|---|---|---|
| Fraude Intentionnelle | `FRAUDE` | 40% | ~4 480 |
| Erreurs Opérationnelles | `ERREUR_OP` | 35% | ~3 920 |
| Biais Système | `BIAIS` | 15% | ~1 680 |
| Risques Techniques | `TECHNIQUE` | 10% | ~1 120 |
| Normal | `NORMAL` | — | ~128 800 |

---

## 3. STRUCTURE DES COLONNES PAR DIMENSION

### Dimension 1 — Identité & Contrat
| Colonne | Type | Description |
|---|---|---|
| `ID_Sinistre` | str | Identifiant unique dossier |
| `ID_Assure` | str | Identifiant assuré |
| `ID_Beneficiaire` | str | Identifiant bénéficiaire |
| `Age_Assure` | int | Âge en années |
| `Sexe` | str | M/F |
| `Pays_Residence` | str | France / Cameroun |
| `Ville_Residence` | str | Ville |
| `Type_Contrat` | str | Individuel / Famille / Groupe |
| `Date_Souscription` | date | Date souscription contrat |
| `Date_Resiliation` | date | Date résiliation (null si actif) |
| `Anciennete_Contrat` | int | Ancienneté en jours |
| `Nb_Sinistres_Historique` | int | Total historique sinistres |
| `Montant_Cumul_Historique` | float | Montant cumulé historique (XAF/EUR) |

### Dimension 2 — Acte Médical
| Colonne | Type | Description |
|---|---|---|
| `ID_Praticien` | str | Identifiant praticien |
| `Nom_Praticien` | str | Nom praticien (fake) |
| `Specialite_Praticien` | str | Spécialité médicale |
| `Code_Acte` | str | Code acte ASAC (CM) ou CCAM (FR) |
| `Libelle_Acte` | str | Libellé de l'acte |
| `Diagnostic_ICD10` | str | Code diagnostic ICD-10 |
| `Type_Prestation` | str | Consultation / Hospitalisation / Médicament |
| `Praticien_Actif` | bool | Agrément en cours |
| `Nb_Actes_Praticien_12m` | int | Volume actes praticien sur 12 mois |

### Dimension 3 — Financière
| Colonne | Type | Description |
|---|---|---|
| `Montant_Facture` | float | Montant facturé |
| `Montant_Rembourse` | float | Montant remboursé |
| `Prix_Reference_Mercuriale` | float | Prix de référence CIMA/CCAM |
| `ratio_prix_mercuriale` | float | `Montant_Facture / Prix_Reference_Mercuriale` — FEATURE CLÉE |
| `Devise` | str | EUR / XAF |
| `Taux_Change_EUR_XAF` | float | 655.957 fixe BEAC (null pour FR) |
| `Montant_EUR_Normalise` | float | Montant converti en EUR |

### Dimension 4 — Temporelle
| Colonne | Type | Description |
|---|---|---|
| `Date_Soin` | date | Date de l'acte médical |
| `Date_Declaration` | date | Date de déclaration à l'assureur |
| `Date_Saisie_Systeme` | datetime | Horodatage saisie informatique |
| `Heure_Saisie` | int | Heure de saisie (7–20) |
| `Delai_Soin_Declaration` | int | Jours entre soin et déclaration |
| `Delai_Declaration_Depot` | int | Jours entre déclaration et dépôt |
| `Flag_Soin_Weekend` | bool | Soin un samedi ou dimanche |
| `Flag_Soin_Ferie` | bool | Soin un jour férié |
| `Flag_Soin_Hors_Periode` | bool | Soin hors période de couverture |
| `Saison_Soin` | str | Hiver / Printemps / Été / Automne |
| `Nb_Sinistres_12m` | int | Sinistres assuré sur 12 mois glissants |
| `Montant_Cumul_12m` | float | Montant cumulé 12 mois |

### Dimension 5 — Documents & OCR
| Colonne | Type | Description |
|---|---|---|
| `Source_Flux` | str | API (numérique) / Scan (documentaire) |
| `Presence_Cachet_Humide` | bool | Présence cachet humide (CM) |
| `Score_Confiance_OCR_Glob` | float | Score OCR global [0–1] (null si API) |
| `Confiance_OCR_Montant` | float | Score OCR champ montant |
| `Confiance_OCR_Code_Acte` | float | Score OCR champ code acte |
| `Resolution_DPI` | int | Résolution du scan (null si API) |
| `Qualite_Image` | float | Qualité image [0–1] |
| `Flag_Document_Altere` | bool | Document potentiellement modifié |
| `Hash_Document` | str | Hash SHA256 du document |
| `Score_Authenticite` | float | Score authenticité document [0–1] |

### Dimension 6 — Labels (vérité terrain)
| Colonne | Type | Description |
|---|---|---|
| `Label_Anomalie` | str | NORMAL / FRAUDE / ERREUR_OP / BIAIS / TECHNIQUE |
| `Sous_Type_Anomalie` | str | Scénario exact injecté (ex: `Surfacturation_Praticien`) |
| `Cause_Racine_RCA` | str | Description cause racine pour RCA |
| `Severite_Anomalie` | str | Nulle / Faible / Moyenne / Haute / Critique |
| `Montant_Prejudice` | float | Montant estimé du préjudice financier |
| `Source_Detection` | str | Méthode de détection attendue |
| `Validee_Par_Auditeur` | bool | Validation auditeur humain (simulée) |
| `Date_Validation` | date | Date de validation |
| `Commentaire_Audit` | str | Commentaire libre audit |

---

## 4. CATALOGUE DES 30 SCÉNARIOS D'ANOMALIES

### Cat I — Fraude Intentionnelle (40% des anomalies)

| Code | Scénario | Features discriminantes |
|---|---|---|
| I-1 | Prêt de carte / Usurpation d'identité | `incoherence_sexe_acte`, `Sexe` vs `Code_Acte` |
| I-2 | Fraude post-mortem | `Date_Soin > Date_Deces_Assure` |
| I-3 | Doublon facturation | Clé composite `(ID_Praticien, Code_Acte, Date_Soin, ID_Assure)` |
| I-4 | Surfacturation prestataire | `ratio_prix_mercuriale > 1.5` |
| I-5 | Phantom billing — acte non réalisé | `Score_Authenticite < 0.3` + cachet absent |
| I-6 | Forçage validation interne | `Presence_Cachet_Humide == False` + montant élevé |
| I-7 | Upcoding (acte mineur → majeur) | `ratio_prix_mercuriale` + `Specialite` vs `Code_Acte` |
| I-8 | Unbundling (acte groupé → actes séparés) | Multiplicité `Code_Acte` même jour même patient |
| I-9 | Falsification ordonnance | `Flag_Document_Altere == True` |
| I-10 | Fraude coordonnée praticien-assuré | Concentration `ID_Praticien` + `ratio_prix_mercuriale` |
| I-11 | Multi-déclaration même sinistre | `Nb_Sinistres_12m` élevé + dates proches |
| I-12 | Loi de Benford (montants suspects) | Distribution premier chiffre `Montant_Facture` |

### Cat II — Erreurs Opérationnelles (35% des anomalies)

| Code | Scénario | Features discriminantes |
|---|---|---|
| II-1 | Inversion chiffres (4500 → 5400) | `Montant_Facture` vs `Prix_Reference_Mercuriale` |
| II-2 | Oubli conversion devise XAF/EUR | `Devise == EUR` + `Pays_Residence == Cameroun` |
| II-3 | Code acte / spécialité incohérent | `Code_Acte` vs `Specialite_Praticien` |
| II-4 | Facture sans cachet humide CM | `Presence_Cachet_Humide == False` + pays CM |
| II-5 | Soin hors période de couverture | `Flag_Soin_Hors_Periode == True` |
| II-6 | Doublon import batch | `ID_Sinistre` dupliqué |

### Cat III — Biais Système (15% des anomalies)

| Code | Scénario | Features discriminantes |
|---|---|---|
| III-1 | Dérive barème (mercuriale non mise à jour) | PSI `ratio_prix_mercuriale` |
| III-2 | Biais OCR zones rurales CM | `Resolution_DPI < 100` + région rurale |
| III-3 | Biais géographique remboursement | Écart taux remboursement par région |
| III-4 | Surestimation systématique praticien | `ratio_prix_mercuriale` praticien > moyenne |
| III-5 | Rejet OCR imprimantes matricielles CM | `Confiance_OCR_Glob < 0.35` + source Scan |

### Cat IV — Risques Techniques (10% des anomalies)

| Code | Scénario | Features discriminantes |
|---|---|---|
| IV-1 | Doublon import batch | `ID_Sinistre` en doublon technique |
| IV-2 | Dérive nomenclature actes | Code acte non reconnu dans référentiel |
| IV-3 | Schema drift format dates | `Date_Soin` format incohérent |
| IV-4 | Corruption hash document | `Hash_Document` invalide |

---

## 5. FEATURES CALCULÉES POUR LE ML

Ces features sont produites par `SanteModule.engineer_features()` — elles ne sont PAS
dans le CSV brut, elles sont calculées à la volée avant l'entraînement.

| Feature | Calcul | Importance attendue |
|---|---|---|
| `ratio_prix_mercuriale` | `Montant_Facture / Prix_Reference_Mercuriale` | CRITIQUE |
| `is_weekend_care` | `Date_Soin.dayofweek >= 5` | HAUTE |
| `delai_soin_depot_anormal` | `Delai_Soin_Declaration > 30` | HAUTE |
| `incoherence_sexe_acte` | Règle métier : sexe vs domaine acte | CRITIQUE |
| `praticien_hors_agrement` | `Praticien_Actif == False` | CRITIQUE |
| `ocr_confiance_faible` | `Score_Confiance_OCR_Glob < 0.5` | HAUTE |
| `document_altere` | `Flag_Document_Altere == True` | CRITIQUE |
| `historique_ratio_praticien` | Moyenne ratio 10 derniers dossiers praticien | CRITIQUE |
| `nb_sinistres_30j` | Sinistres assuré sur 30 jours glissants | HAUTE |
| `montant_normalise_log` | `log(Montant_EUR_Normalise + 1)` | MOYENNE |
| `anciennete_contrat_courte` | `Anciennete_Contrat < 90` | HAUTE |
| `saisie_hors_heures` | `Heure_Saisie < 7 OR Heure_Saisie > 20` | MOYENNE |

---

## 6. PIPELINE ETL APPLIQUÉ (UNITY)

```
Synthea v3.4.0 (HL7 FHIR)     → 806 patients → ~140k actes/dossiers
SNDS/Medicare                  → Référentiel prix actes France
ASAC/BEAC                      → Mercuriale CIMA + taux XAF (synthétique)
Kaggle Healthcare Fraud        → Distributions fraude supplémentaires
        ↓
Harmonisation schéma universel 6 dimensions
Normalisation devises (XAF → EUR, taux BEAC 655.957)
Calcul features dérivées (ratio, flags, historiques)
        ↓
Moteur injection anomalies (manager.py)
30 scénarios Cat I-IV injectés
Étanchéité garantie : 1 dossier = 1 seul scénario (tirage sans remise)
Jitter ±5% sur prix référence (anti-overfitting)
        ↓
Dataset CSV final (~140k lignes × ~115 colonnes)
Split test fixe 20% stratifié seed=42
```

---

## 7. PIÈGES CONNUS — LIRE AVANT DE TOUCHER AU DATASET

| Piège | Description | Solution |
|---|---|---|
| **Score_Confiance_OCR null** | Null pour tous les dossiers `Source_Flux == 'API'` — normal | Filtrer par `Source_Flux == 'Scan'` avant usage |
| **Taux_Change null pour FR** | Null pour dossiers France | Imputer 655.957 pour CM si null |
| **Date_Deces_Assure** | Null pour 99%+ des dossiers — normal | Ne pas confondre null avec vivant |
| **Label_Anomalie est une string** | Pas un booléen — comparaison : `!= 'NORMAL'` | `df[df["Label_Anomalie"] != "NORMAL"]` |
| **Features ML non précalculées** | `ratio_prix_mercuriale` etc. absents du CSV brut | Appeler `SanteModule.engineer_features(df)` |
| **Praticiens surreprésentés** | Quelques praticiens très fréquents (synthétique) | Documenter dans les limites du mémoire |
| **Scénarios Biais (Cat III)** | Légitimes mais classifiés anomalie | Prévoir un seuil de sévérité dans RCA |

---

## 8. UTILISATION POUR L'EXPÉRIENCE H0

```python
import pandas as pd
from sklearn.model_selection import train_test_split

# Chargement
df = pd.read_csv("data/processed/dataset_sante_v1.csv")

# Label binaire pour sklearn
df["y"] = (df["Label_Anomalie"] != "NORMAL").astype(int)

# Split 70/15/15 — STRATIFIÉ sur y
df_train, df_tmp = train_test_split(df, test_size=0.30, random_state=42, stratify=df["y"])
df_val, df_test  = train_test_split(df_tmp, test_size=0.50, random_state=42, stratify=df_tmp["y"])

print(f"Train : {len(df_train)} | Val : {len(df_val)} | Test : {len(df_test)}")
# → Train : ~98000 | Val : ~21000 | Test : ~21000

# Le test fixe PRÉ-GÉNÉRÉ par UNITY est à utiliser en priorité :
df_test_fixe = pd.read_csv("data/processed/dataset_sante_test_fixe.csv")
```

> ⚠️ **Le test fixe ne doit JAMAIS être utilisé pour l'entraînement ni la validation.**
> Il sert uniquement à la mesure des métriques finales de l'expérience H0.

---

## 9. INSPECTION RAPIDE PAR SCÉNARIO

```python
# Distribution des anomalies
print(df["Label_Anomalie"].value_counts())

# Distribution par scénario
anom = df[df["Label_Anomalie"] != "NORMAL"]
print(anom["Sous_Type_Anomalie"].value_counts())

# Isoler un scénario
df_surf = df[df["Sous_Type_Anomalie"] == "Surfacturation_Praticien"]
print(f"Surfacturation : {len(df_surf)} dossiers")

# Vérifier l'étanchéité (1 dossier = 1 anomalie max)
assert df["ID_Sinistre"].duplicated().sum() == 0, "Doublons détectés !"
assert (df[df["Label_Anomalie"] != "NORMAL"]["Sous_Type_Anomalie"] != "RAS").all()

# Montant moyen par catégorie
print(df.groupby("Label_Anomalie")["Montant_Facture"].mean().round(2))
```

---

## 10. CHECKLIST AVANT ENTRAÎNEMENT

```
□ Dataset chargé sans erreur — shape cohérent (~140k × ~115)
□ Taux anomalies vérifié — (df["Label_Anomalie"] != "NORMAL").mean() ≈ 0.08
□ Label binaire créé — df["y"] = (df["Label_Anomalie"] != "NORMAL").astype(int)
□ Features ML calculées — SanteModule.engineer_features(df) appelé
□ Colonnes non numériques encodées ou exclues
□ Valeurs nulles traitées (Score_OCR null pour API → imputer 1.0 ou exclure)
□ Test fixe isolé — NE PAS inclure dans le train
□ Seed random_state=42 utilisé partout
□ Contamination IF alignée sur taux réel : contamination=0.08
□ Split 70/15/15 stratifié sur y
```

---

*Fin du fichier DATASET_SANTE_GUIDE.md*
*Mis à jour : 16 mai 2026 — Session C*
