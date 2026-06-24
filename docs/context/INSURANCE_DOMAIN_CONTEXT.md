# INSURANCE_DOMAIN_CONTEXT.md
## MAKORA Framework — Contexte Domaine Assurance (Référentiel Expert)
> **Statut :** Document de référence obligatoire — à fournir à l'IA à chaque session
> **Portée :** Santé + Auto. Niveaux : mondial → France → Cameroun/CIMA
> **Auteur :** ATABONG EFON STEPHANE FRITZ
> **Version :** v1.0 — Mai 2026
> **Usage :** Ce fichier ancre chaque décision de feature engineering, de règle RCA
>             et de seuil algorithmique dans la réalité opérationnelle du métier d'assurance.
>             L'IA DOIT consulter ce fichier avant tout code lié aux features, aux règles YAML,
>             aux seuils de détection, ou à la narration LLM.

---

## ⚠️ INSTRUCTIONS POUR L'IA (Claude / autre LLM)

Avant de produire du code lié aux features, aux règles RCA, aux seuils ou à la narration :

**CHECKLIST DOMAINE — À VALIDER MENTALEMENT POUR CHAQUE FEATURE OU RÈGLE :**
- [ ] Cette feature a-t-elle un analogue documenté dans la littérature fraude assurance ?
- [ ] Le seuil utilisé est-il justifié par la réglementation CIMA, un papier académique, ou un standard opérationnel ?
- [ ] La feature tient-elle compte de la qualité de la donnée source (OCR, mapping) ?
- [ ] La feature est-elle calculable indépendamment pour FR et CM sans modifier le Kernel ?
- [ ] Le code préserve-t-il la décision humaine finale (pas de rejet automatique) ?
- [ ] Les montants sont-ils systématiquement normalisés en XAF avant tout calcul de ratio ?

**RÈGLES ABSOLUES POUR L'IA :**
1. Ne jamais comparer un montant en EUR avec un prix de référence en XAF sans conversion (taux BEAC : 1 EUR = 655.957 XAF, fixe).
2. Ne jamais hardcoder un seuil de fraude sans référence à ce fichier ou à un papier académique.
3. Ne jamais produire un `is_anomaly=True` qui déclenche un rejet automatique — uniquement une alerte pour décision humaine.
4. Toujours tenir compte de `Confiance_OCR_Glob` avant d'utiliser un champ extrait par OCR comme feature.
5. Un praticien avec `Praticien_Actif=False` est systématiquement un signal fort — ne jamais l'ignorer.

---

## PARTIE 1 — RÉALITÉ ET COMPLEXITÉ DU MÉTIER D'ASSURANCE

### 1.1 Le cycle de vie d'un sinistre — ce que les données reflètent

Un sinistre en assurance n'est pas un événement instantané. C'est un **processus en 7 étapes** dont chaque transition génère des données exploitables et des opportunités de fraude :

```
[SOUSCRIPTION]
    ↓ Vérification du risque déclaré vs risque réel (fraude à la souscription)
[SURVENANCE DU SINISTRE]
    ↓ Délai soin→dépôt : fenêtre de manipulation des dates
[DÉPÔT DU DOSSIER]
    ↓ Documents produits : factures, ordonnances, rapports (falsification)
[INSTRUCTION]
    ↓ Vérification des droits, des tarifs, des plafonds
[DÉCISION DE REMBOURSEMENT]
    ↓ Accord / rejet / enquête complémentaire
[PAIEMENT]
    ↓ Virement / Mobile Money : détection doublons de paiement
[ARCHIVAGE & RECOURS]
    ↓ Réclamations en appel, recours contre tiers
```

**Implication pour MAKORA :** Les features temporelles (Delai_Soin_Depot, Delai_Depot_Saisie, Delai_Traitement) ne sont pas de simples métadonnées — ce sont des indicateurs de manipulation documentaire.

---

