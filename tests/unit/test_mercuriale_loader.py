"""
TESTS : tests/unit/test_mercuriale_loader.py
DESCRIPTION : Tests unitaires pour la brique core/mercuriale/.

              Couvre MercurialeLoader, MercurialeIndex et MercurialeEntry.
              Les tests utilisent des fixtures in-memory (tmp_path) pour
              éviter toute dépendance aux fichiers référentiels réels.

RÉFÉRENCES ACADÉMIQUES :
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML. NeurIPS.
  → Tester le composant de chargement des données de référence est critique :
    un bug silencieux dans le Loader corrompt toutes les features downstream.
- [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection. ICMLA.
  → Les seuils de ratio (> 1.5 = fraude probable) doivent être vérifiables
    mathématiquement — les tests valident les calculs numériques.

STRATÉGIE :
- Fixtures in-memory via tmp_path (pas de dépendance aux fichiers réels)
- Séparation en classes thématiques pour lisibilité
- Test de la généricité : Santé ET Auto utilisent le même Loader
"""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest
import yaml

from core.mercuriale.exceptions import (
    CodeAbsentError,
    MercurialeFileError,
    MercurialeFormatError,
)
from core.mercuriale.loader import MercurialeLoader
from core.mercuriale.models import (
    TAUX_BEAC_EUR_XAF,
    MercurialeEntry,
    MercurialeIndex,
)


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def yaml_sante_path(tmp_path) -> Path:
    """Référentiel Santé minimal au format YAML structuré."""
    data = {
        "entries": [
            {"code": "MG_001",     "Libelle_Officiel": "Consultation MG",     "Prix_Ref_XAF": 8000,   "Categorie": "Acte médical"},
            {"code": "MG_002",     "Libelle_Officiel": "Consultation complexe","Prix_Ref_XAF": 12000,  "Categorie": "Acte médical"},
            {"code": "BIO_001",    "Libelle_Officiel": "NFS",                  "Prix_Ref_XAF": 6000,   "Categorie": "Biologie"},
            {"code": "RAD_001",    "Libelle_Officiel": "Radio thorax",         "Prix_Ref_XAF": 15000,  "Categorie": "Radiologie"},
            {"code": "GYNECO_001", "Libelle_Officiel": "Consultation gynéco",  "Prix_Ref_XAF": 15000,  "Categorie": "Acte médical"},
            {"code": "HOSP_001",   "Libelle_Officiel": "Forfait journalier",   "Prix_Ref_XAF": 35000,  "Categorie": "Hospitalisation"},
        ]
    }
    path = tmp_path / "mercuriale_sante.yaml"
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture
def yaml_auto_path(tmp_path) -> Path:
    """Référentiel Auto minimal au format YAML structuré."""
    data = {
        "entries": [
            {"code": "CARROS_AILE_AV",    "Libelle_Officiel": "Remplacement aile avant",   "Prix_Ref_XAF": 85000,  "Categorie": "Carrosserie"},
            {"code": "VITRE_PARE_BRISE",  "Libelle_Officiel": "Remplacement pare-brise",   "Prix_Ref_XAF": 95000,  "Categorie": "Vitrage"},
            {"code": "MECA_FREINS_AV",    "Libelle_Officiel": "Freins avant",              "Prix_Ref_XAF": 85000,  "Categorie": "Mécanique"},
            {"code": "MO_TAUX_HORAIRE",   "Libelle_Officiel": "Taux horaire MO",           "Prix_Ref_XAF": 8500,   "Categorie": "Main d'oeuvre"},
        ]
    }
    path = tmp_path / "bareme_auto.yaml"
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture
def yaml_flat_path(tmp_path) -> Path:
    """Référentiel au format dict plat {code: prix}."""
    data = {"CODE_A": 10000, "CODE_B": 25000, "CODE_C": 5000}
    path = tmp_path / "mercuriale_flat.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


