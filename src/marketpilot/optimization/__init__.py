"""Phase 5: Dream-RSI (recursive self-improvement through evolving worlds)."""

from marketpilot.optimization.coverage_planner import (
    ArchiveCoveragePlanner,
    CoverageReport,
)
from marketpilot.optimization.dream_rsi import (
    DEFAULT_PARAMS,
    PARAM_KEYS,
    DreamEvaluator,
    ExecutionLedger,
    ExplorationTree,
    HistoricalReplaySimulator,
    MultiWorldDreamEvaluator,
    ObservedStep,
    ParameterizedPolicy,
    PolicyRegistry,
    PolicyStatus,
    PromotionKind,
    RecursiveOptimizationLoop,
    ReplayOutcome,
    ReplayWorldArchive,
    TrajectoryRecord,
    policy_hash,
)
from marketpilot.optimization.proposer import (
    STRATEGY_FAMILIES,
    ContextualHybridPolicy,
    MultiFamilyProposer,
    PolicyConfig,
    propose_batch,
)

__all__ = [
    "DEFAULT_PARAMS",
    "PARAM_KEYS",
    "STRATEGY_FAMILIES",
    "ArchiveCoveragePlanner",
    "ContextualHybridPolicy",
    "CoverageReport",
    "DreamEvaluator",
    "ExecutionLedger",
    "ExplorationTree",
    "HistoricalReplaySimulator",
    "MultiFamilyProposer",
    "MultiWorldDreamEvaluator",
    "ObservedStep",
    "ParameterizedPolicy",
    "PolicyConfig",
    "PolicyRegistry",
    "PolicyStatus",
    "PromotionKind",
    "RecursiveOptimizationLoop",
    "ReplayOutcome",
    "ReplayWorldArchive",
    "TrajectoryRecord",
    "policy_hash",
    "propose_batch",
]
