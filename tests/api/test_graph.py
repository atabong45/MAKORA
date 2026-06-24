"""
MODULE : tests/api/test_graph.py
DESCRIPTION : Tests API — Graphe de fraude Louvain (4 endpoints).
"""
import pytest


class TestGraph:
    def test_communities_no_auth(self, client):
        assert client.get("/api/v1/graph/communities").status_code == 401

    def test_community_detail_no_auth(self, client):
        r = client.get("/api/v1/graph/communities/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 401

    def test_members_no_auth(self, client):
        r = client.get("/api/v1/graph/communities/00000000-0000-0000-0000-000000000000/members")
        assert r.status_code == 401

    def test_run_communities_no_auth(self, client):
        r = client.get("/api/v1/graph/runs/00000000-0000-0000-0000-000000000000/communities")
        assert r.status_code == 401

    def test_community_gestionnaire_forbidden(self, client, gestionnaire_token):
        headers = {"Authorization": f"Bearer {gestionnaire_token}"}
        r = client.get("/api/v1/graph/communities", headers=headers)
        assert r.status_code in (401, 403)

    def test_nonexistent_community(self, client, auditeur_token):
        headers = {"Authorization": f"Bearer {auditeur_token}"}
        r = client.get("/api/v1/graph/communities/00000000-0000-0000-0000-000000000000", headers=headers)
        assert r.status_code in (401, 404)
