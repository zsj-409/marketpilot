"""Minimal static product-selection report."""

# ruff: noqa: E501

import html
from pathlib import Path

from marketpilot.product_selection.loop import ProductSelectionResult


def write_product_report(
    output_path: Path,
    goal: str,
    result: ProductSelectionResult,
    candidates: list[dict[str, object]],
) -> None:
    esc = html.escape
    rows = "\n".join(
        f"<li>{esc(str(candidate.get('title', 'unknown')))}</li>" for candidate in candidates
    )
    followups = "\n".join(
        f"<li>{esc(event.worker_role)} -> {esc(event.facet)}</li>"
        for event in result.followup_events
    )
    document = f"""<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>MarketPilot Product Selection</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem;color:#1f2933}}
section{{margin:1.2rem 0}}
</style></head>
<body>
<h1>Product Selection</h1>
<section><strong>Goal:</strong> {esc(goal)}</section>
<section><strong>Termination:</strong> {esc(result.termination.value)}</section>
<section><strong>Research rounds:</strong> {result.research_rounds}</section>
<section><strong>Final selected:</strong> {esc(str(result.final_candidate_id or "none"))}</section>
<section><strong>Verdict:</strong> {esc(result.final_verdict.value if result.final_verdict else "none")}</section>
<section><h2>Candidates</h2><ul>{rows}</ul></section>
<section><h2>Follow-up research</h2><ul>{followups}</ul></section>
</body></html>
"""
    output_path.write_text(document, encoding="utf-8")
