"""Deterministic verifier for synthetic-environment recommendations."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class VerifierIssueCode(StrEnum):
    """Typed verifier issue codes."""

    MISSING_EVIDENCE = "MISSING_EVIDENCE"
    MISSING_SNAPSHOT = "MISSING_SNAPSHOT"
    CONSTRAINT_VIOLATION = "CONSTRAINT_VIOLATION"
    LOW_SOURCE_DIVERSITY = "LOW_SOURCE_DIVERSITY"
    RISK_NOT_COVERED = "RISK_NOT_COVERED"
    NUMERIC_INCONSISTENCY = "NUMERIC_INCONSISTENCY"
    DUPLICATE_SOURCE_PENALTY = "DUPLICATE_SOURCE_PENALTY"


@dataclass(frozen=True)
class VerifierIssue:
    code: VerifierIssueCode
    message: str


@dataclass(frozen=True)
class VerifierScore:
    evidence: float
    constraints: float
    risk: float
    diversity: float
    total: float


@dataclass(frozen=True)
class VerifierResult:
    passed: bool
    score: VerifierScore
    issues: tuple[VerifierIssue, ...] = field(default_factory=tuple)


def verify_recommendation(
    *,
    product: dict[str, Any],
    constraints: dict[str, float],
    evidence_count: int,
    snapshot_count: int,
    distinct_domains: int,
    risk_covered: bool,
) -> VerifierResult:
    """Return an inspectable, deterministic verification result."""

    issues: list[VerifierIssue] = []
    if evidence_count < 1:
        issues.append(VerifierIssue(VerifierIssueCode.MISSING_EVIDENCE, "no supporting evidence"))
    if snapshot_count < 1:
        issues.append(VerifierIssue(VerifierIssueCode.MISSING_SNAPSHOT, "no source snapshot"))
    if distinct_domains < 2:
        issues.append(
            VerifierIssue(VerifierIssueCode.LOW_SOURCE_DIVERSITY, "fewer than two distinct domains")
        )
    if not risk_covered:
        issues.append(
            VerifierIssue(VerifierIssueCode.RISK_NOT_COVERED, "risk flags do not cover the product")
        )

    margin = float(product.get("gross_margin", 0.0))
    risk = float(product.get("risk_score", 0.0))
    minimum_margin = float(constraints.get("minimum_margin", 0.0))
    maximum_risk = float(constraints.get("maximum_risk", 1.0))
    if margin < minimum_margin:
        issues.append(
            VerifierIssue(
                VerifierIssueCode.CONSTRAINT_VIOLATION,
                f"margin {margin:.2f} below minimum {minimum_margin:.2f}",
            )
        )
    if risk > maximum_risk:
        issues.append(
            VerifierIssue(
                VerifierIssueCode.CONSTRAINT_VIOLATION,
                f"risk {risk:.2f} above maximum {maximum_risk:.2f}",
            )
        )

    evidence_score = 1.0 if evidence_count >= 1 else 0.0
    snapshot_score = 1.0 if snapshot_count >= 1 else 0.0
    constraint_score = (
        1.0
        if not any(issue.code is VerifierIssueCode.CONSTRAINT_VIOLATION for issue in issues)
        else 0.0
    )
    risk_score = 1.0 if risk_covered else 0.0
    diversity_score = 1.0 if distinct_domains >= 2 else 0.5
    total = round(
        0.25 * evidence_score
        + 0.15 * snapshot_score
        + 0.30 * constraint_score
        + 0.15 * risk_score
        + 0.15 * diversity_score,
        4,
    )
    return VerifierResult(
        passed=not issues,
        score=VerifierScore(
            evidence=evidence_score,
            constraints=constraint_score,
            risk=risk_score,
            diversity=diversity_score,
            total=total,
        ),
        issues=tuple(issues),
    )
