"""
Package core/db/models — import de tous les modèles SQLAlchemy MAKORA.

L'import de ce module garantit que tous les modèles sont enregistrés
dans Base.metadata avant tout appel à create_all() ou Alembic.
Ordre d'import respecté pour éviter tout problème de résolution de FK.
"""

from core.db.models.iam import (
    User,
    Role,
    Permission,
    UserRole,
    RolePermission,
    UserSession,
)
from core.db.models.referentiels import (
    Branch,
    Insured,
    Contract,
    Practitioner,
    Garage,
    Employer,
    InsuredEmployer,
    ReferencePrice,
)
from core.db.models.sinistres import (
    Claim,
    ClaimLine,
    ClaimDocument,
    OcrExtraction,
)
from core.db.models.pipeline import (
    ModelVersion,
    ProductionDeployment,
    AnalysisRun,
    Analysis,
    ShapContribution,
)
from core.db.models.hitl_graph import (
    Decision,
    Escalation,
    FraudCommunity,
    CommunityMember,
)
from core.db.models.monitoring import (
    DriftReport,
    DriftFeatureMetric,
    RetrainingRequest,
    AuditLog,
    ExportReport,
    ModuleConfig,
    RcaRuleSnapshot,
)

__all__ = [
    # IAM (6)
    "User", "Role", "Permission", "UserRole", "RolePermission", "UserSession",
    # Référentiels (8)
    "Branch", "Insured", "Contract", "Practitioner", "Garage",
    "Employer", "InsuredEmployer", "ReferencePrice",
    # Sinistres (4)
    "Claim", "ClaimLine", "ClaimDocument", "OcrExtraction",
    # Pipeline ML (5)
    "ModelVersion", "ProductionDeployment", "AnalysisRun", "Analysis", "ShapContribution",
    # HITL + Graphe (4)
    "Decision", "Escalation", "FraudCommunity", "CommunityMember",
    # Monitoring + Audit + Config (7)
    "DriftReport", "DriftFeatureMetric", "RetrainingRequest",
    "AuditLog", "ExportReport", "ModuleConfig", "RcaRuleSnapshot",
]
