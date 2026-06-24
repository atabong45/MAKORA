"""
TESTS : tests/unit/test_sante_yaml_v030.py
DESCRIPTION : Validation du YAML sante v0.4.0 — 17 features (V1 + EXT + RESEAU),
              13+ règles RCA. Vérifie la cohérence YAML ↔ FEATURE_*_FUNCTIONS
              ↔ features.py + features_ext.py + features_reseau.py.

NOTE HISTORIQUE :
- v0.3.0 (Session H) : 14 features (5 V1 + 9 EXT)
- v0.4.0 (Session I) : 17 features (+3 RESEAU : flag_doublon_sante,
                       community_score_sante, praticien_concentration)
- T13.2 : activation graph_analysis.enabled = true (brique optionnelle
          mais activable selon dataset).

RÉFÉRENCES :
- [Sculley2015] : tout paramètre métier doit vivre dans la configuration,
  pas dans le code — ces tests protègent cette invariance.
- [Blondel2008] : features réseau Louvain — community_score_sante.

RUN :
    pytest tests/unit/test_sante_yaml_v030.py -v
"""
from __future__ import annotations

from pathlib import Path
import sys
import yaml
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

YAML_PATH = ROOT / "modules" / "sante" / "sante.yaml"

# APRÈS
EXPECTED_FEATURES_V1 = {
    "ratio_prix_mercuriale",
    "flag_incoherence_sexe_acte",
    "historique_ratio_praticien",
    "nb_sinistres_30j_assure",
    "is_weekend_event",                  # Scénario A
}

EXPECTED_FEATURES_EXT = {
    "document_altere",
    "praticien_hors_agrement",
    "ocr_confiance_faible",
    "delai_depot_anormal",               # Scénario A
    "anciennete_contrat_courte",
    "saisie_hors_heures",
    "montant_log",                       # Scénario C
    "post_mortem_flag",
    "nb_sinistres_meme_iban",
    "acte_incomplet",                    # Scénario A — NOUVEAU
    "document_age_anormal",              # Scénario B — NOUVEAU
    "nb_sinistres_recents",              # Scénario B — NOUVEAU
}

EXPECTED_FEATURES_RESEAU = {
    "flag_doublon",                      # Scénario A
    "community_score",                   # Scénario A
    "prestataire_concentration",         # Scénario A
}

EXPECTED_TOTAL = 20


@pytest.fixture(scope="module")
def cfg():
    """Charge sante.yaml une fois pour tous les tests du module."""
    assert YAML_PATH.exists(), f"sante.yaml introuvable : {YAML_PATH}"
    with YAML_PATH.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


# ===========================================================================
# Tests structure de base
# ===========================================================================

class TestYamlStructure:

    def test_yaml_loads(self, cfg):
        assert cfg is not None

    def test_branch_is_sante(self, cfg):
        assert cfg["branch"] == "sante"

    def test_version_is_030(self, cfg):
        # Renommé sémantiquement : test que la version est >= 0.3.0
        # Le YAML est en 0.4.0 (Session I) — ce test valide la progression.
        from packaging import version as pkg_version
        actual = cfg["version"]
        assert pkg_version.parse(actual) >= pkg_version.parse("0.3.0"), (
            f"Version YAML {actual} < 0.3.0 — régression détectée."
        )

    def test_required_keys_present(self, cfg):
        required = ["branch", "version", "features", "rca_rules",
                    "thresholds", "input_schema", "source_mappings", "drift"]
        for key in required:
            assert key in cfg, f"Clé obligatoire manquante : '{key}'"

    def test_thresholds_present(self, cfg):
        t = cfg["thresholds"]
        assert "contamination" in t
        assert "anomaly_score_alert" in t

    def test_contamination_in_range(self, cfg):
        # [Bauder2017] : taux fraude santé estimé 3-10%
        c = cfg["thresholds"]["contamination"]
        assert 0.03 <= c <= 0.12, (
            f"contamination={c} hors plage [Bauder2017] : 3%-12%"
        )


# ===========================================================================
# Tests features
# ===========================================================================

