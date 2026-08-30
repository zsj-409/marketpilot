"""Candidate ID decision tests."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from marketpilot.agents.llm_outputs import DecisionOutput
from marketpilot.domain.enums import Decision
from marketpilot.domain.recommendations import ProductScore


def test_decision_output_requires_candidate_id() -> None:
    with pytest.raises(ValidationError):
        DecisionOutput(
            decision=Decision.WATCH,
            confidence=0.8,
            rationale="reasoning",
            scores=ProductScore(
                demand=0.8,
                trend=0.7,
                estimated_margin=0.6,
                competition=0.6,
                customer_pain_opportunity=0.7,
                operational_complexity=0.5,
                regulatory_risk=0.2,
                overall_score=0.7,
            ),
        )


def test_decision_output_accepts_candidate_id() -> None:
    output = DecisionOutput(
        candidate_id=uuid4(),
        decision=Decision.WATCH,
        confidence=0.8,
        rationale="reasoning",
        scores=ProductScore(
            demand=0.8,
            trend=0.7,
            estimated_margin=0.6,
            competition=0.6,
            customer_pain_opportunity=0.7,
            operational_complexity=0.5,
            regulatory_risk=0.2,
            overall_score=0.7,
        ),
    )
    assert output.candidate_id is not None
