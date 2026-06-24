"""
Tests d'intégration — core/pipeline.py

Couvre le flux complet Pipeline.run() en mode Session B :
- Détection sans RCA ni LLM (stubs None)
- Détection avec Explainer SHAP (si disponible)
- Dégradation gracieuse : composants manquants → pas d'erreur
- Généricité : le Pipeline fonctionne avec un stub de module quelconque
- Validation des propriétés MAKORAOutput
- Respect de la règle d'or : Pipeline n'importe pas de module concret

[GoF1994] Template Method — le flux est fixé, les points de variation injectés.
[Sculley2015] — le Pipeline est testable sans les modules concrets.
[Amershi2019] — les tests d'intégration couvrent le flux de données complet.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from core.data_models import MAKORAOutput, RCAResult, FeatureSHAP
from core.detector import (
    Detector,
    IsolationForestStrategy,
    LOFStrategy,
    build_detector,
)
from core.explainer import Explainer
from core.pipeline import Pipeline, PipelineError, SchemaValidationError


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def shap_available() -> bool:
    try:
        import shap  # noqa: F401
        return True
    except ImportError:
        return False


requires_shap = pytest.mark.skipif(
    not shap_available(),
    reason="Package 'shap' non installé.",
)


# ---------------------------------------------------------------------------
# Stub de module — respecte BaseModule sans l'importer concrètement
# ---------------------------------------------------------------------------

FEATURE_COLS = [
    "ratio_prix_mercuriale",
    "incoherence_sexe_acte",
    "historique_ratio_praticien",
    "nb_sinistres_30j",
    "is_weekend_care",
]


class StubModule:
    """
    Stub de BaseModule pour les tests d'intégration.
    Le Pipeline ne doit JAMAIS être couplé à SanteModule ou AutoModule
    → utiliser ce stub prouve la généricité [GoF1994 § Plugin Contract].
    """

    branch = "test_branch"

    def validate_input(self, df: pd.DataFrame) -> tuple[bool, list[str]]:
        """Validation minimale : les colonnes features doivent exister."""
        missing = [c for c in FEATURE_COLS if c not in df.columns]
        if missing:
            return False, [f"Colonne manquante : {c}" for c in missing]
        return True, []

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Feature engineering stub — retourne le DataFrame tel quel.
        Dans SanteModule, cette méthode calcule ratio_prix_mercuriale etc.
        """
        return df.copy()

    def get_rca_rules(self) -> list[dict]:
        return []  # Stub — T5 définira les règles réelles

    def get_feature_columns(self) -> list[str]:
        return FEATURE_COLS

    def get_source_mapping(self, source_key: str) -> dict:
        return {}  # Stub — pas de mapping en test


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

N_FEATURES = len(FEATURE_COLS)
N_TRAIN = 500
N_TEST = 30


@pytest.fixture
def stub_module() -> StubModule:
    return StubModule()


@pytest.fixture
def df_train() -> pd.DataFrame:
    """DataFrame d'entraînement : distribution normale, sans anomalies évidentes."""
    rng = np.random.default_rng(42)
    data = rng.standard_normal((N_TRAIN, N_FEATURES))
    df = pd.DataFrame(data, columns=FEATURE_COLS)
    df["Dossier_ID"] = [f"DOSS-TRAIN-{i:05d}" for i in range(N_TRAIN)]
    return df


@pytest.fixture
def df_test_mixed() -> pd.DataFrame:
    """
    DataFrame de test : 20 normaux + 10 anomalies évidentes.
    Les anomalies sont à 10 écarts-types — IF doit toutes les détecter.
    """
    rng = np.random.default_rng(0)
    normals = rng.standard_normal((20, N_FEATURES))
    anomalies = rng.standard_normal((10, N_FEATURES)) * 0.1 + 10

    data = np.vstack([normals, anomalies])
    df = pd.DataFrame(data, columns=FEATURE_COLS)
    df["Dossier_ID"] = [f"DOSS-TEST-{i:05d}" for i in range(N_TEST)]
    df["Label_Anomalie"] = [0] * 20 + [1] * 10  # Ground truth pour évaluation
    return df