### 1.2 La taxonomie complète de la fraude en assurance santé

#### 1.2.1 Fraude par le prestataire (Provider Fraud) — la plus coûteuse

| Type | Définition | Signature dans les données |
|---|---|---|
| **Upcoding** | Facturer un acte de niveau supérieur à celui réellement effectué | `Ratio_Prix` > 1.3 ET `Code_Acte` de spécialité plus élevée que `Specialite_Praticien` |
| **Unbundling** | Facturer séparément des actes normalement groupés en une seule cotation | `Nb_Actes_Meme_Jour` > 3 ET codes actes séquentiellement liés dans la nomenclature |
| **Phantom Billing** | Facturer des actes jamais réalisés | `Praticien_Actif = False` OU patient décédé (`Statut_Vital = 0`) avant la date de soin |
| **Duplicate Billing** | Soumettre le même acte plusieurs fois | `Flag_Doublon = True` OU `Hash_Image` vu plus d'une fois (`Nb_Fois_Hash_Vu > 1`) |
| **Service Substitution** | Facturer un acte réalisable mais non prescrit | `Prescription_Med = False` ET acte nécessitant obligatoirement une prescription |
| **Surfacturation directe** | Prix facturé supérieur au tarif de référence | `Ratio_Prix > 1.5` (seuil CIMA) |
| **Kickback** | Rétro-commission entre praticien et assuré complice | Communauté dense dans le graphe praticien↔assuré |

**Référence :** [Bauder2017] Bauder & Khoshgoftaar (2017) — Medicare fraud detection. ICMLA.

#### 1.2.2 Fraude par l'assuré (Insured Fraud)

| Type | Définition | Signature dans les données |
|---|---|---|
| **Fraude identitaire** | Utiliser les droits d'un autre assuré | `Relation_Assure` incohérent avec l'acte soumis |
| **Antidatage** | Modifier la date du soin pour la faire rentrer dans la période de couverture | `Flag_Soin_Hors_Per = True` / `Date_Soin` < `Date_Souscription` |
| **Soins fictifs** | Inventer des soins avec complicité du praticien | Combinaison phantom billing côté praticien |
| **Double assurance** | Réclamer le même soin auprès de deux assureurs | `Montant_Doublon > 0` |
| **Fraude à la carence** | Déclarer une pathologie préexistante comme nouvelle | Diagnostic grave apparu < 30 jours après souscription |

#### 1.2.3 Fraude documentaire

| Type | Définition | Signature dans les données |
|---|---|---|
| **Falsification de facture** | Modifier les montants sur un document réel | `Flag_Doc_Altere = True` / EXIF "Photoshop" |
| **Faux document** | Créer de toutes pièces une facture | `Presence_Cachet = False` (marché CM) / `Score_Authenticite < 0.5` |
| **Réutilisation de document** | Soumettre plusieurs fois le même scan | `Nb_Fois_Hash_Vu > 1` |
| **Scan de mauvaise qualité intentionnel** | Rendre illisible un document pour masquer des incohérences | `Confiance_OCR_Glob < 0.5` de façon systématique chez un assure |

---

### 1.3 La taxonomie complète de la fraude en assurance auto

#### 1.3.1 Fraude au sinistre

| Type | Définition | Signature dans les données |
|---|---|---|
| **Staged Accident** | Accident volontairement provoqué ou simulé | Heure nocturne + zone isolée + blessures légères + dommages importants |
| **Inflation des dommages** | Majorer les dégâts réels sur le rapport de réparateur | `Montant_Devis` / `Valeur_Vehicule` > 0.6 (proche de la valeur totale) |
| **Fantômes passagers** | Déclarer des blessés fictifs | Nb_Blessés >> médiane pour type d'accident |
| **Sinistre antidaté** | Déclarer un sinistre survenu avant la souscription ou après résiliation | `Date_Sinistre` < `Date_Souscription` ou > `Date_Resiliation` |
| **Vol fictif** | Déclarer un véhicule volé encore en circulation | Contrôle RNI (registre national immatriculation) |
| **Réparateur complice** | Facturation gonflée par le garage avec complicité | Concentration de sinistres sur 1-2 réparateurs pour un assure |

