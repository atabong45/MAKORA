"""
TESTS : tests/integration/test_pipeline_auto.py
DESCRIPTION : Tests d'intégration — Pipeline complet Auto (T11).

              Couvre le flux Auto de bout en bout :
              DataFrame ARGUS → AutoModule.engineer_features()
                              → Detector (IF)
                              → features numériques cohérentes

STRATÉGIE :
- 200 dossiers fixture ARGUS (100 normaux + 100 avec anomalies injectées)
- Entraînement IF sur les 100 normaux uniquement [Chandola2009]
- Évaluation sur les 200 (detection, pas de métriques formelles ici — T12)
- Vérification que le module ne crashe pas sur les vrais patterns ARGUS

RÉFÉRENCES :
- [Liu2008] Liu et al. (2008). Isolation Forest. ICDM.
  → Entraînement sur données normales uniquement (approche non-supervisée).
- [Chandola2009] Chandola et al. (2009). Anomaly detection: A survey.
  → Contamination = taux d'anomalies connu = 0.08.
- [Sculley2015] : tests E2E sur données réelles (même synthétiques)
  détectent les bugs de distribution que les tests unitaires manquent.
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

@pytest.fixture(scope="module")
def auto_yaml_path(tmp_path_factory) -> Path:
    """YAML Auto complet pour les tests d'intégration."""
    tmp = tmp_path_factory.mktemp("auto_integration")
    config = {
        "branch": "auto",
        "version": "1.0.0",
        "input_schema": {
            "required_columns": [
                "ID_Sinistre", "ID_Assure", "Montant_Devis",
                "Anciennete_Contrat", "Delai_Declaration",
                "Heure_Saisie", "Flag_Sinistre_Nuit",
                "Nb_Temoins", "ID_Garage", "Devise",
            ],
            "types": {"Montant_Devis": "float"},
        },
        "features": [
            "ratio_devis_bareme", "vehicule_sur_value",
            "sinistre_nuit_sans_temoin", "document_altere",
            "garage_concentration_score", "garage_non_agree",
            "constat_manquant", "expertise_manquante",
            "delai_declaration_anormal", "anciennete_contrat_courte",
            "ocr_confiance_faible", "ratio_mo_reference",
            "nb_sinistres_12m", "montant_devis_log", "saisie_hors_heures",
        ],
        "thresholds": {"contamination": 0.08, "anomaly_score_alert": 0.65},
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
            },
            {
                "id": "RCA_AUTO_002",
                "priority": 2,
                "category": "Fraude Intentionnelle",
                "subcategory": "Surfacturation réparation",
                "conditions": [
                    {"feature": "ratio_devis_bareme", "operator": "gt", "threshold": 1.30}
                ],
                "logic": "AND",
                "confidence_base": 0.82,
                "message_template": "Surfacturation détectée.",
                "action": "Contre-expertise.",
            },
        ],
        "source_mappings": {"argus_csv": {"ID_Sinistre": "ID_Sinistre"}},
        "mercuriale": {"enabled": False},
        "drift": {
            "monitored_features": ["ratio_devis_bareme"],
            "reference_window_days": 90,
            "current_window_days": 30,
            "thresholds": {"warning": 0.10, "critical": 0.20},
        },
    }
    path = tmp / "auto.yaml"
    path.write_text(yaml.dump(config, allow_unicode=True), encoding="utf-8")
    return path


@pytest.fixture(scope="module")
def module_auto(auto_yaml_path):
    from modules.auto.auto_module import AutoModule
    return AutoModule(config_path=auto_yaml_path)


