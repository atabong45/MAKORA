"""
MODULE : api/services/analyze_service.py
DESCRIPTION : Service d'analyse MAKORA — orchestre le Pipeline complet via
              PluginRegistry + load_strategy_from_joblib (DIF production).

RÈGLE ABSOLUE (ADR-002) : Ce service n'importe JAMAIS un module métier par son
nom concret. Il utilise exclusivement PluginRegistry.get(branch).

RÉFÉRENCES ACADÉMIQUES :
- [Xu2023] Xu et al. (2023). Deep Isolation Forest. IEEE TKDE.
  → Stratégie de production retenue (DIF [64,32]).
- [Lundberg2017] Lundberg & Lee (2017). NeurIPS.
  → KernelSHAP pour l'explicabilité — mode kernel si DIF.
- [Davis2006] Davis & Goadrich (2006). ICML.
  → Seuils calibrés : 0.349775 (Santé), 0.341498 (Auto).
- [Sculley2015] Sculley et al. (2015). NeurIPS.
  → Cache du Pipeline par branche : modèle DIF chargé une seule fois au
    démarrage, pas à chaque requête (fichiers > 300 Mo).

DÉCISIONS DE CONCEPTION :
- Cache _PIPELINE_CACHE[branch] : Pipeline instancié une fois par branche
  et réutilisé pour toutes les requêtes. Thread-safe en lecture (FastAPI).
- Fallback explainer=None si shap_background.npy absent : le pipeline
  fonctionne sans SHAP, les shap_top_k seront vides [Sculley2015].
- Modèle chargé depuis data/models/{branch}/dif_model.joblib (DIF production)
  avec fallback sur data/models/{branch}/production/if_classic_model.joblib.
"""

import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from uuid import UUID

import numpy as np
import pandas as pd
from fastapi import HTTPException
from sqlalchemy.orm import Session


from api.schemas.analyze import AnalyzeBatchResponse, AnalysisResult, RcaResult, ShapFeature
from core.plugin_registry import PluginRegistry
from core.detector import Detector, load_strategy_from_joblib
from core.explainer import Explainer
from core.pipeline import Pipeline
from core.rca.engine import RCAEngine
from core.llm.narrator import LLMNarrator
from core.llm.deepseek_backend import DeepSeekBackend
import os

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Chemins des modèles de production
# ---------------------------------------------------------------------------

_MODEL_DATA_ROOT = Path("data/models")

_DIF_MODEL_PATHS: dict[str, Path] = {
    "sante": _MODEL_DATA_ROOT / "sante" / "dif_model.joblib",
    "auto":  _MODEL_DATA_ROOT / "auto"  / "dif_model.joblib",
}

_IF_FALLBACK_PATHS: dict[str, Path] = {
    "sante": _MODEL_DATA_ROOT / "sante" / "production" / "if_classic_model.joblib",
    "auto":  _MODEL_DATA_ROOT / "auto"  / "production" / "if_classic_model.joblib",
}

_BACKGROUND_PATHS: dict[str, Path] = {
    "sante": _MODEL_DATA_ROOT / "sante" / "shap_background.npy",
    "auto":  _MODEL_DATA_ROOT / "auto"  / "shap_background.npy",
}

# ---------------------------------------------------------------------------
# Cache pipelines — chargé une fois au démarrage [Sculley2015]
# ---------------------------------------------------------------------------

_PIPELINE_CACHE: dict[str, Pipeline] = {}


