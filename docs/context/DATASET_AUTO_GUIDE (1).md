# DATASET_AUTO_GUIDE.md
## MAKORA Framework — Guide d'utilisation du Dataset Auto (ARGUS)
> Dataset : 100 000 lignes — Format CSV + Parquet
> Pipeline : ARGUS (freMTPL2 + Kaggle Auto Fraud + Synthétique Cameroun)
> Anomalies injectées : 30 scénarios (Cat I à IV), 8% du dataset
> Dernière mise à jour : 16 mai 2026 — Session C (génération initiale)

---

## 1. LOCALISATION ET CHARGEMENT

```
ARGUS/data/processed/
├── dataset_auto_v1.parquet              ← dataset complet (format interne, 19 MB)
├── dataset_auto_v1.csv                  ← dataset complet (consultation, ~150 MB)
├── dataset_auto_test_fixe.parquet       ← split test fixe 20k lignes (NE JAMAIS TOUCHER)
├── dataset_auto_test_fixe.csv           ← idem en CSV
├── dataset_auto_test_fixe.sha256        ← checksum reproductibilité
└── dataset_auto_generation_report.md   ← rapport statistique de génération
```

**Checksum test fixe** : `ddb9cec806ce29c2...` (prefix SHA256)

```python
import pandas as pd

# Chargement CSV (recommandé pour consultation)
df      = pd.read_csv("data/processed/dataset_auto_v1.csv")
df_test = pd.read_csv("data/processed/dataset_auto_test_fixe.csv")

# Chargement Parquet (recommandé pour pipeline ML — plus rapide)
df      = pd.read_parquet("data/processed/dataset_auto_v1.parquet")
df_test = pd.read_parquet("data/processed/dataset_auto_test_fixe.parquet")

print(f"Shape complet : {df.shape}")        # (100000, 114)
print(f"Shape test    : {df_test.shape}")   # (20000, 114)
print(df["Label_Anomalie"].value_counts())
```

---

## 2. STATISTIQUES DU DATASET

| Caractéristique | Valeur |
|---|---|
| **Total lignes** | 100 000 |
| **Taux anomalies global** | 8.00% (8 000 dossiers exactement) |
| **Répartition FR/CM** | 55% France / 45% Cameroun |
| **Répartition flux** | ~70% API / ~30% Scan |
| **Période couverte** | 2021–2025 |
| **Colonnes totales** | 114 |
| **Test fixe** | 20 000 lignes (20%), stratifié sur `Label_Anomalie`, seed=42 |
| **Taille Parquet** | 19.2 MB |
| **Seed reproductibilité** | 42 |

### Distribution par catégorie d'anomalie

| Catégorie | Label | Nb lignes | % dataset |
|---|---|---|---|
| Fraude Intentionnelle | `FRAUDE` | 3 200 | 3.20% |
| Erreurs Opérationnelles | `ERREUR_OP` | 2 400 | 2.40% |
| Biais Système | `BIAIS` | 1 200 | 1.20% |
| Risques Techniques | `TECHNIQUE` | 1 200 | 1.20% |
| Normal | `NORMAL` | 92 000 | 92.00% |

### Sources de données utilisées

| Source | Lignes utilisées | Rôle |
|---|---|---|
| **freMTPL2freq/sev** (Dutang 2020) | 24 944 | Sinistres auto France réels — backbone FR |
| **Kaggle Auto Insurance Fraud** | 100 000 | Distributions features incidents |
| **Synthétique Cameroun** | ~45 000 | Calibré barème ASAC Auto + prix Douala/Yaoundé |

---

## 3. STRUCTURE DES COLONNES PAR DIMENSION (114 colonnes)

### Dimension 1 — Identité & Contrat (21 colonnes)

