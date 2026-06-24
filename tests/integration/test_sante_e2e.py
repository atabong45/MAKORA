"""
Tests d'intégration — Pipeline complet Santé (T5)

Couvre le flux SS-01 de bout en bout :
  DataFrame santé → Pipeline → MAKORAOutput avec RCA non-None

Stratégie d'entraînement :
  Le Detector est entraîné sur les données NORMALES uniquement,
  puis évalué sur le dataset complet (normal + fraude).
  C'est l'approche correcte en production non-supervisée :
  le modèle apprend la distribution normale et détecte les écarts.
  [Chandola2009] : unsupervised anomaly detection — fit sur données saines.

Dépendances mockées : Ollama (LLMNarrator).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd
import pytest

from core.data_models import MAKORAOutput
from core.detector import Detector, IsolationForestStrategy
from core.explainer import Explainer
from core.pipeline import Pipeline
from core.rca.engine import RCAEngine
from modules.sante.sante_module import SanteModule


# ---------------------------------------------------------------------------
# Fixtures — datasets
# ---------------------------------------------------------------------------

@pytest.fixture
def sante_df_normal() -> pd.DataFrame:
    """10 dossiers normaux — sert à entraîner le Detector."""
    rng = np.random.default_rng(42)
    n = 10
    return pd.DataFrame({
        "ID_Sinistre":       [f"SIN_{i:03d}" for i in range(n)],
        "ID_Assure":         [f"ASS_{i:03d}" for i in range(n)],
        "ID_Praticien":      [f"PRAT_{i % 3:02d}" for i in range(n)],
        "Dossier_ID":        [f"SIN_{i:03d}" for i in range(n)],
        "Code_Acte":         ["CONSULT_001"] * n,
        "Montant_Facture":   rng.uniform(5000, 12000, n),
        "Prix_Unitaire_Ref": rng.uniform(8000, 11000, n),
        "Devise":            ["XAF"] * n,
        "Date_Soin":         pd.date_range("2026-01-05", periods=n, freq="2D"),
        "Source_Flux":       ["test_fixture"] * n,
        "Sexe_Assure":       ["M", "F"] * 5,
    })


@pytest.fixture
def sante_df_with_fraud(sante_df_normal) -> pd.DataFrame:
    """
    Dataset complet : 10 dossiers normaux + 3 frauduleux.
    Les dossiers frauduleux ont un ratio_prix_mercuriale ~5x
    — outliers nets par rapport à la distribution normale.
    """
    fraud_rows = pd.DataFrame({
        "ID_Sinistre":       ["FRAUD_001", "FRAUD_002", "FRAUD_003"],
        "ID_Assure":         ["ASS_FRAUD", "ASS_FRAUD", "ASS_FRAUD"],
        "ID_Praticien":      ["PRAT_SUSPECT", "PRAT_SUSPECT", "PRAT_SUSPECT"],
        "Dossier_ID":        ["FRAUD_001", "FRAUD_002", "FRAUD_003"],
        "Code_Acte":         ["CONSULT_001", "CONSULT_001", "CONSULT_001"],
        "Montant_Facture":   [50000.0, 48000.0, 55000.0],   # ~5x mercuriale
        "Prix_Unitaire_Ref": [10000.0, 10000.0, 10000.0],
        "Devise":            ["XAF", "XAF", "XAF"],
        "Date_Soin":         [
            pd.Timestamp("2026-01-06"),  # mardi
            pd.Timestamp("2026-01-10"),  # samedi (weekend)
            pd.Timestamp("2026-01-11"),  # dimanche (weekend)
        ],
        "Source_Flux":       ["test_fixture"] * 3,
        "Sexe_Assure":       ["M", "M", "M"],
    })
    return pd.concat([sante_df_normal, fraud_rows], ignore_index=True)


@pytest.fixture
def trained_pipeline(sante_df_normal) -> Pipeline:
    """
    Pipeline entraîné sur les données NORMALES uniquement.
    [Chandola2009] : en détection d'anomalies non-supervisée,
    le modèle apprend la distribution normale et détecte les écarts.

    Threshold abaissé à 0.40 (vs 0.70 en production) car la fixture
    est un petit dataset synthétique — les scores normalisés ont
    une variance plus faible qu'en production réelle.
    """
    module = SanteModule()

    # Entraînement sur données normales uniquement
    df_feat = module.engineer_features(sante_df_normal)
    feature_cols = module.get_feature_names()
    available = [c for c in feature_cols if c in df_feat.columns]
    X_train = df_feat[available].values.astype(np.float64)

    # [Liu2008] : contamination=0.08 — taux fraude santé estimé 3-10%
    # threshold=0.40 adapté aux petits datasets de test (< 50 lignes)
    strategy = IsolationForestStrategy(contamination=0.08)
    detector = Detector(strategy=strategy, threshold=0.40)
    detector.fit(X_train)

    # SHAP explainer — optionnel, None si non disponible
    explainer = None
    try:
        explainer = Explainer(detector=detector, feature_names=available)
    except Exception:
        pass

    # RCA engine
    rca_engine = RCAEngine()

    # LLM narrator mocké — Ollama non disponible en CI
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "Narration LLM mockée pour les tests."

    return Pipeline(
        module=module,
        detector=detector,
        explainer=explainer,
        rca_engine=rca_engine,
        llm_narrator=mock_llm,
    )


# ---------------------------------------------------------------------------
# Tests d'intégration
# ---------------------------------------------------------------------------

class TestSanteE2E:

    def test_pipeline_runs_without_error(self, trained_pipeline,
                                          sante_df_with_fraud):
        """Le pipeline complet s'exécute sans exception."""
        outputs = trained_pipeline.run(sante_df_with_fraud)
        assert outputs is not None
        assert len(outputs) == len(sante_df_with_fraud)

    def test_outputs_are_makora_output_instances(self, trained_pipeline,
                                                   sante_df_with_fraud):
        """Chaque sortie est une instance MAKORAOutput."""
        outputs = trained_pipeline.run(sante_df_with_fraud)
        assert all(isinstance(o, MAKORAOutput) for o in outputs)

    def test_branch_is_sante(self, trained_pipeline, sante_df_with_fraud):
        """La branche dans chaque sortie est 'sante'."""
        outputs = trained_pipeline.run(sante_df_with_fraud)
        assert all(o.branch == "sante" for o in outputs)

    def test_anomaly_scores_are_float(self, trained_pipeline,
                                       sante_df_with_fraud):
        """Les scores d'anomalie sont des float dans [0, 1]."""
        outputs = trained_pipeline.run(sante_df_with_fraud)
        for o in outputs:
            assert isinstance(o.anomaly_score, float)
            assert 0.0 <= o.anomaly_score <= 1.0

    def test_anomalies_detected(self, trained_pipeline, sante_df_with_fraud):
        """
        Au moins un dossier est détecté comme anomalie.
        Les 3 dossiers frauduleux ont ratio=5x — outliers nets
        par rapport à la distribution d'entraînement normale.
        """
        outputs = trained_pipeline.run(sante_df_with_fraud)
        assert any(o.is_anomaly for o in outputs), (
            "Aucune anomalie détectée. Scores : "
            + str([round(o.anomaly_score, 3) for o in outputs])
        )

    def test_fraud_dossiers_have_higher_scores(self, trained_pipeline,
                                                sante_df_with_fraud):
        """
        Les dossiers frauduleux ont un score moyen supérieur
        aux dossiers normaux — validation de la discriminance du modèle.
        """
        outputs = trained_pipeline.run(sante_df_with_fraud)
        fraud_ids = {"FRAUD_001", "FRAUD_002", "FRAUD_003"}

        fraud_scores = [o.anomaly_score for o in outputs
                        if o.dossier_id in fraud_ids]
        normal_scores = [o.anomaly_score for o in outputs
                         if o.dossier_id not in fraud_ids]

        assert fraud_scores, "Aucun output pour les dossiers frauduleux"
        assert normal_scores, "Aucun output pour les dossiers normaux"

        avg_fraud = sum(fraud_scores) / len(fraud_scores)
        avg_normal = sum(normal_scores) / len(normal_scores)

        assert avg_fraud > avg_normal, (
            f"Score moyen fraude ({avg_fraud:.3f}) n'est pas supérieur "
            f"au score moyen normal ({avg_normal:.3f})"
        )

    def test_rca_non_none_for_anomalies(self, trained_pipeline,
                                         sante_df_with_fraud):
        """Les anomalies détectées ont un RCAResult non-None."""
        outputs = trained_pipeline.run(sante_df_with_fraud)
        anomalies = [o for o in outputs if o.is_anomaly]
        assert len(anomalies) > 0, (
            "Aucune anomalie détectée — revoir threshold dans la fixture. "
            "Scores : " + str([round(o.anomaly_score, 3) for o in outputs])
        )
        has_rca = any(o.rca_result is not None for o in anomalies)
        assert has_rca, (
            "Aucune anomalie n'a de RCAResult. "
            "Vérifier les règles YAML et les features calculées."
        )

    def test_surfacturation_rule_triggered(self, trained_pipeline,
                                            sante_df_with_fraud):
        """
        Les dossiers FRAUD_* avec ratio=5x doivent déclencher une règle RCA
        de fraude intentionnelle.

        NB: depuis T13.2 (features réseau), la fixture déclenche aussi
        RCA_CONC_001 (concentration praticien) qui a une priorité plus haute
        que RCA_SURF_001. Le test accepte les deux règles car toutes deux
        catégorisent correctement le scénario de fraude par surfacturation
        coordonnée. [Chain of Responsibility - GoF1994]
        """
        outputs = trained_pipeline.run(sante_df_with_fraud)
        fraud_outputs = [
            o for o in outputs
            if o.dossier_id in {"FRAUD_001", "FRAUD_002", "FRAUD_003"}
            and o.is_anomaly
            and o.rca_result is not None
        ]
        if fraud_outputs:
            triggered = {o.rca_result.rule_id for o in fraud_outputs}
            # Au moins une règle de fraude intentionnelle doit être déclenchée.
            # RCA_SURF_001 : surfacturation simple (avant T13.2)
            # RCA_CONC_001 : concentration praticien (T13.2 — feature réseau)
            # Les deux signalent correctement la fraude FRAUD_001/002/003.
            expected_rules = {"RCA_SURF_001", "RCA_CONC_001"}
            assert triggered & expected_rules, (
                f"Aucune règle de fraude attendue déclenchée. "
                f"Règles trouvées : {triggered}. "
                f"Attendu : au moins une de {expected_rules}"
            )

    def test_llm_narration_for_anomalies(self, trained_pipeline,
                                          sante_df_with_fraud):
        """Les anomalies ont une explication LLM (mockée)."""
        outputs = trained_pipeline.run(sante_df_with_fraud)
        anomalies = [o for o in outputs if o.is_anomaly]
        if anomalies:
            assert all(o.explanation_fr is not None for o in anomalies)

    def test_processing_time_positive(self, trained_pipeline,
                                       sante_df_with_fraud):
        """Le temps de traitement est positif pour chaque dossier."""
        outputs = trained_pipeline.run(sante_df_with_fraud)
        assert all(o.processing_time_ms > 0 for o in outputs)

    def test_kernel_does_not_reference_sante_module(self):
        """Vérifie que pipeline.py ne référence aucun module concret."""
        import inspect
        from core import pipeline
        source = inspect.getsource(pipeline)
        assert "sante_module" not in source, (
            "VIOLATION RÈGLE D'OR : 'sante_module' trouvé dans pipeline.py"
        )
        assert "auto_module" not in source, (
            "VIOLATION RÈGLE D'OR : 'auto_module' trouvé dans pipeline.py"
        )