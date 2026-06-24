# CAHIER DES CHARGES NON-TECHNIQUE

## Framework Générique et Extensible de Détection d'Anomalies par Intelligence Artificielle en Assurance

### Architecture, Implémentation et Validation sur les Marchés Hybrides Afrique-Europe

---

| Champ                    | Valeur                                                  |
| ------------------------ | ------------------------------------------------------- |
| **Auteur**               | ATABONG EFON STEPHANE FRITZ                             |
| **Entreprise d'accueil** | ITNS Nearshore Services                                 |
| **Encadreur académique** | À compléter                                             |
| **Année académique**     | 2025-2026                                               |
| **Version du document**  | v1.0 — Phase 0                                          |
| **Date de création**     | 17 avril 2026                                           |
| **Statut**               | Document vivant — à mettre à jour à chaque fin de phase |
| **Prochain révision**    | Fin Phase 1 (semaine 4)                                 |

---

## RÉSUMÉ EXÉCUTIF

Le secteur de l'assurance est confronté à une problématique universelle et croissante : la détection fiable des anomalies financières — qu'il s'agisse de fraudes intentionnelles, d'erreurs opérationnelles ou de biais systèmes — dans des volumes de données toujours plus importants. Les solutions existantes souffrent d'un défaut fondamental : elles sont conçues pour une seule branche d'assurance à la fois, rendant impossible leur réutilisation sans reconstruction complète.

Ce projet propose une réponse architecturale originale : un **framework générique et extensible**, reposant sur une architecture orientée plugins à schéma déclaratif, capable de s'instancier sur n'importe quelle branche d'assurance (Santé, Auto, Vie, Agricole) sans modifier son moteur central. L'objectif dépasse la simple détection : le système produit une **Root Cause Analysis (RCA)** en langage naturel français, identifiant l'origine exacte de chaque anomalie pour permettre à un gestionnaire non-technique de prendre une décision justifiée et traçable.

La valeur académique majeure réside dans le traitement simultané de deux réalités opérationnelles radicalement différentes au sein d'un pipeline unique : le marché européen (flux numériques structurés, norme NOEMIE, EUR) et le marché camerounais (flux documentaires physiques, OCR, Mercuriale CIMA, XAF). Il n'existe à ce jour pratiquement aucun travail académique traitant sérieusement la détection de fraude en assurance dans le contexte africain. Ce projet occupe cet espace vide.

**Périmètre de validation :** deux branches complètes (Santé + Auto) + conception documentée de deux branches supplémentaires (Vie + Agricole).

---

## TABLE DES MATIÈRES

