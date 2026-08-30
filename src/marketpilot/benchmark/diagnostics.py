"""Offline benchmark diagnostics."""

import csv
import json
import math
from pathlib import Path
from uuid import UUID

from marketpilot.benchmark.strategies import observable_opportunity
from marketpilot.synthetic.environment import SyntheticEnvironment


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) < 2 or len(left) != len(right):
        return 0.0
    left_mean = _mean(left)
    right_mean = _mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right, strict=False))
    left_var = sum((x - left_mean) ** 2 for x in left)
    right_var = sum((y - right_mean) ** 2 for y in right)
    denominator = math.sqrt(left_var * right_var)
    return numerator / denominator if denominator else 0.0


def _spearman(left: list[float], right: list[float]) -> float:
    if len(left) < 2:
        return 0.0

    def ranks(values: list[float]) -> list[float]:
        order = sorted(range(len(values)), key=lambda index: values[index])
        output = [0.0] * len(values)
        for rank, index in enumerate(order):
            output[index] = float(rank)
        return output

    return _pearson(ranks(left), ranks(right))


def compute_saturation_diagnostics(environment: SyntheticEnvironment) -> dict[str, object]:
    rows: list[dict[str, object]] = []
    features = [
        "demand_score",
        "gross_margin",
        "differentiation_score",
        "competition_score",
        "risk_score",
        "monthly_search_volume",
        "seller_count",
        "ad_cpc_proxy",
    ]
    for product in environment.products.values():
        truth = environment.ground_truth_for(product.product_id)
        observation = next(
            item
            for item in environment.observable_products(product.category)
            if item["product_id"] == str(product.product_id)
        )
        rows.append(
            {
                "product_id": str(product.product_id),
                "latent_opportunity": float(str(truth["latent_opportunity_score"])),
                "observable_heuristic": observable_opportunity(observation),
                **{feature: float(str(observation.get(feature, 0.0))) for feature in features},
            }
        )

    latent = [float(str(row["latent_opportunity"])) for row in rows]
    heuristic = [float(str(row["observable_heuristic"])) for row in rows]
    return {
        "product_count": len(rows),
        "latent_heuristic_pearson": _pearson(latent, heuristic),
        "latent_heuristic_spearman": _spearman(latent, heuristic),
        "feature_correlations": {
            feature: _pearson([float(str(row[feature])) for row in rows], latent)
            for feature in features
        },
    }


def compute_verifier_alignment(
    environment: SyntheticEnvironment,
    constraints: dict[str, float],
) -> dict[str, object]:
    from marketpilot.verifier.verifier import verify_recommendation

    scores: list[float] = []
    utilities: list[float] = []
    for category in sorted({product.category for product in environment.products.values()}):
        observations = environment.observable_products(category)
        sources = environment.sources_for_category(category)
        domains = len({source.get("url", "") for source in sources})
        for observation in observations:
            result = verify_recommendation(
                product=observation,
                constraints=constraints,
                evidence_count=1 if sources else 0,
                snapshot_count=1 if sources else 0,
                distinct_domains=domains,
                risk_covered=True,
            )
            truth = environment.ground_truth_for(UUID(str(observation["product_id"])))
            scores.append(result.score.total)
            utilities.append(float(str(truth["latent_opportunity_score"])))
    return {
        "verifier_utility_pearson": _pearson(scores, utilities),
        "verifier_utility_spearman": _spearman(scores, utilities),
        "sample_count": len(scores),
    }


def write_saturation_artifacts(
    environment: SyntheticEnvironment, output_dir: Path
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    diagnostics = compute_saturation_diagnostics(environment)
    (output_dir / "baseline_saturation.json").write_text(
        json.dumps(diagnostics, indent=2), encoding="utf-8"
    )
    with (output_dir / "baseline_saturation.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "product_id",
                "latent_opportunity",
                "observable_heuristic",
                "demand_score",
                "gross_margin",
                "differentiation_score",
                "competition_score",
                "risk_score",
                "monthly_search_volume",
                "seller_count",
                "ad_cpc_proxy",
            ],
        )
        writer.writeheader()
        for product in environment.products.values():
            truth = environment.ground_truth_for(product.product_id)
            observation = next(
                item
                for item in environment.observable_products(product.category)
                if item["product_id"] == str(product.product_id)
            )
            writer.writerow(
                {
                    "product_id": str(product.product_id),
                    "latent_opportunity": truth["latent_opportunity_score"],
                    "observable_heuristic": observable_opportunity(observation),
                    "demand_score": observation.get("demand_score", 0.0),
                    "gross_margin": observation.get("gross_margin", 0.0),
                    "differentiation_score": observation.get("differentiation_score", 0.0),
                    "competition_score": observation.get("competition_score", 0.0),
                    "risk_score": observation.get("risk_score", 0.0),
                    "monthly_search_volume": observation.get("monthly_search_volume", 0),
                    "seller_count": observation.get("seller_count", 0),
                    "ad_cpc_proxy": observation.get("ad_cpc_proxy", 0.0),
                }
            )
    return diagnostics
