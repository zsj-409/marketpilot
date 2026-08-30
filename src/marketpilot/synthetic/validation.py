"""Deterministic validation of generated synthetic data."""

from dataclasses import dataclass

from marketpilot.synthetic.models import SyntheticProduct


@dataclass(frozen=True)
class ValidationIssue:
    message: str
    product_id: str | None = None


def validate_dataset(
    products: list[SyntheticProduct],
    *,
    review_count: int,
) -> list[ValidationIssue]:
    """Return every deterministic invariant violation."""

    issues: list[ValidationIssue] = []
    for product in products:
        if product.estimated_cogs + product.fulfillment_cost >= product.selling_price:
            issues.append(
                ValidationIssue(
                    "COGS + fulfillment must be below selling price", str(product.product_id)
                )
            )
        expected_margin = (
            product.selling_price - product.estimated_cogs - product.fulfillment_cost
        ) / product.selling_price
        if abs(expected_margin - product.gross_margin) > 0.001:
            issues.append(
                ValidationIssue(
                    "gross margin is not mathematically consistent", str(product.product_id)
                )
            )
        if not (0 <= product.rating <= 5):
            issues.append(ValidationIssue("rating out of range", str(product.product_id)))
        if not (0 <= product.return_rate <= 1):
            issues.append(ValidationIssue("return rate out of range", str(product.product_id)))
        if product.review_count < 0:
            issues.append(
                ValidationIssue("review count cannot be negative", str(product.product_id))
            )
        if not (0 <= product.latent_opportunity_score <= 1):
            issues.append(
                ValidationIssue("latent opportunity score out of range", str(product.product_id))
            )

    high_volume = [p for p in products if p.monthly_search_volume > 6000]
    low_volume = [p for p in products if p.monthly_search_volume <= 6000]
    if high_volume and low_volume:
        high_competition = sum(p.competition_score for p in high_volume) / len(high_volume)
        low_competition = sum(p.competition_score for p in low_volume) / len(low_volume)
        if high_competition <= low_competition:
            issues.append(
                ValidationIssue(
                    "higher search volume should generally correlate with higher competition"
                )
            )
    if review_count < len(products):
        issues.append(ValidationIssue("dataset should contain at least one review per product"))
    return issues