def _build_pipeline(branch: str) -> Pipeline:
    """
    Construit le Pipeline de production pour une branche.

    Ordre de priorité pour le modèle :
    1. DIF [64,32] depuis data/models/{branch}/dif_model.joblib [Xu2023]
    2. IF classique depuis data/models/{branch}/production/if_classic_model.joblib

    Pour l'Explainer :
    - DIF → KernelSHAP avec background set [Lundberg2017] si disponible,
      sinon explainer=None (dégradation gracieuse [Sculley2015]).
    - IF → TreeExplainer [Lundberg2020].

    Raises:
        RuntimeError: si aucun modèle n'est disponible pour la branche.
    """
    # 1. Charger le module via PluginRegistry (ADR-002 — jamais d'import direct)
    try:
        if branch not in PluginRegistry._registry:
            if branch == "sante":
                import modules.sante.sante_module  # noqa: F401
            elif branch == "auto":
                import modules.auto.auto_module    # noqa: F401

        yaml_path = Path("modules") / branch / f"{branch}.yaml"
        module = PluginRegistry.get(branch)(config_path=yaml_path)
    except KeyError:
        raise RuntimeError(f"Module '{branch}' non enregistré dans PluginRegistry.")

    feature_names = module.get_feature_names()

    # 2. Charger la stratégie — DIF en priorité, IF classique en fallback
    dif_path = _DIF_MODEL_PATHS.get(branch)
    if_path  = _IF_FALLBACK_PATHS.get(branch)

    strategy = None
    if dif_path and dif_path.exists():
        # [Xu2023] DIF production — seuil calibré par branche [Davis2006]
        strategy = load_strategy_from_joblib(dif_path, branch=branch)
        logger.info("[%s] Stratégie DIF chargée depuis %s", branch.upper(), dif_path)
    elif if_path and if_path.exists():
        # Fallback IF classique [Liu2008]
        strategy = load_strategy_from_joblib(if_path, branch=branch)
        logger.warning(
            "[%s] DIF absent — fallback IF classique depuis %s",
            branch.upper(), if_path,
        )
    else:
        raise RuntimeError(
            f"Aucun modèle disponible pour la branche '{branch}'. "
            f"Attendu : {dif_path} ou {if_path}."
        )

    threshold = getattr(strategy, "_threshold", 0.5)
    detector = Detector(strategy=strategy, threshold=threshold)


    # ─── 2b. Restriction de features : aligner module vs DIF entraîné ────────
    # Le DIF a été entraîné sur N features (ici 17). Le module en expose M > N
    # (ici 20 — 3 features graphe ajoutées dans v0.5.0 après l'entraînement).
    # On détecte N depuis minmax_scaler.n_features_in_ et on restreint.
    # [Xu2023] — le pipeline doit utiliser exactement les features vues à
    # l'entraînement pour que le minmax_scaler interne soit cohérent.
    # ── APRÈS ────────────────────────────────────────────────────────────────────
    _dif_scaler = getattr(
        getattr(strategy, "_model", None), "minmax_scaler", None
    )
    _expected_n = getattr(_dif_scaler, "n_features_in_", None)
    if _expected_n and _expected_n != len(feature_names):
        _original_n = len(feature_names)
        # Priorité : liste explicite dans dif_production.feature_names (YAML).
        # Garantit que l'ordre des features est contractuel et non dépendant
        # du slice [:N] — robuste aux futures modifications du YAML [Sculley2015].
        _yaml_dif_features = module.config.get("dif_production", {}).get("feature_names")
        if _yaml_dif_features and len(_yaml_dif_features) == _expected_n:
            feature_names = list(_yaml_dif_features)
            logger.info(
                "[%s] Features DIF lues depuis dif_production.yaml (%d features) [Sculley2015].",
                branch.upper(), len(feature_names),
            )
        else:
            # Fallback : slice [:N] (ancien comportement conservé)
            feature_names = feature_names[:_expected_n]
            logger.warning(
                "[%s] Feature mismatch : module=%d, DIF=%d → restriction "
                "aux %d premières [Xu2023]. "
                "Ajouter dif_production.feature_names dans le YAML pour fixer l'ordre.",
                branch.upper(), _original_n, _expected_n, _expected_n,
            )
    # ─────────────────────────────────────────────────────────────────────────
    module.get_feature_names = lambda fn=feature_names: list(fn)


    # 3. Construire l'Explainer selon le mode de la stratégie
    explainer: Optional[Explainer] = None
    try:
        exp = Explainer(strategy=strategy, feature_names=feature_names)
        if strategy.supports_shap():
            # TreeExplainer (IF) — pas de background requis [Lundberg2020]
            exp.initialize()
            explainer = exp
            logger.info("[%s] TreeExplainer initialisé.", branch.upper())
        else:
            # KernelSHAP (DIF) — background requis [Lundberg2017]
            bg_path = _BACKGROUND_PATHS.get(branch)
            if bg_path and bg_path.exists():
                X_background = np.load(bg_path)
                exp.initialize(X_background=X_background)
                explainer = exp
                logger.info(
                    "[%s] KernelExplainer initialisé (background n=%d) [Lundberg2017].",
                    branch.upper(), len(X_background),
                )
            else:
                # Dégradation gracieuse — SHAP désactivé [Sculley2015]
                logger.warning(
                    "[%s] Background SHAP absent (%s) — explicabilité désactivée.",
                    branch.upper(), bg_path,
                )
    except Exception as exc:
        logger.warning("[%s] Erreur init Explainer (non-bloquant) : %s", branch.upper(), exc)
        explainer = None

