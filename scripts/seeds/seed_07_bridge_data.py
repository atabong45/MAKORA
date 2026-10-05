"""
MODULE : scripts/seeds/seed_07_bridge_data.py
DESCRIPTION : Entités canoniques frontend↔BD.
  Crée les praticiens héros (IDs courts lisibles), garages, codes actes ASAC
  supplémentaires, 9 sinistres héros (SHAP riche + narration 4-6 phrases),
  15 sinistres graphe légers, et corrige les 2 DriftReports → STABLE.
  Idempotent sur claim_id / id_hash / code_acte.

Prérequis : seed_02, seed_03, seed_04, seed_05 doivent avoir tourné.
Usage     : docker exec makora_api python -m scripts.seeds.seed_07_bridge_data
"""
from __future__ import annotations
import uuid
from datetime import datetime, timedelta, timezone

_NOW = datetime.now(timezone.utc)

# ─── Entités stables ─────────────────────────────────────────────────────────
# (id_hash, specialite, region, pays, agrement_cima, ratio_prix_moyen, nb_sinistres)
PRACTITIONERS = [
    ("PRAT_HASH_4821", "Cardiologie",   "Littoral", "CM", True,  2.14, 47),
    ("PRAT_HASH_9221", "Généraliste",   "Centre",   "CM", True,  1.38, 128),
    ("PRAT_HASH_9824", "Ophtalmologie", "Adamaoua", "CM", False, 1.71, 31),
    ("PRAT_HASH_2901", "Pédiatrie",     "Nord",     "CM", True,  1.05, 58),
    ("PRAT_HASH_1029", "Dentaire",      "Ouest",    "CM", True,  0.92, 32),
]
# (id_hash, nom, type_garage, ville, pays, agrement_cima, ratio_devis_moyen, nb_sinistres)
GARAGES = [
    ("GAR_HASH_112", "Garage Douala Akwa #1", "indépendant", "Douala",  "CM", False, 1.89, 143),
    ("GAR_HASH_334", "Garage Yaoundé Bastos", "agréé",       "Yaoundé", "CM", True,  1.12,  67),
]
# (branch_code, code_acte, libelle, prix_xaf, prix_eur)
EXTRA_ACTES = [
    ("sante", "ASAC_CARD_007", "Échocardiographie",   30_000, 45.73),
    ("sante", "ASAC_CARD_001", "Électrocardiogramme", 12_000, 18.29),
]

