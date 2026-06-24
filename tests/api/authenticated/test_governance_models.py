"""
MODULE : tests/api/authenticated/test_governance_models.py
DESCRIPTION : Tests Gouvernance ML — RBAC réel lu dans les routers.

MATRICE RÉELLE (depuis le code source) :
  models GET   : administrateur, expert_metier, auditeur  (PAS data_scientist)
  models POST  : administrateur seulement
  drift GET    : auditeur, administrateur, expert_metier   (PAS data_scientist)
  retraining   : administrateur, expert_metier             (PAS data_scientist)
  RetrainingCreate.branch_code référence Branch.code → branche doit exister en DB
"""
import pytest

BASE_MODELS  = "/api/v1/models"
BASE_DRIFT   = "/api/v1/drift"
BASE_RETRAIN = "/api/v1/retraining"


class TestModelsRead:
    def test_list_models_no_auth(self, client):
        assert client.get(BASE_MODELS).status_code == 401

    def test_list_models_admin(self, client, admin_headers):
        assert client.get(BASE_MODELS, headers=admin_headers).status_code == 200

    def test_list_models_auditeur(self, client, auditeur_headers):
        assert client.get(BASE_MODELS, headers=auditeur_headers).status_code == 200

    def test_list_models_expert(self, client, expert_headers):
        assert client.get(BASE_MODELS, headers=expert_headers).status_code == 200

    def test_list_models_gestionnaire_forbidden(self, client, gestionnaire_headers):
        assert client.get(BASE_MODELS, headers=gestionnaire_headers).status_code == 403

    def test_list_models_ds_forbidden(self, client, ds_headers):
        """data_scientist n'a pas accès à /models — rôles: admin, expert_metier, auditeur."""
        assert client.get(BASE_MODELS, headers=ds_headers).status_code == 403

    def test_get_nonexistent_model(self, client, admin_headers):
        r = client.get(f"{BASE_MODELS}/00000000-0000-0000-0000-000000000000",
                       headers=admin_headers)
        assert r.status_code == 404


class TestModelsRegister:
    def test_register_no_auth(self, client):
        assert client.post(f"{BASE_MODELS}/register", json={}).status_code == 401

    def test_register_gestionnaire_forbidden(self, client, gestionnaire_headers):
        assert client.post(f"{BASE_MODELS}/register", json={},
                           headers=gestionnaire_headers).status_code == 403

    def test_register_ds_forbidden(self, client, ds_headers):
        """data_scientist ne peut pas enregistrer de modèle — admin seulement."""
        assert client.post(f"{BASE_MODELS}/register", json={},
                           headers=ds_headers).status_code == 403

    def test_register_missing_required_admin(self, client, admin_headers):
        """Admin avec payload vide → 422 (validation, pas 403)."""
        r = client.post(f"{BASE_MODELS}/register", json={}, headers=admin_headers)
        assert r.status_code == 422

    def test_deploy_no_auth(self, client):
        assert client.post(f"{BASE_MODELS}/deploy", json={}).status_code == 401

    def test_deploy_gestionnaire_forbidden(self, client, gestionnaire_headers):
        assert client.post(f"{BASE_MODELS}/deploy",
                           json={"model_version_id": "00000000-0000-0000-0000-000000000000"},
                           headers=gestionnaire_headers).status_code == 403


