"""
MODULE : tests/api/authenticated/test_analyze_flow.py
DESCRIPTION : Tests flux analyse ML.

NOTE : Les tests de création de claims dans ce fichier (TestClaimsAuth,
TestClaimsCRUDGestionnaire) utilisent des claim_id uuid aléatoires pour
éviter les conflits 409 avec test_claims_crud.py (même DB de session).
"""
import uuid
import pytest

BASE_CLAIMS  = "/api/v1/claims"
BASE_ANALYZE = "/api/v1/analyze/"
BASE_RUNS    = "/api/v1/analyze/runs"


def _claim_payload(branch: str) -> dict:
    return {
        "claim_id":    f"SIN-{branch.upper()}-{uuid.uuid4().hex[:8].upper()}",
        "branch_code": branch,
        "source_flux": "structured",
        "montant_facture": 45000.0,
        "devise": "XAF",
        "date_soin": "2026-04-15",
    }


def _analyze_payload(branch: str) -> dict:
    return {
        "branch":  branch,
        "source":  "TEST_CI",
        "dossiers": [
            {
                "ID_Sinistre":      "SIN-TEST-001",
                "ID_Assure":        "ASS-001",
                "ID_Praticien":     "PRAT-001",
                "Code_Acte":        "76601001",
                "Montant_Facture":  45000.0,
                "Prix_Unitaire_Ref": 5000.0,
                "Devise":           "XAF",
                "Taux_Change":      1.0,
                "Date_Soin":        "2026-04-15",
                "Source_Flux":      "Scan_CM",
            }
        ],
    }


# ── Tests claims dans ce fichier (évite duplication mais IDs uniques) ─────────
class TestClaimsAuth:
    def test_list_claims_no_auth(self, client):
        assert client.get(BASE_CLAIMS).status_code == 401

    def test_create_claim_no_auth(self, client):
        assert client.post(BASE_CLAIMS, json=_claim_payload("sante")).status_code == 401


class TestClaimsCRUDGestionnaire:
    def test_create_claim_sante(self, client, gestionnaire_headers):
        r = client.post(BASE_CLAIMS, json=_claim_payload("sante"),
                        headers=gestionnaire_headers)
        assert r.status_code in (200, 201), r.text

    def test_create_claim_auto(self, client, gestionnaire_headers):
        r = client.post(BASE_CLAIMS, json=_claim_payload("auto"),
                        headers=gestionnaire_headers)
        assert r.status_code in (200, 201), r.text

    def test_list_claims(self, client, gestionnaire_headers):
        assert client.get(BASE_CLAIMS, headers=gestionnaire_headers).status_code == 200

    def test_get_nonexistent_claim(self, client, gestionnaire_headers):
        assert client.get(f"{BASE_CLAIMS}/SIN-NEVEREXISTS-AF",
                          headers=gestionnaire_headers).status_code == 404

    def test_create_and_get_claim(self, client, gestionnaire_headers):
        payload = _claim_payload("sante")
        r = client.post(BASE_CLAIMS, json=payload, headers=gestionnaire_headers)
        assert r.status_code in (200, 201), r.text
        claim_id = r.json()["id"]
        r2 = client.get(f"{BASE_CLAIMS}/{payload['claim_id']}",
                        headers=gestionnaire_headers)
        assert r2.status_code == 200
        assert r2.json()["id"] == claim_id

    def test_create_missing_required(self, client, gestionnaire_headers):
        r = client.post(BASE_CLAIMS, json={"claim_id": "X"},
                        headers=gestionnaire_headers)
        assert r.status_code == 422

    def test_source_flux_invalid_enum(self, client, gestionnaire_headers):
        payload = _claim_payload("sante")
        payload["source_flux"] = "INVALIDE"
        r = client.post(BASE_CLAIMS, json=payload, headers=gestionnaire_headers)
        assert r.status_code == 422

    def test_submit_claim(self, client, gestionnaire_headers):
        payload = _claim_payload("sante")
        r = client.post(BASE_CLAIMS, json=payload, headers=gestionnaire_headers)
        assert r.status_code in (200, 201), r.text
        r2 = client.post(f"{BASE_CLAIMS}/{payload['claim_id']}/submit",
                         headers=gestionnaire_headers)
        assert r2.status_code in (200, 201)

    def test_claim_appears_in_list(self, client, gestionnaire_headers):
        """
        Utilise GET /claims/{claim_id} plutôt que le scan de liste paginée
        (instable avec une DB live accumulant les runs).
        """
        payload = _claim_payload("sante")
        r = client.post(BASE_CLAIMS, json=payload, headers=gestionnaire_headers)
        assert r.status_code in (200, 201)
        created_uuid = r.json()["id"]

        r_get = client.get(f"{BASE_CLAIMS}/{payload['claim_id']}",
                        headers=gestionnaire_headers)
        assert r_get.status_code == 200
        assert r_get.json()["id"] == created_uuid

        r_list = client.get(BASE_CLAIMS, headers=gestionnaire_headers)
        assert r_list.status_code == 200
        body = r_list.json()
        assert isinstance(body.get("results", []), list)
        assert body.get("total", 0) >= 1


