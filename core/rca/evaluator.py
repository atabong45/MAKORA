"""
MODULE : core/rca/evaluator.py
DESCRIPTION : Évaluation des conditions individuelles des règles RCA.

RÉFÉRENCES ACADÉMIQUES :
- [GoF1994] Gamma et al. (1994). Design Patterns. Chain of Responsibility.
  → Chaque RuleEvaluator évalue une règle ; passe la main si non-match.
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML. NeurIPS.
  → Séparer logique d'évaluation / logique d'orchestration réduit le couplage.

DÉCISIONS DE CONCEPTION :
- Opérateurs supportés : >, >=, <, <=, ==, !=, in.
  Extensible sans modifier RCAEngine (principe ouvert/fermé).
- Une règle est True si TOUTES ses conditions sont satisfaites (AND logique).
  Le OR est modélisé par plusieurs règles distinctes dans le YAML.
- Feature absente du dossier → condition False (non-bloquant, log warning).
"""

from __future__ import annotations

from typing import Any

from core.logging_config import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Opérateurs supportés
# ---------------------------------------------------------------------------

import operator

_OPERATOR_FUNCS = {
    # Notation symbolique (existante)
    ">":  operator.gt,
    ">=": operator.ge,
    "<":  operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
    "in": lambda a, b: a in b,
    # Notation textuelle (alias YAML — [Sculley2015] flexibilité config)
    "gt":  operator.gt,
    "gte": operator.ge,
    "ge":  operator.ge,
    "lt":  operator.lt,
    "lte": operator.le,
    "le":  operator.le,
    "eq":  operator.eq,
    "neq": operator.ne,
    "ne":  operator.ne,
    "not_in": lambda a, b: a not in b,
}


def evaluate_condition(
    condition: dict[str, Any],
    feature_values: dict[str, float],
) -> bool:
    """
    Évalue une condition individuelle d'une règle RCA.

    Args:
        condition: dict avec clés 'feature', 'operator', 'threshold'.
        feature_values: valeurs des features pour le dossier courant.

    Returns:
        True si la condition est satisfaite, False sinon.
    """
    feature = condition.get("feature")
    operator = condition.get("operator")
    threshold = condition.get("threshold")

    if feature is None or operator is None or threshold is None:
        logger.warning("Condition malformée : %s — ignorée (False).", condition)
        return False

    if feature not in feature_values:
        logger.warning("Feature '%s' absente du dossier — condition False.", feature)
        return False

    op_func = _OPERATOR_FUNCS.get(operator)
    if op_func is None:
        logger.warning(
            "Opérateur '%s' non supporté — condition False. Valides : %s",
            operator, list(_OPERATOR_FUNCS.keys()),
        )
        return False

    try:
        return bool(op_func(feature_values[feature], threshold))
    except (TypeError, ValueError) as exc:
        logger.warning(
            "Erreur évaluation feature='%s' op='%s' threshold=%s : %s — False.",
            feature, operator, threshold, exc,
        )
        return False


def evaluate_rule(
    rule: dict[str, Any],
    feature_values: dict[str, float],
) -> bool:
    """
    Évalue une règle complète : toutes ses conditions (AND logique).

    Args:
        rule: dict de règle issu du YAML.
        feature_values: valeurs des features pour le dossier courant.

    Returns:
        True si TOUTES les conditions sont satisfaites.
    """
    conditions = rule.get("conditions", [])
    if not conditions:
        logger.warning("Règle '%s' sans conditions — False.", rule.get("id", "?"))
        return False

    return all(evaluate_condition(c, feature_values) for c in conditions)


def compute_confidence(
    rule: dict[str, Any],
    feature_values: dict[str, float],
) -> float:
    """
    Calcule la confiance ajustée selon le dépassement du seuil principal.

    La confiance de base vient du YAML (confidence_base).
    Un dépassement fort du seuil augmente légèrement la confiance (+max 15%).

    Returns:
        float ∈ [0.0, 1.0]
    """
    base = float(rule.get("confidence_base", 0.75))
    conditions = rule.get("conditions", [])
    if not conditions:
        return base

    first = conditions[0]
    feature = first.get("feature")
    threshold = first.get("threshold")
    operator = first.get("operator", "")

    if feature not in feature_values or threshold is None:
        return base

    try:
        val = float(feature_values[feature])
        thr = float(threshold)
        if operator in (">", ">=") and thr > 0:
            # +10% de confiance par 100% de dépassement, cap à +15%
            bonus = min(0.15, (val / thr - 1.0) * 0.10)
            return min(1.0, base + bonus)
    except (TypeError, ValueError):
        pass

    return base