| Colonne | Type | Description |
|---|---|---|
| `ID_Sinistre` | str | Identifiant unique dossier sinistre |
| `ID_Assure` | str | Identifiant assuré |
| `ID_Police` | str | Numéro de police d'assurance |
| `Pays_Residence` | str | France / Cameroun |
| `Ville_Residence` | str | Ville de résidence |
| `Age_Conducteur` | int | Âge du conducteur habituel |
| `Sexe_Conducteur` | str | M / F |
| `Anciennete_Permis` | int | Ancienneté du permis en années |
| `Marque_Vehicule` | str | Marque du véhicule |
| `Modele_Vehicule` | str | Modèle du véhicule |
| `Annee_Vehicule` | int | Année de mise en circulation |
| `Puissance_Vehicule` | int | Puissance en CV (VehPower freMTPL2) |
| `Type_Carburant` | str | Diesel / Essence / Électrique |
| `Valeur_Venale` | float | Valeur vénale estimée (XAF ou EUR) |
| `BonusMalus` | int | Coefficient bonus-malus (50–350) |
| `Type_Contrat` | str | RC / Tous Risques / Intermédiaire |
| `Date_Souscription` | date | Date souscription contrat |
| `Date_Resiliation` | date | Date résiliation (null si actif) |
| `Anciennete_Contrat` | int | Ancienneté contrat en jours |
| `Region_Vehicule` | str | Région d'immatriculation |
| `Densite_Zone` | int | Densité de population zone (freMTPL2 Density) |

### Dimension 2 — Sinistre & Réparation (→ 54 colonnes, +33 nouvelles)

| Colonne | Type | Description |
|---|---|---|
| `ID_Garage` | str | Identifiant garage/réparateur |
| `Nom_Garage` | str | Nom du garage |
| `Type_Garage` | str | Agréé constructeur / Indépendant / Non agréé |
| `Ville_Garage` | str | Ville du garage |
| `Agrement_CIMA` | bool | Garage agréé CIMA (CM) |
| `ID_Expert` | str | Identifiant expert automobile |
| `Type_Sinistre` | str | Collision / Vol / Bris de glace / Incendie / Catastrophe nat. |
| `Incident_Severity` | str | Minor / Major / Total Loss / Trivial |
| `Collision_Type` | str | Rear / Front / Side / null |
| `Nb_Vehicules_Impliques` | int | Nombre de véhicules impliqués |
| `Bodily_Injuries` | int | Nombre de blessés corporels |
| `Nb_Temoins` | int | Nombre de témoins |
| `Constat_Amiable_Present` | bool | Présence constat amiable |
| `Rapport_Police_Present` | bool | Présence rapport de police |
| `Rapport_Expertise_Signe` | bool | Rapport expertise signé |
| `Montant_Devis` | float | Montant du devis réparation |
| `Montant_Reference_Bareme` | float | Montant de référence barème ASAC/Argus |
| `Montant_MO` | float | Main d'œuvre facturée |
| `Montant_Pieces` | float | Pièces détachées facturées |
| `Taux_Horaire_MO` | float | Taux horaire main d'œuvre |
| `Taux_Reference_MO` | float | Taux horaire de référence barème |
| `Nb_Heures_MO` | float | Nombre d'heures MO facturées |
| `Km_Vehicule` | int | Kilométrage au moment du sinistre |
| `Localisation_Sinistre` | str | Ville/zone du sinistre |
| `Police_Report_Available` | str | YES / NO / ? (Kaggle encoding) |

### Dimension 3 — Financière (→ 75 colonnes, +21 nouvelles)

| Colonne | Type | Description |
|---|---|---|
| `Devise` | str | EUR / XAF |
| `Taux_Change` | float | Taux BEAC 655.957 (null pour FR) |
| `Montant_Devis_EUR` | float | Montant devis converti EUR |
| `Franchise` | float | Montant de la franchise contractuelle |
| `Montant_Net_Apres_Franchise` | float | Montant après déduction franchise |
| `Montant_Rembourse` | float | Montant remboursé à l'assuré |
| `ratio_devis_bareme` | float | `Montant_Devis / Montant_Reference_Bareme` — FEATURE CLÉE |
| `ratio_mo_reference` | float | `Taux_Horaire_MO / Taux_Reference_MO` — FEATURE CLÉE |
| `Depot_Garantie_Paye` | bool | Dépôt de garantie versé |
| `Nb_Sinistres_Historique` | int | Total historique sinistres assuré |
| `Montant_Cumul_Historique` | float | Cumul montants historique |

