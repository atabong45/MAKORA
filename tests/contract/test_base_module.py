"""Tests du Plugin Contract — BaseModule."""
from __future__ import annotations
from pathlib import Path
import pytest
import yaml

from core.base_module import BaseModule
from core.exceptions import PluginContractError


# ─── Fixtures locales ────────────────────────────────────────────────

VALID_YAML = {
    "branch": "test",
    "version": "0.1.0",
    "features": ["f1", "f2"],
    "rca_rules": [{"id": "R1", "conditions": []}],
    "thresholds": {"contamination": 0.08, "anomaly_score_alert": 0.7},
    "input_schema": {"required": ["ID_Sinistre"]},
}


class _ConcreteModule(BaseModule):
    """Implémentation concrète minimale pour tester BaseModule."""

    def get_feature_names(self): return ["f1", "f2"]
    def engineer_features(self, df): return df
    def get_rca_rules(self): return self.config["rca_rules"]
    def validate_input(self, df): return True, []


def _write_yaml(tmp_path: Path, content: dict, name: str = "test.yaml") -> Path:
    p = tmp_path / name
    p.write_text(yaml.safe_dump(content), encoding="utf-8")
    return p


# ─── Tests ──────────────────────────────────────────────────────────

@pytest.mark.contract
class TestBaseModuleLoading:

    def test_valid_yaml_loads(self, tmp_path):
        path = _write_yaml(tmp_path, VALID_YAML)
        m = _ConcreteModule(path)
        assert m.branch == "test"
        assert m.version == "0.1.0"
        assert m.get_contamination() == 0.08

    def test_missing_file_raises(self):
        with pytest.raises(PluginContractError, match="introuvable"):
            _ConcreteModule("nonexistent.yaml")

    def test_invalid_yaml_raises(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text("a: b: c: invalid", encoding="utf-8")
        with pytest.raises(PluginContractError):
            _ConcreteModule(p)

    def test_missing_required_key_raises(self, tmp_path):
        bad = {k: v for k, v in VALID_YAML.items() if k != "features"}
        path = _write_yaml(tmp_path, bad)
        with pytest.raises(PluginContractError, match="features"):
            _ConcreteModule(path)

    def test_missing_threshold_raises(self, tmp_path):
        bad = {**VALID_YAML, "thresholds": {"contamination": 0.08}}
        path = _write_yaml(tmp_path, bad)
        with pytest.raises(PluginContractError, match="anomaly_score_alert"):
            _ConcreteModule(path)

    @pytest.mark.parametrize("invalid_c", [-0.1, 0, 0.5, 1.0, "0.08"])
    def test_invalid_contamination_raises(self, tmp_path, invalid_c):
        bad = {
            **VALID_YAML,
            "thresholds": {"contamination": invalid_c, "anomaly_score_alert": 0.7},
        }
        path = _write_yaml(tmp_path, bad)
        with pytest.raises(PluginContractError, match="contamination"):
            _ConcreteModule(path)


@pytest.mark.contract
class TestBaseModuleAbstractness:

    def test_cannot_instantiate_directly(self, tmp_path):
        path = _write_yaml(tmp_path, VALID_YAML)
        with pytest.raises(TypeError, match="abstract"):
            BaseModule(path)


@pytest.mark.contract
class TestBaseModuleConcreteMethods:

    @pytest.fixture
    def module(self, tmp_path):
        path = _write_yaml(tmp_path, VALID_YAML)
        return _ConcreteModule(path)

    def test_get_contamination(self, module):
        assert module.get_contamination() == 0.08

    def test_get_anomaly_threshold(self, module):
        assert module.get_anomaly_threshold() == 0.7

    def test_is_graph_enabled_default_false(self, module):
        assert module.is_graph_enabled() is False

    def test_get_graph_config_none_when_disabled(self, module):
        assert module.get_graph_config() is None

    def test_get_source_mapping_empty_by_default(self, module):
        assert module.get_source_mapping("noemie") == {}

    def test_get_input_schema(self, module):
        assert module.get_input_schema() == {"required": ["ID_Sinistre"]}


@pytest.mark.contract
class TestRealSanteModule:
    """Tests sur le vrai sante.yaml — vérifie qu'il respecte le contrat."""

    def test_sante_yaml_loads_without_error(self, sante_yaml_path):
        # Import différé pour déclencher le décorateur @register
        from modules.sante.sante_module import SanteModule
        m = SanteModule(sante_yaml_path)
        assert m.branch == "sante"
        assert m.get_contamination() > 0

    def test_sante_module_implements_all_abstract(self, sante_yaml_path):
        from modules.sante.sante_module import SanteModule
        m = SanteModule(sante_yaml_path)
        assert isinstance(m.get_feature_names(), list)
        assert len(m.get_feature_names()) > 0
        assert isinstance(m.get_rca_rules(), list)
        ok, errs = m.validate_input(None)
        assert ok is False
        assert errs