# 3b. Construire le RCAEngine — STATELESS [GoF1994 Chain of Responsibility]
    # Le RCAEngine reçoit les règles à chaque appel via module.get_rca_rules().
    # Initialisation défensive : si le module n'expose aucune règle, on log
    # mais on instancie quand même — Pipeline gère le cas (rca_engine présent
    # mais rules=[] → RCAResult.indeterminate()) [Sculley2015].
    rca_engine: Optional[RCAEngine] = None
    try:
        rules = module.get_rca_rules()
        if rules:
            rca_engine = RCAEngine()
            logger.info(
                "[%s] RCAEngine initialisé (%d règles chargées) [GoF1994].",
                branch.upper(), len(rules),
            )
        else:
            logger.warning(
                "[%s] Aucune règle RCA exposée par le module — rca_engine=None.",
                branch.upper(),
            )
    except Exception as exc:
        logger.warning(
            "[%s] Erreur init RCAEngine (non-bloquant) : %s",
            branch.upper(), exc,
        )
        rca_engine = None

    # 3c. Construire le LLMNarrator avec DeepSeek [Jiang2023, Wei2022]
    # Dégradation gracieuse [Sculley2015] : si DEEPSEEK_API_KEY absente,
    # llm_narrator=None et le pipeline tourne sans narration (RCA + SHAP OK).
    llm_narrator: Optional[LLMNarrator] = None
    try:
        deepseek_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
        if deepseek_key:
            deepseek_backend = DeepSeekBackend(api_key=deepseek_key)
            llm_narrator = LLMNarrator(backend=deepseek_backend)
            logger.info(
                "[%s] LLMNarrator initialisé avec backend DeepSeek [Jiang2023].",
                branch.upper(),
            )
        else:
            logger.warning(
                "[%s] DEEPSEEK_API_KEY absente — narration LLM désactivée "
                "(dégradation gracieuse) [Sculley2015].",
                branch.upper(),
            )
    except Exception as exc:
        logger.warning(
            "[%s] Erreur init LLMNarrator (non-bloquant) : %s",
            branch.upper(), exc,
        )
        llm_narrator = None

    # 4. Assembler le Pipeline
    pipeline = Pipeline(
        module=module,
        detector=detector,
        explainer=explainer,
        rca_engine=rca_engine,
        llm_narrator=llm_narrator,
        shap_top_k=3,
    )
    logger.info(
        "[%s] Pipeline prêt : detector=%s, shap=%s, rca=%s, llm=%s",
        branch.upper(),
        detector.get_name(),
        explainer is not None,
        rca_engine is not None,
        llm_narrator is not None,
    )
    return pipeline


def _get_pipeline(branch: str) -> Pipeline:
    """
    Retourne le Pipeline mis en cache, ou le construit si absent.
    [Sculley2015] : les modèles DIF font 300+ Mo — ne pas recharger à chaque requête.
    """
    if branch not in _PIPELINE_CACHE:
        _PIPELINE_CACHE[branch] = _build_pipeline(branch)
    return _PIPELINE_CACHE[branch]


# ---------------------------------------------------------------------------
# run_analysis — point d'entrée public
# ---------------------------------------------------------------------------