**Référence :** [Viaene2002] Viaene et al. (2002) — Automobile insurance fraud detection. Journal of Risk and Insurance.
**Référence :** [Subudhi2017] Subudhi & Panigrahi (2017) — JOEKSU.

#### 1.3.2 Fraude à la souscription (auto)

| Type | Définition | Signature dans les données |
|---|---|---|
| **Fausse adresse** | Déclarer une adresse à risque moindre | Adresse déclarée vs. GPS_Scan des documents |
| **Faux conducteur principal** | Déclarer un conducteur moins risqué | `Age_Conducteur` déclaré ≠ profil sinistres |
| **Kilométrage sous-déclaré** | Minorer le kilométrage annuel déclaré | `Km_Sinistre` vs `Km_Declare` |

---

### 1.4 Les biais statistiques propres aux données d'assurance

Ces biais doivent systématiquement être pris en compte dans le feature engineering :

**Biais 1 — Sous-représentation des fraudes avancées**
Les données historiques ne contiennent que les fraudes *détectées*. Les fraudes sophistiquées (upcoding subtil, kickbacks) sont sous-représentées ou absentes. L'IF non-supervisé est justifié car il ne dépend pas de labels historiques.

**Biais 2 — Variabilité légitime des prix**
Un `Ratio_Prix` de 1.4 peut être un upcoding ou un dépassement d'honoraires légal. Le feature seul n'est pas suffisant — il doit être croisé avec `Depassement_Hono` et `Cotation_Modif`.

**Biais 3 — Saisonnalité des soins**
Les consultations augmentent en hiver (grippe), les hospitalisations diminuent en août (vacances). Un `Freq_Consult_30J` élevé en novembre est moins suspect qu'en juillet. La feature `Saison_Soin` est donc un contextualisateur, pas un indicateur de fraude.

**Biais 4 — Hétérogénéité des praticiens**
Un cardiologue facture légitimement 3× plus qu'un généraliste. Toute comparaison de montants doit être faite **intra-spécialité**, jamais toutes spécialités confondues. La feature `Percentile_Montant` dans le dataset encode cette comparaison relative.

**Biais 5 — Effet de la franchise**
Les dossiers dont le montant est inférieur à la franchise (`Franchise_Contrat`) ne sont normalement pas soumis. Si un assuré soumet régulièrement des dossiers sous franchise, c'est un signal comportemental anormal.

---

### 1.5 Règles métier structurantes (universelles)

Ces règles s'appliquent indépendamment du pays et doivent être encodées dans le YAML ou vérifiées dans le feature engineering :

| Règle | Condition | Action MAKORA |
|---|---|---|
| Praticien inactif | `Praticien_Actif = False` | Alerte critique systématique — priorité maximale |
| Patient décédé | `Statut_Vital = 0` ET `Date_Soin > Date_Deces` | Alerte critique — phantom billing |
| Hors période | `Flag_Soin_Hors_Per = True` | Alerte haute |
| Hors nomenclature | `Flag_Hors_Nomen = True` | Alerte haute |
| Document altéré | `Flag_Doc_Altere = True` | Alerte critique — fraude documentaire |
| Seuil plafond | `Montant_Cumul_12M > Plafond_Annuel` | Alerte haute — dépassement possible |
| Doublon de paiement | `Flag_Doublon = True` | Alerte critique |

---

## PARTIE 2 — SPÉCIFICITÉS RÉGLEMENTAIRES FRANCE

### 2.1 Cadre réglementaire

