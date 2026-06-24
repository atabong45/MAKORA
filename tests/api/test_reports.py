"""
MODULE : tests/api/test_reports.py
DESCRIPTION : Tests API — Exports et rapports BF-10 (5 endpoints).
"""
import pytest


class TestReports:
    def test_export_no_auth(self, client):
        r = client.post("/api/v1/reports/export", json={
            "report_type": "audit_decisions", "file_format": "csv"
        })
        assert r.status_code == 401

    def test_export_invalid_format(self, client, auditeur_token):
        headers = {"Authorization": f"Bearer {auditeur_token}"}
        r = client.post("/api/v1/reports/export",
                        json={"report_type": "audit_decisions", "file_format": "pdf"},
                        headers=headers)
        assert r.status_code in (401, 422)

    def test_export_invalid_type(self, client, auditeur_token):
        headers = {"Authorization": f"Bearer {auditeur_token}"}
        r = client.post("/api/v1/reports/export",
                        json={"report_type": "UNKNOWN_TYPE", "file_format": "csv"},
                        headers=headers)
        assert r.status_code in (401, 422)

    def test_download_nonexistent(self, client, auditeur_token):
        headers = {"Authorization": f"Bearer {auditeur_token}"}
        r = client.get(
            "/api/v1/reports/exports/00000000-0000-0000-0000-000000000000/download",
            headers=headers
        )
        assert r.status_code in (401, 404)

    def test_global_stats_no_auth(self, client):
        assert client.get("/api/v1/reports/stats/global").status_code == 401

    def test_list_my_exports_no_auth(self, client):
        assert client.get("/api/v1/reports/exports").status_code == 401
