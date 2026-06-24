# API_CONTRACTS.md
## MAKORA Framework — Contrats API FastAPI
> Ce fichier est la référence pour l'implémentation du backend et du frontend Next.js.
> Tous les endpoints sont documentés avec format requête/réponse et exemples curl.
> Dernière mise à jour : 17 avril 2026 — Phase 0

---

## 1. BASE URL ET CONFIGURATION

```
Base URL (local)  : http://localhost:8000
Documentation API : http://localhost:8000/docs  (Swagger auto-généré)
Version API       : /api/v1/
```

---

## 2. ENDPOINTS

### POST /api/v1/analyze
**Description :** Analyser un dossier ou un batch de dossiers. Retourne le diagnostic MAKORA complet.

**Request :**
```json
{
  "branch": "sante",
  "source": "api",
  "dossiers": [
    {
      "ID_Sinistre": "SIN_2025_CM_00842",
      "Montant_Facture": 18500,
      "Devise": "XAF",
      "Code_Acte": "CARD-001",
      "ID_Praticien": "PRAT_HASH_4821",
      "Date_Soin": "2025-11-10",
      "Pays_Residence": "CM"
    }
  ]
}
```

**Response 200 :**
```json
{
  "batch_id": "BATCH_20251114_092341",
  "branch": "sante",
  "processed": 1,
  "anomalies_detected": 1,
  "results": [
    {
      "claim_id": "SIN_2025_CM_00842",
      "branch": "sante",
      "anomaly_score": 0.87,
      "is_anomaly": true,
      "processing_time_ms": 1243,
      "rca": {
        "category": "Fraude Intentionnelle",
        "subcategory": "Surfacturation Prestataire",
        "confidence": 0.91,
        "rule_triggered": "RCA_SURF_001",
        "top_features": [
          {"name": "ratio_prix_mercuriale", "shap_value": 0.312, "direction": "positive"},
          {"name": "historique_praticien", "shap_value": 0.187, "direction": "positive"},
          {"name": "montant_facture", "shap_value": 0.094, "direction": "positive"}
        ],
        "explanation_fr": "Le montant facturé pour cette consultation dépasse de 81% le tarif de référence..."
      },
      "graph_analysis": null,
      "audit": {
        "timestamp": "2025-11-14T09:23:41Z",
        "model_version": "makora-sante-v1.0",
        "decision": "PENDING"
      }
    }
  ]
}
```

**Curl :**
```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"branch": "sante", "source": "api", "dossiers": [{"ID_Sinistre": "TEST_001", "Montant_Facture": 18500, "Devise": "XAF"}]}'
```

---

### POST /api/v1/analyze/upload
**Description :** Analyser un fichier CSV/JSON/PDF uploadé.

**Request :** `multipart/form-data`
- `file` : fichier à analyser
- `branch` : branche d'assurance
- `source_name` : nom du mapping source (ex: `noemie_api`, `kaggle_healthcare`)

**Response 200 :** Même format que `/analyze`

---

### GET /api/v1/audit
**Description :** Lister les dossiers audités avec filtres.

**Query params :**
- `branch` : filtrer par branche (`sante`, `auto`, `all`)
- `is_anomaly` : filtrer par anomalie (`true`, `false`, `all`)
- `decision` : filtrer par décision (`PENDING`, `CONFIRMED`, `REJECTED`)
- `date_from` : date de début (ISO 8601)
- `date_to` : date de fin (ISO 8601)
- `page` : numéro de page (défaut: 1)
- `page_size` : taille page (défaut: 50, max: 200)

**Response 200 :**
```json
{
  "total": 1243,
  "page": 1,
  "page_size": 50,
  "results": [
    {
      "claim_id": "SIN_2025_CM_00842",
      "branch": "sante",
      "anomaly_score": 0.87,
      "is_anomaly": true,
      "rca_category": "Fraude Intentionnelle",
      "rca_subcategory": "Surfacturation Prestataire",
      "decision": "PENDING",
      "timestamp": "2025-11-14T09:23:41Z"
    }
  ]
}
```

---

### GET /api/v1/audit/{claim_id}
**Description :** Détail complet d'un dossier audité.

**Response 200 :** Format complet identique à la sortie de `/analyze`

---

### POST /api/v1/audit/{claim_id}/validate
**Description :** Valider ou rejeter une anomalie (human-in-the-loop).

**Request :**
```json
{
  "decision": "CONFIRMED",
  "motif": "Surfacturation confirmée après vérification facture originale",
  "gestionnaire_id": "GES_004"
}
```

**Valeurs decision :** `CONFIRMED` | `REJECTED` | `ESCALATED`

**Response 200 :**
```json
{
  "claim_id": "SIN_2025_CM_00842",
  "decision": "CONFIRMED",
  "updated_at": "2025-11-14T10:15:22Z",
  "gestionnaire_id": "GES_004"
}
```

---

### GET /api/v1/drift/status
**Description :** Statut du drift monitoring pour toutes les branches actives.

**Response 200 :**
```json
{
  "timestamp": "2025-11-14T10:00:00Z",
  "branches": {
    "sante": {
      "status": "WARNING",
      "features": {
        "ratio_prix_mercuriale": {"psi": 0.14, "status": "WARNING"},
        "Montant_Facture": {"psi": 0.07, "status": "STABLE"},
        "Score_Confiance_OCR": {"psi": 0.05, "status": "STABLE"}
      },
      "last_check": "2025-11-14T09:00:00Z"
    },
    "auto": {
      "status": "STABLE",
      "features": {},
      "last_check": null
    }
  }
}
```

---

### GET /api/v1/modules
**Description :** Lister les modules MAKORA chargés et leur statut.

**Response 200 :**
```json
{
  "modules": [
    {
      "branch": "sante",
      "version": "1.0.0",
      "status": "LOADED",
      "model_version": "makora-sante-v1.0",
      "graph_enabled": true,
      "last_retrain": "2025-10-01T00:00:00Z"
    },
    {
      "branch": "auto",
      "version": "1.0.0",
      "status": "NOT_LOADED",
      "model_version": null,
      "graph_enabled": false,
      "last_retrain": null
    }
  ]
}
```

---

### GET /api/v1/health
**Description :** Santé du service MAKORA.

**Response 200 :**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "ollama_available": true,
  "modules_loaded": ["sante"],
  "uptime_seconds": 3600
}
```

---

## 3. CODES D'ERREUR

| Code | Signification | Exemple |
|---|---|---|
| `400` | Requête invalide | Branch inconnue, champ manquant |
| `404` | Dossier non trouvé | claim_id inexistant |
| `422` | Erreur de validation Pydantic | Type de données incorrect |
| `503` | Service indisponible | Modèle ML non chargé |

**Format erreur :**
```json
{
  "error": "MODULE_NOT_LOADED",
  "message": "Le module 'auto' n'est pas chargé. Utilisez /api/v1/modules pour vérifier les modules disponibles.",
  "timestamp": "2025-11-14T09:23:41Z"
}
```

---

*Fin du fichier API_CONTRACTS.md*
*À mettre à jour à chaque modification des endpoints*
