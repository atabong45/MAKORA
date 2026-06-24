"""
MODULE : modules/auto/auto_module.py
DESCRIPTION : Module métier Auto pour MAKORA.
              Implémente le Plugin Contract (BaseModule) pour la détection
              d'anomalies sur sinistres auto, marchés France et Cameroun.

RÉFÉRENCES ACADÉMIQUES :
  [Viaene2002]  Viaene et al. (2002). Automobile insurance fraud detection.
                Journal of Risk and Insurance.
                Référence principale pour les features auto et la contamination.
  [Subudhi2017] Subudhi & Panigrahi (2017). Automobile insurance fraud detection.
                Journal of King Saud University.
                Complémentaire Viaene2002 sur ratio_devis_bareme et vehicule_sur_value.
  [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML. NeurIPS.
                Séparation stricte feature engineering / logique métier.
                Inspection de signature au lieu de hardcoding de noms.
  [Xu2023]      Xu et al. (2023). Deep Isolation Forest. IEEE TKDE.
                Module Auto contribue 13 features communes pour M_makora_dif,
                validant H0 [Caruana1997] sur le trade-off généricité/précision.

DÉCISIONS DE CONCEPTION :
  - Toute configuration (seuils, features, règles RCA) est lue depuis
    auto.yaml v1.2.0. Zéro paramètre hardcodé dans la classe. [Sculley2015]
  - engineer_features() utilise inspect.signature() pour détecter les
    fonctions nécessitant mercuriale_index — plus robuste qu'un check par nom.
    [Sculley2015] : évite la liste hardcodée qui deviendrait obsolète.
  - Fallback d'erreur universel : df[feature_name] = 0 (neutre pour IF/DIF).
    0 == False pour bool, 0 == 0.0 pour float — aucune liste à maintenir.
  - validate_input() vérifie les colonnes métier UNIQUEMENT.

CORRECTIONS v1.2.0 (Scénarios A+B+C) :
  1. Import mort supprimé : compute_ratio_devis_bareme n'est plus importé.
  2. Check par inspect.signature() au lieu de check par nom "ratio_devis_bareme".
  3. Fallback erreur universel = 0 (plus de liste booléenne hardcodée).
  21 features (was 15) dont 13 communes avec SanteModule [Xu2023].
"""
from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

import pandas as pd

from core.base_module import BaseModule
from core.logging_config import get_logger
from core.mercuriale.loader import MercurialeLoader
from core.plugin_registry import PluginRegistry
from modules.auto.features import FEATURE_FUNCTIONS          # Correction 1 : import mort supprimé
from modules.auto.features_reseau import FEATURE_RESEAU_FUNCTIONS_AUTO

logger = get_logger(__name__)


