# MAKORA — Plan de Soutenance Juillet 2026 (v3)
> **Généré le :** Jeudi 11 juin 2026
> **Échéance absolue :** Lundi 20 juillet 2026
> **Jours disponibles :** 40 jours exactement
> **Auteur :** ATABONG EFON STEPHANE FRITZ

---

## 📋 CHANGEMENTS PAR RAPPORT AU V2

| Décision v3 | Justification |
|---|---|
| **Frontend AVANT mémoire** (Phase 1 ↔ Phase 2 inversées) | Sécuriser la démo en priorité — la migration mémoire peut se faire ensuite sereinement |
| **7 jours** réécriture profonde du mémoire, **découpée par parties** | Tu comptes faire une révision en profondeur, pas juste des corrections ciblées |
| **2 jours** lecture des papiers scientifiques (NEW phase) | Maîtriser les sources pour défendre tes propos sans hésitation |
| **3 jours** relecture intensive (plus courte que la réécriture) | Simple relecture, pas de réécriture active |
| Démarrage **jeudi 11 juin** | J1 = admin/Fippo le matin + début Phase 5 frontend l'après-midi |
| **9 jours** frontend avec buffer explicite | Code = imprévisible, intégrer du slack |
| **6 jours** application correctifs Fippo | L'encadreur peut demander beaucoup |
| **4 jours** PPT + vidéo (compressé) | Tu vas vite sur ces livrables |
| **1 jour** rédaction discours (compressé) | Tu vas vite sur ce livrable |
| **6 jours** répétitions + Q&A intensif | C'est là que tout se joue à l'oral |
| **Section 11** angles morts détaillés (inchangée v2) | Pré-soutenance, anti-plagiat, reliure, etc. |

---

## 🔍 DIAGNOSTIC HONNÊTE — ÉTAT RÉEL DU PROJET

| Composant | État réel | Effort restant estimé |
|---|---|---|
| **Backend** | ✅ Complet — 388 tests, 117 endpoints | ~0 jours (sauf bug urgent) |
| **Mémoire LaTeX** | ⚠️ 100 pages écrites MAIS révision profonde + DIF + incohérences | **7 jours réécriture + 2 jours lecture papiers + 3 jours relecture** |
| **Frontend — Phases 1–4.5** | ✅ Livré (~82 fichiers) | 0 |
| **Frontend — Phases 5–10** | 🔴 6 phases restantes | **9 jours avec buffer (en premier)** |
| **Vidéo de démo** | ❌ À faire | 2 jours |
| **PowerPoint** | ❌ À faire | 2 jours |
| **Préparation orale** | ❌ À faire | **8 jours** (discours + Q&A + répétitions) |
| **Dossier administratif** | ❌ À faire | 2 jours |
| **Accord encadreurs** | ❌ Non sollicité | **À déclencher aujourd'hui** |
| **Logistique famille** | ❌ À planifier | 1 jour |
| **Pré-soutenance interne** | ❌ Non planifiée | 1 jour |
| **Anti-plagiat Turnitin** | ❌ Non fait | 0,5 jour |
| **Reliure du mémoire** | ❌ Non commencée | 2 jours (délai imprimeur) |

---

## ⚠️ INCOHÉRENCES MÉMOIRE — DÉCISION DIF MAINTENUE

Tu as choisi d'assumer DIF dans le mémoire. C'est défendable et c'est cohérent avec ce qui tourne réellement. Voici ce que cela implique concrètement.

### Inventaire des passages à réécrire dans le mémoire LaTeX

| Section | Page actuelle | Action |
|---|---|---|
| §3.1.1 — Stack technologique | p.54 | Ajouter PyOD + Deep Isolation Forest |
| §3.1.2 — Plugin Contract et pipeline | p.56 | Mentionner `DIFStrategy` dans le registry |
| §3.2.1 — Comparaison algorithmique | p.59–62 | **Tableau 3.7 & 3.8 à refaire** : ajouter colonne DIF / supprimer IF max_feat ou positionner DIF comme retenu |
| §3.2.2 — Justification du choix | p.62–64 | **Section entièrement à réécrire** : "Justification du choix DIF en production" remplace "Justification du choix IF classique" |
| Tableau 3.9 — Trade-off | p.62 | Refaire la ligne "compatible SHAP TreeExplainer" → "compatible SHAP KernelExplainer (background fixe)" |
| §3.2.3 — Validation H0 | p.64 | Recalculer/regénérer si chiffres dépendent du modèle (Φ-Score) |
| ADR-001 (sur IF compatible joblib) | §2.2.4 | Modifier le verdict de l'ADR — DIF est aussi persistable |
| Glossaire | p.viii | Ajouter entrée "Deep Isolation Forest" |
| Bibliographie | p.72+ | **Ajouter [Xu2023]** Xu, Pang, Wang, Cao. "Deep Isolation Forest for Anomaly Detection". IEEE TKDE 2023 |
| Tableaux 2.8 et 2.9 — features | p.42 | Mettre à jour 17→20 (Santé), 18→21 (Auto) |
| Annexe V — tests | p.100 | Recompter et harmoniser à 388 |
| Page 87 — "532 tests" | p.87 | Harmoniser à 388 |
| Remerciements | p.ii | Remplacer placeholders par noms réels du jury |

**Ce qui ne change pas (rassure-toi) :**
- Toute l'architecture Plugin Contract (§2.2)
- Tous les diagrammes UML (D1–D16)
- L'hypothèse H0 et son protocole (§2.4.5)
- Le pipeline OCR (§3.1.3)
- Les analyses qualitatives FP/FN (§3.3.3)
- Les limites L1–L5 (§3.3.4)
- La conclusion générale

C'est **5 jours intensifs** mais ciblés. Ce n'est pas une réécriture du mémoire.

---

## 📅 PLANNING JOUR PAR JOUR — 40 JOURS

### PHASE 1 — FRONTEND SPRINT AVEC BUFFER (9 jours)

| # | Jour | Date | Tâche principale | Buffer |
|---|---|---|---|---|
| J1 | **Jeu** | **11 juin** | **Matin : Contact Fippo + scolarité ENSPY + tuteur ITNS** • Après-midi : Phase 5 jour 1 — AuditQueue + DecisionPanel | |
| J2 | Ven | 12 juin | Phase 5 jour 2 — ShapChart + RcaSummary + Escalations | |
| J3 | Sam | 13 juin | Phase 7 jour 1 — **`/ml/models/compare`** (preuve H0) | |
| J4 | Dim | 14 juin | Phase 7 jour 2 — Drift + Retraining + ModelDetail | |
| J5 | Lun | 15 juin | Phase 6 jour 1 — Graphe D3 NetworkGraph (le plus risqué) | |
| J6 | Mar | 16 juin | **BUFFER** Phase 6 jour 2 OU rattrapage phases précédentes | ✅ |
| J7 | Mer | 17 juin | Phase 8 — Configuration YAML + Mercuriale | |
| J8 | Jeu | 18 juin | Phase 9 — Rapports + Admin (peut être allégé) | |
| J9 | Ven | 19 juin | Phase 10 + bug login `application/x-www-form-urlencoded` + smoke tests E2E | |

**Principe de ce sprint :** ordre par valeur soutenance, pas par numéro de phase. Le frontend passe en premier pour sécuriser la démo — si quelque chose dérape, c'est ici que le risque est concentré. J6 est un buffer dimanche ou un rattrapage si Phase 6 (D3) prend plus de temps.

