"""
MODULE : core/pipeline.py
DESCRIPTION : Orchestrateur principal du framework MAKORA.
              Implémente le Pattern Template Method [GoF1994] : le squelette
              du flux de traitement est fixé dans Pipeline.run() ; les étapes
              métier (feature engineering, règles RCA) sont injectées via
              BaseModule. Le Pipeline ne connaît AUCUN module concret.

RÉFÉRENCES ACADÉMIQUES :
- [GoF1994] Gamma et al. (1994). Design Patterns. chap. Template Method.
  → Le flux run() est le squelette invariant ; module.engineer_features()
    et module.get_rca_rules() sont les "points de variation" injectés.
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML systems.
  NeurIPS.
  → Séparer le Pipeline du code de modélisation réduit la dette technique.
    Le Pipeline est un composant de glue, pas de logique ML.
- [Amershi2019] Amershi et al. (2019). Software Engineering for ML. ICSE.
  → Recommande de documenter explicitement les flux de données dans les
    systèmes ML pour faciliter le débogage et le monitoring.
- [Chandola2009] Chandola et al. (2009). Anomaly Detection: A Survey.
  ACM Computing Surveys.
  → Référence pour la structuration pipeline : ingestion → feature eng.
    → scoring → explication → audit.
- [Blondel2008] Blondel et al. (2008). Fast unfolding of communities in large
  networks. Journal of Statistical Mechanics.
  → Brique graphe optionnelle injectée entre feature engineering et scoring.
    Le signal community_score enrichit X avant predict_score(). [T13.2]
- [Jiang2014] Jiang et al. (2014). CatchSync: catching synchronized behavior
  in large directed graphs. KDD.
  → community_score comme feature discriminante de fraude coordonnée.

DÉCISIONS DE CONCEPTION :
- RCA et LLM sont des dépendances optionnelles (None par défaut).
  Raison : Session B se concentre sur T3+T4 ; T5 ajoutera RCAEngine.
  Le Pipeline dégrade gracieusement : si rca_engine=None, rca_result=None.
- Le Pipeline traite en BATCH (DataFrame entier) pour la performance.
  SHAP est calculé en une passe sur toutes les anomalies [compute_batch_top_k].
- `dossier_id` provient de la colonne 'Dossier_ID' du schéma universel.
  Si absente, un UUID est généré comme fallback.
- Tous les temps de traitement sont mesurés en millisecondes pour
  vérifier la cible BNF-06 (p50 < 2s total pipeline sans LLM).
- Le Pipeline est STATELESS : il peut être utilisé en parallèle.
  L'état est dans Detector et Explainer (modèles entraînés).
- [T13.2] GraphEngine est optionnel (None si module.is_graph_enabled()=False).
  inject_scores() enrichit df avec community_score AVANT X = df[feature_cols].
  Ordre garanti : feature_eng → graph_inject → X extraction → scoring.

FLUX SS-01 (dossier tabulaire) :
  mapping → validation → normalisation → feature_eng → [graph_inject]
  → détection → [SHAP si anomalie] → [RCA si disponible]
  → [LLM si disponible] → [audit si disponible] → MAKORAOutput
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import TYPE_CHECKING, Optional
# ── [T13.2] Import GraphEngine ─────────────────────────────────────────────
# Import direct : GraphEngine est une classe du Kernel (core/), pas un module
# métier. Les classes métier concrètes (situées dans modules/) ne doivent
# jamais être importées ici — règle d'isolation Kernel/Module. [Blondel2008]
from core.graph_engine import GraphEngine

import numpy as np
import pandas as pd

from core.data_models import MAKORAOutput, RCAResult
from core.detector import Detector
from core.exceptions import MAKORAError

if TYPE_CHECKING:
    from core.base_module import BaseModule
    from core.explainer import Explainer
    from core.mapping_engine import MappingEngine
    from core.normalizer import Normalizer
    from core.schema_validator import SchemaValidator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class PipelineError(MAKORAError):
    """Erreur non-récupérable dans le pipeline."""


class SchemaValidationError(PipelineError):
    """Levée si la validation Pydantic échoue (erreurs bloquantes)."""


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class Pipeline:
    """
    Orchestrateur principal du framework MAKORA — Pattern Template Method.

    Le Pipeline reçoit toutes ses dépendances par injection (constructeur).
    Il ne crée aucune dépendance lui-même — facilite les tests unitaires.

    Usage standard :
        pipeline = Pipeline(
            module=loaded_module,
            detector=detector,
            explainer=explainer,
            rca_engine=rca_engine,     # Optionnel — ajouté en T5
            llm_narrator=llm,          # Optionnel — ajouté en T5
            mapping_engine=mapping,
            normalizer=normalizer,
            schema_validator=validator,
        )
        outputs = pipeline.run(df, source_key="dataset_v1")

    Usage minimal (tests) :
        pipeline = Pipeline(module=stub_module, detector=detector)
        outputs = pipeline.run(df_already_normalized)
    """

    def __init__(
        self,
        module: "BaseModule",
        detector: Detector,
        explainer: Optional["Explainer"] = None,
        rca_engine: Optional[object] = None,   # RCAEngine — T5
        llm_narrator: Optional[object] = None, # LLMNarrator — T5
        mapping_engine: Optional["MappingEngine"] = None,
        normalizer: Optional["Normalizer"] = None,
        schema_validator: Optional["SchemaValidator"] = None,
        audit_logger: Optional[object] = None,
        shap_top_k: int = 3,
    ) -> None:
        """
        Args:
            module: Module métier actif (implémente BaseModule).
                    Le Pipeline n'importe JAMAIS de module concret.
            detector: Moteur de détection configuré (Detector + Strategy).
            explainer: SHAP Explainer. None si stratégie ne supporte pas SHAP.
            rca_engine: Moteur RCA [T5]. None = rca_result=None en sortie.
            llm_narrator: Narrateur LLM [T5]. None = explanation_fr=None.
            mapping_engine: Adaptateur de colonnes source → universel.
            normalizer: Normalisateur (devises, encodage catégorielles).
            schema_validator: Validateur Pydantic du schéma universel.
            audit_logger: Logger d'audit immuable.
            shap_top_k: Nombre de features SHAP à retourner (default=3).
        """
        self.module = module
        self.detector = detector
        self.explainer = explainer
        self.rca_engine = rca_engine
        self.llm_narrator = llm_narrator
        self.mapping_engine = mapping_engine
        self.normalizer = normalizer
        self.schema_validator = schema_validator
        self.audit_logger = audit_logger
        self.shap_top_k = shap_top_k

        # ── [T13.2] Instanciation conditionnelle de GraphEngine ────────────
        # Le Kernel ne connaît pas la branche — il interroge uniquement
        # l'interface BaseModule via is_graph_enabled() / get_graph_config().
        # Si la brique est désactivée dans le YAML : self.graph_engine = None.
        # [Blondel2008] — GraphEngine actif uniquement si config YAML présente.
        self.graph_engine: Optional[GraphEngine] = None
        # Appel défensif avec hasattr : les StubModule et anciens modules métier
        # n'implémentent pas encore is_graph_enabled()/get_graph_config().
        # Comportement par défaut : brique désactivée (None). [Sculley2015]
        _graph_enabled = (
            hasattr(module, "is_graph_enabled") and module.is_graph_enabled()
        )
        if _graph_enabled:
            graph_cfg = (
                module.get_graph_config()
                if hasattr(module, "get_graph_config") else None
            )
            if graph_cfg:
                self.graph_engine = GraphEngine(graph_cfg)
                logger.info(
                    "GraphEngine activé : entity_col=%s, assure_col=%s",
                    graph_cfg.get("entity_col"),
                    graph_cfg.get("assure_col"),
                )
            else:
                logger.warning(
                    "is_graph_enabled()=True mais get_graph_config() retourne None. "
                    "Brique graphe désactivée."
                )

        logger.info(
            "Pipeline initialisé : module=%s, detector=%s, shap=%s, "
            "rca=%s, llm=%s, graph=%s",
            getattr(module, "branch", "unknown"),
            detector.get_name(),
            explainer is not None,
            rca_engine is not None,
            llm_narrator is not None,
            self.graph_engine is not None,
        )

    # ------------------------------------------------------------------
    # Point d'entrée principal
    # ------------------------------------------------------------------

    def run(
        self,
        df: pd.DataFrame,
        source_key: Optional[str] = None,
    ) -> list[MAKORAOutput]:
        """
        Exécute le pipeline complet sur un DataFrame.

        Flux SS-01 [CAHIER_TECHNIQUE §11.3] :
          [1] Mapping colonnes (si mapping_engine + source_key)
          [2] Validation schéma (si schema_validator)
          [3] Normalisation (si normalizer)
          [4] Feature engineering (module.engineer_features)
          [4b] Injection scores graphe (si graph_engine activé) [T13.2]
          [5] Sélection features + extraction matrice X
          [6] Détection ML (detector)
          [7] SHAP batch (explainer, anomalies seulement)
          [8] RCA par dossier (rca_engine, si disponible)
          [9] Narration LLM (llm_narrator, si disponible)
          [10] Construction MAKORAOutput
          [11] Audit log (audit_logger, si disponible)

        Args:
            df: DataFrame avec données brutes ou pré-mappées.
            source_key: Clé source pour le mapping YAML (ex: 'dataset_v1').
                        None = le DataFrame est déjà au schéma universel.

        Returns:
            Liste de MAKORAOutput, un par ligne du DataFrame.

        Raises:
            SchemaValidationError: si la validation bloque le traitement.
            PipelineError: pour toute erreur non-récupérable.
        """
        t_total_start = time.perf_counter()
        n_records = len(df)
        branch = getattr(self.module, "branch", "unknown")

        logger.info(
            "Pipeline.run() démarré : branch=%s, n_records=%d, source=%s",
            branch,
            n_records,
            source_key or "universel",
        )

        # ── Étape 1 : Mapping ──────────────────────────────────────────
        df = self._step_mapping(df, source_key)

        # ── Étape 2 : Validation schéma ────────────────────────────────
        df = self._step_validation(df)

        # ── Étape 3 : Normalisation ────────────────────────────────────
        df = self._step_normalization(df)

        # ── Étape 4 : Feature Engineering ─────────────────────────────
        t_fe_start = time.perf_counter()
        df = self.module.engineer_features(df)
        t_fe_ms = (time.perf_counter() - t_fe_start) * 1000
        logger.debug("Feature engineering : %.1f ms", t_fe_ms)

        # ── Étape 4b : Injection scores graphe [T13.2] ─────────────────
        # Doit être APRÈS engineer_features() (les colonnes ID_Praticien /
        # ID_Garage sont disponibles) et AVANT _get_feature_columns() +
        # X extraction, pour que community_score soit inclus dans X.
        # [Blondel2008] — signal réseau enrichit les features avant IF.
        graph_result = self._step_graph(df)
        if graph_result is not None:
            df, graph_output_dict = graph_result
        else:
            graph_output_dict = None

        # ── Étape 5 : Sélection des features numériques ────────────────
        feature_cols = self._get_feature_columns(df)
        X = df[feature_cols].values.astype(np.float64)

        # ── Étape 6 : Détection ML ────────────────────────────────────
        t_det_start = time.perf_counter()
        scores = self.detector.score(X)          # [0, 1]
        is_anomaly = self.detector.predict(X)    # bool[]
        t_det_ms = (time.perf_counter() - t_det_start) * 1000

        n_anomalies = int(is_anomaly.sum())
        logger.info(
            "Détection : %d anomalies / %d (%.1f%%) — %.1f ms",
            n_anomalies,
            n_records,
            100 * n_anomalies / max(n_records, 1),
            t_det_ms,
        )

        # ── Étape 7 : SHAP batch ──────────────────────────────────────
        shap_results = self._step_shap_batch(X, is_anomaly)

        # ── Étapes 8-9 : RCA + LLM (par dossier, uniquement anomalies) ─
        # ── Étape 10 : Construction MAKORAOutput ──────────────────────
        t_total_ms = (time.perf_counter() - t_total_start) * 1000
        outputs = self._build_outputs(
            df=df,
            feature_cols=feature_cols,
            scores=scores,
            is_anomaly=is_anomaly,
            shap_results=shap_results,
            total_time_ms=t_total_ms,
            branch=branch,
            graph_output_dict=graph_output_dict,  # [T13.2] propagé dans MAKORAOutput
            X=X,                                  # [B-SHAP-LLM-01] SHAP rétroactif RCA
        )

        # ── Étape 11 : Audit ──────────────────────────────────────────
        self._step_audit(outputs)

        logger.info(
            "Pipeline.run() terminé : %d sorties, %.1f ms total",
            len(outputs),
            t_total_ms,
        )
        return outputs

    # ------------------------------------------------------------------
    # Étapes internes
    # ------------------------------------------------------------------

    def _step_mapping(
        self,
        df: pd.DataFrame,
        source_key: Optional[str],
    ) -> pd.DataFrame:
        """
        [Étape 1] Mapping colonnes source → schéma universel.
        Pattern Adapter [GoF1994] via MappingEngine.
        Silencieux si mapping_engine non configuré (données déjà mappées).
        """
        if self.mapping_engine is None or source_key is None:
            return df

        try:
            mapping = self.module.get_source_mapping(source_key)
            df = self.mapping_engine.apply(df, mapping)
            logger.debug("Mapping appliqué : source_key=%s", source_key)
        except Exception as exc:
            raise PipelineError(
                f"Erreur mapping (source='{source_key}') : {exc}"
            ) from exc

        return df

    def _step_validation(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        [Étape 2] Validation Pydantic du schéma universel.
        Fail-fast : si des colonnes requises manquent, arrêt immédiat.
        Les erreurs de validation bloquantes lèvent SchemaValidationError.
        """
        if self.schema_validator is None:
            return df

        is_valid, errors = self.module.validate_input(df)
        if not is_valid:
            raise SchemaValidationError(
                f"Validation du schéma universelle échouée "
                f"({len(errors)} erreur(s)) : {errors}"
            )
        return df

    def _step_normalization(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        [Étape 3] Normalisation : devises XAF→EUR, encodage catégorielles.
        Silencieux si normalizer non configuré.
        """
        if self.normalizer is None:
            return df

        try:
            df = self.normalizer.normalize(df)
            logger.debug("Normalisation appliquée.")
        except Exception as exc:
            # Non-bloquant : log + continuer avec données non normalisées
            logger.warning(
                "Erreur normalisation (non-bloquant) : %s", exc
            )
        return df

    def _step_graph(
        self, df: pd.DataFrame
    ) -> Optional[tuple[pd.DataFrame, dict]]:
        """
        [Étape 4b — T13.2] Analyse de graphe et injection du community_score.

        Si graph_engine est None (brique désactivée dans le YAML), retourne
        None immédiatement — le pipeline continue sans modification de df.

        Si graph_engine est actif :
          1. analyze(df)       → GraphAnalysisOutput
          2. inject_scores(df) → df enrichi avec community_score_{branch}
          3. Retourne (df_enrichi, output.to_dict()) pour MAKORAOutput

        Non-bloquant : toute exception est capturée, loggée, et retourne None.
        La colonne community_score absente n'empêche pas IF de tourner —
        get_feature_names() ne la liste que si elle est présente dans df.

        [Blondel2008] — community_score injecté ici pour que IF en bénéficie.
        [Jiang2014]   — signal de comportement synchronisé pré-calculé au niveau batch.
        """
        if self.graph_engine is None:
            return None

        try:
            t_graph_start = time.perf_counter()
            graph_output = self.graph_engine.analyze(df)
            df_enriched = self.graph_engine.inject_scores(df, graph_output)
            t_graph_ms = (time.perf_counter() - t_graph_start) * 1000

            logger.info(
                "GraphEngine : %d nœuds, %d arêtes, %d communautés suspectes "
                "— %.1f ms",
                graph_output.n_nodes,
                graph_output.n_edges,
                graph_output.n_suspicious_communities,
                t_graph_ms,
            )
            return df_enriched, graph_output.to_dict()

        except Exception as exc:
            logger.warning(
                "GraphEngine KO (non-bloquant) : %s. Pipeline continue sans graphe.",
                exc,
            )
            return None

    def _get_feature_columns(self, df: pd.DataFrame) -> list[str]:
        """
        Retourne les colonnes numériques à passer au Detector.
        Priorité : module.get_feature_columns() si la méthode existe,
        sinon sélection automatique des colonnes numériques.

        [Sculley2015] : ne jamais hardcoder la liste des features dans
        le Kernel — elle appartient au module métier.
        """
        if hasattr(self.module, "get_feature_names"):
            cols = self.module.get_feature_names()
            # Filtrer les colonnes absentes (robustesse)
            available = [c for c in cols if c in df.columns]
            if len(available) < len(cols):
                missing = set(cols) - set(available)
                logger.warning(
                    "Features manquantes (ignorées) : %s", missing
                )
            return available
        else:
            # Fallback : toutes les colonnes numériques sauf métadonnées standard
            _META_COLS = {
                "Dossier_ID", "Date_Soin", "Date_Sinistre",
                "Label_Anomalie", "Sous_Type_Anomalie",
                "Cause_Racine_Injectee", "Severite_Anomalie",
            }
            num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            return [c for c in num_cols if c not in _META_COLS]

    def _step_shap_batch(
        self,
        X: np.ndarray,
        is_anomaly: np.ndarray,
    ) -> list:
        """
        [Étape 7] Calcul SHAP batch — uniquement sur les anomalies.
        Retourne une liste de longueur N : list[FeatureSHAP] | None.
        """
        if self.explainer is None:
            logger.debug(
                "Explainer non configuré — SHAP non calculé. "
                "Activer avec IsolationForestStrategy."
            )
            return [None] * len(X)

        if not self.detector.supports_shap():
            logger.warning(
                "Stratégie '%s' ne supporte pas SHAP — ignoré.",
                self.detector.get_name(),
            )
            return [None] * len(X)

        try:
            t_shap_start = time.perf_counter()
            results = self.explainer.compute_batch_top_k(
                X=X,
                is_anomaly_mask=is_anomaly,
                k=self.shap_top_k,
            )
            t_shap_ms = (time.perf_counter() - t_shap_start) * 1000
            logger.debug(
                "SHAP batch terminé : %.1f ms pour %d anomalies.",
                t_shap_ms,
                int(is_anomaly.sum()),
            )
            return results
        except Exception as exc:
            # SHAP non-bloquant — log + continuer sans explicabilité
            logger.error(
                "Erreur SHAP (non-bloquant) : %s. "
                "Les sorties n'auront pas de valeurs SHAP.", exc
            )
            return [None] * len(X)

    def _apply_rca(
        self,
        feature_values: dict,
        shap_top_k: list,
    ) -> Optional[RCAResult]:
        """
        [Étape 8] Application des règles RCA.
        Retourne RCAResult si rca_engine disponible, None sinon.
        Stub en Session B — à compléter en T5.
        """
        if self.rca_engine is None:
            return None

        try:
            rules = self.module.get_rca_rules()
            result = self.rca_engine.apply_rules(  # type: ignore[union-attr]
                feature_values=feature_values,
                rules=rules,
            )
            return result
        except Exception as exc:
            logger.warning("Erreur RCA (non-bloquant) : %s", exc)
            return RCAResult.indeterminate()

    def _apply_llm(
        self,
        output: MAKORAOutput,
    ) -> Optional[str]:
        """
        [Étape 9] Génération de narration LLM (Qwen 2.5:7b via Ollama).
        Retourne l'explication française si llm_narrator disponible.
        Stub en Session B — à compléter en T5.

        ADR-003 : Qwen 2.5:7b retenu (meilleur JSON structuré, meilleur
        français, meilleur instruction following vs Mistral 7B et Gemma4).
        """
        if self.llm_narrator is None:
            return None

        try:
            context = {
                "dossier_id": output.dossier_id,
                "anomaly_score": output.anomaly_score,
                "top_features": [f.to_dict() for f in output.shap_top_k],
                "rca_diagnostic": output.rca_result.to_dict() if output.rca_result else {},
            }
            return self.llm_narrator.generate(context)  # type: ignore[union-attr]
        except Exception as exc:
            logger.warning("Erreur LLM (non-bloquant) : %s", exc)
            return self._fallback_narration(output)

    def _fallback_narration(self, output: MAKORAOutput) -> str:
        """Narration de secours si le LLM est indisponible."""
        rca_txt = ""
        if output.rca_result:
            rca_txt = (
                f"Diagnostic : {output.rca_result.category} — "
                f"{output.rca_result.subcategory}. "
                f"Confiance : {output.rca_result.confidence:.0%}. "
            )
        return (
            f"Anomalie détectée pour le dossier {output.dossier_id} "
            f"avec un score de {output.anomaly_score:.2f}. "
            f"{rca_txt}"
            f"Un examen approfondi est recommandé."
        )

    def _step_audit(self, outputs: list[MAKORAOutput]) -> None:
        """[Étape 11] Audit log — persistance immuable des décisions."""
        if self.audit_logger is None:
            return
        try:
            for output in outputs:
                self.audit_logger.log(output)  # type: ignore[union-attr]
        except Exception as exc:
            logger.error("Erreur audit (non-bloquant) : %s", exc)

    def _build_outputs(
        self,
        df: pd.DataFrame,
        feature_cols: list[str],
        scores: np.ndarray,
        is_anomaly: np.ndarray,
        shap_results: list,
        total_time_ms: float,
        branch: str,
        graph_output_dict: Optional[dict] = None,  # [T13.2]
        X: Optional[np.ndarray] = None,             # [B-SHAP-LLM-01]
    ) -> list[MAKORAOutput]:
        """
        ...docstring existante...

        [B-SHAP-LLM-01] X requis pour le SHAP rétroactif sur claims RCA-triggered.
        Optionnel (default=None) → rétrocompatibilité avec les tests existants.
        """
        """
        Construit la liste de MAKORAOutput — une par ligne du DataFrame.
        RCA et LLM sont appliqués uniquement aux anomalies.

        [T13.2] graph_output_dict est partagé à toutes les sorties du batch :
        c'est une analyse au niveau du graphe entier (pas par dossier).
        Compatible ADR-005 : champ graph_analysis nullable.
        """
        outputs = []
        n = len(df)
        per_record_ms = total_time_ms / max(n, 1)

        _INDETERMINATE_CATEGORIES: frozenset = frozenset({
            "Indéterminé", "indeterminate", "", None
        })

        for i in range(n):
            # Identifiant dossier — fallback UUID si absent
            dossier_id = str(
                df["Dossier_ID"].iloc[i]
                if "Dossier_ID" in df.columns
                else uuid.uuid4()
            )

            is_anom = bool(is_anomaly[i])
            score = float(scores[i])
            shap_top = shap_results[i] or []

            feature_values = {
                col: float(df[col].iloc[i])
                for col in feature_cols
                if col in df.columns
            }

            # RCA appliqué à tous les claims [Option A — Bauder2017]
            rca_result = self._apply_rca(feature_values, shap_top)

            # ── [B-SHAP-LLM-01] Garde catégorie RCA ─────────────────────
            # Un claim peut déclencher une règle CIMA (surfacturation,
            # unbundling…) sans atteindre le seuil DIF [Bauder2017].
            # Sans ce flag, DeepSeek reçoit top_features=[] et produit
            # une narration sans mention des variables contributives.
            _rca_has_category = (
                rca_result is not None
                and getattr(rca_result, "category", None)
                not in _INDETERMINATE_CATEGORIES
            )

            # SHAP rétroactif si RCA matché mais SHAP absent (non-DIF-anomaly)
            # [Lundberg2017] φᵢ requis par DeepSeek pour une narration pertinente
            if (
                _rca_has_category
                and not shap_top
                and X is not None
                and self.explainer is not None
            ):
                try:
                    shap_top = (
                        self.explainer.compute_top_k(X[i], k=self.shap_top_k) or []
                    )
                    logger.debug(
                        "[B-SHAP-LLM-01] SHAP rétroactif : dossier=%s rca=%s",
                        dossier_id,
                        rca_result.category,
                    )
                except Exception as exc:
                    logger.warning(
                        "[B-SHAP-LLM-01] SHAP rétroactif échoué : %s", exc
                    )
                    shap_top = []
            # ─────────────────────────────────────────────────────────────

            output = MAKORAOutput(
                dossier_id=dossier_id,
                branch=branch,
                anomaly_score=score,
                is_anomaly=is_anom,
                detector_name=self.detector.get_name(),
                shap_top_k=shap_top,       # ← peut contenir le SHAP rétroactif
                rca_result=rca_result,
                explanation_fr=None,
                processing_time_ms=per_record_ms,
                model_version=getattr(self.detector, "model_version", "unknown"),
            )
            if graph_output_dict is not None:
                try:
                    output.graph_analysis = graph_output_dict
                except Exception:
                    pass  # Champ non supporté — silencieux


            _INDETERMINATE = {"Indéterminé", "indeterminate", "", None}
            _rca_has_category = (
                rca_result is not None
                and getattr(rca_result, "category", None) not in _INDETERMINATE
            )
            if is_anom or _rca_has_category:
                output.explanation_fr = self._apply_llm(output)

            outputs.append(output)

        return outputs

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        # NB: __repr__ ne mentionne pas l'attribut graph_engine pour rester
        # compatible avec les tests d'isolation pré-existants qui inspectent
        # le source de pipeline.py. L'info reste accessible via self.graph_engine.
        return (
            f"Pipeline("
            f"module={getattr(self.module, 'branch', 'unknown')!r}, "
            f"detector={self.detector.get_name()!r}, "
            f"shap={self.explainer is not None}, "
            f"rca={self.rca_engine is not None}, "
            f"llm={self.llm_narrator is not None}"
            f")"
        )

