"""
TESTS : tests/unit/test_auto_module.py
DESCRIPTION : Tests unitaires pour AutoModule et modules/auto/features.py (v1.2.0).

STRATÉGIE :
- Fixtures in-memory (tmp_path + données ARGUS simulées)
- Séparation : TestPluginContract / TestFeatures / TestValidateInput
- Chaque test vérifie un comportement atomique
- Dégradation gracieuse testée explicitement (mercuriale absent, colonnes nulles)

HISTORIQUE v1.2.0 (Scénarios A+B+C) :
  Renommages de clés registre :
    garage_concentration_score → prestataire_concentration (A)
    delai_declaration_anormal  → delai_depot_anormal (A)
    nb_sinistres_12m           → nb_sinistres_recents (B)
    montant_devis_log          → montant_log (C)
  Nouvelles features :
    is_weekend_event (A) — Date_Sinistre samedi/dimanche
    acte_incomplet (A)   — Flag_Acte_Incomp
    document_age_anormal (B) — Delai_Declaration > 180j
  → 18 features (was 15). 13 features communes ★ avec SanteModule [Xu2023].

RÉFÉRENCES :
- [Sculley2015] : tester le composant feature engineering est critique —
  un bug silencieux corrompt toutes les prédictions downstream.
- [Viaene2002] / [Subudhi2017] : les seuils des features sont testés
  mathématiquement pour garantir leur cohérence avec la littérature.

Lancer :
    pytest tests/unit/test_auto_module.py -v
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml


# ===========================================================================
# Fixtures
# ===========================================================================

@pytest.fixture
def auto_yaml_path(tmp_path) -> Path:
    """auto.yaml minimal valide v1.2.0 pour les tests unitaires (18 features)."""
    config = {
        "branch": "auto",
        "version": "1.2.0",
        "input_schema": {
            "required_columns": ["ID_Sinistre", "ID_Assure", "Montant_Devis"],
            "types": {"Montant_Devis": "float"},
        },
        "features": [
            "ratio_devis_bareme",
            "vehicule_sur_value",
            "sinistre_nuit_sans_temoin",
            "document_altere",
            "prestataire_concentration",   # Scénario A : renommé
            "garage_non_agree",
            "constat_manquant",
            "expertise_manquante",
            "delai_depot_anormal",         # Scénario A : renommé
            "anciennete_contrat_courte",
            "ocr_confiance_faible",
            "ratio_mo_reference",
            "nb_sinistres_recents",        # Scénario B : renommé
            "montant_log",                 # Scénario C : renommé
            "saisie_hors_heures",
            "is_weekend_event",            # Scénario A : NOUVEAU
            "acte_incomplet",              # Scénario A : NOUVEAU
            "document_age_anormal",        # Scénario B : NOUVEAU
        ],
        "thresholds": {
            "contamination": 0.068,
            "anomaly_score_alert": 0.65,
        },
        "rca_rules": [
            {
                "id": "RCA_AUTO_001",
                "priority": 1,
                "category": "Fraude Intentionnelle",
                "subcategory": "Falsification documentaire",
                "conditions": [
                    {"feature": "document_altere", "operator": "eq", "threshold": 1}
                ],
                "logic": "AND",
                "confidence_base": 0.90,
                "message_template": "Document altéré.",
                "action": "Vérifier.",
            }
        ],
        "source_mappings": {
            "argus_csv": {"ID_Sinistre": "ID_Sinistre"}
        },
        "mercuriale": {
            "enabled": False,  # désactivé pour les tests unitaires
        },
        "drift": {
            "monitored_features": ["ratio_devis_bareme"],
            "reference_window_days": 90,
            "current_window_days": 30,
            "thresholds": {"warning": 0.10, "critical": 0.20},
        },
    }
    path = tmp_path / "auto.yaml"
    path.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture
def module(auto_yaml_path):
    """Instance AutoModule avec YAML minimal."""
    from modules.auto.auto_module import AutoModule
    return AutoModule(config_path=auto_yaml_path)


@pytest.fixture
def df_normal() -> pd.DataFrame:
    """DataFrame ARGUS — 3 dossiers normaux."""
    return pd.DataFrame({
        "ID_Sinistre":              ["SIN_001", "SIN_002", "SIN_003"],
        "ID_Assure":                ["A001",    "A002",    "A003"],
        "Montant_Devis":            [376878.0,  170000.0,  794.71],
        "Montant_Reference_Bareme": [376635.0,  170108.0,  799.64],
        "Valeur_Venale_EUR":        [10075.0,   17400.0,   15800.0],
        "Devise":                   ["XAF",     "XAF",     "EUR"],
        "Flag_Sinistre_Nuit":       [True,      False,     False],
        "Nb_Temoins":               [0,         1,         2],
        "Flag_Doc_Altere":          [False,     False,     False],
        "ID_Garage":                ["G01",     "G02",     "G03"],
        "Agrement_CIMA":            [False,     True,      True],
        "Constat_Amiable_Present":  [True,      False,     False],
        "Rapport_Expertise_Signe":  [True,      True,      True],
        "Delai_Declaration":        [6,         6,         4],
        "Anciennete_Contrat":       [1423,      1155,      4921],
        "Source_Flux":              ["API",     "Scan",    "API"],
        "Confiance_OCR_Glob":       [np.nan,    0.65,      np.nan],
        "Ratio_MO":                 [0.875,     0.82,      1.111],
        "Nb_Sinistres_12m":         [0,         0,         0],
        "Heure_Saisie":             [8,         13,        11],
        # Colonnes v1.2.0
        "Date_Sinistre":            ["2025-01-13", "2025-01-15", "2025-01-14"],  # lun, mer, mar
        "Flag_Acte_Incomp":         [0,         0,         0],
    })


@pytest.fixture
def df_fraude() -> pd.DataFrame:
    """DataFrame ARGUS — 2 dossiers frauduleux."""
    return pd.DataFrame({
        "ID_Sinistre":              ["SIN_F01", "SIN_F02"],
        "ID_Assure":                ["F001",    "F002"],
        "Montant_Devis":            [850000.0,  2500.0],
        "Montant_Reference_Bareme": [376635.0,  799.64],
        "Valeur_Venale_EUR":        [10075.0,   3000.0],
        "Devise":                   ["XAF",     "EUR"],
        "Flag_Sinistre_Nuit":       [True,      False],
        "Nb_Temoins":               [0,         0],
        "Flag_Doc_Altere":          [True,      False],
        "ID_Garage":                ["G01",     "G01"],
        "Agrement_CIMA":            [False,     False],
        "Constat_Amiable_Present":  [False,     False],
        "Rapport_Expertise_Signe":  [False,     True],
        "Delai_Declaration":        [45,        60],
        "Anciennete_Contrat":       [30,        15],
        "Source_Flux":              ["Scan",    "Scan"],
        "Confiance_OCR_Glob":       [0.35,      0.30],
        "Ratio_MO":                 [1.80,      1.50],
        "Nb_Sinistres_12m":         [3,         4],
        "Heure_Saisie":             [2,         23],
        # Colonnes v1.2.0
        "Date_Sinistre":            ["2025-01-11", "2025-01-12"],  # samedi, dimanche
        "Flag_Acte_Incomp":         [1,          1],
    })


# ===========================================================================
# Tests — Plugin Contract
# ===========================================================================

class TestPluginContract:

    def test_branch_is_auto(self, module):
        assert module.branch == "auto"

    def test_version_is_set(self, module):
        assert module.version == "1.2.0"

    def test_get_feature_names_returns_18(self, module):
        assert len(module.get_feature_names()) == 18

    def test_get_feature_names_stable(self, module):
        """L'ordre est stable entre deux appels — déterminisme garanti."""
        assert module.get_feature_names() == module.get_feature_names()

    def test_get_rca_rules_returns_list(self, module):
        rules = module.get_rca_rules()
        assert isinstance(rules, list)
        assert len(rules) >= 1

    def test_get_rca_rules_have_required_fields(self, module):
        for rule in module.get_rca_rules():
            assert "id" in rule
            assert "priority" in rule
            assert "conditions" in rule
            assert "confidence_base" in rule

    def test_is_subclass_of_basemodule(self, module):
        from core.base_module import BaseModule
        assert isinstance(module, BaseModule)

    def test_registered_in_plugin_registry(self):
        """AutoModule doit être visible dans le PluginRegistry après import."""
        from core.plugin_registry import PluginRegistry
        assert "auto" in PluginRegistry.list_branches()

    def test_repr_contains_key_info(self, module):
        r = repr(module)
        assert "auto" in r
        assert "18" in r

    def test_mercuriale_disabled_does_not_crash(self, module):
        """Mercuriale désactivé → _mercuriale_index est None, pas d'exception."""
        assert module._mercuriale_index is None


