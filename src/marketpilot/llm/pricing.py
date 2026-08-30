"""Provider-neutral model pricing."""

from pydantic import BaseModel, Field

from marketpilot.llm.models import LLMUsage


class ModelPrice(BaseModel):
    """Price per one million tokens."""

    input_cost_per_million: float = Field(ge=0)
    output_cost_per_million: float = Field(ge=0)


class PricingCalculator:
    """Calculate estimated cost without embedding business logic in agents."""

    def __init__(self, prices: dict[str, ModelPrice] | None = None) -> None:
        self._prices = prices or {}

    def estimate(self, model: str, usage: LLMUsage) -> float | None:
        price = self._prices.get(model)
        if price is None:
            return None
        return round(
            (
                usage.input_tokens * price.input_cost_per_million
                + usage.output_tokens * price.output_cost_per_million
            )
            / 1_000_000,
            8,
        )
