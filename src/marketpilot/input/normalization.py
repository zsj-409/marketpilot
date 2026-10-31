"""Price, currency, unit, inventory, and time normalization (Phase 1).

Deterministic, offline, strongly typed. No hidden truth is read here.
"""

import re
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from marketpilot.input.errors import InputError


class NormalizedMoney(BaseModel):
    """A normalized monetary value in a canonical currency and minor unit."""

    model_config = ConfigDict(frozen=True)

    amount: float = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    minor_unit: int = Field(default=2, ge=0, le=8)
    raw: str = Field(default="", max_length=200)

    @property
    def amount_in_minor(self) -> int:
        # mypy strict flags round() as returning Any; the value is integral.
        return int(round(self.amount * (10**self.minor_unit)))  # noqa: RUF046


_CURRENCY_CODES = {
    "USD": "USD",
    "US": "USD",
    "US$": "USD",
    "$": "USD",
    "EUR": "EUR",
    "€": "EUR",
    "GBP": "GBP",
    "£": "GBP",
    "JPY": "JPY",
    "¥": "JPY",
    "CNY": "CNY",
    "RMB": "CNY",
    "元": "CNY",
    "HK$": "HKD",
    "HKD": "HKD",
    "CAD": "CAD",
    "AUD": "AUD",
    "CHF": "CHF",
    "INR": "INR",
}

_MONEY_RE = re.compile(
    r"^\s*(?P<symbol>[$€£¥元]|[A-Z]{2,3}|RMB|HK\$)?\s*"
    r"(?P<amount>\d{1,15}(?:[.,]\d{1,8})?)\s*"
    r"(?P<code>[A-Z]{2,3}|RMB)?\s*$",
    re.IGNORECASE,
)


class NormalizedQuantity(BaseModel):
    """A normalized quantity with canonical unit and unit family."""

    model_config = ConfigDict(frozen=True)

    value: float = Field(ge=0)
    unit: str = Field(min_length=1, max_length=50)
    family: str = Field(min_length=1, max_length=50)
    raw: str = Field(default="", max_length=200)


# unit -> (canonical, family)
_UNITS = {
    "kg": ("kg", "mass"),
    "kilogram": ("kg", "mass"),
    "kilograms": ("kg", "mass"),
    "g": ("g", "mass"),
    "gram": ("g", "mass"),
    "grams": ("g", "mass"),
    "lb": ("lb", "mass"),
    "lbs": ("lb", "mass"),
    "pound": ("lb", "mass"),
    "pounds": ("lb", "mass"),
    "oz": ("oz", "mass"),
    "ounce": ("oz", "mass"),
    "ounces": ("oz", "mass"),
    "ml": ("ml", "volume"),
    "milliliter": ("ml", "volume"),
    "milliliters": ("ml", "volume"),
    "l": ("l", "volume"),
    "liter": ("l", "volume"),
    "liters": ("l", "volume"),
    "cm": ("cm", "length"),
    "centimeter": ("cm", "length"),
    "centimeters": ("cm", "length"),
    "m": ("m", "length"),
    "meter": ("m", "length"),
    "meters": ("m", "length"),
    "in": ("in", "length"),
    "inch": ("in", "length"),
    "inches": ("in", "length"),
    "pcs": ("pcs", "count"),
    "pc": ("pcs", "count"),
    "piece": ("pcs", "count"),
    "pieces": ("pcs", "count"),
    "pack": ("pack", "count"),
    "set": ("set", "count"),
    "box": ("box", "count"),
}

_QUANTITY_RE = re.compile(
    r"^\s*(?P<value>\d+(?:[.,]\d+)?)\s*(?P<unit>[a-zA-Z]+)\s*$",
)


class InventoryStatus(StrEnum):
    IN_STOCK = "IN_STOCK"
    LOW_STOCK = "LOW_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    PREORDER = "PREORDER"
    UNKNOWN = "UNKNOWN"