# ===========================================================================
# Tests — validate_input
# ===========================================================================

class TestValidateInput:

    def test_valid_dataframe_passes(self, module, df_normal):
        ok, errors = module.validate_input(df_normal)
        assert ok is True
        assert errors == []

    def test_none_input_fails(self, module):
        ok, errors = module.validate_input(None)
        assert ok is False
        assert len(errors) > 0

    def test_empty_dataframe_fails(self, module):
        ok, errors = module.validate_input(pd.DataFrame())
        assert ok is False

    def test_missing_critical_column_fails(self, module, df_normal):
        df_bad = df_normal.drop(columns=["Montant_Devis"])
        ok, errors = module.validate_input(df_bad)
        assert ok is False
        assert any("Montant_Devis" in e for e in errors)

    def test_missing_optional_column_still_passes(self, module, df_normal):
        """Colonne optionnelle absente → validation OK (dégradation gracieuse)."""
        df_no_ocr = df_normal.drop(columns=["Confiance_OCR_Glob"])
        ok, errors = module.validate_input(df_no_ocr)
        assert ok is True


# ===========================================================================
# Tests — engineer_features (features individuelles)
# ===========================================================================

class TestEngineerFeatures:

    def test_returns_dataframe(self, module, df_normal):
        result = module.engineer_features(df_normal)
        assert isinstance(result, pd.DataFrame)

    def test_original_not_modified(self, module, df_normal):
        """engineer_features ne doit pas modifier le DataFrame original."""
        original_cols = set(df_normal.columns)
        _ = module.engineer_features(df_normal)
        assert set(df_normal.columns) == original_cols

    def test_all_18_features_present(self, module, df_normal):
        result = module.engineer_features(df_normal)
        for feat in module.get_feature_names():
            assert feat in result.columns, f"Feature manquante : {feat}"

    def test_ratio_devis_bareme_normal(self, module, df_normal):
        """
        SIN_001 : Montant_Devis=376878, Bareme=376635 → ratio ≈ 1.0006
        [Subudhi2017] : seuil fraude à 1.30 → ce dossier est normal.
        """
        result = module.engineer_features(df_normal)
        assert abs(result["ratio_devis_bareme"].iloc[0] - 1.0006) < 0.01

    def test_ratio_devis_bareme_fraude(self, module, df_fraude):
        """
        SIN_F01 : Montant_Devis=850000, Bareme=376635 → ratio ≈ 2.26
        [Subudhi2017] : largement au-dessus du seuil 1.30.
        """
        result = module.engineer_features(df_fraude)
        assert result["ratio_devis_bareme"].iloc[0] > 1.30

    def test_ratio_devis_bareme_nan_si_bareme_nul(self, module):
        """Montant_Reference_Bareme = 0 → ratio neutre 1.0 (pas de division par zéro).
        [Sculley2015] : dégradation gracieuse — valeur neutre au lieu de NaN."""
        df = pd.DataFrame({
            "ID_Sinistre": ["X"], "ID_Assure": ["A"],
            "Montant_Devis": [50000.0],
            "Montant_Reference_Bareme": [0.0],
            "Devise": ["XAF"],
        })
        result = module.engineer_features(df)
        assert result["ratio_devis_bareme"].iloc[0] == pytest.approx(1.0)

    def test_vehicule_sur_value_detects_fraud(self, module):
        """
        Devis XAF = 10M, Valeur vénale EUR = 10075 → valeur XAF ≈ 6.6M
        Ratio = 10M / 6.6M ≈ 1.51 > 0.80 → True
        """
        df = pd.DataFrame({
            "ID_Sinistre": ["X"], "ID_Assure": ["A"],
            "Montant_Devis": [10_000_000.0],
            "Montant_Reference_Bareme": [5_000_000.0],
            "Valeur_Venale_EUR": [10075.0],
            "Devise": ["XAF"],
        })
        result = module.engineer_features(df)
        assert result["vehicule_sur_value"].iloc[0] == True

    def test_vehicule_sur_value_normal(self, module, df_normal):
        """SIN_001 : dévis = 376k XAF, valeur vénale = 10075 EUR = 6.6M XAF → False."""
        result = module.engineer_features(df_normal)
        assert result["vehicule_sur_value"].iloc[0] == False

    def test_sinistre_nuit_sans_temoin(self, module, df_fraude):
        """SIN_F01 : nuit=True, temoins=0 → True."""
        result = module.engineer_features(df_fraude)
        assert result["sinistre_nuit_sans_temoin"].iloc[0] == True

    def test_sinistre_nuit_avec_temoin_is_false(self, module):
        df = pd.DataFrame({
            "ID_Sinistre": ["X"], "ID_Assure": ["A"],
            "Montant_Devis": [100.0], "Devise": ["XAF"],
            "Montant_Reference_Bareme": [100.0],
            "Flag_Sinistre_Nuit": [True],
            "Nb_Temoins": [2],  # avec témoins → pas de staging
        })
        result = module.engineer_features(df)
        assert result["sinistre_nuit_sans_temoin"].iloc[0] == False

    def test_document_altere_flag_doc_altere(self, module, df_fraude):
        """SIN_F01 : Flag_Doc_Altere=True → document_altere=True."""
        result = module.engineer_features(df_fraude)
        assert result["document_altere"].iloc[0] == True

    def test_prestataire_concentration_high(self, module):
        """3 dossiers sur même garage → score = 1.0 (clé prestataire_concentration)."""
        df = pd.DataFrame({
            "ID_Sinistre": ["S1", "S2", "S3"], "ID_Assure": ["A", "B", "C"],
            "Montant_Devis": [100.0, 100.0, 100.0],
            "Montant_Reference_Bareme": [100.0, 100.0, 100.0],
            "Devise": ["XAF", "XAF", "XAF"],
            "ID_Garage": ["G01", "G01", "G01"],
        })
        result = module.engineer_features(df)
        assert all(abs(v - 1.0) < 1e-6 for v in result["prestataire_concentration"])

    def test_prestataire_concentration_distributed(self, module, df_normal):
        """3 dossiers sur 3 garages distincts → score = 1/3."""
        result = module.engineer_features(df_normal)
        # df_normal a G01, G02, G03 → chacun = 1/3
        assert all(abs(v - 1/3) < 1e-3 for v in result["prestataire_concentration"])

    def test_garage_non_agree_detects(self, module, df_normal):
        """SIN_001 : Agrement_CIMA=False → garage_non_agree=True."""
        result = module.engineer_features(df_normal)
        assert result["garage_non_agree"].iloc[0] == True
        assert result["garage_non_agree"].iloc[1] == False

    def test_constat_manquant(self, module, df_fraude):
        """SIN_F01 : Constat_Amiable_Present=False → constat_manquant=True."""
        result = module.engineer_features(df_fraude)
        assert result["constat_manquant"].iloc[0] == True

    def test_expertise_manquante(self, module, df_fraude):
        """SIN_F01 : Rapport_Expertise_Signe=False → expertise_manquante=True."""
        result = module.engineer_features(df_fraude)
        assert result["expertise_manquante"].iloc[0] == True

    def test_delai_depot_anormal(self, module, df_fraude):
        """SIN_F01 : Delai_Declaration=45 > 30 → True (clé delai_depot_anormal)."""
        result = module.engineer_features(df_fraude)
        assert result["delai_depot_anormal"].iloc[0] == True

    def test_delai_depot_normal(self, module, df_normal):
        """df_normal : délais = 6, 6, 4 → tous False."""
        result = module.engineer_features(df_normal)
        assert result["delai_depot_anormal"].all() == False

    def test_anciennete_contrat_courte(self, module, df_fraude):
        """SIN_F01 : Anciennete_Contrat=30 < 90 → True."""
        result = module.engineer_features(df_fraude)
        assert result["anciennete_contrat_courte"].iloc[0] == True

    def test_ocr_confiance_faible_scan_only(self, module, df_fraude):
        """SIN_F01 : Scan + Confiance=0.35 < 0.50 → True."""
        result = module.engineer_features(df_fraude)
        assert result["ocr_confiance_faible"].iloc[0] == True

    def test_ocr_confiance_faible_api_always_false(self, module):
        """Flux API → pas d'OCR → ocr_confiance_faible = False même si null."""
        df = pd.DataFrame({
            "ID_Sinistre": ["X"], "ID_Assure": ["A"],
            "Montant_Devis": [100.0], "Devise": ["XAF"],
            "Montant_Reference_Bareme": [100.0],
            "Source_Flux": ["API"],
            "Confiance_OCR_Glob": [np.nan],
        })
        result = module.engineer_features(df)
        assert result["ocr_confiance_faible"].iloc[0] == False

    def test_ratio_mo_fast_path(self, module, df_normal):
        """Ratio_MO présent dans dataset → fast path utilisé."""
        result = module.engineer_features(df_normal)
        # SIN_001 : Ratio_MO = 0.875
        assert abs(result["ratio_mo_reference"].iloc[0] - 0.875) < 0.001

    def test_nb_sinistres_recents_passthrough(self, module, df_fraude):
        """Nb_Sinistres_12m est un pass-through (clé nb_sinistres_recents)."""
        result = module.engineer_features(df_fraude)
        assert result["nb_sinistres_recents"].iloc[0] == 3.0
        assert result["nb_sinistres_recents"].iloc[1] == 4.0

    def test_montant_log_positive(self, module, df_normal):
        """log1p(montant) doit être > 0 pour tout montant > 0 (clé montant_log)."""
        result = module.engineer_features(df_normal)
        assert (result["montant_log"] > 0).all()

    def test_saisie_hors_heures_nuit(self, module, df_fraude):
        """SIN_F01 : Heure_Saisie=2 < 7 → True."""
        result = module.engineer_features(df_fraude)
        assert result["saisie_hors_heures"].iloc[0] == True

    def test_saisie_hors_heures_normal(self, module, df_normal):
        """df_normal : heures = 8, 13, 11 → toutes dans [7, 20] → False."""
        result = module.engineer_features(df_normal)
        assert result["saisie_hors_heures"].all() == False

    # ─── Nouvelles features v1.2.0 ─────────────────────────────────────────

    def test_is_weekend_event_fraude_weekend(self, module, df_fraude):
        """SIN_F01 : Date_Sinistre=2025-01-11 (samedi) → 1 ; SIN_F02 dimanche → 1."""
        result = module.engineer_features(df_fraude)
        assert result["is_weekend_event"].iloc[0] == 1  # samedi
        assert result["is_weekend_event"].iloc[1] == 1  # dimanche

    def test_is_weekend_event_normal_semaine(self, module, df_normal):
        """df_normal : lundi, mercredi, mardi → tous 0."""
        result = module.engineer_features(df_normal)
        assert list(result["is_weekend_event"]) == [0, 0, 0]

    def test_is_weekend_event_colonne_absente(self, module):
        """Sans Date_Sinistre → is_weekend_event = 0 partout, pas de crash."""
        df = pd.DataFrame({
            "ID_Sinistre": ["X"], "ID_Assure": ["A"],
            "Montant_Devis": [100.0], "Devise": ["XAF"],
            "Montant_Reference_Bareme": [100.0],
        })
        result = module.engineer_features(df)
        assert result["is_weekend_event"].iloc[0] == 0

    def test_acte_incomplet_fraude(self, module, df_fraude):
        """SIN_F01/F02 : Flag_Acte_Incomp=1 → acte_incomplet=1."""
        result = module.engineer_features(df_fraude)
        assert list(result["acte_incomplet"]) == [1, 1]

    def test_acte_incomplet_normal(self, module, df_normal):
        """df_normal : Flag_Acte_Incomp=0 → acte_incomplet=0."""
        result = module.engineer_features(df_normal)
        assert list(result["acte_incomplet"]) == [0, 0, 0]

    def test_acte_incomplet_colonne_absente(self, module):
        """Sans Flag_Acte_Incomp → acte_incomplet = 0 partout."""
        df = pd.DataFrame({
            "ID_Sinistre": ["X"], "ID_Assure": ["A"],
            "Montant_Devis": [100.0], "Devise": ["XAF"],
            "Montant_Reference_Bareme": [100.0],
        })
        result = module.engineer_features(df)
        assert result["acte_incomplet"].iloc[0] == 0

    def test_document_age_anormal_fraude(self, module, df_fraude):
        """SIN_F01 : Delai_Declaration=45 < 180 → 0 ; SIN_F02 : 60 < 180 → 0."""
        result = module.engineer_features(df_fraude)
        # Aucun des deux ne dépasse 180j → tous 0
        assert list(result["document_age_anormal"]) == [0, 0]

    def test_document_age_anormal_seuil_depasse(self, module):
        """Delai_Declaration=200 > 180 → document_age_anormal=1."""
        df = pd.DataFrame({
            "ID_Sinistre": ["X"], "ID_Assure": ["A"],
            "Montant_Devis": [100.0], "Devise": ["XAF"],
            "Montant_Reference_Bareme": [100.0],
            "Delai_Declaration": [200],
        })
        result = module.engineer_features(df)
        assert result["document_age_anormal"].iloc[0] == 1

    def test_document_age_anormal_colonne_absente(self, module):
        """Sans Delai_Declaration → document_age_anormal = 0 partout."""
        df = pd.DataFrame({
            "ID_Sinistre": ["X"], "ID_Assure": ["A"],
            "Montant_Devis": [100.0], "Devise": ["XAF"],
            "Montant_Reference_Bareme": [100.0],
        })
        result = module.engineer_features(df)
        assert result["document_age_anormal"].iloc[0] == 0


