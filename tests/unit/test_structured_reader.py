"""Tests du StructuredReader."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
import pytest

from core.ingestion.structured_reader import StructuredReader
from core.exceptions import IngestionError


@pytest.mark.unit
class TestFormatDetection:

    def test_detect_csv(self):
        assert StructuredReader.detect_format("file.csv") == "csv"

    def test_detect_json(self):
        assert StructuredReader.detect_format("file.json") == "json"

    def test_detect_parquet(self):
        assert StructuredReader.detect_format("file.parquet") == "parquet"
        assert StructuredReader.detect_format("file.pq") == "parquet"

    def test_unsupported_extension_raises(self):
        with pytest.raises(IngestionError, match="non supportée"):
            StructuredReader.detect_format("file.xlsx")


@pytest.mark.unit
class TestReadCSV:

    def test_read_valid_csv(self, tmp_path: Path):
        p = tmp_path / "test.csv"
        p.write_text("a,b\n1,2\n3,4\n", encoding="utf-8")
        df = StructuredReader.read(p)
        assert df.shape == (2, 2)
        assert list(df.columns) == ["a", "b"]

    def test_read_csv_with_dates(self, tmp_path: Path):
        p = tmp_path / "test.csv"
        p.write_text("date,value\n2025-01-15,100\n", encoding="utf-8")
        df = StructuredReader.read(p, parse_dates=["date"])
        assert pd.api.types.is_datetime64_any_dtype(df["date"])

    def test_missing_file_raises(self):
        with pytest.raises(IngestionError, match="introuvable"):
            StructuredReader.read("nonexistent.csv")


@pytest.mark.unit
class TestReadParquet:

    def test_read_write_parquet_roundtrip(self, tmp_path: Path):
        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        p = tmp_path / "out.parquet"
        StructuredReader.write_parquet(df, p)
        assert p.exists()
        df2 = StructuredReader.read(p)
        pd.testing.assert_frame_equal(df, df2)

    def test_write_creates_parent_dirs(self, tmp_path: Path):
        df = pd.DataFrame({"a": [1]})
        nested = tmp_path / "deep" / "path" / "out.parquet"
        StructuredReader.write_parquet(df, nested)
        assert nested.exists()