"""
MODULE : scripts/seeds/seed_06_demo_claims_v2.py
DESCRIPTION : Seed enrichi v2 — 50 sinistres supplémentaires + entités liées.
  Complète seed_05 (qui DOIT avoir tourné avant).

  Crée :
   - 20 praticiens hashés (10 régions Cameroun × 10 spécialités)
   - 5 garages hashés (4 villes)
   - 50 nouveaux sinistres (30 santé + 20 auto)
   - 5 catégories RCA distinctes pour diversifier Top 5 Patterns
   - SHAP variés (positifs ET négatifs) pour Top SHAP discriminant
   - Claim lines (actes ASAC santé / postes auto)
   - 2 drift reports (STABLE santé psi=0.08, WARNING auto psi=0.14)

Idempotent : skip si claim_id existe déjà.

Usage :
    docker exec makora_api python -m scripts.seeds.seed_06_demo_claims_v2
"""
from __future__ import annotations

import hashlib
import random
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

# ─── Distribution ──────────────────────────────────────────────────────────────
N_SANTE_V2 = 30
N_AUTO_V2  = 20
_ANOM_SANTE_IDX = {0, 4, 8, 12, 15, 18, 22, 25, 28}   # 9 anomalies santé
_ANOM_AUTO_IDX  = {1, 4, 9, 13, 16, 19}                # 6 anomalies auto

# 10 régions du Cameroun (ordre administratif officiel)
REGIONS_CM = [
    "Adamaoua", "Centre", "Est", "Extrême-Nord", "Littoral",
    "Nord", "Nord-Ouest", "Ouest", "Sud", "Sud-Ouest",
]

# 10 spécialités médicales fréquentes
SPECIALITES = [
    "Cardiologie", "Généraliste", "Dentaire", "Ophtalmologie", "Pédiatrie",
    "Gynécologie", "Chirurgie", "Radiologie", "Laboratoire", "Pharmacie",
]

# 5 catégories RCA distinctes — résoud le bug "100% Fraude Intentionnelle"
_SANTE_RCA = [
    ("Fraude Intentionnelle", "Surfacturation Prestataire", "RCA_S_01"),
    ("Fraude Intentionnelle", "Phantom Billing",            "RCA_S_02"),
    ("Erreur Administrative",  "Doublon de facturation",    "RCA_S_05"),
    ("Anomalie Documentaire",  "Document falsifié",         "RCA_S_06"),
    ("Pattern Réseau",         "Coordination praticien-assuré", "RCA_S_07"),
    ("Comportement Suspect",   "Sinistralité anormale",     "RCA_S_08"),
    ("Fraude Intentionnelle", "Unbundling",                 "RCA_S_03"),
    ("Anomalie Documentaire",  "Cachet manquant",           "RCA_S_09"),
    ("Erreur Administrative",  "Acte hors nomenclature",    "RCA_S_10"),
]
_AUTO_RCA = [
    ("Fraude Intentionnelle", "Mise en Scène d'Accident",  "RCA_A_01"),
    ("Fraude Intentionnelle", "Inflation des Dommages",    "RCA_A_02"),
    ("Anomalie Documentaire",  "Devis incohérent",         "RCA_A_05"),
    ("Pattern Réseau",         "Réseau garage-assuré",     "RCA_A_06"),
    ("Comportement Suspect",   "Fréquence anormale",       "RCA_A_07"),
    ("Erreur Administrative",  "Double déclaration",       "RCA_A_08"),
]

# Codes actes santé (ASAC) — codes réalistes
ACTES_SANTE = [
    ("CONS_GEN",    "Consultation médecine générale",  15_000),
    ("CONS_SPE",    "Consultation spécialiste",        25_000),
    ("RAD_THX",     "Radiographie thoracique",         18_000),
    ("ECHO_ABD",    "Échographie abdominale",          35_000),
    ("BILAN_LAB",   "Bilan biologique standard",       22_000),
    ("ECG",         "Électrocardiogramme",             12_000),
    ("DENT_SOIN",   "Soin dentaire simple",            15_000),
    ("MED_GEN",     "Médicaments génériques",           8_500),
    ("OPHT_FOND",   "Fond d'œil",                      18_000),
    ("CHIR_AMB",    "Chirurgie ambulatoire mineure",   85_000),
]

# Postes auto (nomenclature CIMA)
POSTES_AUTO = [
    ("PARE_BRISE",  "Remplacement pare-brise",        180_000),
    ("CARROSSERIE", "Réparation carrosserie",         420_000),
    ("PEINTURE",    "Peinture complète portière",     150_000),
    ("MECA_MOT",    "Réparation moteur",              850_000),
    ("OPTIQUE",     "Remplacement optique avant",     120_000),
    ("PNEU",        "Remplacement pneus (jeu)",       240_000),
    ("EXPERT",      "Frais d'expertise",               45_000),
]

