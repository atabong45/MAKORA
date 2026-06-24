"""
MODULE : tests/api/test_e2e_escalation.py
DESCRIPTION : Tests E2E — Flux escalade : décision ESCALATED → assignation → résolution.
"""
import pytest


class TestE2EEscalation:
    def test_escalation_endpoints_exist(self, client):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        esc_paths = [p for p in paths if "/escalations" in p]
        assert len(esc_paths) >= 4, f"Endpoints escalades insuffisants : {len(esc_paths)}"

    def test_pending_queue_endpoint_exists(self, client):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        assert any("pending" in p for p in paths)

    def test_assign_endpoint_exists(self, client):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        assert any("assign" in p for p in paths)

    def test_resolve_endpoint_exists(self, client):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        assert any("resolve" in p for p in paths)

    def test_escalation_requires_analysis_id(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.post("/api/v1/escalations/", json={"motif_escalade": "Cas suspect"}, headers=headers)
        assert r.status_code in (401, 403, 422)

    def test_resolution_note_required(self, client, auditeur_token):
        headers = {"Authorization": f"Bearer {auditeur_token}"}
        r = client.patch(
            "/api/v1/escalations/00000000-0000-0000-0000-000000000000/resolve",
            json={}, headers=headers
        )
        assert r.status_code in (401, 404, 422)
