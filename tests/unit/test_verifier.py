"""Verifier tests."""

from marketpilot.verifier.verifier import VerifierIssueCode, verify_recommendation


def test_verifier_rejects_constraint_violation() -> None:
    result = verify_recommendation(
        product={"gross_margin": 0.1, "risk_score": 0.2},
        constraints={"minimum_margin": 0.3, "maximum_risk": 0.6},
        evidence_count=1,
        snapshot_count=1,
        distinct_domains=2,
        risk_covered=True,
    )
    assert any(issue.code is VerifierIssueCode.CONSTRAINT_VIOLATION for issue in result.issues)
    assert not result.passed


def test_verifier_accepts_valid_recommendation() -> None:
    result = verify_recommendation(
        product={"gross_margin": 0.5, "risk_score": 0.2},
        constraints={"minimum_margin": 0.3, "maximum_risk": 0.6},
        evidence_count=2,
        snapshot_count=1,
        distinct_domains=3,
        risk_covered=True,
    )
    assert result.passed
