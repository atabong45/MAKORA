"""
Tests unitaires — core/llm/ (LLMNarrator + prompts)

Stratégie : Ollama est mocké (unittest.mock.patch) — les tests
ne nécessitent pas Ollama en fonctionnement.

Couvre :
- build_user_prompt : formatage du contexte
- build_fallback_narration : template de secours
- OllamaClient.generate : timeout, HTTPError
- LLMNarrator.generate : succès JSON, JSON invalide, Ollama KO
- LLMNarrator._parse_response : parsing et fallback
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from core.llm.narrator import LLMNarrator, OllamaClient
from core.llm.prompts import build_fallback_narration, build_user_prompt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_context() -> dict:
    return {
        "dossier_id": "SIN_2026_001",
        "anomaly_score": 0.87,
        "top_features": [
            {"feature_name": "ratio_prix_mercuriale", "feature_value": 2.1,
             "shap_value": 0.312},
            {"feature_name": "historique_ratio_praticien", "feature_value": 1.5,
             "shap_value": 0.187},
        ],
        "rca_diagnostic": {
            "category": "Fraude Financière",
            "subcategory": "Surfacturation",
            "rule_triggered": "RCA_SURF_001",
            "confidence": 0.91,
        },
    }


@pytest.fixture
def mock_ollama_client() -> MagicMock:
    client = MagicMock(spec=OllamaClient)
    client.model = "qwen2.5:7b"
    client.base_url = "http://ollama:11434/api/generate"
    return client


# ---------------------------------------------------------------------------
# Tests — build_user_prompt
# ---------------------------------------------------------------------------

class TestBuildUserPrompt:

    def test_contains_dossier_id(self, sample_context):
        prompt = build_user_prompt(sample_context)
        assert "SIN_2026_001" in prompt

    def test_contains_anomaly_score(self, sample_context):
        prompt = build_user_prompt(sample_context)
        assert "0.87" in prompt

    def test_contains_feature_names(self, sample_context):
        prompt = build_user_prompt(sample_context)
        assert "ratio_prix_mercuriale" in prompt

    def test_contains_rca_category(self, sample_context):
        prompt = build_user_prompt(sample_context)
        assert "Fraude Financière" in prompt

    def test_empty_features_handled(self):
        ctx = {"dossier_id": "X", "anomaly_score": 0.75,
               "top_features": [], "rca_diagnostic": {}}
        prompt = build_user_prompt(ctx)
        assert "non disponibles" in prompt

    def test_indeterminate_rca_handled(self):
        ctx = {"dossier_id": "X", "anomaly_score": 0.75,
               "top_features": [],
               "rca_diagnostic": {"category": "Indéterminée"}}
        prompt = build_user_prompt(ctx)
        assert "Aucune règle" in prompt


# ---------------------------------------------------------------------------
# Tests — build_fallback_narration
# ---------------------------------------------------------------------------

class TestBuildFallbackNarration:

    def test_contains_dossier_id(self, sample_context):
        text = build_fallback_narration(sample_context)
        assert "SIN_2026_001" in text

    def test_contains_score(self, sample_context):
        text = build_fallback_narration(sample_context)
        assert "0.87" in text

    def test_contains_rca_category_when_present(self, sample_context):
        text = build_fallback_narration(sample_context)
        assert "Fraude Financière" in text

    def test_no_rca_still_returns_text(self):
        ctx = {"dossier_id": "Y", "anomaly_score": 0.72,
               "top_features": [], "rca_diagnostic": {}}
        text = build_fallback_narration(ctx)
        assert "Y" in text
        assert len(text) > 10


# ---------------------------------------------------------------------------
# Tests — LLMNarrator avec Ollama mocké
# ---------------------------------------------------------------------------

class TestLLMNarratorGenerate:

    def test_successful_llm_response(self, sample_context, mock_ollama_client):
        """Ollama répond avec un JSON valide."""
        valid_json = '{"titre": "Surfacturation détectée", "resume": "Prix excessif.", "analyse": "Le ratio est à 2.1.", "recommandation": "Enquêter."}'
        mock_ollama_client.generate.return_value = valid_json

        narrator = LLMNarrator(backend=mock_ollama_client)
        result = narrator.generate(sample_context)

        assert "Surfacturation détectée" in result
        mock_ollama_client.generate.assert_called_once()

    def test_ollama_timeout_triggers_fallback(self, sample_context, mock_ollama_client):
        """Timeout Ollama → fallback template activé."""
        mock_ollama_client.generate.side_effect = requests.Timeout("timeout")

        narrator = LLMNarrator(backend=mock_ollama_client)
        result = narrator.generate(sample_context)

        # Fallback doit contenir le dossier_id
        assert "SIN_2026_001" in result

    def test_ollama_connection_error_triggers_fallback(self, sample_context,
                                                        mock_ollama_client):
        """Connexion refusée → fallback template."""
        mock_ollama_client.generate.side_effect = requests.ConnectionError("refused")

        narrator = LLMNarrator(backend=mock_ollama_client)
        result = narrator.generate(sample_context)

        assert "SIN_2026_001" in result

    def test_invalid_json_response_triggers_fallback(self, sample_context,
                                                      mock_ollama_client):
        """LLM répond un texte libre (pas de JSON) → fallback template."""
        mock_ollama_client.generate.return_value = "Désolé, je ne comprends pas."

        narrator = LLMNarrator(backend=mock_ollama_client)
        result = narrator.generate(sample_context)

        # Le fallback est retourné
        assert "SIN_2026_001" in result

    def test_json_with_markdown_fences(self, sample_context, mock_ollama_client):
        """LLM entoure le JSON de backticks → parsing doit réussir."""
        wrapped = '```json\n{"titre": "Test", "resume": "OK", "analyse": "Detail.", "recommandation": "Agir."}\n```'
        mock_ollama_client.generate.return_value = wrapped

        narrator = LLMNarrator(backend=mock_ollama_client)
        result = narrator.generate(sample_context)

        assert "Test" in result

    def test_repr(self, mock_ollama_client):
        narrator = LLMNarrator(backend=mock_ollama_client)
        assert "LLMNarrator" in repr(narrator)