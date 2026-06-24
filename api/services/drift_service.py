"""
MODULE : api/services/drift_service.py
DESCRIPTION : Service drift — wrapping core/drift_monitor.py [Gama2014].
PSI seuils : STABLE<0.10 < WARNING<0.20 <= CRITICAL.
"""
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session


def get_all_status(db: Session) -> dict:
    from core.db.models.referentiels import Branch
    from core.db.models.monitoring import DriftReport
    branches = db.query(Branch).filter(Branch.is_active == True).all()
    result = {}
    for b in branches:
        last = db.query(DriftReport).filter(DriftReport.branch_id == b.id).order_by(DriftReport.computed_at.desc()).first()
        result[b.code] = {
            "status": last.status if last else "UNKNOWN",
            "psi_max": last.psi_max if last else None,
            "last_check": last.computed_at.isoformat() if last else None,
        }
    return {"branches": result, "timestamp": datetime.now(tz=timezone.utc).isoformat()}


def get_branch_status(db: Session, branch: str) -> dict:
    from core.db.models.referentiels import Branch
    from core.db.models.monitoring import DriftReport, DriftFeatureMetric
    b = db.query(Branch).filter(Branch.code == branch).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche inconnue : {branch}")
    last = db.query(DriftReport).filter(DriftReport.branch_id == b.id).order_by(DriftReport.computed_at.desc()).first()
    if not last:
        return {"branch": branch, "status": "UNKNOWN", "features": {}, "recommendation": "Aucun rapport disponible"}
    features = db.query(DriftFeatureMetric).filter(DriftFeatureMetric.report_id == last.id).all()
    recommendation = "Stable" if last.status == "STABLE" else ("Surveiller" if last.status == "WARNING" else "Réentraînement recommandé")
    return {
        "branch": branch, "status": last.status, "psi_max": last.psi_max,
        "n_features_warning": last.n_features_warning, "n_features_critical": last.n_features_critical,
        "last_check": last.computed_at.isoformat(), "recommendation": recommendation,
        "features": {f.feature_name: {"psi": f.psi_value, "status": f.status} for f in features},
    }


def get_drift_history(db: Session, branch: str, days: int, offset: int, limit: int):
    from core.db.models.referentiels import Branch
    from core.db.models.monitoring import DriftReport
    b = db.query(Branch).filter(Branch.code == branch).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche inconnue : {branch}")
    q = db.query(DriftReport).filter(DriftReport.branch_id == b.id).order_by(DriftReport.computed_at.desc())
    total = q.count()
    return total, q.offset(offset).limit(limit).all()


def get_report_detail(db: Session, report_id: UUID):
    from core.db.models.monitoring import DriftReport, DriftFeatureMetric
    report = db.query(DriftReport).filter(DriftReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    report.features = db.query(DriftFeatureMetric).filter(DriftFeatureMetric.report_id == report_id).all()
    return report


def run_drift(db: Session, branch: str, ref_days: int, cur_days: int, triggered_by: UUID) -> dict:
    """Déclenche le calcul PSI via core/drift_monitor.py et persiste le résultat."""
    from core.db.models.referentiels import Branch
    from core.db.models.monitoring import DriftReport, DriftFeatureMetric
    b = db.query(Branch).filter(Branch.code == branch).first()
    if not b:
        raise HTTPException(status_code=404, detail=f"Branche inconnue : {branch}")
    try:
        from core.drift_monitor import DriftMonitor
        monitor = DriftMonitor()
        result = monitor.compute_psi(branch=branch, reference_days=ref_days, current_days=cur_days)
        report = DriftReport(
            branch_id=b.id, status=result.get("status", "STABLE"),
            psi_max=result.get("psi_max", 0.0), n_features_analyzed=result.get("n_features", 0),
            n_features_warning=result.get("n_warning", 0), n_features_critical=result.get("n_critical", 0),
            reference_window_days=ref_days, current_window_days=cur_days,
            triggered_by=triggered_by,
        )
        db.add(report)
        db.commit()
        return {"status": report.status, "psi_max": report.psi_max, "report_id": str(report.id)}
    except Exception as exc:
        return {"status": "ERROR", "message": str(exc)}