### Dimension 4 — Temporelle (→ 92 colonnes, +17 nouvelles)

| Colonne | Type | Description |
|---|---|---|
| `Date_Sinistre` | date | Date du sinistre |
| `Date_Declaration` | date | Date de déclaration à l'assureur |
| `Date_Saisie_Systeme` | date | Date saisie informatique |
| `Heure_Saisie` | int | Heure de saisie (7–20) |
| `Heure_Sinistre` | int | Heure du sinistre (0–23) |
| `Jour_Semaine_Saisie` | str | Lundi–Dimanche |
| `Jour_Semaine_Sinistre` | str | Lundi–Dimanche |
| `Delai_Declaration` | int | Jours entre sinistre et déclaration |
| `Delai_Depot_Saisie` | int | Jours entre déclaration et dépôt |
| `Delai_Traitement` | int | Jours de traitement dossier |
| `Flag_Sinistre_Hors_Per` | bool | Sinistre hors période de couverture |
| `Flag_Sinistre_Ferie` | bool | Sinistre un jour férié |
| `Flag_Sinistre_Nuit` | bool | Sinistre entre 20h et 6h |
| `Saison_Sinistre` | str | Hiver / Printemps / Été / Automne |
| `Nb_Sinistres_12m` | int | Sinistres assuré sur 12 mois |
| `Montant_Cumul_12m` | float | Montant cumulé 12 mois |
| `Intervalle_Moyen_Sinistres` | float | Intervalle moyen entre sinistres (jours) |

### Dimension 5 — Documents & OCR (→ 114 colonnes, +22 nouvelles)

| Colonne | Type | Description |
|---|---|---|
| `Source_Flux` | str | API (numérique) / Scan (documentaire) |
| `Score_Authenticite` | float | Score authenticité document [0–1] |
| `Confiance_OCR_Glob` | float | Score OCR global [0–1] (null si API) |
| `Confiance_OCR_Montant` | float | Score OCR champ montant |
| `Confiance_OCR_Garage` | float | Score OCR champ garage |
| `Resolution_DPI` | int | Résolution du scan |
| `Qualite_Image` | float | Qualité image [0–1] |
| `Flag_Document_Altere` | bool | Document potentiellement modifié |
| `Hash_Image` | str | Hash MD5 du document/image |
| `Nb_Pages_Document` | int | Nombre de pages du dossier |
| `Type_Document_Principal` | str | Constat / Expertise / Devis / PV Police |

### Dimension 6 — Labels (vérité terrain — injectés par ARGUS)

| Colonne | Type | Description |
|---|---|---|
| `Label_Anomalie` | str | NORMAL / FRAUDE / ERREUR_OP / BIAIS / TECHNIQUE |
| `Sous_Type_Anomalie` | str | Scénario exact (ex: `Staging_Accident`, `Collusion_Garage_Assure`) |
| `Cause_Racine_RCA` | str | Description cause racine pour moteur RCA |
| `Severite_Anomalie` | str | Nulle / Faible / Moyenne / Haute / Critique |
| `Montant_Prejudice` | float | Préjudice estimé = max(Devis - Barème, 0) |
| `Source_Detection` | str | Méthode de détection attendue |
| `Validee_Par_Auditeur` | bool | Validation auditeur simulée |
| `Date_Validation` | date | Date de validation |
| `Commentaire_Audit` | str | Commentaire libre audit |

---

## 4. CATALOGUE DES 30 SCÉNARIOS D'ANOMALIES

