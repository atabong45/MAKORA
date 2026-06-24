# Analyse qualitative des erreurs de classification — T12.3
## MAKORA — Expérience H0 — Deep Isolation Forest

> **Périmètre :** 80 cas analysés — 10 faux positifs (FP) + 10 faux négatifs (FN) par
> modèle × 4 combinaisons (M_sante/sante, M_makora/sante, M_auto/auto, M_makora/auto).
> **Méthode d'explicabilité :** KernelSHAP [Lundberg2017], background set = 100 dossiers
> normaux du train set, `nsamples=100`, `l1_reg="aic"`.
> **Date d'exécution :** 08 juin 2026.

---

## 1. Protocole d'analyse

L'évaluation quantitative d'un système de détection d'anomalies — métriques F1, MCC,
AUC-ROC — ne suffit pas à caractériser ses limites opérationnelles. Chandola et al.
soulignent que l'inspection qualitative des cas d'erreur est nécessaire pour identifier
les angles morts structurels des méthodes non-supervisées, en particulier la distinction
entre les erreurs corrigeables (seuil mal calibré) et les erreurs intrinsèques (fraudes
indétectables avec les features disponibles) [Chandola2009, §5.3].

MAKORA adopte ce protocole en analysant les cas les plus proches du seuil de décision,
et non les cas extrêmes. Ce choix est délibéré : un dossier avec un score très élevé
est trivial à interpréter ; un dossier juste au-dessus du seuil révèle les vraies
frontières du modèle [Chandola2009]. La proximité au seuil est mesurée par
`|score - médiane(scores)`, la médiane des scores DIF servant de référence naturelle
puisque les scores DIF ne sont pas normalisés dans [0, 1] [Xu2023].

L'explicabilité est fournie par KernelSHAP [Lundberg2017]. Deep Isolation Forest est
un réseau de neurones — TreeExplainer est inapplicable. KernelSHAP est un estimateur
model-agnostique basé sur les valeurs de Shapley de la théorie des jeux coopératifs
[Shapley1953] : il mesure la contribution marginale de chaque feature à la prédiction
d'un cas donné, relativement à un background set de dossiers de référence. Le background
set est constitué de 100 dossiers normaux tirés aléatoirement du train set, après
application de la même transformation de features (`engineer_features()`) qu'à
l'inférence.

---

## 2. Répartition des causes d'erreur

Sur les 80 cas analysés, trois catégories d'erreur ont été identifiées :

| Cause | Nb cas | % | Type d'erreur |
|---|---|---|---|
| `CAS_LIMITE_METIER` | 40 | 50.0% | Faux négatifs (FN) |
| `SEUIL_MAL_CALITRE` | 26 | 32.5% | Faux positifs (FP) |
| `BRUIT_DONNEES` | 14 | 17.5% | Faux positifs (FP) |

La distribution est symétrique dans sa grande ligne : 50% des erreurs sont des FN
non évitables, 50% sont des FP répartis entre deux mécanismes distincts. Cette
répartition est cohérente avec les observations de Bauder et Khoshgoftaar sur les
données Medicare, où les FP proviennent principalement de prestataires légitimes
à comportement atypique, tandis que les FN correspondent à des fraudes bien camouflées
[Bauder2017].

---

## 3. Faux négatifs — Fraudes non détectées

### 3.1 Mécanisme général

Les 40 FN appartiennent tous à la catégorie `CAS_LIMITE_METIER`. L'inspection des
valeurs phi KernelSHAP révèle un pattern systématique : toutes les contributions sont
négatives ou nulles, signifiant que chaque feature pousse le score vers "normal". Le
modèle ne dispose d'aucun signal qui distingue ces dossiers de la distribution normale.

Ce résultat n'est pas un échec du modèle : il documente une limite structurelle des
approches non-supervisées basées sur des features tabulaires stateless. Chandola et al.
caractérisent cette catégorie comme des anomalies "contextuelles" — leur nature
frauduleuse n'est visible que dans un contexte inter-temporel ou inter-entités
[Chandola2009, §3.2]. Avec une architecture de features stateless (calculées sur le
batch courant sans historique inter-batches, dette technique DT-002), ces cas sont
intrinsèquement indétectables.

### 3.2 Sous-types représentés

Les sous-types de fraude présents dans les FN illustrent concrètement ce mécanisme.

