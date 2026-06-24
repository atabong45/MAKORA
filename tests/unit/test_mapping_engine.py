"""Tests du MappingEngine."""
from __future__ import annotations
import pandas as pd
import pytest

from core.mapping_engine import MappingEngine
from core.exceptions import MappingError


@pytest.mark.unit
class TestMappingEngineApply:

    def test_basic_renaming(self):
        df = pd.DataFrame({"ClaimAmount": [100], "CareDate": ["2025-01-01"]})
        mapping = {"ClaimAmount": "Montant_Facture", "CareDate": "Date_Soin"}
        result = MappingEngine.apply(df, mapping)
        assert "Montant_Facture" in result.columns
        assert "Date_Soin" in result.columns
        assert "ClaimAmount" not in result.columns

    def test_empty_mapping_returns_copy(self):
        df = pd.DataFrame({"ID_Sinistre": ["S1"]})
        result = MappingEngine.apply(df, {})
        assert result.equals(df)
        assert result is not df  # copy

    def test_missing_source_column_non_strict_warns(self, caplog):
        df = pd.DataFrame({"A": [1]})
        mapping = {"A": "X", "B": "Y"}  # B absent
        result = MappingEngine.apply(df, mapping, strict=False)
        assert "X" in result.columns
        assert "Y" not in result.columns

    def test_missing_source_column_strict_raises(self):
        df = pd.DataFrame({"A": [1]})
        mapping = {"A": "X", "B": "Y"}
        with pytest.raises(MappingError, match="absente"):
            MappingEngine.apply(df, mapping, strict=True)

    def test_collision_raises(self):
        df = pd.DataFrame({"src": [1], "Montant_Facture": [100]})
        mapping = {"src": "Montant_Facture"}
        with pytest.raises(MappingError, match="Collision"):
            MappingEngine.apply(df, mapping)

    def test_empty_df_raises(self):
        with pytest.raises(MappingError, match="vide"):
            MappingEngine.apply(pd.DataFrame(), {"A": "B"})


@pytest.mark.unit
class TestMappingEngineDetectSource:

    def test_detect_best_source(self):
        df = pd.DataFrame({"ClaimAmount": [1], "CareDate": ["x"]})
        sources = {
            "noemie": {"ClaimAmount": "Montant_Facture", "CareDate": "Date_Soin"},
            "scan_cm": {"facture_montant": "Montant_Facture"},
        }
        assert MappingEngine.detect_source(df, sources) == "noemie"

    def test_no_match_raises(self):
        df = pd.DataFrame({"unknown_col": [1]})
        sources = {"noemie": {"ClaimAmount": "Montant_Facture"}}
        with pytest.raises(MappingError, match="50%"):
            MappingEngine.detect_source(df, sources)


@pytest.mark.unit
class TestMappingEngineCompleteness:

    def test_complete_mapping(self):
        mapping = {"A": "X", "B": "Y"}
        missing = MappingEngine.validate_mapping_completeness(mapping, ["X", "Y"])
        assert missing == []

    def test_incomplete_mapping(self):
        mapping = {"A": "X"}
        missing = MappingEngine.validate_mapping_completeness(mapping, ["X", "Y", "Z"])
        assert set(missing) == {"Y", "Z"}