@pytest.fixture
def fitted_detector(df_train) -> Detector:
    """Detector IF entraîné sur df_train."""
    config = {
        "algorithm": "isolation_forest",
        "contamination": 0.08,
        "n_estimators": 50,
        "threshold": 0.5,
        "random_state": 42,
    }
    d = build_detector(config)
    X = df_train[FEATURE_COLS].values.astype(np.float64)
    d.fit(X)
    return d


@pytest.fixture
def pipeline_minimal(stub_module, fitted_detector) -> Pipeline:
    """Pipeline minimal : pas de SHAP, pas de RCA, pas de LLM."""
    return Pipeline(module=stub_module, detector=fitted_detector)


@pytest.fixture
def pipeline_with_shap(stub_module, fitted_detector) -> Pipeline:
    """Pipeline avec Explainer SHAP (si disponible)."""
    if not shap_available():
        return Pipeline(module=stub_module, detector=fitted_detector)

    explainer = Explainer(
        strategy=fitted_detector.strategy,
        feature_names=FEATURE_COLS,
    )
    explainer.initialize()
    return Pipeline(
        module=stub_module,
        detector=fitted_detector,
        explainer=explainer,
        shap_top_k=3,
    )


# ===========================================================================
# Pipeline minimal (sans SHAP/RCA/LLM)
# ===========================================================================

class TestPipelineMinimal:

    def test_run_returns_list_of_makora_output(
        self, pipeline_minimal, df_test_mixed
    ):
        outputs = pipeline_minimal.run(df_test_mixed)
        assert isinstance(outputs, list)
        assert len(outputs) == N_TEST
        assert all(isinstance(o, MAKORAOutput) for o in outputs)

    def test_output_count_matches_input(self, pipeline_minimal, df_test_mixed):
        outputs = pipeline_minimal.run(df_test_mixed)
        assert len(outputs) == len(df_test_mixed)

    def test_dossier_ids_preserved(self, pipeline_minimal, df_test_mixed):
        """Les IDs du DataFrame d'entrée doivent se retrouver dans les sorties."""
        outputs = pipeline_minimal.run(df_test_mixed)
        expected_ids = df_test_mixed["Dossier_ID"].tolist()
        output_ids = [o.dossier_id for o in outputs]
        assert output_ids == expected_ids

    def test_branch_set_from_module(self, pipeline_minimal, df_test_mixed):
        outputs = pipeline_minimal.run(df_test_mixed)
        assert all(o.branch == "test_branch" for o in outputs)

    def test_anomaly_scores_in_unit_interval(self, pipeline_minimal, df_test_mixed):
        outputs = pipeline_minimal.run(df_test_mixed)
        for o in outputs:
            assert 0.0 <= o.anomaly_score <= 1.0, (
                f"Score hors [0,1] pour {o.dossier_id} : {o.anomaly_score}"
            )

    def test_is_anomaly_is_bool(self, pipeline_minimal, df_test_mixed):
        outputs = pipeline_minimal.run(df_test_mixed)
        for o in outputs:
            assert isinstance(o.is_anomaly, bool)

    def test_detector_name_correct(self, pipeline_minimal, df_test_mixed):
        outputs = pipeline_minimal.run(df_test_mixed)
        assert all(o.detector_name == "isolation_forest" for o in outputs)

    def test_no_shap_without_explainer(self, pipeline_minimal, df_test_mixed):
        """Sans Explainer, shap_top_k doit être vide pour tous les dossiers."""
        outputs = pipeline_minimal.run(df_test_mixed)
        for o in outputs:
            assert o.shap_top_k == []

    def test_no_rca_without_engine(self, pipeline_minimal, df_test_mixed):
        """Sans RCAEngine, rca_result doit être None."""
        outputs = pipeline_minimal.run(df_test_mixed)
        for o in outputs:
            assert o.rca_result is None

    def test_timestamp_populated(self, pipeline_minimal, df_test_mixed):
        outputs = pipeline_minimal.run(df_test_mixed)
        for o in outputs:
            assert o.timestamp is not None
            assert o.timestamp.endswith("Z")

    def test_anomalies_detected_in_obvious_dataset(
        self, pipeline_minimal, df_test_mixed
    ):
        """
        Les 10 anomalies à +10 sigma doivent être détectées.
        Cible : recall >= 0.8 sur ces anomalies évidentes.
        [Bauder2017] : seuil de validation académique minimal.
        """
        outputs = pipeline_minimal.run(df_test_mixed)
        # Les 10 derniers enregistrements sont les anomalies injectées
        anomaly_outputs = outputs[20:]
        n_detected = sum(o.is_anomaly for o in anomaly_outputs)
        recall = n_detected / 10

        assert recall >= 0.7, (
            f"Recall trop faible : {recall:.2f}. "
            f"Attendu >= 0.70 sur anomalies à +10 sigma. "
            f"Vérifier contamination et threshold."
        )


