"""
MODULE : core/normalizer.py
DESCRIPTION : Normalisation post-mapping — devises, encodage catégoriel,
              imputation des valeurs manquantes, log-transform.

RÉFÉRENCES ACADÉMIQUES :
- [Garcia2016] García et al. (2016). Big data preprocessing. Springer.
  → Justifie la séquence imputation → encodage → transformation.
- [Liu2008] Liu et al. (2008). Isolation Forest.
  → L'IF est sensible aux features à très grande dynamique → log-transform
    recommandé sur les montants.

DÉCISIONS DE CONCEPTION :
- Conversion XAF → EUR via Taux_Change présent dans la ligne (pas via API
  externe — reproductibilité scientifique exigée).
- Imputation par médiane (numérique) / mode (catégoriel) — [Garcia2016].
- Encodage one-hot pour les catégorielles à faible cardinalité (<10),
  label-encoding sinon. Pas de target-encoding (data leakage).
- Toutes les colonnes calculées sont préfixées par "_norm_" pour ne pas
  écraser les originales (auditabilité).
"""

from __future__ import annotations
from typing import Iterable
import numpy as np
import pandas as pd

from core.exceptions import NormalizationError
from core.logging_config import get_logger

logger = get_logger(__name__)


# Constantes — alignées sur GLOSSAIRE.md
TAUX_EUR_XAF_FALLBACK: float = 655.957
SUPPORTED_CURRENCIES: tuple[str, ...] = ("EUR", "XAF", "USD")
LOW_CARDINALITY_THRESHOLD: int = 10


