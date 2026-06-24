"""Tests du Normalizer."""
from __future__ import annotations
import numpy as np
import pandas as pd
import pytest

from core.normalizer import Normalizer, TAUX_EUR_XAF_FALLBACK
from core.exceptions import NormalizationError


@pytest.fixture
def df_with_currencies() -> pd.DataFrame:
    return pd.DataFrame({
        "Montant_Facture": [100.0, 65595.7, 200.0],
        "Devise": ["EUR", "XAF", "EUR"],
        "Taux_Change": [1.0, 655.957, 1.0],
    })


@pytest.mark.unit
class TestImputation:

    def test_imputes_numeric_with_median(self):
        df = pd.DataFrame({"x": [1.0, 2.0, np.nan, 4.0]})
        result = Normalizer.handle_missing(df, flag_imputed=False)
        assert result["x"].isna().sum() == 0
        assert result["x"].iloc[2] == 2.0  # médiane

    def test_imputes_categorical_with_mode(self):
        df = pd.DataFrame({"c": ["A", "A", None, "B"]})
        result = Normalizer.handle_missing(df, flag_imputed=False)
        assert result["c"].isna().sum() == 0
        assert result["c"].iloc[2] == "A"

    def test_flag_imputed_added(self):
        df = pd.DataFrame({"x": [1.0, np.nan]})
        result = Normalizer.handle_missing(df, flag_imputed=True)
        assert "_was_imputed" in result.columns
        assert result["_was_imputed"].tolist() == [False, True]

    def test_unknown_strategy_raises(self):
        df = pd.DataFrame({"x": [1.0, np.nan]})
        with pytest.raises(NormalizationError):
            Normalizer.handle_missing(df, numeric_strategy="invalid")


@pytest.mark.unit
class TestCurrencyNormalization:

    def test_xaf_converted_to_eur(self, df_with_currencies):
        n = Normalizer(target_currency="EUR")
        result = n.normalize_currency(df_with_currencies)
        assert "_norm_Montant_Facture" in result.columns
        # 65595.7 XAF / 655.957 = 100.0 EUR
        assert result["_norm_Montant_Facture"].iloc[1] == pytest.approx(100.0, rel=1e-3)
        assert result["_norm_Montant_Facture"].iloc[0] == 100.0

    def test_unknown_currency_raises(self):
        df = pd.DataFrame({
            "Montant_Facture": [100.0], "Devise": ["GBP"], "Taux_Change": [1.0],
        })
        with pytest.raises(NormalizationError, match="inconnues"):
            Normalizer().normalize_currency(df)

    def test_missing_currency_column_raises(self):
        df = pd.DataFrame({"Montant_Facture": [100.0]})
        with pytest.raises(NormalizationError, match="devise"):
            Normalizer().normalize_currency(df)

    def test_fallback_rate_used_when_rate_column_missing(self):
        df = pd.DataFrame({
            "Montant_Facture": [TAUX_EUR_XAF_FALLBACK],
            "Devise": ["XAF"],
        })
        result = Normalizer().normalize_currency(df)
        assert result["_norm_Montant_Facture"].iloc[0] == pytest.approx(1.0, rel=1e-3)


@pytest.mark.unit
class TestCategoricalEncoding:

    def test_low_cardinality_one_hot(self):
        df = pd.DataFrame({"c": ["A", "B", "A", "B"]})
        result = Normalizer.encode_categoricals(df, ["c"])
        # 2 catégories → one-hot
        assert any(col.startswith("_enc_c_") for col in result.columns)

    def test_high_cardinality_label_encoded(self):
        df = pd.DataFrame({"c": [f"v{i}" for i in range(30)]})
        result = Normalizer.encode_categoricals(
            df, ["c"], low_cardinality_threshold=10,
        )
        assert "_enc_c" in result.columns
        assert result["_enc_c"].dtype in (np.int64, np.int32, int)

    def test_id_columns_skipped(self):
        df = pd.DataFrame({"ID_Praticien": ["P1", "P2"]})
        result = Normalizer.encode_categoricals(df)
        assert not any(col.startswith("_enc_ID_") for col in result.columns)


@pytest.mark.unit
class TestLogTransform:

    def test_log_transform_applied(self):
        df = pd.DataFrame({"Montant_Facture": [0, 100, 1000]})
        result = Normalizer.log_transform(df, ["Montant_Facture"])
        assert "_log_Montant_Facture" in result.columns
        assert result["_log_Montant_Facture"].iloc[0] == 0  # log1p(0)
        assert result["_log_Montant_Facture"].iloc[1] == pytest.approx(np.log1p(100))

    def test_negative_clipped_to_zero(self):
        df = pd.DataFrame({"x": [-10, 0, 10]})
        result = Normalizer.log_transform(df, ["x"])
        assert result["_log_x"].iloc[0] == 0