"""
MODULE : tests/api/test_auth.py
DESCRIPTION : Tests API — Authentification (10 endpoints).
"""
import pytest


class TestLogin:
    def test_login_wrong_password(self, client):
        r = client.post("/api/v1/auth/login", json={"username": "nonexistent", "password": "wrong"})
        assert r.status_code in (401, 422)

    def test_login_missing_fields(self, client):
        r = client.post("/api/v1/auth/login", json={"username": "admin"})
        assert r.status_code == 422

    def test_login_empty_body(self, client):
        r = client.post("/api/v1/auth/login", json={})
        assert r.status_code == 422

    def test_refresh_invalid_token(self, client):
        r = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.token.here"})
        assert r.status_code == 401

    def test_me_without_token(self, client):
        r = client.get("/api/v1/auth/me")
        assert r.status_code == 401

    def test_me_with_invalid_token(self, client):
        r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})
        assert r.status_code == 401

    def test_forgot_password_valid_email(self, client):
        r = client.post("/api/v1/auth/forgot-password", json={"email": "test@example.com"})
        assert r.status_code == 200
        assert "message" in r.json()

    def test_forgot_password_invalid_email(self, client):
        r = client.post("/api/v1/auth/forgot-password", json={"email": "not-an-email"})
        assert r.status_code == 422

    def test_reset_password_invalid_token(self, client):
        r = client.post("/api/v1/auth/reset-password", json={"token": "bad", "new_password": "New1234!"})
        assert r.status_code == 400

    def test_reset_password_too_short(self, client):
        r = client.post("/api/v1/auth/reset-password", json={"token": "tok", "new_password": "short"})
        assert r.status_code == 422

    def test_change_password_no_auth(self, client):
        r = client.post("/api/v1/auth/change-password",
                        json={"current_password": "old", "new_password": "New1234!"})
        assert r.status_code == 401

    def test_sessions_no_auth(self, client):
        r = client.get("/api/v1/auth/sessions")
        assert r.status_code == 401

    def test_logout_no_auth(self, client):
        r = client.post("/api/v1/auth/logout", json={"refresh_token": "tok"})
        assert r.status_code == 401
