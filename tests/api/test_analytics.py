"""
MODULE : tests/api/test_analytics.py
DESCRIPTION : Tests API — Analytics dashboard (5 endpoints).
"""
import pytest


class TestAnalytics:
    def test_dashboard_no_auth(self, client):
        assert client.get("/api/v1/analytics/dashboard").status_code == 401

    def test_top_features_no_auth(self, client):
        assert client.get("/api/v1/analytics/shap/top-features").status_code == 401

    def test_rca_distribution_no_auth(self, client):
        assert client.get("/api/v1/analytics/rca/distribution").status_code == 401

    def test_model_performance_no_auth(self, client):
        assert client.get("/api/v1/analytics/models/performance").status_code == 401

    def test_period_days_negative(self, client, admin_token):
        headers = {"Authorization": f"Bearer {admin_token}"}
        r = client.get("/api/v1/analytics/dashboard?period_days=-1", headers=headers)
        assert r.status_code in (401, 422)

    def test_openapi_analytics_endpoints(self, client):
        r = client.get("/api/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        assert any("/analytics" in p for p in paths)