class TestClaimsRBAC:
    def test_auditeur_can_read(self, client, auditeur_headers):
        assert client.get(BASE_CLAIMS, headers=auditeur_headers).status_code == 200

    def test_auditeur_cannot_create(self, client, auditeur_headers):
        assert client.post(BASE_CLAIMS, json=_claim_payload("sante"),
                           headers=auditeur_headers).status_code == 403

    def test_ds_cannot_create(self, client, ds_headers):
        assert client.post(BASE_CLAIMS, json=_claim_payload("sante"),
                           headers=ds_headers).status_code == 403

    def test_expert_cannot_create(self, client, expert_headers):
        assert client.post(BASE_CLAIMS, json=_claim_payload("sante"),
                           headers=expert_headers).status_code == 403


# ── Tests analyse ML ──────────────────────────────────────────────────────────
class TestAnalyzeAuth:
    def test_analyze_no_auth(self, client):
        assert client.post(BASE_ANALYZE, json=_analyze_payload("sante")).status_code == 401

    def test_runs_no_auth(self, client):
        assert client.get(BASE_RUNS).status_code == 401


class TestAnalyzeSante:
    def test_analyze_sante_gestionnaire(self, client, gestionnaire_headers):
        r = client.post(BASE_ANALYZE, json=_analyze_payload("sante"),
                        headers=gestionnaire_headers)
        assert r.status_code in (200, 201, 503), f"{r.status_code} {r.text[:300]}"

    def test_analyze_missing_branch(self, client, gestionnaire_headers):
        r = client.post(BASE_ANALYZE, json={"dossiers": [{}]},
                        headers=gestionnaire_headers)
        assert r.status_code == 422

    def test_analyze_missing_dossiers(self, client, gestionnaire_headers):
        r = client.post(BASE_ANALYZE, json={"branch": "sante"},
                        headers=gestionnaire_headers)
        assert r.status_code == 422


class TestAnalyzeAuto:
    def test_analyze_auto_gestionnaire(self, client, gestionnaire_headers):
        r = client.post(BASE_ANALYZE, json=_analyze_payload("auto"),
                        headers=gestionnaire_headers)
        assert r.status_code in (200, 201, 503)


class TestAnalyzeRuns:
    def test_list_runs_admin(self, client, admin_headers):
        assert client.get(BASE_RUNS, headers=admin_headers).status_code == 200

    def test_list_runs_auditeur(self, client, auditeur_headers):
        assert client.get(BASE_RUNS, headers=auditeur_headers).status_code == 200

    def test_get_nonexistent_run(self, client, admin_headers):
        r = client.get(f"{BASE_RUNS}/00000000-0000-0000-0000-000000000000",
                       headers=admin_headers)
        assert r.status_code == 404


class TestAnalyzeKernelIsolation:
    def test_unknown_branch_no_500(self, client, gestionnaire_headers):
        r = client.post(BASE_ANALYZE,
                        json={"branch": "branche_inexistante", "dossiers": [{}]},
                        headers=gestionnaire_headers)
        assert r.status_code != 500, "ADR-002 VIOLÉ"
        assert r.status_code in (400, 404, 422, 503)

    def test_no_auth_returns_401(self, client):
        assert client.post(BASE_ANALYZE,
                           json={"branch": "sante", "dossiers": []}).status_code == 401