### Cat I — Fraude Intentionnelle (3 200 dossiers, 15 scénarios)

| Code | Scénario | Features discriminantes | Contexte |
|---|---|---|---|
| I-1 | Staging accident (accident simulé) | `Flag_Sinistre_Nuit`, `Nb_Temoins==0`, `Constat_Amiable_Present==False` | CM |
| I-2 | Vol fictif | `Type_Sinistre=='Vol'`, `Rapport_Police_Present==False` | FR+CM |
| I-3 | Véhicule sur-valorisé | `Montant_Devis > Valeur_Venale * 0.8` | FR+CM |
| I-4 | Assurance post-sinistre | `Date_Souscription > Date_Sinistre - 30j` | FR+CM |
| I-5 | Multi-sinistres répétés | `Nb_Sinistres_12m >= 3` | FR+CM |
| I-6 | Faux conducteur habituel | Incohérence `Age_Conducteur` vs `BonusMalus` | FR+CM |
| I-7 | Falsification constat amiable | `Flag_Document_Altere==True` + `Score_Authenticite < 0.3` | FR+CM |
| I-8 | Constat rétroactif | `Date_Declaration < Date_Sinistre` (inversion) | FR+CM |
| I-9 | Recyclage numérique devis | `Hash_Image` identique sur dossiers différents | FR+CM |
| I-10 | Loi de Benford | Distribution premier chiffre `Montant_Devis` anormale | FR+CM |
| I-11 | Surfacturation réparation | `ratio_devis_bareme > 1.5` | FR+CM |
| I-12 | Pièces non montées facturées | `Montant_Pieces` élevé + expertise absente | FR+CM |
| I-13 | Pièces réemploi facturées neuf | `ratio_devis_bareme` modéré + `Type_Garage` non agréé | FR+CM |
| I-14 | Expert corrompu | `ID_Expert` concentré + `ratio_devis_bareme > 1.3` | FR+CM |
| I-15 | Collusion garage-assuré | Concentration `ID_Garage` + `Agrement_CIMA==False` | FR+CM |

### Cat II — Erreurs Opérationnelles (2 400 dossiers, 6 scénarios)

| Code | Scénario | Features discriminantes |
|---|---|---|
| II-1 | Erreur barème main d'œuvre | `ratio_mo_reference` hors plage normale |
| II-2 | Double déclaration même sinistre | `ID_Sinistre` ou clé composite dupliquée |
| II-3 | Inversion montant (frappe) | `Montant_Devis` statistiquement aberrant (outlier) |
| II-4 | Sinistre hors période garantie | `Flag_Sinistre_Hors_Per == True` |
| II-5 | Erreur codification type réparation | `Type_Sinistre` vs `Montant_Pieces` incohérent |
| II-6 | Oubli conversion devise XAF/EUR | `Devise == EUR` + `Pays_Residence == Cameroun` |

### Cat III — Biais Système (1 200 dossiers, 5 scénarios)

| Code | Scénario | Features discriminantes |
|---|---|---|
| III-1 | Dérive barème (inflation non répercutée) | PSI `ratio_devis_bareme` dans le temps |
| III-2 | Biais OCR zones rurales CM | `Resolution_DPI < 72` + ville rurale CM |
| III-3 | Biais géographique BonusMalus | Écart `BonusMalus` par région non justifié |
| III-4 | Surestimation systématique expert | `ID_Expert` avec biais positif historique |
| III-5 | Rejet OCR imprimantes matricielles CM | `Confiance_OCR_Glob < 0.35` + source Scan |

### Cat IV — Risques Techniques (1 200 dossiers, 4 scénarios)

| Code | Scénario | Features discriminantes |
|---|---|---|
| IV-1 | Doublon import batch | `ID_Sinistre` dupliqué techniquement |
| IV-2 | Dérive nomenclature réparation | Code type réparation inconnu dans référentiel |
| IV-3 | Schema drift format dates | `Date_Sinistre` format incohérent (legacy) |
| IV-4 | Corruption hash document | `Hash_Image` préfixé `CORRUPTED_` + `Score_Authenticite < 0.2` |

