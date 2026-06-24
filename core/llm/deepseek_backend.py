"""
MODULE : core/llm/deepseek_backend.py
DESCRIPTION : Implémentation LLMBackend pour DeepSeek via API OpenAI-compatible.

RÉFÉRENCES ACADÉMIQUES :
- [Gamma1994] Design Patterns — Strategy.
  → DeepSeekBackend est l'implémentation concrète Strategy pour l'API cloud.
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML. NeurIPS.
  → Les credentials (API key) sont lus depuis les variables d'environnement,
    jamais hardcodés — évite la dette de sécurité.

DÉCISIONS DE CONCEPTION :
- L'API DeepSeek est OpenAI-compatible : même format messages, même endpoint
  /v1/chat/completions. Permet de réutiliser le SDK openai si disponible,
  ou de tomber en fallback urllib si le SDK est absent.
- temperature=0.0 forcée pour la cohérence JSON (reproductibilité ADR-005).
- La clé API est lue depuis DEEPSEEK_API_KEY — jamais passée en dur.
- is_available() fait un appel minimal (max_tokens=1) pour vérifier le quota.

NOTER POUR LE MÉMOIRE :
- DeepSeek est utilisé en phase de développement (clé API disponible).
- En production Cameroun, le switch vers Ollama local garantit la souveraineté
  des données médicales (BNF-03 — pas de données patient hors site). [ADR-003]
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

from core.llm.backend import LLMBackend, LLMResponse
from core.logging_config import get_logger

logger = get_logger(__name__)

_DEEPSEEK_BASE_URL  = "https://api.deepseek.com"
_DEFAULT_MODEL      = "deepseek-chat"
_DEFAULT_TIMEOUT    = 60
_DEFAULT_MAX_TOKENS = 1024


class DeepSeekBackend(LLMBackend):
    """
    Backend LLM DeepSeek — API cloud OpenAI-compatible.

    Tente d'utiliser le SDK `openai` si disponible (plus robuste),
    sinon fallback sur urllib (zéro dépendance supplémentaire).

    Usage :
        backend = DeepSeekBackend(api_key=os.environ["DEEPSEEK_API_KEY"])
        resp = backend.complete(system_prompt, user_prompt)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = _DEFAULT_MODEL,
        base_url: str = _DEEPSEEK_BASE_URL,
        timeout_s: int = _DEFAULT_TIMEOUT,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        self._api_key   = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self._model     = model
        self._base_url  = base_url.rstrip("/")
        self._timeout   = timeout_s
        self._max_tokens = max_tokens

        if not self._api_key:
            logger.warning("[DeepSeek] DEEPSEEK_API_KEY non définie — les appels échoueront.")

    @property
    def name(self) -> str:
        return "deepseek"

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """
        Appelle l'API DeepSeek /v1/chat/completions.
        Format OpenAI : messages=[{role, content}, ...].
        """
        # Essai SDK openai (plus robuste pour retry/streaming)
        try:
            from openai import OpenAI
            return self._complete_sdk(system_prompt, user_prompt)
        except ImportError:
            pass

        # Fallback urllib (zéro dépendance)
        return self._complete_urllib(system_prompt, user_prompt)

    def _complete_sdk(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Appel via SDK openai (si disponible)."""
        try:
            from openai import OpenAI, APIError, APITimeoutError

            client = OpenAI(api_key=self._api_key, base_url=self._base_url)
            response = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
                temperature=0.0,
                max_tokens=self._max_tokens,
                timeout=self._timeout,
            )
            text = response.choices[0].message.content or ""
            return LLMResponse(text=text.strip(), success=True, backend_name=self.name)

        except Exception as e:
            logger.warning("[DeepSeek SDK] Erreur : %s", e)
            return LLMResponse.ko(str(e), self.name)

    def _complete_urllib(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Appel via urllib — fallback si SDK openai absent."""
        payload = json.dumps({
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": self._max_tokens,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self._base_url}/v1/chat/completions",
            data=payload,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            text = data["choices"][0]["message"]["content"] or ""
            return LLMResponse(text=text.strip(), success=True, backend_name=self.name)

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="ignore")[:200]
            logger.warning("[DeepSeek] HTTP %d : %s", e.code, body)
            return LLMResponse.ko(f"HTTP_{e.code}", self.name)
        except urllib.error.URLError as e:
            logger.warning("[DeepSeek] URLError : %s", e.reason)
            return LLMResponse.ko("CONNECTION_ERROR", self.name)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.warning("[DeepSeek] Réponse malformée : %s", e)
            return LLMResponse.ko("MALFORMED_RESPONSE", self.name)
        except Exception as e:
            logger.warning("[DeepSeek] Erreur inattendue : %s", e)
            return LLMResponse.ko(str(e), self.name)

    def is_available(self) -> bool:
        """Vérifie la disponibilité via un appel minimal (1 token)."""
        if not self._api_key:
            return False
        resp = self._complete_urllib("ping", "pong")
        return resp.success

    def __repr__(self) -> str:
        masked = f"{self._api_key[:8]}..." if self._api_key else "None"
        return f"DeepSeekBackend(model={self._model!r}, api_key={masked!r})"