def _make_argus_fixture(n: int, rng: np.random.Generator, anomalie: bool) -> pd.DataFrame:
    """
    Génère n dossiers ARGUS synthétiques calibrés sur les distributions réelles.
    anomalie=True → patterns fraude injectés.
    """
    prefix = "F" if anomalie else "N"
    ids_sin = [f"SIN_{prefix}_{i:04d}" for i in range(n)]
    ids_ass = [f"ASS_{i:04d}" for i in range(n)]

    pays = rng.choice(["France", "Cameroun"], size=n, p=[0.55, 0.45])
    devise = np.where(pays == "France", "EUR", "XAF")

    # Montants de base calibrés sur ARGUS
    montant_base_xaf = rng.lognormal(mean=12.5, sigma=1.2, size=n)
    montant_base_eur = montant_base_xaf / 655.957

    montant_devis = np.where(devise == "XAF", montant_base_xaf, montant_base_eur)

    if anomalie:
        # Surfacturation ×2.5 pour les fraudeurs
        montant_devis = montant_devis * rng.uniform(2.0, 3.5, size=n)

    bareme = montant_base_xaf * rng.uniform(0.95, 1.05, size=n)
    bareme_eur = bareme / 655.957
    montant_ref = np.where(devise == "XAF", bareme, bareme_eur)

    valeur_venale = rng.uniform(3000, 25000, size=n)  # EUR

    garages = (
        rng.choice([f"GAR_{i:03d}" for i in range(3)], size=n)  # 3 garages = collusion
        if anomalie
        else rng.choice([f"GAR_{i:03d}" for i in range(20)], size=n)  # 20 garages = normal
    )

    source_flux = rng.choice(["API", "Scan"], size=n, p=[0.7, 0.3])
    confiance_ocr = np.where(
        source_flux == "Scan",
        rng.uniform(0.2 if anomalie else 0.6, 0.5 if anomalie else 1.0, size=n),
        np.nan,
    )

    return pd.DataFrame({
        "ID_Sinistre":              ids_sin,
        "ID_Assure":                ids_ass,
        "Pays_Residence":           pays,
        "Montant_Devis":            montant_devis.astype(float),
        "Montant_Reference_Bareme": montant_ref.astype(float),
        "Valeur_Venale_EUR":        valeur_venale,
        "Devise":                   devise,
        "Flag_Sinistre_Nuit":       rng.random(n) < (0.6 if anomalie else 0.15),
        "Nb_Temoins":               rng.integers(0, 1 if anomalie else 4, size=n),
        "Flag_Doc_Altere":          rng.random(n) < (0.4 if anomalie else 0.02),
        "ID_Garage":                garages,
        "Agrement_CIMA":            rng.random(n) > (0.6 if anomalie else 0.1),
        "Constat_Amiable_Present":  rng.random(n) > (0.5 if anomalie else 0.05),
        "Rapport_Expertise_Signe":  rng.random(n) > (0.5 if anomalie else 0.05),
        "Delai_Declaration":        rng.integers(35 if anomalie else 1, 60, size=n),
        "Anciennete_Contrat":       rng.integers(10 if anomalie else 180, 60 if anomalie else 2000, size=n),
        "Source_Flux":              source_flux,
        "Confiance_OCR_Glob":       confiance_ocr,
        "Ratio_MO":                 rng.uniform(1.3 if anomalie else 0.7, 2.0 if anomalie else 1.2, size=n),
        "Nb_Sinistres_12m":         rng.integers(2 if anomalie else 0, 5 if anomalie else 2, size=n),
        "Heure_Saisie":             rng.integers(0 if anomalie else 7, 6 if anomalie else 20, size=n),
        "Label_Anomalie":           ["FRAUDE" if anomalie else "NORMAL"] * n,
    })


@pytest.fixture(scope="module")
def df_fixture_200() -> pd.DataFrame:
    """200 dossiers ARGUS : 100 normaux + 100 frauduleux."""
    rng = np.random.default_rng(42)
    df_normal = _make_argus_fixture(100, rng, anomalie=False)
    df_fraude = _make_argus_fixture(100, rng, anomalie=True)
    df = pd.concat([df_normal, df_fraude], ignore_index=True)
    return df.sample(frac=1, random_state=42).reset_index(drop=True)