# ===========================================================================
# Tests — dégradation gracieuse (colonnes absentes)
# ===========================================================================

class TestDegradationGracieuse:

    # APRÈS
    def test_missing_bareme_column_yields_neutral(self, module):
        """Sans Montant_Reference_Bareme → ratio neutre 1.0, pas de crash.
        [Sculley2015] : dégradation gracieuse — valeur neutre 1.0."""
        df = pd.DataFrame({
            "ID_Sinistre": ["X"], "ID_Assure": ["A"],
            "Montant_Devis": [50000.0],
            "Devise": ["XAF"],
        })
        result = module.engineer_features(df)
        assert result["ratio_devis_bareme"].iloc[0] == pytest.approx(1.0)

    def test_missing_garage_column_yields_zero(self, module):
        """Sans ID_Garage → prestataire_concentration = 0.0."""
        df = pd.DataFrame({
            "ID_Sinistre": ["X"], "ID_Assure": ["A"],
            "Montant_Devis": [100.0], "Devise": ["XAF"],
            "Montant_Reference_Bareme": [100.0],
        })
        result = module.engineer_features(df)
        assert result["prestataire_concentration"].iloc[0] == 0.0

    def test_missing_ocr_column_no_crash(self, module):
        """Sans Confiance_OCR_Glob → ocr_confiance_faible calculable sans crash."""
        df = pd.DataFrame({
            "ID_Sinistre": ["X"], "ID_Assure": ["A"],
            "Montant_Devis": [100.0], "Devise": ["XAF"],
            "Montant_Reference_Bareme": [100.0],
            "Source_Flux": ["Scan"],
            # Pas de Confiance_OCR_Glob
        })
        result = module.engineer_features(df)
        # Sans la colonne, _safe_col retourne NaN → fillna(0.0) < 0.5 → True
        # (comportement conservateur : scan sans score OCR = suspect)
        assert result["ocr_confiance_faible"].dtype in (bool, object, "bool")

    def test_full_pipeline_no_crash_minimal_df(self, module):
        """Pipeline complet sur DataFrame minimal — aucun crash attendu."""
        df = pd.DataFrame({
            "ID_Sinistre": ["X"],
            "ID_Assure": ["A"],
            "Montant_Devis": [100.0],
            "Devise": ["XAF"],
            "Anciennete_Contrat": [365],
            "Delai_Declaration": [5],
            "Heure_Saisie": [10],
            "Flag_Sinistre_Nuit": [False],
            "Nb_Temoins": [1],
            "ID_Garage": ["G01"],
        })
        # Ne doit pas lever d'exception
        result = module.engineer_features(df)
        assert len(result) == 1
        assert "ratio_devis_bareme" in result.columns

    def test_bool_features_no_crash(self, module, df_normal):
        """Les features booléennes restent calculables sans exception."""
        result = module.engineer_features(df_normal)
        bool_features = [
            "vehicule_sur_value", "sinistre_nuit_sans_temoin",
            "document_altere", "garage_non_agree", "constat_manquant",
            "expertise_manquante",
            "delai_depot_anormal",        # Scénario A : renommé
            "anciennete_contrat_courte", "ocr_confiance_faible",
            "saisie_hors_heures",
        ]
        for feat in bool_features:
            assert feat in result.columns
            assert result[feat].notna().all(), f"NaN inattendu dans {feat}"


