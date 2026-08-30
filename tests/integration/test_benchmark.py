"""Benchmark runner integration test."""

from pathlib import Path

from marketpilot.benchmark.runner import BenchmarkRunner
from marketpilot.synthetic.generator import SyntheticMarketGenerator


def test_benchmark_runner_writes_artifacts(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "datasets" / "synthetic-market-v1"
    SyntheticMarketGenerator(seed=5, products_per_category=4).write(dataset_dir)
    runner = BenchmarkRunner(
        datasets_dir=tmp_path / "datasets",
        output_dir=tmp_path / "benchmark_runs",
        suite_name="marketpilot-synthetic-v1",
        strategy_name="baseline",
    )
    manifest, results, metrics = runner.run()
    assert len(results) == 48
    assert (tmp_path / "benchmark_runs" / manifest.experiment_id / "benchmark.html").exists()
    assert metrics["task_count"] == 48
