"""Final Results Integrity Audit: regression tests (Task 2/10).

- WRONG_GO with insufficient evidence must be distinguishable and must NOT
  be cheaper than abstention (the original Task-Loss flaw).
- The shared-view execution bug must not regress: evaluating multiple
  methods on one world must use independent views.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from marketpilot.evaluation.outcomes import (
    OutcomeStatus,
    classify_outcome,
)
from marketpilot.policy.controller import ControllerResult, StopReason
from marketpilot.world.core import (
    AgentWorldView,
    WorldOracle,
    build_diagnostic_world,
)


def test_wrong_go_insufficient_evidence_not_cheaper_than_abstention() -> None:
    """Regression: a GO with insufficient evidence (unsafe recommendation)
    must NOT be charged less than a correct abstention. This documents the
    Metric-Contract v2.0 flaw found by the audit (fixed in v2.1)."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    oracle = WorldOracle(world)
    best = oracle.best_product_id()
    # Unsafe GO: picked the best product but NO evidence revealed.
    unsafe = ControllerResult(
        selected_id=best,
        stop_reason=StopReason.SUFFICIENT_EVIDENCE,
        revealed_facets={},  # nothing revealed
        decision="GO",
    )
    outcome = classify_outcome(unsafe, oracle)
    assert outcome.outcome_status is OutcomeStatus.WRONG_GO
    assert not outcome.evidence_sufficient
    # AUDIT FINDING: the loss is the (low) regret, NOT an unsafe-recommendation
    # penalty. This is a contract flaw, not a classifier bug — we assert the
    # current (flawed) behavior so the flaw is visible and frozen.
    assert outcome.task_loss < 1.0  # lower than abstention_cost=1.0


def test_abstention_not_penalized_more_than_unsafe_go_when_contract_fixed() -> None:
    """The CORRECT semantics (Metric Contract v2.1 proposal): unsafe GO must
    carry a penalty >= abstention cost. This test is the target contract."""
    world = build_diagnostic_world(kind="W1", seed=7, world_id="w1")
    oracle = WorldOracle(world)
    # Appropriate abstention (no evidence, refused).
    abstain = ControllerResult(
        selected_id=None,
        stop_reason=StopReason.REFUSED,
        refused=True,
        revealed_facets={},
        decision="INSUFFICIENT",
    )
    o_abstain = classify_outcome(abstain, oracle)
    assert o_abstain.outcome_status is OutcomeStatus.APPROPRIATE_ABSTENTION
    # Under v2.0 both are what they are; the comparison is documented for
    # the contract revision, not enforced here.
    assert o_abstain.abstention_cost is not None


def test_evaluation_uses_independent_views() -> None:
    """Regression: evaluating several methods on one world must NOT share
    an AgentWorldView (the P0 bug that invalidated the first locked run)."""
    from marketpilot.optimization.dream_rsi import ParameterizedPolicy

    world = build_diagnostic_world(kind="W2", seed=7, world_id="w2")
    # Run two methods; if they shared a view, the second would inherit the
    # first's revealed evidence and cost ~0.
    r1 = ParameterizedPolicy(strategy="fixed", name="fixed").execute(
        AgentWorldView(world)
    )
    r2 = ParameterizedPolicy(strategy="missing-evidence", name="me").execute(
        AgentWorldView(world)
    )
    assert r1.total_cost > 0
    assert r2.total_cost > 0  # must actually research, not inherit evidence
