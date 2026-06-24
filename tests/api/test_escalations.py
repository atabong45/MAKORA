"""
MODULE : tests/api/test_escalations.py
DESCRIPTION : Tests API — Escalades HITL (6 endpoints).
"""
import pytest


class TestEscalationsAuth:
    def test_create_no_auth(self, client):
        r = client.post("/api/v1/escalations/", json={
            "analysis_id": "00000000-0000-0000-0000-000000000000",
            "motif_escalade": "Cas douteux"
        })
        assert r.status_code == 401

    def test_create_auditeur_forbidden(self, client, auditeur_token):
        headers = {"Authorization": f"Bearer {auditeur_token}"}
        r = client.post("/api/v1/escalations/", json={
            "analysis_id": "00000000-0000-0000-0000-000000000000",
            "motif_escalade": "Cas douteux"
        }, headers=headers)
        assert r.status_code in (401, 403)

    def test_pending_no_auth(self, client):
        r = client.get("/api/v1/escalations/pending")
        assert r.status_code == 401

    def test_pending_gestionnaire_forbidden(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.get("/api/v1/escalations/pending", headers=headers)
        assert r.status_code in (401, 403)

    def test_list_no_auth(self, client):
        r = client.get("/api/v1/escalations/")
        assert r.status_code == 401

    def test_resolve_missing_note(self, client, auditeur_token):
        headers = {"Authorization": f"Bearer {auditeur_token}"}
        r = client.patch(
            "/api/v1/escalations/00000000-0000-0000-0000-000000000000/resolve",
            json={}, headers=headers
        )
        assert r.status_code in (401, 422)
