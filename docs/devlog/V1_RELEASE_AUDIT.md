# MarketPilot v1 Independent Release Audit

## Verdict

```text
READY FOR MARKETPILOT-V1
```

## Audit Method

The auditor re-ran static checks, tests, deterministic dataset generation, and benchmark commands, then inspected synthetic generation, evaluator formulas, verifier inference, benchmark leakage surfaces, README claims, and generated artifacts.

## Claims Checked

1. Baseline saturation was genuinely diagnosed: PASS. Artifacts in `artifacts/diagnostics/baseline_saturation.json` show perfect coupling before hardening and partial correlation after hardening.
2. Hidden ground truth does not leak into Agent-visible state: PASS. `products.jsonl` contains no `latent_*` fields; latent data lives only in `ground_truth.jsonl`, read only by offline evaluators.
3. Easy/medium/hard difficulty is meaningful: PASS. Tasks carry difficulty, and `SyntheticEnvironment.observable_products` applies controlled masking and deterministic noise.
4. Benchmark generation is deterministic: PASS. Two seed-42 runs produced identical aggregate metrics.
5. Synthetic reviews are causally coherent rather than random filler: PASS. Review topics are derived from product flags and return rates.
6. Verifier never sees latent utility during inference: PASS. The verifier uses only observable features and constraints.
7. Verifier/utility correlation is computed only offline: PASS. `benchmark/diagnostics.py` is an offline analysis path.
8. Candidate generation and selector quality are separated: PARTIAL. Selection quality is analyzed; a full per-rollout candidate-generation separation remains future work.
9. Oracle selection is analysis-only: PASS. No oracle score is available during inference.
10. Fixed vs Adaptive ablation is real: PASS with limitation. Adaptive adds tool cost and changes hard-task ranking, but no quality gain.
11. No Memory vs Episodic vs Skill ablation is real: PASS with limitation. Memory strategies perform retrieval and storage but do not change ranking in this environment.
12. N=1/2/4 experiments use the claimed mechanism: PASS with limitation. They are deterministic heuristic candidate scaling, explicitly labeled as such.
13. Deterministic heuristic variants are not mislabeled as independent LLM samples: PASS.
14. Quality/cost metrics are calculated correctly: PASS. Tool calls are a deterministic proxy.
15. README claims match generated results: PASS. Tables and finding statements match artifacts.
16. benchmark.html matches machine-readable results: PASS.
17. Reproducibility commands work: PASS.
18. CI remains offline: PASS.
19. No credentials or secrets appear in artifacts: PASS.
20. Release tag status: NEEDS UPDATE. An earlier `marketpilot-v1` tag exists from the prior sprint and must be moved to the final hardened commit.

## Issues

### LOW

- `marketpilot-v1` tag currently points at a pre-hardening commit and must be recreated at the final release commit.
- Oracle/random/verifier selection diagnostics are summarized qualitatively rather than emitted as a full machine-readable matrix.

### MEDIUM

- Candidate generation vs selection failure is not yet fully separated at rollout granularity.

## Conclusion

The hardening sprint addressed the original formula-coupling leakage, expanded review data, added difficulty tiers, produced honest ablations, and documented a clear negative result: verifier score is weakly aligned with hidden decision utility. The repository is credible as a deterministic, reproducible research platform, provided the release tag is moved to the final commit.
