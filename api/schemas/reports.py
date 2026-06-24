"""
MODULE : api/schemas/reports.py
DESCRIPTION : Schémas Pydantic v2 — Exports et rapports (BF-10 CDC).
"""
from datetime import date, datetime
from uuid import UUID
from typing import Literal
from pydantic import BaseModel


class ExportRequest(BaseModel):
    report_type: Literal[
        "audit_decisions", "anomaly_summary",
        "drift_history", "community_fraud"
    ] = "audit_decisions"
    file_format: Literal["csv", "xlsx", "json"] = "csv"
    branch_filter: str | None = None
    decision_filter: str | None = None
    date_from: date | None = None
    date_to: date | None = None


class ExportReportResponse(BaseModel):
    id: UUID
    report_type: str
    file_format: str
    branch_filter: str | None = None
    status: str
    row_count: int | None = None
    created_at: datetime
    completed_at: datetime | None = None
    model_config = {"from_attributes": True}


class GlobalStats(BaseModel):
    total_dossiers: int
    anomaly_rate: float
    avg_anomaly_score: float
    by_branch: dict[str, dict]
    by_rca_category: list[dict]
    time_series: list[dict]


class BranchStats(BaseModel):
    branch: str
    total_analyzed: int
    anomaly_rate: float
    avg_score: float
    fp_fn_rate: float | None = None
    top_features: list[dict]
    rca_distribution: list[dict]
    reference_metrics: dict | None = None
