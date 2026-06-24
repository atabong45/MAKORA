"""
Configuration globale pytest — fixtures partagées.
"""
from __future__ import annotations
from pathlib import Path
import sys
import pandas as pd
import pytest

# Permet d'importer core/, modules/ depuis les tests
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_universal_df() -> pd.DataFrame:
    """DataFrame minimal au schéma universel MAKORA."""
    return pd.DataFrame({
        "ID_Sinistre": ["S001", "S002", "S003"],
        "ID_Assure": ["A001", "A002", "A003"],
        "ID_Praticien": ["P001", "P002", "P003"],
        "Code_Acte": ["76601001", "76601001", "ABC123"],
        "Montant_Facture": [100.0, 250.0, 50.0],
        "Prix_Unitaire_Ref": [100.0, 200.0, 50.0],
        "Devise": ["EUR", "XAF", "EUR"],
        "Taux_Change": [1.0, 655.957, 1.0],
        "Date_Soin": pd.to_datetime(["2025-01-15", "2025-02-20", "2025-03-10"]),
        "Source_Flux": ["NOEMIE-API", "Scan_CM", "NOEMIE-API"],
    })


@pytest.fixture
def sante_yaml_path() -> Path:
    """Chemin du sante.yaml — vérifie qu'il existe."""
    p = ROOT / "modules" / "sante" / "sante.yaml"
    assert p.exists(), f"sante.yaml manquant : {p}"
    return p