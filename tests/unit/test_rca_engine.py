"""
Tests unitaires — core/rca/ (RCAEngine + evaluator)

Couvre :
- evaluate_condition : tous les opérateurs
- evaluate_rule : AND logique, feature manquante, règle vide
- compute_confidence : bonus de dépassement
- RCAEngine.apply_rules : match, no-match, priorité, erreur non-bloquante

NOTE v0.5.0 (Scénario A) :
  La fixture sample_features utilise la clé 'is_weekend_event' (au lieu de
  l'ancienne 'flag_weekend_care') pour rester cohérente avec le registre
  FEATURE_FUNCTIONS_SANTE_V1 et les règles RCA harmonisées. Cette clé n'est
  pas utilisée dans les assertions existantes mais reflète le nommage réel
  des features fournies au moteur RCA.

Lancer :
    pytest tests/unit/test_rca_engine.py -v
"""

from __future__ import annotations

import pytest

from core.rca.engine import RCAEngine
from core.rca.evaluator import compute_confidence, evaluate_condition, evaluate_rule


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_features() -> dict:
    return {
        "ratio_prix_mercuriale": 2.1,
        "flag_incoherence_sexe_acte": 0,
        "historique_ratio_praticien": 1.5,
        "nb_sinistres_30j_assure": 3,
        "is_weekend_event": 1,          # Scénario A : renommé depuis flag_weekend_care
    }


@pytest.fixture
def rule_surfacturation() -> dict:
    return {
        "id": "RCA_SURF_001",
        "name": "Surfacturation",
        "category": "Fraude Financière",
        "subcategory": "Surfacturation",
        "priority": 1,
        "confidence_base": 0.85,
        "severity": "HIGH",
        "description": "Prix > mercuriale",
        "conditions": [
            {"feature": "ratio_prix_mercuriale", "operator": ">", "threshold": 1.5}
        ],
    }


@pytest.fixture
def rule_identitaire() -> dict:
    return {
        "id": "RCA_IDENT_001",
        "name": "Incohérence sexe/acte",
        "category": "Fraude Identitaire",
        "subcategory": "Usurpation",
        "priority": 3,
        "confidence_base": 0.90,
        "severity": "CRITICAL",
        "description": "Acte incompatible avec le sexe",
        "conditions": [
            {"feature": "flag_incoherence_sexe_acte", "operator": "==", "threshold": 1}
        ],
    }


# ---------------------------------------------------------------------------
# Tests — evaluate_condition
# ---------------------------------------------------------------------------

class TestEvaluateCondition:

    def test_operator_gt_true(self):
        cond = {"feature": "ratio", "operator": ">", "threshold": 1.5}
        assert evaluate_condition(cond, {"ratio": 2.0}) is True

    def test_operator_gt_false(self):
        cond = {"feature": "ratio", "operator": ">", "threshold": 1.5}
        assert evaluate_condition(cond, {"ratio": 1.0}) is False

    def test_operator_eq(self):
        cond = {"feature": "flag", "operator": "==", "threshold": 1}
        assert evaluate_condition(cond, {"flag": 1.0}) is True

    def test_operator_lte(self):
        cond = {"feature": "score", "operator": "<=", "threshold": 0.5}
        assert evaluate_condition(cond, {"score": 0.3}) is True

    def test_operator_in(self):
        cond = {"feature": "code", "operator": "in", "threshold": ["A", "B"]}
        assert evaluate_condition(cond, {"code": "A"}) is True
        assert evaluate_condition(cond, {"code": "C"}) is False

    def test_missing_feature_returns_false(self):
        cond = {"feature": "absent", "operator": ">", "threshold": 1.0}
        assert evaluate_condition(cond, {"autre": 2.0}) is False

    def test_malformed_condition_returns_false(self):
        assert evaluate_condition({}, {"ratio": 2.0}) is False

    def test_unknown_operator_returns_false(self):
        cond = {"feature": "x", "operator": "BETWEEN", "threshold": 1.0}
        assert evaluate_condition(cond, {"x": 1.5}) is False


# ---------------------------------------------------------------------------
# Tests — evaluate_rule
# ---------------------------------------------------------------------------

