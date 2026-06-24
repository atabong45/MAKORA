"""
MODULE : tests/api/test_governance.py
DESCRIPTION : Tests API — Gouvernance ML : modèles, drift, réentraînement, modules (28 ep.).
"""
import pytest


class TestModels:
    def test_list_models_no_auth(self, client):
        assert client.get("/api/v1/models/").status_code == 401

    def test_register_model_no_auth(self, client):
        r = client.post("/api/v1/models/register", json={
            "branch_code": "sante", "version_tag": "v1.0", "file_path": "/path/model.joblib",
            "contamination": 0.05, "feature_names": ["feat1"]
        })
        assert r.status_code == 401

    def test_register_model_gestionnaire_forbidden(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.post("/api/v1/models/register", json={
            "branch_code": "sante", "version_tag": "v1.0", "file_path": "/path/model.joblib",
            "contamination": 0.05, "feature_names": ["feat1"]
        }, headers=headers)
        assert r.status_code in (401, 403)

    def test_deploy_no_auth(self, client):
        r = client.post("/api/v1/models/deploy", json={
            "model_version_id": "00000000-0000-0000-0000-000000000000"
        })
        assert r.status_code == 401


class TestDrift:
    def test_status_no_auth(self, client):
        assert client.get("/api/v1/drift/status").status_code == 401

    def test_branch_status_no_auth(self, client):
        assert client.get("/api/v1/drift/status/sante").status_code == 401

    def test_run_no_auth(self, client):
        r = client.post("/api/v1/drift/run/sante",
                        json={"reference_window_days": 90, "current_window_days": 30})
        assert r.status_code == 401


class TestRetraining:
    def test_create_no_auth(self, client):
        r = client.post("/api/v1/retraining/",
                        json={"branch_code": "sante", "reason": "Drift critique"})
        assert r.status_code == 401

    def test_approve_no_auth(self, client):
        r = client.patch("/api/v1/retraining/00000000-0000-0000-0000-000000000000/approve")
        assert r.status_code == 401

    def test_state_machine_invalid(self, client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = client.patch(
            "/api/v1/retraining/00000000-0000-0000-0000-000000000000/approve",
            headers=headers
        )
        assert r.status_code in (401, 404)


class TestModules:
    def test_list_no_auth(self, client):
        assert client.get("/api/v1/modules/").status_code == 401

    def test_reload_no_auth(self, client):
        r = client.post("/api/v1/modules/sante/reload")
        assert r.status_code == 401

    def test_config_update_no_auth(self, client):
        r = client.patch("/api/v1/modules/sante/config",
                         json={"contamination": 0.05})
        assert r.status_code == 401

    def test_contamination_invalid(self, client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = client.patch("/api/v1/modules/sante/config",
                         json={"contamination": 2.0}, headers=headers)
        assert r.status_code in (400, 401, 404, 422)