class Normalizer:
    """
    Normalisation déterministe d'un DataFrame au schéma universel.

    Pipeline standard :
        1. handle_missing()    — impute valeurs manquantes
        2. normalize_currency() — convertit toutes les devises en EUR
        3. encode_categoricals() — encode les variables catégorielles
        4. log_transform()     — transforme log1p les montants
    """

    def __init__(self, target_currency: str = "EUR") -> None:
        if target_currency not in SUPPORTED_CURRENCIES:
            raise NormalizationError(
                f"Devise cible non supportée : {target_currency}. "
                f"Supportées : {SUPPORTED_CURRENCIES}",
                payload={"target_currency": target_currency},
            )
        self.target_currency = target_currency

    # ────────────────────────────────────────────────────────────────
    # 1. IMPUTATION
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def handle_missing(
        df: pd.DataFrame,
        *,
        numeric_strategy: str = "median",
        categorical_strategy: str = "mode",
        flag_imputed: bool = True,
    ) -> pd.DataFrame:
        """
        Impute les valeurs manquantes.

        Args:
            df: DataFrame à traiter.
            numeric_strategy: 'median' | 'mean' | 'zero'.
            categorical_strategy: 'mode' | 'constant'.
            flag_imputed: si True, ajoute une colonne booléenne _was_imputed.

        Returns:
            DataFrame sans NaN dans les colonnes traitées.
        """
        if df is None or df.empty:
            raise NormalizationError(
                "DataFrame vide.",
                payload={"n_rows": 0 if df is None else len(df)},
            )

        result = df.copy()
        if flag_imputed:
            result["_was_imputed"] = result.isna().any(axis=1)

        n_imputed_total = 0
        for col in result.columns:
            if col == "_was_imputed":
                continue
            n_na = result[col].isna().sum()
            if n_na == 0:
                continue

            if pd.api.types.is_numeric_dtype(result[col]):
                if numeric_strategy == "median":
                    fill = result[col].median()
                elif numeric_strategy == "mean":
                    fill = result[col].mean()
                elif numeric_strategy == "zero":
                    fill = 0
                else:
                    raise NormalizationError(
                        f"numeric_strategy inconnue : {numeric_strategy}",
                        payload={"strategy": numeric_strategy},
                    )
                # Médiane sur colonne entièrement NaN → 0
                if pd.isna(fill):
                    fill = 0
                result[col] = result[col].fillna(fill)
            else:
                if categorical_strategy == "mode":
                    mode_vals = result[col].mode(dropna=True)
                    fill = mode_vals.iloc[0] if not mode_vals.empty else "UNKNOWN"
                elif categorical_strategy == "constant":
                    fill = "UNKNOWN"
                else:
                    raise NormalizationError(
                        f"categorical_strategy inconnue : {categorical_strategy}",
                        payload={"strategy": categorical_strategy},
                    )
                result[col] = result[col].fillna(fill)

            n_imputed_total += int(n_na)

        if n_imputed_total > 0:
            logger.info(
                "Imputation effectuée : %d valeur(s) manquante(s) remplie(s).",
                n_imputed_total,
            )
        return result

    # ────────────────────────────────────────────────────────────────
    # 2. DEVISE
    # ────────────────────────────────────────────────────────────────

    def normalize_currency(
        self,
        df: pd.DataFrame,
        amount_columns: Iterable[str] = ("Montant_Facture",),
        currency_column: str = "Devise",
        rate_column: str = "Taux_Change",
    ) -> pd.DataFrame:
        """
        Convertit tous les montants vers la devise cible.

        Règle : montant_EUR = montant_origine / Taux_Change si devise != EUR.
        Le Taux_Change doit être présent dans le DataFrame (saisi à
        l'ingestion — reproductibilité scientifique).

        Args:
            df: DataFrame.
            amount_columns: colonnes de montants à convertir.
            currency_column: nom de la colonne devise.
            rate_column: nom de la colonne taux de change.

        Returns:
            DataFrame avec colonnes _norm_<col> ajoutées (montants en EUR).
        """
        if currency_column not in df.columns:
            raise NormalizationError(
                f"Colonne devise '{currency_column}' absente.",
                payload={"received_columns": list(df.columns)},
            )

        result = df.copy()
        # Si Taux_Change absent, on utilise le fallback pour XAF
        if rate_column not in result.columns:
            logger.warning(
                "Colonne '%s' absente — utilisation du taux fallback XAF=%.3f",
                rate_column, TAUX_EUR_XAF_FALLBACK,
            )
            result[rate_column] = result[currency_column].map(
                {"EUR": 1.0, "XAF": TAUX_EUR_XAF_FALLBACK, "USD": 1.0}
            ).fillna(1.0)

        # Validation des devises
        unknown = set(result[currency_column].dropna().unique()) - set(SUPPORTED_CURRENCIES)
        if unknown:
            raise NormalizationError(
                f"Devises inconnues : {unknown}",
                payload={"unknown_currencies": list(unknown)},
            )

        for col in amount_columns:
            if col not in result.columns:
                logger.warning("Colonne montant '%s' absente — ignorée.", col)
                continue
            # Conversion : EUR direct, XAF → EUR via taux
            result[f"_norm_{col}"] = np.where(
                result[currency_column] == self.target_currency,
                result[col],
                result[col] / result[rate_column].replace(0, np.nan),
            )

        logger.info(
            "Devises normalisées vers %s : colonnes %s",
            self.target_currency, list(amount_columns),
        )
        return result

    # ────────────────────────────────────────────────────────────────
    # 3. ENCODAGE CATÉGORIEL
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def encode_categoricals(
        df: pd.DataFrame,
        columns: Iterable[str] | None = None,
        *,
        low_cardinality_threshold: int = LOW_CARDINALITY_THRESHOLD,
    ) -> pd.DataFrame:
        """
        Encode les variables catégorielles.

        - cardinalité ≤ threshold → one-hot encoding
        - cardinalité  > threshold → label encoding (entier ordinal)

        Args:
            df: DataFrame.
            columns: colonnes à encoder. Si None, détection auto (dtype object).
            low_cardinality_threshold: seuil one-hot vs label encoding.

        Returns:
            DataFrame avec colonnes encodées (originales conservées).
        """
        result = df.copy()
        if columns is None:
            columns = [
                c for c in result.columns
                if result[c].dtype == "object"
                and not c.startswith("_")
                and not c.startswith("ID_")  # IDs jamais encodés
                and not c.startswith("Hash_")
            ]

        for col in columns:
            if col not in result.columns:
                continue
            n_unique = result[col].nunique(dropna=True)
            if n_unique <= 1:
                continue  # colonne constante — inutile
            if n_unique <= low_cardinality_threshold:
                dummies = pd.get_dummies(
                    result[col], prefix=f"_enc_{col}", dtype=int,
                )
                result = pd.concat([result, dummies], axis=1)
            else:
                # Label encoding déterministe (ordre alphabétique)
                cats = sorted(result[col].dropna().unique().tolist())
                mapping = {v: i for i, v in enumerate(cats)}
                result[f"_enc_{col}"] = result[col].map(mapping).fillna(-1).astype(int)

        return result

    # ────────────────────────────────────────────────────────────────
    # 4. LOG-TRANSFORM
    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def log_transform(
        df: pd.DataFrame,
        columns: Iterable[str],
    ) -> pd.DataFrame:
        """
        Applique log1p(x) sur les colonnes monétaires pour réduire
        la dynamique (recommandé pour Isolation Forest — [Liu2008]).

        Args:
            df: DataFrame.
            columns: colonnes à transformer.

        Returns:
            DataFrame avec colonnes _log_<col> ajoutées.
        """
        result = df.copy()
        for col in columns:
            if col not in result.columns:
                logger.warning("Colonne '%s' absente — log_transform ignoré.", col)
                continue
            if not pd.api.types.is_numeric_dtype(result[col]):
                logger.warning("Colonne '%s' non numérique — log_transform ignoré.", col)
                continue
            # log1p garantit pas d'erreur sur 0, on clip les négatifs à 0
            result[f"_log_{col}"] = np.log1p(result[col].clip(lower=0))
        return result