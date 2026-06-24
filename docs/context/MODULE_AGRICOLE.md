# MODULE_AGRICOLE.md
## MAKORA Framework — Module Agricole (Branche Assurance Agricole)
> Statut : Conception documentée uniquement — contribution académique sur le gap africain
> Spécificité : branche quasi-absente de la littérature académique sur la détection de fraude
> Dernière mise à jour : 17 avril 2026 — Phase 0

---

## 1. IDENTITÉ DU MODULE

| Champ | Valeur |
|---|---|
| **branch** | `agricole` |
| **Statut** | Conception seulement |
| **Marchés envisagés** | CM (prioritaire) + FR (secondaire) |
| **Implémentation** | Hors périmètre V1 |

---

## 2. POURQUOI CE MODULE EST ACADÉMIQUEMENT IMPORTANT

L'assurance agricole en Afrique subsaharienne est un terrain **quasi-vierge** dans la littérature académique sur la détection de fraude par IA. Documenter sa conception dans MAKORA constitue une contribution originale en soi : elle démontre que le Plugin Contract peut s'instancier sur une branche avec des contraintes radicalement différentes (expertise terrain, données satellitaires, flux 100% documentaire, micro-assurance).

---

## 3. SPÉCIFICITÉS MÉTIER AGRICOLE (CAMEROUN)

Ce qui rend cette branche fondamentalement différente :
- L'expertise est **terrain** (inspection physique des cultures sinistrées)
- Les preuves peuvent inclure des **données satellitaires** (NDVI, pluviométrie)
- La micro-assurance couvre des **petites surfaces** (< 5 hectares typiquement)
- Le sinistre est souvent **collectif** (même catastrophe climatique sur une zone)
- Le paiement se fait quasi-exclusivement via **Mobile Money**

### Gap de données documenté
Il n'existe pas de référentiel tarifaire public standardisé pour les cultures au Cameroun équivalent à la Mercuriale CIMA. Les prix de référence doivent être construits à partir de données de marché locales (marchés hebdomadaires, données MINADER). C'est une limite assumée et documentée de ce module.

---

## 4. SCHÉMA YAML — CONCEPTION

```yaml
branch: "agricole"
version: "1.0.0-conception"
description: "Module Agricole MAKORA — Conception uniquement"
market: ["CM"]

thresholds:
  contamination: 0.06
  anomaly_score_alert: 0.72

input_schema:
  required:
    - name: "ID_Sinistre"
      type: "string"
    - name: "ID_Agriculteur"
      type: "string"
    - name: "Surface_Declaree_Ha"
      type: "float"
      description: "Surface sinistrée déclarée en hectares"
    - name: "Surface_Verifiee_Ha"
      type: "float"
      description: "Surface vérifiée par l'expert terrain"
    - name: "Type_Sinistre_Agricole"
      type: "string"
      description: "SECHERESSE | INONDATION | PARASITES | GRELE"
    - name: "Culture_Principale"
      type: "string"
      description: "CACAO | CAFE | MANIOC | MAIS | PALMIER etc."
    - name: "Montant_Reclame"
      type: "float"
    - name: "Prix_Reference_Culture_XAF"
      type: "float"
      description: "Prix de référence par kg selon données MINADER"
    - name: "Region_Cameroun"
      type: "string"
      description: "Région administrative (10 régions)"
    - name: "Date_Sinistre_Declare"
      type: "date"
    - name: "Rapport_Expert_Terrain"
      type: "boolean"
    - name: "Photo_Terrain_Presente"
      type: "boolean"

  optional:
    - name: "NDVI_Score"
      type: "float"
      description: "Indice végétation satellite (0-1) — si disponible"
    - name: "Pluviometrie_Mm"
      type: "float"
      description: "Pluviométrie enregistrée sur la période"

features:
  - name: "ratio_surface_declare_verifie"
    description: "Surface_Declaree_Ha / Surface_Verifiee_Ha"
    importance: "critique"
  - name: "ratio_montant_reference"
    description: "Montant_Reclame / (Surface_Verifiee * Prix_Reference)"
    importance: "critique"
  - name: "sinistre_sans_rapport_expert"
    description: "True si pas de rapport d'expert terrain"
    importance: "critique"
  - name: "sinistre_collectif_zone"
    description: "True si >5 sinistres similaires dans la même zone sur 30j"
    importance: "haute"
  - name: "coherence_ndvi_sinistre"
    description: "Incohérence entre score NDVI satellitaire et sinistre déclaré"
    importance: "haute"

rca_rules:
  - id: "AGR_RCA_001"
    name: "Sur-déclaration de surface"
    category: "Fraude Intentionnelle"
    subcategory: "Sur-déclaration Superficie"
    conditions:
      - feature: "ratio_surface_declare_verifie"
        operator: "gt"
        threshold: 1.3
    confidence_base: 0.85

  - id: "AGR_RCA_002"
    name: "Sinistre sans preuve terrain"
    category: "Erreur Opérationnelle"
    subcategory: "Non-conformité Documentaire"
    conditions:
      - feature: "sinistre_sans_rapport_expert"
        operator: "eq"
        threshold: 1
    confidence_base: 0.75

graph_analysis:
  enabled: true
  node_entities: ["ID_Agriculteur", "Region_Cameroun"]
  edge_weight: "Montant_Reclame"
  community_algorithm: "louvain"
```

---

## 5. SCÉNARIOS D'ANOMALIES — MODULE AGRICOLE

| # | Scénario | Catégorie | Signal |
|---|---|---|---|
| Agr-1 | Sur-déclaration de surface sinistrée | Fraude | `ratio_surface_declare_verifie` |
| Agr-2 | Sinistre déclaré sans événement météo | Fraude | `coherence_ndvi_sinistre` |
| Agr-3 | Dommages fabriqués (sans rapport terrain) | Fraude | `sinistre_sans_rapport_expert` |
| Agr-4 | Sinistres collectifs coordonnés (réseau) | Fraude réseau | Graphe zone géographique |
| Agr-5 | Montant réclamé vs prix marché MINADER | Fraude | `ratio_montant_reference` |

---

## 6. GAPS DOCUMENTÉS — LIMITES ASSUMÉES

| Gap | Description | Impact |
|---|---|---|
| **Pas de référentiel tarifaire public** | Aucun équivalent Mercuriale CIMA pour les cultures | Prix de référence à construire manuellement |
| **Données satellitaires NDVI** | Accès limité pour le prototype | Feature optionnelle, pas critique |
| **Expertise terrain impossible** | Pas de dataset d'expertises terrain réelles disponible | Données entièrement synthétiques |
| **Micro-assurance** | Montants très faibles — bruit statistique élevé | Seuils de contamination ajustés |

---

*Fin du fichier MODULE_AGRICOLE.md*
