"""
MODULE : core/plugin_registry.py
DESCRIPTION : Registre central des modules MAKORA. Implémente le pattern
              Plugin Registry — le Kernel découvre les modules sans jamais
              les importer par leur nom concret.

RÉFÉRENCES ACADÉMIQUES :
- [Fowler2004] Fowler, M. (2004). Patterns of Enterprise Application
  Architecture. Pattern : Registry.
- [Wolfinger2008] Wolfinger et al. (2008). Plug-in architecture.

DÉCISIONS DE CONCEPTION :
- Singleton implicite via attributs de classe (pas d'instance — classe
  utilisée comme namespace).
- Décorateur @register("nom") — DSL léger, plus lisible qu'un appel
  manuel à add(...).
- discover() optionnel : permet l'auto-import des modules/ pour les tests
  E2E sans connaître les noms à l'avance.
- get() lève PluginNotFoundError plutôt que de retourner None — force le
  caller à gérer le cas, pas de silent failure.
"""

from __future__ import annotations
from typing import Callable
import importlib
import pkgutil

from core.base_module import BaseModule
from core.exceptions import (
    PluginAlreadyRegisteredError,
    PluginContractError,
    PluginNotFoundError,
)
from core.logging_config import get_logger

logger = get_logger(__name__)


class PluginRegistry:
    """
    Registre central des modules MAKORA.

    Utilisation :
        # Côté module (modules/sante/sante_module.py)
        @PluginRegistry.register("sante")
        class SanteModule(BaseModule):
            ...

        # Côté Kernel
        SanteCls = PluginRegistry.get("sante")
        module = SanteCls("modules/sante/sante.yaml")
    """

    _registry: dict[str, type[BaseModule]] = {}

    # ────────────────────────────────────────────────────────────────
    # ENREGISTREMENT
    # ────────────────────────────────────────────────────────────────

    @classmethod
    def register(cls, branch: str) -> Callable[[type[BaseModule]], type[BaseModule]]:
        """
        Décorateur d'enregistrement d'un module.

        Args:
            branch: identifiant unique de la branche (ex: "sante", "auto").

        Raises:
            PluginContractError: la classe décorée n'hérite pas de BaseModule.
            PluginAlreadyRegisteredError: la branche est déjà enregistrée.
        """
        if not isinstance(branch, str) or not branch.strip():
            raise PluginContractError(
                "Le nom de branche doit être une chaîne non vide.",
                payload={"branch": branch},
            )
        branch = branch.strip().lower()

        def decorator(klass: type[BaseModule]) -> type[BaseModule]:
            if not isinstance(klass, type) or not issubclass(klass, BaseModule):
                raise PluginContractError(
                    f"@register('{branch}') : la classe {klass.__name__} "
                    f"doit hériter de BaseModule.",
                    payload={"class": klass.__name__},
                )
            if branch in cls._registry:
                raise PluginAlreadyRegisteredError(
                    f"Branche '{branch}' déjà enregistrée par "
                    f"{cls._registry[branch].__name__}.",
                    payload={
                        "branch": branch,
                        "existing": cls._registry[branch].__name__,
                        "new": klass.__name__,
                    },
                )
            cls._registry[branch] = klass
            logger.info("Module enregistré : '%s' → %s", branch, klass.__name__)
            return klass

        return decorator

    # ────────────────────────────────────────────────────────────────
    # ACCÈS
    # ────────────────────────────────────────────────────────────────

    @classmethod
    def get(cls, branch: str) -> type[BaseModule]:
        """
        Récupère la classe d'un module enregistré.

        Raises:
            PluginNotFoundError: si la branche est inconnue.
        """
        key = branch.strip().lower()
        if key not in cls._registry:
            raise PluginNotFoundError(
                f"Branche '{branch}' non enregistrée. "
                f"Branches disponibles : {cls.list_branches()}",
                payload={"requested": branch, "available": cls.list_branches()},
            )
        return cls._registry[key]

    @classmethod
    def list_branches(cls) -> list[str]:
        """Liste triée des branches enregistrées."""
        return sorted(cls._registry.keys())

    @classmethod
    def is_registered(cls, branch: str) -> bool:
        """True si la branche est enregistrée."""
        return branch.strip().lower() in cls._registry

    # ────────────────────────────────────────────────────────────────
    # DÉCOUVERTE DYNAMIQUE
    # ────────────────────────────────────────────────────────────────

    @classmethod
    def discover(cls, package: str = "modules") -> list[str]:
        """
        Importe automatiquement tous les sous-packages de `package`
        pour déclencher leurs décorateurs @register.

        Utile pour les tests E2E et l'API au démarrage.

        Returns:
            Liste des branches découvertes pendant l'appel.
        """
        before = set(cls._registry.keys())

        try:
            pkg = importlib.import_module(package)
        except ImportError as e:
            logger.warning("Package '%s' introuvable : %s", package, e)
            return []

        if not hasattr(pkg, "__path__"):
            return []

        for _, modname, _ in pkgutil.iter_modules(pkg.__path__):
            full = f"{package}.{modname}"
            try:
                # On essaie d'importer le sous-package puis son module principal
                sub = importlib.import_module(full)
                # Convention : modules/sante/sante_module.py
                candidate = f"{full}.{modname}_module"
                try:
                    importlib.import_module(candidate)
                except ImportError:
                    # Pas grave si le sous-module n'existe pas encore
                    pass
            except Exception as e:
                logger.warning("Échec import '%s' : %s", full, e)

        after = set(cls._registry.keys())
        newly = sorted(after - before)
        if newly:
            logger.info("Modules découverts : %s", newly)
        return newly

    # ────────────────────────────────────────────────────────────────
    # UTILS — réservé aux tests
    # ────────────────────────────────────────────────────────────────

    @classmethod
    def _clear(cls) -> None:
        """À N'UTILISER QU'EN TESTS — vide le registre."""
        cls._registry.clear()