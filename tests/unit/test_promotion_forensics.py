"""Promotion forensics smoke tests."""

import json
from pathlib import Path

from marketpilot.evaluation.promotion_forensics import run_promotion_forensics
from marketpilot.synthetic.generator import SyntheticMarketGenerator


def test_promotion_forensics_runs_offline(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "datasets" / "synthetic-market-v1"
    SyntheticMarketGenerator(seed=17, products_per_category=4).write(dataset_dir)
    products = json.loads(
        (dataset_dir / "products.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    ranking = [products["product_id"]]
    records = [
        {
            "task_key": "test-hard",
            "category": products["category"],
            "difficulty": "hard",
            "policy": "static-ranking",
            "ranking": ranking,
            "metrics": {"input_tokens": 1, "output_tokens": 1},
            "trajectory_wall_latency_ms": 1.0,
            "evidence": "test",
        }
    ]
    branch_records = tmp_path / "branch_records.jsonl"
    branch_records.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8"
    )
    report = run_promotion_forensics(dataset_dir, branch_records, tmp_path)
    assert report.results
    assert (tmp_path / "promotion_forensics.json").exists()
