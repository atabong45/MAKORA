"""
MODULE : tests/api/authenticated/test_rbac_matrix.py
DESCRIPTION : Test exhaustif de la matrice RBAC — basé sur le code source réel.

MATRICE RÉELLE extraite des routers :
  /claims GET     : gestionnaire, auditeur, administrateur
  /claims POST    : gestionnaire, administrateur
  /models GET     : administrateur, expert_metier, auditeur
  /models/register POST : administrateur seulement
  /drift/status   : auditeur, administrateur, expert_metier
  /retraining     : administrateur, expert_metier
  /roles          : administrateur
  /users          : administrateur
  /admin/branches : administrateur
"""
import pytest


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def assert_allowed(r, label: str) -> None:
    assert r.status_code not in (401, 403), (
        f"[RBAC] {label} → attendu AUTORISÉ, obtenu {r.status_code}: {r.text[:300]}"
    )


def assert_denied(r, label: str) -> None:
    assert r.status_code in (401, 403), (
        f"[RBAC] {label} → attendu REFUSÉ (401/403), obtenu {r.status_code}"
    )


class TestRBACClaims:
    EP = "/api/v1/claims"

    def test_admin_can_read(self, client, admin_token):
        assert_allowed(client.get(self.EP, headers=auth(admin_token)), "admin GET /claims")

    def test_gestionnaire_can_read(self, client, gestionnaire_token):
        assert_allowed(client.get(self.EP, headers=auth(gestionnaire_token)),
                       "gestionnaire GET /claims")

    def test_auditeur_can_read(self, client, auditeur_token):
        assert_allowed(client.get(self.EP, headers=auth(auditeur_token)),
                       "auditeur GET /claims")

    def test_expert_cannot_read(self, client, expert_token):
        assert_denied(client.get(self.EP, headers=auth(expert_token)),
                      "expert GET /claims")

    def test_ds_cannot_read(self, client, ds_token):
        assert_denied(client.get(self.EP, headers=auth(ds_token)), "ds GET /claims")

    def test_auditeur_cannot_create(self, client, auditeur_token):
        assert_denied(
            client.post(self.EP,
                        json={"claim_id": "X", "branch_code": "sante",
                              "source_flux": "structured"},
                        headers=auth(auditeur_token)),
            "auditeur POST /claims"
        )

    def test_ds_cannot_create(self, client, ds_token):
        assert_denied(
            client.post(self.EP,
                        json={"claim_id": "X", "branch_code": "sante",
                              "source_flux": "structured"},
                        headers=auth(ds_token)),
            "ds POST /claims"
        )

    def test_expert_cannot_create(self, client, expert_token):
        assert_denied(
            client.post(self.EP,
                        json={"claim_id": "X", "branch_code": "sante",
                              "source_flux": "structured"},
                        headers=auth(expert_token)),
            "expert POST /claims"
        )


class TestRBACModels:
    EP = "/api/v1/models"

    def test_admin_can_read(self, client, admin_token):
        assert_allowed(client.get(self.EP, headers=auth(admin_token)), "admin GET /models")

    def test_auditeur_can_read(self, client, auditeur_token):
        assert_allowed(client.get(self.EP, headers=auth(auditeur_token)),
                       "auditeur GET /models")

    def test_expert_can_read(self, client, expert_token):
        assert_allowed(client.get(self.EP, headers=auth(expert_token)),
                       "expert GET /models")

    def test_gestionnaire_cannot_read(self, client, gestionnaire_token):
        assert_denied(client.get(self.EP, headers=auth(gestionnaire_token)),
                      "gestionnaire GET /models")

    def test_ds_cannot_read(self, client, ds_token):
        assert_denied(client.get(self.EP, headers=auth(ds_token)), "ds GET /models")

    def test_gestionnaire_cannot_register(self, client, gestionnaire_token):
        assert_denied(
            client.post(f"{self.EP}/register", json={},
                        headers=auth(gestionnaire_token)),
            "gestionnaire POST /models/register"
        )

    def test_auditeur_cannot_register(self, client, auditeur_token):
        assert_denied(
            client.post(f"{self.EP}/register", json={},
                        headers=auth(auditeur_token)),
            "auditeur POST /models/register"
        )

    def test_ds_cannot_register(self, client, ds_token):
        assert_denied(
            client.post(f"{self.EP}/register", json={}, headers=auth(ds_token)),
            "ds POST /models/register"
        )


