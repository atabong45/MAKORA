"""
MODULE : tests/api/test_security.py
DESCRIPTION : Tests sécurité transversaux — JWT, RBAC, injection, headers.
"""
import pytest


class TestJWT:
    def test_expired_token_rejected(self, client):
        expired = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiJ1c2VyMSIsImV4cCI6MX0."
            "aSIgk3NQ0C7zH3MrUPr25kChcFpSlqNa2dMmXlpC9rY"
        )
        r = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"})
        assert r.status_code == 401

    def test_malformed_token_rejected(self, client):
        r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not.a.valid.token"})
        assert r.status_code == 401

    def test_missing_bearer_prefix(self, client):
        r = client.get("/api/v1/auth/me", headers={"Authorization": "sometoken"})
        assert r.status_code == 401

    def test_no_authorization_header(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401


class TestRBAC:
    PROTECTED_ADMIN = [
        "/api/v1/users/",
        "/api/v1/admin/status",
        "/api/v1/admin/branches",
    ]

    def test_admin_endpoints_require_admin_role(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        for endpoint in self.PROTECTED_ADMIN:
            r = client.get(endpoint, headers=headers)
            assert r.status_code in (401, 403), f"Endpoint {endpoint} accessible par gestionnaire"

    def test_graph_requires_auditeur(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.get("/api/v1/graph/communities", headers=headers)
        assert r.status_code in (401, 403)


class TestHeaders:
    def test_error_format(self, client):
        r = client.get("/api/v1/claims/NONEXISTENT", headers={"Authorization": "Bearer bad"})
        assert r.status_code in (401, 404)
        if r.status_code == 404:
            data = r.json()
            assert "error" in data
            assert "message" in data

    def test_health_public(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data
        assert data["status"] in ("ok", "degraded")

    def test_openapi_accessible(self, client):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert data["info"]["title"] == "MAKORA"