# ─── Sinistres héros ─────────────────────────────────────────────────────────
# (cid, br, prov, kind, mnt, score, is_anom, rca_cat, rca_sub, rca_rule,
#  rca_conf, dec_str, motif, actes, shap_feats, narration, days_ago)
HERO_CLAIMS = [
  ("SIN_2026_CM_01847","sante","PRAT_HASH_4821","praticien",54_300,0.91,True,
   "Fraude Intentionnelle","Surfacturation Prestataire","RCA_SURF_001",0.89,
   "CONFIRMED","Surfacturation vérifiée — ratio 1,81× Mercuriale CIMA confirmé "
   "sur facture originale n°2912.",
   [("ASAC_CARD_007","Échocardiographie",30_000,1.81)],
   [("ratio_prix_mercuriale",+.312,1.81),("historique_ratio_praticien",+.187,2.14),
    ("montant_normalise_log",+.094,9.83),("nb_actes_journee",+.071,4.0),
    ("nb_sinistres_30j_assure",+.043,3.0),("score_confiance_ocr_agg",-.038,.91),
    ("anciennete_contrat",-.021,8.0)],
   ("Dossier SIN_2026_CM_01847 — score critique 0,91. Ratio prix/Mercuriale de 1,81× : "
    "échocardiographie facturée 54 300 XAF vs barème CIMA 30 000 XAF, violation "
    "RCA_SURF_001 (seuil 1,5×). Pattern systémique sur 7/12 dossiers récents du praticien "
    "PRAT_HASH_4821 (historique_ratio_praticien : 2,14, SHAP +0,187). "
    "Cluster Louvain de 8 assurés détecté (community_score : 0,72). "
    "Recommandation : suspension du remboursement et saisine cellule anti-fraude CIMA."), 3),

  ("SIN_2026_CM_01822","sante","PRAT_HASH_4821","praticien",42_000,0.76,True,
   "Fraude Intentionnelle","Unbundling","RCA_UNB_001",0.82,
   "CONFIRMED","Unbundling avéré — 3 actes facturés séparément pour un bilan cardio "
   "global (25 000 XAF).",
   [("ASAC_C_002","Consultation spécialiste",10_000,1.20),
    ("ASAC_CARD_001","Électrocardiogramme",12_000,0.92),
    ("ASAC_B_002","Bilan sanguin NFS",8_000,1.10)],
   [("nb_actes_journee",+.298,4.0),("ratio_prix_mercuriale",+.214,1.07),
    ("community_score_sante",+.141,.72),("praticien_hors_agrement",-.065,0.0),
    ("score_confiance_ocr_agg",-.031,.93)],
   ("Dossier SIN_2026_CM_01822 — score 0,76. Trois actes connexes facturés séparément "
    "le même jour par PRAT_HASH_4821 totalisent 42 000 XAF, alors qu'un forfait cardio "
    "global est tarifé 25 000 XAF en Mercuriale CIMA (nb_actes_journee, SHAP +0,298). "
    "L'appartenance au cluster Louvain n°1 (community_score : 0,72) renforce la suspicion "
    "de pratiques systémiques d'unbundling."), 5),

  ("SIN_2026_CM_01799","sante","PRAT_HASH_4821","praticien",22_000,0.88,True,
   "Fraude Intentionnelle","Phantom Billing","RCA_PHAN_001",0.94,
   "CONFIRMED","Phantom billing confirmé — soin facturé 15 jours après le décès de "
   "l'assuré.",
   [("ASAC_C_002","Consultation spécialiste",10_000,2.20)],
   [("post_mortem_flag",+.410,1.0),("delai_soin_depot_anormal",+.285,31.0),
    ("praticien_hors_agrement",+.192,0.0),("flag_weekend_care",+.121,1.0),
    ("score_confiance_ocr_agg",-.088,.78)],
   ("Dossier SIN_2026_CM_01799 — score élevé 0,88. Le post_mortem_flag (SHAP +0,410) "
    "indique que la date de soin (10/05/2026) est postérieure de 15 jours au décès "
    "de l'assuré. Le praticien PRAT_HASH_4821 n'est plus inscrit au registre CIMA "
    "depuis 02/2026 (praticien_hors_agrement, SHAP +0,192). "
    "Action : blocage immédiat et ouverture d'une procédure pénale."), 7),

("SIN_2026_CM_01848","sante","PRAT_HASH_9221","praticien",42_500,0.54,True,
   "Comportement Suspect","Sinistralité Assuré Anormale","RCA_FREQ_001",0.71,
   "PENDING",None,
   [("ASAC_C_001","Consultation générale",5_000,1.18),
    ("ASAC_CARD_001","Électrocardiogramme",12_000,0.95),
    ("ASAC_I_002","Échographie abdominale",15_000,1.05),
    ("ASAC_B_002","Bilan sanguin NFS",10_000,1.00)],
   [("nb_sinistres_30j_assure",+.261,8.0),("historique_ratio_praticien",+.143,1.38),
    ("community_score_sante",+.087,.41),("anciennete_contrat",-.052,3.0),
    ("score_confiance_ocr_agg",-.029,.88)],
   ("Dossier SIN_2026_CM_01848 — score modéré 0,54 (seuil alerte : 0,50). "
    "La fréquence de l'assuré est anormalement élevée : 8 sinistres en 30 jours vs "
    "une moyenne régionale de 1,2 (nb_sinistres_30j_assure, SHAP +0,261). "
    "Les actes individuels restent dans la norme, mais la concentration temporelle "
    "suggère un usage abusif de la couverture."), 0),

  ("SIN_2026_CM_01831","sante","PRAT_HASH_9221","praticien",25_000,0.67,True,
   "Anomalie Documentaire","Document Falsifié","RCA_DOC_001",0.76,
   "REJECTED","Faux positif — signature numérique validée après vérification manuelle.",
   [("ASAC_I_002","Échographie abdominale",45_000,0.56)],
   [("document_altere",+.334,1.0),("score_confiance_ocr_agg",+.218,.43),
    ("praticien_hors_agrement",+.092,0.0),("anciennete_contrat",-.118,6.0),
    ("historique_ratio_praticien",-.041,1.38)],
   ("Dossier SIN_2026_CM_01831 — score 0,67, catégorie Document Falsifié. "
    "L'OCR a signalé une discordance de signature (confiance : 0,43 vs seuil 0,60). "
    "Après vérification manuelle, la dégradation du scan a été confirmée — "
    "non une falsification. Classé faux positif. "
    "Recommandation : renforcement du pipeline OCR pour ce format de document."), 3),

  ("SIN_2026_CM_01849","sante","PRAT_HASH_1029","praticien",8_500,0.12,False,
   None,None,None,None,"PENDING",None,
   [("ASAC_C_001","Consultation générale",5_000,0.95)],[],None,4),

  ("SIN_2026_CM_01402","sante","PRAT_HASH_2901","praticien",32_000,0.69,True,
   "Pattern Réseau","Coordination Praticien-Assuré","RCA_NET_001",0.73,
   "REJECTED","Faux positif réseau — cluster professionnel (mutuelle EMP_027).",
   [("ASAC_I_002","Échographie abdominale",45_000,0.71)],
   [("community_score_sante",+.284,.63),("nb_sinistres_meme_iban",+.157,3.0),
    ("historique_ratio_praticien",+.089,1.05),("anciennete_contrat",-.074,4.0),
    ("score_confiance_ocr_agg",-.033,.91)],
   ("Dossier SIN_2026_CM_01402 — score 0,69, communauté Louvain suspecte (score : 0,63). "
    "L'audit a établi que le regroupement est d'ordre professionnel (mutuelle d'entreprise "
    "EMP_027). Classé faux positif réseau ; praticien PRAT_HASH_2901 blanchi."), 9),

  ("AUTO_2026_CM_00234","auto","GAR_HASH_112","garage",385_000,0.78,True,
   "Fraude Intentionnelle","Mise en Scène d'Accident","RCA_STG_001",0.83,
   "PENDING","Investigation en cours — photos d'accident transmises à l'expert Akono.",
   [("CARROSSERIE","Réparation carrosserie",420_000,0.92),
    ("EXPERT","Frais d'expertise",45_000,1.00)],
   [("sinistre_nuit_sans_temoin",+.308,1.0),("delai_depot_anormal",+.221,1.0),
    ("garage_non_agree",+.175,1.0),("expert_garage_correlation",+.132,.71),
    ("anciennete_contrat",-.049,2.0)],
   ("Dossier AUTO_2026_CM_00234 — score 0,78. Trois signaux classiques de staging : "
    "accident nocturne à 02h45 sans témoin, déclaration en moins de 6h, et garage non "
    "agréé CIMA (ratio devis moyen : 1,89×, corrélation expert-garage : 0,71). "
    "Investigation ouverte ; remboursement suspendu."), 3),

  ("AUTO_2026_CM_00198","auto","GAR_HASH_112","garage",980_000,0.82,True,
   "Fraude Intentionnelle","Inflation des Dommages","RCA_INF_001",0.88,
   "ESCALATED","Réseau garage-assuré suspecté — 3 sinistres similaires / 60 jours. "
   "Transmis BRH.",
   [("CARROSSERIE","Réparation carrosserie complète",420_000,2.05),
    ("PARE_BRISE","Remplacement pare-brise",120_000,1.95)],
   [("ratio_devis_bareme",+.384,2.05),("expert_garage_correlation",+.267,.83),
    ("document_altere",+.198,1.0),("anciennete_contrat",-.061,1.5),
    ("ocr_confiance_faible",-.028,.72)],
   ("Dossier AUTO_2026_CM_00198 — score 0,82. Devis de 980 000 XAF dépasse de 2,05× "
    "le barème CIMA, avec des dommages structurels décrits absents des photos fournies. "
    "Le garage GAR_HASH_112 est impliqué dans 3 sinistres analogues sur 60 jours "
    "(expert_garage_correlation : 0,83). Escalade BRH pour réseau suspecté."), 4),
]