---

## 5. FEATURES CALCULÉES POUR LE ML

Ces features sont calculées par `AutoModule.engineer_features()` à la volée.

| Feature | Calcul | Importance attendue |
|---|---|---|
| `ratio_devis_bareme` | `Montant_Devis / Montant_Reference_Bareme` | CRITIQUE |
| `ratio_mo_reference` | `Taux_Horaire_MO / Taux_Reference_MO` | HAUTE |
| `delai_declaration_anormal` | `Delai_Declaration > 30` | HAUTE |
| `vehicule_sur_value` | `Montant_Devis > Valeur_Venale * 0.8` | CRITIQUE |
| `garage_non_agree` | `Agrement_CIMA == False` | HAUTE |
| `sinistre_nuit_sans_temoin` | `Flag_Sinistre_Nuit AND Nb_Temoins == 0` | CRITIQUE |
| `constat_manquant` | `Constat_Amiable_Present == False` | HAUTE |
| `expertise_manquante` | `Rapport_Expertise_Signe == False` | HAUTE |
| `nb_sinistres_12m` | Déjà dans dataset | HAUTE |
| `montant_devis_log` | `log(Montant_Devis + 1)` | MOYENNE |
| `anciennete_contrat_courte` | `Anciennete_Contrat < 90` | HAUTE |
| `saisie_hors_heures` | `Heure_Saisie < 7 OR Heure_Saisie > 20` | MOYENNE |
| `garage_concentration_score` | Part sinistres sur même garage (historique) | CRITIQUE |
| `ocr_confiance_faible` | `Confiance_OCR_Glob < 0.5` | HAUTE |
| `document_altere` | `Flag_Document_Altere == True` | CRITIQUE |

---

## 6. PIPELINE ARGUS — ARCHITECTURE

```
freMTPL2freq/sev (Dutang 2020)   → 24 944 dossiers FR réels
Kaggle Auto Insurance Fraud      → Distributions features incidents
Synthétique Cameroun ASAC        → ~45 000 dossiers CM (Autojiji.cm calibré)
        ↓
Dimension 1 : Identité & Contrat     (21 colonnes)
Dimension 2 : Sinistre & Réparation  (→ 54 colonnes)
Dimension 3 : Financière             (→ 75 colonnes)
Dimension 4 : Temporelle             (→ 92 colonnes)
Dimension 5 : Documents & OCR        (→ 114 colonnes)
        ↓
Mélange aléatoire (seed=42)
        ↓
Moteur injection anomalies ARGUS (manager.py)
  Cat I  : 15 scénarios — 3 200 dossiers
  Cat II :  6 scénarios — 2 400 dossiers
  Cat III:  5 scénarios — 1 200 dossiers
  Cat IV :  4 scénarios — 1 200 dossiers
Étanchéité garantie : 1 dossier = 1 seul scénario
Passe de cohérence finale (recalcul totaux après injection)
        ↓
Dataset Parquet + CSV final (100 000 lignes × 114 colonnes)
Split test fixe 20% stratifié seed=42
SHA256 : ddb9cec806ce29c2...
```

---

## 7. PIÈGES CONNUS — LIRE AVANT DE TOUCHER AU DATASET

