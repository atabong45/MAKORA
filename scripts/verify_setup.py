"""
Script de vérification de la Session A — T1 + T2.
Lance : python -m scripts.verify_setup
"""
from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

print("=" * 70)
print("VÉRIFICATION SETUP MAKORA — Session A (T1 + T2)")
print("=" * 70)

# 1. Import du Kernel
print("\n[1/5] Import du Kernel...")
from core.base_module import BaseModule
from core.plugin_registry import PluginRegistry
from core.mapping_engine import MappingEngine
from core.normalizer import Normalizer
from core.schema_validator import validate_universal_schema
from core.ingestion.structured_reader import StructuredReader
print("    ✓ Kernel importé sans erreur")

# 2. Découverte du module Santé
print("\n[2/5] Découverte du module Santé...")
PluginRegistry._clear()
PluginRegistry.discover("modules")
branches = PluginRegistry.list_branches()
print(f"    ✓ Branches enregistrées : {branches}")
assert "sante" in branches, "Module Santé non découvert !"

# 3. Chargement du module Santé
print("\n[3/5] Instanciation du module Santé...")
SanteCls = PluginRegistry.get("sante")
sante = SanteCls(ROOT / "modules" / "sante" / "sante.yaml")
print(f"    ✓ {sante}")
print(f"    ✓ Features déclarées : {sante.get_feature_names()}")
print(f"    ✓ Contamination : {sante.get_contamination()}")
print(f"    ✓ Sources connues : {sante.list_known_sources()}")

# 4. Pipeline ETL minimal sur un DataFrame fictif
print("\n[4/5] Test pipeline ETL...")
import pandas as pd
df = pd.DataFrame({
    "ID_Sinistre": ["S001", "S002"],
    "ID_Assure": ["A001", "A002"],
    "ID_Praticien": ["P001", "P002"],
    "Code_Acte": ["76601001", "ABC123"],
    "Montant_Facture": [100.0, 65595.7],
    "Prix_Unitaire_Ref": [100.0, 200.0],
    "Devise": ["EUR", "XAF"],
    "Taux_Change": [1.0, 655.957],
    "Date_Soin": pd.to_datetime(["2025-01-15", "2025-02-20"]),
    "Source_Flux": ["NOEMIE-API", "Scan_CM"],
})
print(f"    ✓ DataFrame de test : {df.shape}")

# Validation schéma universel
validate_universal_schema(df)
print("    ✓ Schéma universel validé")

# Validation module-spécifique
ok, errs = sante.validate_input(df)
assert ok, f"Validation Santé échouée : {errs}"
print("    ✓ Validation module Santé OK")

# Normalisation devise
df = Normalizer().normalize_currency(df)
assert "_norm_Montant_Facture" in df.columns
print(f"    ✓ Devises normalisées (XAF→EUR : {df['_norm_Montant_Facture'].iloc[1]:.2f} EUR)")

# Feature engineering
df = sante.engineer_features(df)
for feat in sante.get_feature_names():
    assert feat in df.columns, f"Feature manquante : {feat}"
print(f"    ✓ Features calculées : {sante.get_feature_names()}")

# 5. Résumé
print("\n[5/5] Résumé")
print("    ✓ Plugin Contract opérationnel")
print("    ✓ Pipeline ETL fonctionnel")
print("    ✓ Module Santé prêt pour la suite (T3-T7)")

print("\n" + "=" * 70)
print("✅ SESSION A COMPLÈTE — Prêt pour Session B (Detector + Explainer)")
print("=" * 70)