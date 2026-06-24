"""Tests du schema_validator."""
from __future__ import annotations
import pandas as pd
import pytest

from core.schema_validator import (
    validate_universal_schema,
    UniversalRecord,
    UNIVERSAL_REQUIRED_COLUMNS,
)
from core.exceptions import SchemaValidationError


@pytest.mark.unit
class TestUniversalSchemaValidation:

    def test_valid_df_passes(self, sample_universal_df):
        validate_universal_schema(sample_universal_df)  # ne lève rien

    def test_empty_df_raises(self):
        with pytest.raises(SchemaValidationError, match="vide"):
            validate_universal_schema(pd.DataFrame())

    def test_none_raises(self):
        with pytest.raises(SchemaValidationError):
            validate_universal_schema(None)

    @pytest.mark.parametrize("missing_col", UNIVERSAL_REQUIRED_COLUMNS)
    def test_missing_column_raises(self, sample_universal_df, missing_col):
        df = sample_universal_df.drop(columns=[missing_col])
        with pytest.raises(SchemaValidationError, match="manquantes"):
            validate_universal_schema(df)

    def test_negative_amount_raises(self, sample_universal_df):
        sample_universal_df.loc[0, "Montant_Facture"] = -10.0
        with pytest.raises(SchemaValidationError, match="négatives"):
            validate_universal_schema(sample_universal_df)

    def test_non_numeric_amount_raises(self, sample_universal_df):
        sample_universal_df["Montant_Facture"] = sample_universal_df["Montant_Facture"].astype(str)
        with pytest.raises(SchemaValidationError, match="numérique"):
            validate_universal_schema(sample_universal_df)


@pytest.mark.unit
class TestUniversalRecordModel:

    def test_valid_record(self):
        r = UniversalRecord(
            ID_Sinistre="S001",
            ID_Assure="A001",
            Montant_Facture=100.0,
            Devise="EUR",
            Date_Soin="2025-01-15",
            Source_Flux="NOEMIE-API",
        )
        assert r.Devise == "EUR"

    def test_currency_normalized_to_upper(self):
        r = UniversalRecord(
            ID_Sinistre="S001",
            ID_Assure="A001",
            Montant_Facture=100.0,
            Devise="eur",
            Date_Soin="2025-01-15",
            Source_Flux="NOEMIE-API",
        )
        assert r.Devise == "EUR"

    def test_unknown_currency_raises(self):
        with pytest.raises(Exception):
            UniversalRecord(
                ID_Sinistre="S001", ID_Assure="A001",
                Montant_Facture=100.0, Devise="GBP",
                Date_Soin="2025-01-15", Source_Flux="X",
            )