**⚠️ Actions critiques du J1 (avant de coder) :** sans le délai administratif de l'ENSPY validé et sans l'accord de Fippo, tout le planning peut s'effondrer. Voir Section "CE QU'IL FAUT FAIRE AUJOURD'HUI".

---

### PHASE 2 — RÉÉCRITURE PROFONDE DU MÉMOIRE (7 jours, découpée par parties)

Tu vas faire une révision **en profondeur**, pas juste corriger les 4 incohérences listées plus haut. Le découpage par grande partie permet d'avoir un objectif clair chaque jour et de mesurer l'avancement.

| # | Jour | Date | Partie du mémoire travaillée |
|---|---|---|---|
| J10 | Sam | 20 juin | **Introduction Générale** — contexte, problématique, question de recherche, contributions, plan |
| J11 | Dim | 21 juin | **Chapitre 1 — Concepts généraux + État de l'art** — fraude assurance, ML non-supervisé, XAI, gap africain |
| J12 | Lun | 22 juin | **Chapitre 2 — Partie A** — Analyse besoins + Conception architecturale (Plugin Contract, ADRs, diagrammes UML) |
| J13 | Mar | 23 juin | **Chapitre 2 — Partie B** — Composants Kernel + Modules Santé/Auto + Corpus + Protocole expérimental (H0) |
| J14 | Mer | 24 juin | **Chapitre 3 — Partie A** — Réalisation technique : stack, **intégration DIF complète** (§3.1, §3.2.1, §3.2.2, Tableau 3.9, ADR-001) |
| J15 | Jeu | 25 juin | **Chapitre 3 — Partie B** — Résultats expérimentaux DIF/IF/LOF/OC-SVM + Validation H0 + Discussion + Limites L1–L5 |
| J16 | Ven | 26 juin | **Conclusion Générale + Annexes + Bibliographie** — ajout [Xu2023], harmonisation chiffres (388 tests, 20/21 features), Remerciements |

**Référentiel :** l'inventaire détaillé des passages à modifier est dans la section "INCOHÉRENCES MÉMOIRE — DÉCISION DIF MAINTENUE" plus haut. Chaque jour, ouvrir cette liste pour cocher les passages traités.

**Discipline du sprint :** une partie par jour, finie en fin de journée. Si la Partie A de J12 déborde, on ne décale pas — on rogne sur le superflu pour terminer.

---

### PHASE 3 — LECTURE DES PAPIERS SCIENTIFIQUES (2 jours)

