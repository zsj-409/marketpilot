"""Input perturbation testing (Phase 1).

Deterministic perturbations of normalized inputs and an invariance checker:
the same semantic input expressed differently must normalize to the same
structured value (up to documented tolerance).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.input.errors import InputError
from marketpilot.input.normalization import (
    NormalizedInventory,
    NormalizedMoney,
    NormalizedQuantity,
    NormalizedTimestamp,
    normalize_inventory,
    normalize_money,
    normalize_quantity,
    normalize_timestamp,
)


@dataclass(frozen=True)
class Perturbation:
    """One deterministic perturbation of a raw input string."""

    label: str
    value: str


def deterministic_perturbations(raw: str) -> list[Perturbation]:
    """Generate deterministic perturbed variants of a raw input string.

    Covers: whitespace, case, extra punctuation, currency symbol variants,
    thousand separators, and decimal comma/dot swaps.
    """
    stripped = raw.strip()
    return [
        Perturbation("strip", stripped),
        Perturbation("lower", stripped.lower()),
        Perturbation("upper", stripped.upper()),
        Perturbation("extra-whitespace", re_space(stripped)),
        Perturbation("trailing-dot", stripped + "."),
        Perturbation("thousand-sep", thousand_sep(stripped)),
        Perturbation("decimal-comma", decimal_comma(stripped)),
    ]


def re_space(text: str) -> str:
    import re

    return re.sub(r"\s+", "  ", text)


def thousand_sep(text: str) -> str:
    import re

    return re.sub(r"(?<=\d)(?=(\d{3})+(?!\d))", ",", text)


def decimal_comma(text: str) -> str:
    import re

    return re.sub(r"(?<=\d)\.(?=\d)", ",", text)


class InvarianceResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    normalizer: str
    raw: str
    perturbed_count: int
    failures: list[str] = Field(default_factory=list)
    passed: bool = True


_NORMALIZERS: dict[str, Callable[[str], Any]] = {
    "money": normalize_money,
    "quantity": normalize_quantity,
    "inventory": normalize_inventory,
    "timestamp": normalize_timestamp,
}


def _key(value: Any) -> tuple[Any, ...]:
    if isinstance(value, NormalizedMoney):
        return (round(value.amount, 4), value.currency, value.minor_unit)
    if isinstance(value, NormalizedQuantity):
        return (round(value.value, 4), value.unit, value.family)
    if isinstance(value, NormalizedInventory):
        return (value.status.value, value.quantity)
    if isinstance(value, NormalizedTimestamp):
        return (value.value.isoformat(),)
    return (str(value),)


def check_normalization_invariance(
    raw: str,
    *,
    normalizers: tuple[str, ...] | None = None,
) -> list[InvarianceResult]:
    """Check that perturbed variants normalize to the same canonical value."""
    results: list[InvarianceResult] = []
    for name in normalizers or tuple(_NORMALIZERS):
        normalize = _NORMALIZERS[name]
        try:
            baseline = normalize(raw)
        except InputError:
            continue  # raw is not parseable by this normalizer; skip
        failures: list[str] = []
        for perturbation in deterministic_perturbations(raw):
            try:
                candidate = normalize(perturbation.value)
            except InputError:
                failures.append(f"{perturbation.label}: unparseable")
                continue
            if _key(candidate) != _key(baseline):
                failures.append(
                    f"{perturbation.label}: {_key(candidate)!r} != {_key(baseline)!r}"
                )
        results.append(
            InvarianceResult(
                normalizer=name,
                raw=raw,
                perturbed_count=len(deterministic_perturbations(raw)),
                failures=failures,
                passed=not failures,
            )
        )
    return results
