"""Phase 3/4: research policy layer (candidate frontier + adaptive controller)."""

from marketpilot.policy.controller import (
    AdaptiveVOIController,
    ControllerAction,
    ControllerResult,
    FixedController,
    MissingEvidenceController,
    StrategyKind,
    UncertaintyController,
    controller_for,
    run_controller_episode,
)
from marketpilot.policy.curves import (
    build_regret_budget_curve,
    evaluate_episode,
    write_curves,
)
from marketpilot.policy.frontier import (
    BranchResult,
    FrontierMetrics,
    compute_frontier_metrics,
    ranking_overlap,
    write_frontier_report,
)

__all__ = [
    "AdaptiveVOIController",
    "BranchResult",
    "ControllerAction",
    "ControllerResult",
    "FixedController",
    "FrontierMetrics",
    "MissingEvidenceController",
    "StrategyKind",
    "UncertaintyController",
    "build_regret_budget_curve",
    "compute_frontier_metrics",
    "controller_for",
    "evaluate_episode",
    "ranking_overlap",
    "run_controller_episode",
    "write_curves",
    "write_frontier_report",
]