**Fraudes de surfacturation conformes à la mercuriale.** Les dossiers présentent un
`ratio_prix_mercuriale` et un `montant_log` dans les bornes acceptables. La fraude
consiste à facturer des actes réellement réalisés mais à des tarifs légèrement gonflés,
restant sous le seuil d'alerte de la mercuriale CIMA. Sans historique de facturation
du praticien sur plusieurs batches, le modèle ne peut détecter la dérive progressive
[Bauder2017].

**Doublons techniques inter-batches.** La feature `flag_doublon` détecte les doublons
au sein du même batch. Les dossiers soumis deux fois sur des batches différents
produisent un `flag_doublon = 0` sur les deux occurrences et un score DIF normal.
C'est la dette DT-002 documentée : l'absence de persistance inter-batches rend ces
doublons invisibles.

**Fraudes en réseau à signal faible.** Les dossiers impliqués dans des schémas de
collusion (praticien-réseau, kickbacks) présentent des features individuelles conformes.
La feature `community_score` capte l'appartenance à une communauté Louvain suspecte
[Blondel2008, Jiang2014], mais son signal est insuffisant lorsque la communauté est
petite (moins de 5 membres) ou récente. Pour M_makora en particulier — qui opère sur
13 features communes — le signal réseau est plus dilué que pour M_sante sur ses
20 features spécialisées.

### 3.3 Implication pour la thèse

Ces FN constituent une limite honnête et documentée du système. Ils ne disqualifient
pas MAKORA : ils définissent son périmètre d'efficacité. La détection de ces cas
nécessiterait soit un historique inter-batches (architecture stateful, hors scope V1),
soit des données relationnelles plus denses (graphe complet avec historique de 6 mois
minimum), soit un modèle semi-supervisé incorporant des labels partiels [Chandola2009,
§5.3]. Ces pistes constituent des perspectives de recherche explicitement formulées
dans la conclusion du mémoire.

---

## 4. Faux positifs — Dossiers normaux mal classés

Les 40 FP se répartissent en deux mécanismes distincts, révélés par les valeurs phi
KernelSHAP.

### 4.1 SEUIL_MAL_CALITRE — 26 cas (32.5%)

**Pattern SHAP observé.** Les valeurs phi sont toutes négatives ou très proches de
zéro. Aucune feature ne pousse le dossier vers "anomalie" de manière isolée : c'est
la somme des contributions qui dépasse le seuil médiane. Un exemple typique sur la
branche Santé :

```
phi = [-0.022, -0.017, -0.016, -0.014, -0.011, -0.009, -0.008, ...]
```

Chaque feature contribue modestement vers "normal", mais l'accumulation de ces
contributions négatives (relativement au background set) donne un score supérieur
à la médiane.

**Interprétation métier.** Ces dossiers sont statistiquement atypiques sur plusieurs
dimensions sans être frauduleux sur aucune. En branche Santé, il s'agit typiquement
de praticiens à fort volume de facturation dont tous les montants sont conformes à la
mercuriale CIMA mais dont le profil global diffère du background set de dossiers normaux.
En branche Auto, il s'agit de véhicules haut de gamme dont le devis est cohérent avec
la cote Argus mais dont plusieurs features administratives (délai de déclaration,
absence de constat) présentent des valeurs atypiques légitimes.

**Cause technique.** La contamination entraîne DIF à considérer un certain pourcentage
du train comme anomalie. Si la contamination calibrée (0.068 pour Santé, 0.100 pour
Auto) est légèrement supérieure au taux de fraude réel dans certains segments de la
distribution, le modèle abaisse son seuil de détection et flagge des cas légitimes
atypiques [Davis2006]. C'est le compromis fondamental des méthodes non-supervisées
décrit par Viaene et al. : un seuil plus bas augmente le rappel mais dégrade la
précision sur les cas frontières [Viaene2002].

### 4.2 BRUIT_DONNEES — 14 cas (17.5%)

**Pattern SHAP observé.** Contrairement aux cas précédents, les valeurs phi présentent
une feature fortement positive isolée, pendant que les autres restent négatives. Un
exemple typique sur M_makora branche Auto :

```
phi = [+0.022, +0.012, -0.021, -0.015, -0.008, -0.006, ...]
```

La feature positive domine les autres et propulse le score au-dessus du seuil.

**Identification de la feature dominante.** L'inspection des cas BRUIT_DONNEES révèle
que la feature positive est systématiquement `community_score` ou
`prestataire_concentration`. Ces features mesurent respectivement l'appartenance à une
communauté Louvain (score élevé = communauté dense) et la concentration des sinistres
sur un prestataire dans le batch courant.

