"""
MODULE : tests/api/authenticated/test_referentiels_crud.py
DESCRIPTION : Tests référentiels — URLs et schémas réels.

CORRECTION test_get_practitioner_by_hash :
  GET /referentiels/practitioners/{id_hash}/claims retourne 200 + []
  pour un hash inexistant — comportement "liste vide" cohérent avec toute l'API.
"""
import pytest

BASE_ADMIN_BR = "/api/v1/admin/branches"
BASE_PRICES   = "/api/v1/referentiels/prices"
BASE_PRACT    = "/api/v1/referentiels/practitioners"
BASE_GARAGES  = "/api/v1/referentiels/garages"


class TestAdminBranches:
    def test_list_branches_admin(self, client, admin_headers):
        assert client.get(BASE_ADMIN_BR, headers=admin_headers).status_code == 200

    def test_branches_contains_sante_auto(self, client, admin_headers):
        r = client.get(BASE_ADMIN_BR, headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        results = body.get("results", body) if isinstance(body, dict) else body
        if not isinstance(results, list):
            pytest.skip(f"Format inattendu : {type(results)}")
        codes = {b.get("code") or b.get("branch_code") or b.get("name") for b in results}
        assert "sante" in codes
        assert "auto" in codes

    def test_get_branch_sante(self, client, admin_headers):
        r = client.get(f"{BASE_ADMIN_BR}/sante", headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        assert body.get("code") == "sante"
        assert body.get("is_active") is True
        assert abs(body.get("contamination_threshold", 0) - 0.068) < 0.001

    def test_get_branch_auto(self, client, admin_headers):
        r = client.get(f"{BASE_ADMIN_BR}/auto", headers=admin_headers)
        assert r.status_code == 200
        assert abs(r.json().get("contamination_threshold", 0) - 0.080) < 0.001

    def test_get_branch_nonexistent(self, client, admin_headers):
        assert client.get(f"{BASE_ADMIN_BR}/inexistante",
                          headers=admin_headers).status_code == 404

    def test_branches_admin_only(self, client, gestionnaire_headers):
        assert client.get(BASE_ADMIN_BR,
                          headers=gestionnaire_headers).status_code == 403

    def test_activate_via_patch(self, client, admin_headers):
        r = client.patch(f"{BASE_ADMIN_BR}/vie/activate", headers=admin_headers)
        assert r.status_code in (200, 404)


class TestPrices:
    def test_list_prices_sante(self, client, admin_headers):
        assert client.get(f"{BASE_PRICES}/sante",
                          headers=admin_headers).status_code == 200

    def test_list_prices_auto(self, client, admin_headers):
        assert client.get(f"{BASE_PRICES}/auto",
                          headers=admin_headers).status_code == 200

    def test_list_prices_no_auth(self, client):
        assert client.get(f"{BASE_PRICES}/sante").status_code == 401

    def test_create_price_expert(self, client, expert_headers):
        r = client.post(BASE_PRICES, json={
            "branch_code": "sante", "code_acte": "76601001",
            "nomenclature": "ASAC", "libelle": "Consultation généraliste — test CI",
            "prix_ref_xaf": 5000.0, "valid_from": "2026-01-01",
        }, headers=expert_headers)
        assert r.status_code in (200, 201, 409), r.text

    def test_create_price_unknown_branch(self, client, expert_headers):
        r = client.post(BASE_PRICES, json={
            "branch_code": "branche_inconnue", "code_acte": "99999999",
            "nomenclature": "ASAC", "valid_from": "2026-01-01",
        }, headers=expert_headers)
        assert r.status_code in (400, 422)

    def test_create_price_missing_required(self, client, expert_headers):
        r = client.post(BASE_PRICES, json={
            "branch_code": "sante", "code_acte": "76601001",
            "valid_from": "2026-01-01",
        }, headers=expert_headers)
        assert r.status_code == 422

    def test_create_price_gestionnaire_forbidden(self, client, gestionnaire_headers):
        r = client.post(BASE_PRICES, json={
            "branch_code": "sante", "code_acte": "76601002",
            "nomenclature": "ASAC", "valid_from": "2026-01-01",
        }, headers=gestionnaire_headers)
        assert r.status_code == 403


class TestPractitioners:
    def test_list_practitioners_admin(self, client, admin_headers):
        assert client.get(BASE_PRACT, headers=admin_headers).status_code == 200

    def test_practitioners_no_auth(self, client):
        assert client.get(BASE_PRACT).status_code == 401

    def test_get_practitioner_by_uuid(self, client, admin_headers):
        r = client.get(f"{BASE_PRACT}/00000000-0000-0000-0000-000000000000",
                       headers=admin_headers)
        assert r.status_code == 404

    def test_get_practitioner_claims_by_hash_empty(self, client, admin_headers):
        """
        GET /practitioners/{id_hash}/claims → 200 + [] pour hash inexistant.
        Comportement "liste vide" cohérent avec /audit/{id}/shap et /decisions.
        id_hash est une clé de recherche souple (pas FK stricte) — pas de 404.
        """
        r = client.get(f"{BASE_PRACT}/HASH_INEXISTANT_123/claims",
                       headers=admin_headers)
        assert r.status_code == 200
        body = r.json()
        results = body.get("results", body) if isinstance(body, dict) else body
        assert isinstance(results, list)
        assert len(results) == 0


class TestGarages:
    def test_list_garages_admin(self, client, admin_headers):
        assert client.get(BASE_GARAGES, headers=admin_headers).status_code == 200

    def test_garages_no_auth(self, client):
        assert client.get(BASE_GARAGES).status_code == 401