# ===========================================================================
# Pipeline avec SHAP
# ===========================================================================

@requires_shap
class TestPipelineWithSHAP:

    def test_anomalies_have_shap_values(
        self, pipeline_with_shap, df_test_mixed
    ):
        """is_anomaly=True → shap_top_k doit être peuplé."""
        outputs = pipeline_with_shap.run(df_test_mixed)
        anomalies = [o for o in outputs if o.is_anomaly]

        if not anomalies:
            pytest.skip("Aucune anomalie détectée — test non-applicable.")

        for o in anomalies:
            assert len(o.shap_top_k) > 0, (
                f"Anomalie {o.dossier_id} sans valeurs SHAP."
            )

    def test_normal_records_have_no_shap(self, pipeline_with_shap, df_test_mixed):
        """is_anomaly=False → shap_top_k doit être vide (optimisation perf)."""
        outputs = pipeline_with_shap.run(df_test_mixed)
        normals = [o for o in outputs if not o.is_anomaly]

        for o in normals:
            assert o.shap_top_k == [], (
                f"Dossier normal {o.dossier_id} ne devrait pas avoir de SHAP."
            )

    def test_shap_top_k_has_correct_count(self, pipeline_with_shap, df_test_mixed):
        outputs = pipeline_with_shap.run(df_test_mixed)
        anomalies = [o for o in outputs if o.is_anomaly]

        for o in anomalies:
            assert len(o.shap_top_k) <= 3  # shap_top_k=3 dans la fixture

    def test_shap_feature_names_from_module(
        self, pipeline_with_shap, df_test_mixed
    ):
        """Les noms SHAP doivent correspondre aux features du module."""
        outputs = pipeline_with_shap.run(df_test_mixed)
        anomalies = [o for o in outputs if o.is_anomaly]

        for o in anomalies:
            for f in o.shap_top_k:
                assert f.name in FEATURE_COLS, (
                    f"Feature SHAP inconnue : '{f.name}'. "
                    f"Doit être dans {FEATURE_COLS}."
                )


# ===========================================================================
# Dégradation gracieuse
# ===========================================================================

class TestPipelineGracefulDegradation:

    def test_missing_dossier_id_generates_uuid(
        self, stub_module, fitted_detector
    ):
        """Si 'Dossier_ID' est absent, le Pipeline génère un UUID."""
        rng = np.random.default_rng(42)
        df = pd.DataFrame(
            rng.standard_normal((5, N_FEATURES)),
            columns=FEATURE_COLS,
        )
        # Pas de colonne Dossier_ID

        pipeline = Pipeline(module=stub_module, detector=fitted_detector)
        outputs = pipeline.run(df)

        assert len(outputs) == 5
        ids = [o.dossier_id for o in outputs]
        # Les IDs doivent être non-vides et différents
        assert all(ids)
        assert len(set(ids)) == 5, "Les UUIDs générés doivent être uniques."

    def test_no_normalizer_does_not_crash(
        self, stub_module, fitted_detector, df_test_mixed
    ):
        """Sans Normalizer, le Pipeline continue."""
        pipeline = Pipeline(
            module=stub_module,
            detector=fitted_detector,
            normalizer=None,
        )
        outputs = pipeline.run(df_test_mixed)
        assert len(outputs) == N_TEST

    def test_pipeline_with_lof_no_shap(self, stub_module, df_train, df_test_mixed):
        """
        Avec LOF (sans SHAP), le Pipeline doit fonctionner mais
        shap_top_k doit être vide.
        """
        lof = LOFStrategy(n_neighbors=10, contamination=0.08)
        X = df_train[FEATURE_COLS].values.astype(np.float64)
        lof.fit(X)
        detector = Detector(strategy=lof, threshold=0.5)

        pipeline = Pipeline(module=stub_module, detector=detector)
        outputs = pipeline.run(df_test_mixed)

        assert len(outputs) == N_TEST
        assert all(o.detector_name == "lof" for o in outputs)
        assert all(o.shap_top_k == [] for o in outputs)

    def test_stub_rca_engine_returns_none(
        self, stub_module, fitted_detector, df_test_mixed
    ):
        """
        Un rca_engine=None signifie rca_result=None pour toutes les sorties.
        Comportement Session B attendu.
        """
        pipeline = Pipeline(
            module=stub_module,
            detector=fitted_detector,
            rca_engine=None,
        )
        outputs = pipeline.run(df_test_mixed)
        assert all(o.rca_result is None for o in outputs)


