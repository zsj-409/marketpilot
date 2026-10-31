"""MarketPilot safety subpackage: deterministic final decision gating."""

from marketpilot.safety.gate import (
    BudgetState,
    EvidenceRecord,
    FinalDecisionSafetyGate,
    GateReason,
    GateResult,
    GateVerdict,
    TaskSpec,
    validate_final_decision,
)
from marketpilot.safety.gateway import (
    GatedEmission,
    gate_recommendation,
    gate_workbench_run,
)
from marketpilot.safety.trust import (
    AuthoritativeTaskState,
    EvidenceIntegrityReport,
    check_evidence_integrity,
    gate_with_authoritative_state,
)

__all__ = [
    "AuthoritativeTaskState",
    "BudgetState",
    "EvidenceIntegrityReport",
    "EvidenceRecord",
    "FinalDecisionSafetyGate",
    "GateReason",
    "GateResult",
    "GateVerdict",
    "GatedEmission",
    "TaskSpec",
    "check_evidence_integrity",
    "gate_recommendation",
    "gate_with_authoritative_state",
    "gate_workbench_run",
    "validate_final_decision",
]