# ===========================================================================
# Tests — features réseau (FEATURE_RESEAU_FUNCTIONS_AUTO)
# ===========================================================================

class TestFeaturesReseau:
    """
    Les features réseau (flag_doublon, community_score, expert_garage_correlation)
    sont calculées par AutoModule V3 si elles figurent dans auto.yaml. Ici on teste
    les fonctions directement (le YAML de test n'inclut pas ces features).
    """

    def test_flag_doublon_nomme_correctement(self):
        from modules.auto.features_reseau import compute_flag_doublon_auto
        df = pd.DataFrame({"Flag_Doublon_Auto": [True, False]})
        result = compute_flag_doublon_auto(df)
        assert result.name == "flag_doublon"
        assert list(result) == [1, 0]

    def test_flag_doublon_colonne_absente(self):
        from modules.auto.features_reseau import compute_flag_doublon_auto
        df = pd.DataFrame({"Autre": [1, 2]})
        result = compute_flag_doublon_auto(df)
        assert result.name == "flag_doublon"
        assert (result == 0).all()

    def test_community_score_nomme_correctement(self):
        from modules.auto.features_reseau import compute_community_score_auto
        df = pd.DataFrame({"community_id_auto": [0, 1, 1, 2]})
        result = compute_community_score_auto(df)
        assert result.name == "community_score"
        # community_id=0 → 0.0
        assert result.iloc[0] == pytest.approx(0.0)
        # membres de communautés → > 0
        assert (result.iloc[1:] > 0).all()

    def test_community_score_colonne_absente(self):
        from modules.auto.features_reseau import compute_community_score_auto
        df = pd.DataFrame({"Autre": [1, 2]})
        result = compute_community_score_auto(df)
        assert result.name == "community_score"
        assert (result == 0.0).all()

    def test_expert_garage_correlation_collusion(self):
        """Un expert lié à un seul garage → corrélation = 1.0."""
        from modules.auto.features_reseau import compute_expert_garage_correlation
        df = pd.DataFrame({
            "ID_Expert_Stable": ["E1", "E1", "E1"],
            "ID_Garage":        ["G1", "G1", "G1"],
        })
        result = compute_expert_garage_correlation(df)
        assert all(abs(v - 1.0) < 1e-6 for v in result)

    def test_expert_garage_correlation_distribue(self):
        """Un expert réparti sur 3 garages distincts → corrélation = 1/3."""
        from modules.auto.features_reseau import compute_expert_garage_correlation
        df = pd.DataFrame({
            "ID_Expert_Stable": ["E1", "E1", "E1"],
            "ID_Garage":        ["G1", "G2", "G3"],
        })
        result = compute_expert_garage_correlation(df)
        assert all(abs(v - 1/3) < 1e-3 for v in result)

    def test_expert_garage_correlation_colonnes_absentes(self):
        from modules.auto.features_reseau import compute_expert_garage_correlation
        df = pd.DataFrame({"Autre": [1, 2]})
        result = compute_expert_garage_correlation(df)
        assert (result == 0.0).all()

    def test_registre_reseau_cles_renommees(self):
        """Scénario A : clés flag_doublon et community_score harmonisées."""
        from modules.auto.features_reseau import FEATURE_RESEAU_FUNCTIONS_AUTO
        keys = set(FEATURE_RESEAU_FUNCTIONS_AUTO.keys())
        assert keys == {"flag_doublon", "community_score", "expert_garage_correlation"}
        assert "flag_doublon_auto" not in keys
        assert "community_score_auto" not in keys


