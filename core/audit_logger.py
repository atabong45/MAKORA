"""
MODULE : core/audit_logger.py
DESCRIPTION : Journal immuable des actions MAKORA — résout DT-AUDIT.
Appelé depuis api/middleware/audit.py et les services métiers.

DÉCISION DE CONCEPTION :
- Utilise une session DB indépendante (pas la session request) pour garantir
  que le log est écrit même si la transaction principale est rollbackée.
- INSERT ONLY via Row Level Security PostgreSQL (immuabilité renforcée DB).
"""
from __future__ import annotations
import logging
from typing import Optional

logger = logging.getLogger("makora.audit")


def log_action(
    user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    payload: Optional[dict] = None,
    ip_address: Optional[str] = None,
    result: str = "SUCCESS",
    error_message: Optional[str] = None,
) -> None:
    """Enregistre une action dans audit_logs (session indépendante)."""
    try:
        from core.db.base import SessionLocal
        from core.db.models.monitoring import AuditLog
        import uuid

        db = SessionLocal()
        try:
            log = AuditLog(
                id=uuid.uuid4(),
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                payload=payload,
                ip_address=ip_address,
                result=result,
                error_message=error_message,
            )
            db.add(log)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning("audit_logger: échec écriture DB: %s", e)
        finally:
            db.close()
    except ImportError:
        logger.debug("audit_logger: modèles DB non disponibles — skip")
    except Exception as e:
        logger.warning("audit_logger: erreur inattendue: %s", e)


def log_analysis(user_id: Optional[str], branch: str, batch_id: str, nb_anomalies: int) -> None:
    log_action(
        user_id=user_id, action="analysis:run",
        resource_type="analysis", resource_id=batch_id,
        payload={"branch": branch, "nb_anomalies": nb_anomalies},
    )


def log_decision(user_id: str, analysis_id: str, decision: str, motif: Optional[str]) -> None:
    log_action(
        user_id=user_id, action=f"decision:{decision.lower()}",
        resource_type="decision", resource_id=analysis_id,
        payload={"decision": decision, "motif": motif},
    )


def log_model_deploy(user_id: str, branch: str, model_version_id: str) -> None:
    log_action(
        user_id=user_id, action="model:deploy",
        resource_type="model", resource_id=model_version_id,
        payload={"branch": branch},
    )