def run_analysis(
    db: Session,
    branch: str,
    source: str,
    dossiers: list[dict],
    triggered_by=None,
) -> AnalyzeBatchResponse:
    """
    Lance le pipeline MAKORA complet (DIF + SHAP + RCA) sur un batch de dossiers.

    Respecte l'isolation Kernel (ADR-002) : le module métier est chargé
    exclusivement via PluginRegistry — jamais par nom concret.
    La stratégie de détection est auto-détectée via load_strategy_from_joblib
    (DIF en priorité, IF classique en fallback) [Xu2023].
    """
    from core.db.models.referentiels import Branch

    db_branch = db.query(Branch).filter(
        Branch.code == branch, Branch.is_active == True
    ).first()
    if not db_branch:
        raise HTTPException(status_code=400, detail=f"Branche '{branch}' inconnue ou inactive")

    run_id    = uuid.uuid4()
    started_at = datetime.now(tz=timezone.utc)

    # Charger (ou récupérer depuis le cache) le pipeline
    try:
        pipeline = _get_pipeline(branch)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("[%s] Pipeline non disponible : %s", branch.upper(), exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail=f"Modèle non disponible pour '{branch}'. Cause : {type(exc).__name__}: {exc}",
        )

    # Construire le DataFrame du batch
    df_batch = pd.DataFrame(dossiers)

    # Exécuter le pipeline sur tout le batch
    t0 = time.monotonic()
    try:
        makora_outputs = pipeline.run(df_batch, source_key=source)
    except Exception as exc:
        logger.error("[%s] Erreur pipeline : %s", branch.upper(), exc)
        raise HTTPException(status_code=500, detail=f"Erreur pipeline : {exc}")

    total_ms = (time.monotonic() - t0) * 1000

    # Sérialiser les MAKORAOutput → AnalysisResult (schéma API)
    results: list[AnalysisResult] = []
    anomaly_count = 0
    per_record_ms = round(total_ms / max(len(makora_outputs), 1), 1)

    for out in makora_outputs:
        if out.is_anomaly:
            anomaly_count += 1

        # Conversion SHAP
        shap_features = [
            ShapFeature(
                feature_name=f.name,
                shap_value=f.shap_value,
                direction=f.direction,
                rank=f.rank,
            )
            for f in out.shap_top_k
        ] if out.shap_top_k else []

        # Conversion RCA
        rca = None
        if out.rca_result:
            rca = RcaResult(
                category=out.rca_result.category,
                subcategory=out.rca_result.subcategory,
                confidence=out.rca_result.confidence,
                explanation_fr=out.rca_result.explanation_fr,
                rules_triggered=out.rca_result.rules_triggered,
            )

        results.append(AnalysisResult(
            claim_id=out.dossier_id,
            branch=branch,
            anomaly_score=round(float(out.anomaly_score), 6),
            is_anomaly=out.is_anomaly,
            processing_time_ms=per_record_ms,
            shap_features=shap_features,
            rca=rca,
            decision_status="PENDING",
            detector_name=out.detector_name,
        ))

    completed_at = datetime.now(tz=timezone.utc)
    batch_id = f"BATCH_{completed_at.strftime('%Y%m%d_%H%M%S')}_{branch.upper()}"

    logger.info(
        "[%s] Batch terminé : %d dossiers, %d anomalies, %.0f ms total",
        branch.upper(), len(dossiers), anomaly_count, total_ms,
    )

    return AnalyzeBatchResponse(
        batch_id=batch_id,
        run_id=run_id,
        branch=branch,
        processed=len(dossiers),
        anomalies_detected=anomaly_count,
        results=results,
        started_at=started_at,
        completed_at=completed_at,
    )


# ---------------------------------------------------------------------------
# get_run / list_runs — inchangés
# ---------------------------------------------------------------------------

def get_run(db: Session, run_id):
    from core.db.models.pipeline import AnalysisRun
    run = db.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run introuvable")
    return run