class TestDrift:
    """Rôles drift : auditeur, administrateur, expert_metier — PAS data_scientist."""

    def test_drift_status_no_auth(self, client):
        assert client.get(f"{BASE_DRIFT}/status").status_code == 401

    def test_drift_status_admin(self, client, admin_headers):
        assert client.get(f"{BASE_DRIFT}/status", headers=admin_headers).status_code == 200

    def test_drift_status_auditeur(self, client, auditeur_headers):
        assert client.get(f"{BASE_DRIFT}/status", headers=auditeur_headers).status_code == 200

    def test_drift_status_expert(self, client, expert_headers):
        assert client.get(f"{BASE_DRIFT}/status", headers=expert_headers).status_code == 200

    def test_drift_status_gestionnaire_forbidden(self, client, gestionnaire_headers):
        assert client.get(f"{BASE_DRIFT}/status",
                          headers=gestionnaire_headers).status_code == 403

    def test_drift_status_ds_forbidden(self, client, ds_headers):
        """data_scientist non autorisé sur /drift — rôles: auditeur, admin, expert_metier."""
        assert client.get(f"{BASE_DRIFT}/status", headers=ds_headers).status_code == 403

    def test_drift_status_branch_sante(self, client, admin_headers):
        assert client.get(f"{BASE_DRIFT}/status/sante",
                          headers=admin_headers).status_code == 200

    def test_drift_history_sante(self, client, expert_headers):
        assert client.get(f"{BASE_DRIFT}/history/sante",
                          headers=expert_headers).status_code == 200

    def test_drift_run_no_auth(self, client):
        assert client.post(f"{BASE_DRIFT}/run/sante").status_code == 401


class TestRetraining:
    """Rôles retraining : administrateur, expert_metier — PAS data_scientist."""

    def test_list_retrain_admin(self, client, admin_headers):
        assert client.get(BASE_RETRAIN, headers=admin_headers).status_code == 200

    def test_list_retrain_expert(self, client, expert_headers):
        assert client.get(BASE_RETRAIN, headers=expert_headers).status_code == 200

    def test_list_retrain_ds_forbidden(self, client, ds_headers):
        assert client.get(BASE_RETRAIN, headers=ds_headers).status_code == 403

    def test_list_retrain_gestionnaire_forbidden(self, client, gestionnaire_headers):
        assert client.get(BASE_RETRAIN, headers=gestionnaire_headers).status_code == 403

    def test_retrain_no_auth(self, client):
        assert client.get(BASE_RETRAIN).status_code == 401

    def test_create_retrain_expert(self, client, expert_headers):
        """branch_code doit exister en DB (seedé dans conftest)."""
        payload = {"branch_code": "sante", "reason": "Drift PSI > 0.25 — test CI"}
        r = client.post(BASE_RETRAIN, json=payload, headers=expert_headers)
        assert r.status_code in (200, 201), r.text

    def test_create_retrain_admin(self, client, admin_headers):
        payload = {"branch_code": "auto", "reason": "Drift détecté — test CI"}
        r = client.post(BASE_RETRAIN, json=payload, headers=admin_headers)
        assert r.status_code in (200, 201), r.text

    def test_create_retrain_ds_forbidden(self, client, ds_headers):
        r = client.post(BASE_RETRAIN,
                        json={"branch_code": "sante", "reason": "test"},
                        headers=ds_headers)
        assert r.status_code == 403

    def test_create_retrain_missing_reason_expert(self, client, expert_headers):
        """Payload sans reason → 422."""
        r = client.post(BASE_RETRAIN, json={"branch_code": "sante"}, headers=expert_headers)
        assert r.status_code == 422

    def test_create_retrain_unknown_branch(self, client, expert_headers):
        """Branche inconnue → 400."""
        r = client.post(BASE_RETRAIN,
                        json={"branch_code": "branche_inconnue", "reason": "test"},
                        headers=expert_headers)
        assert r.status_code == 400

    def test_approve_nonexistent_admin(self, client, admin_headers):
        r = client.patch(
            f"{BASE_RETRAIN}/00000000-0000-0000-0000-000000000000/approve",
            headers=admin_headers,
        )
        assert r.status_code == 404

    def test_approve_gestionnaire_forbidden(self, client, gestionnaire_headers):
        r = client.patch(
            f"{BASE_RETRAIN}/00000000-0000-0000-0000-000000000000/approve",
            headers=gestionnaire_headers,
        )
        assert r.status_code in (403, 404)