# ─── Sinistres graphe légers ──────────────────────────────────────────────────
# (cid, br, prov, kind, mnt, score, anom, rca_cat, rca_sub, days_ago)
GRAPH_CLAIMS = [
    ("SIN_2026_CM_01850","sante","PRAT_HASH_4821","praticien",
     38_000,0.83,True,"Fraude Intentionnelle","Unbundling",6),
    ("SIN_2026_CM_01851","sante","PRAT_HASH_4821","praticien",
     29_000,0.79,True,"Fraude Intentionnelle","Surfacturation Prestataire",8),
    ("SIN_2026_CM_01854","sante","PRAT_HASH_9824","praticien",
     42_000,0.87,True,"Fraude Intentionnelle","Surfacturation Prestataire",7),
    ("SIN_2026_CM_01857","sante","PRAT_HASH_9221","praticien",
     22_000,0.74,True,"Comportement Suspect","Sinistralité anormale",5),
    ("SIN_2026_CM_01860","sante","PRAT_HASH_1029","praticien",
     8_000,0.08,False,None,None,4),
    ("SIN_2026_CM_01861","sante","PRAT_HASH_2901","praticien",
     14_000,0.15,False,None,None,6),
    ("AUTO_2026_CM_00240","auto","GAR_HASH_112","garage",
     650_000,0.85,True,"Fraude Intentionnelle","Inflation des Dommages",4),
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _seed_entities(db, branches):
    from core.db.models.referentiels import Practitioner, Garage, ReferencePrice
    from datetime import date as dt
    stats = {"practitioners": 0, "garages": 0, "actes": 0}
    for id_h, spec, reg, pays, agr, ratio, nb in PRACTITIONERS:
        if db.query(Practitioner).filter(Practitioner.id_hash == id_h).first():
            continue
        db.add(Practitioner(id_hash=id_h, specialite=spec, region=reg, pays=pays,
                            agrement_cima=agr, ratio_prix_moyen=ratio,
                            nb_sinistres_total=nb))
        stats["practitioners"] += 1
    for id_h, nom, type_g, ville, pays, agr, ratio, nb in GARAGES:
        if db.query(Garage).filter(Garage.id_hash == id_h).first():
            continue
        db.add(Garage(id_hash=id_h, nom=nom, type_garage=type_g, ville=ville,
                      pays=pays, agrement_cima=agr, ratio_devis_moyen=ratio,
                      nb_sinistres_total=nb))
        stats["garages"] += 1
    vf = dt(2025, 1, 1)
    for br_code, code, libelle, px, pe in EXTRA_ACTES:
        branch = branches[br_code]
        if db.query(ReferencePrice).filter(
            ReferencePrice.branch_id == branch.id,
            ReferencePrice.code_acte == code,
        ).first():
            continue
        db.add(ReferencePrice(id=uuid.uuid4(), branch_id=branch.id,
                              code_acte=code, libelle=libelle,
                              prix_ref_xaf=float(px), prix_ref_eur=pe,
                              nomenclature="ASAC", valid_from=vf,
                              devise_principale="XAF"))
        stats["actes"] += 1
    db.flush()
    return stats


def _seed_hero_claim(db, entry, branches, run_map, mv_map, gest_id):
    from core.db.models.sinistres import Claim, ClaimLine
    from core.db.models.pipeline import Analysis, ShapContribution
    from core.db.models.hitl_graph import Decision
    (cid, br, prov, kind, mnt, score, is_anom,
     rca_cat, rca_sub, rca_rule, rca_conf, dec_str, motif,
     actes, shap_feats, narr, days_ago) = entry
    if db.query(Claim).filter(Claim.claim_id == cid).first():
        return False
    ts = _NOW - timedelta(days=days_ago, hours=2)
    branch = branches[br]
    claim = Claim(
        claim_id=cid, branch_id=branch.id, contract_id=None,
        source_flux="structured", montant_facture=float(mnt),
        devise="XAF", montant_xaf=float(mnt),
        date_soin=(ts - timedelta(days=3)).date(),
        date_declaration=(ts - timedelta(days=1)).date(),
        date_saisie=ts.date(), heure_saisie=ts.hour,
        statut="CLOSED" if dec_str in ("CONFIRMED","REJECTED") else "OPEN",
        created_by=None, created_at=ts, updated_at=ts,
    )
    db.add(claim); db.flush()
    for code_a, libelle, prix_ref, ratio in actes:
        kw = dict(claim_id=claim.id, code_acte=code_a, libelle=libelle,
                  montant_ligne=round(float(prix_ref) * ratio),
                  prix_ref=float(prix_ref), ratio_prix=round(ratio, 3), quantite=1)
        kw["praticien_id_hash" if kind == "praticien" else "garage_id_hash"] = prov
        db.add(ClaimLine(**kw))
    analysis = Analysis(
        claim_id=claim.id, run_id=run_map[br].id, branch_id=branch.id,
        model_version_id=mv_map[br].id, anomaly_score=score, is_anomaly=is_anom,
        detector_name="deep_isolation_forest",
        rca_category=rca_cat, rca_subcategory=rca_sub,
        rca_confidence=rca_conf, rca_rule_id=rca_rule,
        explanation_fr=narr, decision_status=dec_str or "PENDING",
        processing_time_ms=round(score * 400 + 80, 1),
        created_at=ts + timedelta(minutes=5),
    )
    db.add(analysis); db.flush()
    for rank, (fname, sval, fval) in enumerate(shap_feats, 1):
        db.add(ShapContribution(
            analysis_id=analysis.id, feature_name=fname,
            shap_value=round(sval, 4), feature_value=round(fval, 3),
            direction="positive" if sval > 0 else "negative", rank=rank,
        ))
    if dec_str and dec_str != "PENDING":
        db.add(Decision(analysis_id=analysis.id, decision=dec_str,
                        motif=motif, gestionnaire_id=gest_id,
                        created_at=ts + timedelta(hours=2)))
    return True


def _seed_graph_claims(db, branches, run_map, mv_map):
    from core.db.models.sinistres import Claim
    from core.db.models.pipeline import Analysis
    created = 0
    for cid, br, prov, kind, mnt, score, is_anom, rca_cat, rca_sub, days_ago in GRAPH_CLAIMS:
        if db.query(Claim).filter(Claim.claim_id == cid).first():
            continue
        ts = _NOW - timedelta(days=days_ago, hours=4)
        branch = branches[br]
        claim = Claim(
            claim_id=cid, branch_id=branch.id, contract_id=None,
            source_flux="structured", montant_facture=float(mnt),
            devise="XAF", montant_xaf=float(mnt),
            date_soin=(ts - timedelta(days=2)).date(),
            date_declaration=ts.date(), date_saisie=ts.date(),
            heure_saisie=10, statut="OPEN",
            created_by=None, created_at=ts, updated_at=ts,
        )
        db.add(claim); db.flush()
        db.add(Analysis(
            claim_id=claim.id, run_id=run_map[br].id, branch_id=branch.id,
            model_version_id=mv_map[br].id, anomaly_score=score,
            is_anomaly=is_anom, detector_name="deep_isolation_forest",
            rca_category=rca_cat, rca_subcategory=rca_sub,
            rca_confidence=round(score * 0.9, 3) if is_anom else None,
            decision_status="PENDING",
            processing_time_ms=round(score * 300 + 60, 1),
            created_at=ts + timedelta(minutes=3),
        ))
        created += 1
    db.flush()
    return created


def _fix_drift_reports(db, branches):
    from core.db.models.monitoring import DriftReport
    updated = 0
    for code, branch in branches.items():
        psi = 0.062 if code == "sante" else 0.078
        rep = (
            db.query(DriftReport)
            .filter(DriftReport.branch_id == branch.id)
            .order_by(DriftReport.id.desc())
            .first()
        )
        if rep:
            rep.overall_status = "STABLE"
            rep.psi_global = psi
            for attr in ("n_features_warning", "n_features_critical"):
                if hasattr(rep, attr):
                    setattr(rep, attr, 0)
            updated += 1
    db.flush()
    return updated


# ─── Point d'entrée ──────────────────────────────────────────────────────────

def run(db) -> dict:
    from sqlalchemy.orm import Session
    from core.db.models.referentiels import Branch
    from core.db.models.iam import User
    from core.db.models.pipeline import ModelVersion, AnalysisRun

    stats = {"practitioners": 0, "garages": 0, "actes": 0,
             "hero_claims": 0, "graph_claims": 0, "drift_updated": 0}

    branches = {b.code: b for b in db.query(Branch).filter(
        Branch.code.in_(["sante", "auto"])).all()}
    if len(branches) < 2:
        raise RuntimeError("Branches manquantes — exécuter seed_02 d'abord.")

    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        raise RuntimeError("Admin manquant — exécuter seed_03 d'abord.")
    gest = db.query(User).filter(User.username == "gestionnaire1").first() or admin

    mv_map = {}
    for code, branch in branches.items():
        mv = (db.query(ModelVersion).filter(ModelVersion.branch_id == branch.id)
              .order_by(ModelVersion.id.desc()).first())
        if not mv:
            raise RuntimeError(f"ModelVersion manquante pour {code} — seed_05 d'abord.")
        mv_map[code] = mv

    run_map = {}
    for code, branch in branches.items():
        run_obj = (db.query(AnalysisRun).filter(AnalysisRun.branch_id == branch.id)
                   .order_by(AnalysisRun.started_at.desc()).first())
        if not run_obj:
            run_obj = AnalysisRun(
                branch_id=branch.id, model_version_id=mv_map[code].id,
                run_type="batch", nb_dossiers=24, nb_anomalies=9,
                graph_enabled=True,
                started_at=_NOW - timedelta(hours=12),
                completed_at=_NOW - timedelta(hours=11, minutes=50),
                triggered_by=admin.id,
            )
            db.add(run_obj); db.flush()
        run_map[code] = run_obj

    e = _seed_entities(db, branches)
    stats.update(e)
    for entry in HERO_CLAIMS:
        if _seed_hero_claim(db, entry, branches, run_map, mv_map, gest.id):
            stats["hero_claims"] += 1
    stats["graph_claims"] = _seed_graph_claims(db, branches, run_map, mv_map)
    stats["drift_updated"] = _fix_drift_reports(db, branches)
    db.commit()
    return stats


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from core.db.base import SessionLocal
    db = SessionLocal()
    try:
        s = run(db)
        print(f"✅ Praticiens     : {s['practitioners']}")
        print(f"✅ Garages        : {s['garages']}")
        print(f"✅ Actes ASAC+    : {s['actes']}")
        print(f"✅ Claims héros   : {s['hero_claims']}")
        print(f"✅ Claims graphe  : {s['graph_claims']}")
        print(f"✅ Drift → STABLE : {s['drift_updated']}")
    except Exception as e:
        db.rollback()
        print(f"❌ {e}")
        raise
    finally:
        db.close()
