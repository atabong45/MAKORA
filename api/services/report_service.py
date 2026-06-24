"""
MODULE : api/services/report_service.py
DESCRIPTION : Service exports rapports (BF-10 CDC) — CSV, XLSX, JSON.
Export async via BackgroundTasks pour gros volumes (> 1000 lignes).
"""
import csv
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from api.config import get_settings
from api.schemas.reports import ExportRequest

settings = get_settings()


def create_export_request(db: Session, data: ExportRequest, requested_by: UUID):
    from core.db.models.monitoring import ExportReport
    report = ExportReport(
        requested_by=requested_by, report_type=data.report_type,
        branch_filter=data.branch_filter, decision_filter=data.decision_filter,
        date_from=data.date_from, date_to=data.date_to,
        file_format=data.file_format, status="PENDING",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def generate_export(db: Session, report_id: UUID) -> None:
    """Génération synchrone — appelé en BackgroundTask pour gros exports."""
    from core.db.models.monitoring import ExportReport
    from core.db.models.pipeline import Analysis
    report = db.query(ExportReport).filter(ExportReport.id == report_id).first()
    if not report:
        return
    report.status = "GENERATING"
    db.commit()
    try:
        q = db.query(Analysis)
        if report.decision_filter:
            q = q.filter(Analysis.decision_status == report.decision_filter)
        analyses = q.limit(50000).all()
        rows = [{"id": str(a.id), "anomaly_score": a.anomaly_score, "is_anomaly": a.is_anomaly,
                 "rca_category": a.rca_category, "decision_status": a.decision_status,
                 "created_at": str(a.created_at)} for a in analyses]
        export_dir = Path(settings.MAKORA_EXPORTS_PATH)
        export_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
        if report.file_format == "json":
            filepath = export_dir / f"export_{ts}.json"
            filepath.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            filepath = export_dir / f"export_{ts}.csv"
            if rows:
                buf = io.StringIO()
                writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
                filepath.write_text(buf.getvalue(), encoding="utf-8")
        report.file_path = str(filepath.relative_to(settings.MAKORA_EXPORTS_PATH))
        report.row_count = len(rows)
        report.status = "READY"
        report.completed_at = datetime.now(tz=timezone.utc)
    except Exception as e:
        report.status = "FAILED"
    db.commit()


def get_export(db: Session, report_id: UUID, user_id: UUID):
    from core.db.models.monitoring import ExportReport
    report = db.query(ExportReport).filter(ExportReport.id == report_id, ExportReport.requested_by == user_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Export introuvable")
    return report


def download_export(db: Session, report_id: UUID, user_id: UUID) -> tuple[bytes, str, str]:
    report = get_export(db, report_id, user_id)
    if report.status != "READY":
        raise HTTPException(status_code=202, detail=f"Export en cours : {report.status}")
    filepath = Path(settings.MAKORA_EXPORTS_PATH) / report.file_path
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="Fichier export introuvable")
    mime = "application/json" if report.file_format == "json" else "text/csv"
    return filepath.read_bytes(), mime, filepath.name


def list_my_exports(db: Session, user_id: UUID, offset: int, limit: int):
    from core.db.models.monitoring import ExportReport
    q = db.query(ExportReport).filter(ExportReport.requested_by == user_id).order_by(ExportReport.created_at.desc())
    total = q.count()
    return total, q.offset(offset).limit(limit).all()




def get_global_stats(db, period_days: int) -> dict:
    """
    Stats globales pour /reports/stats/global.
    Produit la forme `GlobalStats` complète, dont le time_series quotidien
    nécessaire au widget Timeline du dashboard.

    Référence : [Sculley2015] — l'observabilité opérationnelle des pipelines ML
    impose un suivi temporel des taux d'anomalie.
    """
    from datetime import datetime, timedelta, timezone, date as _date
    from collections import defaultdict
    from sqlalchemy import func
    from core.db.models.pipeline import Analysis
    from core.db.models.referentiels import Branch

    since = datetime.now(tz=timezone.utc) - timedelta(days=period_days)

    # Totaux globaux
    total = db.query(Analysis).filter(Analysis.created_at >= since).count()
    anomalies = db.query(Analysis).filter(
        Analysis.created_at >= since, Analysis.is_anomaly == True
    ).count()
    avg_score_row = db.query(func.avg(Analysis.anomaly_score)).filter(
        Analysis.created_at >= since
    ).scalar()

    # Time series quotidien — fenêtre roulante sur period_days
    daily_rows = db.query(
        func.date(Analysis.created_at).label("d"),
        func.count().label("total"),
        func.sum(func.cast(Analysis.is_anomaly, __import__("sqlalchemy").Integer)).label("anom"),
    ).filter(Analysis.created_at >= since).group_by(func.date(Analysis.created_at)).all()

    by_date = {r.d: (r.total or 0, r.anom or 0) for r in daily_rows}
    time_series = []
    today = datetime.now(tz=timezone.utc).date()
    for i in range(period_days, -1, -1):
        d = today - timedelta(days=i)
        tot, anom = by_date.get(d, (0, 0))
        time_series.append({
            "date": d.isoformat(),
            "total_analyzed": int(tot),
            "anomaly_count": int(anom),
        })

    # By branch — JOIN avec Branch pour avoir le code lisible
    branch_rows = db.query(
        Branch.code, func.count(Analysis.id), func.sum(func.cast(Analysis.is_anomaly, __import__("sqlalchemy").Integer))
    ).join(Branch, Analysis.branch_id == Branch.id).filter(
        Analysis.created_at >= since
    ).group_by(Branch.code).all()

    by_branch = {}
    for code, t, a in branch_rows:
        t = int(t or 0); a = int(a or 0)
        by_branch[code] = {
            "total_analyzed": t, "anomaly_count": a,
            "anomaly_rate": round(a / t, 4) if t else 0.0,
        }

    # By RCA category
    rca_rows = db.query(
        Analysis.rca_category, func.count().label("cnt")
    ).filter(
        Analysis.created_at >= since, Analysis.rca_category != None
    ).group_by(Analysis.rca_category).order_by(func.count().desc()).all()
    rca_total = sum(r.cnt for r in rca_rows) or 1
    by_rca_category = [
        {"category": r.rca_category, "count": r.cnt,
         "percentage": round(r.cnt / rca_total * 100, 1)}
        for r in rca_rows
    ]

    return {
        "total_dossiers": total,
        "anomaly_rate": round(anomalies / total, 4) if total else 0.0,
        "avg_anomaly_score": round(float(avg_score_row or 0.0), 4),
        "by_branch": by_branch,
        "by_rca_category": by_rca_category,
        "time_series": time_series,
    }