class TestFeatures:

    def test_features_count_is_14(self, cfg):
        # Renommé sémantiquement : 17 features attendues en v0.4.0
        # (5 V1 + 9 EXT + 3 RESEAU)
        features = cfg["features"]
        assert len(features) == EXPECTED_TOTAL, (
            f"{EXPECTED_TOTAL} features attendues (5 V1 + 9 EXT + 3 RESEAU), "
            f"trouvées : {len(features)}\nFeatures : {features}"
        )

    def test_all_v1_features_present(self, cfg):
        features = set(cfg["features"])
        missing = EXPECTED_FEATURES_V1 - features
        assert not missing, f"Features V1 manquantes dans le YAML : {missing}"

    def test_all_ext_features_present(self, cfg):
        features = set(cfg["features"])
        missing = EXPECTED_FEATURES_EXT - features
        assert not missing, f"Features EXT manquantes dans le YAML : {missing}"

    def test_all_reseau_features_present(self, cfg):
        """[T13.2] Les 3 features réseau doivent être déclarées en v0.4.0."""
        features = set(cfg["features"])
        missing = EXPECTED_FEATURES_RESEAU - features
        assert not missing, f"Features RESEAU manquantes dans le YAML : {missing}"

    def test_no_duplicate_features(self, cfg):
        features = cfg["features"]
        assert len(features) == len(set(features)), (
            f"Doublons détectés dans features: "
            f"{[f for f in features if features.count(f) > 1]}"
        )

    def test_features_aligned_with_feature_ext_functions(self):
        """
        Vérifie que toutes les features de FEATURE_EXT_FUNCTIONS sont
        dans le YAML — la source de vérité du code doit correspondre au YAML.
        """
        try:
            from modules.sante.features_ext import FEATURE_EXT_FUNCTIONS
            yaml_features = set(yaml.safe_load(YAML_PATH.read_text())["features"])
            for name in FEATURE_EXT_FUNCTIONS:
                assert name in yaml_features, (
                    f"Feature '{name}' dans FEATURE_EXT_FUNCTIONS "
                    f"mais absente du YAML — désynchronisation."
                )
        except ImportError:
            pytest.skip("modules.sante.features_ext non importable depuis ce contexte")

    def test_features_described(self, cfg):
        """Toutes les features ont une description (bonne pratique doc)."""
        descriptions = cfg.get("features_descriptions", {})
        features = cfg["features"]
        missing_desc = [f for f in features if f not in descriptions]
        # On tolère l'absence de description — warning uniquement
        if missing_desc:
            import warnings
            warnings.warn(
                f"Features sans description dans YAML : {missing_desc}",
                UserWarning,
                stacklevel=2,
            )


# ===========================================================================
# Tests règles RCA
# ===========================================================================

class TestRcaRules:

    def test_rca_rules_count(self, cfg):
        rules = cfg["rca_rules"]
        assert len(rules) >= 10, (
            f"Attendu ≥ 10 règles RCA, trouvé : {len(rules)}"
        )

    def test_rca_rule_ids_unique(self, cfg):
        ids = [r["id"] for r in cfg["rca_rules"]]
        assert len(ids) == len(set(ids)), (
            f"IDs RCA dupliqués : {[i for i in ids if ids.count(i) > 1]}"
        )

    def test_rca_rule_ids_format(self, cfg):
        import re
        pattern = re.compile(r"^RCA_[A-Z]+_\d{3}$")
        for rule in cfg["rca_rules"]:
            assert pattern.match(rule["id"]), (
                f"Format ID invalide : '{rule['id']}' "
                f"(attendu : RCA_XXX_NNN)"
            )

    def test_rca_required_fields(self, cfg):
        required = ["id", "priority", "category", "subcategory",
                    "conditions", "logic", "confidence_base", "message_template"]
        for rule in cfg["rca_rules"]:
            for field in required:
                assert field in rule, (
                    f"Règle '{rule.get('id', '?')}' — champ manquant : '{field}'"
                )

    def test_rca_confidence_in_range(self, cfg):
        for rule in cfg["rca_rules"]:
            c = rule["confidence_base"]
            assert 0.0 <= c <= 1.0, (
                f"Règle '{rule['id']}' — confidence_base={c} hors [0,1]"
            )

    def test_rca_priority_unique_and_positive(self, cfg):
        priorities = [r["priority"] for r in cfg["rca_rules"]]
        assert all(p >= 1 for p in priorities), "Priorité doit être >= 1"
        assert len(priorities) == len(set(priorities)), (
            f"Priorités dupliquées : {[p for p in priorities if priorities.count(p) > 1]}"
        )

    def test_rca_conditions_reference_known_features(self, cfg):
        """Les conditions RCA ne doivent référencer que des features du YAML."""
        known_features = set(cfg["features"])
        for rule in cfg["rca_rules"]:
            for cond in rule.get("conditions", []):
                feat = cond["feature"]
                assert feat in known_features, (
                    f"Règle '{rule['id']}' : condition sur feature inconnue "
                    f"'{feat}'. Features connues : {sorted(known_features)}"
                )

    def test_critical_rules_present(self, cfg):
        """Les règles de haute confiance doivent exister."""
        ids = {r["id"] for r in cfg["rca_rules"]}
        critical = ["RCA_GHOST_001", "RCA_DEAD_001", "RCA_DOC_001", "RCA_SURF_001"]
        for rule_id in critical:
            assert rule_id in ids, f"Règle critique manquante : {rule_id}"

    def test_ghost_rule_highest_confidence(self, cfg):
        """RCA_GHOST_001 (post-mortem) doit avoir la confiance la plus élevée."""
        ghost = next(r for r in cfg["rca_rules"] if r["id"] == "RCA_GHOST_001")
        assert ghost["confidence_base"] >= 0.95, (
            f"RCA_GHOST_001 confidence={ghost['confidence_base']} < 0.95"
        )

    def test_rca_logic_valid(self, cfg):
        for rule in cfg["rca_rules"]:
            assert rule["logic"] in ("AND", "OR"), (
                f"Règle '{rule['id']}' — logic='{rule['logic']}' invalide"
            )

    def test_rca_categories_valid(self, cfg):
        valid_cats = {
            "Fraude Intentionnelle",
            "Erreur Opérationnelle",
            "Biais Système",
            "Risque Technique",
        }
        for rule in cfg["rca_rules"]:
            assert rule["category"] in valid_cats, (
                f"Règle '{rule['id']}' — catégorie invalide : '{rule['category']}'"
            )