class NormalizedInventory(BaseModel):
    """A normalized inventory snapshot."""

    model_config = ConfigDict(frozen=True)

    status: InventoryStatus
    quantity: int | None = Field(default=None, ge=0)
    raw: str = Field(default="", max_length=200)


_INVENTORY_STATUSES = {
    "in stock": InventoryStatus.IN_STOCK,
    "instock": InventoryStatus.IN_STOCK,
    "available": InventoryStatus.IN_STOCK,
    "有货": InventoryStatus.IN_STOCK,
    "low stock": InventoryStatus.LOW_STOCK,
    "lowstock": InventoryStatus.LOW_STOCK,
    "limited": InventoryStatus.LOW_STOCK,
    "only few left": InventoryStatus.LOW_STOCK,
    "out of stock": InventoryStatus.OUT_OF_STOCK,
    "outofstock": InventoryStatus.OUT_OF_STOCK,
    "sold out": InventoryStatus.OUT_OF_STOCK,
    "unavailable": InventoryStatus.OUT_OF_STOCK,
    "缺货": InventoryStatus.OUT_OF_STOCK,
    "preorder": InventoryStatus.PREORDER,
    "pre-order": InventoryStatus.PREORDER,
    "预订": InventoryStatus.PREORDER,
}

_STOCK_QTY_RE = re.compile(r"(?P<qty>\d+)\s*(?:left|remaining|in stock|available|件|个)", re.I)


class NormalizedTimestamp(BaseModel):
    """A normalized UTC timestamp with explicit parse provenance."""

    model_config = ConfigDict(frozen=True)

    value: datetime
    raw: str = Field(default="", max_length=200)
    had_date: bool = True
    had_time: bool = False


_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%m/%d/%Y",
    "%d/%m/%Y",
    "%d %b %Y",
    "%b %d, %Y",
    "%B %d, %Y",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%SZ",
    "%d/%m/%Y %H:%M",
)

_RELATIVE_TIME_RE = re.compile(
    r"^\s*(?P<num>\d+)\s*(?P<unit>days|day|hours|hour|weeks|week|months|month)\s*ago\s*$",
    re.I,
)


def normalize_money(raw: str | None) -> NormalizedMoney:
    """Parse a money string into a canonical (amount, currency, minor unit)."""
    if raw is None or not raw.strip():
        raise InputError("PARSE", "empty money value")
    text = raw.strip()
    match = _MONEY_RE.match(text)
    if not match:
        # Tolerate a trailing period ("$12.99.") — common in scraped text.
        stripped = text.rstrip(".")
        if stripped and stripped != text:
            match = _MONEY_RE.match(stripped)
            text = stripped
    if not match:
        raise InputError("PARSE", f"cannot parse money: {raw[:80]}")
    symbol = match.group("symbol") or ""
    amount_str = match.group("amount")
    code = match.group("code") or ""
    amount_raw = amount_str
    # Normalize decimal separators: accept "12,99" as 12.99 for non-USD.
    if "," in amount_str and "." not in amount_str:
        amount_raw = amount_str.replace(",", ".")
    amount = float(amount_raw)
    currency_source = code.upper() if code else symbol
    currency = _CURRENCY_CODES.get(currency_source)
    if currency is None:
        raise InputError("PARSE", f"unknown currency: {currency_source}")
    decimal_places = 0 if "." not in amount_raw else len(amount_raw.split(".")[1])
    return NormalizedMoney(
        amount=round(amount, 8),
        currency=currency,
        minor_unit=decimal_places,
        raw=text[:200],
    )


