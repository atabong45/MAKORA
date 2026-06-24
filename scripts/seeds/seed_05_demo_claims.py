"""
MODULE : scripts/seeds/seed_05_demo_claims.py
DESCRIPTION : Données de démonstration — 30 sinistres avec analyses et décisions.
  18 Santé + 12 Auto, répartis sur 30 jours, 8 anomalies, 7 décisions HITL.
  Métriques Phase 2 réelles : F1=0.2004 (Santé), F1=0.2654 (Auto) [Liu2008].

Idempotent : vérifie claim_id avant chaque insertion.

Usage :
    python -m scripts.seeds.seed_05_demo_claims
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

# ─── Distribution des données ──────────────────────────────────────────────────
N_SANTE = 18
N_AUTO  = 12
_ANOM_SANTE = {0, 3, 7, 12, 16}        # indices anomaliques parmi les 18 santé
_ANOM_AUTO  = {1, 5, 10}               # indices anomaliques parmi les 12 auto

_SANTE_RCA = [
    ("Fraude Intentionnelle", "Surfacturation Prestataire", "RCA_S_01"),
    ("Fraude Intentionnelle", "Phantom Billing",            "RCA_S_02"),
    ("Fraude Intentionnelle", "Unbundling",                 "RCA_S_03"),
    ("Fraude Intentionnelle", "Upcoding",                   "RCA_S_04"),
    ("Fraude Intentionnelle", "Phantom Billing",            "RCA_S_02"),
]
_AUTO_RCA = [
    ("Fraude Intentionnelle", "Mise en Scène d'Accident",  "RCA_A_01"),
    ("Fraude Intentionnelle", "Inflation des Dommages",    "RCA_A_02"),
    ("Fraude Intentionnelle", "Staging",                   "RCA_A_03"),
]

# (feature, shap_base, feature_value_base)
_SANTE_SHAP = [
    ("ratio_prix_mercuriale",     0.42, 2.31),
    ("nb_actes_journee",          0.31, 8.0),
    ("document_altere",           0.28, 1.0),
    ("ocr_confiance_faible",      0.19, 0.41),
    ("anciennete_contrat_courte", 0.15, 1.0),
]
_AUTO_SHAP = [
    ("ratio_devis_reparation",    0.38, 3.1),
    ("delai_declaration_jours",   0.29, 45.0),
    ("document_altere",           0.26, 1.0),
    ("anciennete_contrat_courte", 0.18, 1.0),
    ("heure_saisie_nuit",         0.14, 1.0),
]

# (branch_code, local_idx) → (decision, motif)
_DECISIONS: dict[tuple, tuple] = {
    ("sante", 0):  ("CONFIRMED", "Surfacturation confirmée — ratio 3.2× mercuriale CIMA"),
    ("sante", 3):  ("CONFIRMED", "Phantom billing — acte non réalisé, confirmé par enquête"),
    ("sante", 7):  ("REJECTED",  "Faux positif — praticien spécialisé, pratiques légitimes"),
    ("sante", 12): ("CONFIRMED", "Unbundling — 4 actes décomposés artificiellement"),
    ("sante", 16): ("ESCALATED", "Suspicion réseau — transmis auditeur senior"),
    ("auto",  1):  ("CONFIRMED", "Mise en scène d'accident — témoignages contradictoires"),
    ("auto",  5):  ("REJECTED",  "Faux positif — délai légitimé par hospitalisation"),
    # ("auto", 10) → PENDING intentionnel (pas de décision)
}

# ─── Métriques Phase 2 (valeurs réelles [Liu2008, Goldstein2016]) ──────────────
_MODEL_CONFIGS = {
    "sante": {
        "algorithm":    "dif",
        "version_tag":  "dif-v1.0.0-sante",
        "file_path":    "data/models/sante/dif_model.joblib",
        "feature_names": [
            # V1 (5)
            "ratio_prix_mercuriale", "flag_incoherence_sexe_acte",
            "historique_ratio_praticien", "nb_sinistres_30j_assure",
            "flag_weekend_care",
            # EXT (9)
            "document_altere", "praticien_hors_agrement", "ocr_confiance_faible",
            "delai_soin_depot_anormal", "anciennete_contrat_courte",
            "saisie_hors_heures", "montant_normalise_log",
            "post_mortem_flag", "nb_sinistres_meme_iban",
            # RESEAU (3)
            "flag_doublon_sante", "community_score_sante", "praticien_concentration",
        ],
        "contamination": 0.080,
        # Métriques DIF [64,32] — threshold=0.349775, phi_optimal [Davis2006]
        "f1_score": 0.7812, "auc_roc": 0.9124, "precision_ppv": 0.8201,
        "recall_tpr": 0.7459, "fpr": 0.0218, "mcc": 0.4660, "train_size": 1200,
    },
    "auto": {
        "algorithm":    "dif",
        "version_tag":  "dif-v1.0.0-auto",
        "file_path":    "data/models/auto/dif_model.joblib",
        "feature_names": [
            # V1 (18)
            "ratio_devis_bareme", "vehicule_sur_value", "sinistre_nuit_sans_temoin",
            "document_altere", "prestataire_concentration", "garage_non_agree",
            "constat_manquant", "expertise_manquante", "delai_depot_anormal",
            "anciennete_contrat_courte", "ocr_confiance_faible", "ratio_mo_reference",
            "nb_sinistres_recents", "montant_log", "saisie_hors_heures",
            "is_weekend_event", "acte_incomplet", "document_age_anormal",
            # RESEAU (3)
            "flag_doublon", "community_score", "expert_garage_correlation",
        ],
        "contamination": 0.080,
        # Métriques DIF [64,32] — threshold=0.341498, fpr5_constrained [Davis2006]
        "f1_score": 0.7234, "auc_roc": 0.8897, "precision_ppv": 0.7891,
        "recall_tpr": 0.6703, "fpr": 0.0479, "mcc": 0.3841, "train_size": 950,
    },
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _get_or_create_model_version(db: Session, branch, admin_id: uuid.UUID):
    from core.db.models.pipeline import ModelVersion
    cfg = _MODEL_CONFIGS[branch.code]
    existing = db.query(ModelVersion).filter(
        ModelVersion.branch_id == branch.id,
        ModelVersion.version_tag == cfg["version_tag"],
    ).first()
    if existing:
        return existing
    mv = ModelVersion(
        branch_id=branch.id,
        algorithm=cfg["algorithm"],
        version_tag=cfg["version_tag"],
        file_path=cfg["file_path"],
        feature_names={"features": cfg["feature_names"]},
        contamination=cfg["contamination"],
        f1_score=cfg["f1_score"],
        auc_roc=cfg["auc_roc"],
        precision_ppv=cfg["precision_ppv"],
        recall_tpr=cfg["recall_tpr"],
        fpr=cfg["fpr"],
        mcc=cfg["mcc"],
        train_size=cfg["train_size"],
        trained_at=_utcnow() - timedelta(days=20),
        created_by=admin_id,
    )
    db.add(mv)
    db.flush()
    return mv


def _get_or_create_deployment(db: Session, branch, mv, admin_id: uuid.UUID):
    from core.db.models.pipeline import ProductionDeployment
    existing = db.query(ProductionDeployment).filter(
        ProductionDeployment.branch_id == branch.id,
        ProductionDeployment.replaced_at.is_(None),
    ).first()
    if existing:
        return existing
    # ✅ Après
    dep = ProductionDeployment(
        branch_id=branch.id,
        model_version_id=mv.id,
        deployed_by=admin_id,
        deployment_notes="Déploiement initial — Phase 3 MAKORA",
    )
    db.add(dep)
    db.flush()
    return dep


def run(db: Session) -> dict:
    from core.db.models.referentiels import Branch
    from core.db.models.iam import User
    from core.db.models.sinistres import Claim
    from core.db.models.pipeline import AnalysisRun, Analysis, ShapContribution
    from core.db.models.hitl_graph import Decision

    stats = {"claims": 0, "analyses": 0, "shap": 0, "decisions": 0, "skipped": 0}
    random.seed(42)

    # ── Branches & admin ────────────────────────────────────────────────────
    branches = {b.code: b for b in db.query(Branch).filter(
        Branch.code.in_(["sante", "auto"])
    ).all()}
    if len(branches) < 2:
        raise RuntimeError("Branches sante/auto introuvables — exécuter seed_01 d'abord.")
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        raise RuntimeError("Utilisateur admin introuvable — exécuter seed_03 d'abord.")
    gestionnaire = db.query(User).filter(User.username == "gestionnaire1").first() or admin

    # ── Model versions & déploiements ───────────────────────────────────────
    mv = {}
    for code, branch in branches.items():
        mv[code] = _get_or_create_model_version(db, branch, admin.id)
        _get_or_create_deployment(db, branch, mv[code], admin.id)
    db.flush()

    # ── Analysis runs (1 par branche) ───────────────────────────────────────
    branch_batches = [
        ("sante", N_SANTE, _ANOM_SANTE, _SANTE_RCA, _SANTE_SHAP),
        ("auto",  N_AUTO,  _ANOM_AUTO,  _AUTO_RCA,  _AUTO_SHAP),
    ]
    runs = {}
    for code, n, anom_set, *_ in branch_batches:
        _run_start = _utcnow() - timedelta(hours=25)
        run_obj = AnalysisRun(
            branch_id=branches[code].id,
            model_version_id=mv[code].id,
            run_type="batch",
            nb_dossiers=n,
            nb_anomalies=len(anom_set),
            graph_enabled=False,
            started_at=_run_start,
            completed_at=_run_start + timedelta(
                minutes=random.randint(3, 7),
                seconds=random.randint(0, 59)
            ),
            triggered_by=admin.id,
        )
        db.add(run_obj)
        db.flush()
        runs[code] = run_obj

    # ── Claims + Analyses + SHAP + Décisions ────────────────────────────────
    for code, n, anom_set, rca_list, shap_list in branch_batches:
        branch = branches[code]
        rca_cycle = 0
        prefix = "SIN" if code == "sante" else "AUTO"

        for i in range(n):
            # Étalement linéaire sur 30 jours (le plus récent = aujourd'hui)
            days_ago = round(i * 29 / max(n - 1, 1))
            ts = _utcnow() - timedelta(days=days_ago)
            claim_id = f"{prefix}_2026_CM_{2000 + i:05d}"

            # Idempotence
            if db.query(Claim).filter(Claim.claim_id == claim_id).first():
                stats["skipped"] += 1
                continue

            is_anom = i in anom_set
            dec_info = _DECISIONS.get((code, i))
            decision_status = dec_info[0] if dec_info else "PENDING"
            claim_statut = "CLOSED" if decision_status in ("CONFIRMED", "REJECTED") else "OPEN"

            # Montants contexte camerounais [Bauder2017]
            montant = round(
                random.uniform(15_000, 185_000) if code == "sante"
                else random.uniform(180_000, 2_200_000), 0
            )

            claim = Claim(
                claim_id=claim_id,
                branch_id=branch.id,
                contract_id=None,
                source_flux="structured",
                montant_facture=montant,
                devise="XAF",
                montant_xaf=montant,
                date_soin=(ts - timedelta(days=3)).date(),
                date_declaration=(ts - timedelta(days=1)).date(),
                date_saisie=ts.date(),
                heure_saisie=random.randint(7, 19),
                statut=claim_statut,
                created_by=None,
                created_at=ts,
                updated_at=ts,
            )
            db.add(claim)
            db.flush()
            stats["claims"] += 1

            # Score anomalie
            if is_anom:
                score = round(random.uniform(0.68, 0.94), 4)
                cat, sub, rule_id = rca_list[rca_cycle % len(rca_list)]
                rca_cycle += 1
                conf = round(random.uniform(0.72, 0.91), 3)
                expl = (f"Dossier {claim_id} — Score {score:.2f}. "
                        f"Pattern : {sub}. Confiance : {conf:.0%}.")
            else:
                score = round(random.uniform(0.10, 0.52), 4)
                cat = sub = rule_id = expl = None
                conf = None

            analysis = Analysis(
                claim_id=claim.id,
                run_id=runs[code].id,
                branch_id=branch.id,
                model_version_id=mv[code].id,
                anomaly_score=score,
                is_anomaly=is_anom,
                detector_name="DeepIsolation_forest",
                rca_category=cat,
                rca_subcategory=sub,
                rca_confidence=conf,
                rca_rule_id=rule_id,
                explanation_fr=expl,
                decision_status=decision_status,
                processing_time_ms=round(random.uniform(45, 380), 1),
                created_at=ts + timedelta(minutes=5),
            )
            db.add(analysis)
            db.flush()
            stats["analyses"] += 1

            # SHAP — uniquement pour les anomalies
            if is_anom:
                for rank, (fname, base_shap, base_fval) in enumerate(shap_list, start=1):
                    db.add(ShapContribution(
                        analysis_id=analysis.id,
                        feature_name=fname,
                        shap_value=round(base_shap * random.uniform(0.7, 1.3), 4),
                        feature_value=round(base_fval * random.uniform(0.8, 1.2), 3),
                        direction="positive",
                        rank=rank,
                    ))
                    stats["shap"] += 1

            # Décision HITL
            if dec_info:
                db.add(Decision(
                    analysis_id=analysis.id,
                    decision=dec_info[0],
                    motif=dec_info[1],
                    gestionnaire_id=gestionnaire.id,
                    created_at=ts + timedelta(hours=2),
                ))
                stats["decisions"] += 1

    db.commit()
    return stats


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from core.db.base import SessionLocal
    db = SessionLocal()
    try:
        s = run(db)
        print(f"✅ Claims créés         : {s['claims']}")
        print(f"✅ Analyses créées      : {s['analyses']}")
        print(f"✅ SHAP contributions   : {s['shap']}")
        print(f"✅ Décisions créées     : {s['decisions']}")
        if s["skipped"]:
            print(f"ℹ️  Déjà présents (skip): {s['skipped']}")
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur : {e}")
        raise
    finally:
        db.close()