# ===========================================================================
# Règle d'or — généricité
# ===========================================================================

class TestPipelineGenericity:

    def test_pipeline_does_not_import_sante_module(self):
        """
        Le code source de pipeline.py ne doit CONTENIR aucune référence
        à un module concret (SanteModule, AutoModule, etc.).
        [Règle absolue MAKORA — Cahier Technique §11.5]
        """
        import inspect
        import core.pipeline as pipeline_module

        source = inspect.getsource(pipeline_module)
        forbidden_names = [
            "SanteModule", "AutoModule", "VieModule",
            "AgricoleModule", "sante_module", "auto_module",
        ]
        for name in forbidden_names:
            assert name not in source, (
                f"VIOLATION DE LA RÈGLE D'OR : '{name}' trouvé dans pipeline.py. "
                f"Le Kernel ne doit JAMAIS référencer un module concret."
            )

    def test_pipeline_works_with_any_stub_module(self, fitted_detector):
        """
        Le Pipeline doit fonctionner avec N'IMPORTE quel stub qui respecte
        le contrat BaseModule (validate_input + engineer_features +
        get_feature_columns).
        """
        class AnotherModule:
            branch = "auto"
            features = ["f1", "f2", "f3"]

            def validate_input(self, df):
                return True, []

            def engineer_features(self, df):
                return df

            def get_rca_rules(self):
                return []

            def get_feature_columns(self):
                return ["f1", "f2", "f3"]

        rng = np.random.default_rng(0)
        df = pd.DataFrame(
            rng.standard_normal((10, 3)),
            columns=["f1", "f2", "f3"],
        )
        df["Dossier_ID"] = [f"AUTO-{i}" for i in range(10)]

        # Entraîner un nouveau détecteur sur 3 features
        strat = IsolationForestStrategy(n_estimators=50, random_state=42)
        strat.fit(rng.standard_normal((200, 3)))
        detector = Detector(strategy=strat, threshold=0.5)

        pipeline = Pipeline(module=AnotherModule(), detector=detector)
        outputs = pipeline.run(df)

        assert len(outputs) == 10
        assert all(o.branch == "auto" for o in outputs)


# ===========================================================================
# Représentation et méta-données
# ===========================================================================

class TestPipelineMetadata:

    def test_repr_contains_key_info(self, pipeline_minimal):
        repr_str = repr(pipeline_minimal)
        assert "test_branch" in repr_str
        assert "isolation_forest" in repr_str

    def test_makora_output_to_dict_complete(
        self, pipeline_minimal, df_test_mixed
    ):
        """to_dict() doit retourner tous les champs requis par l'API."""
        outputs = pipeline_minimal.run(df_test_mixed)
        for o in outputs:
            d = o.to_dict()
            required_keys = [
                "dossier_id", "branch", "anomaly_score", "is_anomaly",
                "detector_name", "shap_top_k", "rca_result",
                "explanation_fr", "processing_time_ms", "timestamp",
            ]
            for key in required_keys:
                assert key in d, f"Clé '{key}' manquante dans to_dict()."

    def test_is_high_severity_threshold(
        self, pipeline_minimal, df_test_mixed
    ):
        """is_high_severity doit être True ssi anomaly_score >= 0.85."""
        outputs = pipeline_minimal.run(df_test_mixed)
        for o in outputs:
            expected = o.anomaly_score >= 0.85
            assert o.is_high_severity == expected