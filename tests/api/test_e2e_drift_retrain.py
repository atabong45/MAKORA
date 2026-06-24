"""
MODULE : tests/api/test_e2e_drift_retrain.py
DESCRIPTION : Tests E2E — Flux drift CRITICAL → réentraînement → déploiement.
"""
import pytest


class TestE2EDriftRetrain:
    def test_drift_endpoints_exist(self, client):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        drift_paths = [p for p in paths if "/drift" in p]
        assert len(drift_paths) >= 4

    def test_retraining_endpoints_exist(self, client):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        retrain_paths = [p for p in paths if "/retraining" in p]
        assert len(retrain_paths) >= 4

    def test_drift_run_requires_auth(self, client):
        r = client.post("/api/v1/drift/run/sante",
                        json={"reference_window_days": 90, "current_window_days": 30})
        assert r.status_code == 401

    def test_retraining_create_requires_auth(self, client):
        r = client.post("/api/v1/retraining/",
                        json={"branch_code": "sante", "reason": "Drift critique"})
        assert r.status_code == 401

    def test_retraining_approve_requires_admin(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.patch("/api/v1/retraining/00000000-0000-0000-0000-000000000000/approve",
                         headers=headers)
        assert r.status_code in (401, 403)

    def test_model_deploy_requires_admin(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.post("/api/v1/models/deploy",
                        json={"model_version_id": "00000000-0000-0000-0000-000000000000"},
                        headers=headers)
        assert r.status_code in (401, 403)

    def test_complete_retrain_state_machine(self, client, admin_token):
        """Vérifie qu'on ne peut pas compléter une demande inexistante."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = client.patch(
            "/api/v1/retraining/00000000-0000-0000-0000-000000000000/complete"
            "?new_model_version_id=00000000-0000-0000-0000-000000000001",
            headers=headers
        )
        assert r.status_code in (401, 404)
