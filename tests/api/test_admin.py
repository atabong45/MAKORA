"""
MODULE : tests/api/test_admin.py
DESCRIPTION : Tests API — Administration système (6 endpoints).
"""
import pytest


class TestAdmin:
    def test_status_no_auth(self, client):
        assert client.get("/api/v1/admin/status").status_code == 401

    def test_status_gestionnaire_forbidden(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.get("/api/v1/admin/status", headers=headers)
        assert r.status_code in (401, 403)

    def test_branches_no_auth(self, client):
        assert client.get("/api/v1/admin/branches").status_code == 401

    def test_activity_log_no_auth(self, client):
        assert client.get("/api/v1/admin/activity-log").status_code == 401

    def test_activity_log_gestionnaire_forbidden(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.get("/api/v1/admin/activity-log", headers=headers)
        assert r.status_code in (401, 403)

    def test_activate_branch_no_auth(self, client):
        r = client.patch("/api/v1/admin/branches/sante/activate")
        assert r.status_code == 401
