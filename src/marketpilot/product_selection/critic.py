"""Deterministic decision critic."""

from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.product_selection.models import (
    ConstraintViolation,
    DecisionCriticVerdict,
    EvidenceConflict,
    ResearchGap,
)


class CriticOutput(BaseModel):
    model_config = ConfigDict(frozen=True)

    verdict: DecisionCriticVerdict
    gaps: list[ResearchGap] = Field(default_factory=list)
    violations: list[ConstraintViolation] = Field(default_factory=list)
    conflicts: list[EvidenceConflict] = Field(default_factory=list)


class DecisionCritic:
    """Apply deterministic, typed critiques to a provisional decision."""

    def critique(
        self,
        *,
        selected_candidate_id: UUID,
        evidence: dict[str, list[str]],
        constraints: dict[str, object],
        candidate_facts: dict[str, object],
    ) -> CriticOutput:
        violations: list[ConstraintViolation] = []
        gaps: list[ResearchGap] = []
        for constraint, expected in constraints.items():
            actual = (
                candidate_facts.get("battery")
                if constraint == "no_battery"
                else candidate_facts.get("price")
                if constraint == "max_price"
                else candidate_facts.get(constraint)
            )
            if actual is None:
                gaps.append(
                    ResearchGap(
                        candidate_id=selected_candidate_id,
                        facet="battery" if constraint == "no_battery" else constraint,
                        reason=f"missing {constraint} evidence",
                        priority=1,
                        required_evidence=f"{constraint} evidence",
                    )
                )
            elif not _satisfies(constraint, actual, expected):
                violations.append(
                    ConstraintViolation(
                        candidate_id=selected_candidate_id,
                        constraint=constraint,
                        severity="hard",
                        evidence_ids=[],
                    )
                )
        if gaps:
            return CriticOutput(verdict=DecisionCriticVerdict.MISSING_EVIDENCE, gaps=gaps)
        if violations:
            return CriticOutput(
                verdict=DecisionCriticVerdict.CONSTRAINT_FAILURE,
                violations=violations,
            )

        conflicts: list[EvidenceConflict] = []
        required_facets = {"demand", "risk", "competition"}
        for facet in required_facets:
            values = evidence.get(facet, [])
            if not values:
                gaps.append(
                    ResearchGap(
                        candidate_id=selected_candidate_id,
                        facet=facet,
                        reason=f"missing {facet} evidence",
                        priority=1,
                        required_evidence=f"{facet} evidence",
                    )
                )
            elif "conflict" in values:
                conflicts.append(
                    EvidenceConflict(
                        candidate_id=selected_candidate_id,
                        facet=facet,
                        evidence_ids=[uuid4(), uuid4()],
                        explanation=f"conflicting {facet} evidence",
                    )
                )
        if conflicts:
            return CriticOutput(
                verdict=DecisionCriticVerdict.EVIDENCE_CONFLICT,
                conflicts=conflicts,
            )
        if gaps:
            return CriticOutput(verdict=DecisionCriticVerdict.MISSING_EVIDENCE, gaps=gaps)
        return CriticOutput(verdict=DecisionCriticVerdict.ACCEPT)


def _satisfies(constraint: str, actual: object, expected: object) -> bool:
    if constraint == "max_price":
        return float(str(actual)) <= float(str(expected))
    if constraint == "no_battery":
        return not bool(actual)
    return True