**Mécanisme de l'artefact.** L'algorithme de Louvain partitionne le graphe
praticien/assuré en communautés à modularité maximale [Blondel2008]. Sur un batch de
30 jours avec peu de dossiers, le graphe est peu dense et l'algorithme crée des
communautés artificiellement petites et serrées qui ne correspondent pas à un réseau
de fraude réel. Le `community_score` d'un assuré peut ainsi être élevé simplement
parce qu'il partage un praticien avec deux ou trois autres assurés dans le même
arrondissement de Yaoundé, sans aucune collusion. Jiang et al. documentent ce type
d'artefact dans les graphes peu denses : la synchronisation comportementale n'est
significative qu'au-delà d'un seuil de densité minimale [Jiang2014].

Ce mécanisme est plus fréquent sur M_makora (13 features communes) que sur les modèles
spécialisés (20-21 features), car M_makora donne proportionnellement plus de poids aux
features réseau dans son espace de représentation réduit.

---

## 5. Comparaison par modèle

### 5.1 M_sante (spécialisé, branche Santé)

Seuil de référence médiane : 0.2930. Les FP sont exclusivement de type
`SEUIL_MAL_CALITRE`. Les valeurs phi montrent des contributions uniformément
distribuées sur les 20 features sans feature dominante, confirmant que ces dossiers
sont atypiques de manière diffuse. Les FN présentent des scores proches de la médiane
(0.27-0.31), attestant que le modèle n'a aucun signal discriminant sur ces cas.

### 5.2 M_makora sur Santé (générique, 13 features)

Seuil de référence médiane : 0.2522. Le background set contient 100 dossiers normaux
avec 13 features engineerées. Les FP de type `BRUIT_DONNEES` apparaissent ici car
`community_score` représente 1/13 des features contre 1/20 dans M_sante, ce qui
amplifie son influence relative. Les FN présentent les mêmes patterns que M_sante mais
avec des valeurs phi légèrement plus concentrées sur un sous-ensemble réduit de features.

### 5.3 M_auto (spécialisé, branche Auto)

Seuil de référence médiane : 0.3050. Les FP `SEUIL_MAL_CALITRE` présentent des
patterns SHAP différents des cas Santé : `ocr_confiance_faible`, `constat_manquant`
et `expertise_manquante` dominent. Ces features reflètent les patterns de fraude
automobile documentés par Viaene et al. — absence de documents physiques lors de
sinistres réels [Viaene2002]. Les FN incluent des sous-types `Falsification_Constat`
et `Pieces_Reemploi` dont les features tabulaires sont conformes aux barèmes ASAC.

### 5.4 M_makora sur Auto (générique, 13 features)

Seuil de référence médiane : 0.2606. C'est le modèle présentant le plus de cas
`BRUIT_DONNEES` proportionnellement. La feature `community_score` dans l'espace 13D
génère davantage de faux positifs réseaux que dans M_auto (21 features), ce qui est
cohérent avec le principe de l'Isolation Forest : dans un espace de plus faible
dimension, les points sont moins isolables et les frontières de décision sont plus
sensibles aux features réseau à forte variance [Liu2008].

---

## 6. Lecture des valeurs phi KernelSHAP

Une valeur phi positive signifie que la feature en question pousse le score d'anomalie
vers le haut par rapport au comportement attendu sur un dossier normal du background
set. Une valeur phi négative signifie qu'elle le pousse vers le bas. La somme des phi
est égale à la différence entre le score du cas analysé et le score moyen du background
set [Lundberg2017].

Cette propriété d'additivité garantit que l'interprétation est cohérente : un dossier
flaggé fraude avec toutes les phi négatives est un cas où le modèle décide sur
l'accumulation de déviations mineures par rapport à la normale, non sur un signal fort
d'une feature particulière. Inversement, un dossier avec une phi fortement positive
isolée est un cas où une feature unique déclenche l'alerte.

La stabilité des valeurs phi a été vérifiée à un niveau préliminaire : les runs
successifs sur les mêmes dossiers produisent des classements de features cohérents,
ce qui est attendu avec `nsamples=100` et `l1_reg="aic"` sur un espace de dimension
modérée (13-21 features) [Lundberg2017].

---

## 7. Synthèse et limites documentées

L'analyse qualitative T12.3 met en évidence trois résultats exploitables dans le
mémoire.

