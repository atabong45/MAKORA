"""
MODULE : tests/api/test_audit.py
DESCRIPTION : Tests API — Audit HITL (6 endpoints).
"""
import pytest


class TestAuditAuth:
    def test_list_no_auth(self, client):
        r = client.get("/api/v1/audit/")
        assert r.status_code == 401

    def test_stats_no_auth(self, client):
        r = client.get("/api/v1/audit/stats")
        assert r.status_code == 401

    def test_decision_no_auth(self, client):
        r = client.post("/api/v1/audit/00000000-0000-0000-0000-000000000000/decision",
                        json={"decision": "CONFIRMED"})
        assert r.status_code == 401

    def test_invalid_decision_value(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.post("/api/v1/audit/00000000-0000-0000-0000-000000000000/decision",
                        json={"decision": "MAYBE"}, headers=headers)
        assert r.status_code in (401, 422)

    def test_shap_no_auth(self, client):
        r = client.get("/api/v1/audit/00000000-0000-0000-0000-000000000000/shap")
        assert r.status_code == 401

    def test_decisions_history_no_auth(self, client):
        r = client.get("/api/v1/audit/00000000-0000-0000-0000-000000000000/decisions")
        assert r.status_code == 401