| Élément | Détail |
|---|---|
| **Nomenclature actes** | CCAM (Classification Commune des Actes Médicaux) — > 7 000 codes |
| **Référentiel prix** | SNDS (Système National des Données de Santé) / tarifs Sécu |
| **Format flux** | NOEMIE (Norme Ouverte d'Échanges entre la Maladie et les Intervenants Extérieurs) |
| **Régulateur** | ACPR (Autorité de Contrôle Prudentiel et de Résolution) |
| **Loi données santé** | RGPD + Loi Informatique et Libertés + HDS (Hébergeur Données Santé) |
| **Taux de fraude estimé** | 2-5% des remboursements (source : Assurance Maladie, rapport 2023) |

### 2.2 Particularités CCAM importantes pour le feature engineering

- Les codes CCAM sont hiérarchisés : les 2 premiers caractères = chapitre anatomique. Une incohérence entre le chapitre et la spécialité du praticien est détectable algorithmiquement.
- Les actes marqués "incompatibles" dans la CCAM ne peuvent légalement pas être facturés le même jour — `Nb_Actes_Meme_Jour` couplé à `Flag_Acte_Incomp` est un signal fort.
- Les actes de chirurgie ont une DMS (Durée Moyenne de Séjour) de référence. `Ratio_DMS = DMS_Reelle / DMS_Reference` : un ratio < 0.5 suggère une hospitalisation trop courte pour l'acte facturé.

---

## PARTIE 3 — SPÉCIFICITÉS RÉGLEMENTAIRES CAMEROUN / CIMA

### 3.1 Le cadre CIMA

La **CIMA** (Conférence Interafricaine des Marchés d'Assurance) est l'organe de régulation de l'assurance pour 14 pays africains dont le Cameroun. Son code (Code CIMA) est le texte de référence.

| Élément | Détail |
|---|---|
| **Nomenclature actes santé** | ASAC (Association des Sociétés d'Assurance du Cameroun) |
| **Référentiel prix** | Mercuriale CIMA — liste officielle des prix de référence en XAF |
| **Devise** | XAF (Franc CFA) — taux fixe avec EUR : **1 EUR = 655.957 XAF** (taux BEAC) |
| **Régulateur** | CIMA + MINFI (Ministère des Finances Cameroun) |
| **Délai légal dépôt** | 90 jours après le soin (au-delà : prescription sauf cas exceptionnel) |
| **Document obligatoire** | Facture acquittée + ordonnance + **cachet humide de l'établissement** |
| **Taux de fraude estimé** | 8-15% (estimation terrain — absence de données officielles publiées) |

### 3.2 La mercuriale CIMA — comment elle fonctionne

La mercuriale est un fichier tabulaire qui associe :
- Un `Code_Acte` (nomenclature ASAC)
- Un `Libelle_Officiel`
- Un `Prix_Ref_XAF` (prix de référence en francs CFA)
- Une `Categorie` (Acte médical / Médicament / Biologie / Radiologie / Hospitalisation)

**Règles d'usage dans MAKORA :**

1. **Conversion obligatoire** : si le dataset contient des montants en EUR (flux France), convertir en XAF avant toute comparaison avec la mercuriale. Taux : `montant_XAF = montant_EUR × 655.957`.

2. **Code acte absent de la mercuriale** : deux cas possibles :
   - Code CCAM (France) vs code ASAC (Cameroun) : ne pas comparer directement — utiliser le Libelle pour correspondance approximative si besoin.
   - Code inconnu : `ratio_prix_mercuriale = None` → feature non calculable → ne pas imputer à 1.0 silencieusement, mettre un flag `flag_code_hors_mercuriale = True`.

3. **Jitter de tolérance** : la mercuriale est révisée périodiquement. Un ratio entre 0.95 et 1.05 est considéré comme conforme (jitter de ±5% documenté dans la conception du dataset).

4. **Format du fichier mercuriale** : deux formats existent selon la source.
   - Mercuriale camerounaise : colonne `Prix_Ref_XAF`
   - Mercuriale française pour comparaison : colonne `Prix_Ref_EUR`
   - Le `MercurialeLoader` doit normaliser les deux vers `Prix_Ref_XAF` via le taux BEAC.

### 3.3 Les patterns de fraude spécifiques au Cameroun

Ces patterns sont issus des pratiques terrain documentées par les sociétés d'assurance camerounaises :

| Pattern | Description | Signature données |
|---|---|---|
| **Surfacturation mercuriale** | Facturer au-dessus du prix CIMA | `ratio_prix_mercuriale > 1.5` |
| **Faux cachet** | Apposer un cachet contrefait ou absent | `Presence_Cachet = False` + dossier soumis |
| **Ordonnance antidatée** | Date de prescription postérieure à la date de soin | `Date_Prescription > Date_Soin` |
| **Praticien fantôme** | Praticien sans agrément RPPS valide | `RPPS_Agrement` non vérifié dans le registre |
| **Mobile Money circulaire** | Remboursement vers un IBAN utilisé par de nombreux assurés | `Nb_Sinistres_Meme_IBAN > 10` |
| **Soin pendant carence** | Soin dans la période de carence du contrat | `Periode_Carence_Act = True` |
| **Soin jour férié** | Consultation dans un établissement public un jour férié | `Flag_Soin_Ferie = True` + `Type_Etablissement = Hôpital Public` |

### 3.4 Contraintes qualité documentaire spécifiques au Cameroun

Ces contraintes doivent systématiquement conditionner l'utilisation des features OCR :

| Contrainte | Impact sur les données | Comportement MAKORA |
|---|---|---|
| **Cachet humide** | Détection par masque HSV OpenCV — taux d'erreur estimé ~15% sur documents < 200 DPI | Ne jamais utiliser `Presence_Cachet` comme signal binaire dur — pondérer par `Confiance_OCR_Glob` |
| **Documents photographiés** (pas scannés) | Distorsion, ombres, reflets | `Resolution_DPI < 150` → qualité insuffisante → `Qualite_Image = 0` |
| **Factures manuscrites** | Tesseract/EasyOCR peu fiable sur écriture manuscrite | `Confiance_OCR_Glob < 0.5` → fallback LLM structuring obligatoire |
| **Montants en lettres** | "sept mille cinq cents" non parsé par regex | Nécessite LLM pour extraction → `Confiance_Montant` spécifique |
| **Codes ASAC non standardisés** | Certains établissements utilisent des codes maison | `Flag_Hors_Nomen = True` probable → ne pas rejeter automatiquement |
| **Tampons multicolores** | Un même établissement peut avoir plusieurs cachets (rouge, bleu, noir) | Le détecteur de cachet doit couvrir les 3 plages HSV |

---

## PARTIE 4 — FEATURES ENGINEERING — RÉFÉRENTIEL PAR DOMAINE

### 4.1 Features santé — référentiel de seuils justifiés

| Feature | Formule | Seuil alerte | Justification |
|---|---|---|---|
| `ratio_prix_mercuriale` | `Prix_Unitaire_Facture_XAF / Prix_Ref_XAF` | > 1.5 | Seuil CIMA — tolérance opérationnelle standard |
| `incoherence_sexe_acte` | Actes sexe-spécifiques vs `Sexe_Assure` | = 1 (binaire) | Règle métier universelle — acte gynécologique sur homme |
| `historique_ratio_praticien` | Moyenne des `Ratio_Prix` du praticien sur le batch | > 1.3 | Signal comportemental — praticien systématiquement au-dessus du tarif |
| `nb_sinistres_30j` | Count `ID_Assure` sur fenêtre 30 jours | > 5 | [Bauder2017] — fréquence anormale de réclamations |
| `is_weekend_care` | `Jour_Semaine_Saisie in [Samedi, Dimanche]` | = 1 (contexte) | Indicateur documentaire — saisie hors heures ouvrées |
| `ratio_dms` | `DMS_Reelle / DMS_Reference` | < 0.5 | Hospitalisation trop courte pour l'acte facturé |
| `delai_soin_depot` | `Date_Depot - Date_Soin` (jours) | > 90 | Délai légal CIMA — au-delà : suspect ou prescription |
| `flag_acte_incompatible` | `Flag_Acte_Incomp = True` ET `Nb_Actes_Meme_Jour > 1` | Combinaison | CCAM — actes légalement non cumulables |
| `score_ocr_faible` | `Confiance_OCR_Glob < 0.5` | < 0.5 | Features OCR non fiables si score bas |
| `concentration_iban` | `Nb_Sinistres_Meme_IBAN` | > 10 | Signal Mobile Money circulaire (spécifique CM) |

### 4.2 Features auto — référentiel de seuils justifiés

| Feature | Formule | Seuil alerte | Justification |
|---|---|---|---|
| `ratio_devis_valeur` | `Montant_Devis / Valeur_Vehicule` | > 0.7 | Inflation dommages — approche valeur totale |
| `nb_sinistres_12m` | Count sinistres sur 12 mois | > 3 | [Viaene2002] — fréquence anormale auto |
| `anciennete_contrat_sinistre` | Jours entre `Date_Souscription` et premier sinistre | < 30 | Fraude à la souscription — sinistre immédiat |
| `heures_nocturnes` | `Heure_Saisie in [22h-6h]` | = 1 (contexte) | Staged accidents souvent nocturnes |
| `reparateur_concentre` | Count sinistres sur même réparateur par assuré | > 3 | Entente réparateur-assuré |
| `ratio_km_sinistre` | `Km_Sinistre / Km_Declare_Annuel` | > 1.5 | Kilométrage sous-déclaré à la souscription |
| `localisation_risque` | Distance GPS entre adresse déclarée et lieu sinistre | > 500 km systématique | Fausse adresse de souscription |

---

## PARTIE 5 — RÈGLES RCA PAR BRANCHE (RÉFÉRENTIEL YAML)

### 5.1 Structure d'une règle RCA correcte

Chaque règle RCA dans le YAML du module DOIT avoir :
- Un `rule_id` unique (ex: `RCA_SURF_001`)
- Une `category` (ex: `Surfacturation`)
- Une `subcategory` (ex: `Surfacturation Mercuriale CIMA`)
- Une `condition` exprimée sur des features calculées (pas des colonnes brutes)
- Un `confidence` entre 0 et 1 (justifié par la précision observée de la règle)
- Une `priority` (1 = plus haute) pour le Chain of Responsibility
- Un `action` décrivant la recommandation pour le gestionnaire

### 5.2 Règles RCA santé — catalogue de référence

```
RCA_DEAD_001   : Praticien inactif + acte soumis              → Phantom Billing      confidence=0.95  priority=1
RCA_GHOST_001  : Patient décédé + date soin postérieure       → Phantom Billing      confidence=0.99  priority=1
RCA_DOC_001    : Document altéré (EXIF Photoshop)             → Fraude documentaire  confidence=0.90  priority=1
RCA_DUP_001    : Hash image vu > 1 fois                       → Doublon document     confidence=0.95  priority=1
RCA_SURF_001   : ratio_prix_mercuriale > 1.5                  → Surfacturation       confidence=0.80  priority=2
RCA_UPCODE_001 : Spécialité incohérente avec chapitre CCAM    → Upcoding             confidence=0.75  priority=2
RCA_UNBUNDL_001: Nb_Actes_Meme_Jour > 3 + actes liés         → Unbundling           confidence=0.70  priority=2
RCA_FREQ_001   : nb_sinistres_30j > 5                         → Fréquence anormale   confidence=0.65  priority=3
RCA_CARENCE_001: Soin pendant période de carence              → Fraude à la carence  confidence=0.85  priority=2
RCA_CACHET_001 : Presence_Cachet=False (CM uniquement)        → Document incomplet   confidence=0.70  priority=3
RCA_IBAN_001   : Nb_Sinistres_Meme_IBAN > 10                  → Réseau Mobile Money  confidence=0.75  priority=2
RCA_DMS_001    : Ratio_DMS < 0.5                              → Hospitalisation courte confidence=0.65 priority=3
```

### 5.3 Règles RCA auto — catalogue de référence

```
RCA_STAG_001   : Heure nocturne + ratio_devis_valeur > 0.7   → Staged accident      confidence=0.70  priority=1
RCA_INFL_001   : ratio_devis_valeur > 0.7                    → Inflation dommages   confidence=0.75  priority=2
RCA_FREQ_AUTO_001: nb_sinistres_12m > 3                      → Fréquence anormale   confidence=0.65  priority=3
RCA_SOUSC_001  : anciennete_contrat_sinistre < 30 jours      → Fraude souscription  confidence=0.80  priority=2
RCA_REP_001    : reparateur_concentre > 3                    → Entente réparateur   confidence=0.70  priority=2
RCA_KM_001     : ratio_km_sinistre > 1.5                     → Kilométrage frauduleux confidence=0.65 priority=3
```

---

## PARTIE 6 — SEUILS ET PARAMÈTRES ML JUSTIFIÉS

### 6.1 Paramètre contamination de l'Isolation Forest

| Valeur | Justification |
|---|---|
| `contamination = 0.08` | [Bauder2017] — taux fraude Medicare estimé 3-10%. Choix conservateur à 8% pour limiter les faux positifs en contexte opérationnel. À recalibrer sur le taux réel observé dans chaque dataset. |

### 6.2 Split train/validation/test

| Partition | Ratio | Règle |
|---|---|---|
| Train | 70% | Entraînement des modèles |
| Validation | 15% | Sélection des hyperparamètres |
| Test | 15% | Évaluation finale — JAMAIS TOUCHÉ avant l'évaluation finale |
| Seed | `random_state=42` | Reproductibilité |
| Stratification | Sur `Label_Anomalie` | Préserver le ratio fraude/normal |

### 6.3 Métriques prioritaires pour l'assurance

En assurance, la métrique la plus importante opérationnellement est le **False Positive Rate (FPR)** — un faux positif signifie qu'un assuré légitime est suspecté à tort, ce qui génère une plainte et une perte de client. La précision est donc priorisée sur le rappel.

| Métrique | Cible minimale | Raison |
|---|---|---|
| F1-score | ≥ 0.70 | Équilibre Precision/Recall |
| Precision (PPV) | ≥ 0.75 | Limiter les faux positifs — priorité opérationnelle |
| Recall (Sensitivity) | ≥ 0.60 | Détecter au minimum 60% des fraudes |
| AUC-ROC | ≥ 0.80 | Discriminance globale du modèle |
| FPR | ≤ 0.10 | Maximum 10% de faux positifs acceptables |
| MCC | ≥ 0.50 | Robustesse sur données déséquilibrées |

---

## PARTIE 7 — ARCHITECTURE OCR RECOMMANDÉE

### 7.1 Composants recommandés

| Composant | Outil | Raison |
|---|---|---|
| OCR principal | **EasyOCR** (`easyocr`) | Meilleure précision sur documents dégradés vs Tesseract, supporte le français, pip install |
| OCR fallback | **Tesseract** (`pytesseract`) | Déjà dans la stack, léger |
| Détection cachet | **OpenCV** (HSV mask) | Déjà dans la stack |
| Structuration sortie | **LLM Ollama** (Qwen 2.5:7b) | Déjà dans la stack — transforme le texte brut OCR en JSON structuré |
| Fallback structuration | **Regex compilées** | Si Ollama KO |

### 7.2 Prompt LLM pour structuration OCR

Le prompt envoyé au LLM local pour structurer la sortie OCR doit être strict et cadré :

```
Tu es un extracteur de données médicales. Extrais UNIQUEMENT les champs suivants
du texte OCR ci-dessous. Réponds UNIQUEMENT en JSON valide, sans commentaire.
Si un champ est absent ou illisible, retourne null pour ce champ.

Champs à extraire :
- montant_facture : float (montant total facturé)
- devise : string ("XAF", "EUR", "FCFA" → normaliser en "XAF" si FCFA)
- date_soin : string (format YYYY-MM-DD)
- code_acte : string (code ASAC ou CCAM)
- nom_praticien : string
- presence_cachet : boolean (mentionne-t-il un cachet ou tampon ?)
- etablissement : string

Texte OCR :
{texte_ocr_brut}
```

### 7.3 Règle de confiance pour les features issues de l'OCR

Une feature calculée à partir d'un champ extrait par OCR hérite du score de confiance de ce champ. Si `Confiance_Montant < 0.6`, la feature `ratio_prix_mercuriale` calculée sur ce montant est marquée `feature_fiable = False` et ne doit pas déclencher de règle RCA à elle seule.

---

## PARTIE 8 — CONTRAINTES ÉTHIQUES ET RÉGLEMENTAIRES ABSOLUES

Ces contraintes ne peuvent jamais être contournées, même pour améliorer les métriques :

1. **Pas de rejet automatique** : MAKORA peut seulement émettre une alerte et calculer un score. La décision de rembourser ou de refuser appartient TOUJOURS à un humain (gestionnaire ou auditeur).

2. **Traçabilité obligatoire** : chaque alerte doit être accompagnée de l'explication SHAP des 3 features principales et du diagnostic RCA. Une alerte sans explication est invalide opérationnellement et académiquement.

3. **Pseudonymisation** : `ID_Assure`, `ID_Praticien`, `IBAN_Beneficiaire` sont toujours hashés SHA-256 + salt avant tout traitement. Jamais de données nominatives dans les logs.

4. **Souveraineté des données** : toute l'infrastructure tourne localement (FastAPI + Ollama + PostgreSQL local). Aucune donnée ne sort vers un service cloud externe.

5. **Droit à l'explication (RGPD Art. 22)** : tout assuré suspecté a le droit de demander une explication humaine de la décision. Le rapport SHAP + RCA généré par MAKORA est la base de cette explication.

---

## PARTIE 9 — RÉFÉRENCES BIBLIOGRAPHIQUES DOMAINE

| Référence | Contribution au projet |
|---|---|
| [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection. ICMLA. | Taux fraude santé, paramètre contamination, features fréquence |
| [Viaene2002] Viaene et al. (2002). Auto insurance fraud. Journal of Risk and Insurance. | Patterns fraude auto, features staged accidents |
| [Subudhi2017] Subudhi & Panigrahi (2017). Auto insurance fraud. JOEKSU. | Comparaison algorithmes sur données auto |
| [Liu2008] Liu et al. (2008). Isolation Forest. ICDM. | Algorithme principal de détection |
| [Lundberg2017] Lundberg & Lee (2017). SHAP. NeurIPS. | Explicabilité des alertes |
| [Blondel2008] Blondel et al. (2008). Louvain algorithm. | Détection communautés de fraude |
| [Chandola2009] Chandola et al. (2009). Anomaly detection survey. ACM CS. | Référence encyclopédique |
| Code CIMA — Édition consolidée 2024 | Réglementation assurance zone franc |
| ASAC — Nomenclature des actes médicaux CM | Codes actes Cameroun |

---

*INSURANCE_DOMAIN_CONTEXT.md — v1.0 — Mai 2026*
*Projet MAKORA — ATABONG EFON STEPHANE FRITZ*
*À fournir à l'IA en début de chaque session touchant aux features, règles RCA, seuils ou narration*
