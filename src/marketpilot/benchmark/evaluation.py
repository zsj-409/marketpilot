"""Business-level synthetic decision quality evaluation."""

from uuid import UUID

from marketpilot.synthetic.environment import SyntheticEnvironment


def evaluate_selection(
    environment: SyntheticEnvironment,
    category: str,
    selected: list[UUID],
    constraints: dict[str, float],
) -> dict[str, float | bool]:
    """Compare agent selection against hidden synthetic ground truth."""

    products = environment.observable_products(category)
    product_by_id = {UUID(str(item["product_id"])): item for item in products}
    opportunities = {
        UUID(str(item["product_id"])): float(
            str(
                environment.ground_truth_for(UUID(str(item["product_id"])))[
                    "latent_opportunity_score"
                ]
            )
        )
        for item in products
    }
    risks = {
        UUID(str(item["product_id"])): float(
            str(environment.ground_truth_for(UUID(str(item["product_id"])))["latent_risk_score"])
        )
        for item in products
    }
    if not opportunities:
        return {}

    best_available = max(opportunities.values())
    selected_opportunities = [opportunities.get(item, 0.0) for item in selected[:3]]
    selected_opportunity = max(selected_opportunities) if selected_opportunities else 0.0
    regret = best_available - selected_opportunity

    top_k_ids = sorted(opportunities, key=lambda item: opportunities[item], reverse=True)[:3]
    top_k_recall = len(set(selected[:3]) & set(top_k_ids)) / len(top_k_ids)

    minimum_margin = float(constraints.get("minimum_margin", 0.0))
    maximum_risk = float(constraints.get("maximum_risk", 1.0))
    selected_product = product_by_id.get(selected[0]) if selected else None
    if selected_product is None:
        constraint_satisfied = False
        risk_recall = 0.0
    else:
        margin = float(selected_product.get("gross_margin", 0.0))
        risk = risks.get(selected[0], 0.0)
        constraint_satisfied = margin >= minimum_margin and risk <= maximum_risk
        risk_recall = 1.0 if risk >= 0.5 else 0.0

    if len(selected) > 1 and len(selected) == len(opportunities):
        rank_truth = sorted(
            opportunities,
            key=lambda item: opportunities[item],
            reverse=True,
        )
        pairs = min(len(selected), len(rank_truth))
        concordant = sum(
            1
            for i in range(pairs)
            for j in range(i + 1, pairs)
            if (selected.index(rank_truth[i]) - selected.index(rank_truth[j])) * (i - j) > 0
        )
        total_pairs = pairs * (pairs - 1) / 2
        ranking_correlation = concordant / total_pairs if total_pairs else 0.0
    else:
        ranking_correlation = 0.0

    return {
        "best_available_opportunity": best_available,
        "selected_opportunity": selected_opportunity,
        "regret": regret,
        "top_k_recall": top_k_recall,
        "constraint_satisfied": bool(constraint_satisfied),
        "risk_recall": risk_recall,
        "ranking_correlation": ranking_correlation,
    }
