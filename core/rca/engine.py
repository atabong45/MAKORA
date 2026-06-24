"""
MODULE : core/rca/engine.py
DESCRIPTION : Moteur RCA — implémente le Pattern Chain of Responsibility
              pour l'évaluation des règles de diagnostic MAKORA.

RÉFÉRENCES ACADÉMIQUES :
- [GoF1994] Gamma et al. (1994). Design Patterns. Chain of Responsibility.
  → Les règles YAML triées par priorité forment une chaîne ; la première
    règle matchée produit le RCAResult. Les suivantes ne sont pas évaluées.
- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML. NeurIPS.
  → Les règles RCA externalisées en YAML évitent le couplage entre la
    logique métier et le code du Kernel.
- [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection.
  → Justifie l'approche règles + ML hybride : les règles expliquent
    le "pourquoi", le ML détecte le "quoi".

DÉCISIONS DE CONCEPTION :
- RCAEngine ne connaît PAS les règles à l'avance. Elles lui sont passées
  par le module via get_rca_rules() — le Kernel reste agnostique.
- Si aucune règle ne matche → RCAResult.indeterminate() (non-bloquant).
- Les règles sont triées par priority ascendante (1 = plus haute priorité).
- apply_rules() est STATELESS : peut être appelé en parallèle.
"""

from __future__ import annotations

from typing import Any

from core.data_models import RCAResult
from core.logging_config import get_logger
from core.rca.evaluator import compute_confidence, evaluate_rule

logger = get_logger(__name__)


class RCAEngine:
    """
    Moteur d'application des règles RCA — Pattern Chain of Responsibility.

    Reçoit les règles du module via apply_rules() à chaque appel.
    Ne stocke aucun état entre les appels (STATELESS).

    Usage :
        engine = RCAEngine()
        result = engine.apply_rules(
            feature_values={"ratio_prix_mercuriale": 2.1, ...},
            rules=sante_module.get_rca_rules(),
        )
    """

    def apply_rules(
        self,
        feature_values: dict[str, float],
        rules: list[dict[str, Any]],
    ) -> RCAResult:
        """
        Évalue les règles dans l'ordre de priorité (ascendant).
        Retourne le résultat de la première règle matchée.

        [GoF1994] — Chain of Responsibility : délégation jusqu'au premier
        handler capable de traiter la requête.

        Args:
            feature_values: dict {nom_feature: valeur} pour le dossier.
            rules: liste de règles issues de module.get_rca_rules().

        Returns:
            RCAResult avec diagnostic, ou RCAResult.indeterminate() si
            aucune règle ne matche.
        """
        if not rules:
            logger.debug("apply_rules — aucune règle fournie → indeterminate.")
            return RCAResult.indeterminate()

        if not feature_values:
            logger.warning("apply_rules — feature_values vide → indeterminate.")
            return RCAResult.indeterminate()

        # Tri par priorité ascendante (1 = évalué en premier)
        sorted_rules = sorted(rules, key=lambda r: int(r.get("priority", 99)))

        for rule in sorted_rules:
            rule_id = rule.get("id", "?")
            try:
                if evaluate_rule(rule, feature_values):
                    confidence = compute_confidence(rule, feature_values)
                    result = self._build_result(rule, confidence, feature_values)
                    logger.debug(
                        "RCA match : règle=%s, catégorie=%s, confiance=%.2f",
                        rule_id, result.category, confidence,
                    )
                    return result
            except Exception as exc:
                # Non-bloquant : une règle défectueuse ne doit pas arrêter le pipeline
                logger.warning(
                    "Erreur évaluation règle '%s' (ignorée) : %s", rule_id, exc
                )
                continue

        logger.debug(
            "apply_rules — aucune des %d règles ne matche → indeterminate.",
            len(sorted_rules),
        )
        return RCAResult.indeterminate()

    @staticmethod
    def _build_result(
        rule: dict[str, Any],
        confidence: float,
        feature_values: dict[str, float],
    ) -> RCAResult:
        """
        Construit un RCAResult à partir d'une règle matchée.

        Args:
            rule: règle matchée.
            confidence: confiance calculée par compute_confidence().
            feature_values: valeurs des features (pour enrichir le contexte).

        Returns:
            RCAResult instancié.
        """
        # Résumé des features ayant déclenché la règle
        triggered_features = {
            cond["feature"]: feature_values.get(cond["feature"])
            for cond in rule.get("conditions", [])
            if cond.get("feature") in feature_values
        }

        return RCAResult(
            category=rule.get("category", "Indéterminé"),
            subcategory=rule.get("subcategory", ""),
            confidence=confidence,
            rule_id=rule.get("id"),
            message_template=rule.get("description", "").strip(),
        )

    def __repr__(self) -> str:
        return "RCAEngine(pattern=ChainOfResponsibility, stateless=True)"