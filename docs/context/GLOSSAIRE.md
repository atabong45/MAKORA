# GLOSSAIRE.md
## MAKORA Framework — Glossaire technique et métier
> Version orientée développement — pour que l'IA génère du code métier pertinent.
> Dernière mise à jour : 17 avril 2026 — Phase 0

---

## TERMES MÉTIER ASSURANCE

| Terme | Définition technique | Impact sur le code |
|---|---|---|
| **AMO** | Assurance Maladie Obligatoire — régime de base SS | Champ `Part_AMO` dans le dataset |
| **AMC** | Assurance Maladie Complémentaire — mutuelle privée | Champ `Part_AMC` dans le dataset |
| **ASAC** | Association des Sociétés d'Assurance du Cameroun — définit la nomenclature des actes CM | `Code_Acte` au format ASAC pour les dossiers CM |
| **BIA** | Bulletin Individuel d'Adhésion — formulaire papier CM | Source flux documentaire, pipeline OCR |
| **BEAC** | Banque des États de l'Afrique Centrale | Référence pour taux de change XAF |
| **CCAM** | Classification Commune des Actes Médicaux — >7000 codes actes FR | `Code_Acte` au format CCAM pour les dossiers FR |
| **CIMA** | Conférence Interafricaine des Marchés d'Assurance | Référentiel tarifaire `Prix_Reference_Mercuriale` pour CM |
| **Contamination** | Paramètre IF — proportion estimée d'anomalies | `IsolationForest(contamination=0.08)` |
| **Data Drift** | Dérive distribution données production vs entraînement | `drift_monitor.py` — PSI > 0.2 = alerte |
| **eIDAS** | Standard signature électronique européen | Contexte enrôlement FR uniquement |
| **FHIR R4** | Standard HL7 — format données de santé | Inspiration schéma universel, Synthea output |
| **ICD-10** | Classification OMS des diagnostics médicaux | Champ `Diagnostic_ICD10` — croisement avec `Code_Acte` |
| **Mercuriale CIMA** | Référentiel tarifaire officiel zone CIMA | `Prix_Reference_Mercuriale` pour calcul `ratio_prix_mercuriale` |
| **Mobile Money** | Paiement mobile (Orange/MTN) — canal remboursement CM | Canal de paiement sinistres CM |
| **NOEMIE** | Norme échange données SS France | Format source flux structuré FR — mapping YAML `noemie_api` |
| **OCR** | Optical Character Recognition | `vision/ocr_pipeline.py` — Tesseract + OpenCV |
| **PSI** | Population Stability Index — métrique drift | PSI < 0.1 stable, 0.1-0.2 warning, > 0.2 critique |
| **RCA** | Root Cause Analysis — diagnostic cause racine | `core/rca_engine.py` — output : catégorie + sous-catégorie |
| **RPPS** | Répertoire Partagé des Professionnels de Santé — identifiant praticien FR | Champ `RPPS_Agrement` pour dossiers FR |
| **SHAP** | SHapley Additive exPlanations — explicabilité ML | `core/explainer.py` — TreeExplainer sur Isolation Forest |
| **SNDS** | Système National Données de Santé — référentiel prix FR | Source `Prix_Reference_Mercuriale` pour dossiers FR |
| **Tiers-payant** | Paiement direct assureur → prestataire (sans avance de frais) | Mode de règlement fréquent en Santé CM |
| **XAF** | Franc CFA zone CEMAC — devise Cameroun | `Devise = "XAF"`, taux de change `EUR/XAF ≈ 655.957` |

---

## TERMES TECHNIQUES MAKORA

| Terme | Définition |
|---|---|
| **BaseModule** | Classe abstraite Python que tout module doit implémenter — `core/base_module.py` |
| **Kernel** | Le moteur central MAKORA — jamais modifié pour ajouter un module |
| **Plugin Contract** | Contrat formel = 1 YAML + 1 classe Python héritant de BaseModule |
| **Dataset Universel** | Schéma de données commun à tous les modules — format Parquet |
| **Moteur d'injection** | `manager.py` — injecte les 23 scénarios d'anomalies avec étanchéité |
| **Jitter ±5%** | Bruit aléatoire sur les prix de référence pour éviter l'overfitting |
| **ADR** | Architecture Decision Record — décision architecturale tracée dans `ARCHITECTURE.md` |
| **Human-in-the-loop** | Validation humaine obligatoire avant toute décision finale |
| **Fallback narration** | Narration template si Mistral 7B indisponible — `llm_narrator.py` |
| **Étanchéité anomalies** | 1 dossier = 1 seul type d'anomalie injecté — garanti par `manager.py` |

---

## VALEURS DE RÉFÉRENCE À CONNAÎTRE

```python
# Constantes à utiliser dans le code — NE PAS coder en dur dans la logique métier
# Toujours lire depuis la config YAML ou les referentials/

TAUX_EUR_XAF_FALLBACK = 655.957       # Taux de change fallback (si API indisponible)
CONTAMINATION_DEFAULT = 0.08           # 8% d'anomalies par défaut
PSI_WARNING_THRESHOLD = 0.10           # PSI alerte légère
PSI_CRITICAL_THRESHOLD = 0.20          # PSI alerte critique
OCR_CONFIDENCE_MIN = 0.50              # Score OCR minimum acceptable
ANOMALY_SCORE_ALERT_DEFAULT = 0.70     # Seuil alerte anomalie par défaut
RANDOM_STATE = 42                      # Seed universel pour reproductibilité
MAX_FEATURES_ISOLATION_FOREST = 20     # Limite pertinence IF (au-delà = dégradation)
```

---

*Fin du fichier GLOSSAIRE.md*