@pytest.fixture(scope="module")
def df_enrichi(module_auto, df_fixture_200) -> pd.DataFrame:
    """DataFrame ARGUS enrichi des 15 features Auto."""
    return module_auto.engineer_features(df_fixture_200)


# ===========================================================================
# Tests E2E — engineer_features sur 200 dossiers
# ===========================================================================

class TestEngineerFeaturesE2E:

    def test_shape_preserved(self, df_fixture_200, df_enrichi):
        """Le nombre de lignes est préservé."""
        assert len(df_enrichi) == len(df_fixture_200)

    def test_all_features_computed(self, module_auto, df_enrichi):
        """Les 15 features sont toutes présentes."""
        for feat in module_auto.get_feature_names():
            assert feat in df_enrichi.columns

    def test_no_all_nan_feature(self, module_auto, df_enrichi):
        """Aucune feature ne doit être entièrement NaN."""
        for feat in module_auto.get_feature_names():
            pct_nan = df_enrichi[feat].isna().mean()
            assert pct_nan < 1.0, f"Feature '{feat}' est entièrement NaN"

    def test_ratio_devis_bareme_range(self, df_enrichi):
        """ratio_devis_bareme doit être dans [0, 50]."""
        valid = df_enrichi["ratio_devis_bareme"].dropna()
        assert (valid >= 0).all()
        assert (valid <= 50.0).all()

    def test_bool_features_are_bool(self, df_enrichi):
        """Les features binaires doivent contenir uniquement True/False."""
        bool_features = [
            "vehicule_sur_value", "sinistre_nuit_sans_temoin",
            "document_altere", "garage_non_agree", "constat_manquant",
            "expertise_manquante", "delai_declaration_anormal",
            "anciennete_contrat_courte", "ocr_confiance_faible",
            "saisie_hors_heures",
        ]
        for feat in bool_features:
            unique_vals = set(df_enrichi[feat].dropna().unique())
            assert unique_vals.issubset({True, False, 0, 1}), \
                f"Feature '{feat}' contient des valeurs non-booléennes : {unique_vals}"

    def test_fraudeurs_ont_plus_de_signaux(self, df_fixture_200, df_enrichi):
        """
        Les dossiers frauduleux doivent avoir en moyenne plus de features
        activées que les dossiers normaux.
        [Viaene2002] : les fraudeurs cumulent plusieurs signaux.
        """
        bool_feats = [
            "sinistre_nuit_sans_temoin", "document_altere",
            "constat_manquant", "expertise_manquante",
            "delai_declaration_anormal", "anciennete_contrat_courte",
            "ocr_confiance_faible", "saisie_hors_heures",
        ]
        df_eval = df_enrichi.copy()
        df_eval["label"] = df_fixture_200["Label_Anomalie"]
        df_eval["nb_signaux"] = df_eval[bool_feats].astype(int).sum(axis=1)

        mean_fraude = df_eval[df_eval["label"] == "FRAUDE"]["nb_signaux"].mean()
        mean_normal = df_eval[df_eval["label"] == "NORMAL"]["nb_signaux"].mean()

        assert mean_fraude > mean_normal, (
            f"Les fraudeurs doivent avoir plus de signaux : "
            f"fraude={mean_fraude:.2f}, normal={mean_normal:.2f}"
        )

    def test_ratio_fraude_higher_than_normal(self, df_fixture_200, df_enrichi):
        """
        ratio_devis_bareme moyen des fraudeurs > celui des normaux.
        [Subudhi2017] : ratio est la feature discriminante #1.
        """
        df_eval = df_enrichi.copy()
        df_eval["label"] = df_fixture_200["Label_Anomalie"]

        mean_ratio_fraude = df_eval[df_eval["label"] == "FRAUDE"]["ratio_devis_bareme"].mean()
        mean_ratio_normal = df_eval[df_eval["label"] == "NORMAL"]["ratio_devis_bareme"].mean()

        assert mean_ratio_fraude > mean_ratio_normal


