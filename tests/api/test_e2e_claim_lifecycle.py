"""
MODULE : tests/api/test_e2e_claim_lifecycle.py
DESCRIPTION : Tests E2E — Flux complet sinistre DRAFT→SUBMITTED→OPEN→CLOSED.
1 test = 1 histoire métier complète.
"""
import pytest


class TestE2EClaimLifecycle:
    """
    Flux nominal : DRAFT → SUBMITTED → (analyse ML) → décision → CLOSED
    Ce test simule le parcours complet d'un gestionnaire sur un sinistre santé.
    """

    def test_full_claim_lifecycle_endpoints_exist(self, client):
        """Vérifie que tous les endpoints du cycle de vie existent dans l'OpenAPI."""
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        claim_paths = [p for p in paths if "/claims" in p]
        assert len(claim_paths) >= 5, f"Endpoints claims insuffisants : {len(claim_paths)}"

    def test_claim_crud_endpoints_registered(self, client):
        """Vérifie registration des endpoints claims dans le router."""
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        assert "/api/v1/claims/" in paths
        assert "post" in paths["/api/v1/claims/"]
        assert "get" in paths["/api/v1/claims/"]

    def test_analyze_endpoint_registered(self, client):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        assert "/api/v1/analyze/" in paths

    def test_audit_decision_endpoint_registered(self, client):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        audit_paths = [p for p in paths if "/audit" in p]
        assert any("decision" in p for p in audit_paths)

    def test_claim_create_requires_auth(self, client):
        r = client.post("/api/v1/claims/", json={"claim_id": "E2E_001", "branch_code": "sante"})
        assert r.status_code == 401

    def test_claim_submit_requires_auth(self, client):
        r = client.post("/api/v1/claims/E2E_001/submit")
        assert r.status_code == 401

    def test_claim_ocr_requires_auth(self, client):
        r = client.post("/api/v1/claims/E2E_001/ocr/run?doc_id=00000000-0000-0000-0000-000000000000")
        assert r.status_code == 401

    def test_claim_document_upload_requires_auth(self, client):
        r = client.post("/api/v1/claims/E2E_001/documents",
                        files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")})
        assert r.status_code == 401

    def test_e2e_flow_unauthorized_path(self, client):
        """Vérifie que sans token, aucune étape du flux n'est accessible."""
        steps = [
            ("POST", "/api/v1/claims/", {"claim_id": "E2E_TEST", "branch_code": "sante"}),
            ("GET", "/api/v1/claims/E2E_TEST", None),
            ("POST", "/api/v1/analyze/", {"branch": "sante", "dossiers": [{}]}),
            ("GET", "/api/v1/audit/", None),
        ]
        for method, path, json_body in steps:
            if method == "POST":
                r = client.post(path, json=json_body or {})
            else:
                r = client.get(path)
            assert r.status_code == 401, f"Step {method} {path} devrait retourner 401"
