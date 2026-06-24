"""
MODULE : tests/api/test_analyze.py
DESCRIPTION : Tests API — Pipeline d'analyse ML (4 endpoints).
Vérifie l'isolation Kernel (ADR-002) via le service.
"""
import pathlib

import pytest


class TestAnalyzeAuth:
    def test_analyze_no_auth(self, client):
        r = client.post("/api/v1/analyze/", json={"branch": "sante", "dossiers": [{}]})
        assert r.status_code == 401

    def test_analyze_missing_branch(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.post("/api/v1/analyze/", json={"dossiers": [{"ID_Sinistre": "T001"}]}, headers=headers)
        assert r.status_code in (401, 422)

    def test_analyze_unknown_branch(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.post("/api/v1/analyze/",
                        json={"branch": "UNKNOWN_BRANCH", "dossiers": [{"ID_Sinistre": "T001"}]},
                        headers=headers)
        assert r.status_code in (400, 401, 503)

    def test_runs_no_auth(self, client):
        r = client.get("/api/v1/analyze/runs")
        assert r.status_code == 401

    def test_run_detail_invalid_id(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.get("/api/v1/analyze/runs/00000000-0000-0000-0000-000000000000", headers=headers)
        assert r.status_code in (401, 404)

    def test_upload_wrong_mime(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.post("/api/v1/analyze/upload?branch=sante",
                        files={"file": ("test.txt", b"plain text", "text/plain")}, headers=headers)
        assert r.status_code in (401, 415, 422)


class TestKernelIsolation:
    def test_analyze_service_no_direct_import(self):
        """ADR-002 : analyze_service.py ne doit pas importer de module métier par nom concret."""
        import ast, pathlib
        src = (pathlib.Path(__file__).parent.parent.parent / "api" / "services" / "analyze_service.py").read_text()
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not mod.startswith("modules.sante"), f"Import interdit détecté : {mod}"
                assert not mod.startswith("modules.auto"), f"Import interdit détecté : {mod}"
                assert not mod.startswith("modules.vie"), f"Import interdit détecté : {mod}"
