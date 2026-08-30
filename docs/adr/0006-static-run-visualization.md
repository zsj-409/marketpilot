# ADR-0006: Static Run Visualization Artifact

## Context

Developers need to inspect a run without a server, database, or live network. A frontend application would add deployment complexity before the research benchmark exists.

## Decision

Generate a self-contained `report.html` from run artifacts using a Python report builder and embedded HTML/CSS. Keep the report data model separate from rendering.

## Alternatives

1. Build a React/Next.js frontend.
2. Use a hosted visualization service.
3. Require a Jupyter notebook.

## Consequences

### Positive

- offline and portable
- no frontend build pipeline
- simple to generate and test
- prepares a clean data model for a future UI

### Negative

- Visual design is intentionally minimal.

## Status

Accepted.
