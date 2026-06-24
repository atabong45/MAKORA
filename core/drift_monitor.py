"""
MODULE : core/drift_monitor.py
DESCRIPTION : Surveillance du drift de distribution des features par module.
              Implémente le PSI (Population Stability Index) sur fenêtre
              glissante configurable. Générique — aucune dépendance à un
              module métier concret.

RÉFÉRENCES ACADÉMIQUES :
- [Gama2014] Gama et al. (2014). A survey on concept drift adaptation.
  ACM Computing Surveys, 46(4), 1-37.
  → Justifie la nécessité de détecter le drift de distribution en production.
  → Le PSI est l'indicateur standard du domaine bancaire/assurance,
    recommandé comme baseline par Gama pour les variables continues.

- [Sculley2015] Sculley et al. (2015). Hidden technical debt in ML systems.
  NeurIPS 2015.
  → Justifie l'intégration du monitoring dans le pipeline dès la conception
    (anti-pattern "data slums" évité).

DÉCISIONS DE CONCEPTION :
- PSI en 10 bins (standard industrie assurance/bancaire [Gama2014]).
- Seuils PSI externalisés dans YAML : warning=0.10, critical=0.20
  — pas de valeurs hardcodées dans ce fichier.
- Granularité feature : le statut MODULE = max(statuts features).
- `reference_window_days` et `current_window_days` extraits du YAML.
- La détection ne bloque pas le pipeline : retourne un DriftReport
  enrichissant MAKORAOutput.drift_warning (décision API-001).
- Colonne de date configurable (défaut "Batch_Date") — présente dans
  les deux datasets v1 (Santé + Auto).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES PSI — standard industrie assurance [Gama2014]
# ─────────────────────────────────────────────────────────────────────────────
_PSI_BINS = 10
_EPSILON = 1e-6          # évite log(0) dans la formule PSI
_DEFAULT_WARNING = 0.10
_DEFAULT_CRITICAL = 0.20
_DEFAULT_REF_DAYS = 90
_DEFAULT_CUR_DAYS = 30
_DEFAULT_DATE_COL = "Batch_Date"
_MIN_SAMPLES = 30        # en dessous, PSI non fiable → statut UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class FeatureDrift:
    """Résultat PSI pour une feature individuelle."""
    feature: str
    psi: float
    status: str          # STABLE | WARNING | CRITICAL | UNKNOWN
    n_reference: int
    n_current: int


@dataclass
class DriftReport:
    """Rapport de drift complet pour un module à un instant donné."""
    branch: str
    computed_at: datetime
    status: str                                  # statut global = max(features)
    features: dict[str, FeatureDrift] = field(default_factory=dict)
    reference_window_days: int = _DEFAULT_REF_DAYS
    current_window_days: int = _DEFAULT_CUR_DAYS

    def to_dict(self) -> dict:
        return {
            "branch": self.branch,
            "computed_at": self.computed_at.isoformat(),
            "status": self.status,
            "reference_window_days": self.reference_window_days,
            "current_window_days": self.current_window_days,
            "features": {
                name: {
                    "psi": round(fd.psi, 6),
                    "status": fd.status,
                    "n_reference": fd.n_reference,
                    "n_current": fd.n_current,
                }
                for name, fd in self.features.items()
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# DRIFT MONITOR
# ─────────────────────────────────────────────────────────────────────────────

class DriftMonitor:
    """
    Surveillance du drift de distribution des features par PSI.

    Usage typique dans le pipeline :
        monitor = DriftMonitor(branch="sante", config=module.get_drift_config())
        monitor.fit_reference(df_train)
        report = monitor.compute(df_batch)
        if report.status != "STABLE":
            output.drift_warning = report.to_dict()

    [Gama2014] — le PSI mesure la différence de distribution entre une
    population de référence (train) et une population courante (batch).
    Formule :
        PSI = Σ (P_actual - P_expected) × ln(P_actual / P_expected)
    Interprétation :
        PSI < 0.10  → STABLE   (changement négligeable)
        PSI < 0.20  → WARNING  (changement modéré, surveiller)
        PSI >= 0.20 → CRITICAL (changement majeur, réentraîner)
    """

    def __init__(
        self,
        branch: str,
        config: dict,
        date_col: str = _DEFAULT_DATE_COL,
    ) -> None:
        """
        Args:
            branch: nom de la branche ("sante", "auto", ...)
            config: dict extrait de BaseModule.get_drift_config()
                    Clés attendues :
                      - features_to_monitor : List[str]
                      - reference_window_days : int (défaut 90)
                      - current_window_days   : int (défaut 30)
                      - thresholds.warning    : float (défaut 0.10)
                      - thresholds.critical   : float (défaut 0.20)
            date_col: colonne de date dans les DataFrames (défaut "Batch_Date")
        """
        self.branch = branch
        self.date_col = date_col

        self._features: list[str] = list(config.get("features_to_monitor", []))
        self._ref_days: int = int(
            config.get("reference_window_days", _DEFAULT_REF_DAYS)
        )
        self._cur_days: int = int(
            config.get("current_window_days", _DEFAULT_CUR_DAYS)
        )
        thresholds = config.get("thresholds", {})
        self._warn_thr: float = float(thresholds.get("warning", _DEFAULT_WARNING))
        self._crit_thr: float = float(thresholds.get("critical", _DEFAULT_CRITICAL))

        # Distributions de référence : {feature: (counts, edges)}
        self._reference: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        self._fitted = False

    # ─────────────────────────────────────────────────────────────
    # API PUBLIQUE
    # ─────────────────────────────────────────────────────────────

    def fit_reference(self, df: pd.DataFrame) -> None:
        """
        Calcule et mémorise les distributions de référence à partir du
        DataFrame d'entraînement (ou d'une fenêtre historique).

        Args:
            df: DataFrame contenant au moins les colonnes self._features.
        """
        self._reference = {}
        available = [f for f in self._features if f in df.columns]
        missing = [f for f in self._features if f not in df.columns]
        if missing:
            logger.warning(
                "[DriftMonitor:%s] Features absentes du df référence : %s",
                self.branch, missing,
            )
        for feat in available:
            series = df[feat].dropna()
            if len(series) < _MIN_SAMPLES:
                logger.warning(
                    "[DriftMonitor:%s] Référence trop petite pour '%s' (%d < %d)",
                    self.branch, feat, len(series), _MIN_SAMPLES,
                )
                continue
            counts, edges = self._build_histogram(series)
            self._reference[feat] = (counts, edges)

        self._fitted = bool(self._reference)
        logger.info(
            "[DriftMonitor:%s] Référence calculée sur %d features (%d lignes)",
            self.branch, len(self._reference), len(df),
        )

    def compute(
        self,
        df: pd.DataFrame,
        reference_date: Optional[datetime] = None,
    ) -> DriftReport:
        """
        Calcule le PSI de chaque feature surveillée et retourne un DriftReport.

        Si `reference_date` est fourni et que `date_col` est présente dans df,
        filtre df pour ne retenir que la fenêtre `current_window_days` précédant
        cette date. Sinon, utilise tout df.

        Args:
            df: DataFrame du batch courant.
            reference_date: date pivot pour le filtrage temporel (optionnel).

        Returns:
            DriftReport avec statut global et détail par feature.
        """
        if not self._fitted:
            logger.warning(
                "[DriftMonitor:%s] fit_reference() non appelé — rapport vide.",
                self.branch,
            )
            return DriftReport(
                branch=self.branch,
                computed_at=datetime.now(),
                status="UNKNOWN",
                reference_window_days=self._ref_days,
                current_window_days=self._cur_days,
            )

        df_current = self._filter_window(df, reference_date)
        feature_results: dict[str, FeatureDrift] = {}

        for feat, (ref_counts, ref_edges) in self._reference.items():
            if feat not in df_current.columns:
                feature_results[feat] = FeatureDrift(
                    feature=feat, psi=0.0, status="UNKNOWN",
                    n_reference=int(ref_counts.sum()), n_current=0,
                )
                continue

            series = df_current[feat].dropna()
            if len(series) < _MIN_SAMPLES:
                feature_results[feat] = FeatureDrift(
                    feature=feat, psi=0.0, status="UNKNOWN",
                    n_reference=int(ref_counts.sum()), n_current=len(series),
                )
                continue

            cur_counts = self._apply_histogram(series, ref_edges)
            psi = self._psi_formula(ref_counts, cur_counts)
            status = self._classify(psi)

            feature_results[feat] = FeatureDrift(
                feature=feat,
                psi=round(psi, 6),
                status=status,
                n_reference=int(ref_counts.sum()),
                n_current=len(series),
            )

        global_status = self._aggregate_status(feature_results)
        report = DriftReport(
            branch=self.branch,
            computed_at=datetime.now(),
            status=global_status,
            features=feature_results,
            reference_window_days=self._ref_days,
            current_window_days=self._cur_days,
        )
        logger.info(
            "[DriftMonitor:%s] Drift = %s (features: %s)",
            self.branch,
            global_status,
            {k: v.status for k, v in feature_results.items()},
        )
        return report

    def update_reference(self, df: pd.DataFrame) -> None:
        """
        Remplace la distribution de référence par la distribution du df fourni.
        Appelé après un réentraînement validé (F1 nouveau >= F1 ancien).
        """
        self.fit_reference(df)
        logger.info(
            "[DriftMonitor:%s] Référence mise à jour (%d lignes).",
            self.branch, len(df),
        )

    @property
    def is_fitted(self) -> bool:
        return self._fitted

    @property
    def monitored_features(self) -> list[str]:
        return list(self._features)

    # ─────────────────────────────────────────────────────────────
    # MÉTHODES INTERNES
    # ─────────────────────────────────────────────────────────────

    def _psi_formula(
        self,
        expected: np.ndarray,
        actual: np.ndarray,
    ) -> float:
        """
        PSI = sum((actual_i - expected_i) * ln(actual_i / expected_i))

        [Gama2014] — formule standard industrie.
        Les proportions sont normalisées et clippées à _EPSILON pour éviter
        log(0) sur les bins vides.
        """
        exp_pct = expected / (expected.sum() + _EPSILON)
        act_pct = actual / (actual.sum() + _EPSILON)
        exp_pct = np.clip(exp_pct, _EPSILON, None)
        act_pct = np.clip(act_pct, _EPSILON, None)
        return float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))

    def _build_histogram(
        self, series: pd.Series
    ) -> tuple[np.ndarray, np.ndarray]:
        """Construit l'histogramme de référence (counts + edges)."""
        counts, edges = np.histogram(series, bins=_PSI_BINS)
        return counts.astype(float), edges

    def _apply_histogram(
        self, series: pd.Series, edges: np.ndarray
    ) -> np.ndarray:
        """Applique les bin edges de référence à la série courante."""
        counts, _ = np.histogram(series, bins=edges)
        return counts.astype(float)

    def _classify(self, psi: float) -> str:
        """Classifie un PSI en statut selon les seuils YAML [Gama2014]."""
        if psi >= self._crit_thr:
            return "CRITICAL"
        if psi >= self._warn_thr:
            return "WARNING"
        return "STABLE"

    def _aggregate_status(
        self, features: dict[str, FeatureDrift]
    ) -> str:
        """
        Statut global = max(statuts features).
        CRITICAL > WARNING > UNKNOWN > STABLE.
        Un seul feature CRITICAL suffit à mettre le module en CRITICAL.
        """
        priority = {"CRITICAL": 3, "WARNING": 2, "UNKNOWN": 1, "STABLE": 0}
        if not features:
            return "UNKNOWN"
        top = max(features.values(), key=lambda fd: priority.get(fd.status, 0))
        return top.status

    def _filter_window(
        self,
        df: pd.DataFrame,
        reference_date: Optional[datetime],
    ) -> pd.DataFrame:
        """
        Filtre df pour ne retenir que la fenêtre current_window_days.
        Si date_col absent ou reference_date non fourni, retourne df entier.
        """
        if reference_date is None or self.date_col not in df.columns:
            return df
        try:
            dates = pd.to_datetime(df[self.date_col], errors="coerce")
            cutoff = reference_date - timedelta(days=self._cur_days)
            mask = (dates >= cutoff) & (dates <= reference_date)
            filtered = df[mask]
            if filtered.empty:
                logger.warning(
                    "[DriftMonitor:%s] Fenêtre courante vide (ref=%s, days=%d) "
                    "— utilisation du df entier.",
                    self.branch, reference_date.date(), self._cur_days,
                )
                return df
            return filtered
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "[DriftMonitor:%s] Erreur filtrage temporel : %s — df entier.",
                self.branch, exc,
            )
            return df