class TestRBACDrift:
    EP = "/api/v1/drift/status"

    def test_admin_can_read(self, client, admin_token):
        assert_allowed(client.get(self.EP, headers=auth(admin_token)),
                       "admin GET /drift/status")

    def test_auditeur_can_read(self, client, auditeur_token):
        assert_allowed(client.get(self.EP, headers=auth(auditeur_token)),
                       "auditeur GET /drift/status")

    def test_expert_can_read(self, client, expert_token):
        assert_allowed(client.get(self.EP, headers=auth(expert_token)),
                       "expert GET /drift/status")

    def test_gestionnaire_cannot_read(self, client, gestionnaire_token):
        assert_denied(client.get(self.EP, headers=auth(gestionnaire_token)),
                      "gestionnaire GET /drift/status")

    def test_ds_cannot_read(self, client, ds_token):
        assert_denied(client.get(self.EP, headers=auth(ds_token)),
                      "ds GET /drift/status")


class TestRBACRoles:
    EP = "/api/v1/roles"

    def test_admin_can_read(self, client, admin_token):
        assert_allowed(client.get(self.EP, headers=auth(admin_token)), "admin GET /roles")

    def test_gestionnaire_cannot_read(self, client, gestionnaire_token):
        assert_denied(client.get(self.EP, headers=auth(gestionnaire_token)),
                      "gestionnaire GET /roles")

    def test_auditeur_cannot_read(self, client, auditeur_token):
        assert_denied(client.get(self.EP, headers=auth(auditeur_token)),
                      "auditeur GET /roles")

    def test_ds_cannot_read(self, client, ds_token):
        assert_denied(client.get(self.EP, headers=auth(ds_token)), "ds GET /roles")

    def test_expert_cannot_read(self, client, expert_token):
        assert_denied(client.get(self.EP, headers=auth(expert_token)), "expert GET /roles")


class TestRBACUsers:
    EP = "/api/v1/users"

    def test_admin_can_list(self, client, admin_token):
        assert_allowed(client.get(self.EP, headers=auth(admin_token)), "admin GET /users")

    def test_gestionnaire_cannot_list(self, client, gestionnaire_token):
        assert_denied(client.get(self.EP, headers=auth(gestionnaire_token)),
                      "gestionnaire GET /users")

    def test_auditeur_cannot_list(self, client, auditeur_token):
        assert_denied(client.get(self.EP, headers=auth(auditeur_token)),
                      "auditeur GET /users")

    def test_ds_cannot_list(self, client, ds_token):
        assert_denied(client.get(self.EP, headers=auth(ds_token)), "ds GET /users")

    def test_expert_cannot_list(self, client, expert_token):
        assert_denied(client.get(self.EP, headers=auth(expert_token)), "expert GET /users")


class TestRBACRetraining:
    EP = "/api/v1/retraining"

    def test_admin_can_list(self, client, admin_token):
        assert_allowed(client.get(self.EP, headers=auth(admin_token)),
                       "admin GET /retraining")

    def test_expert_can_list(self, client, expert_token):
        assert_allowed(client.get(self.EP, headers=auth(expert_token)),
                       "expert GET /retraining")

    def test_gestionnaire_cannot_list(self, client, gestionnaire_token):
        assert_denied(client.get(self.EP, headers=auth(gestionnaire_token)),
                      "gestionnaire GET /retraining")

    def test_auditeur_cannot_list(self, client, auditeur_token):
        assert_denied(client.get(self.EP, headers=auth(auditeur_token)),
                      "auditeur GET /retraining")

    def test_ds_cannot_list(self, client, ds_token):
        assert_denied(client.get(self.EP, headers=auth(ds_token)), "ds GET /retraining")


class TestRBACAdminBranches:
    EP = "/api/v1/admin/branches"

    def test_admin_can_read(self, client, admin_token):
        assert_allowed(client.get(self.EP, headers=auth(admin_token)),
                       "admin GET /admin/branches")

    def test_gestionnaire_cannot_read(self, client, gestionnaire_token):
        assert_denied(client.get(self.EP, headers=auth(gestionnaire_token)),
                      "gestionnaire GET /admin/branches")

    def test_ds_cannot_read(self, client, ds_token):
        assert_denied(client.get(self.EP, headers=auth(ds_token)),
                      "ds GET /admin/branches")

    def test_expert_cannot_read(self, client, expert_token):
        assert_denied(client.get(self.EP, headers=auth(expert_token)),
                      "expert GET /admin/branches")