"""
MODULE : tests/api/test_claims.py
DESCRIPTION : Tests API — Sinistres (17 endpoints).
"""
import pytest


class TestClaimsAuth:
    def test_list_claims_no_auth(self, client):
        r = client.get("/api/v1/claims/")
        assert r.status_code == 401

    def test_create_claim_no_auth(self, client):
        r = client.post("/api/v1/claims/", json={"claim_id": "TST001", "branch_code": "sante"})
        assert r.status_code == 401

    def test_create_claim_invalid_branch(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.post("/api/v1/claims/", json={"claim_id": "TST001", "branch_code": "INVALID"}, headers=headers)
        assert r.status_code in (400, 401, 422)

    def test_get_nonexistent_claim(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.get("/api/v1/claims/NONEXISTENT_99999", headers=headers)
        assert r.status_code in (401, 404)

    def test_claim_lifecycle_schema(self, client):
        """Vérifie que les endpoints claims existent dans l'OpenAPI."""
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        assert any("/claims" in p for p in paths)


class TestClaimsValidation:
    def test_create_claim_missing_id(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.post("/api/v1/claims/", json={"branch_code": "sante"}, headers=headers)
        assert r.status_code in (401, 422)

    def test_create_claim_invalid_source(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.post("/api/v1/claims/", json={
            "claim_id": "TST001", "branch_code": "sante", "source_flux": "INVALID_SOURCE"
        }, headers=headers)
        assert r.status_code in (401, 422)