def list_runs(db, branch, offset, limit):
    from core.db.models.pipeline import AnalysisRun
    from core.db.models.referentiels import Branch as BranchModel
 
    # JOIN Branch pour obtenir branch_code directement
    q = (
        db.query(AnalysisRun, BranchModel.code.label("branch_code"))
        .outerjoin(BranchModel, AnalysisRun.branch_id == BranchModel.id)
    )
 
    if branch:
        q = q.filter(BranchModel.code == branch)
 
    total = q.count()
    rows = (
        q.order_by(AnalysisRun.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
 
    # Construire des dicts compatibles RunStatusResponse (from_attributes=True
    # ne fonctionne pas sur les tuples — on sérialise manuellement)
    results = []
    for run, branch_code in rows:
        results.append({
            "id":            run.id,
            "branch_id":     run.branch_id,
            "branch_code":   branch_code,
            "run_type":      run.run_type,
            "nb_dossiers":   run.nb_dossiers,
            "nb_anomalies":  run.nb_anomalies,
            "graph_enabled": run.graph_enabled,
            "started_at":    run.started_at,
            "completed_at":  run.completed_at,
        })
 
    return total, results

def _get_latest_ocr_for_claim(db: Session, claim) -> "OcrExtraction | None":
    """
    Sprint 5 — Retourne le dernier OcrExtraction avec success=True pour
    n'importe quel document du claim, ou None.

    Référence : [Bauder2017] — qualité documentaire comme signal de fraude.
    """
    from core.db.models.sinistres import OcrExtraction
    doc_ids = [d.id for d in claim.documents]
    if not doc_ids:
        return None
    return (
        db.query(OcrExtraction)
        .filter(
            OcrExtraction.document_id.in_(doc_ids),
            OcrExtraction.success == True,  # noqa: E712 — comparaison SQLAlchemy
        )
        .order_by(OcrExtraction.created_at.desc())
        .first()
    )

def run_pipeline_for_claim(
    claim_uuid,
    branch_code: str,
    dossier: dict,
    triggered_by_id=None,
) -> None:
    """
    Background task — exécute le pipeline DIF + KernelSHAP + RCA + LLM
    sur un claim soumis et persiste les résultats.

    RÉFÉRENCE : [Xu2023] DIF — pipeline de production MAKORA.

    DÉCISIONS DE CONCEPTION (B-AI-NEW-01) :
    - Ouvre sa propre session DB via SessionLocal() — la session HTTP du request
      est déjà fermée quand le background task s'exécute (FastAPI lifecycle).
    - Ne lève JAMAIS d'exception : toutes les erreurs sont logguées. Le claim
      reste en statut SUBMITTED si quoi que ce soit échoue (Décision 1 :
      signal d'alerte pour l'admin via le stepper frontend).
    - ModelVersion résolu en fallback "plus récent pour la branche" même sans
      ProductionDeployment formel (Décision 2 — dev/démo). À durcir post-soutenance.
    - Aucune écriture sur Claim.latest_* (colonnes inexistantes) : l'enrichissement
      se fait dans get_claim() via jointure (Décision 3).

    Args:
        claim_uuid: UUID interne du claim (Claim.id), PAS le claim_id métier
        branch_code: 'sante' ou 'auto'
        dossier: dict pré-construit par claim_to_dossier_dict()
        triggered_by_id: User.id qui a déclenché la soumission (optionnel)
    """
    # Imports locaux pour éviter les cycles à l'import du module
    from core.db.base import SessionLocal
    from core.db.models.sinistres import Claim
    from core.db.models.pipeline import (
        AnalysisRun, Analysis, ShapContribution, ModelVersion,
    )
    from core.db.models.referentiels import Branch

    db: Session = SessionLocal()
    try:
        # ─── 1. Recharger le claim (vérifier qu'il existe et est SUBMITTED) ─
        claim = db.query(Claim).filter(Claim.id == claim_uuid).first()
        if not claim:
            logger.error(
                "[%s] Pipeline background : claim UUID %s introuvable",
                branch_code.upper(), claim_uuid,
            )
            return

        if claim.statut != "SUBMITTED":
            logger.warning(
                "[%s] Pipeline background : claim %s en statut '%s' "
                "(attendu SUBMITTED) — skip",
                branch_code.upper(), claim.claim_id, claim.statut,
            )
            return

        # ─── 2. Résoudre la branche en DB ────────────────────────────────────
        db_branch = db.query(Branch).filter(
            Branch.code == branch_code, Branch.is_active == True
        ).first()
        if not db_branch:
            logger.error(
                "[%s] Branche inconnue ou inactive — claim %s reste SUBMITTED",
                branch_code.upper(), claim.claim_id,
            )
            return

        # ─── 3. Résoudre le ModelVersion (Décision 2 : plus récent) ──────────
        model_version = (
            db.query(ModelVersion)
            .filter(ModelVersion.branch_id == db_branch.id)
            .order_by(ModelVersion.trained_at.desc())
            .first()
        )
        if not model_version:
            logger.error(
                "[%s] Aucun ModelVersion trouvé pour la branche — "
                "claim %s reste SUBMITTED (Décision 1)",
                branch_code.upper(), claim.claim_id,
            )
            return

        # ─── 4. Charger le pipeline (cache) ──────────────────────────────────
        try:
            pipeline = _get_pipeline(branch_code)
        except Exception as exc:
            logger.error(
                "[%s] Pipeline non disponible (%s) — "
                "claim %s reste SUBMITTED (Décision 1)",
                branch_code.upper(), exc, claim.claim_id, exc_info=True,
            )
            return

        # ─── 5. Créer l'AnalysisRun (en cours) ───────────────────────────────
        started_at = datetime.now(tz=timezone.utc)
        analysis_run = AnalysisRun(
            branch_id=db_branch.id,
            model_version_id=model_version.id,
            run_type="single",
            nb_dossiers=1,
            nb_anomalies=0,
            graph_enabled=False,
            started_at=started_at,
            triggered_by=triggered_by_id,
        )
        db.add(analysis_run)
        db.flush()


        # ─── 5b. Enrichir le dossier avec les features OCR (Sprint 5) ────────
        # [Bauder2017] — qualité documentaire comme signal de fraude
        ocr = _get_latest_ocr_for_claim(db, claim)
        if ocr:
            dossier["document_altere"] = ocr.flag_altere
            dossier["ocr_confiance_faible"] = ocr.score_confiance_global < 0.60
            logger.info(
                "[%s] OCR features injectées : altere=%s, confiance_faible=%s (score=%.2f)",
                branch_code.upper(),
                dossier["document_altere"],
                dossier["ocr_confiance_faible"],
                ocr.score_confiance_global,
            )
            

        # ─── 6. Exécuter le pipeline sur un DataFrame mono-ligne ─────────────
        try:
            df_batch = pd.DataFrame([dossier])
            t0 = time.monotonic()
            outputs = pipeline.run(
                df_batch,
                source_key=dossier.get("Source_Flux", "submit_claim"),
            )
            processing_ms = (time.monotonic() - t0) * 1000
        except Exception as exc:
            logger.error(
                "[%s] Erreur exécution pipeline pour claim %s : %s",
                branch_code.upper(), claim.claim_id, exc, exc_info=True,
            )
            # On clôt le run comme "tenté mais en erreur"
            analysis_run.completed_at = datetime.now(tz=timezone.utc)
            db.commit()
            return

        if not outputs:
            logger.error(
                "[%s] Pipeline a retourné un batch vide pour claim %s",
                branch_code.upper(), claim.claim_id,
            )
            analysis_run.completed_at = datetime.now(tz=timezone.utc)
            db.commit()
            return

        out = outputs[0]

        # ─── 7. Persister l'Analysis ─────────────────────────────────────────
        # Clip défensif pour respecter la CHECK constraint anomaly_score ∈ [0,1]
        # (raw DIF score typique ~0.35 mais on protège contre overflow extrêmes)
        score_raw = float(out.anomaly_score)
        score_clipped = min(1.0, max(0.0, score_raw))
        if abs(score_raw - score_clipped) > 1e-6:
            logger.warning(
                "[%s] Score DIF brut hors [0,1] : %.6f → clippé à %.6f "
                "(CHECK constraint analyses.anomaly_score)",
                branch_code.upper(), score_raw, score_clipped,
            )

        rca = out.rca_result
        analysis = Analysis(
            claim_id=claim.id,
            run_id=analysis_run.id,
            branch_id=db_branch.id,
            model_version_id=model_version.id,
            anomaly_score=score_clipped,
            is_anomaly=bool(out.is_anomaly),
            detector_name=getattr(out, "detector_name", None) or "dif",
            rca_category=(rca.category if rca else None),
            rca_subcategory=(rca.subcategory if rca else None),
            rca_confidence=(rca.confidence if rca else None),
            rca_rule_id=(
                getattr(rca, "rule_id", None)
                if rca else None
            ),
            explanation_fr=out.explanation_fr,
            decision_status="PENDING",
            processing_time_ms=round(processing_ms, 1),
        )
        db.add(analysis)
        db.flush()

        # ─── 8. Persister les ShapContribution (top-K) ───────────────────────
        if out.shap_top_k:
            for feat in out.shap_top_k:
                feat_value = getattr(feat, "feature_value", None)
                db.add(ShapContribution(
                    analysis_id=analysis.id,
                    feature_name=feat.name,
                    shap_value=float(feat.shap_value),
                    feature_value=(
                        float(feat_value) if feat_value is not None else None
                    ),
                    direction=feat.direction,
                    rank=feat.rank,
                ))

        # ─── 9. Finaliser l'AnalysisRun ──────────────────────────────────────
        analysis_run.completed_at = datetime.now(tz=timezone.utc)
        analysis_run.nb_anomalies = 1 if out.is_anomaly else 0

        # ─── 10. Passer le claim en OPEN ─────────────────────────────────────
        claim.statut = "OPEN"

        db.commit()

        logger.info(
            "[%s] Pipeline OK pour claim %s : "
            "score=%.4f anomaly=%s rca=%s temps=%.1fms",
            branch_code.upper(),
            claim.claim_id,
            score_clipped,
            out.is_anomaly,
            (rca.category if rca else "—"),
            processing_ms,
        )

    except Exception as exc:
        # Filet de sécurité : un background task ne doit JAMAIS lever
        logger.error(
            "[%s] Erreur fatale non capturée dans run_pipeline_for_claim : %s",
            branch_code.upper(), exc, exc_info=True,
        )
        try:
            db.rollback()
        except Exception:
            pass
    finally:
        db.close()