def normalize_quantity(raw: str | None) -> NormalizedQuantity:
    """Parse a quantity string into a canonical unit."""
    if raw is None or not raw.strip():
        raise InputError("PARSE", "empty quantity value")
    text = raw.strip().rstrip(".")
    match = _QUANTITY_RE.match(text)
    if not match:
        raise InputError("PARSE", f"cannot parse quantity: {raw[:80]}")
    unit_raw = match.group("unit").lower()
    canonical = _UNITS.get(unit_raw)
    if canonical is None:
        raise InputError("PARSE", f"unknown unit: {unit_raw}")
    value = float(match.group("value").replace(",", "."))
    canonical_unit, family = canonical
    return NormalizedQuantity(
        value=value,
        unit=canonical_unit,
        family=family,
        raw=text[:200],
    )


def normalize_inventory(raw: str | None) -> NormalizedInventory:
    """Parse an inventory/stock string into a normalized status + quantity."""
    if raw is None or not raw.strip():
        return NormalizedInventory(status=InventoryStatus.UNKNOWN, raw="")
    lowered = raw.strip().lower()
    status: InventoryStatus = InventoryStatus.UNKNOWN
    # Order matters: "low stock" / "out of stock" / "preorder" contain the
    # substring "stock", so check the more specific markers first.
    for marker, mapped in (
        ("out of stock", InventoryStatus.OUT_OF_STOCK),
        ("outofstock", InventoryStatus.OUT_OF_STOCK),
        ("sold out", InventoryStatus.OUT_OF_STOCK),
        ("unavailable", InventoryStatus.OUT_OF_STOCK),
        ("缺货", InventoryStatus.OUT_OF_STOCK),
        ("low stock", InventoryStatus.LOW_STOCK),
        ("lowstock", InventoryStatus.LOW_STOCK),
        ("limited", InventoryStatus.LOW_STOCK),
        ("only few left", InventoryStatus.LOW_STOCK),
        ("left in stock", InventoryStatus.LOW_STOCK),
        ("remaining", InventoryStatus.LOW_STOCK),
        ("preorder", InventoryStatus.PREORDER),
        ("pre-order", InventoryStatus.PREORDER),
        ("预订", InventoryStatus.PREORDER),
        ("in stock", InventoryStatus.IN_STOCK),
        ("instock", InventoryStatus.IN_STOCK),
        ("available", InventoryStatus.IN_STOCK),
        ("有货", InventoryStatus.IN_STOCK),
    ):
        if marker in lowered:
            status = mapped
            break
    quantity: int | None = None
    qty_match = _STOCK_QTY_RE.search(lowered)
    if qty_match:
        quantity = int(qty_match.group("qty"))
    return NormalizedInventory(status=status, quantity=quantity, raw=raw.strip()[:200])


def normalize_timestamp(raw: str | None) -> NormalizedTimestamp:
    """Parse a date/datetime string into a UTC NormalizedTimestamp."""
    if raw is None or not raw.strip():
        raise InputError("PARSE", "empty timestamp value")
    text = raw.strip()
    relative = _RELATIVE_TIME_RE.match(text)
    if relative:
        num = int(relative.group("num"))
        unit = relative.group("unit").lower()
        if unit.startswith("day"):
            delta = timedelta(days=num)
        elif unit.startswith("hour"):
            delta = timedelta(hours=num)
        elif unit.startswith("week"):
            delta = timedelta(weeks=num)
        else:
            delta = timedelta(days=30 * num)
        return NormalizedTimestamp(
            value=datetime.now(UTC) - delta,
            raw=text[:200],
            had_date=True,
            had_time="hour" in unit,
        )
    had_time = False
    for fmt in _DATE_FORMATS:
        try:
            parsed = datetime.strptime(text, fmt)
            had_time = "%H" in fmt
            if fmt.endswith("Z") or fmt.endswith("z"):
                parsed = parsed.replace(tzinfo=UTC)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return NormalizedTimestamp(
                value=parsed,
                raw=text[:200],
                had_date=True,
                had_time=had_time,
            )
        except ValueError:
            continue
    raise InputError("PARSE", f"cannot parse timestamp: {raw[:80]}")