# ===========================================================================
# Tests E2E — Isolation Forest sur features Auto
# ===========================================================================

class TestIsolationForestAuto:

    @pytest.fixture(scope="class")
    def df_train_features(self, module_auto, df_fixture_200):
        """Features numériques des dossiers normaux pour entraînement IF."""
        df_normal = df_fixture_200[df_fixture_200["Label_Anomalie"] == "NORMAL"].copy()
        df_enrichi = module_auto.engineer_features(df_normal)
        feature_cols = module_auto.get_feature_names()
        return df_enrichi[feature_cols].fillna(0).astype(float)

    @pytest.fixture(scope="class")
    def df_test_features(self, module_auto, df_fixture_200):
        """Features numériques de tous les dossiers pour évaluation."""
        df_enrichi = module_auto.engineer_features(df_fixture_200)
        feature_cols = module_auto.get_feature_names()
        return df_enrichi[feature_cols].fillna(0).astype(float)

    def test_isolation_forest_trains_without_error(self, df_train_features):
        """L'IF doit s'entraîner sur les 15 features Auto sans erreur."""
        from sklearn.ensemble import IsolationForest
        clf = IsolationForest(
            n_estimators=100,
            contamination=0.08,
            random_state=42,
        )
        clf.fit(df_train_features)
        assert clf.n_features_in_ == 15

    def test_isolation_forest_scores_all_samples(
        self, df_train_features, df_test_features
    ):
        """IF doit scorer 200 dossiers sans erreur."""
        from sklearn.ensemble import IsolationForest
        clf = IsolationForest(n_estimators=100, contamination=0.08, random_state=42)
        clf.fit(df_train_features)
        scores = clf.decision_function(df_test_features)
        assert len(scores) == 200
        assert not np.isnan(scores).any()

    def test_fraud_scores_lower_than_normal(
        self, module_auto, df_fixture_200, df_train_features, df_test_features
    ):
        """
        Les dossiers frauduleux doivent avoir un score IF plus bas que les normaux.
        Score IF : plus bas = plus anomal [Liu2008].
        """
        from sklearn.ensemble import IsolationForest
        clf = IsolationForest(n_estimators=100, contamination=0.08, random_state=42)
        clf.fit(df_train_features)
        scores = clf.decision_function(df_test_features)

        labels = df_fixture_200["Label_Anomalie"].values
        mean_score_fraude = scores[labels == "FRAUDE"].mean()
        mean_score_normal = scores[labels == "NORMAL"].mean()

        assert mean_score_fraude < mean_score_normal, (
            f"Scores IF : fraude={mean_score_fraude:.4f} doit être < "
            f"normal={mean_score_normal:.4f}"
        )

    def test_no_crash_on_single_sample(self, module_auto, auto_yaml_path):
        """Pipeline sur un seul dossier — aucun crash."""
        from modules.auto.auto_module import AutoModule
        m = AutoModule(config_path=auto_yaml_path)
        df = pd.DataFrame({
            "ID_Sinistre": ["X"], "ID_Assure": ["A"],
            "Montant_Devis": [376878.0],
            "Montant_Reference_Bareme": [376635.0],
            "Valeur_Venale_EUR": [10075.0],
            "Devise": ["XAF"],
            "Flag_Sinistre_Nuit": [True],
            "Nb_Temoins": [0],
            "Flag_Doc_Altere": [False],
            "ID_Garage": ["G01"],
            "Agrement_CIMA": [False],
            "Constat_Amiable_Present": [True],
            "Rapport_Expertise_Signe": [True],
            "Delai_Declaration": [6],
            "Anciennete_Contrat": [1423],
            "Source_Flux": ["API"],
            "Confiance_OCR_Glob": [np.nan],
            "Ratio_MO": [0.875],
            "Nb_Sinistres_12m": [0],
            "Heure_Saisie": [8],
        })
        result = m.engineer_features(df)
        assert len(result) == 1
        assert len(m.get_feature_names()) == 15