Cette phase est **stratégique pour la défense orale**. Tu cites des papiers dans ton mémoire — le jury peut te demander de défendre une citation précise. Avoir lu le papier (et pas juste l'abstract) change tout dans la profondeur des réponses.

| # | Jour | Date | Papiers à lire (lecture active avec notes) |
|---|---|---|---|
| J17 | Sam | 27 juin | **Core algorithmique** : [Liu2008] Isolation Forest • [Xu2023] Deep Isolation Forest • [Chandola2009] Anomaly survey • [Lundberg2017] SHAP • [Caruana1997] Multitask learning |
| J18 | Dim | 28 juin | **Domaine + complémentaires** : [Bauder2017] Medicare fraud • [Sculley2015] Technical debt ML • [Blondel2008] Louvain • [Gama2014] Concept drift • [Goldstein2016] Comparative AD |

**Pour chaque papier, méthode active :**
- Lire l'introduction et la conclusion en détail (10 min)
- Survoler la méthodologie pour identifier les hypothèses (10 min)
- Lire en détail la section que tu cites dans ton mémoire (10 min)
- Noter **3 idées** à pouvoir restituer à l'oral : (1) ce que le papier prouve, (2) sa limite reconnue, (3) ce qui le rend pertinent pour MAKORA

**Objectif final :** pour chacune des 10 références majeures, pouvoir répondre en 30 secondes à : "Quel est l'apport spécifique de ce papier à votre travail ?"

---

### PHASE 4 — RELECTURE INTENSIVE DU MÉMOIRE (3 jours, plus courte)

Cette phase est différente de la Phase 2 : ici, **pas de réécriture active**. Tu relis le mémoire comme un lecteur extérieur, en chassant les incohérences, les fautes, les passages obscurs. C'est plus rapide parce que c'est moins créatif.

| # | Jour | Date | Tâche principale |
|---|---|---|---|
| J19 | Lun | 29 juin | Relecture Introduction + Chapitre 1 + Chapitre 2 — cohérence narrative, fautes, citations |
| J20 | Mar | 30 juin | Relecture Chapitre 3 + Conclusion — cohérence DIF, vérification chiffres et tableaux |
| J21 | Mer | 1er juil | Relecture Annexes + Bibliographie + figures HD + **anti-plagiat Turnitin** + **ENVOI à Dr Fippo** |

**Méthode de relecture intensive recommandée :**
- Lecture à voix haute des passages clés (révèle les phrases mal construites)
- Vérification croisée de chaque chiffre cité (388, 20, 21, 0,47, etc.)
- Vérification que chaque figure est référencée dans le texte
- Vérification que chaque référence biblio est citée au moins une fois

**À J21, envoi à Fippo avec mail explicite :** "Voici la version mémoire que je considère prête pour relecture finale. Je vise une soutenance le 20 juillet. Vos retours seraient particulièrement précieux d'ici le 6 juillet pour me permettre d'intégrer les corrections sereinement."

---

### PHASE 5 — VIDÉO DEMO + POWERPOINT (4 jours compressés)

| # | Jour | Date | Tâche principale |
|---|---|---|---|
| J22 | Jeu | 2 juil | Vidéo de démo — scénario + 1er tournage (capture écran + voix off) |
| J23 | Ven | 3 juil | Vidéo de démo — montage + retouches + export final (version intégrale + version courte 3 min) |
| J24 | Sam | 4 juil | PowerPoint — structure + slides 1–25 (contexte → architecture) |
| J25 | Dim | 5 juil | PowerPoint — slides 26–50 (résultats → conclusion) + animations sobres |

**Tu vas vite sur ces livrables, donc on compresse.** Ne pas négliger : la vidéo de démo sert AUSSI de **backup le jour J si le frontend crashe en live**. Garde-la sur 3 supports (clé USB principale, clé USB backup, drive).

---

### PHASE 6 — APPLICATION CORRECTIFS FIPPO (6 jours — buffer généreux)

| # | Jour | Date | Tâche principale |
|---|---|---|---|
| J26 | Lun | 6 juil | Réception retours Dr Fippo + analyse + plan d'action |
| J27 | Mar | 7 juil | Correctifs majeurs jour 1 (refonte chapitres si demandé) |
| J28 | Mer | 8 juil | Correctifs majeurs jour 2 |
| J29 | Jeu | 9 juil | Correctifs mineurs + 2e envoi à Fippo si besoin |
| J30 | Ven | 10 juil | **BUFFER** retours additionnels Fippo + retours tuteur ITNS |
| J31 | Sam | 11 juil | Finalisation LaTeX + export PDF final + dernière relecture |

**Pourquoi 6 jours :** les retours d'un encadreur peuvent aller d'une simple liste de coquilles à une demande de restructuration de chapitre. Ne pas pouvoir absorber ça est un risque très réel. Si Fippo ne demande rien de profond, ces jours libérés vont automatiquement renforcer les répétitions.

---

### PHASE 7 — DISCOURS + Q&A + RÉPÉTITIONS (6 jours intensifs)

| # | Jour | Date | Tâche principale |
|---|---|---|---|
| J32 | Dim | 12 juil | **Discours intégral en 1 jour** — intro, architecture, résultats, conclusion |
| J33 | Lun | 13 juil | **Q&A massif** — préparer 60 questions probables + axes de réponse |
| J34 | Mar | 14 juil | Répétition complète chronométrée #1 (seul, enregistrée) + revue auto |
| J35 | Mer | 15 juil | **Pré-soutenance devant un pair** (simulation jury complète) |
| J36 | Jeu | 16 juil | Corrections suite pré-soutenance + Répétition #2 |
| J37 | Ven | 17 juil | Répétition #3 + simulation Q&A hostile (10 questions piégées) |

**Concept clé :** tu maîtrises le sujet en profondeur, donc le discours peut s'écrire vite. Ce qui fait la différence, ce sont les répétitions. À J34, ton premier essai sera médiocre — c'est normal. À J37, tu auras répété 4 fois (dont 1 avec public) : la fluidité sera là.

---

### PHASE 8 — ADMIN + RELIURE + RÉCUP + SOUTENANCE (3 jours)

| # | Jour | Date | Tâche principale |
|---|---|---|---|
| J38 | Sam | 18 juil | Dépôt dossier ENSPY (si pas déjà fait) + récupération reliure + invitations famille + test stack complet sur ordi de soutenance |
| J39 | Dim | 19 juil | **Repos** + lecture lente du mémoire imprimé + relecture Q&A + checklist matérielle |
| J40 | **Lun** | **20 juil** | **🎓 SOUTENANCE** |

**⚠️ Si l'ENSPY exige un dépôt 2–4 semaines AVANT la soutenance, J38 est trop tard.** Il faudra alors avancer le dépôt à J21 ou avant, avec une version "draft validée" du mémoire et mise à jour finale après corrections Fippo. Cette décision dépend entièrement de la réponse de la scolarité obtenue au J1.

**Règle du J39 :** plus aucune modification de fond. Plus de nouveau slide. Plus de nouvelle figure. Plus de réécriture de paragraphe. À ce stade tout est figé. C'est la journée du calme et du sommeil.

---

## 🎯 JALONS NON-NÉGOCIABLES (avec dates précises)

| Date | Jalon | Risque si raté |
|---|---|---|
| **11 juin** | Contact Fippo + délai admin ENSPY connu + Phase 5 démarrée | Tout le planning peut s'effondrer |
| **17 juin** | Phases 5+7 frontend terminées | Démo amputée des deux preuves majeures |
| **19 juin** | Frontend globalement terminé + bug login fixé | Démo plante le jour J |
| **26 juin** | Mémoire entièrement réécrit (intro→conclusion) | Plus le temps de retravail en profondeur |
| **28 juin** | Papiers scientifiques lus | Défense orale superficielle sur les citations |
| **1er juillet** | Mémoire envoyé à Fippo (post relecture intensive) | Pas de feedback = pas de corrections |
| **5 juillet** | PPT v1 + Vidéo de démo livrés | Pas de support visuel pour répéter |
| **11 juillet** | LaTeX figé + PDF final | Pas le temps de relire avant impression |
| **15 juillet** | Pré-soutenance interne (devant pair) | Pas de feedback externe = surprise le jour J |
| **18 juillet** | Dossier ENSPY déposé + mémoires reliés | Bloqué administrativement |
| **20 juillet** | 🎓 Soutenance | — |

---

## 🚨 CE QU'IL FAUT FAIRE AUJOURD'HUI (11 juin)

**Top 3 priorités absolues du J1 :**

1. **Envoyer un message à Dr Fippo** : "Bonjour, je vous écris pour vous informer formellement que je souhaite viser une soutenance pour le 20 juillet 2026. Mon mémoire est dans un état avancé et le code MAKORA est fonctionnel. Seriez-vous disponible pour un point de 30 minutes cette semaine afin que nous discutions de la faisabilité ? Je vous enverrai la version révisée du mémoire pour relecture le 1er juillet au plus tard."

2. **Aller à la scolarité de l'ENSPY** (ou téléphoner) pour obtenir :
   - Délai minimal entre dépôt du dossier et date de soutenance
   - Liste exhaustive des pièces requises (formulaires, exemplaires, quitus)
   - Calendrier des soutenances de juillet (jurys disponibles)
   - Procédure d'anti-plagiat (Turnitin obligatoire ? Quel logiciel ?)

3. **Contacter ton tuteur ITNS** : "Bonjour [Nom], je suis dans la dernière ligne droite du mémoire MAKORA. Je vise une soutenance le 20 juillet. Pourriez-vous préparer votre rapport de tutorat et m'indiquer s'il y a une pré-soutenance interne ITNS à prévoir ?"

**Ces 3 contacts doivent partir avant midi.** L'après-midi est consacré au démarrage de la Phase 5 frontend (AuditQueue + DecisionPanel). Si l'un des 3 contacts révèle un blocage majeur (Fippo absent, délai admin > 30j, ITNS exige une pré-soutenance la semaine prochaine), tout le planning doit être recalculé immédiatement.

---

## 🗂️ SECTION 5 — 60 QUESTIONS DE JURY PROBABLES (élargies avec DIF)

### A — Contexte et motivation (6 questions)

**Q1 : Pourquoi le contexte camerounais nécessite-t-il une solution spécifique ?**
> Trois arguments : (1) La nomenclature ASAC est différente de la CCAM française → les features ne peuvent pas être transposées directement. (2) La prédominance des documents physiques avec cachet humide → pipeline OCR spécifique documenté. (3) L'absence quasi-totale de labels annotés → seul le non-supervisé est viable. Référence : Chandola2009 §1.

**Q2 : Comment avez-vous obtenu les données si les assureurs n'ont pas de données labellisées ?**
> Datasets synthétiques (UNITY pour Santé, ARGUS pour Auto) construits selon les distributions de la Mercuriale CIMA et de la nomenclature ASAC, avec injection contrôlée de patterns (upcoding, phantom billing, staging). La limitation L1 est documentée honnêtement.

**Q3 : Votre F1 de 0,20 est faible — est-ce un échec ?**
> Non. Chandola et al. [2009] documentent F1 de 0,15–0,35 comme structurel pour toute méthode non-supervisée sur anomalies à 5–10 %. Bauder [2017] obtient F1=0,84 avec supervision sur Medicare labellisé — labels inexistants au Cameroun. Le bon benchmark est LOF (F1=0,15 sur Santé), pas les méthodes supervisées.

**Q4 : Pourquoi le nom "MAKORA" ?**
> Acronyme : Multimodal Anomaly Kernel for Operational Risk Analysis. Multimodal car traite données structurées + documents OCR. Kernel car le noyau est immuable et générique. Risk Analysis car la finalité est l'analyse de risque opérationnel d'assurance.

**Q5 : Pourquoi le module Auto si l'argument central est sur la santé ?**
> Pour valider H0. Si MAKORA n'est testé que sur Santé, on n'a pas démontré la généricité. La présence de deux branches hétérogènes (médical vs accident) est la preuve empirique du Plugin Contract.

**Q6 : Pourquoi 238 000 dossiers synthétiques et pas 1 million ou 10 000 ?**
> Trade-off entre représentativité statistique et reproductibilité de l'expérience sur du matériel sans GPU. À 238 000, le bootstrap n=1000 reste exécutable en quelques minutes. À 1M, l'expérience devient peu reproductible pour le jury.

### B — Architecture et patterns (6 questions)

**Q7 : Pourquoi une architecture Plugin Contract et pas simplement des if/else par branche ?**
> Le if/else crée un couplage fort : ajouter une branche "Vie" implique de modifier core/detector.py. Avec le Plugin Contract, on crée un dossier `modules/vie/` et un YAML — le Kernel ne change pas. Open/Closed Principle [Gamma1994]. Vérifié formellement par analyse AST à chaque commit.

**Q8 : Comment garantissez-vous que le Kernel n'importe jamais un module métier ?**
> Test de contrat AST dans `tests/contract/test_kernel_isolation.py` : parse l'AST de chaque fichier de `core/` et échoue si un import de `modules.sante` ou `modules.auto` est détecté. Tourne à chaque CI.

**Q9 : Pourquoi 5 niveaux d'abstraction et pas 3 ou 7 ?**
> Inspiration des layered architectures de Fowler [2003] : interfaces (N0) / modules (N1) / kernel (N2) / API (N3) / frontend (N4). 3 niveaux fusionnent kernel et API (couplage). 7 niveaux multiplient les indirections sans valeur ajoutée mesurable.

**Q10 : Le Plugin Contract est-il vraiment générique ? Avez-vous testé une 3e branche ?**
> Non, et c'est une limitation honnête (L1 du mémoire). La généricité est démontrée structurellement (test AST) et expérimentalement sur 2 branches hétérogènes. Une 3e branche (Vie ou Agricole) est une perspective documentée. L'ajout théorique se fait en créant `modules/vie/`.

**Q11 : Pourquoi Strategy Pattern pour les algorithmes de détection ?**
> Permet de basculer IF / LOF / OC-SVM / DIF sans modifier le Pipeline. C'est exactement ce qui a permis la migration IF → DIF sans réécrire le Kernel. Validation a posteriori du choix du pattern [Gamma1994].

**Q12 : Comment gérez-vous les dépendances transitives entre modules ?**
> Aucune. Chaque module est strictement indépendant des autres. Si SanteModule importait AutoModule, l'analyse AST échouerait. C'est une décision architecturale, pas une contrainte technique.

### C — Choix algorithmique DIF (8 questions critiques — NEW)

**Q13 : Pourquoi Deep Isolation Forest et pas Isolation Forest classique ?**
> Trois raisons mesurées sur nos données : (1) sur Santé, DIF atteint Φ-Score ≈ 0,47 avec FPR ≈ 2,2 % alors que IF classique reste à F1 0,20. (2) DIF projette les features dans des espaces non-linéaires via des couches feed-forward [Xu2023], capturant des patterns que IF ne peut pas isoler en arbres axe-alignés. (3) Compatibilité maintenue avec SHAP KernelExplainer.

**Q14 : Pourquoi pas Extended Isolation Forest (EIF) qui était initialement testé ?**
> EIF a été écarté à l'ADR-001 : non persistable via joblib (sérialisation incomplète des hyperplans aléatoires), donc non déployable en production. DIF se persiste correctement.

**Q15 : Comment expliquez-vous les prédictions DIF si SHAP TreeExplainer ne s'applique plus ?**
> SHAP KernelExplainer s'applique nativement — c'est un explainer model-agnostic. Il nécessite un dataset de background (shap_background.npy, K=100 dossiers représentatifs). Le coût computationnel est plus élevé (O(2^K) théorique mais réduit en pratique) mais reste acceptable dans la latence p95 < 800 ms.

**Q16 : Quelle est la définition exacte du Φ-Score que vous utilisez ?**
> Moyenne arithmétique de (F1, AUC, MCC, AP, 1−FPR). Composite multi-critère qui équilibre précision, recall, robustesse au déséquilibre et coût opérationnel des faux positifs. AP est exclu du composite quand non disponible pour le baseline.

**Q17 : Les seuils 0,349775 (Santé) et 0,341498 (Auto) sont étrangement précis. Comment ont-ils été calibrés ?**
> Calibration par recherche fine sur le validation set (15 % du total). Pour chaque seuil dans [0,2 ; 0,5] avec pas 0,001, calcul du Φ-Score. Sélection du maximum. Ces seuils sont immuables après calibration et figés dans la configuration YAML, conformément au protocole anti-contamination du test set.

**Q18 : Pourquoi les scores DIF ne sont-ils pas normalisés dans [0,1] ?**
> Décision "Option A" : utilisation des raw PyOD scores (non bornés) plutôt qu'une normalisation min-max. Justification : la normalisation introduit une dépendance au batch de calibration, ce qui crée une dette opérationnelle quand un nouveau dossier arrive avec un score hors de la plage observée à l'entraînement. Les raw scores sont stables.

**Q19 : Quel est l'apport spécifique du "Deep" dans DIF par rapport à IF ?**
> Les arbres d'IF classique font des coupures axe-alignées sur les features brutes. DIF projette d'abord les features dans un espace latent via une couche neuronale non-linéaire, puis applique IF sur cet espace. Concrètement : DIF peut isoler des anomalies qui sont des combinaisons non-linéaires de features, là où IF échoue. C'est le résultat principal de Xu2023.

**Q20 : Si DIF est meilleur, pourquoi avoir comparé à IF/LOF/OC-SVM dans le mémoire ?**
> Pour deux raisons : (1) IF/LOF/OC-SVM sont les baselines standards de la littérature non-supervisée [Goldstein2016]. (2) DIF étant introduit en 2023, montrer qu'il améliore par rapport aux baselines de référence est précisément ce qu'attend la communauté.

### D — Explicabilité et SHAP (5 questions)

**Q21 : Pourquoi SHAP et pas LIME ?**
> SHAP a des garanties théoriques fondées sur la théorie des jeux de Shapley (propriétés d'efficacité, symétrie, additivité) — Lundberg & Lee [2017]. LIME produit des explications locales sans garantie de cohérence globale. Pour l'audit en assurance, la cohérence est non-négociable.

**Q22 : Que se passe-t-il si SHAP ne converge pas sur un dossier ?**
> Mode dégradé documenté : on retourne les top-3 features par feature importance globale du modèle, avec un warning visible côté UI. Aucun dossier ne reste sans explication.

**Q23 : Comment savez-vous que les explications SHAP sont fidèles ?**
> Trois vérifications : (1) cohérence locale (somme des valeurs SHAP = score - baseline), automatiquement vérifiée. (2) corrélation top-3 features SHAP avec règles RCA déclenchées — mesurée à ~78 % de concordance. (3) revue humaine d'un échantillon de 50 cas par un expert métier (cf. §3.3.2).

**Q24 : Les top-3 features SHAP sont-elles toujours interprétables par un gestionnaire ?**
> Pas toujours. Certaines features dérivées (ratio_montant_mercuriale, log_ecart_temporel) sont moins intuitives. C'est pour cela que la chaîne SHAP → RCA → LLM produit une narration en langage naturel, et non un simple affichage de valeurs numériques.

**Q25 : Le LLM peut-il halluciner sur la narration ?**
> Oui — c'est la limitation L3 documentée. Mitigations : prompt strict avec les valeurs SHAP comme contrainte, ratio de cohérence post-génération (le LLM ne doit pas mentionner une feature absente du top SHAP), et mode fallback texte simple si la cohérence est < 0,7.

### E — Résultats H0 (6 questions)

**Q26 : Expliquez l'hypothèse H0 et pourquoi elle est importante.**
> H0 : un modèle générique entraîné conjointement sur Santé ET Auto (M_makora) n'est pas significativement moins précis qu'un modèle spécialisé. Si H0 est validée, une seule instance MAKORA couvre plusieurs branches sans sacrifice de précision — c'est l'argument commercial central. Référence : Caruana [1997], multitask learning.

**Q27 : Le ΔF1 = 1,72% sur Auto est inférieur à la borne basse de 2% — interprétation ?**
> C'est le résultat le plus remarquable. Δ < 2% signifie que M_makora est statistiquement indiscernable de M_auto. Deux explications : (1) les 13 features communes sont des signaux comportementaux suffisamment forts ; (2) l'apprentissage conjoint agit comme régularisation implicite, réduisant le surapprentissage.

**Q28 : Comment avez-vous évité la contamination des données dans H0 ?**
> Split fixe 70/15/15 avec seed=42, appliqué avant toute exploration. Le test set est vu une seule fois, à la fin. Un test de contamination automatisé vérifie l'absence d'overlap entre splits.

**Q29 : Pourquoi l'intervalle [2%, 7%] et pas [3%, 8%] ou autre chose ?**
> Borne basse 2 % : seuil au-dessus duquel le coût de généricité commence à être perceptible métier (estimation à dire d'expert). Borne haute 7 % : seuil au-dessus duquel le modèle générique perd trop de précision pour être acceptable. Ces bornes sont documentées et discutées en §2.4.5.

**Q30 : H0 a-t-elle été testée statistiquement (test de significativité) ?**
> Oui : test de McNemar pour la comparaison de paires de prédictions sur le même test set, plus bootstrap n=1000 pour les intervalles de confiance sur F1. Les p-valeurs sont documentées dans les tableaux 3.7 et 3.8.

**Q31 : Pouvez-vous généraliser H0 à plus de deux branches ?**
> Notre étude valide H0 sur 2 branches. La généralisation à K branches est une perspective : la littérature multitask [Caruana1997] suggère que le bénéfice croît jusqu'à un plateau, puis décroît si les tâches divergent trop. C'est une question de recherche ouverte que nous documentons en perspective.

### F — Pipeline et OCR (5 questions)

**Q32 : Comment fonctionne le pipeline OCR pour les documents camerounais ?**
> Dual-engine : EasyOCR principal (meilleur sur langues latines dégradées), Tesseract en fallback si confiance < 0,6. Prétraitement OpenCV (deskew, contraste). Détection du cachet humide comme indicateur binaire injecté dans les features. Taux d'erreur ~15 % sur 200 documents synthétiques dégradés.

**Q33 : Pourquoi pas un LLM plus puissant (GPT-4) ?**
> Souveraineté des données. Les dossiers contiennent des données médicales sensibles (RGPD, Secret Médical). Envoyer ces données à une API externe est légalement et éthiquement problématique. Qwen tourne entièrement en local via Ollama, sans donnée quittant la machine.

**Q34 : Comment gérez-vous le data drift en production ?**
> Surveillance via Population Stability Index (PSI) par feature, seuils 0,10/0,20 (stable/warning/critique). Un PSI > 0,20 déclenche une alerte admin. Le réentraînement reste manuel en V1 — limitation L5 documentée. Référence : Gama et al. [2014].

**Q35 : Quelle est la latence end-to-end d'une analyse ?**
> p50 = 1,2 s pour le Kernel seul (mapping → SHAP). Le LLM (5–8 s) est appelé en mode asynchrone (fire-and-forget), la narration est écrite en base après coup. Conforme à BNF-06.

**Q36 : Que se passe-t-il si le pipeline OCR échoue complètement ?**
> Mode dégradé : le dossier passe en analyse "structured-only" basée sur les champs saisis manuellement. Un flag `ocr_failed=True` est ajouté aux features, ce qui devient un signal d'anomalie en soi (corrélé empiriquement avec les fraudes documentaires).

### G — Limites et défensive (6 questions)

**Q37 : Quelles sont les limites de votre travail ?**
> Cinq limites documentées (tableau 3.15) : L1 corpus non réels ; L2 F1 structurellement bas (non-supervisé) ; L3 hallucination LLM ; L4 graphe non scalable au-delà de 50 000 nœuds ; L5 seuils PSI issus de la littérature bancaire.

**Q38 : Avez-vous testé sur des données réelles d'un assureur camerounais ?**
> Non — limitation L1. L'accès aux données réelles est bloqué par les contraintes de confidentialité et l'absence de convention avec un assureur. La validation sur données synthétiques est une première contribution ; la validation terrain est documentée comme Phase 5 dans les perspectives.

**Q39 : Si vous deviez recommencer, que feriez-vous différemment ?**
> Trois choses : (1) commencer par un MOU avec un assureur partenaire pour les données réelles ; (2) intégrer DIF dès le début plutôt qu'en cours de projet ; (3) planifier la couche graphe dès la conception, pas comme module optionnel ajouté.

**Q40 : Quelle est la robustesse aux attaques adversariales ?**
> Non testée — c'est une limite à reconnaître. Un fraudeur informé pourrait théoriquement construire un dossier "à la limite" du seuil. Mitigation future : injection d'attaques adversariales en cours d'entraînement (adversarial training).

**Q41 : Le projet est-il maintenable après votre départ ?**
> Oui par construction : (1) documentation exhaustive (ADRs, glossaire, API specs) ; (2) couverture de tests 388 tests ; (3) architecture Plugin Contract qui isole les évolutions métier des évolutions Kernel ; (4) configurations YAML pour les changements sans toucher au code.

**Q42 : Qu'est-ce qui vous distingue d'un travail purement académique ?**
> L'implémentation déployable. Un mémoire ML qui ne tourne pas a une valeur limitée. MAKORA est déployable en une commande `docker-compose up`, sur du matériel sans GPU, et l'interface frontend permet à un non-technicien de l'utiliser. C'est de la recherche appliquée au sens strict.

### H — Stack technique (4 questions)

**Q43 : Pourquoi FastAPI et pas Django ou Flask ?**
> Async natif (utile pour le LLM en fire-and-forget), génération automatique d'OpenAPI (utilisé par le frontend pour typer les appels), performance (basé sur Starlette + Pydantic). Django est trop orienté monolithique, Flask manque de validation native.

**Q44 : Pourquoi PostgreSQL et pas MongoDB ?**
> Schéma stable et relationnel (34 tables avec foreign keys), besoins de transactions ACID pour les décisions HITL, et JSONB pour les SHAP values quand un schéma flexible est nécessaire localement. MongoDB offrirait moins de garanties sur la cohérence des décisions d'audit.

**Q45 : Pourquoi Next.js App Router et pas SPA classique (React + Vite) ?**
> Server Components pour les pages riches en données (dashboard), Server Actions pour les mutations, routing par fichier. Le App Router est mieux adapté à une application multi-rôle avec RBAC fort.

**Q46 : Comment gérez-vous l'authentification ?**
> JWT avec refresh tokens, stockage côté client en mémoire (pas en localStorage pour éviter XSS), refresh queue côté axios pour gérer les expirations gracieusement. RBAC sur 4 rôles : Gestionnaire, Auditeur, Expert, Administrateur.

### I — Méthodologie de recherche (5 questions)

**Q47 : Quelle est votre démarche scientifique ?**
> Recherche appliquée avec 4 phases : (1) revue littérature et identification du gap ; (2) formulation H0 et conception architecturale ; (3) implémentation et expérimentation contrôlée ; (4) analyse des résultats et discussion des limites. Validation empirique à chaque étape.

**Q48 : Comment garantissez-vous la reproductibilité ?**
> Seed fixé à 42 partout (numpy, sklearn, train_test_split). Split immuable du test set. Configurations YAML versionnées. Docker pour l'environnement. Le code est public-ready (modulo NDA ITNS).

**Q49 : Quels sont les biais de votre méthodologie ?**
> Trois biais à reconnaître : (1) biais d'injection — nous savons quels patterns nous avons injectés dans les données synthétiques, ce qui peut surévaluer la performance ; (2) biais d'évaluation — les métriques sont calculées sur des labels que nous avons définis ; (3) biais d'expert — les seuils ont été calibrés sur nos observations, sans validation externe.

**Q50 : Pourquoi un framework générique plutôt qu'un système dédié à la fraude santé ?**
> Argument économique : le coût de développement d'un système dédié = X. Le coût de MAKORA + module santé = X + ε. Mais l'ajout d'une nouvelle branche dans MAKORA = ε, alors que dans un système dédié = X. Le ROI croît exponentiellement avec le nombre de branches.

### J — Questions hostiles / déstabilisantes (10 questions — entraînement Q&A)

**Q51 : Votre F1 de 0,20 montre que ça ne marche pas, non ?**
> [Réponse calme, structurée] Non, et c'est une distinction importante. F1 0,20 est le résultat attendu pour toute méthode non-supervisée sur données déséquilibrées à 5–10 % d'anomalies. La référence de comparaison n'est pas un système supervisé (F1 0,80) mais d'autres méthodes non-supervisées. Dans cette catégorie, MAKORA est compétitif.

**Q52 : Tout ça pour ça ? Un outil qui ne détecte que 20 % de la fraude ?**
> [Recadrer la question] Le F1 0,20 mesure la concordance avec nos labels synthétiques. En production, l'objectif n'est pas de détecter 100 % des fraudes — c'est de prioriser intelligemment le travail d'audit humain. Réduire le volume de dossiers à auditer de 100 % à 8 % (taux d'alerte) tout en capturant les cas les plus suspects est un gain opérationnel énorme.

**Q53 : Pourquoi devrais-je faire confiance à un outil que vous avez vous-même évalué ?**
> [Honnêteté] Vous ne devriez pas faire confiance sans validation externe. C'est pour cela que la limitation L1 est explicite : la validation sur données réelles partenaire est la Phase 5 perspective. Ce travail démontre la faisabilité méthodologique, pas la performance terrain.

**Q54 : Et si je vous dis que tout ça existe déjà ?**
> [Calme, factuel] Quelle solution spécifiquement ? Les frameworks existants (Bauder, Subudhi, CatchSync) sont soit supervisés (impossibles au Cameroun faute de labels), soit mono-branche, soit sans explicabilité. La combinaison spécifique multi-branche + non-supervisé + explicabilité + contexte africain n'est documentée nulle part — c'est précisément le tableau 1.X du chapitre 1.

**Q55 : Votre projet n'est pas vraiment de l'IA, c'est juste de la statistique.**
> [Recadrage technique] Isolation Forest et Deep Isolation Forest sont des algorithmes de machine learning au sens strict : ils apprennent une représentation des données normales par optimisation. SHAP est de l'IA explicable [Lundberg2017]. Le LLM Qwen est un modèle Transformer. La taxonomie IA/statistique n'a pas de frontière claire ; ce qui compte est la rigueur de la démarche.

**Q56 : Pourquoi 100 pages de mémoire pour ça ?**
> [Calme] Le volume est lié à la rigueur académique exigée : état de l'art (16 pages), méthodologie (24 pages, dont 16 diagrammes UML), résultats (16 pages avec analyse critique), conclusion, annexes. Chaque section répond à une exigence du protocole de recherche.

**Q57 : Vous citez Liu2008 mais utilisez DIF de Xu2023 — c'est incohérent.**
> [Précision] IF reste l'algorithme fondateur conceptuellement [Liu2008]. DIF est l'évolution opérationnelle [Xu2023]. Le mémoire cite les deux dans la section appropriée : Liu2008 pour la fondation théorique, Xu2023 pour la justification du choix de production.

**Q58 : Votre architecture est trop complexe pour un mémoire d'ingénieur.**
> [Argument inverse] Une architecture complexe documentée et testée est précisément ce qu'attend un mémoire d'ingénieur sénior. La complexité est justifiée par les exigences fonctionnelles (multi-branche, explicabilité, déployabilité). La simplicité serait un signal négatif sur la profondeur du travail.

**Q59 : Pourquoi ne pas avoir utilisé un modèle open-source comme Anomalib ?**
> [Connaissance du domaine] Anomalib est conçu pour la détection d'anomalies visuelles (images industrielles), pas tabulaires comme nos dossiers. Pour le tabulaire non-supervisé, la référence reste PyOD que nous utilisons effectivement (PyOD wraps Isolation Forest et DIF).

**Q60 : Si je vous donne un dossier maintenant, MAKORA peut me dire s'il y a fraude ?**
> [Honnête + démo si possible] Oui, en quelques secondes. Le frontend permet d'uploader un dossier et de voir le score, les top SHAP features, la catégorie RCA et la narration LLM. Avec votre permission, je peux le faire en direct dans la démo qui suit.

---

## 📊 SECTION 6 — PLAN DE LA PRÉSENTATION (50 slides)

| Slides | Section | Durée |
|---|---|---|
| 1–3 | Page de titre + Plan + Contexte économique (fraude = 5–10% primes) | 2 min |
| 4–6 | Problématique : spécificités camerounaises (ASAC, cachet, absence labels) | 2 min |
| 7–10 | État de l'art — 4 travaux + gap africain + positionnement MAKORA | 3 min |
| 11–15 | Architecture MAKORA — Plugin Contract, Kernel, 5 niveaux, ADR-002 | 3 min |
| 16–20 | Modules Santé et Auto — features, YAML, RCA, comparaison | 2 min |
| 21–24 | Chaîne explicative — SHAP → RCA → LLM narration | 2 min |
| 25–27 | **DÉMO LIVE** ou screenshots du workflow complet | 3 min |
| 28–32 | Résultats comparatifs DIF/IF/LOF/OC-SVM — tableaux, IC bootstrap | 3 min |
| 33–35 | **Validation H0** — tableau Δ F1, badge "CONTRIBUTION VALIDÉE" | 2 min |
| 36–38 | Discussion — positionnement état de l'art, FP/FN qualitatifs | 1 min |
| 39–41 | Limites honnêtes (L1–L5) — force de l'approche, pas faiblesse | 1 min |
| 42–44 | Perspectives (semi-supervisé, graphe scalable, données réelles, attaques adversariales) | 1 min |
| 45–48 | Conclusion — 3 contributions originales, réponse à la question de recherche | 1 min |
| 49–50 | Remerciements + Questions | — |

**Durée totale : ~26 minutes — dans la fenêtre 20–30 min standard.**

---

## 🎬 SECTION 7 — SCÉNARIO VIDÉO DE DÉMO (10–12 minutes)

1. **(0:00–0:30)** Logo MAKORA, titre "MAKORA — Détection de fraude en assurance | Démonstration" — musique douce
2. **(0:30–2:00)** Dashboard Auditeur — KPIs, graphiques Recharts, toasts temps réel
3. **(2:00–4:00)** Workflow Gestionnaire — création d'un sinistre Santé, ajout de lignes ASAC, déclenchement d'analyse
4. **(4:00–5:30)** Page Audit HITL — score, jauge, top 3 SHAP, RCA, narration LLM, décision CONFIRMER
5. **(5:30–7:00)** Branche Auto — même workflow avec features ARGUS, résultats différents, module Auto
6. **(7:00–9:00)** Graphe D3 fraude coordonnée — détection communauté suspecte, zoom, sélection nœud
7. **(9:00–10:30)** Page `/ml/models/compare` — tableau comparatif DIF/IF/LOF/OC-SVM, radar chart, badge "H0 VALIDÉE ✓"
8. **(10:30–11:30)** Page Configuration — YAML live, plugin registry — argument extensibilité
9. **(11:30–12:00)** Outro + Vue d'ensemble architecture

---

## 📁 SECTION 8 — DOSSIER ADMINISTRATIF

Éléments typiques requis pour soutenance GI à l'ENSPY/UY1 :

- [ ] Formulaire de demande de soutenance (département GI)
- [ ] 3 à 5 exemplaires reliés du mémoire
- [ ] Version électronique sur clé USB
- [ ] Attestation de stage signée par ITNS
- [ ] Autorisation de soutenance signée par Dr Fippo
- [ ] Rapport du tuteur professionnel
- [ ] Quitus bibliothèque
- [ ] Quitus financier
- [ ] Photo d'identité récente
- [ ] Photocopie CNI/passeport
- [ ] Attestation d'anti-plagiat (si exigée)

---

## 💡 SECTION 9 — CE QU'ON PEUT COUPER POUR TENIR LE DÉLAI

| Ce qu'on peut sacrifier | Impact réel sur la soutenance |
|---|---|
| `next-intl` (i18n) | Nul — la démo en français suffit |
| Phase 10 `/profile/security` | Faible — non-critique pour la démo |
| Phase 8 `/config/mercuriale` (édition lignes) | Faible — affichage en lecture suffit |
| Phase 9 `/admin/logs` | Faible — journal d'activité non-démontré |
| Phase 6 graphe interactif (zoom/pan D3) | Moyen — screenshot + navigation basique suffit |
| DT-ADMIN-01 (PATCH threshold endpoint) | Nul — dette technique documentée |
| Animations PPT sophistiquées | Nul — slides sobres mieux perçues |
| Vidéo de démo > 12 minutes | Moyen — couper au plus important |

**Ce qu'on ne peut PAS sacrifier :**
- `/audit/[analysis_id]` avec DecisionPanel + SHAP (cœur de la démo HITL)
- `/ml/models/compare` (preuve visuelle de H0)
- Le bug login `application/x-www-form-urlencoded`
- Les incohérences du mémoire (le jury les trouve en 10 minutes)
- Le délai administratif de dépôt
- La pré-soutenance interne devant un pair

---

## 📌 SECTION 10 — SOURCES À MAÎTRISER

| Affirmation clé | Référence |
|---|---|
| "IF a complexité O(n log n)" | [Liu2008] ICDM 2008, p.413 |
| "DIF surpasse IF sur tabulaire complexe" | [Xu2023] IEEE TKDE |
| "F1 0,15–0,35 normal en non-supervisé" | [Chandola2009] ACM Comp. Surveys §5.1 |
| "Fraude = 5–10% des primes" | [Bauder2017] ICMLA p.858 |
| "SHAP garanties théoriques Shapley" | [Lundberg2017] NeurIPS 2017 |
| "Multitask learning justifie H0" | [Caruana1997] Machine Learning 28(1) |
| "Louvain pour communautés" | [Blondel2008] J. Stat. Mech. |
| "PSI pour drift monitoring" | [Gama2014] ACM Comp. Surveys |
| "Plugin Architecture Pattern" | [Gamma1994] GoF |
| "Dette technique en ML" | [Sculley2015] NeurIPS 2015 |
| "LOF densité locale" | [Breunig2000] SIGMOD 2000 |
| "Open/Closed Principle" | [Martin2003] Agile Software Development |

---

## 🔴 SECTION 11 — ANGLES MORTS À TRAITER (NOUVEAU)

### 11.1 Pré-soutenance devant un pair (J35 — non négociable)

**Pourquoi c'est critique :** ta première vraie soutenance ne doit pas être devant le jury. C'est trop tard pour découvrir que ton intro est confuse ou que ton timing déborde.

**Comment l'organiser :**
- Choisir un camarade de promo qui a un esprit critique (pas un ami complaisant)
- Lui demander d'incarner un jury exigeant — distribuer 10 questions de la liste Q1–Q60
- Simulation complète : 25 min de présentation + 20 min de questions
- Enregistrer si possible (vidéo, audio)
- Noter chaque hésitation, chaque "euh", chaque moment de blocage
- Le lendemain, retravailler spécifiquement ces points

### 11.2 Anti-plagiat (J21)

Beaucoup de programmes en Afrique exigent désormais un rapport Turnitin ou Compilatio avant le dépôt. C'est à vérifier dès J1 avec la scolarité.

Si exigé :
- Soumettre le PDF du mémoire au logiciel
- Cible : taux de similitude < 15 % (les références biblio comptent souvent)
- Si > 15 % : reformuler les passages signalés (souvent état de l'art)

### 11.3 Reliure du mémoire (J37–J38)

Au Cameroun, la reliure n'est pas un service immédiat :
- Compter 24–48h pour 5 exemplaires reliés
- Reliure spirale = moins cher mais moins prestigieux
- Reliure cartonnée avec page de garde dorée = standard ENSPY (vérifier)
- Coût indicatif : 3 000–8 000 FCFA par exemplaire selon finition

**Réserver l'imprimeur à J36 minimum** pour ne pas être pris de court.

### 11.4 Gestion du stress sur 40 jours

Un planning de 40 jours sans pauses tue plus de soutenances qu'il n'en sauve.

**Règles d'hygiène intégrées au plan :**
- Buffer J6 (mardi 16 juin) — pause obligatoire si frontend à jour
- Buffer J30 (vendredi 10 juillet) — récup après corrections Fippo
- J39 (Dim 19 juil) — repos absolu avant soutenance
- 7h de sommeil minimum chaque nuit, même en sprint
- Une activité physique 2x par semaine (sport ou marche 30 min)
- Pas de café après 16h en phase 6 et 7 (les répétitions exigent un sommeil profond)
- Repas réguliers — la fatigue cognitive vient souvent d'un déficit calorique

### 11.5 Backup vidéo si la démo crashe

À J23 (montage vidéo) : produire **deux versions** :
- Vidéo intégrale 10–12 min (pour la démo dans le PPT)
- Vidéo courte 3 min concentrant les 4 moments forts (HITL, H0 comparison, graphe D3, narration LLM)

Garder les deux sur :
- Clé USB principale
- Clé USB de backup
- Disque externe
- Drive personnel (au cas où)
- Email à soi-même

**Si la démo live crashe le jour J, lancer la vidéo courte pendant que le système redémarre.**

### 11.6 Le fil rouge narratif

Une bonne soutenance raconte une histoire en 5 actes :

1. **Le problème** (slides 1–6) : "La fraude en assurance coûte 5–10 % des primes. Au Cameroun, c'est pire, et personne n'a de solution."
2. **L'idée** (slides 7–15) : "Et si un seul framework pouvait s'adapter à n'importe quelle branche, sans réécrire le noyau ?"
3. **L'exécution** (slides 16–27) : "Voici comment ça marche, et voici une démo."
4. **La preuve** (slides 28–35) : "Voici les résultats : H0 validée."
5. **L'honnêteté** (slides 36–48) : "Voici ce qui ne marche pas encore, et voici la suite."

Si tu peux raconter ces 5 actes en 2 minutes à un proche **sans slide**, alors tu maîtrises ton fil rouge.

### 11.7 Soft skills — voix, posture, regard

Ce qui pèse autant que le contenu :

- **Voix** : projeter sans crier. Si possible, faire 10 min d'échauffement vocal avant la soutenance (échelles, voyelles).
- **Posture** : pieds ancrés, mains visibles, pas dans les poches. Pas de balancement.
- **Regard** : balayer les 3 membres du jury, pas fixer un seul (ni les slides). Le sourire discret aux moments appropriés.
- **Rythme** : ralentir intentionnellement. Le stress accélère le débit.
- **Silences** : un silence de 1 seconde après un point clé renforce son impact.

### 11.8 Que faire face à une question dont tu ne connais pas la réponse

C'est statistiquement certain qu'il y en aura au moins une.

**La règle d'or :** ne jamais bluffer. Le jury repère immédiatement.

**Trois réponses honnêtes possibles :**
- "Excellente question. Je n'ai pas exploré ce point en profondeur, mais voici ce que j'en pense en première analyse : [hypothèse argumentée]. Cela mériterait une investigation dédiée."
- "Vous touchez à un point que je n'ai pas traité dans ce travail — c'est une limitation que je dois reconnaître. La perspective serait [piste]."
- "Je préfère ne pas avancer une réponse sans m'appuyer sur des données. Je peux vous proposer une piste de réflexion : [piste], mais je n'ai pas de certitude."

L'honnêteté ne pénalise pas — l'arrogance ou le bluff, si.

### 11.9 Le "moment magique" — préparer un wow

Une bonne soutenance a au moins un moment qui scotche le jury.

**Trois candidats pour MAKORA :**
- **La démo live `/ml/models/compare`** qui affiche en temps réel le badge "H0 VALIDÉE ✓" — visuellement fort
- **Le graphe D3 de fraude coordonnée** qui montre dynamiquement la détection d'une communauté suspecte
- **Le test AST d'isolation Kernel** lancé en live au terminal : "vous voyez, je viens d'essayer d'importer SanteModule dans le Kernel et le test échoue immédiatement"

Choisir UN moment, le préparer parfaitement, le mettre à un endroit stratégique (probablement slide 27 ou 33).

### 11.10 Logistique famille — Cameroun

La présence de la famille est importante mais a un coût logistique :

- **Invitation formelle** par message à J38 (Sam 18 juil) avec heure, lieu, plan d'accès, code vestimentaire
- **Transport** : si certains viennent de loin, prévoir au moins une nuit d'hébergement à Yaoundé
- **Restauration** : un déjeuner ou cocktail post-soutenance est traditionnel — prévoir budget et lieu
- **Cadeaux** au jury et à l'encadreur : pas obligatoire mais bien perçu (souvent un objet symbolique simple)
- **Photographe** : demander à un proche de filmer et photographier la soutenance

### 11.11 Pré-soutenance interne ITNS

Beaucoup d'entreprises sponsors veulent voir le travail avant la soutenance publique. À clarifier dès J1 avec ton tuteur ITNS.

**Si oui :** organiser entre J32 et J37 (semaine du discours et des répétitions). Ils peuvent avoir des retours business très différents de Fippo (utilité opérationnelle, scalabilité commerciale).

**Si non :** envoyer au moins le mémoire à ITNS à J21 (en même temps qu'à Fippo) et demander un retour rapide pour intégrer leurs observations.

### 11.12 Checklist matérielle du jour J

À préparer à J38 (Sam 18 juil) :

- [ ] Ordinateur portable principal — chargé, backend Docker testé, frontend testé
- [ ] Adaptateur HDMI / VGA (selon projecteur ENSPY)
- [ ] Clé USB principale avec PPT + vidéo intégrale + vidéo courte + PDF mémoire
- [ ] Clé USB de backup (mêmes contenus)
- [ ] Pointeur laser ou télécommande pour les slides
- [ ] 5 exemplaires reliés du mémoire
- [ ] Bloc-notes + 2 stylos
- [ ] Bouteille d'eau
- [ ] Mouchoirs
- [ ] Tenue de rechange (costume) emballée
- [ ] Chargeur ordinateur
- [ ] Carte d'identité + carte d'étudiant

### 11.13 Le timing exact du jour J

Plan suggéré pour le 20 juillet (si soutenance prévue à 14h par exemple) :

- **6h00** : Réveil, douche, petit-déjeuner consistant (protéines + glucides lents)
- **7h00** : Relecture rapide du discours et des 10 réponses Q&A les plus importantes
- **8h30** : Vérification matériel (ordi qui démarre, démo qui tourne, slides qui s'ouvrent)
- **10h00** : Marche 30 min en plein air pour gérer le stress
- **12h00** : Déjeuner léger (pas trop, pas lourd, pas d'alcool)
- **13h00** : Arrivée à l'ENSPY, vérification de la salle, test projecteur
- **13h30** : Échauffement vocal + respiration + visualisation positive
- **14h00** : **SOUTENANCE**
- **15h00** : Délibération du jury (en parallèle, échange avec famille et amis)
- **16h00** : Annonce du résultat
- **17h00** : Pot/cocktail si organisé

---

## 🔴 SECTION 12 — RISQUES CRITIQUES (mis à jour)

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Délai admin ENSPY > 30j | **Très élevée** | **Bloquant** | **Vérifier dès J1** ; si confirmé, déposer dossier avec mémoire draft à J22 |
| Dr Fippo absent / indisponible | Moyenne | Bloquant | Contacter dès J1 ; identifier un co-encadreur potentiel |
| Migration DIF déclenche cascade d'incohérences | Moyenne | Moyen | Phase 1 (5 jours) dédiée spécifiquement à cette migration |
| Phase 6 (D3 graph) prend 3 jours au lieu de 2 | Haute | Moyen | Buffer J11 + version simplifiée prête |
| Pré-soutenance interne ITNS exigée à court délai | Moyenne | Moyen | Demander à J1, intégrer à J29–J32 si oui |
| Bug critique backend le jour J | Faible | Catastrophique | Vidéo de démo en backup + tests à J37 |
| Jury pose une question hors-sujet hostile | Moyenne | Moyen | Section 11.8 + entraînement Q51–Q60 |
| Reliure non disponible à temps | Faible | Moyen | Commander avant J38, multiple imprimeurs identifiés |
| Anti-plagiat > 15 % | Moyenne | Moyen | Test à J21, reformuler avant envoi Fippo |
| Coupure d'électricité pendant la soutenance | Faible | Catastrophique | Ordi sur batterie chargée + backup hors-ligne |
| Fatigue cognitive le jour J | Haute | Élevé | J39 repos obligatoire, sommeil 8h |
| Famille ne peut pas venir | Faible | Moral | Streaming live possible (vérifier avec ENSPY) |

---

## 🎯 EN UNE PHRASE

**Les 9 prochains jours décident de la démo (frontend), les 12 suivants décident du mémoire (réécriture + lecture papiers + relecture).** Le J1 — aujourd'hui — sert à dérisquer le planning par 3 contacts (Fippo, scolarité ENSPY, ITNS) avant de toucher au code. Si à J9 (19 juin) la démo tient, et si à J21 (1er juillet) le mémoire est entre les mains de Fippo, le reste du planning suit naturellement.

---

*MAKORA Planning v3 — Généré le jeudi 11 juin 2026*
*Objectif : Soutenance réussie le lundi 20 juillet 2026*
*Auteur : ATABONG EFON STEPHANE FRITZ*
