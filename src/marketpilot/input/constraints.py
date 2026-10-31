"""User constraint standardization and validation (Phase 1)."""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ConstraintViolationKind(StrEnum):
    """Machine-readable reason a constraint was rejected."""

    OUT_OF_RANGE = "OUT_OF_RANGE"
    INCONSISTENT = "INCONSISTENT"
    UNKNOWN_KEY = "UNKNOWN_KEY"
    INVALID_TYPE = "INVALID_TYPE"


class ConstraintIssue(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: ConstraintViolationKind
    key: str
    message: str


class ConstraintSpec(BaseModel):
    """Normalized, validated business constraints.

    All values are in [0, 1] fractions by default. Additional typed constraint
    fields can be added without breaking consumers, because unknown keys are
    rejected (never silently dropped).
    """

    model_config = ConfigDict(frozen=True)

    minimum_margin: float = Field(default=0.0, ge=0.0, le=1.0)
    maximum_risk: float = Field(default=1.0, ge=0.0, le=1.0)
    minimum_evidence_count: int = Field(default=1, ge=1)
    maximum_price: float | None = Field(default=None, gt=0)
    no_battery: bool = Field(default=False)
    fragile_ok: bool = Field(default=True)

    @model_validator(mode="after")
    def _validate_consistency(self) -> "ConstraintSpec":
        if self.minimum_margin > self.maximum_risk and self.minimum_evidence_count < 1:
            raise ValueError(
                "minimum_margin cannot exceed maximum_risk when evidence minimum is positive"
            )
        return self


_KNOWN_KEYS = {
    "minimum_margin",
    "maximum_risk",
    "minimum_evidence_count",
    "maximum_price",
    "no_battery",
    "fragile_ok",
}


def normalize_constraints(
    raw: dict[str, Any] | None,
    *,
    reject_unknown_keys: bool = True,
) -> tuple[ConstraintSpec, list[ConstraintIssue]]:
    """Normalize and validate a user-supplied constraint dict.

    Returns (spec, issues). When issues are present, the returned spec uses the
    accepted subset; the caller decides whether to refuse or proceed with the
    issue list attached.
    """
    issues: list[ConstraintIssue] = []
    if raw is None:
        return ConstraintSpec(), issues

    cleaned: dict[str, Any] = {}
    for key, value in raw.items():
        if key not in _KNOWN_KEYS:
            if reject_unknown_keys:
                issues.append(
                    ConstraintIssue(
                        kind=ConstraintViolationKind.UNKNOWN_KEY,
                        key=key,
                        message=f"unknown constraint key: {key}",
                    )
                )
            continue
        cleaned[key] = value

    try:
        spec = ConstraintSpec(**cleaned)
    except Exception as exc:  # pydantic ValidationError
        message = str(exc)
        issues.append(
            ConstraintIssue(
                kind=ConstraintViolationKind.INVALID_TYPE,
                key="<spec>",
                message=message[:500],
            )
        )
        # Fall back to the safest default rather than raising: the issue list
        # carries the rejection reason.
        return ConstraintSpec(), issues

    # Semantic consistency checks that pydantic does not cover.
    if spec.minimum_margin > spec.maximum_risk:
        issues.append(
            ConstraintIssue(
                kind=ConstraintViolationKind.INCONSISTENT,
                key="minimum_margin",
                message="minimum_margin must not exceed maximum_risk",
            )
        )
    if spec.maximum_price is not None and spec.maximum_price <= 0:
        issues.append(
            ConstraintIssue(
                kind=ConstraintViolationKind.OUT_OF_RANGE,
                key="maximum_price",
                message="maximum_price must be positive",
            )
        )
    return spec, issues
