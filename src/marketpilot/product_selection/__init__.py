"""Closed-loop product selection runtime."""

from marketpilot.product_selection.controller import TerminationController
from marketpilot.product_selection.critic import DecisionCritic
from marketpilot.product_selection.decision import DecisionModule
from marketpilot.product_selection.loop import ClosedLoopRunner, ProductSelectionResult
from marketpilot.product_selection.models import (
    ConstraintViolation,
    DecisionCriticVerdict,
    EvidenceConflict,
    ResearchGap,
    ResearchRound,
    TerminationDecision,
)
from marketpilot.product_selection.workers import WorkerRegistry

__all__ = [
    "ClosedLoopRunner",
    "ConstraintViolation",
    "DecisionCritic",
    "DecisionCriticVerdict",
    "DecisionModule",
    "EvidenceConflict",
    "ProductSelectionResult",
    "ResearchGap",
    "ResearchRound",
    "TerminationController",
    "TerminationDecision",
    "WorkerRegistry",
]