1. [Contexte Général](#1-contexte-général)
2. [Vision et Objectifs du Projet](#2-vision-et-objectifs-du-projet)
3. [Parties Prenantes](#3-parties-prenantes)
4. [Description des Processus Métiers](#4-description-des-processus-métiers)
5. [Cartographie Exhaustive des Anomalies](#5-cartographie-exhaustive-des-anomalies)
6. [Besoins Fonctionnels](#6-besoins-fonctionnels)
7. [Besoins Non-Fonctionnels](#7-besoins-non-fonctionnels)
8. [Contraintes du Projet](#8-contraintes-du-projet)
9. [Livrables du Projet](#9-livrables-du-projet)
10. [Critères de Succès et Indicateurs de Validation](#10-critères-de-succès-et-indicateurs-de-validation)
11. [Planning Synthétique](#11-planning-synthétique)
12. [Glossaire Métier](#12-glossaire-métier)
13. [Annexes](#13-annexes)

---

## 1. CONTEXTE GÉNÉRAL

### 1.1 Présentation de l'entreprise d'accueil — ITNS Nearshore Services

ITNS Nearshore Services est une société de services informatiques positionnée sur le segment du nearshoring technologique à destination des marchés européens et africains. Son activité couvre le développement de solutions logicielles sur mesure, l'intégration de systèmes d'information et le conseil en transformation digitale pour des clients du secteur financier et assurantiel.

Dans le cadre de ce projet de mémoire, ITNS Nearshore Services constitue le terrain d'expérimentation et d'encadrement professionnel. La problématique de la détection d'anomalies en assurance représente un enjeu business direct pour l'entreprise, qui opère sur des marchés hybrides où coexistent des systèmes d'information matures (Europe) et des environnements fortement documentaires (Afrique subsaharienne).

### 1.2 Le problème métier : la fraude et les anomalies en assurance

#### 1.2.1 Ampleur du phénomène

L'assurance mondiale fait face à une recrudescence complexe d'anomalies financières. Selon l'**Association of Certified Fraud Examiners (ACFE)**, la fraude et les abus représentent environ **5% des revenus annuels** des organisations à l'échelle mondiale. Dans le secteur spécifique de la santé, ces pertes sont accentuées par la multiplicité des acteurs et la sophistication des méthodes de _billing fraud_ (surfacturation).

Au-delà de la fraude intentionnelle, les compagnies d'assurance subissent également des pertes significatives dues aux **erreurs opérationnelles** (erreurs de saisie, mauvaise codification des actes, oublis documentaires) et aux **biais systèmes** (anomalies issues d'un algorithme de tarification mal calibré, rejets OCR discriminants par zone géographique).

Ces trois types d'anomalies ont un point commun : sans outil approprié, elles sont **quasi-indétectables à l'échelle** dans des portefeuilles de plusieurs milliers de dossiers.

#### 1.2.2 Pourquoi la détection manuelle ne suffit plus

Le gestionnaire de sinistres humain est confronté à plusieurs limites structurelles :

- **Volume** : un portefeuille santé peut générer des dizaines de milliers de lignes de remboursement par mois.
- **Complexité** : les schémas de fraude en réseau (collusion prestataire-assuré) sont invisibles à l'œil nu sur un seul dossier.
- **Hétérogénéité** : un même dossier peut combiner un flux numérique structuré (API NOEMIE) et un document physique scanné, rendant la vérification manuelle longue et sujette aux erreurs.
- **Traçabilité** : une décision de rejet sans justification documentée expose l'assureur à un risque juridique.

L'intelligence artificielle, et plus spécifiquement la détection d'anomalies non-supervisée couplée à l'IA explicable, est la réponse technique à ces quatre limites.

#### 1.2.3 Le besoin spécifique : aller au-delà de la détection

Détecter une anomalie est insuffisant. Un gestionnaire qui reçoit une alerte "ce dossier est suspect" ne peut pas agir sans comprendre **pourquoi**. Le besoin réel est un **diagnostic** : quelle est la cause probable ? Est-ce une fraude intentionnelle, une erreur humaine ou un dysfonctionnement technique ? C'est précisément ce que la **Root Cause Analysis (RCA)** automatisée apporte.

### 1.3 La dualité des marchés : Europe vs Afrique

L'originalité centrale de ce projet est de traiter simultanément deux réalités opérationnelles dans le même pipeline.

#### 1.3.1 Le marché européen — flux numérique (France)

| Caractéristique           | Détail                                                                           |
| ------------------------- | -------------------------------------------------------------------------------- |
| **Mode d'échange**        | API REST / JSON structurés                                                       |
| **Norme de référence**    | NOEMIE (Norme Ouverte d'Échange entre la Maladie et les Intervenants Extérieurs) |
| **Codes actes médicaux**  | CCAM (Classification Commune des Actes Médicaux)                                 |
| **Référentiel tarifaire** | SNDS (Système National des Données de Santé), tarifs Sécurité Sociale            |
| **Devise**                | EUR (Euro)                                                                       |
| **Enrôlement**            | Dématérialisé, signature électronique eIDAS                                      |
| **Paiement sinistres**    | Virement bancaire standard XML ISO 20022                                         |

Le marché français se caractérise par une infrastructure numérique mature, des données structurées et des référentiels tarifaires publics accessibles. Le risque d'anomalie y est principalement lié à la sophistication des schémas de fraude (surfacturation, collusion réseaux) et aux erreurs de codification dans des nomenclatures complexes (CCAM : plus de 7 000 codes actes).

#### 1.3.2 Le marché camerounais — flux documentaire (Cameroun / Zone CIMA)

| Caractéristique           | Détail                                                                             |
| ------------------------- | ---------------------------------------------------------------------------------- |
| **Mode d'échange**        | Documents physiques (scans de factures, ordonnances manuscrites)                   |
| **Organisme régulateur**  | ASAC (Association des Sociétés d'Assurance du Cameroun) / BEAC                     |
| **Codes actes médicaux**  | Nomenclature ASAC                                                                  |
| **Référentiel tarifaire** | Mercuriale CIMA (Conférence Interafricaine des Marchés d'Assurance)                |
| **Devise**                | XAF (Franc CFA)                                                                    |
| **Enrôlement**            | Bulletin Individuel d'Adhésion (BIA) papier, photo d'identité physique obligatoire |
| **Paiement sinistres**    | Mobile Money (Orange/MTN), virement bancaire                                       |
| **Spécificité critique**  | Cachet humide obligatoire sur les factures et ordonnances                          |
| **Taux de change**        | EUR/XAF flottant — à intégrer dans le pipeline financier                           |

Le marché camerounais présente des défis radicalement différents : l'absence de dématérialisation impose un pipeline de traitement des documents physiques (OCR, extraction d'information, détection de falsification). La fraude documentaire — altération numérique de scans, fabrication de cachets — est un vecteur de risque spécifique à ce contexte.

#### 1.3.3 Le gap académique — originalité du projet

Une revue de la littérature scientifique sur la détection d'anomalies et la fraude en assurance révèle un constat frappant : **la quasi-totalité des travaux existants se concentre sur les marchés occidentaux matures** (US Medicare, NHS britannique, assurance automobile française). Le contexte africain — flux documentaires physiques, infrastructures limitées, micro-assurance, codes ASAC, Mercuriale CIMA — est pratiquement absent de la recherche académique publiée.

Ce projet occupe cet espace vide. La contribution académique est double : proposer une architecture générique prouvée ET documenter rigoureusement les spécificités techniques du traitement du flux documentaire en contexte africain.

### 1.4 Pourquoi l'assurance Santé comme terrain de validation principal

Le secteur de l'assurance santé a été sélectionné comme terrain de validation prioritaire pour une raison structurelle : il est le seul à exposer simultanément les **quatre catégories d'anomalies** de notre cartographie, ce qui en fait le banc d'essai le plus exigeant et le plus complet pour le framework.

| Catégorie d'anomalie                        | Exposition en Santé                                                                          |
| ------------------------------------------- | -------------------------------------------------------------------------------------------- |
| **Fraude Intentionnelle (Cat. I)**          | Forte : falsification de documents, réseaux prestataires complices, prêt de carte            |
| **Erreurs Opérationnelles (Cat. II)**       | Très forte : volume massif de micro-transactions, saisie manuelle, codes CCAM/ASAC complexes |
| **Biais Système et Modèle (Cat. III)**      | Forte : complexité des règles de tarification, plafonds de garanties, biais OCR géographique |
| **Risques Techniques et Données (Cat. IV)** | Forte : ingestion de données non structurées, synchronisation inter-systèmes, data drift     |

---

## 2. VISION ET OBJECTIFS DU PROJET

### 2.1 La vision — le framework comme prise électrique universelle

La métaphore fondatrice de ce projet est celle de la **prise électrique universelle**.

Imaginez une prise murale. Son mécanisme interne (le courant, la tension, la sécurité) est identique partout. Ce qu'on y branche peut être infiniment varié : une lampe, un ordinateur, un chargeur de téléphone. Tous ces appareils fonctionnent immédiatement, car ils respectent le même format de connexion — le contrat de la prise.

Le framework de ce projet fonctionne de la même manière :

- La **prise murale** = le moteur central d'IA (pipeline ML, Isolation Forest, SHAP, moteur RCA, LLM). Il ne change jamais.
- **Ce qu'on branche** = les modules métiers (Santé, Auto, Vie, Agricole). Chacun respecte un contrat formel appelé le **Plugin Contract**.
- Le **contrat de la prise** = un fichier YAML déclaratif qui décrit le schéma de données, les features à calculer et les règles RCA propres à chaque branche.

> **Ce que "framework" signifie ici :** il ne s'agit pas de React ou Django. Le framework est un ensemble de règles, contrats et briques réutilisables _conçu de toutes pièces_ dans le cadre de ce projet, dans lequel des modules métiers peuvent s'insérer sans modifier le moteur central.

### 2.2 L'objectif principal

**Concevoir, implémenter et valider un système d'intelligence artificielle unique capable de détecter les anomalies et de produire une Root Cause Analysis (RCA) dans n'importe quelle branche d'assurance, en instanciant dynamiquement le moteur central via un module plugin déclaratif.**

La RCA est le cœur de la valeur ajoutée : il ne suffit pas de signaler qu'un dossier est "suspect". Le système doit identifier l'origine de l'anomalie parmi trois grandes familles de causes — fraude intentionnelle, erreur humaine, dysfonctionnement technique — et produire une explication en français compréhensible par un gestionnaire non-technique.

### 2.3 Les objectifs secondaires

**OS-01 — Prouver la généricité par l'expérimentation**
Instancier le framework sur deux branches complètes (Santé et Auto) avec des données, des features et des règles RCA entièrement différentes, sans modifier une ligne du moteur central. Mesurer le coût en précision de la généricité par rapport à un modèle spécialisé.

**OS-02 — Garantir l'intelligibilité des diagnostics**
Chaque décision IA doit être accompagnée d'une explication en français naturel, produite par un LLM local (Mistral 7B), ou gemma4 e4b compréhensible par un gestionnaire qui ne connaît pas le machine learning.

**OS-03 — Traiter le flux hybride dans un pipeline unique**
Ingérer indifféremment des données structurées (CSV/JSON) et des documents non-structurés (scans PDF, images) dans le même pipeline de traitement, avec une normalisation vers un schéma universel.

**OS-04 — Assurer la traçabilité et l'auditabilité**
Toute décision IA est horodatée, justifiée par ses valeurs SHAP et sa règle RCA déclenchée. Un auditeur peut remonter à l'origine de n'importe quelle alerte à tout moment.

**OS-05 — Permettre l'extensibilité sans développeur**
Un expert métier doit pouvoir ajouter ou modifier des règles RCA en éditant un fichier YAML ou a travers l'interface graphique, sans toucher au code Python du moteur.

**OS-06 — Documenter l'originalité africaine**
Produire une documentation rigoureuse des spécificités techniques du flux documentaire camerounais (OCR, Mercuriale CIMA, XAF) pour combler le gap académique identifié.

### 2.4 Ce que le projet ne fait PAS — périmètre explicitement exclu

Il est essentiel de délimiter clairement ce que le prototype ne couvre pas, afin d'éviter tout malentendu lors de la soutenance.

| Exclusion                                      | Justification                                                                                                                                               |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Décision automatique de rejet d'un dossier** | Le système alerte et diagnostique. La décision finale appartient toujours au gestionnaire humain (_human-in-the-loop_ obligatoire).                         |
| **Déploiement cloud en production**            | Le prototype fonctionne en local. L'industrialisation est hors périmètre du mémoire.                                                                        |
| **Réentraînement automatique du modèle**       | La dérive des données est détectée et alertée. Le réentraînement est un acte manuel et délibéré. Choix assumé pour le prototype.                            |
| **Modules Vie et Agricole en production**      | Ces deux branches font l'objet d'une conception documentée complète (schéma YAML, anomalies, règles RCA), mais sans implémentation ni validation empirique. |
| **Données réelles de clients**                 | Toutes les données utilisées sont synthétiques ou issues de jeux de données publics (Kaggle, Synthea). Aucune donnée réelle d'assuré.                       |
| **Interface mobile**                           | Le dashboard est une application web locale (Next.js), 100% responsive sur mobile. Pas d'application mobile.                                                |

---

### 2.5 Stratégie d'évolution du framework — Gouvernance des ajouts futurs

Le CDC définit le périmètre du prototype V1. Il ne liste pas exhaustivement tous les
scénarios futurs possibles — c'est précisément pour cette raison que l'architecture
orientée plugins a été choisie. Toute évolution future est gouvernée par trois niveaux
d'impact clairement distincts.

#### Les trois niveaux d'évolution

| Niveau       | Type d'évolution                                              | Impact sur le moteur central                                                        | Exemples concrets                                                                                                        |
| ------------ | ------------------------------------------------------------- | ----------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| **Niveau 1** | Ajout ou modification d'une règle RCA dans un module existant | **Aucun** — modification du fichier YAML uniquement                                 | Nouveau seuil de surfacturation, nouvelle règle de conformité documentaire, ajustement mercuriale                        |
| **Niveau 2** | Ajout d'un nouveau module métier complet                      | **Aucun** — création d'un fichier YAML + une classe Python héritant de `BaseModule` | Module Agricole en production, Module Vie avec validation empirique, nouvelle branche Auto-Moto                          |
| **Niveau 3** | Ajout d'une capacité algorithmique structurellement nouvelle  | **Extension contrôlée et tracée** du moteur — nécessite un ADR                      | Détection de fraude en réseau (algorithmes de graphes), module NLP sur ordonnances manuscrites, modèle supervisé hybride |

#### Règles de gouvernance

**Pour les évolutions Niveau 1 et Niveau 2 :**
Elles sont entièrement couvertes par le Plugin Contract. Aucune décision architecturale
n'est requise. Un expert métier peut réaliser une évolution Niveau 1 sans développeur.

**Pour les évolutions Niveau 3 :**
Toute extension du moteur central doit faire l'objet d'un **ADR (Architecture Decision
Record)** documenté dans `ARCHITECTURE.md`. Un ADR répond à trois questions :

- Pourquoi cette capacité ne peut-elle pas être intégrée via un simple plugin Niveau 2 ?
- Comment garantit-on que l'extension ne casse aucun module existant ?
- Quels tests de non-régression valident l'extension ?

#### Cas spécifique : la détection de fraude en réseau

La fraude organisée en réseau (collusion prestataire-assuré, soins fantômes) nécessite
des algorithmes de détection de communautés dans un graphe de relations
(NetworkX, Graph Neural Networks). L'Isolation Forest ne peut pas détecter ce type
de pattern — il analyse chaque dossier individuellement, sans vision des liens entre
entités.

Ce scénario est documenté `[V2]` dans ce CDC. Cela signifie :

- Le prototype V1 ne l'implémente pas — choix assumé et documenté.
- L'architecture est conçue pour l'accueillir : le format de sortie JSON standardisé
  prévoit un champ `graph_analysis` optionnel qui n'impacte pas les modules existants.
- Dans le mémoire, ce scénario est traité comme une perspective d'évolution
  architecturalement justifiée, ce qui constitue une contribution académique en soi.

#### Synthèse

> Le framework ne prétend pas tout couvrir dès la V1. Il prétend être conçu pour
> que tout ajout futur soit prévisible, isolé et non-destructif. C'est cette propriété
> — et non l'exhaustivité — qui constitue la preuve de sa généricité.

## 3. PARTIES PRENANTES

### 3.1 Acteurs internes — utilisateurs du système

#### Le gestionnaire de sinistres (utilisateur principal)

**Profil :** Technicien ou cadre intermédiaire d'une compagnie d'assurance. Connaît le métier de l'assurance, ne maîtrise pas le machine learning.

**Besoins :**

- Consulter la liste des dossiers signalés comme anomalies
- Comprendre en langage simple pourquoi un dossier a été signalé
- Filtrer les alertes par niveau de criticité, branche, date
- Valider ou rejeter une alerte (feedback humain)
- Accéder à la pièce justificative d'un dossier directement depuis le dashboard

#### L'auditeur / responsable anti-fraude (utilisateur avancé)

**Profil :** Expert métier senior. Comprend les patterns de fraude, utilise le système pour approfondir son investigation.

**Besoins :**

- Accéder aux détails SHAP d'une anomalie (quelles features ont le plus contribué)
- Visualiser les tendances temporelles des anomalies (drift)
- Exporter les rapports d'audit avec justifications IA
- Consulter l'historique des décisions de validation/rejet

#### L'administrateur système

**Profil :** Développeur ou technicien IT. Gère l'infrastructure du prototype.

**Besoins :**

- Déployer et maintenir l'environnement local
- Charger les modèles ML (fichiers `.joblib`)
- Monitorer les alertes de data drift (PSI)
- Gérer les fichiers de mapping et de règles YAML

#### L'expert métier assurance (rédacteur de règles RCA)

**Profil :** Actuaire, juriste ou technicien senior. Connaît parfaitement le métier mais ne code pas.

**Besoins :**

- Pouvoir ajouter ou modifier les règles RCA d'une branche en éditant un fichier YAML lisible
- Ne pas avoir besoin d'un développeur pour ajuster les seuils de détection
- Disposer d'une documentation claire sur la syntaxe du fichier de règles

### 3.2 Acteurs externes — non-utilisateurs directs

#### L'assuré

Source des données (identité, contrat, dossiers de sinistres). N'interagit jamais directement avec le système. Ses données sont pseudonymisées.

#### Le prestataire de soins / garage / agriculteur

Acteur surveillé. Son comportement de facturation est analysé par le système. Il n'a aucun accès au système.

#### Le jury académique et l'encadreur

Lecteurs du mémoire et évaluateurs du prototype. Leurs attentes spécifiques sont intégrées dans les critères de succès (section 10) et les questions anticipées.

### 3.3 Matrice besoins par acteur

| Acteur                 | Besoin principal                  | Fonctionnalité associée        | Priorité |
| ---------------------- | --------------------------------- | ------------------------------ | -------- |
| Gestionnaire sinistres | Comprendre une alerte             | RCA en langage naturel (BF-05) | CRITIQUE |
| Gestionnaire sinistres | Valider/rejeter une alerte        | Human-in-the-loop (BF-07)      | CRITIQUE |
| Auditeur               | Analyser les features IA          | Visualisation SHAP (BF-04)     | HAUTE    |
| Auditeur               | Suivre les tendances              | Drift monitoring (BF-09)       | HAUTE    |
| Administrateur         | Ajouter une branche               | Plugin extensible (BF-08)      | CRITIQUE |
| Expert métier          | Modifier les règles RCA           | Fichier YAML éditable (BF-08)  | CRITIQUE |
| Jury académique        | Voir une anomalie de bout en bout | Démo complète + export rapport | CRITIQUE |

---

## 4. DESCRIPTION DES PROCESSUS MÉTIERS

### 4.1 Cycle de vie complet d'un sinistre Santé

Le système d'IA ne vit pas en dehors du processus métier. Il s'y insère à des points précis. Comprendre ce cycle est indispensable pour comprendre où et comment le framework intervient.

```
┌─────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 1 — SOUSCRIPTION & ENRÔLEMENT                                │
│  Création de l'identité numérique de l'assuré                       │
│  → France : dématérialisé, signature eIDAS, flux API                │
│  → Cameroun : BIA papier, photo d'identité, cachet humide           │
│  ⚡ Point d'injection IA : vérification cohérence identité + QS     │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 2 — RECOUVREMENT DES PRIMES                                  │
│  Prélèvement mensuel ou trimestriel de la cotisation                │
│  → France : prélèvement SEPA automatique                            │
│  → Cameroun : Mobile Money (Orange/MTN), virement                   │
│  ⚡ Point d'injection IA : détection anomalies prélèvements/impayés │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 3 — DÉCLARATION & RÉCEPTION DU SINISTRE                      │
│  L'assuré ou le prestataire soumet une demande de remboursement     │
│  → France : flux NOEMIE structuré (JSON/XML)                        │
│  → Cameroun : scan facture + ordonnance + cachet humide             │
│  ⚡ Point d'injection IA : routage flux (structuré vs documentaire) │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 4 — INSTRUCTION & LIQUIDATION                                │
│  Vérification des garanties, calcul du remboursement                │
│  → Confrontation acte facturé vs. tarif référence (SNDS/Mercuriale) │
│  → Vérification conformité pièces jointes (ordonnances, factures)   │
│  ⚡ Point d'injection IA : DÉTECTION PRINCIPALE (Isolation Forest)  │
│  ⚡ Point d'injection IA : RCA + narration Mistral 7B               │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 5 — VALIDATION HUMAINE (Human-in-the-loop)                   │
│  Le gestionnaire consulte le dashboard, lit le diagnostic RCA       │
│  → Confirme l'anomalie → dossier mis en investigation               │
│  → Rejette l'alerte (faux positif) → feedback loop ML              │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 6 — PAIEMENT & DÉNOUEMENT                                    │
│  Virement du remboursement vers le bénéficiaire                     │
│  → France : virement XML ISO 20022                                  │
│  → Cameroun : Mobile Money ou virement BEAC                         │
│  ⚡ Point d'injection IA : détection doublons de paiement           │
└────────────────────────────┬────────────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  ÉTAPE 7 — ARCHIVAGE & AUDIT                                        │
│  Conservation du journal de décisions IA avec justifications        │
│  ⚡ Point d'injection IA : monitoring drift, rapports audit         │
└─────────────────────────────────────────────────────────────────────┘
```

### 4.2 Le double flux d'ingestion — le Double Entonnoir

La spécificité technique centrale du framework est sa capacité à traiter deux types de données radicalement différents dans le même pipeline, via ce que l'on appelle le **Double Entonnoir**.

```
     FLUX STRUCTURÉ (France)              FLUX DOCUMENTAIRE (Cameroun)
     ─────────────────────                ────────────────────────────
     Fichier CSV / JSON                   Scan PDF / Image (JPG, PNG)
     Format NOEMIE / API                  Facture + Ordonnance physique
            │                                        │
            ▼                                        ▼
     Validation schéma                    Pipeline OCR
     (Pydantic)                           (Tesseract + OpenCV)
            │                                        │
            │                             Extraction informations :
            │                             - Montants, dates, codes
            │                             - Détection cachet humide
            │                             - Score confiance OCR
            │                             - Flag document altéré
            │                                        │
            └──────────────┬─────────────────────────┘
                           ▼
              COUCHE DE MAPPING & NORMALISATION
              - Harmonisation vers schéma universel
              - Normalisation des devises (EUR / XAF → valeur commune)
              - Encodage des variables catégorielles
              - Calcul des features dérivées (ratio_prix_mercuriale, etc.)
                           │
                           ▼
              DATASET UNIVERSEL (format Parquet)
              Prêt pour l'Isolation Forest
```

### 4.3 Processus métiers des autres branches (périmètre de conception)

#### Branche Auto

Le cycle sinistre automobile couvre la déclaration d'accident, l'expertise véhicule, le calcul des indemnités selon le barème légal et le paiement au réparateur ou à l'assuré. Les anomalies typiques incluent la surfacturation de réparations, la falsification de constats amiables et les collusions garagiste-assuré.

#### Branche Vie

Le cycle sinistre vie couvre la déclaration de décès ou d'invalidité, la vérification des bénéficiaires, le calcul du capital et le versement. Les anomalies typiques incluent les déclarations post-mortem tardives, les bénéficiaires fictifs et les fraudes à l'incapacité de travail.

#### Branche Agricole (spécificité Cameroun)

Le cycle sinistre agricole couvre la déclaration de sinistre climatique ou parasitaire, l'expertise terrain, le calcul de l'indemnité selon les rendements et le versement. Les anomalies typiques incluent la sur-déclaration de surfaces sinistrées et les dommages fabriqués. Cette branche est particulièrement sous-documentée dans la littérature académique africaine.

---

## 5. CARTOGRAPHIE EXHAUSTIVE DES ANOMALIES

Le framework est conçu pour détecter et diagnostiquer quatre catégories fondamentales d'anomalies. Cette cartographie est universelle : elle s'applique à toutes les branches, avec des manifestations concrètes différentes selon le contexte.

> **Principe de lecture de chaque anomalie :**
>
> - **Factualité** : ce qui se passe dans le monde réel
> - **Signal détectable** : ce que l'IA observe dans les données
> - **RCA** : ce que le système diagnostique comme cause racine
> - **Statut** : implémenté dans le prototype V1 ou prévu en évolution

---

### 5.1 Catégorie I — Fraude Intentionnelle

La fraude intentionnelle regroupe toutes les manipulations délibérées visant à obtenir un profit financier illégitime au détriment de la compagnie d'assurance.

#### 5.1.1 Fraude à la souscription

**Scénario I-A : Usurpation d'identité / Prêt de carte** _(Statut : Implémenté V1)_

| Champ                  | Description                                                                                                                                                                                                                           |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**         | Un individu utilise la carte d'assurance d'un ayant droit (conjoint, enfant) pour bénéficier de soins qu'il n'est pas en droit de percevoir.                                                                                          |
| **Signal détectable**  | Incohérence flagrante entre l'âge ou le sexe du bénéficiaire enregistré au contrat et la nature de l'acte médical facturé. Ex : consultation pédiatrique pour un assuré de 45 ans. Acte de maternité pour un assuré de sexe masculin. |
| **Données mobilisées** | `Sexe_Assure`, `Age_Assure`, `Code_Acte_CCAM/ASAC`, `Diagnostic_ICD10`, `Specialite_Praticien`                                                                                                                                        |
| **RCA**                | "Incohérence biologique majeure entre le sexe/âge de l'assuré et l'acte médical facturé — Suspicion de prêt de carte"                                                                                                                 |
| **Impact business**    | Remboursement illégitime + risque de résiliation du contrat                                                                                                                                                                           |

**Scénario I-B : Fraude post-mortem** _(Statut : Implémenté V1)_

| Champ                  | Description                                                                                                                            |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**         | Des soins sont facturés pour un assuré décédé, dont la date de décès est connue du système mais le contrat n'a pas encore été résilié. |
| **Signal détectable**  | Date de soin postérieure à la date de décès enregistrée dans le système de gestion.                                                    |
| **Données mobilisées** | `Date_Soin`, `Date_Deces_Assure`, `Statut_Contrat`                                                                                     |
| **RCA**                | "Acte médical facturé après le décès de l'assuré — Suspicion de fraude post-mortem"                                                    |

**Scénario I-C : Omission de pathologie préexistante** _(Statut : Évolution V2)_

| Champ                  | Description                                                                                                                                                    |
| ---------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**         | Un client omet volontairement une maladie chronique grave lors de la rédaction de son Questionnaire de Santé, pour éviter une majoration de prime ou un refus. |
| **Signal détectable**  | Déclenchement d'un sinistre lourd (ex : dialyse rénale, chimiothérapie) quelques jours seulement après la fin du délai de carence contractuel.                 |
| **Données mobilisées** | `Date_Debut_Contrat`, `Date_Soin`, `Delai_Carence`, `Code_Acte`, `Diagnostic_ICD10`, historique de consommation médicale longitudinal                          |
| **RCA**                | "Sinistre lourd survenu immédiatement après le délai de carence — Suspicion de fausse déclaration à la souscription"                                           |
| **Note**               | Ce scénario nécessite une interconnexion de bases de données longitudinales. Prévu en V2.                                                                      |

#### 5.1.2 Fraude au sinistre

**Scénario I-D : Doublon de facturation** _(Statut : Implémenté V1)_

| Champ                  | Description                                                                                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**         | Un assuré ou un prestataire soumet deux fois la même facture papier, à quelques jours d'intervalle, en espérant un double remboursement.                            |
| **Signal détectable**  | Deux lignes de sinistres présentent le même `ID_Assure`, la même `Date_Soin`, le même `Montant_Facture` et le même `Code_Acte`, mais des `Date_Saisie` différentes. |
| **Données mobilisées** | `ID_Assure`, `Date_Soin`, `Montant_Facture`, `Code_Acte`, `Date_Saisie`                                                                                             |
| **RCA**                | "Soumission multiple d'un même acte détectée — Suspicion de doublon de facturation intentionnel"                                                                    |

**Scénario I-E : Surfacturation prestataire** _(Statut : Implémenté V1)_

| Champ                  | Description                                                                                                                                                                   |
| ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**         | Un médecin, pharmacien ou clinique facture systématiquement ses actes à un tarif supérieur au prix de référence de la Mercuriale CIMA ou du SNDS.                             |
| **Signal détectable**  | `Ratio_Prix` = `Montant_Facture` / `Prix_Reference_Mercuriale` > seuil configurable (ex : > 1.3, soit +30%). Pattern systématique sur plusieurs dossiers du même prestataire. |
| **Données mobilisées** | `Montant_Facture`, `Prix_Reference_Mercuriale`, `ID_Praticien`, historique de facturation du praticien                                                                        |
| **RCA**                | "Montant facturé dépasse de X% le tarif mercuriale de référence pour cet acte — Suspicion de surfacturation prestataire"                                                      |

**Scénario I-F : Fraude en réseau / Collusion** _(Statut : Évolution V2)_

| Champ                  | Description                                                                                                                                                                                                     |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**         | Un médecin et un groupe d'assurés s'entendent pour facturer des actes fictifs (soins fantômes) ou gonfler systématiquement les montants en échange d'une commission.                                            |
| **Signal détectable**  | Fréquence d'actes statistiquement impossible pour un seul praticien sur une période donnée. Groupe d'assurés partageant un même employeur et concentrés chez un seul prestataire avec des ratios prix anormaux. |
| **Données mobilisées** | Graphe de relations prestataires-assurés, `ID_Praticien`, `ID_Assure`, `Employeur`, `Frequence_Actes`                                                                                                           |
| **RCA**                | "Concentration anormale de dossiers entre un groupe d'assurés et un praticien unique — Suspicion de fraude organisée en réseau"                                                                                 |
| **Note**               | Nécessite des algorithmes de détection de communautés (Graph Neural Networks, NetworkX). Prévu en V2.                                                                                                           |

#### 5.1.3 Fraude interne

**Scénario I-G : Forçage de validation sans pièce justificative** _(Statut : Implémenté V1)_

| Champ                  | Description                                                                                                                                                                     |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**         | Un gestionnaire interne valide et paie un dossier de remboursement sans que les pièces justificatives requises (ordonnance, facture acquittée) aient été fournies ou vérifiées. |
| **Signal détectable**  | `Statut_Validation` = "VALIDÉ" alors que `Presence_Cachet_Humide` = False ou `Ordonnance_Presente` = False. Validation effectuée en dehors des heures ouvrables.                |
| **Données mobilisées** | `Statut_Validation`, `Presence_Cachet_Humide`, `Ordonnance_Presente`, `Timestamp_Validation`, `ID_Gestionnaire`                                                                 |
| **RCA**                | "Dossier validé sans pièces justificatives conformes — Suspicion de validation interne frauduleuse"                                                                             |

---

### 5.2 Catégorie II — Erreurs Opérationnelles

Les erreurs opérationnelles sont des anomalies non-intentionnelles résultant d'une défaillance humaine ou procédurale dans le processus de traitement des dossiers.

#### 5.2.1 Erreurs de saisie et de données

**Scénario II-A : Inversion de chiffres (faute de frappe / transposition)** _(Statut : Implémenté V1)_

| Champ                  | Description                                                                                                                                                                                            |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Factualité**         | Un agent de saisie inverse accidentellement des chiffres lors de l'enregistrement d'un montant (ex : 1 250 XAF saisi comme 12 500 XAF).                                                                |
| **Signal détectable**  | Montant statistiquement aberrant par rapport à la distribution historique des montants pour cet acte médical et cette spécialité. Score d'anomalie Isolation Forest élevé sur la dimension financière. |
| **Données mobilisées** | `Montant_Facture`, distribution historique `Montant_Facture` par `Code_Acte` et `Specialite_Praticien`                                                                                                 |
| **RCA**                | "Montant statistiquement aberrant par rapport à l'historique de cet acte — Suspicion d'erreur de saisie (transposition de chiffres)"                                                                   |

**Scénario II-B : Oubli de conversion de devise** _(Statut : Implémenté V1)_

| Champ                  | Description                                                                                                                                                                                                            |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**         | Un dossier camerounais (XAF) est traité par un système configuré en EUR, sans conversion de devise appliquée. Le montant est enregistré en XAF dans un champ attendu en EUR, créant une aberration financière massive. |
| **Signal détectable**  | `Montant_Facture` en EUR paraît 655 fois supérieur au montant attendu (taux de change EUR/XAF ≈ 655). `Devise_Saisie` ≠ `Devise_Attendue`.                                                                             |
| **Données mobilisées** | `Montant_Facture`, `Devise_Saisie`, `Devise_Contrat`, `Taux_Change_EUR_XAF`                                                                                                                                            |
| **RCA**                | "Montant aberrant détecté — Absence probable de conversion de devise EUR/XAF (taux ≈ 655)"                                                                                                                             |

#### 5.2.2 Erreurs de traitement et de workflow

**Scénario II-C : Code acte incompatible avec la spécialité** _(Statut : Implémenté V1)_

| Champ                  | Description                                                                                                                                                     |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**         | Un agent enregistre un code d'acte médical qui ne correspond pas à la spécialité du praticien déclaré (ex : acte de neurochirurgie facturé par un généraliste). |
| **Signal détectable**  | `Code_Acte_CCAM` appartient à une nomenclature incompatible avec `Specialite_Praticien`. Règle métier déclenchée dans le moteur YAML.                           |
| **Données mobilisées** | `Code_Acte`, `Specialite_Praticien`, table de compatibilité actes/spécialités                                                                                   |
| **RCA**                | "Code acte CCAM/ASAC incompatible avec la spécialité déclarée du praticien — Suspicion d'erreur de codification"                                                |

**Scénario II-D : Doublon de dossier complet** _(Statut : Implémenté V1)_

| Champ                 | Description                                                                                                                                                      |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**        | Un dossier entier est soumis deux fois dans le système (double ingestion, bug API), créant un doublon avec un `ID_Sinistre` différent mais un contenu identique. |
| **Signal détectable** | Deux dossiers partagent le même `ID_Assure`, `Date_Soin`, `Code_Acte`, `Montant_Facture` et `ID_Praticien` avec des `ID_Sinistre` distincts.                     |
| **RCA**               | "Dossier dupliqué dans le système — Suspicion de double ingestion (erreur pipeline ou API)"                                                                      |

#### 5.2.3 Non-conformité documentaire

**Scénario II-E : Facture sans cachet humide (Cameroun)** _(Statut : Implémenté V1)_

| Champ                  | Description                                                                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**         | Une facture ou ordonnance scannée ne présente pas le cachet humide de l'établissement de soins, pourtant obligatoire selon la réglementation ASAC/CIMA. |
| **Signal détectable**  | `Presence_Cachet_Humide` = False détecté par le pipeline OCR (analyse des métadonnées de l'image et des zones de tampon).                               |
| **Données mobilisées** | `Presence_Cachet_Humide`, `Source_Flux` = "documentaire", `Pays_Flux` = "CM"                                                                            |
| **RCA**                | "Document non-conforme : absence de cachet humide obligatoire selon la réglementation CIMA — Document à renvoyer pour correction"                       |

---

### 5.3 Catégorie III — Biais Système et Modèle

Les biais système sont des anomalies générées par le système lui-même — qu'il s'agisse d'un algorithme de tarification mal calibré, d'un moteur OCR discriminant ou d'un modèle ML produisant des scores aberrants sur certaines sous-populations.

#### 5.3.1 Biais de tarification

**Scénario III-A : Dépassement systématique de la Mercuriale** _(Statut : Implémenté V1)_

| Champ                  | Description                                                                                                                                                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Factualité**         | Le référentiel tarifaire Mercuriale CIMA utilisé par le système n'a pas été mis à jour depuis plusieurs mois, tandis que les prix réels du marché ont évolué. Le système génère donc des alertes "surfacturation" erronées en masse. |
| **Signal détectable**  | Taux d'anomalies de type "surfacturation" anormalement élevé sur une période récente. PSI (Population Stability Index) élevé sur la feature `Ratio_Prix`. Pas de signal sur les autres features.                                     |
| **Données mobilisées** | `Ratio_Prix`, taux d'anomalies historiques, `PSI_Ratio_Prix`                                                                                                                                                                         |
| **RCA**                | "Taux d'alertes surfacturation anormalement élevé sur la période — Suspicion de dépassement systématique lié à un référentiel Mercuriale obsolète"                                                                                   |

#### 5.3.2 Biais de sélection

**Scénario III-B : Rejets OCR massifs sur zone rurale** _(Statut : Implémenté V1)_

| Champ                  | Description                                                                                                                                                                                                                                                                                                                    |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Factualité**         | Le moteur OCR produit des scores de confiance systématiquement bas sur les documents provenant de zones rurales du Cameroun, où la qualité des scans (mauvaise luminosité, papier froissé, imprimantes thermiques) est inférieure. Le système génère des alertes "document non-conforme" discriminantes par zone géographique. |
| **Signal détectable**  | Taux de `Score_Confiance_OCR_Glob` < seuil anormalement concentré sur une région spécifique (`Region_Etablissement`). Distribution bimodale du score OCR par région.                                                                                                                                                           |
| **Données mobilisées** | `Score_Confiance_OCR_Glob`, `Region_Etablissement`, `Source_Flux`                                                                                                                                                                                                                                                              |
| **RCA**                | "Taux de rejet OCR anormalement concentré sur la région X — Suspicion de biais de sélection géographique dans le moteur de reconnaissance documentaire"                                                                                                                                                                        |

#### 5.3.3 Biais de scoring

**Scénario III-C : Concentration des scores sur un prestataire** _(Statut : Implémenté V1)_

| Champ                 | Description                                                                                                                                                                                                                                            |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Factualité**        | Le modèle Isolation Forest attribue des scores d'anomalie anormalement élevés à tous les dossiers d'un même établissement de soins, indépendamment du contenu réel, en raison d'une surreprésentation de cet établissement dans le jeu d'entraînement. |
| **Signal détectable** | Distribution des scores d'anomalie (`Anomaly_Score`) fortement concentrée sur un `ID_Etablissement` ou `ID_Praticien` spécifique, sans corrélation avec les features métier.                                                                           |
| **RCA**               | "Score d'anomalie anormalement concentré sur l'établissement X — Suspicion de biais de scoring lié à la distribution du jeu d'entraînement"                                                                                                            |

---

### 5.4 Catégorie IV — Risques Techniques et Données

Les risques techniques sont des anomalies issues de défaillances dans le pipeline de traitement des données lui-même.

#### 5.4.1 Risques pipeline et intégration

**Scénario IV-A : Fichier entrant corrompu** _(Statut : Implémenté V1)_

| Champ                 | Description                                                                                                                                               |
| --------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**        | Un fichier CSV ou JSON envoyé via l'API contient des doublons massifs, des champs manquants obligatoires ou une structure non conforme au schéma attendu. |
| **Signal détectable** | Validation Pydantic échoue. Hash du fichier entrant ≠ hash de référence. Taux de valeurs manquantes sur colonnes critiques > seuil.                       |
| **RCA**               | "Fichier entrant non-conforme au schéma attendu — Erreur pipeline d'intégration. Fichier retourné à l'expéditeur pour correction."                        |

**Scénario IV-B : Doublons API d'ingestion massive** _(Statut : Implémenté V1)_

| Champ                 | Description                                                                                                                                                                    |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Factualité**        | Un bug dans le système source provoque l'envoi du même batch de dossiers plusieurs fois en quelques secondes via l'API d'ingestion.                                            |
| **Signal détectable** | Augmentation soudaine et anormale du volume de dossiers entrants sur une fenêtre temporelle de quelques minutes. Hash de batch identique pour plusieurs requêtes consécutives. |
| **RCA**               | "Volume d'ingestion anormalement élevé sur une fenêtre de 5 minutes — Suspicion de doublons API. Dé-duplication appliquée."                                                    |

#### 5.4.2 Dérive et qualité des données

**Scénario IV-C : Data Drift — dérive statistique des données** _(Statut : Implémenté V1)_

| Champ                  | Description                                                                                                                                                                                                                              |
| ---------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**         | La distribution des données en production dérive progressivement par rapport à la distribution du jeu d'entraînement (saisonnalité, nouveau type de prestataire, changement réglementaire). Le modèle ML perd en pertinence sans alerte. |
| **Signal détectable**  | PSI (Population Stability Index) > 0.2 sur une ou plusieurs features clés sur une fenêtre glissante de 30 jours.                                                                                                                         |
| **Données mobilisées** | Distribution des features sur fenêtre courante vs. distribution de référence d'entraînement                                                                                                                                              |
| **RCA**                | "Dérive statistique détectée sur la feature X (PSI = Y) — Réentraînement du modèle recommandé. Alertes courantes à considérer avec prudence."                                                                                            |

**Scénario IV-D : Schema Drift — format de date invalide** _(Statut : Implémenté V1)_

| Champ                 | Description                                                                                                                                                                                    |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Factualité**        | Un changement de système source modifie silencieusement le format des dates (ex : passage de DD/MM/YYYY à YYYY-MM-DD), rendant les dates non-parsables et corrompant les features temporelles. |
| **Signal détectable** | Échec de parsing sur la colonne `Date_Soin` pour N% des nouveaux dossiers. Taux d'erreur de validation Pydantic en hausse sur les champs date.                                                 |
| **RCA**               | "Erreur de format de date détectée sur X% des dossiers entrants — Schema drift probable sur le système source. Migration de format requise."                                                   |

---

### 5.5 Tableau récapitulatif des 23 scénarios

| #      | Scénario                              | Catégorie             | Statut V1     | Branch principale |
| ------ | ------------------------------------- | --------------------- | ------------- | ----------------- |
| I-A    | Usurpation d'identité / Prêt de carte | Fraude                | ✅ Implémenté | Santé             |
| I-B    | Fraude post-mortem                    | Fraude                | ✅ Implémenté | Santé             |
| I-C    | Omission pathologie préexistante      | Fraude                | 🔄 V2         | Santé             |
| I-D    | Doublon de facturation                | Fraude                | ✅ Implémenté | Santé, Auto       |
| I-E    | Surfacturation prestataire            | Fraude                | ✅ Implémenté | Santé, Auto       |
| I-F    | Fraude en réseau / Collusion          | Fraude                | 🔄 V2         | Santé             |
| I-G    | Forçage validation sans justificatif  | Fraude interne        | ✅ Implémenté | Santé             |
| II-A   | Inversion de chiffres (transposition) | Erreur opérationnelle | ✅ Implémenté | Toutes            |
| II-B   | Oubli conversion devise EUR/XAF       | Erreur opérationnelle | ✅ Implémenté | Santé (Cameroun)  |
| II-C   | Code acte incompatible spécialité     | Erreur opérationnelle | ✅ Implémenté | Santé             |
| II-D   | Doublon de dossier complet            | Erreur opérationnelle | ✅ Implémenté | Toutes            |
| II-E   | Facture sans cachet humide            | Erreur documentaire   | ✅ Implémenté | Santé (Cameroun)  |
| III-A  | Dépassement systématique Mercuriale   | Biais système         | ✅ Implémenté | Santé (Cameroun)  |
| III-B  | Rejets OCR massifs zone rurale        | Biais sélection       | ✅ Implémenté | Santé (Cameroun)  |
| III-C  | Concentration scores sur prestataire  | Biais scoring         | ✅ Implémenté | Santé, Auto       |
| IV-A   | Fichier entrant corrompu              | Risque technique      | ✅ Implémenté | Toutes            |
| IV-B   | Doublons API ingestion massive        | Risque technique      | ✅ Implémenté | Toutes            |
| IV-C   | Data drift (PSI)                      | Risque technique      | ✅ Implémenté | Toutes            |
| IV-D   | Schema drift (format date)            | Risque technique      | ✅ Implémenté | Toutes            |
| Auto-1 | Surfacturation réparation véhicule    | Fraude Auto           | ✅ Phase 2    | Auto              |
| Auto-2 | Falsification constat amiable         | Fraude Auto           | ✅ Phase 2    | Auto              |
| Auto-3 | Collusion garagiste-assuré            | Fraude Auto           | 🔄 V2         | Auto              |
| Auto-4 | Erreur barème légal indemnités        | Erreur Auto           | ✅ Phase 2    | Auto              |

---

## 6. BESOINS FONCTIONNELS

Les besoins fonctionnels décrivent ce que le système **doit faire**. Chaque besoin est identifié par un code unique, un niveau de priorité (CRITIQUE / HAUTE / MOYENNE) et son statut dans le planning.

### BF-01 — Ingestion multi-flux

| Attribut                  | Valeur                                                                                                                                                                                                                                                                         |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Priorité**              | CRITIQUE                                                                                                                                                                                                                                                                       |
| **Description**           | Le système doit accepter des données en entrée sous deux formes radicalement différentes : des fichiers structurés (CSV, JSON) représentant le flux numérique européen, et des fichiers non-structurés (PDF scanné, image JPG/PNG) représentant le flux documentaire africain. |
| **Entrées acceptées**     | `.csv`, `.json` (flux structuré) ; `.pdf`, `.jpg`, `.png` (flux documentaire)                                                                                                                                                                                                  |
| **Comportement attendu**  | Le système détecte automatiquement le type de flux entrant et le route vers le pipeline approprié (validation schéma vs. OCR).                                                                                                                                                 |
| **Critère d'acceptation** | Un fichier CSV France et un scan PDF Cameroun, portant sur le même type de sinistre, produisent en sortie deux lignes dans le dataset universel avec un schéma identique.                                                                                                      |

### BF-02 — Normalisation et harmonisation universelle

| Attribut                     | Valeur                                                                                                                                                                                                                 |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Priorité**                 | CRITIQUE                                                                                                                                                                                                               |
| **Description**              | Toutes les données ingérées, quelle que soit leur source, doivent être transformées vers un schéma universel unique (le Dataset Universel), permettant au moteur ML de les traiter de manière identique.               |
| **Transformations requises** | Mapping de colonnes (via fichier YAML par source) ; normalisation des devises (XAF → EUR via taux de change) ; encodage des variables catégorielles ; calcul des features dérivées (ratio prix, flags temporels, etc.) |
| **Critère d'acceptation**    | Le moteur Isolation Forest reçoit exactement le même format de données pour un dossier Santé France et un dossier Santé Cameroun.                                                                                      |

### BF-03 — Détection d'anomalies par score

| Attribut                  | Valeur                                                                                                                                                                 |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Priorité**              | CRITIQUE                                                                                                                                                               |
| **Description**           | Pour chaque dossier traité, le système doit calculer un score d'anomalie normalisé entre 0 et 1, et un marqueur booléen (`is_anomaly`) basé sur un seuil configurable. |
| **Algorithme**            | Isolation Forest (Liu et al., 2008) — algorithme non-supervisé qui isole les anomalies par nombre minimum de "coupes" dans l'espace des features.                      |
| **Seuil**                 | Configurable par module dans le fichier YAML du Plugin Contract. Valeur par défaut : contamination = 0.08 (8% de dossiers marqués anomalies).                          |
| **Sortie**                | `anomaly_score` : float [0.0, 1.0] ; `is_anomaly` : boolean                                                                                                            |
| **Critère d'acceptation** | Sur le dataset Santé (140 225 lignes avec labels injectés), le modèle atteint un F1-score ≥ seuil défini et documenté.                                                 |

### BF-04 — Explicabilité par SHAP

| Attribut                  | Valeur                                                                                                                                                                                                                                  |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Priorité**              | CRITIQUE                                                                                                                                                                                                                                |
| **Description**           | Pour chaque dossier marqué comme anomalie, le système doit calculer les valeurs SHAP (SHapley Additive exPlanations) de chaque feature, permettant d'identifier quantitativement les variables qui ont le plus contribué à la décision. |
| **Algorithme**            | SHAP TreeExplainer sur Isolation Forest (Lundberg & Lee, 2017).                                                                                                                                                                         |
| **Sortie**                | Vecteur de valeurs SHAP par feature ; Top 3 features contributeurs avec valeur et direction (positif/négatif)                                                                                                                           |
| **Critère d'acceptation** | Les top 3 features SHAP d'un dossier de surfacturation incluent systématiquement `ratio_prix_mercuriale` dans le top 3.                                                                                                                 |

### BF-05 — Root Cause Analysis structurée

| Attribut                  | Valeur                                                                                                                                                                                                                                                         |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Priorité**              | CRITIQUE                                                                                                                                                                                                                                                       |
| **Description**           | Pour chaque anomalie détectée, le moteur RCA doit croiser les valeurs SHAP avec les règles métier définies dans le fichier YAML du module pour produire un diagnostic structuré : catégorie d'anomalie, sous-catégorie, règle déclenchée, niveau de confiance. |
| **Mécanisme**             | Le moteur RCA est un système à base de règles déclaratives (fichier YAML). Chaque règle définit : condition sur features SHAP + seuils → catégorie RCA + sous-catégorie.                                                                                       |
| **Sortie structurée**     | `rca_category` (ex: "Fraude Intentionnelle") ; `rca_subcategory` (ex: "Surfacturation Prestataire") ; `rca_rule_triggered` ; `rca_confidence` : float [0.0, 1.0]                                                                                               |
| **Critère d'acceptation** | 90% des dossiers injectés avec une fraude de surfacturation reçoivent un diagnostic RCA de catégorie "Fraude Intentionnelle / Surfacturation".                                                                                                                 |

### BF-06 — Narration en langage naturel

| Attribut                  | Valeur                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Priorité**              | HAUTE                                                                                                                                                                                                                                                                                                                                                                                      |
| **Description**           | Pour chaque anomalie, le système doit produire une explication en français naturel, compréhensible par un gestionnaire non-technique, décrivant en 2 à 4 phrases ce qui a été détecté, pourquoi et ce qui est recommandé.                                                                                                                                                                  |
| **Mécanisme**             | Mistral 7B (LLM open source) fonctionnant en local. Reçoit en entrée un prompt structuré contenant le contexte du dossier, le score d'anomalie, les top 3 features SHAP et le diagnostic RCA. Produit une explication en sortie.                                                                                                                                                           |
| **Contrainte**            | L'explication ne doit jamais affirmer une fraude comme certaine — toujours utiliser le conditionnel ("suspicion de", "pourrait indiquer").                                                                                                                                                                                                                                                 |
| **Exemple de sortie**     | "Le montant facturé pour cet acte de consultation spécialisée (12 500 XAF) dépasse de 73% le tarif de référence de la Mercuriale CIMA pour cette spécialité (7 220 XAF). Ce dépassement systématique, observé sur 8 des 10 derniers dossiers de ce praticien, pourrait indiquer une surfacturation intentionnelle. Un contrôle approfondi de l'activité de ce prestataire est recommandé." |
| **Critère d'acceptation** | Score ≥ 3/5 sur la grille d'évaluation LLM (cohérence factuelle, utilisation du conditionnel, compréhensibilité, longueur appropriée, recommandation actionnable).                                                                                                                                                                                                                         |

### BF-07 — Dashboard de visualisation

| Attribut                      | Valeur                                                                                                                                                                                                                                   |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Priorité**                  | HAUTE                                                                                                                                                                                                                                    |
| **Description**               | Interface web permettant à un gestionnaire de consulter, filtrer et explorer les alertes et leurs diagnostics.                                                                                                                           |
| **Fonctionnalités minimales** | Liste des anomalies avec score et catégorie RCA ; filtre par branche, catégorie, date, score ; vue détaillée d'un dossier (SHAP, RCA, narration) ; accès à la pièce justificative (document scanné) ; indicateurs de drift en temps réel |
| **Stack technique**           | Next.js (frontend) ; FastAPI (backend API)                                                                                                                                                                                               |
| **Critère d'acceptation**     | Un gestionnaire non-technique peut, en moins de 3 clics depuis la liste des alertes, accéder à l'explication complète d'une anomalie et valider ou rejeter l'alerte.                                                                     |

### BF-08 — Human-in-the-loop

| Attribut                  | Valeur                                                                                                                                                                                                                                              |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Priorité**              | CRITIQUE                                                                                                                                                                                                                                            |
| **Description**           | Le gestionnaire ou l'auditeur doit pouvoir statuer sur chaque anomalie : confirmer (la mettre en investigation formelle) ou rejeter (la qualifier de faux positif). Ce feedback est enregistré et peut alimenter un futur réentraînement supervisé. |
| **Actions disponibles**   | "Confirmer anomalie" → statut = INVESTIGATION ; "Rejeter (Faux Positif)" → statut = REJETÉ + motif libre ; "Escalader à l'auditeur"                                                                                                                 |
| **Traçabilité**           | Toute action est horodatée et associée à l'ID du gestionnaire.                                                                                                                                                                                      |
| **Critère d'acceptation** | Toutes les actions de validation/rejet sont persistées avec horodatage, ID gestionnaire et motif. Un rapport d'audit peut être exporté.                                                                                                             |

### BF-09 — Extensibilité par plugin (Plugin Contract)

| Attribut                  | Valeur                                                                                                                                                                                                                                                                |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Priorité**              | CRITIQUE                                                                                                                                                                                                                                                              |
| **Description**           | Ajouter une nouvelle branche d'assurance au framework doit nécessiter uniquement la création d'un fichier YAML de configuration (schéma, features, règles RCA) et d'une classe Python héritant de l'interface BaseModule. Le moteur central ne doit pas être modifié. |
| **Règle d'or**            | "Zéro modification du moteur central pour ajouter un nouveau module."                                                                                                                                                                                                 |
| **Critère d'acceptation** | L'ajout du module Auto, après le module Santé, n'a nécessité aucune modification des fichiers du moteur ML (pipeline.py, rca_engine.py, llm_narrator.py).                                                                                                             |

### BF-10 — Drift monitoring

| Attribut                  | Valeur                                                                                                                                                                                                   |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Priorité**              | HAUTE                                                                                                                                                                                                    |
| **Description**           | Le système doit surveiller en continu la dérive statistique des données entrantes par rapport à la distribution de référence du jeu d'entraînement, et alerter l'administrateur si un seuil est dépassé. |
| **Métrique**              | PSI (Population Stability Index) : PSI < 0.1 = stable ; 0.1 ≤ PSI < 0.2 = alerte légère ; PSI ≥ 0.2 = alerte critique, réentraînement recommandé.                                                        |
| **Critère d'acceptation** | Si le PSI de la feature `ratio_prix` dépasse 0.2 sur une fenêtre de 30 jours, une alerte est visible dans le dashboard dans les 24h.                                                                     |

### BF-11 — Traçabilité et auditabilité

| Attribut                  | Valeur                                                                                                                                                                                                     |
| ------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Priorité**              | CRITIQUE                                                                                                                                                                                                   |
| **Description**           | Chaque décision produite par le système IA doit être conservée dans un journal d'audit immuable : score d'anomalie, valeurs SHAP, règle RCA déclenchée, narration LLM, action du gestionnaire, horodatage. |
| **Format**                | JSON structuré persisté en base de données locale.                                                                                                                                                         |
| **Critère d'acceptation** | Pour n'importe quel dossier traité dans les 90 derniers jours, un auditeur peut reconstituer intégralement la chaîne de décision IA en moins de 2 minutes.                                                 |

---

## 7. BESOINS NON-FONCTIONNELS

Les besoins non-fonctionnels décrivent comment le système doit fonctionner — les contraintes de qualité qui s'appliquent à l'ensemble du système.

### 7.1 Performance

| Besoin                                                   | Cible                           |
| -------------------------------------------------------- | ------------------------------- |
| Temps de traitement d'un dossier tabulaire (hors OCR)    | < 3 secondes                    |
| Temps de traitement d'un dossier documentaire (avec OCR) | < 30 secondes                   |
| Volume supporté en batch                                 | ≥ 10 000 dossiers par exécution |
| Temps de génération narration LLM (Mistral 7B local)     | < 10 secondes par dossier       |
| Latence API endpoint `/analyze`                          | < 5 secondes (p95)              |

> **Note :** Ces cibles sont définies pour le prototype local. Elles ne constituent pas des SLA de production.

### 7.2 Intelligibilité (Explainability-First)

Toute décision du système IA doit être accompagnée d'une explication humainement compréhensible. Il n'existe pas de "boîte noire" acceptable dans ce framework. Cette exigence est non négociable : elle constitue l'un des arguments académiques centraux du projet.

Concrètement, pour chaque dossier marqué anomalie, le système fournit systématiquement :

1. Le score d'anomalie (0-1)
2. Les top 3 features ayant le plus contribué à la décision (valeurs SHAP)
3. Le diagnostic RCA structuré (catégorie + sous-catégorie + règle déclenchée)
4. La narration en français naturel (Mistral 7B)

### 7.3 Portabilité et reproductibilité

Le prototype doit fonctionner entièrement en local, sans dépendance à un service cloud payant. L'environnement d'exécution doit être entièrement reproductible :

- **Gestionnaire de dépendances :** `requirements.txt` versionné + `pyproject.toml`
- **Conteneurisation :** `docker-compose.yml` permettant de lancer l'ensemble de la stack en une commande
- **Modèles ML :** fichiers `.joblib` versionnés et checksum SHA-256 documenté
- **LLM :** Mistral 7B via Ollama, modèle téléchargeable via une commande documentée

### 7.4 Maintenabilité

La maintenabilité du framework est un critère académique central — elle prouve la généricité.

- **Règle d'or :** ajouter un module = modifier uniquement 1 fichier YAML + 1 classe Python (< 50 lignes)
- **Règles RCA :** entièrement modifiables en YAML sans toucher au code Python
- **Seuils de détection :** configurables par module dans le fichier YAML (contamination, seuils PSI, etc.)
- **Documentation :** chaque module est accompagné d'un README décrivant son schéma, ses features et ses règles RCA

### 7.5 Sécurité et confidentialité des données

Même dans un contexte prototype, les bonnes pratiques de protection des données doivent être respectées :

- **Pseudonymisation :** toutes les données patients sont pseudonymisées. Les `ID_Assure` et `ID_Praticien` sont des identifiants hachés (UUID), jamais des noms réels.
- **Données en clair :** aucune donnée réelle de client ou de patient ne doit apparaître dans le dépôt Git.
- **Fichier `.gitignore` :** les fichiers CSV contenant des données sensibles sont exclus du versioning.
- **Chiffrement :** non requis pour le prototype local.

### 7.6 Robustesse et gestion des erreurs

Le système ne doit pas planter face à des données imparfaites — une réalité inévitable en production.

| Situation                               | Comportement attendu                                                                               |
| --------------------------------------- | -------------------------------------------------------------------------------------------------- |
| **Valeurs manquantes** sur une feature  | Imputation par la médiane (numérique) ou mode (catégorielle) avec flag `imputed = True`            |
| **Format de fichier invalide**          | Rejet propre avec message d'erreur structuré JSON + log d'audit                                    |
| **Score OCR trop bas** (< 0.3)          | Document renvoyé pour re-scan + diagnostic RCA "qualité insuffisante"                              |
| **Modèle ML non chargé**                | Mode dégradé heuristique : règles métier simples (seuils fixes) sans ML                            |
| **LLM Mistral non disponible**          | Narration de secours template-based (phrases pré-construites à partir du diagnostic RCA structuré) |
| **Taux de change EUR/XAF indisponible** | Utilisation du dernier taux connu + alerte dans le log                                             |

### 7.7 Testabilité

- **Tests unitaires :** chaque module Python dispose de tests unitaires (`pytest`) couvrant les cas nominaux et les cas limites.
- **Tests d'intégration :** un test E2E valide le pipeline complet de bout en bout (ingestion → détection → RCA → narration → sortie JSON) pour les modules Santé et Auto.
- **Jeu de test de référence :** un dataset de 1 000 dossiers avec labels connus est conservé comme jeu de test fixe pour mesurer la régression entre versions.

---

## 8. CONTRAINTES DU PROJET

### 8.1 Contraintes académiques

Ces contraintes sont imposées par le cadre du mémoire d'ingénieur de conception. Elles ne sont pas négociables.

| Contrainte                   | Description                                                                                                                                                                                      |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Généricité prouvée**       | La démonstration de généricité doit être expérimentale et chiffrée, pas seulement affirmée dans le texte. Deux modules complets (Santé + Auto) avec features et règles radicalement différentes. |
| **Résultats mesurables**     | Toutes les performances doivent être chiffrées : F1-score, précision, rappel, taux de faux positifs, PSI drift, delta généricité/précision.                                                      |
| **Trade-off documenté**      | Le coût en précision de la généricité (modèle générique vs. modèle spécialisé) doit être mesuré et documenté honnêtement.                                                                        |
| **LLM évalué**               | Les narrations Mistral 7B doivent être évaluées sur une grille rigoureuse documentée (cohérence factuelle, ton conditionnel, actionabilité).                                                     |
| **Questions jury préparées** | Les 7 questions anticipées (section 10.3) doivent trouver une réponse concrète et chiffrée dans les livrables.                                                                                   |

### 8.2 Contraintes de données

| Contrainte                 | Description                                                                                                                                                                                                                         |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Pas de données réelles** | Aucune donnée réelle d'assuré n'est disponible. Le prototype repose sur des datasets synthétiques et publics.                                                                                                                       |
| **Dataset Santé existant** | 140 225 lignes disponibles (Synthea + SNDS/Medicare + ASAC/BEAC + Kaggle Healthcare Fraud). À réutiliser tel quel avec adaptations.                                                                                                 |
| **Dataset Auto**           | À constituer en Phase 2 (French Motor Claims Kaggle + génération synthétique Cameroun).                                                                                                                                             |
| **Données camerounaises**  | Entièrement synthétiques (Mercuriale CIMA simulée, codes ASAC, taux de change EUR/XAF). Le modèle entraîné sur ces données ne se comportera pas nécessairement comme sur de vraies données ASAC/Activa — à documenter comme limite. |
| **Taux de change EUR/XAF** | Flottant (~655). Doit être configurable dans le pipeline, pas codé en dur.                                                                                                                                                          |

### 8.3 Contraintes techniques

| Contrainte                        | Description                                                                                                               |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| **Langage principal**             | Python 3.11+                                                                                                              |
| **Framework backend**             | FastAPI                                                                                                                   |
| **Framework frontend**            | Next.js                                                                                                                   |
| **Algorithme de détection**       | Isolation Forest (scikit-learn) — non-supervisé, choix assumé et justifiable (pas de labels fiables en production réelle) |
| **Explicabilité**                 | SHAP (TreeExplainer)                                                                                                      |
| **LLM**                           | Mistral 7B en local (Ollama) — pas de service cloud payant (OpenAI, Anthropic API)                                        |
| **Format de persistance dataset** | Apache Parquet (performances sur grands datasets)                                                                         |
| **Validation de schéma**          | Pydantic v2                                                                                                               |
| **Gestion des règles**            | Fichiers YAML (PyYAML)                                                                                                    |
| **Tests**                         | pytest                                                                                                                    |
| **Versioning**                    | Git + GitHub                                                                                                              |
| **Pas de service cloud**          | Le prototype doit fonctionner intégralement en local, sur un poste de travail standard.                                   |

### 8.4 Contraintes temporelles

| Phase                      | Semaines | Contenu                                                       | Durée effective (×5) |
| -------------------------- | -------- | ------------------------------------------------------------- | -------------------- |
| **Phase 0 — Fondations**   | S1–S2    | CDC, contexte IA, architecture, cahier technique              | 2 jours effectifs    |
| **Phase 1 — Core + Santé** | S2–S4    | Stack, pipeline ML, module Santé complet, métriques           | 3 jours effectifs    |
| **Phase 2 — Auto + LLM**   | S4–S7    | Dataset Auto, module Auto, Mistral 7B, RCA narratif           | 4 jours effectifs    |
| **Phase 3 — UI + Drift**   | S7–S9    | Dashboard Next.js, drift monitoring, conceptions Vie/Agricole | 3 jours effectifs    |
| **Phase 4 — Validation**   | S9–S11   | Tests E2E, analyse comparative, buffer                        | 3 jours effectifs    |
| **Juillet**                | —        | Rédaction mémoire (encadreur académique)                      | —                    |

> **Facteur ×5 :** ce que l'étudiant moyen fait en 1 semaine classique, ce projet le réalise en 1 jour effectif grâce à l'utilisation intensive de Claude + Cursor comme outils de génération et validation de code.

---

## 9. LIVRABLES DU PROJET

| #       | Livrable                                       | Phase   | Format                | Destinataire       |
| ------- | ---------------------------------------------- | ------- | --------------------- | ------------------ |
| **L1**  | Cahier des charges non-technique (ce document) | 0       | Markdown → PDF        | Jury, encadreur    |
| **L2**  | Architecture & Plugin Contract                 | 0       | Markdown + diagrammes | Jury, développeurs |
| **L3**  | Cahier technique d'analyse & conception        | 0       | Markdown → PDF        | Jury, encadreur    |
| **L4**  | Fichiers contexte IA (`/context/`)             | 0       | Markdown              | Usage interne      |
| **L5**  | Dataset Santé finalisé + pipeline ETL          | 1       | Parquet + code Python | Usage interne      |
| **L6**  | Module Santé complet + métriques               | 1       | Code + rapport PDF    | Jury               |
| **L7**  | Dataset Auto + pipeline ETL                    | 2       | Parquet + code Python | Usage interne      |
| **L8**  | Module Auto complet + métriques                | 2       | Code + rapport PDF    | Jury               |
| **L9**  | Intégration Mistral 7B + grille évaluation RCA | 2       | Code + rapport PDF    | Jury               |
| **L10** | Dashboard Next.js fonctionnel                  | 3       | Application web       | Jury (démo)        |
| **L11** | Drift monitoring opérationnel                  | 3       | Code + documentation  | Jury               |
| **L12** | Conception Vie + Agricole (YAML + doc)         | 3       | Markdown              | Jury               |
| **L13** | Rapport de validation final                    | 4       | PDF                   | Jury               |
| **L14** | Mémoire final                                  | Juillet | PDF                   | Jury, école        |

---

## 10. CRITÈRES DE SUCCÈS ET INDICATEURS DE VALIDATION

### 10.1 Critères quantitatifs

Ces métriques seront mesurées sur les datasets de test et présentées dans le rapport de validation final (L13).

| Métrique                           | Cible                                                        | Module            |
| ---------------------------------- | ------------------------------------------------------------ | ----------------- |
| **F1-score** (détection anomalies) | À définir en Phase 1 selon distribution labels               | Santé, Auto       |
| **Précision**                      | À définir                                                    | Santé, Auto       |
| **Rappel**                         | À définir                                                    | Santé, Auto       |
| **Taux de faux positifs**          | Documenté et commenté                                        | Santé, Auto       |
| **Delta généricité/précision**     | Chiffré (comparaison modèle générique vs. spécialisé)        | Santé vs. Auto    |
| **PSI drift**                      | Détection confirmée quand PSI > 0.2 injecté artificiellement | Toutes            |
| **Score grille LLM**               | ≥ 3/5 sur 5 critères                                         | Narration Mistral |
| **Temps de traitement**            | < 3s tabulaire, < 30s documentaire                           | Toutes            |

### 10.2 Critères qualitatifs

| Critère                      | Comment le vérifier                                                                                                                           |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Intelligibilité**          | Un gestionnaire fictif (personne non-technique) peut comprendre une alerte sans lire le code — démontré en soutenance                         |
| **Extensibilité**            | Ajouter le module Auto n'a nécessité aucune modification du moteur central — vérifiable sur Git (diff des fichiers moteur = 0 ligne modifiée) |
| **Modifiabilité des règles** | Un expert métier peut modifier un seuil de détection en éditant uniquement le fichier YAML — démontré en direct                               |
| **Reproductibilité**         | L'environnement se lance en une commande `docker-compose up` et produit des résultats identiques                                              |

### 10.3 Questions jury anticipées et réponses préparées

| Question                                                                              | Réponse préparée                                                                                                                                                                          |
| ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| _"Montrez-nous une anomalie détectée avec son score SHAP et sa cause racine."_        | Démo live : charger un dossier de surfacturation, afficher le score 0.87, les top 3 SHAP (ratio_prix en tête), le diagnostic RCA et la narration Mistral.                                 |
| _"Quelles sont les performances de votre Isolation Forest ? Taux de faux positifs ?"_ | Tableau de métriques sur jeu de test. Commentaire honnête sur les limites.                                                                                                                |
| _"Pourquoi Isolation Forest et pas un Autoencoder ou un modèle supervisé ?"_          | Justification : en production réelle, les labels de fraude sont rares et non fiables. L'IF est non-supervisé, robuste, interprétable via SHAP, et standard académique (Liu et al., 2008). |
| _"Votre dataset est synthétique. Comment vous assurez-vous de la généralisabilité ?"_ | Distribution validée contre les statistiques publiques disponibles. Bruit ±5% injecté. Limite documentée honnêtement.                                                                     |
| _"Comment prouvez-vous que votre framework est générique ?"_                          | Diff Git : moteur central identique entre modules Santé et Auto. Seuls les fichiers YAML et les classes de module ont changé.                                                             |
| _"Votre LLM peut halluciner. Comment le détectez-vous ?"_                             | Grille d'évaluation sur 5 critères. Prompt engineering restrictif (conditionnel obligatoire). Narration de secours template-based.                                                        |
| _"La généricité a-t-elle un coût en précision ? Chiffrez-le."_                        | Tableau comparatif : F1-score modèle Santé seul vs. modèle générique Santé+Auto. Delta mesuré et commenté.                                                                                |

---

## 11. PLANNING SYNTHÉTIQUE

```
AVRIL 2026                          MAI 2026                            JUIN 2026
─────────────────────               ─────────────────────               ─────────────────────
S1  S2  S3  S4  S5  S6  S7          S8  S9  S10 S11                     S12 (buffer)
│   │   │   │   │   │   │           │   │   │   │
╔═══╦═══╗                                                                  Juillet :
║ P0║   ║                                                                  Rédaction
╚═══╩═══╩═══╦═══╗                                                         mémoire
            ║ P1║
            ╚═══╩═══╦═══╦═══╦═══╗
                    ║       P2      ║
                    ╚═══╩═══╩═══╩═══╦═══╦═══╗
                                    ║   P3   ║
                                    ╚═══╩═══╩═══╦═══╦═══╦═══╗
                                                ║       P4       ║
                                                ╚═══╩═══╩═══╚═══╝
```

| Phase  | Contenu principal                                                      | Livrable clé   |
| ------ | ---------------------------------------------------------------------- | -------------- |
| **P0** | CDC, contexte IA, architecture Plugin Contract, cahier technique       | L1, L2, L3, L4 |
| **P1** | Stack setup, pipeline ETL Santé, Isolation Forest, SHAP, module Santé  | L5, L6         |
| **P2** | Dataset Auto, module Auto, Mistral 7B, RCA narratif, grille évaluation | L7, L8, L9     |
| **P3** | Dashboard Next.js, drift monitoring, conceptions Vie+Agricole          | L10, L11, L12  |
| **P4** | Tests E2E, analyse comparative généricité/précision, rapport final     | L13            |

---

## 12. GLOSSAIRE MÉTIER

| Terme                 | Définition                                                                                                                                                                                                        |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ACFE**              | Association of Certified Fraud Examiners. Organisation internationale de référence sur la fraude et les malversations financières.                                                                                |
| **AMC**               | Assurance Maladie Complémentaire. Mutuelle ou assurance privée qui complète le remboursement de l'AMO.                                                                                                            |
| **AMO**               | Assurance Maladie Obligatoire. Régime de base de sécurité sociale couvrant une partie des frais de santé.                                                                                                         |
| **ASAC**              | Association des Sociétés d'Assurance du Cameroun. Organisme professionnel régulant le secteur assurantiel camerounais. Définit la nomenclature des actes médicaux en usage au Cameroun.                           |
| **BEAC**              | Banque des États de l'Afrique Centrale. Banque centrale des pays de la zone CEMAC.                                                                                                                                |
| **BIA**               | Bulletin Individuel d'Adhésion. Formulaire papier utilisé au Cameroun pour souscrire à une assurance santé.                                                                                                       |
| **CCAM**              | Classification Commune des Actes Médicaux. Nomenclature française listant plus de 7 000 actes médicaux avec leurs codes et tarifs de référence.                                                                   |
| **CIMA**              | Conférence Interafricaine des Marchés d'Assurance. Organisation regroupant 14 pays africains et définissant le cadre réglementaire de l'assurance dans la zone CEMAC/UEMOA.                                       |
| **Contamination**     | Paramètre de l'algorithme Isolation Forest représentant la proportion estimée de dossiers anormaux dans le dataset.                                                                                               |
| **Data Drift**        | Phénomène par lequel la distribution statistique des données en production évolue progressivement par rapport à la distribution du jeu d'entraînement, réduisant les performances du modèle ML.                   |
| **eIDAS**             | Règlement européen sur l'identification électronique et les services de confiance. Cadre légal de la signature électronique en Europe.                                                                            |
| **F1-score**          | Moyenne harmonique de la précision et du rappel. Métrique d'évaluation des modèles de classification binaire.                                                                                                     |
| **Feature**           | Variable (colonne) d'un dataset utilisée comme signal d'entrée par un modèle de machine learning.                                                                                                                 |
| **FHIR**              | Fast Healthcare Interoperability Resources. Standard international HL7 définissant le format d'échange des données de santé.                                                                                      |
| **Framework**         | Dans ce projet : ensemble de règles, contrats et briques réutilisables permettant à des modules métiers de s'insérer dans un moteur central sans le modifier. Pas un framework web (≠ React, Django).             |
| **HL7**               | Health Level 7. Organisation internationale définissant les standards d'interopérabilité pour les systèmes d'information de santé.                                                                                |
| **Human-in-the-loop** | Principe architectural selon lequel toute décision automatique de l'IA doit être soumise à validation humaine avant exécution.                                                                                    |
| **ICD-10**            | International Classification of Diseases, 10th revision. Référentiel OMS des codes diagnostics médicaux, utilisé mondialement.                                                                                    |
| **Isolation Forest**  | Algorithme de détection d'anomalies non-supervisé proposé par Liu et al. (2008). Fonctionne en isolant les points aberrants par un minimum de "coupes" aléatoires dans l'espace des features.                     |
| **Mercuriale CIMA**   | Référentiel tarifaire officiel des actes médicaux dans la zone CIMA. Équivalent africain du SNDS français. Utilisé comme prix de référence pour détecter les surfacturations.                                     |
| **Mobile Money**      | Service de paiement mobile (Orange Money, MTN Mobile Money) largement utilisé en Afrique subsaharienne pour les remboursements d'assurance.                                                                       |
| **NOEMIE**            | Norme Ouverte d'Échange entre la Maladie et les Intervenants Extérieurs. Standard français d'échange électronique de données entre l'Assurance Maladie et les organismes complémentaires.                         |
| **OCR**               | Optical Character Recognition. Technologie permettant d'extraire le texte contenu dans une image ou un document scanné.                                                                                           |
| **Plugin Contract**   | Contrat formel (interface Python + schéma YAML) que tout module métier doit respecter pour s'intégrer dans le framework sans modifier le moteur central.                                                          |
| **PSI**               | Population Stability Index. Métrique standard de drift monitoring mesurant le changement de distribution d'une variable entre deux périodes. PSI < 0.1 = stable ; 0.1–0.2 = alerte ; > 0.2 = instable.            |
| **RCA**               | Root Cause Analysis. Analyse de la cause racine. Dans ce projet : mécanisme automatisé identifiant l'origine d'une anomalie (fraude, erreur ou biais) à partir des valeurs SHAP et des règles métier YAML.        |
| **Schema Drift**      | Variante du data drift où c'est la structure du schéma de données (noms de colonnes, types, formats) qui change, rendant le pipeline incompatible.                                                                |
| **SHAP**              | SHapley Additive exPlanations. Méthode d'explicabilité proposée par Lundberg & Lee (2017), basée sur la théorie des jeux de Shapley, permettant de quantifier la contribution de chaque feature à une prédiction. |
| **SNDS**              | Système National des Données de Santé. Référentiel français des données de remboursement de l'Assurance Maladie. Source de référence pour les prix des actes en France.                                           |
| **XAF**               | Franc CFA (zone CEMAC). Devise officielle du Cameroun et de 5 autres pays d'Afrique centrale. Taux de change fixe théorique vis-à-vis de l'EUR (≈ 655 XAF/EUR), mais flottant en pratique pour les conversions.   |

---

## 13. ANNEXES

### Annexe A — Taxonomie complète des anomalies (arbre visuel)

```
Anomalies en Assurance (Framework Générique)
│
├── Catégorie I : Fraude Intentionnelle
│   ├── Fraude à la souscription
│   │   ├── I-A : Usurpation d'identité / Prêt de carte       [V1]
│   │   ├── I-B : Fraude post-mortem                          [V1]
│   │   └── I-C : Omission pathologie préexistante            [V2]
│   ├── Fraude au sinistre
│   │   ├── I-D : Doublon de facturation                      [V1]
│   │   ├── I-E : Surfacturation prestataire                  [V1]
│   │   └── I-F : Fraude en réseau / Collusion                [V2]
│   └── Fraude interne
│       └── I-G : Forçage validation sans justificatif        [V1]
│
├── Catégorie II : Erreurs Opérationnelles
│   ├── Saisie et données
│   │   ├── II-A : Inversion de chiffres (transposition)      [V1]
│   │   └── II-B : Oubli conversion devise EUR/XAF            [V1]
│   ├── Traitement et workflow
│   │   ├── II-C : Code acte incompatible spécialité          [V1]
│   │   └── II-D : Doublon de dossier complet                 [V1]
│   └── Conformité documentaire
│       └── II-E : Facture sans cachet humide (Cameroun)      [V1]
│
├── Catégorie III : Biais Système et Modèle
│   ├── Biais de tarification
│   │   └── III-A : Dépassement systématique Mercuriale       [V1]
│   ├── Biais de sélection
│   │   └── III-B : Rejets OCR massifs zone rurale            [V1]
│   └── Biais de scoring
│       └── III-C : Concentration scores prestataire          [V1]
│
└── Catégorie IV : Risques Techniques et Données
    ├── Pipeline et intégration
    │   ├── IV-A : Fichier entrant corrompu                   [V1]
    │   └── IV-B : Doublons API ingestion massive             [V1]
    ├── Dérive et qualité
    │   ├── IV-C : Data drift (PSI)                           [V1]
    │   └── IV-D : Schema drift (format date)                 [V1]
    └── Performance et disponibilité
        └── [Monitoring — hors périmètre prototype]
```

### Annexe B — Architecture 3 niveaux du framework

```
┌──────────────────────────────────────────────────────────────────┐
│  NIVEAU 3 : PRÉSENTATION                                         │
│  Dashboard Next.js — Interface universelle                       │
│  S'adapte dynamiquement à la branche sélectionnée               │
│  Visualisation SHAP, RCA, narration, validation humaine          │
└─────────────────────────────┬────────────────────────────────────┘
                              │ API REST (FastAPI)
┌─────────────────────────────▼────────────────────────────────────┐
│  NIVEAU 2 : MOTEUR GÉNÉRIQUE (ne change jamais)                  │
│  ┌─────────────┐ ┌──────────┐ ┌──────────────┐ ┌─────────────┐  │
│  │ ETL Pipeline│ │Isolation │ │  SHAP Engine │ │  Mistral 7B │  │
│  │(mapping +   │ │ Forest   │ │(explicabilité│ │ (narration  │  │
│  │normalisation│ │(détection│ │     IA)      │ │  française) │  │
│  └─────────────┘ └──────────┘ └──────────────┘ └─────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │              MOTEUR RCA (règles YAML)                    │    │
│  │  SHAP values + règles métier → catégorie + sous-cat     │    │
│  └──────────────────────────────────────────────────────────┘    │
└─────────────────────────────┬────────────────────────────────────┘
                              │ Plugin Contract
┌─────────────────────────────▼────────────────────────────────────┐
│  NIVEAU 1 : MODULES MÉTIERS (Plugins)                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │   SANTÉ      │ │    AUTO      │ │     VIE      │             │
│  │ (Complet V1) │ │ (Complet V2) │ │ (Conception) │             │
│  │ YAML + Class │ │ YAML + Class │ │ YAML seulem. │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                             ┌──────────────┐                     │
│                             │  AGRICOLE    │                     │
│                             │ (Conception) │                     │
│                             └──────────────┘                     │
└──────────────────────────────────────────────────────────────────┘
```

### Annexe C — Exemple de fiche anomalie complète (bout en bout)

**Dossier SIN_2025_CM_00842 — Module Santé / Flux Cameroun**

```
ENTRÉE
──────
Source       : Scan PDF (flux documentaire, Cameroun)
Établissement: Clinique X, Yaoundé
Acte facturé : Consultation spécialisée cardiologie (Code ASAC: CARD-001)
Montant      : 18 500 XAF
Mercuriale   : 10 200 XAF

TRAITEMENT PIPELINE
───────────────────
1. OCR extraction      → Score confiance global : 0.87 (OK)
                          Cachet humide : présent (OK)
                          Montant extrait : 18 500 XAF ✓
2. Normalisation       → Conversion XAF→EUR : 28.24 EUR
                          Ratio_Prix : 18 500 / 10 200 = 1.814
3. Feature Engineering → ratio_prix_mercuriale = 1.814
                          is_weekend_care = False
                          delai_soin_depot = 3 jours (normal)
                          praticien_actif = True

DÉTECTION ML
────────────
Algorithme   : Isolation Forest
Score anomalie : 0.87 / 1.0
is_anomaly   : TRUE

VALEURS SHAP (top 3)
─────────────────────
1. ratio_prix_mercuriale  : +0.312 (contribution majeure ↑ score anomalie)
2. historique_praticien   : +0.187 (8/10 derniers dossiers > 1.5x Mercuriale)
3. montant_facture        : +0.094

DIAGNOSTIC RCA
──────────────
Catégorie    : Fraude Intentionnelle
Sous-catégorie: Surfacturation Prestataire
Règle YAML   : ratio_prix_mercuriale > 1.5 AND historique_ratio_praticien > 1.3
Confiance RCA: 0.91

NARRATION MISTRAL 7B
─────────────────────
"Le montant facturé pour cette consultation cardiologique (18 500 XAF)
dépasse de 81% le tarif de référence de la Mercuriale CIMA pour cet acte
(10 200 XAF). Ce dépassement n'est pas isolé : sur les 10 derniers dossiers
enregistrés pour ce praticien, 8 présentent un ratio similaire supérieur à
1,5 fois le tarif mercuriale. Ce comportement systématique pourrait indiquer
une pratique de surfacturation délibérée. Un contrôle approfondi de
l'activité de facturation de ce praticien est recommandé avant tout
remboursement."

ACTION GESTIONNAIRE
────────────────────
Décision  : ESCALADE AUDITEUR
Horodatage: 2025-11-14 09:23:41
ID gestionnaire: GES_004
```

### Annexe D — Références bibliographiques clés

| #   | Référence                                                                                                                                                                    |
| --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [1] | Association of Certified Fraud Examiners (ACFE). _Report to the Nations 2022 — Global Study on Occupational Fraud and Abuse._ ACFE, 2022.                                    |
| [2] | Liu, F.T., Ting, K.M., & Zhou, Z.H. _Isolation Forest._ IEEE International Conference on Data Mining, 2008.                                                                  |
| [3] | Lundberg, S.M., & Lee, S.I. _A Unified Approach to Interpreting Model Predictions (SHAP)._ Advances in Neural Information Processing Systems, 2017.                          |
| [4] | HL7 International. _FHIR R4 — Fast Healthcare Interoperability Resources._ hl7.org, 2019.                                                                                    |
| [5] | OMS. _International Classification of Diseases, 10th Revision (ICD-10)._ World Health Organization, 1992 (révision 2019).                                                    |
| [6] | CIMA. _Mercuriale des actes médicaux et pharmaceutiques — Zone CIMA._ Conférence Interafricaine des Marchés d'Assurance.                                                     |
| [7] | Xu, L., et al. _Modeling Tabular Data using Conditional GAN (CTGAN)._ Advances in Neural Information Processing Systems, 2019.                                               |
| [8] | Walonoski, J., et al. _Synthea: An Approach, Method, and Software Mechanism for Generating Synthetic Patients and the Synthetic Electronic Health Care Record._ JAMIA, 2018. |

---

_Fin du document — Version 1.0_
_Prochaine mise à jour : fin Phase 0 (après finalisation Architecture & Plugin Contract)_
_Document maintenu par : ATABONG EFON STEPHANE FRITZ_

---

## 14. IDENTITÉ DU FRAMEWORK — MAKORA

### 14.1 Titre officiel du mémoire

> **Conception d'un framework générique et extensible de détection d'anomalies par
> intelligence artificielle en assurance : architecture, implémentation et validation
> sur les marchés hybrides Afrique-Europe.**

### 14.2 Question de recherche directrice

> **Dans quelle mesure une architecture orientée plugins à schéma déclaratif
> permet-elle de généraliser la détection d'anomalies et la Root Cause Analysis
> à des branches d'assurance hétérogènes, tout en maintenant la précision de
> détection et l'intelligibilité des diagnostics pour les gestionnaires métiers ?**

### 14.3 Nom du framework — MAKORA

Le framework développé dans le cadre de ce projet porte le nom **MAKORA**.

**Acronyme :** Multimodal Anomaly Kernel for Operational Risk Analysis
**Traduction :** Noyau Multimodal d'Analyse des Anomalies pour les Risques Opérationnels

Chaque terme de l'acronyme est directement justifié par l'architecture du projet :

| Terme                | Justification architecturale                                                                                                                                          |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Multimodal**       | Le framework traite simultanément des données structurées (CSV/JSON) et non-structurées (scans PDF, images) dans un pipeline unique — hybridité France/Cameroun.      |
| **Anomaly**          | La détection d'anomalies est la fonction centrale du système, couvrant fraudes, erreurs opérationnelles, biais système et risques techniques.                         |
| **Kernel**           | Le moteur central est un noyau immuable. Les modules métiers (Santé, Auto, Vie, Agricole) gravitent autour de lui sans jamais le modifier — c'est le Plugin Contract. |
| **Operational Risk** | Le framework s'inscrit dans le cadre de la gestion des risques opérationnels financiers, vocabulaire reconnu en actuariat et en audit.                                |
| **Analysis**         | Le système ne détecte pas seulement — il analyse et explique via la Root Cause Analysis et la narration en langage naturel.                                           |

### 14.4 Le Cycle d'Adaptation MAKORA

Le fonctionnement du framework repose sur un cycle itératif en trois phases :

**Phase 1 — L'Exposition**
Le système reçoit un flux de données inconnu ou d'une nouvelle nature (nouvelle
branche d'assurance, nouveau marché géographique, nouveau type de document).

**Phase 2 — La Rotation (Analyse Multimodale)**
Le Kernel s'active. Les briques du moteur central (ingestion, normalisation, détection
ML, explicabilité SHAP, moteur RCA, narration LLM) traitent simultanément le dossier
sous tous ses angles, indépendamment de sa source ou de sa branche.

**Phase 3 — L'Adaptation (RCA)**
Le système produit un diagnostic. Il ne se contente pas de lever une alerte — il
identifie la logique de l'anomalie, la catégorise et l'explique en français naturel.
Chaque décision humaine (validation/rejet) alimente la boucle de rétroaction et
renforce la précision future du Kernel.

> Ce cycle illustre la propriété fondamentale que ce mémoire cherche à prouver :
> un framework générique n'est pas un système qui fait tout de manière médiocre —
> c'est un système qui apprend à s'adapter à n'importe quel contexte sans perdre
> en rigueur analytique.

### 14.5 Note d'inspiration

Le nom MAKORA est inspiré des _Mahoragas_, divinités protectrices de la mythologie
bouddhiste, symbolisant la résilience face à l'adversité et la capacité d'adaptation
face à des menaces imprévisibles — deux propriétés que ce framework cherche
précisément à incarner face à la fraude en assurance.
