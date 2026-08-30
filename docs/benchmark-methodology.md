# Benchmark Methodology

MarketPilot Synthetic Benchmark v1 contains 48 tasks across eight product categories and six task families. Each task includes a goal, market, category, constraints, an environment reference, a research budget, a rubric, and a hidden ground-truth reference.

Evaluation has three levels:

- Structural: run completion, valid DAG, valid references, evidence coverage, tool success.
- Research quality: source diversity, duplicate rate, retrieval success, evidence density, budget compliance.
- Synthetic decision quality: regret, top-k recall, constraint satisfaction, risk recall, ranking correlation, and unsupported-claim rate.

Decision quality compares a selected candidate against hidden synthetic ground truth. Regret is the best available latent opportunity minus the selected latent opportunity. These metrics are labeled explicitly as synthetic-environment decision quality, not real market accuracy.