@pytest.fixture
def csv_path(tmp_path) -> Path:
    """Référentiel au format CSV."""
    path = tmp_path / "mercuriale.csv"
    rows = [
        {"Code_Acte": "MG_001",  "Prix_Ref_XAF": "8000",  "Libelle_Officiel": "Consultation MG",  "Categorie": "Acte médical"},
        {"Code_Acte": "BIO_001", "Prix_Ref_XAF": "6000",  "Libelle_Officiel": "NFS",              "Categorie": "Biologie"},
        {"Code_Acte": "RAD_001", "Prix_Ref_XAF": "15000", "Libelle_Officiel": "Radio thorax",     "Categorie": "Radiologie"},
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return path


@pytest.fixture
def eur_yaml_path(tmp_path) -> Path:
    """Référentiel source EUR (doit être converti en XAF au chargement)."""
    data = {
        "entries": [
            {"code": "FR_001", "Libelle_Officiel": "Acte France", "Prix_Ref_EUR": 50.0,  "Categorie": "Acte médical"},
            {"code": "FR_002", "Libelle_Officiel": "Radio France", "Prix_Ref_EUR": 100.0, "Categorie": "Radiologie"},
        ]
    }
    path = tmp_path / "mercuriale_eur.yaml"
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture
def loader_sante(yaml_sante_path) -> MercurialeLoader:
    return MercurialeLoader(
        path=yaml_sante_path,
        code_column="Code_Acte",
        price_column="Prix_Ref_XAF",
        currency="XAF",
        branch="sante",
    )


@pytest.fixture
def loader_auto(yaml_auto_path) -> MercurialeLoader:
    return MercurialeLoader(
        path=yaml_auto_path,
        code_column="Code_Reparation",
        price_column="Prix_Ref_XAF",
        currency="XAF",
        branch="auto",
    )


# ===========================================================================
# Tests — MercurialeEntry
# ===========================================================================

class TestMercurialeEntry:

    def test_entry_creation_valid(self):
        entry = MercurialeEntry(
            code="MG_001",
            libelle="Consultation MG",
            price_ref_xaf=8000.0,
            category="Acte médical",
        )
        assert entry.code == "MG_001"
        assert entry.price_ref_xaf == 8000.0
        assert entry.price_ref_eur is None

    def test_entry_frozen(self):
        """MercurialeEntry est immuable — toute modification doit lever AttributeError."""
        entry = MercurialeEntry(code="X", libelle="", price_ref_xaf=1000.0, category="")
        with pytest.raises(AttributeError):
            entry.price_ref_xaf = 9999.0  # type: ignore

    def test_entry_negative_price_raises(self):
        with pytest.raises(ValueError, match="négatif"):
            MercurialeEntry(code="X", libelle="", price_ref_xaf=-500.0, category="")

    def test_entry_zero_price_is_valid(self):
        """Prix à 0 est accepté (acte gratuit possible)."""
        entry = MercurialeEntry(code="GRATUIT", libelle="", price_ref_xaf=0.0, category="")
        assert entry.price_ref_xaf == 0.0


# ===========================================================================
# Tests — Chargement YAML structuré
# ===========================================================================

class TestLoaderYAML:

    def test_load_yaml_sante_count(self, loader_sante):
        """Le Loader charge le bon nombre d'entrées."""
        assert loader_sante.index.size == 6

    def test_load_yaml_auto_count(self, loader_auto):
        """Le même Loader fonctionne pour Auto — généricité prouvée."""
        assert loader_auto.index.size == 4

    def test_load_flat_yaml(self, yaml_flat_path, tmp_path):
        """Format plat {code: prix} est supporté."""
        loader = MercurialeLoader(path=yaml_flat_path, currency="XAF", branch="test")
        assert loader.index.size == 3
        assert loader.index.get_price("CODE_A") == 10000.0

    def test_file_not_found_raises(self, tmp_path):
        loader = MercurialeLoader(path=tmp_path / "absent.yaml", branch="test")
        with pytest.raises(MercurialeFileError, match="introuvable"):
            _ = loader.index

    def test_empty_yaml_raises(self, tmp_path):
        path = tmp_path / "empty.yaml"
        path.write_text("", encoding="utf-8")
        loader = MercurialeLoader(path=path, branch="test")
        with pytest.raises(MercurialeFormatError, match="vide"):
            _ = loader.index

    def test_unsupported_format_raises(self, tmp_path):
        path = tmp_path / "mercuriale.json"
        path.write_text('{"MG_001": 8000}', encoding="utf-8")
        loader = MercurialeLoader(path=path, branch="test")
        with pytest.raises(MercurialeFileError, match="Format non supporté"):
            _ = loader.index


# ===========================================================================
# Tests — Chargement CSV
# ===========================================================================

class TestLoaderCSV:

    def test_load_csv_count(self, csv_path):
        loader = MercurialeLoader(path=csv_path, currency="XAF", branch="test")
        assert loader.index.size == 3

    def test_load_csv_price_correct(self, csv_path):
        loader = MercurialeLoader(path=csv_path, currency="XAF", branch="test")
        assert loader.index.get_price("MG_001") == 8000.0

    def test_csv_missing_code_column_raises(self, tmp_path):
        path = tmp_path / "bad.csv"
        path.write_text("WrongCol,Prix_Ref_XAF\nMG_001,8000\n", encoding="utf-8")
        loader = MercurialeLoader(
            path=path, code_column="Code_Acte", price_column="Prix_Ref_XAF", branch="test"
        )
        with pytest.raises(MercurialeFormatError, match="Code_Acte"):
            _ = loader.index


# ===========================================================================
# Tests — Conversion EUR → XAF
# ===========================================================================

class TestEURConversion:

    def test_eur_converted_to_xaf_at_load(self, tmp_path):
        """
        La conversion EUR→XAF doit se faire au chargement.
        [INSURANCE_DOMAIN_CONTEXT §3.2] : taux BEAC 1 EUR = 655.957 XAF.
        """
        data = {
            "entries": [
                {"code": "FR_001", "Libelle_Officiel": "Acte", "Prix_Ref_EUR": 50.0, "Categorie": "Acte"}
            ]
        }
        path = tmp_path / "eur.yaml"
        path.write_text(yaml.dump(data), encoding="utf-8")
        loader = MercurialeLoader(
            path=path,
            price_column="Prix_Ref_EUR",
            currency="EUR",
            branch="test",
        )
        expected_xaf = 50.0 * TAUX_BEAC_EUR_XAF
        assert abs(loader.index.get_price("FR_001") - expected_xaf) < 0.01

    def test_xaf_source_unchanged(self, loader_sante):
        """Source XAF : pas de conversion, valeur identique."""
        assert loader_sante.index.get_price("MG_001") == 8000.0


# ===========================================================================
# Tests — MercurialeIndex lookups
# ===========================================================================

class TestMercurialeIndex:

    def test_get_price_present(self, loader_sante):
        assert loader_sante.index.get_price("MG_001") == 8000.0

    def test_get_price_absent_returns_none(self, loader_sante):
        """[INSURANCE_DOMAIN_CONTEXT §3.2] : code absent → None, jamais 1.0."""
        assert loader_sante.index.get_price("CODE_INEXISTANT") is None

    def test_contains(self, loader_sante):
        assert loader_sante.index.contains("MG_001") is True
        assert loader_sante.index.contains("ABSENT") is False

    def test_codes_list(self, loader_sante):
        codes = loader_sante.index.codes
        assert "MG_001" in codes
        assert "GYNECO_001" in codes
        assert len(codes) == 6

    def test_lookup_series_vectorised(self, loader_sante):
        """lookup_series doit traiter une Series entière sans boucle."""
        codes = pd.Series(["MG_001", "BIO_001", "ABSENT", "RAD_001"])
        result = loader_sante.index.lookup_series(codes)
        assert result.iloc[0] == 8000.0
        assert result.iloc[1] == 6000.0
        assert pd.isna(result.iloc[2])   # Code absent → NaN
        assert result.iloc[3] == 15000.0

    def test_flag_absent_series(self, loader_sante):
        codes = pd.Series(["MG_001", "ABSENT", "BIO_001", "HORS_MERCU"])
        flags = loader_sante.index.flag_absent_series(codes)
        assert flags.tolist() == [False, True, False, True]

    def test_compute_ratio_series(self, loader_sante):
        """
        [Bauder2017] : ratio > 1.5 = surfacturation probable.
        On vérifie le calcul numérique exact.
        """
        amounts = pd.Series([8000.0, 24000.0, 999.0])  # exact, ×3, absent
        codes = pd.Series(["MG_001", "MG_001", "ABSENT"])
        ratios = loader_sante.index.compute_ratio_series(amounts, codes)

        assert abs(ratios.iloc[0] - 1.0) < 0.001   # exact → ratio = 1.0
        assert abs(ratios.iloc[1] - 3.0) < 0.001   # ×3 → ratio = 3.0
        assert pd.isna(ratios.iloc[2])               # absent → NaN

    def test_ratio_capped_at_50(self, loader_sante):
        """Ratio extrême clampé à 50.0 pour stabilité SHAP [Lundberg2017]."""
        amounts = pd.Series([10_000_000.0])  # montant absurde
        codes = pd.Series(["MG_001"])        # prix ref = 8000
        ratio = loader_sante.index.compute_ratio_series(amounts, codes)
        assert ratio.iloc[0] == 50.0

    def test_is_within_tolerance(self, loader_sante):
        """
        Jitter ±5% [INSURANCE_DOMAIN_CONTEXT §3.2].
        MG_001 = 8000 XAF → tolérance [7600, 8400].
        """
        amounts = pd.Series([8000.0, 8200.0, 8500.0, 7500.0])
        codes = pd.Series(["MG_001", "MG_001", "MG_001", "MG_001"])
        within = loader_sante.index.is_within_tolerance(codes, amounts)

        assert within.iloc[0] == True   # exact
        assert within.iloc[1] == True   # +2.5% → dans tolérance
        assert within.iloc[2] == False  # +6.25% → hors tolérance
        assert within.iloc[3] == False  # -6.25% → hors tolérance

    def test_repr(self, loader_sante):
        r = repr(loader_sante.index)
        assert "sante" in r
        assert "6" in r


# ===========================================================================
# Tests — from_module_config (constructeur alternatif)
# ===========================================================================

class TestFromModuleConfig:

    def test_from_module_config_sante(self, yaml_sante_path, tmp_path):
        """Simule l'appel depuis SanteModule avec son YAML."""
        config = {
            "path": str(yaml_sante_path),
            "currency": "XAF",
            "tolerance_pct": 5,
            "code_column": "Code_Acte",
            "price_column": "Prix_Ref_XAF",
        }
        loader = MercurialeLoader.from_module_config(config, branch="sante")
        assert loader.branch == "sante"
        assert loader.index.size == 6

    def test_from_module_config_auto(self, yaml_auto_path):
        """
        Simule l'appel depuis AutoModule — même Loader, config différente.
        PREUVE DE GÉNÉRICITÉ : le MercurialeLoader est identique pour Santé et Auto.
        """
        config = {
            "path": str(yaml_auto_path),
            "currency": "XAF",
            "tolerance_pct": 5,
            "code_column": "Code_Reparation",
            "price_column": "Prix_Ref_XAF",
        }
        loader = MercurialeLoader.from_module_config(config, branch="auto")
        assert loader.branch == "auto"
        assert loader.index.size == 4

    def test_from_module_config_missing_path_raises(self):
        with pytest.raises(KeyError):
            MercurialeLoader.from_module_config({"currency": "XAF"}, branch="test")


# ===========================================================================
# Tests — Mode strict (CodeAbsentError)
# ===========================================================================

class TestStrictMode:

    def test_strict_mode_absent_raises(self, yaml_sante_path):
        loader = MercurialeLoader(
            path=yaml_sante_path, currency="XAF", branch="sante", strict=True
        )
        with pytest.raises(CodeAbsentError, match="CODE_ABSENT"):
            loader.get_price_xaf("CODE_ABSENT")

    def test_non_strict_mode_absent_returns_none(self, loader_sante):
        """Mode par défaut : code absent → None sans exception."""
        result = loader_sante.get_price_xaf("CODE_ABSENT")
        assert result is None


# ===========================================================================
# Tests — Mise en cache
# ===========================================================================

class TestCache:

    def test_cache_returns_same_index(self, yaml_sante_path):
        MercurialeLoader.clear_cache()
        loader1 = MercurialeLoader.cached(yaml_sante_path, branch="sante")
        loader2 = MercurialeLoader.cached(yaml_sante_path, branch="sante")
        # Les deux partagent le même objet MercurialeIndex en cache
        assert loader1.index is loader2.index

    def test_clear_cache(self, yaml_sante_path):
        MercurialeLoader.clear_cache()
        _ = MercurialeLoader.cached(yaml_sante_path, branch="sante").index
        MercurialeLoader.clear_cache()
        # Après clear, un nouveau chargement crée un nouvel index
        loader_after = MercurialeLoader.cached(yaml_sante_path, branch="sante")
        assert loader_after.index.size == 6


# ===========================================================================
# Tests — Représentation et métadonnées
# ===========================================================================

class TestRepr:

    def test_loader_repr_not_loaded(self, yaml_sante_path):
        loader = MercurialeLoader(path=yaml_sante_path, branch="sante")
        r = repr(loader)
        assert "sante" in r
        assert "non chargé" in r

    def test_loader_repr_loaded(self, loader_sante):
        _ = loader_sante.index  # déclenche le chargement
        r = repr(loader_sante)
        assert "chargé" in r


# ===========================================================================
# Tests d'intégration — Généricité Santé + Auto sur même Loader
# ===========================================================================

class TestGenericite:

    def test_same_loader_class_sante_and_auto(
        self, yaml_sante_path, yaml_auto_path
    ):
        """
        PREUVE DE GÉNÉRICITÉ T6 :
        Le MercurialeLoader fonctionne identiquement pour Santé et Auto.
        Seuls les fichiers YAML source et les noms de colonnes changent.
        [Sculley2015] : la séparation des responsabilités permet la réutilisation.
        """
        loader_s = MercurialeLoader(
            path=yaml_sante_path,
            code_column="Code_Acte",
            price_column="Prix_Ref_XAF",
            branch="sante",
        )
        loader_a = MercurialeLoader(
            path=yaml_auto_path,
            code_column="Code_Reparation",
            price_column="Prix_Ref_XAF",
            branch="auto",
        )

        # Les deux Loaders sont du même type
        assert type(loader_s) is type(loader_a)

        # Chacun connaît son domaine
        assert loader_s.index.contains("MG_001") is True
        assert loader_s.index.contains("CARROS_AILE_AV") is False
        assert loader_a.index.contains("CARROS_AILE_AV") is True
        assert loader_a.index.contains("MG_001") is False

    def test_compute_ratio_santé_fraude_surfacturation(self, loader_sante):
        """
        Scénario fraude Santé : consultation MG facturée 40 000 XAF
        alors que la mercuriale CIMA indique 8 000 XAF → ratio = 5.0
        → Largement au-delà du seuil de 1.5 [Bauder2017].
        """
        amounts = pd.Series([40_000.0])
        codes = pd.Series(["MG_001"])
        ratio = loader_sante.index.compute_ratio_series(amounts, codes)
        assert ratio.iloc[0] == pytest.approx(5.0, rel=1e-3)

    def test_compute_ratio_auto_fraude_surfacturation(self, loader_auto):
        """
        Scénario fraude Auto : aile avant facturée 255 000 XAF
        alors que le barème ASAC indique 85 000 XAF → ratio = 3.0
        → Au-delà du seuil de 1.3 [Subudhi2017].
        """
        amounts = pd.Series([255_000.0])
        codes = pd.Series(["CARROS_AILE_AV"])
        ratio = loader_auto.index.compute_ratio_series(amounts, codes)
        assert ratio.iloc[0] == pytest.approx(3.0, rel=1e-3)