| Piège | Description | Solution |
|---|---|---|
| **Confiance_OCR null** | Null pour tous les dossiers `Source_Flux == 'API'` — normal | Filtrer par `Source_Flux == 'Scan'` avant usage |
| **Taux_Change null pour FR** | Null pour dossiers France | Imputer 655.957 pour CM si null |
| **Label_Anomalie est une string** | Pas un booléen | `df[df["Label_Anomalie"] != "NORMAL"]` |
| **ratio_devis_bareme déjà présent** | Précalculé dans dataset (contrairement à Santé) | Ne pas recalculer, utiliser directement |
| **Valeur_Venale en XAF pour CM** | Pas convertie en EUR dans le CSV brut | Diviser par 655.957 pour comparer avec FR |
| **freMTPL2 : seulement 24k dossiers réels** | 55k FR attendus → les 30k restants sont synthétiques calibrés | Documenter dans les limites du mémoire |
| **Scénario I-1 (Staging) : CM uniquement** | Spécifique au contexte camerounais | Ne pas s'attendre à le voir dans les dossiers FR |
| **Cat III (Biais) = légitimes** | Classifiés anomalie mais non frauduleux | Seuil de sévérité dans RCA : `Severite_Anomalie != 'Nulle'` |

---

## 8. UTILISATION POUR L'EXPÉRIENCE H0

```python
import pandas as pd
from sklearn.model_selection import train_test_split

# Chargement
df = pd.read_parquet("data/processed/dataset_auto_v1.parquet")

# Label binaire pour sklearn
df["y"] = (df["Label_Anomalie"] != "NORMAL").astype(int)

# Split 70/15/15 — STRATIFIÉ sur y
df_train, df_tmp = train_test_split(df, test_size=0.30, random_state=42, stratify=df["y"])
df_val, df_test  = train_test_split(df_tmp, test_size=0.50, random_state=42, stratify=df_tmp["y"])

print(f"Train : {len(df_train)} | Val : {len(df_val)} | Test : {len(df_test)}")
# → Train : 70000 | Val : 15000 | Test : 15000

# Utiliser le test fixe PRÉ-GÉNÉRÉ par ARGUS (à privilégier pour H0) :
df_test_fixe = pd.read_parquet("data/processed/dataset_auto_test_fixe.parquet")
# → 20 000 lignes, SHA256 : ddb9cec806ce29c2...
```

> ⚠️ **Le test fixe ne doit JAMAIS être utilisé pour l'entraînement ni la validation.**

---

## 9. INSPECTION RAPIDE

```python
# Distribution anomalies
print(df["Label_Anomalie"].value_counts())

# Scénarios injectés
anom = df[df["Label_Anomalie"] != "NORMAL"]
print(anom["Sous_Type_Anomalie"].value_counts())

# Répartition FR/CM
print(df["Pays_Residence"].value_counts())

# Vérifier l'étanchéité
assert df["ID_Sinistre"].duplicated().sum() == 0
assert df[df["Label_Anomalie"] != "NORMAL"]["Sous_Type_Anomalie"].ne("RAS").all()

# Montant moyen devis par catégorie
print(df.groupby("Label_Anomalie")["Montant_Devis"].mean().round(2))

# Taux anomalies par pays
print(df.groupby("Pays_Residence").apply(
    lambda x: (x["Label_Anomalie"] != "NORMAL").mean()
).round(4))
```

---

## 10. CHECKLIST AVANT ENTRAÎNEMENT

```
□ Dataset chargé sans erreur — shape (100000, 114)
□ Taux anomalies vérifié — (df["Label_Anomalie"] != "NORMAL").mean() == 0.08
□ Label binaire créé — df["y"] = (df["Label_Anomalie"] != "NORMAL").astype(int)
□ Features ML calculées — AutoModule.engineer_features(df) appelé
□ Colonnes non numériques encodées ou exclues (ID_, Nom_, str dates...)
□ Valeurs nulles traitées (Confiance_OCR null pour API → imputer 1.0)
□ Test fixe isolé — NE PAS inclure dans le train (SHA256 vérifié)
□ Seed random_state=42 utilisé partout
□ Contamination IF alignée sur taux réel : contamination=0.08
□ Split 70/15/15 stratifié sur y
```

---

*Fin du fichier DATASET_AUTO_GUIDE.md*
*Créé : 16 mai 2026 — Session C (génération initiale ARGUS)*
*Prochaine mise à jour : après T10/T11 (métriques IF/LOF/OC-SVM remplies)*