@PluginRegistry.register("auto")
class AutoModule(BaseModule):
    """
    Module Auto MAKORA — détection d'anomalies sur sinistres automobile.

    Couvre flux France (numérique, EUR) et Cameroun (documentaire, XAF).
    Patterns couverts : staging accident, surfacturation réparation,
    véhicule sur-valorisé, falsification constat, collusion garagiste-assuré,
    fraude en réseau garage-expert, doublons de déclaration,
    sinistre weekend, acte incomplet, document périmé.

    Version : 1.2.0 — 21 features dont 13 communes avec SanteModule.
    Contamination calibrée : 0.068 (T10.3, [Viaene2002] taux fraude 3-10%).

    [Xu2023] : M_makora_dif exploite les 13 features communes Auto/Santé
    pour valider H0 [Caruana1997] sur le trade-off généricité/précision.
    """

    branch: str = "auto"

    def __init__(self, config_path: Path | None = None) -> None:
        super().__init__(config_path=config_path)
        self._mercuriale_index = self._load_mercuriale()

    # ------------------------------------------------------------------
    # Chargement barème ASAC Auto
    # ------------------------------------------------------------------

    def _load_mercuriale(self) -> Any:
        """
        Charge le barème ASAC Auto depuis la config YAML.

        Dégradation gracieuse : si le barème est absent ou invalide,
        retourne None et logue un avertissement. Le pipeline continue
        en utilisant Montant_Reference_Bareme si disponible.

        [Sculley2015] : isoler les dépendances externes pour éviter pannes
        en cascade.
        """
        mercu_config = self.config.get("mercuriale", {})
        if not mercu_config:
            logger.debug("AutoModule — aucune mercuriale configurée dans auto.yaml.")
            return None

        path = Path(mercu_config.get("path", ""))
        if not path.exists():
            logger.warning(
                "AutoModule — barème ASAC introuvable : %s. "
                "Dégradation vers colonne Montant_Reference_Bareme.",
                path,
            )
            return None

        try:
            loader = MercurialeLoader.from_module_config(
                config=mercu_config,
                branch=self.branch,
                base_path=Path("."),
            )
            logger.info(
                "AutoModule — barème chargé : %d codes ASAC (tolérance +/-%s%%)",
                loader.index.size,
                mercu_config.get("tolerance_pct", 10),
            )
            return loader.index
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "AutoModule — échec chargement barème (%s). "
                "Dégradation vers colonne Montant_Reference_Bareme.",
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Plugin Contract — méthodes abstraites
    # ------------------------------------------------------------------

    def get_feature_names(self) -> list[str]:
        """
        Retourne la liste ordonnée des 21 features du module Auto.
        Ordre stable défini dans auto.yaml v1.2.0, section 'features'.

        [Sculley2015] : l'ordre de calcul fait partie du contrat du pipeline.
        """
        return list(self.config.get("features", []))

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule les 21 features Auto et les ajoute au DataFrame.

        Stratégie d'appel :
          - V1 : itération FEATURE_FUNCTIONS (features.py)
                 Détection automatique de mercuriale_index via inspect.signature()
                 [Sculley2015] : plus robuste qu'un check par nom de feature.
          - V3 : itération FEATURE_RESEAU_FUNCTIONS_AUTO (features_reseau.py)

        Fallback erreur universel : df[feature_name] = 0
        [Sculley2015] : 0 est la valeur neutre universelle.
        0 == False pour bool, 0 == 0.0 pour float.
        Aucune liste hardcodée à maintenir.

        Args:
            df: DataFrame normalisé (schéma universel ARGUS).

        Returns:
            DataFrame enrichi avec les 21 features ajoutées.
        """
        df = df.copy()

        # V1 — Features principales (FEATURE_FUNCTIONS)
        for feature_name in self.get_feature_names():

            # Les features réseau sont gérées par FEATURE_RESEAU_FUNCTIONS_AUTO
            if feature_name in FEATURE_RESEAU_FUNCTIONS_AUTO:
                continue

            fn = FEATURE_FUNCTIONS.get(feature_name)
            if fn is None:
                logger.warning(
                    "AutoModule — feature '%s' déclarée dans auto.yaml "
                    "mais absente de FEATURE_FUNCTIONS — ignorée.",
                    feature_name,
                )
                continue

            try:
                # Correction 2 : inspect.signature() au lieu de check par nom
                # [Sculley2015] : robuste aux futurs renommages de features
                if "mercuriale_index" in inspect.signature(fn).parameters:
                    df[feature_name] = fn(df, mercuriale_index=self._mercuriale_index)
                else:
                    df[feature_name] = fn(df)

            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "AutoModule V1 — erreur calcul feature '%s' : %s "
                    "— valeur neutre 0 appliquée.",
                    feature_name, exc,
                )
                # Correction 3 : fallback universel 0 (plus de liste hardcodée)
                # [Sculley2015] : 0 == False (bool), 0 == 0.0 (float)
                df[feature_name] = 0

        # V3 — Features réseau (FEATURE_RESEAU_FUNCTIONS_AUTO)
        # [Jiang2014] : community_score et flag_doublon sont des signaux
        # de fraude coordonnée calculés sur le batch courant.
        for feature_name, fn in FEATURE_RESEAU_FUNCTIONS_AUTO.items():
            try:
                df[feature_name] = fn(df)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "AutoModule V3 — erreur calcul feature réseau '%s' : %s "
                    "— valeur neutre 0 appliquée.",
                    feature_name, exc,
                )
                df[feature_name] = 0

        logger.debug(
            "AutoModule.engineer_features — %d lignes, features : %s",
            len(df),
            self.get_feature_names(),
        )
        return df

    def validate_input(self, df: pd.DataFrame) -> tuple[bool, list[str]]:
        """
        Vérifie les colonnes métier Auto UNIQUEMENT.

        Lit required_columns depuis input_schema.required_columns (auto.yaml v1.2.0).
        Gère explicitement None et DataFrame vide.

        Returns:
            (valid: bool, errors: list[str])
        """
        if df is None or (hasattr(df, "empty") and df.empty):
            return False, ["DataFrame vide ou None"]

        errors: list[str] = []
        required_auto = (
            self.config
            .get("input_schema", {})
            .get("required_columns", [])
        )

        for col in required_auto:
            if col not in df.columns:
                errors.append(f"Colonne requise manquante : '{col}'")

        if errors:
            logger.warning(
                "AutoModule.validate_input — %d erreurs : %s",
                len(errors), errors,
            )
            return False, errors

        return True, []

    def get_rca_rules(self) -> list[dict]:
        """
        Retourne les règles RCA depuis auto.yaml.
        Pattern Chain of Responsibility [GoF1994].
        """
        return list(self.config.get("rca_rules", []))

    def get_source_mapping(self, source_key: str) -> dict[str, str]:
        """
        Retourne le mapping colonne source -> colonne universelle.
        """
        mappings = self.config.get("source_mappings", {})
        if source_key not in mappings:
            logger.warning(
                "Source mapping '%s' introuvable dans auto.yaml — mapping vide.",
                source_key,
            )
            return {}
        return dict(mappings[source_key])

    # ------------------------------------------------------------------
    # Représentation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        mercu_status = (
            f"{self._mercuriale_index.size} codes"
            if self._mercuriale_index is not None
            else "absent"
        )
        return (
            f"AutoModule("
            f"branch={self.branch!r}, "
            f"features={len(self.get_feature_names())}, "
            f"rca_rules={len(self.get_rca_rules())}, "
            f"mercuriale={mercu_status})"
        )