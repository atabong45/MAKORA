"""Tests du PluginRegistry."""
from __future__ import annotations
import pytest

from core.base_module import BaseModule
from core.plugin_registry import PluginRegistry
from core.exceptions import (
    PluginContractError,
    PluginNotFoundError,
    PluginAlreadyRegisteredError,
)


class _DummyModule(BaseModule):
    """Module factice pour les tests."""
    def __init__(self): pass  # bypass YAML loading
    def get_feature_names(self): return []
    def engineer_features(self, df): return df
    def get_rca_rules(self): return []
    def validate_input(self, df): return True, []


@pytest.fixture(autouse=True)
def _clear_registry():
    """Vide le registre avant chaque test pour isolation."""
    # Sauvegarde l'état pour ne pas casser les autres tests
    snapshot = dict(PluginRegistry._registry)
    PluginRegistry._clear()
    yield
    PluginRegistry._registry.update(snapshot)


@pytest.mark.contract
class TestPluginRegistry:

    def test_register_valid_module(self):
        @PluginRegistry.register("dummy")
        class M(_DummyModule):
            pass
        assert PluginRegistry.is_registered("dummy")
        assert PluginRegistry.get("dummy") is M

    def test_register_normalizes_case(self):
        @PluginRegistry.register("  DuMmY  ")
        class M(_DummyModule):
            pass
        assert PluginRegistry.is_registered("dummy")
        assert PluginRegistry.is_registered("DUMMY")  # case-insensitive

    def test_register_non_basemodule_raises(self):
        with pytest.raises(PluginContractError, match="BaseModule"):
            @PluginRegistry.register("bad")
            class NotAModule:  # n'hérite pas
                pass

    def test_register_duplicate_raises(self):
        @PluginRegistry.register("twice")
        class M1(_DummyModule):
            pass
        with pytest.raises(PluginAlreadyRegisteredError):
            @PluginRegistry.register("twice")
            class M2(_DummyModule):
                pass

    def test_register_empty_branch_raises(self):
        with pytest.raises(PluginContractError, match="non vide"):
            PluginRegistry.register("")

    def test_get_unknown_raises(self):
        with pytest.raises(PluginNotFoundError, match="non enregistrée"):
            PluginRegistry.get("ghost")

    def test_list_branches_sorted(self):
        @PluginRegistry.register("zeta")
        class M1(_DummyModule):
            pass

        @PluginRegistry.register("alpha")
        class M2(_DummyModule):
            pass

        assert PluginRegistry.list_branches() == ["alpha", "zeta"]