**Résultat 1 — 50% des erreurs sont structurellement irréductibles** avec les features
et l'architecture actuelles. Les fraudes de type `CAS_LIMITE_METIER` nécessitent un
historique inter-batches, une densité de graphe plus grande, ou un modèle semi-supervisé.
Ces cas ne constituent pas un échec du système : ils définissent son périmètre.

**Résultat 2 — Les 32.5% de FP par seuil mal calibré** sont partiellement corrigeables.
La stratégie `fpr5_constrained` déjà appliquée sur la branche Auto (contrainte FPR ≤ 5%)
réduit significativement cette catégorie. Sur Santé, la stratégie `phi_optimal` est
un compromis entre précision et rappel. Une segmentation plus fine du train set par
profil de praticien pourrait réduire ces FP sans dégrader le rappel [Davis2006].

**Résultat 3 — Les 17.5% de FP par bruit réseau** sont spécifiques à l'architecture
stateless du graphe Louvain sur batch de 30 jours. Ils sont plus fréquents sur M_makora
que sur les modèles spécialisés, ce qui constitue un coût concret de la généricité
identifiable et quantifiable. Ce coût reste acceptable au regard du gain de généricité
apporté par M_makora [Caruana1997].

Ces trois résultats sont cohérents avec les limites documentées des approches
non-supervisées par Chandola et al. [Chandola2009] et constituent une contribution
analytique du mémoire au-delà des métriques agrégées.

---

## Références

**[Bauder2017]** Bauder, R. A., & Khoshgoftaar, T. M. (2017). Medicare fraud detection
using machine learning methods. *14th International Conference on Machine Learning
and Applications (ICMLA)*, 858-865.

**[Blondel2008]** Blondel, V. D., Guillaume, J. L., Lambiotte, R., & Lefebvre, E. (2008).
Fast unfolding of communities in large networks. *Journal of Statistical Mechanics:
Theory and Experiment*, P10008.

**[Caruana1997]** Caruana, R. (1997). Multitask learning. *Machine Learning*, 28(1), 41-75.

**[Chandola2009]** Chandola, V., Banerjee, A., & Kumar, V. (2009). Anomaly detection:
A survey. *ACM Computing Surveys*, 41(3), 15:1-15:58.

**[Davis2006]** Davis, J., & Goadrich, M. (2006). The relationship between
Precision-Recall and ROC curves. *Proceedings of the 23rd International Conference
on Machine Learning (ICML)*, 233-240.

**[Jiang2014]** Jiang, M., Cui, P., Beutel, A., Faloutsos, C., & Yang, S. (2014).
CatchSync: Catching synchronized behavior in large directed graphs. *Proceedings of
the 20th ACM SIGKDD International Conference on Knowledge Discovery and Data Mining*,
941-950.

**[Liu2008]** Liu, F. T., Ting, K. M., & Zhou, Z. H. (2008). Isolation forest.
*Eighth IEEE International Conference on Data Mining (ICDM)*, 413-422.

**[Lundberg2017]** Lundberg, S. M., & Lee, S. I. (2017). A unified approach to
interpreting model predictions. *Advances in Neural Information Processing Systems
(NeurIPS)*, 30, 4765-4774.

**[Shapley1953]** Shapley, L. S. (1953). A value for n-person games. *Contributions
to the Theory of Games*, 2, 307-317.

**[Sculley2015]** Sculley, D., Holt, G., Golovin, D., Davydov, E., Phillips, T.,
Ebner, D., Chaudhary, V., Young, M., Crespo, J. F., & Dennison, D. (2015). Hidden
technical debt in machine learning systems. *Advances in Neural Information Processing
Systems (NeurIPS)*, 28, 2503-2511.

**[Viaene2002]** Viaene, S., Derrig, R. A., Baesens, B., & Dedene, G. (2002).
A comparison of state-of-the-art classification techniques for expert automobile
insurance fraud detection. *Journal of Risk and Insurance*, 69(3), 373-421.

**[Xu2023]** Xu, H., Pang, G., Wang, Y., & Wang, Y. (2023). Deep isolation forest
for anomaly detection. *IEEE Transactions on Knowledge and Data Engineering*, 35(12),
12591-12604.

---

*MAKORA T12.3 — Analyse qualitative FP/FN avec KernelSHAP*
*ATABONG EFON STEPHANE FRITZ — ENSPY/UY1 — 08 juin 2026*
*80 cas analysés | 4 modèles × 2 branches | background=100 dossiers normaux*