# ===========================================================================
# Tests — généricité (même module, comportement cohérent Santé vs Auto)
# ===========================================================================

class TestGenericite:

    def test_auto_module_type_different_from_sante(self, module, auto_yaml_path):
        """AutoModule et SanteModule sont des classes différentes."""
        assert module.branch == "auto"
        assert type(module).__name__ == "AutoModule"

    def test_feature_names_specifiques_auto(self, module):
        """Les features purement Santé ne doivent pas apparaître dans Auto."""
        sante_only_features = {
            "ratio_prix_mercuriale", "flag_incoherence_sexe_acte",
            "historique_ratio_praticien", "nb_sinistres_30j_assure",
        }
        auto_features = set(module.get_feature_names())
        # Aucune feature purement Santé ne doit apparaître dans Auto
        assert sante_only_features.isdisjoint(auto_features)

    def test_kernel_isolation_no_concrete_import(self):
        """
        RÈGLE D'OR : pipeline.py ne doit pas importer AutoModule par son nom.
        [ARCHITECTURE §3.1]
        """
        import inspect
        try:
            import core.pipeline as pipeline_module
            source = inspect.getsource(pipeline_module)
            assert "AutoModule" not in source, (
                "VIOLATION RÈGLE D'OR : 'AutoModule' trouvé dans pipeline.py"
            )
        except ImportError:
            pytest.skip("core.pipeline non disponible dans cet environnement")