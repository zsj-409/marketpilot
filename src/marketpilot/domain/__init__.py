"""Typed MarketPilot domain contracts."""

from marketpilot.domain.enums import Decision
from marketpilot.domain.evidence import EvidenceItem
from marketpilot.domain.findings import Finding
from marketpilot.domain.goals import ResearchGoal
from marketpilot.domain.recommendations import (
    ProductCandidate,
    ProductScore,
    Recommendation,
    RiskFlag,
)
from marketpilot.domain.state import ResearchState
from marketpilot.domain.tasks import TaskNode

__all__ = [
    "Decision",
    "EvidenceItem",
    "Finding",
    "ProductCandidate",
    "ProductScore",
    "Recommendation",
    "ResearchGoal",
    "ResearchState",
    "RiskFlag",
    "TaskNode",
]
