"""Phase 1: stable input and data layer for MarketPilot 2.0.

Strongly typed, offline-testable normalization of user input (task specs,
constraints, product entities, price/currency/unit/inventory/time), untrusted
external content isolation, tool-replay vs trajectory-replay distinction, and
unified error classification. No component here reads hidden ground truth.
"""

from marketpilot.input.constraints import ConstraintSpec, normalize_constraints
from marketpilot.input.entities import ProductEntity, extract_product_entities
from marketpilot.input.errors import ErrorClassifier, InputError, classify_error
from marketpilot.input.isolation import (
    InjectionSignal,
    sanitize_untrusted_text,
    scan_injection_signals,
)
from marketpilot.input.normalization import (
    InventoryStatus,
    NormalizedInventory,
    NormalizedMoney,
    NormalizedQuantity,
    NormalizedTimestamp,
    normalize_inventory,
    normalize_money,
    normalize_quantity,
    normalize_timestamp,
)
from marketpilot.input.perturbation import (
    Perturbation,
    check_normalization_invariance,
    deterministic_perturbations,
)
from marketpilot.input.replay import (
    ReplayKind,
    ToolReplayRecord,
    TrajectoryReplayRecord,
    classify_replay_record,
    trajectory_replay_coverage,
)
from marketpilot.input.spec import (
    ResearchTaskSpec,
    UnifiedResearchBudget,
    WorldSplit,
    task_spec_from_goal,
)

__all__ = [
    "ConstraintSpec",
    "ErrorClassifier",
    "InjectionSignal",
    "InputError",
    "InventoryStatus",
    "NormalizedInventory",
    "NormalizedMoney",
    "NormalizedQuantity",
    "NormalizedTimestamp",
    "Perturbation",
    "ProductEntity",
    "ReplayKind",
    "ResearchTaskSpec",
    "ToolReplayRecord",
    "TrajectoryReplayRecord",
    "UnifiedResearchBudget",
    "WorldSplit",
    "check_normalization_invariance",
    "classify_error",
    "classify_replay_record",
    "deterministic_perturbations",
    "extract_product_entities",
    "normalize_constraints",
    "normalize_inventory",
    "normalize_money",
    "normalize_quantity",
    "normalize_timestamp",
    "sanitize_untrusted_text",
    "scan_injection_signals",
    "task_spec_from_goal",
    "trajectory_replay_coverage",
]
