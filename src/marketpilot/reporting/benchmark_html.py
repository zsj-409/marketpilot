"""Static benchmark HTML report."""

# ruff: noqa: E501

import html
from pathlib import Path

from marketpilot.benchmark.models import BenchmarkResult, ExperimentManifest


def render_benchmark_html(
    manifest: ExperimentManifest,
    metrics: dict[str, object],
    results: list[BenchmarkResult],
    output_path: Path,
) -> None:
    """Render a self-contained benchmark report."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    esc = html.escape
    rows = "\n".join(
        f"<tr><td>{esc(r.task_key)}</td><td>{esc(r.family)}</td><td>{esc(r.category)}</td>"
        f"<td>{esc(r.status)}</td><td>{r.regret:.3f}</td><td>{r.top_k_recall:.3f}</td>"
        f"<td>{r.verifier_score:.3f}</td><td>{esc(r.failure.value if r.failure else '')}</td></tr>"
        for r in results
    )
    metric_items = "\n".join(
        f"<div class='metric'><div class='label'>{esc(str(k))}</div>"
        f"<div class='value'>{esc(str(v))}</div></div>"
        for k, v in metrics.items()
        if not isinstance(v, dict)
    )
    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>MarketPilot Benchmark {esc(manifest.experiment_id)}</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem;color:#1f2933}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}
th,td{{border:1px solid #d9e2ec;padding:.45rem;font-size:.85rem;text-align:left}}
th{{background:#f0f4f8}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:1rem}}
.metric{{border:1px solid #d9e2ec;border-radius:.4rem;padding:.8rem}}
.label{{color:#52606d;font-size:.8rem}}
.value{{font-size:1.3rem;font-weight:600}}
</style>
</head>
<body>
<h1>MarketPilot Benchmark</h1>
<p>Suite: {esc(manifest.benchmark_suite)} | Strategy: {esc(manifest.strategy)} | Seed: {manifest.seed}</p>
<p>Synthetic environment decision quality. These results do not describe real market performance.</p>
<div class="grid">{metric_items}</div>
<h2>Tasks</h2>
<table><tr><th>Task</th><th>Family</th><th>Category</th><th>Status</th><th>Regret</th><th>Top-k</th><th>Verifier</th><th>Failure</th></tr>{rows}</table>
</body>
</html>
"""
    output_path.write_text(document, encoding="utf-8")
