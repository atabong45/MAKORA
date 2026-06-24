"""
MODULE : core/llm/backend.py
DESCRIPTION : Interface abstraite LLMBackend — Strategy Pattern pour les
              backends LLM de MAKORA (Ollama local, DeepSeek API, etc.).

RÉFÉRENCES ACADÉMIQUES :
- [Gamma1994] Gamma et al. (1994). Design Patterns. Pattern : Strategy.
  → LLMBackend est la stratégie abstraite. OllamaBackend et DeepSeekBackend
    sont les implémentations concrètes interchangeables. Le code appelant
    (LLMNarrator, DocumentaryReader) ne connaît que l'interface.
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML. NeurIPS.
  → Isoler les dépendances externes (LLM providers) derrière une interface
    réduit la dette technique lors des migrations de provider.

DÉCISIONS DE CONCEPTION :
- `complete()` retourne toujours un `LLMResponse` — jamais d'exception levée
  vers le code appelant. Les erreurs sont encapsulées dans success=False.
- `build_backend()` lit les variables d'environnement pour sélectionner le
  provider. Ordre de priorité : DEEPSEEK_API_KEY → Ollama local.
- Aucune configuration YAML ici — les variables d'environnement sont le bon
  niveau d'abstraction pour les credentials et URLs de providers externes.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from core.logging_config import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Contrat de réponse
# ---------------------------------------------------------------------------

@dataclass
class LLMResponse:
    """
    Réponse standardisée d'un backend LLM.
    Toujours retournée — jamais d'exception levée vers l'appelant.
    """
    text: str
    success: bool
    error: Optional[str] = None
    backend_name: str = "unknown"

    @classmethod
    def ko(cls, error: str, backend_name: str = "unknown") -> "LLMResponse":
        """Constructeur sémantique pour un échec."""
        return cls(text="", success=False, error=error, backend_name=backend_name)


# ---------------------------------------------------------------------------
# Interface abstraite — Strategy
# ---------------------------------------------------------------------------

class LLMBackend(ABC):
    """
    Interface Strategy pour les backends LLM.

    Toute implémentation concrète doit :
    - Retourner un LLMResponse depuis complete() — jamais lever d'exception.
    - Implémenter is_available() pour une vérification de santé légère.

    [Gamma1994] Strategy Pattern : le code appelant est découplé
    de l'implémentation concrete du provider LLM.
    """

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """
        Appelle le LLM et retourne sa réponse.

        Args:
            system_prompt: instruction système (rôle, contraintes format).
            user_prompt: contenu de la requête utilisateur.

        Returns:
            LLMResponse — toujours, même en cas d'erreur.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifiant du backend (ex: 'ollama', 'deepseek')."""

    @abstractmethod
    def is_available(self) -> bool:
        """Vérifie la disponibilité du backend (appel léger, sans génération)."""


# ---------------------------------------------------------------------------
# Factory — sélection automatique du backend
# ---------------------------------------------------------------------------

def build_backend(
    *,
    deepseek_api_key: Optional[str] = None,
    ollama_url: Optional[str] = None,
    model: Optional[str] = None,
) -> LLMBackend:
    """
    Construit le backend LLM approprié selon la configuration.

    Priorité :
    1. DeepSeek si DEEPSEEK_API_KEY est défini (ou passé en argument)
    2. Ollama sinon (fallback local)

    Args:
        deepseek_api_key: clé API DeepSeek (surcharge DEEPSEEK_API_KEY env).
        ollama_url: URL Ollama (surcharge OLLAMA_URL env).
        model: nom du modèle (surcharge le défaut du backend sélectionné).

    Returns:
        Instance concrète de LLMBackend.

    Example:
        # Lecture automatique depuis les variables d'environnement
        backend = build_backend()

        # Forçage DeepSeek en test
        backend = build_backend(deepseek_api_key="sk-test...")
    """
    # Lazy import pour éviter les imports circulaires
    from core.llm.deepseek_backend import DeepSeekBackend
    from core.llm.ollama_backend import OllamaBackend

    api_key = deepseek_api_key or os.getenv("DEEPSEEK_API_KEY", "")

    if api_key:
        logger.info("[LLM] Backend sélectionné : DeepSeek")
        return DeepSeekBackend(
            api_key=api_key,
            model=model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        )

    logger.info("[LLM] Backend sélectionné : Ollama (local)")
    url = ollama_url or os.getenv("OLLAMA_URL", "http://ollama:11434")
    return OllamaBackend(
        base_url=url,
        model=model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
    )