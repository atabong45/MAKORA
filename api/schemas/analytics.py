"""
MODULE : api/schemas/analytics.py
DESCRIPTION : Schémas Pydantic v2 — Dashboard et analytics agrégées.

RÉFÉRENCES ACADÉMIQUES :
- [Sculley2015] Hidden Technical Debt in ML Systems — monitoring orienté
  entités opérationnelles (praticiens, régions) pour identifier les drifts
  comportementaux locaux. §3 slice-based monitoring.
- [Bauder2017] Bauder & Khoshgoftaar (2017). Medicare fraud detection using
  machine learning methods. ICMLA. → §4 analyse par prestataire.
- [Chandola2009] Anomaly Detection: A Survey. §6.5 — l'analyse contextuelle
  par sous-population (région) révèle des anomalies invisibles globalement.

DÉCISIONS DE CONCEPTION :
- PractitionerWatchlistItem expose le hash COMPLET (pseudonymisé SHA-256).
  L'UI tronque à 8 caractères pour l'affichage compact.
- score_trend / level : seuils ±0.05 / 0.04 / 0.08 — heuristiques opérationnelles.
- RegionalAnomalyItem : toutes les 10 régions camerounaises sont
  systématiquement retournées (level="no_data" si claim_count=0).
"""
from typing import Literal
from pydantic import BaseModel


class DashboardStats(BaseModel):
    period_days: int
    total_analyzed: int
    anomaly_count: int
    anomaly_rate: float
    pending_decisions: int
    confirmed_fraud: int
    rejected: int
    escalated: int
    by_branch: dict[str, dict]
    drift_alerts: dict[str, str]


class ShapTopFeature(BaseModel):
    feature_name: str
    avg_shap: float
    count: int
    positive_ratio: float


class RcaDistributionItem(BaseModel):
    category: str
    count: int
    percentage: float


class ModelPerformanceRow(BaseModel):
    model_id: str
    branch: str
    algorithm: str
    version_tag: str
    f1_score: float | None
    auc_roc: float | None
    mcc: float | None
    fpr: float | None
    is_production: bool


# ─────────────────────────────────────────────────────────────────────
# Gap #4 — Praticiens à surveiller (Étape 6)
# ─────────────────────────────────────────────────────────────────────

ScoreTrend = Literal["up", "down", "stable"]


class PractitionerWatchlistItem(BaseModel):
    """
    Praticien identifié comme à surveiller sur une période donnée.

    Référence : [Bauder2017] §4 — l'unité d'investigation en fraude santé
    est le prestataire (NPI / id_hash chez MAKORA).
    """

    practitioner_hash: str
    """Hash SHA-256 du praticien (64 chars, pseudonymisé)."""

    specialty: str | None
    """Spécialité médicale (None si non renseignée)."""

    region: str | None
    """Région camerounaise (10 régions ASAC, None si non renseignée)."""

    branch: str
    """Branche du sinistre : 'sante' ou 'auto'."""

    claims_count: int
    """Nombre de claims distincts sur la période."""

    anomaly_count: int
    """Nombre d'analyses ayant déclenché is_anomaly=True."""

    avg_anomaly_score: float
    """Score d'anomalie moyen sur la période (0.0 à 1.0)."""

    score_trend: ScoreTrend
    """
    Tendance vs période précédente (même longueur) :
    - "up"     : delta > +0.05 (plus suspect)
    - "down"   : delta < -0.05 (moins suspect)
    - "stable" : |delta| ≤ 0.05 ou pas de données N-1
    """


# ─────────────────────────────────────────────────────────────────────
# Gap #5 — Focus régional Cameroun (Étape 7)
# ─────────────────────────────────────────────────────────────────────

RegionalLevel = Literal["high", "medium", "low", "no_data"]


class RegionalAnomalyItem(BaseModel):
    """
    Statistiques d'anomalies par région camerounaise.

    Référence : [Chandola2009] §6.5 — l'analyse contextuelle par
    sous-population (région) révèle des anomalies invisibles globalement.

    Stratégie de mapping (pas de claims.region en DB) :
    - Claims santé : claim_lines.praticien_id_hash → practitioners.region
    - Claims auto  : claim_lines.garage_id_hash → garages.ville → région
    """

    region: str
    """Nom officiel d'une des 10 régions ASAC du Cameroun."""

    claim_count: int
    """Nombre total de claims distincts sur la période."""

    anomaly_count: int
    """Nombre d'analyses is_anomaly=True sur la période."""

    anomaly_rate: float
    """Taux d'anomalie (anomaly_count / claim_count), 0 si pas de claims."""

    level: RegionalLevel
    """
    Niveau d'alerte régional :
    - "high"    : anomaly_rate > 0.08
    - "medium"  : 0.04 < anomaly_rate <= 0.08
    - "low"     : 0 < anomaly_rate <= 0.04
    - "no_data" : claim_count == 0
    """

    branch_breakdown: dict[str, int]
    """
    Décomposition par branche : {"sante": N, "auto": M}.
    Permet à l'UI de comprendre la nature du risque régional.
    """