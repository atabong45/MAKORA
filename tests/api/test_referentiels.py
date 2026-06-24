"""
MODULE : tests/api/test_referentiels.py
DESCRIPTION : Tests API — Référentiels pseudonymisés (13 endpoints).
"""
import pytest


class TestReferentiels:
    def test_practitioners_no_auth(self, client):
        assert client.get("/api/v1/referentiels/practitioners").status_code == 401

    def test_garages_no_auth(self, client):
        assert client.get("/api/v1/referentiels/garages").status_code == 401

    def test_prices_no_auth(self, client):
        assert client.get("/api/v1/referentiels/prices/sante").status_code == 401

    def test_insured_no_auth(self, client):
        assert client.get("/api/v1/referentiels/insureds/HASH123").status_code == 401

    def test_employer_no_auth(self, client):
        r = client.get("/api/v1/referentiels/employers/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 401

    def test_import_price_no_auth(self, client):
        r = client.post("/api/v1/referentiels/prices", json={
            "branch_code": "sante", "code_acte": "C001",
            "nomenclature": "CCAM", "valid_from": "2025-01-01", "devise_principale": "XAF"
        })
        assert r.status_code == 401

    def test_import_price_missing_fields(self, client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = client.post("/api/v1/referentiels/prices",
                        json={"branch_code": "sante"}, headers=headers)
        assert r.status_code in (401, 422)
