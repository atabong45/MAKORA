"""
MODULE : tests/api/authenticated/test_auth_flow.py
DESCRIPTION : Tests du flux d'authentification complet.
"""
import pytest

BASE = "/api/v1/auth"


class TestLogin:
    def test_login_admin_ok(self, client):
        r = client.post(f"{BASE}/login",
                        json={"username": "admin", "password": "Admin1234!"})
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"
        assert body["expires_in"] > 0

    def test_login_wrong_password(self, client):
        r = client.post(f"{BASE}/login",
                        json={"username": "admin", "password": "WrongPass!"})
        assert r.status_code in (401, 429)  # 429 si rate limit non désactivé

    def test_login_unknown_user(self, client):
        r = client.post(f"{BASE}/login",
                        json={"username": "ghost", "password": "Test1234!"})
        assert r.status_code in (401, 429)

    def test_login_missing_fields(self, client):
        r = client.post(f"{BASE}/login", json={"username": "admin"})
        assert r.status_code == 422

    def test_login_all_roles(self, client):
        """Tous les comptes seedés doivent pouvoir se connecter."""
        credentials = [
            ("admin",          "Admin1234!"),
            ("gestionnaire1",  "Test1234!"),
            ("auditeur1",      "Test1234!"),
            ("expert1",        "Test1234!"),
            ("datascientist1", "Test1234!"),
        ]
        for username, password in credentials:
            r = client.post(f"{BASE}/login",
                            json={"username": username, "password": password})
            assert r.status_code == 200, f"Login {username} échoué : {r.text}"


class TestRefreshToken:
    def test_refresh_ok(self, client):
        r = client.post(f"{BASE}/login",
                        json={"username": "gestionnaire1", "password": "Test1234!"})
        assert r.status_code == 200
        refresh_token = r.json()["refresh_token"]

        r2 = client.post(f"{BASE}/refresh",
                         json={"refresh_token": refresh_token})
        assert r2.status_code == 200
        assert "access_token" in r2.json()

    def test_refresh_invalid_token(self, client):
        r = client.post(f"{BASE}/refresh",
                        json={"refresh_token": "ce-token-nexiste-pas"})
        assert r.status_code == 401

    def test_refresh_missing_token(self, client):
        r = client.post(f"{BASE}/refresh", json={})
        assert r.status_code == 422


class TestMe:
    def test_me_ok(self, client, admin_headers):
        r = client.get(f"{BASE}/me", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body["username"] == "admin"
        assert "password_hash" not in body

    def test_me_no_auth(self, client):
        r = client.get(f"{BASE}/me")
        assert r.status_code == 401

    def test_me_invalid_token(self, client):
        r = client.get(f"{BASE}/me",
                       headers={"Authorization": "Bearer token.invalide.xxx"})
        assert r.status_code == 401


class TestLogout:
    def test_logout_ok(self, client):
        r = client.post(f"{BASE}/login",
                        json={"username": "auditeur1", "password": "Test1234!"})
        assert r.status_code == 200
        data = r.json()
        access  = data["access_token"]
        refresh = data["refresh_token"]

        r2 = client.post(f"{BASE}/logout",
                         json={"refresh_token": refresh},
                         headers={"Authorization": f"Bearer {access}"})
        assert r2.status_code == 200

        # Le refresh token est maintenant révoqué
        r3 = client.post(f"{BASE}/refresh",
                         json={"refresh_token": refresh})
        assert r3.status_code == 401

    def test_logout_no_auth(self, client):
        r = client.post(f"{BASE}/logout",
                        json={"refresh_token": "quelconque"})
        assert r.status_code == 401


class TestChangePassword:
    def test_change_password_ok(self, client):
        r = client.post(f"{BASE}/login",
                        json={"username": "expert1", "password": "Test1234!"})
        assert r.status_code == 200
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        r2 = client.post(f"{BASE}/change-password",
                         json={"current_password": "Test1234!",
                               "new_password":     "NewPass5678!"},
                         headers=headers)
        assert r2.status_code == 200

        # Restaurer
        r3 = client.post(f"{BASE}/login",
                         json={"username": "expert1", "password": "NewPass5678!"})
        assert r3.status_code == 200
        token2 = r3.json()["access_token"]
        client.post(f"{BASE}/change-password",
                    json={"current_password": "NewPass5678!",
                          "new_password":     "Test1234!"},
                    headers={"Authorization": f"Bearer {token2}"})

    def test_change_password_wrong_current(self, client, expert_headers):
        r = client.post(f"{BASE}/change-password",
                        json={"current_password": "MauvaisMotDePasse!",
                              "new_password":     "Autre1234!"},
                        headers=expert_headers)
        assert r.status_code == 400

    def test_change_password_no_auth(self, client):
        r = client.post(f"{BASE}/change-password",
                        json={"current_password": "Test1234!",
                              "new_password":     "Autre1234!"})
        assert r.status_code == 401