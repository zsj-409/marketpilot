"""Dataset and benchmark loading helpers."""

from pathlib import Path

from marketpilot.benchmark.models import BenchmarkSuite
from marketpilot.benchmark.suite import build_synthetic_suite


def load_benchmark_suite(
    suite_name: str,
    datasets_dir: Path,
) -> BenchmarkSuite:
    """Load or construct a benchmark suite."""

    if suite_name == "marketpilot-synthetic-v1":
        dataset_dir = datasets_dir / "synthetic-market-v1"
        if not (dataset_dir / "manifest.json").exists():
            raise FileNotFoundError(
                f"dataset not found at {dataset_dir}; run `marketpilot dataset generate` first"
            )
        return build_synthetic_suite(suite_name, "v1")
    raise ValueError(f"unknown benchmark suite: {suite_name}")
