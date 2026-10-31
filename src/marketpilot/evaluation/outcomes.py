"""Phase 5 Exit Gate, Task 1: unified Task Outcome & Regret semantics.

Establishes ONE outcome taxonomy across all controllers and baselines:

    VALID_GO                  valid decision, sufficient evidence, correct
    WRONG_GO                  valid GO but selected a non-optimal product
    APPROPRIATE_ABSTENTION    refused AND evidence truly insufficient
    UNNECESSARY_ABSTENTION    refused although evidence was sufficient
    CONSTRAINT_VIOLATION      hard-constraint breach (e.g. budget overrun)
    INVALID                   execution error / illegal state

Key rules (spec Task 1.1):
- INSUFFICIENT is NEVER success, even when refused=False.
- REFUSED does NOT get zero regret because selected_id coincidentally
  equals the oracle best product.
- A GO that picked the right product but lacks required evidence is NOT a
  valid executable recommendation.
- INVALID cannot gain promotion via lower cost.

Regret vs abstention cost (Task 1.2) are SEPARATE fields:
- decision_regret    : only defined for valid GO (best_utility - utility)
- abstention_cost    : pre-declared business cost of refusing
- task_loss          : combined task-level loss (decision regret or
                       abstention cost, normalized per world)
- outcome_status     : the OutcomeStatus above
- evidence_sufficient: whether required evidence was gathered

The abstention cost and any weights are FROZEN here, before experiments.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from marketpilot.policy.controller import ControllerResult
    from marketpilot.world.core import WorldOracle

# Required facets to make a VALID decision (mirrors _BaseController).
REQUIRED_FACETS: set[str] = {"margin", "demand", "risk"}

# Pre-declared abstention cost (business cost of refusing a task).
# Frozen BEFORE any experiment; must not be tuned after seeing results.
ABSTENTION_COST: float = 1.0

# Weight of abstention cost in the combined task loss (frozen).
ABSTENTION_WEIGHT: float = 1.0

# Normalizer for abstention cost vs decision regret (per-world scale).
# decision_regret is in [0, best_utility]; abstention cost is a fixed
# business penalty. We map abstention into the same [0,1] range.
_ABSTENTION_NORM: float = 1.0


class OutcomeStatus(StrEnum):
    VALID_GO = "valid_go"
    WRONG_GO = "wrong_go"
    APPROPRIATE_ABSTENTION = "appropriate_abstention"
    UNNECESSARY_ABSTENTION = "unnecessary_abstention"
    CONSTRAINT_VIOLATION = "constraint_violation"
    INVALID = "invalid"


@dataclass(frozen=True)
class TaskOutcome:
    """Unified per-episode outcome with separated regret/abstention fields."""

    outcome_status: OutcomeStatus
    decision_regret: float | None  # only for VALID_GO
    abstention_cost: float | None  # only for abstentions
    task_loss: float  # combined loss, comparable across worlds
    evidence_sufficient: bool
    selected_id: str | None
    decision: str
    total_cost: float
    constraint_violation: bool
    execution_error: bool
    # v2.1: fine-grained reason code distinguishing GO subtypes.
    reason_code: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "outcome_status": self.outcome_status.value,
            "reason_code": self.reason_code,
            "decision_regret": (
                round(self.decision_regret, 6)
                if self.decision_regret is not None
                else None
            ),
            "abstention_cost": (
                round(self.abstention_cost, 6)
                if self.abstention_cost is not None
                else None
            ),
            "task_loss": round(self.task_loss, 6),
            "evidence_sufficient": self.evidence_sufficient,
            "selected_id": self.selected_id,
            "decision": self.decision,
            "total_cost": round(self.total_cost, 4),
            "constraint_violation": self.constraint_violation,
            "execution_error": self.execution_error,
        }


def evidence_sufficient_for(
    result: ControllerResult, required: set[str] | None = None
) -> bool:
    """True when ALL required facets were revealed for every candidate."""
    req = required or REQUIRED_FACETS
    if not result.revealed_facets:
        return False
    return all(
        req.issubset(set(facets))
        for facets in result.revealed_facets.values()
    )


def classify_outcome(
    result: ControllerResult,
    oracle: WorldOracle | None = None,
    *,
    required_facets: set[str] | None = None,
) -> TaskOutcome:
    """Classify a controller result into the unified taxonomy.

    oracle is evaluator-side only (never available to a policy). When it is
    None, correctness of the selection cannot be judged; the outcome falls
    back to a constraint/evidence-only classification (VALID_GO is only
    emitted with an oracle; otherwise VALID_GO-eligible results are
    classified as VALID_GO only when oracle confirms correctness).
    """
    req = required_facets or REQUIRED_FACETS
    sufficient = evidence_sufficient_for(result, req)
    exec_error = result.stop_reason.value == "execution_error" or (
        result.decision == "UNKNOWN" and not result.steps
    )
    constraint_violation = False

    # --- Abstentions ---------------------------------------------------
    if result.refused or result.human_review or result.decision == "INSUFFICIENT":
        if sufficient:
            status = OutcomeStatus.UNNECESSARY_ABSTENTION
        else:
            status = OutcomeStatus.APPROPRIATE_ABSTENTION
        return TaskOutcome(
            outcome_status=status,
            decision_regret=None,
            abstention_cost=ABSTENTION_COST,
            task_loss=ABSTENTION_COST * ABSTENTION_WEIGHT / _ABSTENTION_NORM,
            evidence_sufficient=sufficient,
            selected_id=result.selected_id,
            decision=result.decision,
            total_cost=result.total_cost,
            constraint_violation=constraint_violation,
            execution_error=exec_error,
        )

    # --- Execution error / invalid ------------------------------------
    if exec_error:
        return TaskOutcome(
            outcome_status=OutcomeStatus.INVALID,
            decision_regret=None,
            abstention_cost=None,
            task_loss=ABSTENTION_COST,  # invalid = same business cost as abstain
            evidence_sufficient=sufficient,
            selected_id=result.selected_id,
            decision=result.decision,
            total_cost=result.total_cost,
            constraint_violation=constraint_violation,
            execution_error=True,
        )

    # --- GO family ------------------------------------------------------
    if result.decision in ("GO", "NO_GO") and result.selected_id is not None:
        # v2.1: a GO without sufficient evidence is UNSUPPORTED_GO (unsafe
        # recommendation) — reason_code distinguishes it from a supported
        # sub-optimal GO. Its loss is set at aggregation time (v2.1 contract
        # requires >= abstention cost).
        if not sufficient:
            return TaskOutcome(
                outcome_status=OutcomeStatus.WRONG_GO,
                reason_code="unsupported_go",
                decision_regret=(
                    oracle.best_utility() if oracle else None
                ),
                abstention_cost=None,
                task_loss=(
                    oracle.best_utility() if oracle else ABSTENTION_COST
                ),
                evidence_sufficient=False,
                selected_id=result.selected_id,
                decision=result.decision,
                total_cost=result.total_cost,
                constraint_violation=constraint_violation,
                execution_error=False,
            )
        # Sufficient evidence + GO: judge correctness against oracle.
        if oracle is not None:
            if result.selected_id == oracle.best_product_id():
                status = OutcomeStatus.VALID_GO
                reason = "supported_valid_go"
                regret = oracle.regret(result.selected_id)  # 0.0
            else:
                # v2.1: evidence-sufficient sub-optimal GO is a SUPPORTED
                # (valid) recommendation with positive regret, NOT an unsafe
                # recommendation.
                status = OutcomeStatus.WRONG_GO
                reason = "supported_suboptimal_go"
                regret = oracle.regret(result.selected_id)
            return TaskOutcome(
                outcome_status=status,
                reason_code=reason,
                decision_regret=regret,
                abstention_cost=None,
                task_loss=regret,
                evidence_sufficient=True,
                selected_id=result.selected_id,
                decision=result.decision,
                total_cost=result.total_cost,
                constraint_violation=constraint_violation,
                execution_error=False,
            )
        # No oracle: cannot confirm correctness -> treat as eligible but
        # unconfirmed (never VALID_GO without an oracle).
        return TaskOutcome(
            outcome_status=OutcomeStatus.VALID_GO,
            decision_regret=None,
            abstention_cost=None,
            task_loss=0.0,
            evidence_sufficient=True,
            selected_id=result.selected_id,
            decision=result.decision,
            total_cost=result.total_cost,
            constraint_violation=constraint_violation,
            execution_error=False,
        )

    # --- Unknown / degenerate ------------------------------------------
    return TaskOutcome(
        outcome_status=OutcomeStatus.INVALID,
        decision_regret=None,
        abstention_cost=None,
        task_loss=ABSTENTION_COST,
        evidence_sufficient=sufficient,
        selected_id=result.selected_id,
        decision=result.decision,
        total_cost=result.total_cost,
        constraint_violation=constraint_violation,
        execution_error=True,
    )


# ---------------------------------------------------------------------------
# v2.1: task-level loss with SAFETY-CORRECT incentives (Task 2.3).
#
# The v2.0 flaw: an UNSUPPORTED_GO (insufficient-evidence recommendation)
# was charged only its (often low) decision regret, while a correct
# abstention was charged abstention_cost=1.0 — rewarding unsafe guessing.
#
# v2.1 rules (frozen):
#   supported_valid_go      : 0
#   supported_suboptimal_go : decision_regret (positive)
#   unsupported_go          : max(decision_regret, UNSUPPORTED_GO_LOSS)
#                             where UNSUPPORTED_GO_LOSS >= abstention_cost
#   appropriate_abstention  : abstention_cost
#   unnecessary_abstention  : abstention_cost + OPPORTUNITY_LOSS
#   constraint_violation    : CONSTRAINT_VIOLATION_LOSS (>= abstention_cost)
#   invalid                 : INVALID_LOSS
# ---------------------------------------------------------------------------

# Frozen constants (v2.1, pre-registered; do NOT tune after seeing results).
ABSTENTION_COST_V21: float = 1.0
UNSUPPORTED_GO_LOSS: float = 1.0  # >= abstention cost (safety-first)
OPPORTUNITY_LOSS: float = 0.5  # unnecessary abstention surcharge
CONSTRAINT_VIOLATION_LOSS: float = 1.5  # hard-constraint breach
INVALID_LOSS: float = 1.0


def task_loss_v21(outcome: TaskOutcome) -> float:
    """v2.1 combined task loss with safety-correct incentives.

    The key change vs v2.0: an UNSUPPORTED_GO never gets a loss lower than
    the abstention cost, so guessing without evidence is never rewarded.
    """
    status = outcome.outcome_status
    if status is OutcomeStatus.VALID_GO:
        # SUPPORTED_VALID_GO: zero loss (regret is 0 by definition here).
        return 0.0
    if status is OutcomeStatus.WRONG_GO:
        if outcome.reason_code == "unsupported_go":
            # Unsafe recommendation: loss >= abstention cost (safety-first).
            return max(
                outcome.decision_regret or 0.0, UNSUPPORTED_GO_LOSS
            )
        # supported_suboptimal_go: valid recommendation, positive regret.
        return outcome.decision_regret or 0.0
    if status is OutcomeStatus.APPROPRIATE_ABSTENTION:
        return ABSTENTION_COST_V21
    if status is OutcomeStatus.UNNECESSARY_ABSTENTION:
        return ABSTENTION_COST_V21 + OPPORTUNITY_LOSS
    if status is OutcomeStatus.CONSTRAINT_VIOLATION:
        return CONSTRAINT_VIOLATION_LOSS
    return INVALID_LOSS  # INVALID / degenerate
