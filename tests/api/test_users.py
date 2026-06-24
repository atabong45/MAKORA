"""
MODULE : tests/api/test_users.py
DESCRIPTION : Tests API — Gestion utilisateurs (9 endpoints).
"""
import pytest


class TestUsersAuth:
    def test_list_users_no_auth(self, client):
        r = client.get("/api/v1/users/")
        assert r.status_code == 401

    def test_list_users_gestionnaire_forbidden(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.get("/api/v1/users/", headers=headers)
        assert r.status_code in (401, 403)

    def test_create_user_no_auth(self, client):
        r = client.post("/api/v1/users/", json={
            "username": "newuser", "email": "new@test.cm",
            "full_name": "New User", "password": "Pass1234!"
        })
        assert r.status_code == 401

    def test_create_user_missing_fields(self, client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = client.post("/api/v1/users/", json={"username": "incomplete"}, headers=headers)
        assert r.status_code in (401, 422)

    def test_get_nonexistent_user(self, client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = client.get("/api/v1/users/00000000-0000-0000-0000-000000000000", headers=headers)
        assert r.status_code in (401, 404)