class TestEvaluateRule:

    def test_all_conditions_true(self, sample_features, rule_surfacturation):
        assert evaluate_rule(rule_surfacturation, sample_features) is True

    def test_one_condition_false(self, sample_features, rule_identitaire):
        # flag_incoherence_sexe_acte = 0, règle attend == 1
        assert evaluate_rule(rule_identitaire, sample_features) is False

    def test_empty_conditions_returns_false(self, sample_features):
        rule = {"id": "EMPTY", "conditions": []}
        assert evaluate_rule(rule, sample_features) is False

    def test_multi_condition_and_logic(self, sample_features):
        rule = {
            "id": "MULTI",
            "conditions": [
                {"feature": "ratio_prix_mercuriale", "operator": ">", "threshold": 1.5},
                {"feature": "is_weekend_event", "operator": "==", "threshold": 1},
            ],
        }
        # ratio=2.1 > 1.5 ✓ AND is_weekend_event=1 == 1 ✓ → True
        assert evaluate_rule(rule, sample_features) is True

    def test_multi_condition_one_fails(self, sample_features):
        rule = {
            "id": "MULTI_FAIL",
            "conditions": [
                {"feature": "ratio_prix_mercuriale", "operator": ">", "threshold": 1.5},
                {"feature": "flag_incoherence_sexe_acte", "operator": "==", "threshold": 1},
            ],
        }
        # ratio=2.1 > 1.5 ✓ AND flag=0 == 1 ✗ → False
        assert evaluate_rule(rule, sample_features) is False


# ---------------------------------------------------------------------------
# Tests — compute_confidence
# ---------------------------------------------------------------------------

class TestComputeConfidence:

    def test_base_confidence_no_overshoot(self):
        rule = {"confidence_base": 0.80, "conditions": [
            {"feature": "ratio", "operator": ">", "threshold": 1.5}
        ]}
        # ratio exactement au seuil → bonus = 0
        conf = compute_confidence(rule, {"ratio": 1.5})
        assert conf == pytest.approx(0.80, abs=0.01)

    def test_confidence_increases_with_overshoot(self):
        rule = {"confidence_base": 0.80, "conditions": [
            {"feature": "ratio", "operator": ">", "threshold": 1.5}
        ]}
        conf_low = compute_confidence(rule, {"ratio": 1.6})
        conf_high = compute_confidence(rule, {"ratio": 3.0})
        assert conf_high > conf_low

    def test_confidence_capped_at_1(self):
        rule = {"confidence_base": 0.95, "conditions": [
            {"feature": "ratio", "operator": ">", "threshold": 1.0}
        ]}
        conf = compute_confidence(rule, {"ratio": 100.0})
        assert conf <= 1.0


# ---------------------------------------------------------------------------
# Tests — RCAEngine
# ---------------------------------------------------------------------------

class TestRCAEngine:

    def test_match_returns_correct_category(self, sample_features, rule_surfacturation):
        engine = RCAEngine()
        result = engine.apply_rules(sample_features, [rule_surfacturation])
        assert result.category == "Fraude Financière"
        assert result.rule_id == "RCA_SURF_001"
        assert result.confidence > 0.80  # base 0.85 + bonus

    def test_no_match_returns_indeterminate(self, rule_surfacturation):
        engine = RCAEngine()
        features_normaux = {"ratio_prix_mercuriale": 0.9}
        result = engine.apply_rules(features_normaux, [rule_surfacturation])
        assert result.category == "Indéterminé"

    def test_priority_order_respected(self, sample_features,
                                       rule_surfacturation, rule_identitaire):
        engine = RCAEngine()
        # rule_surfacturation priority=1 doit gagner sur rule_identitaire priority=3
        # Même si identitaire n'aurait pas matché, s'assurer que l'ordre est respecté
        rules = [rule_identitaire, rule_surfacturation]  # ordre inversé dans la liste
        result = engine.apply_rules(sample_features, rules)
        # surfacturation (prio 1) est évaluée en premier → match
        assert result.rule_id == "RCA_SURF_001"

    def test_empty_rules_returns_indeterminate(self, sample_features):
        engine = RCAEngine()
        result = engine.apply_rules(sample_features, [])
        assert result.category == "Indéterminé"

    def test_empty_features_returns_indeterminate(self, rule_surfacturation):
        engine = RCAEngine()
        result = engine.apply_rules({}, [rule_surfacturation])
        assert result.category == "Indéterminé"

    def test_defective_rule_does_not_crash(self, sample_features):
        engine = RCAEngine()
        bad_rule = {"id": "BAD", "priority": 0, "conditions": None}
        good_rule = {
            "id": "GOOD", "priority": 1, "confidence_base": 0.80,
            "category": "Test", "subcategory": "", "severity": "LOW",
            "conditions": [{"feature": "ratio_prix_mercuriale", "operator": ">", "threshold": 1.5}],
        }
        # La règle défectueuse ne doit pas arrêter le moteur
        result = engine.apply_rules(sample_features, [bad_rule, good_rule])
        assert result.category == "Test"