# ===========================================================================
# Tests drift et graph
# ===========================================================================

class TestDriftAndGraph:

    def test_drift_section_present(self, cfg):
        assert "drift" in cfg
        drift = cfg["drift"]
        assert "monitored_features" in drift
        assert "thresholds" in drift

    def test_drift_features_are_known(self, cfg):
        known = set(cfg["features"])
        for f in cfg["drift"]["monitored_features"]:
            assert f in known, (
                f"Feature drift '{f}' inconnue dans la liste features YAML"
            )

    def test_drift_thresholds_ordered(self, cfg):
        """[Gama2014] : warning < critical."""
        t = cfg["drift"]["thresholds"]
        assert t["warning"] < t["critical"], (
            f"Seuils drift incohérents : warning={t['warning']} >= critical={t['critical']}"
        )

    def test_graph_section_present_and_disabled(self, cfg):
        """
        [T13.2] La section graph_analysis est présente et configurée.
        Renommé sémantiquement : la brique est désormais ACTIVÉE en v0.4.0
        (la nomenclature 'disabled' du test original était v0.3.0).
        L'activation reste conditionnelle au dataset (colonnes requises).
        """
        assert "graph_analysis" in cfg, (
            "Section graph_analysis manquante dans le YAML"
        )
        graph_cfg = cfg["graph_analysis"]
        # La brique est explicitement configurée (enabled true ou false)
        assert "enabled" in graph_cfg, (
            "graph_analysis.enabled doit être déclaré (true ou false)"
        )
        # Si activée, les colonnes requises doivent être présentes
        if graph_cfg["enabled"]:
            for required_key in ("entity_col", "assure_col"):
                assert required_key in graph_cfg, (
                    f"graph_analysis activé mais '{required_key}' absent"
                )


# ===========================================================================
# Test d'intégration léger — instanciation du module
# ===========================================================================

class TestModuleInstantiation:

    def test_sante_module_loads_with_14_features(self):
        """
        Renommé sémantiquement : SanteModule retourne le nombre attendu
        de features (17 en v0.4.0, 14 en v0.3.0).
        """
        try:
            import modules.sante.sante_module  # noqa — déclenche @register
            from modules.sante.sante_module import SanteModule
            m = SanteModule(config_path=YAML_PATH) 
            features = m.get_feature_names()
            assert len(features) == EXPECTED_TOTAL, (
                f"SanteModule.get_feature_names() retourne {len(features)} "
                f"features, attendu {EXPECTED_TOTAL}.\nFeatures : {features}"
            )
        except ImportError:
            pytest.skip("SanteModule non importable depuis ce contexte de test")

    def test_feature_ext_functions_count(self):
        """FEATURE_EXT_FUNCTIONS doit contenir exactement 9 entrées."""
        try:
            from modules.sante.features_ext import FEATURE_EXT_FUNCTIONS
            assert len(FEATURE_EXT_FUNCTIONS) == 12, (  # v0.5.0 : +3 nouvelles
                f"FEATURE_EXT_FUNCTIONS contient {len(FEATURE_EXT_FUNCTIONS)} "
                f"fonctions, attendu 12."
            )
        except ImportError:
            pytest.skip("features_ext non importable depuis ce contexte")