# Garages (4 villes principales)
GARAGES_DATA = [
    ("Douala",   "agréé"),
    ("Yaoundé",  "agréé"),
    ("Bafoussam","indépendant"),
    ("Garoua",   "agréé"),
    ("Douala",   "indépendant"),
]

# Décisions à appliquer (10 décisions sur 50 claims, indices globaux)
# (branch_code, local_idx) → (decision, motif)
_DECISIONS_V2 = {
    ("sante", 0):  ("CONFIRMED", "Surfacturation 4.1× mercuriale CIMA confirmée"),
    ("sante", 4):  ("CONFIRMED", "Phantom billing — patient non vu confirmation enquête"),
    ("sante", 8):  ("REJECTED",  "Faux positif — protocole oncologique justifie cumul"),
    ("sante", 15): ("CONFIRMED", "Document falsifié — signature praticien non conforme"),
    ("sante", 22): ("ESCALATED", "Pattern réseau suspecté — escalade auditeur senior"),
    ("auto",  1):  ("CONFIRMED", "Mise en scène — photos accident incohérentes"),
    ("auto",  4):  ("REJECTED",  "Faux positif — sinistre légitime, expertise corroborée"),
    ("auto",  9):  ("CONFIRMED", "Inflation devis 2.3× tarif référence CIMA"),
    ("auto",  13): ("ESCALATED", "Réseau garage-assuré — investigation BRH"),
    ("auto",  16): ("CONFIRMED", "Double déclaration — sinistre déjà indemnisé"),
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash_id(prefix: str, n: int) -> str:
    """Hash SHA-256 pseudonymisé (64 chars) — conforme architecture MAKORA."""
    raw = f"{prefix}_2026_CM_{n:04d}_makora_seed_salt"
    return hashlib.sha256(raw.encode()).hexdigest()


def _seed_practitioners(db: Session) -> list:
    """Crée 20 praticiens (idempotent), distribués sur 10 régions × 10 spécialités."""
    from core.db.models.referentiels import Practitioner

    practs = []
    for i in range(20):
        id_hash = _hash_id("PRAT", i + 100)
        existing = db.query(Practitioner).filter(Practitioner.id_hash == id_hash).first()
        if existing:
            practs.append(existing)
            continue
        p = Practitioner(
            id_hash=id_hash,
            specialite=SPECIALITES[i % 10],
            region=REGIONS_CM[i % 10],
            pays="CM",
            agrement_cima=random.choice([True, True, True, False]),
            ratio_prix_moyen=round(random.uniform(0.9, 1.8), 2),
            nb_sinistres_total=random.randint(15, 280),
        )
        db.add(p)
        practs.append(p)
    db.flush()
    return practs


def _seed_garages(db: Session) -> list:
    """Crée 5 garages (idempotent), sur 4 villes."""
    from core.db.models.referentiels import Garage

    garages = []
    for i, (ville, type_g) in enumerate(GARAGES_DATA):
        id_hash = _hash_id("GAR", i + 100)
        existing = db.query(Garage).filter(Garage.id_hash == id_hash).first()
        if existing:
            garages.append(existing)
            continue
        g = Garage(
            id_hash=id_hash,
            nom=f"Garage {ville} #{i + 1}",
            type_garage=type_g,
            ville=ville,
            pays="CM",
            agrement_cima=(type_g == "agréé"),
            ratio_devis_moyen=round(random.uniform(1.0, 2.1), 2),
            nb_sinistres_total=random.randint(40, 350),
        )
        db.add(g)
        garages.append(g)
    db.flush()
    return garages


def _seed_drift_reports(db: Session, branches: dict, admin_id: uuid.UUID) -> int:
    """Crée 2 drift reports : STABLE santé, WARNING auto. Idempotent."""
    from core.db.models.monitoring import DriftReport

    created = 0
    # Skip si reports existent déjà
    existing_count = db.query(DriftReport).count()
    if existing_count >= 2:
        return 0

    configs = [
        ("sante", "STABLE",  0.082,  9, 1, 0),
        ("auto",  "WARNING", 0.143,  8, 2, 1),
    ]
    for code, status, psi_max, n_feat, n_warn, n_crit in configs:
        dr = DriftReport(
            branch_id=branches[code].id,
            status=status,
            psi_max=psi_max,
            n_features_analyzed=n_feat,
            n_features_warning=n_warn,
            n_features_critical=n_crit,
            reference_window_days=90,
            current_window_days=30,
            triggered_by=admin_id,
        )
        # Set computed_at si présent dans le modèle
        if hasattr(dr, "computed_at"):
            dr.computed_at = _utcnow() - timedelta(hours=3)
        db.add(dr)
        created += 1
    db.flush()
    return created


def run(db: Session) -> dict:
    from core.db.models.referentiels import Branch
    from core.db.models.iam import User
    from core.db.models.sinistres import Claim, ClaimLine
    from core.db.models.pipeline import (
        AnalysisRun, Analysis, ShapContribution, ModelVersion, ProductionDeployment,
    )
    from core.db.models.hitl_graph import Decision

    stats = {
        "practitioners": 0, "garages": 0, "claims": 0, "lines": 0,
        "analyses": 0, "shap": 0, "decisions": 0, "drift": 0, "skipped": 0,
    }
    random.seed(2026)

    # ── Lookup prérequis ─────────────────────────────────────────────────────
    branches = {b.code: b for b in db.query(Branch).filter(
        Branch.code.in_(["sante", "auto"])
    ).all()}
    if len(branches) < 2:
        raise RuntimeError("Branches sante/auto introuvables — exécuter seed_01.")
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        raise RuntimeError("User admin introuvable — exécuter seed_03.")
    gestionnaire = db.query(User).filter(User.username == "gestionnaire1").first() or admin

    # Récupère les ProductionDeployments actifs (créés par seed_05)
    deployments = {}
    for code, branch in branches.items():
        dep = db.query(ProductionDeployment).filter(
            ProductionDeployment.branch_id == branch.id,
            ProductionDeployment.replaced_at.is_(None),
        ).first()
        if not dep:
            raise RuntimeError(f"Aucun modèle déployé pour {code} — exécuter seed_05 d'abord.")
        deployments[code] = dep

    # ── Praticiens + Garages ─────────────────────────────────────────────────
    practs = _seed_practitioners(db)
    stats["practitioners"] = len(practs)
    garages = _seed_garages(db)
    stats["garages"] = len(garages)

    # ── Drift reports ────────────────────────────────────────────────────────
    stats["drift"] = _seed_drift_reports(db, branches, admin.id)

    # ── Analysis runs v2 ─────────────────────────────────────────────────────
    runs = {}
    for code, branch in branches.items():
        n = N_SANTE_V2 if code == "sante" else N_AUTO_V2
        n_anom = len(_ANOM_SANTE_IDX) if code == "sante" else len(_ANOM_AUTO_IDX)
        _run_start = _utcnow() - timedelta(hours=6)
        run_obj = AnalysisRun(
            branch_id=branch.id,
            model_version_id=deployments[code].model_version_id,
            run_type="batch",
            nb_dossiers=n, nb_anomalies=n_anom,
            graph_enabled=True,  # v2 active le graphe pour Pattern Réseau
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

    # ── Boucle sinistres ─────────────────────────────────────────────────────
    branch_batches = [
        ("sante", N_SANTE_V2, _ANOM_SANTE_IDX, _SANTE_RCA, "SIN",  practs,  ACTES_SANTE, "praticien"),
        ("auto",  N_AUTO_V2,  _ANOM_AUTO_IDX,  _AUTO_RCA,  "AUTO", garages, POSTES_AUTO, "garage"),
    ]

    for code, n, anom_set, rca_list, prefix, providers, items, kind in branch_batches:
        branch = branches[code]
        rca_cycle = 0

        for i in range(n):
            days_ago = round(i * 29 / max(n - 1, 1))
            ts = _utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))
            claim_id = f"{prefix}_2026_CM_{3000 + i:05d}"

            if db.query(Claim).filter(Claim.claim_id == claim_id).first():
                stats["skipped"] += 1
                continue

            is_anom = i in anom_set
            dec_info = _DECISIONS_V2.get((code, i))
            decision_status = dec_info[0] if dec_info else "PENDING"
            claim_statut = "CLOSED" if decision_status in ("CONFIRMED", "REJECTED") else "OPEN"

            montant = round(
                random.uniform(15_000, 220_000) if code == "sante"
                else random.uniform(200_000, 2_500_000), 0
            )

            claim = Claim(
                claim_id=claim_id, branch_id=branch.id, contract_id=None,
                source_flux="structured", montant_facture=montant, devise="XAF",
                montant_xaf=montant,
                date_soin=(ts - timedelta(days=3)).date(),
                date_declaration=(ts - timedelta(days=1)).date(),
                date_saisie=ts.date(), heure_saisie=random.randint(7, 19),
                statut=claim_statut, created_by=None,
                created_at=ts, updated_at=ts,
            )
            db.add(claim)
            db.flush()
            stats["claims"] += 1

            # Claim lines : 1-4 actes/postes, lié à un prestataire
            primary_provider = random.choice(providers)
            n_lines = random.randint(1, 4) if code == "sante" else random.randint(1, 3)
            total_lines = 0.0
            for _ in range(n_lines):
                code_a, libelle, prix_ref = random.choice(items)
                facteur = random.uniform(0.85, 3.2) if is_anom else random.uniform(0.9, 1.25)
                montant_l = round(prix_ref * facteur, 0)
                total_lines += montant_l
                line_kwargs = dict(
                    claim_id=claim.id, code_acte=code_a, libelle=libelle,
                    montant_ligne=montant_l, prix_ref=prix_ref,
                    ratio_prix=round(facteur, 3), quantite=1,
                )
                if kind == "praticien":
                    line_kwargs["praticien_id_hash"] = primary_provider.id_hash
                else:
                    line_kwargs["garage_id_hash"] = primary_provider.id_hash
                db.add(ClaimLine(**line_kwargs))
                stats["lines"] += 1

            # Score d'anomalie + RCA
            if is_anom:
                score = round(random.uniform(0.65, 0.96), 4)
                cat, sub, rule_id = rca_list[rca_cycle % len(rca_list)]
                rca_cycle += 1
                conf = round(random.uniform(0.70, 0.94), 3)
                expl = (f"Dossier {claim_id} — Score {score:.2f}. "
                        f"Catégorie : {cat} ({sub}). "
                        f"Confiance : {conf:.0%}.")
            else:
                score = round(random.uniform(0.08, 0.55), 4)
                cat = sub = rule_id = expl = None
                conf = None

            analysis = Analysis(
                claim_id=claim.id, run_id=runs[code].id, branch_id=branch.id,
                model_version_id=deployments[code].model_version_id,
                anomaly_score=score, is_anomaly=is_anom,
                detector_name="isolation_forest",
                rca_category=cat, rca_subcategory=sub,
                rca_confidence=conf, rca_rule_id=rule_id,
                explanation_fr=expl, decision_status=decision_status,
                processing_time_ms=round(random.uniform(40, 420), 1),
                created_at=ts + timedelta(minutes=5),
            )
            db.add(analysis)
            db.flush()
            stats["analyses"] += 1

            # SHAP — diversifié (positifs ET négatifs) pour anomalies
            if is_anom:
                # Pool de features avec orientation potentielle (signe)
                features_pool = (
                    [("ratio_prix_mercuriale", 0.40, 2.5, 1),
                     ("document_altere",       0.32, 1.0, 1),
                     ("nb_actes_journee",      0.28, 7.0, 1),
                     ("anciennete_contrat",    0.18, 0.5, -1),    # négatif (réduit le risque)
                     ("agrement_cima",         0.15, 1.0, -1)]
                    if code == "sante" else
                    [("ratio_devis_reparation", 0.38, 3.0, 1),
                     ("delai_declaration_jours",0.30, 40.0, 1),
                     ("document_altere",        0.27, 1.0, 1),
                     ("anciennete_contrat",     0.20, 0.6, -1),
                     ("type_garage_agree",      0.16, 1.0, -1)]
                )
                for rank, (fname, base_shap, base_fval, sign) in enumerate(features_pool, start=1):
                    shap_val = round(base_shap * random.uniform(0.6, 1.4) * sign, 4)
                    db.add(ShapContribution(
                        analysis_id=analysis.id, feature_name=fname,
                        shap_value=shap_val,
                        feature_value=round(base_fval * random.uniform(0.8, 1.2), 3),
                        direction="positive" if sign > 0 else "negative",
                        rank=rank,
                    ))
                    stats["shap"] += 1

            # Décision HITL
            if dec_info:
                db.add(Decision(
                    analysis_id=analysis.id, decision=dec_info[0],
                    motif=dec_info[1], gestionnaire_id=gestionnaire.id,
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
        print(f"✅ Praticiens (total)   : {s['practitioners']}")
        print(f"✅ Garages (total)      : {s['garages']}")
        print(f"✅ Claims créés         : {s['claims']}")
        print(f"✅ Claim lines          : {s['lines']}")
        print(f"✅ Analyses créées      : {s['analyses']}")
        print(f"✅ SHAP contributions   : {s['shap']}")
        print(f"✅ Décisions HITL       : {s['decisions']}")
        print(f"✅ Drift reports        : {s['drift']}")
        if s["skipped"]:
            print(f"ℹ️  Claims déjà présents: {s['skipped']}")
    except Exception as e:
        db.rollback()
        print(f"❌ Erreur : {e}")
        raise
    finally:
        db.close()