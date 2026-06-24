"""
MODULE : core/llm/ollama_backend.py
DESCRIPTION : Implémentation LLMBackend pour Ollama (modèle local).
              Wrapper autour du OllamaClient existant dans narrator.py.

RÉFÉRENCES ACADÉMIQUES :
- [Jiang2023] Jiang et al. (2023). Mistral 7B. arXiv:2310.06825.
  → Architecture de référence pour les LLM 7B. Qwen 2.5:7b retenu (ADR-003)
    pour ses meilleures performances en français et génération JSON.
- [Gamma1994] Design Patterns — Strategy.
  → OllamaBackend est l'implémentation concrète Strategy pour Ollama.

DÉCISIONS DE CONCEPTION :
- Appel HTTP direct via `requests` — pas de SDK Ollama officiel nécessaire.
- Format prompt : balises <|system|>/<|user|>/<|assistant|> compatibles
  Qwen 2.5 et Mistral instruction-following.
- Timeout configurable — jamais hardcodé (IMP-007).
- is_available() appelle /api/tags (endpoint léger sans génération).
"""

from __future__ import annotations

from typing import Optional

import requests

from core.llm.backend import LLMBackend, LLMResponse
from core.logging_config import get_logger

logger = get_logger(__name__)

_DEFAULT_URL   = "http://ollama:11434"
_DEFAULT_MODEL = "qwen2.5:7b"
_DEFAULT_TIMEOUT = 45
_DEFAULT_MAX_TOKENS = 512


class OllamaBackend(LLMBackend):
    """
    Backend LLM Ollama — appel au serveur local Ollama.

    Usage :
        backend = OllamaBackend()
        resp = backend.complete(system_prompt, user_prompt)
        if resp.success:
            print(resp.text)
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_URL,
        model: str = _DEFAULT_MODEL,
        timeout_s: int = _DEFAULT_TIMEOUT,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self._base_url  = base_url.rstrip("/")
        self._model     = model
        self._timeout   = timeout_s
        self._max_tokens = max_tokens

    @property
    def name(self) -> str:
        return "ollama"

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """
        Appelle /api/generate d'Ollama.

        Format prompt instruction-following compatible Qwen 2.5 / Mistral :
        <|system|> ... <|user|> ... <|assistant|>
        """
        prompt = (
            f"<|system|>\n{system_prompt}\n"
            f"<|user|>\n{user_prompt}\n"
            f"<|assistant|>"
        )
        payload = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": self._max_tokens,
                "temperature": 0.0,
            },
        }

        try:
            resp = requests.post(
                f"{self._base_url}/api/generate",
                json=payload,
                timeout=self._timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            text = data.get("response", "").strip()
            if not text:
                return LLMResponse.ko("EMPTY_RESPONSE", self.name)

            return LLMResponse(text=text, success=True, backend_name=self.name)

        except requests.Timeout:
            logger.warning("[Ollama] Timeout après %ds", self._timeout)
            return LLMResponse.ko("TIMEOUT", self.name)
        except requests.ConnectionError:
            logger.warning("[Ollama] Connexion refusée — serveur démarré ?")
            return LLMResponse.ko("CONNECTION_ERROR", self.name)
        except Exception as e:
            logger.warning("[Ollama] Erreur inattendue : %s", e)
            return LLMResponse.ko(str(e), self.name)

    def is_available(self) -> bool:
        """Ping /api/tags — endpoint léger sans génération."""
        try:
            resp = requests.get(
                f"{self._base_url}/api/tags",
                timeout=3,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def __repr__(self) -> str:
        return f"OllamaBackend(model={self._model!r}, url={self._base_url!r})"