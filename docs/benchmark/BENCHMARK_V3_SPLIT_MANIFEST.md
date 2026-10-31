# Benchmark v3.1 Split Manifest — 440 世界数据划分清单

| Status | Commit | Date |
|---|---|---|
| FROZEN | worktree (pre-commit) | 2026-10-29 |

## 1. 数据划分（Task 6）

| Split | 数量 | 构成 |
|---|---|---|
| Generation DEV | 160 | 10 ID 家族 × 16 seed（100-115） |
| Confirmation DEV | 80 | 10 ID 家族 × 8 seed（200-207） |
| Held-out TEST | 120 | 10 ID 家族 × 12 seed（300-311） |
| OOD Stress TEST | 80 | 4 OOD 组合 × 20 seed（400-419） |
| **总计** | **440** | |

## 2. ID 机制家族（10，每家族 16/8/12）

conflict / noisy / asym-cost / redundant / drift / scarce / multi-cand /
strict / cheap / balanced —— 每家族 dev 16 + conf 8 + test 12。

## 3. OOD 机制组合（4，每组合 20）

- ood-drift-conflict：时间漂移 + 冲突证据。
- ood-risk-asym：隐藏风险 + 不对称成本。
- ood-multi-ambiguity：8 候选 + 实体歧义（高噪声高偏差）。
- ood-src-toolfail：低可靠性 + 高缺失（工具失败模拟）。

## 4. 独立性验证（Task 6.1）

- **440 个唯一 world hash**（无重复市场实例）。
- **0 个跨分区 spec+seed 重复**（同一潜在市场不跨分区）。
- 每个世界记录：world_family / latent_market_group / mechanism_tags /
  generator_version / generator_seed / source_template_group /
  difficulty_band / split / world_hash。

## 5. Reachability 分布

| Split | GO | ABSTAIN | UNRESOLVED |
|---|---|---|---|
| DEV | 144 | 16 | 0 |
| Conf | 72 | 8 | 0 |
| TEST | 108 | 12 | 0 |
| OOD | 80 | 0 | 0 |

## 6. Manifest

`benchmark_v31_manifest.json`（BenchmarkManifest）：
benchmark_version / generator_version / evaluator_version /
metric_contract_version / git_commit / execution_mode=frozen /
world_ids / world_config_hashes / seed_registry / research_budget /
dataset_split_hash。

`split_manifest_v31.json`：split_counts / seed_ranges / rows（含每世界
reachability 判定）/ reachability_stats / dataset_split_hash。
