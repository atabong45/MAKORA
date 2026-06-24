"""
MODULE : modules/sante/sante_module.py
DESCRIPTION : Module métier Santé pour MAKORA.
              Implémente BaseModule via le Plugin Contract YAML.
              Délègue le feature engineering aux 3 registres.

RÉFÉRENCES ACADÉMIQUES :
  [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection using
               machine learning methods. ICMLA.
               Features et contamination pour la santé (taux fraude 3-10%).
  [Chandola2009] Chandola et al. (2009). Anomaly Detection: A Survey.
                 ACM Computing Surveys.
                 Justification de l'approche non-supervisée dans un contexte
                 à labels rares (fraude < 10% des dossiers).
  [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML systems.
                NeurIPS. Séparation stricte feature engineering / logique
                métier. Ordre de calcul fait partie du contrat du pipeline.
  [Xu2023] Xu et al. (2023). Deep Isolation Forest for Anomaly Detection.
           IEEE TKDE. Module Santé contribue 13 features communes pour
           M_makora_dif, validant H0 [Caruana1997] sur le trade-off
           généricité/précision.

DÉCISIONS DE CONCEPTION :
  - Toute configuration (seuils, features, règles RCA) est lue depuis
    sante.yaml v0.5.0. Zéro paramètre hardcodé dans la classe. [Sculley2015]
  - engineer_features() est YAML-driven : itération des registres au lieu
    d'appels explicites. Ajouter une feature = YAML + registre, pas ce fichier.
  - validate_input() vérifie les colonnes métier UNIQUEMENT. Le schéma
    universel est validé séparément par schema_validator.py.
  - get_feature_names() retourne la liste issue du YAML, garantissant la
    cohérence YAML / code.
  - Les 3 registres respectent l'ordre de dépendance de calcul :
    V1 (ratio avant historique) -> V2 (features ext) -> V3 (features réseau).
    [Sculley2015] : l'ordre de calcul fait partie du contrat du pipeline.

CHANGEMENTS v0.5.0 (Scénarios A+B+C) :
  - Import : FEATURE_FUNCTIONS_SANTE_V1 au lieu des 5 imports explicites
  - engineer_features() : 3 boucles d'itération YAML-driven
  - 20 features (was 17) dont 13 communes avec AutoModule [Xu2023]
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.base_module import BaseModule
from core.logging_config import get_logger
from core.mercuriale.loader import MercurialeLoader
from core.plugin_registry import PluginRegistry
from modules.sante.features import FEATURE_FUNCTIONS_SANTE_V1
from modules.sante.features_ext import FEATURE_EXT_FUNCTIONS
from modules.sante.features_reseau import FEATURE_RESEAU_FUNCTIONS_SANTE

logger = get_logger(__name__)


@PluginRegistry.register("sante")
class SanteModule(BaseModule):
    """
    Module Santé MAKORA — détection d'anomalies sur sinistres santé.

    Couvre flux ASAC camerounais et scans documentaires (mercuriale CIMA).
    Patterns couverts : upcoding, phantom billing, unbundling, fraude
    documentaire, fraude fréquence, saisie hors heures, fraude en réseau
    praticien-assuré, doublons de soumission, acte incomplet, document périmé.

    Version : 0.5.0 — 20 features dont 13 communes avec AutoModule.
    Contamination calibrée : 0.068 (T10.3, [Bauder2017] taux fraude 3-10%).

    [Bauder2017] : features de concentration et de doublons sont les signaux
    les plus robustes de fraude Medicare.
    [Xu2023] : M_makora_dif exploite les 13 features communes Santé/Auto
    pour valider H0 [Caruana1997] sur le trade-off généricité/précision.
    """

    branch: str = "sante"

    def __init__(self, config_path: Path | None = None) -> None:
        super().__init__(config_path=config_path)
        self._mercuriale_index = self._load_mercuriale()

    # ------------------------------------------------------------------
    # Chargement barème mercuriale
    # ------------------------------------------------------------------

    def _load_mercuriale(self) -> Any:
        """
        Charge le barème mercuriale CIMA depuis la config YAML.

        Dégradation gracieuse : si le barème est absent ou invalide,
        retourne None et logue un avertissement. Le pipeline continue
        en mode dégradé (ratio calculé depuis Montant_Reference_Mercuriale).

        [Sculley2015] : isoler les dépendances externes pour éviter les
        pannes en cascade.
        """
        mercu_config = self.config.get("mercuriale", {})
        if not mercu_config:
            logger.debug("SanteModule — aucune mercuriale configurée dans sante.yaml.")
            return None

        path = Path(mercu_config.get("path", ""))
        if not path.exists():
            logger.warning(
                "SanteModule — barème mercuriale introuvable : %s. "
                "Dégradation vers colonne Montant_Reference_Mercuriale.",
                path,
            )
            return None

        try:
            loader = MercurialeLoader.from_module_config(
                config=mercu_config,
                branch=self.branch,
                base_path=Path("."),
            )
            self._mercuriale_index = loader.index
            logger.info(
                "SanteModule — barème chargé : %d codes ASAC (tolérance +/-%s%%)",
                loader.index.size,
                mercu_config.get("tolerance_pct", 10),
            )
            return loader.index
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "SanteModule — échec chargement barème (%s). "
                "Dégradation vers colonne Montant_Reference_Mercuriale.",
                exc,
            )
            return None

    # ------------------------------------------------------------------
    # Plugin Contract — méthodes abstraites
    # ------------------------------------------------------------------

    def get_feature_names(self) -> list[str]:
        """
        Retourne la liste ordonnée des 20 features du module Santé.
        Ordre stable défini dans sante.yaml v0.5.0, section 'features'.

        [Sculley2015] : l'ordre de calcul fait partie du contrat du pipeline.
        get_feature_names() garantit que train et inference utilisent le même
        ordre de colonnes.
        """
        return list(self.config.get("features", []))

    def engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calcule les 20 features du module Santé et les ajoute au DataFrame.

        Stratégie d'appel YAML-driven (ADR-002) :
          - V1 : itération FEATURE_FUNCTIONS_SANTE_V1
                 (ordre critique : ratio avant historique_ratio) [Sculley2015]
          - V2 : itération FEATURE_EXT_FUNCTIONS (features_ext.py)
          - V3 : itération FEATURE_RESEAU_FUNCTIONS_SANTE (features_reseau.py)

        Ajouter une feature = modifier sante.yaml + le registre correspondant.
        Ce fichier NE DOIT PAS être modifié pour ajouter une feature.

        13 features communes avec AutoModule pour M_makora_dif [Xu2023].

        Args:
            df: DataFrame normalisé (schéma universel ARGUS).

        Returns:
            DataFrame enrichi avec les 20 features ajoutées.
        """
        df = df.copy()

        # V1 — ordre dict garanti Python 3.7+ : ratio avant historique_ratio
        # [Sculley2015] : historique_ratio_praticien dépend de ratio_prix_mercuriale
        for feature_name, fn in FEATURE_FUNCTIONS_SANTE_V1.items():
            try:
                df[feature_name] = fn(df)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "SanteModule V1 — erreur calcul feature '%s' : %s "
                    "— valeur neutre 0 appliquée.",
                    feature_name, exc,
                )
                df[feature_name] = 0

        # V2 — features complémentaires (features_ext.py)
        for feature_name, fn in FEATURE_EXT_FUNCTIONS.items():
            try:
                df[feature_name] = fn(df)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "SanteModule V2 — erreur calcul feature '%s' : %s "
                    "— valeur neutre 0 appliquée.",
                    feature_name, exc,
                )
                df[feature_name] = 0

        # V3 — features réseau et doublons (features_reseau.py)
        # [Jiang2014] : community_score et prestataire_concentration sont
        # des signaux de fraude coordonnée calculés sur le batch courant.
        for feature_name, fn in FEATURE_RESEAU_FUNCTIONS_SANTE.items():
            try:
                df[feature_name] = fn(df)
            except Exception as exc:  # noqa: BLE001
                logger.error(
                    "SanteModule V3 — erreur calcul feature '%s' : %s "
                    "— valeur neutre 0 appliquée.",
                    feature_name, exc,
                )
                df[feature_name] = 0

        logger.debug(
            "SanteModule.engineer_features — %d lignes, features : %s",
            len(df),
            self.get_feature_names(),
        )
        return df

    def validate_input(self, df: pd.DataFrame) -> tuple[bool, list[str]]:
        """
        Vérifie les colonnes métier Santé UNIQUEMENT.

        Le schéma universel (Dossier_ID, Montant_Facture, etc.) est validé
        séparément par schema_validator.py avant cet appel.

        Returns:
            (valid: bool, errors: list[str])
        """
        # APRÈS
        if df is None or (hasattr(df, "empty") and df.empty):
            return False, ["DataFrame vide ou None"]

        errors: list[str] = []
        required_sante = (
            self.config
            .get("input_schema", {})
            .get("required_columns", [])
        )

        for col in required_sante:
            if col not in df.columns:
                errors.append(f"Colonne requise manquante : '{col}'")

        if errors:
            logger.warning(
                "SanteModule.validate_input — %d erreurs : %s",
                len(errors), errors,
            )
            return False, errors

        return True, []

    def get_rca_rules(self) -> list[dict]:
        """
        Retourne les règles RCA depuis sante.yaml.
        Pattern Chain of Responsibility [GoF1994] — première règle matchée.
        """
        return list(self.config.get("rca_rules", []))

    def get_source_mapping(self, source_key: str) -> dict[str, str]:
        """
        Retourne le mapping colonne source -> colonne universelle
        pour la clé source donnée.
        """
        mappings = self.config.get("source_mappings", {})
        if source_key not in mappings:
            logger.warning(
                "Source mapping '%s' introuvable dans sante.yaml — mapping vide.",
                source_key,
            )
            return {}
        return dict(mappings[source_key])

    # ------------------------------------------------------------------
    # Représentation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"SanteModule("
            f"branch={self.branch!r}, "
            f"features={len(self.get_feature_names())}, "
            f"rca_rules={len(self.get_rca_rules())})"
        )