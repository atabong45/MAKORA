"""
MODULE : core/llm/narrator.py
DESCRIPTION : Narrateur LLM pour MAKORA — génère des explications en français
              via Qwen 2.5:7b (Ollama) avec fallback template.

RÉFÉRENCES ACADÉMIQUES :
- [Jiang2023] Jiang et al. (2023). Mistral 7B. arXiv:2310.06825.
  → Architecture de référence pour les LLM 7B instruction-following.
    Qwen 2.5:7b retenu (ADR-003) pour ses meilleures performances
    en français et en génération JSON structuré.
- [Wei2022] Wei et al. (2022). Chain-of-thought prompting. NeurIPS.
  → Le prompt structure le raisonnement en étapes explicites.
- [Lundberg2017] Lundberg & Lee (2017). SHAP. NeurIPS.
  → Les valeurs SHAP sont intégrées dans le contexte LLM pour
    ancrer l'explication dans les features réelles du modèle.

DÉCISIONS DE CONCEPTION :
- Ollama est appelé via HTTP (pas de SDK) pour minimiser les dépendances.
- Le timeout est configurable (default 30s) — jamais hardcodé.
- Si Ollama est KO → fallback template immédiat (non-bloquant).
- La réponse JSON d'Ollama est parsée et retournée comme texte formaté.
  Si le parsing échoue → fallback template.
- Le LLMNarrator est STATELESS : peut être instancié une fois et réutilisé.
"""

from __future__ import annotations

import json
from typing import Any

import requests

from core.llm.prompts import SYSTEM_PROMPT, build_fallback_narration, build_user_prompt
from core.logging_config import get_logger
from core.llm.backend import LLMBackend, build_backend

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constantes — valeurs par défaut (surchargées par config YAML si fourni)
# ---------------------------------------------------------------------------

_DEFAULT_OLLAMA_URL = "http://ollama:11434/api/generate"
_DEFAULT_MODEL = "qwen2.5:7b"
_DEFAULT_TIMEOUT_S = 30
_DEFAULT_MAX_TOKENS = 512


class OllamaClient:
    """
    Client HTTP minimal pour l'API Ollama.
    Séparé de LLMNarrator pour faciliter le mock dans les tests.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_OLLAMA_URL,
        model: str = _DEFAULT_MODEL,
        timeout_s: int = _DEFAULT_TIMEOUT_S,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self.base_url = base_url
        self.model = model
        self.timeout_s = timeout_s
        self.max_tokens = max_tokens

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Appelle l'endpoint /api/generate d'Ollama.

        Args:
            system_prompt: instruction système.
            user_prompt: prompt utilisateur.

        Returns:
            Texte brut généré par le modèle.

        Raises:
            requests.RequestException: si Ollama est inaccessible.
            ValueError: si la réponse ne contient pas de champ 'response'.
        """
        payload = {
            "model": self.model,
            "prompt": f"<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>",
            "stream": False,
            "options": {"num_predict": self.max_tokens, "temperature": 0.3},
        }

        response = requests.post(
            self.base_url,
            json=payload,
            timeout=self.timeout_s,
        )
        response.raise_for_status()
        data = response.json()

        if "response" not in data:
            raise ValueError(f"Réponse Ollama sans champ 'response' : {data}")

        return data["response"].strip()

    def is_available(self) -> bool:
        """Vérifie la disponibilité d'Ollama (appel léger sur /api/tags)."""
        try:
            url = self.base_url.replace("/api/generate", "/api/tags")
            resp = requests.get(url, timeout=3)
            return resp.status_code == 200
        except requests.RequestException:
            return False



class LLMNarrator:
    def __init__(
        self,
        backend: LLMBackend | OllamaClient | None = None,
        config: dict | None = None,
    ) -> None:
        cfg = config or {}
        if isinstance(backend, OllamaClient):
            # Adaptateur : OllamaClient → LLMBackend
            # Permet le mock des tests avec spec=OllamaClient
            from core.llm.ollama_backend import OllamaBackend
            _client = backend
            class _AdaptedBackend(LLMBackend):
                @property
                def name(self) -> str:
                    return "ollama_adapted"
                def is_available(self) -> bool:
                    return True
                def complete(self, system_prompt: str, user_prompt: str):
                    from core.llm.backend import LLMResponse
                    import requests
                    try:
                        text = _client.generate(system_prompt, user_prompt)
                        return LLMResponse(text=text, success=True, backend_name="ollama_adapted")
                    except (requests.Timeout, requests.ConnectionError) as e:
                        return LLMResponse.ko(str(e), backend_name="ollama_adapted")
            self.backend = _AdaptedBackend()
            self._client_ref = backend
        else:
            self.backend = backend or build_backend(
                ollama_url=cfg.get("ollama_url"),
                model=cfg.get("model"),
            )
            self._client_ref = None

    def __repr__(self) -> str:
        return f"LLMNarrator(backend={self.backend!r})"

    def generate(self, context: dict) -> str:
        user_prompt = build_user_prompt(context)
        resp = self.backend.complete(SYSTEM_PROMPT, user_prompt)
        if not resp.success:
            logger.warning("LLM KO (%s) — fallback activé.", resp.error)
            return build_fallback_narration(context)
        return self._parse_response(resp.text, context)
    



    @staticmethod
    def _parse_response(raw: str, context: dict[str, Any]) -> str:
        """
        Parse la réponse JSON du LLM et formate en texte lisible.
        Si le JSON est invalide → fallback template.

        Args:
            raw: réponse brute du LLM.
            context: contexte original (pour le fallback).

        Returns:
            str — texte formaté ou fallback.
        """
        try:
            # Nettoyage des balises markdown éventuelles
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("```")[1]
                if cleaned.startswith("json"):
                    cleaned = cleaned[4:]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            titre = data.get("titre", "")
            resume = data.get("resume", "")
            analyse = data.get("analyse", "")
            recommandation = data.get("recommandation", "")

            parts = [p for p in [titre, resume, analyse, recommandation] if p]
            return " | ".join(parts) if parts else build_fallback_narration(context)

        except (json.JSONDecodeError, KeyError) as exc:
            logger.warning(
                "Parsing réponse LLM échoué (%s) — fallback template.", exc
            )
            return build_fallback_narration(context)
