# World Generation Spec — 世界生成规格

| Status | Commit | Date |
|---|---|---|
| FROZEN (v3) | worktree (pre-commit) | 2026-10-29 |

## 1. 生成流程

`generate_world(spec, seed, world_id, split, family)`：

1. 用 `random.Random(seed)` 初始化确定性 RNG。
2. 生成隐藏真值：best 商品（高 margin/demand/reliability，低 risk/
   competition）+ n-1 个干扰商品（效用递减）。
3. Anti-leak：shuffle 商品顺序 + 随机标签（`p{letter}`），best 不在
   固定位置、ID 前缀不泄漏。
4. 观测模型：observable = truth + gauss(0, noise) + bias。
5. 动作环境：per-facet 成本（base + asymmetry 偏移）。
6. 证据：主来源（可靠）+ 冗余副本 + 冲突来源 + 时间漂移（stale + fresh）。
7. 难度：candidate_utility_gap → EASY/MEDIUM/HARD。

## 2. 隐藏真值

- `TrueProduct`: true_margin/reliability/demand/competition/risk/utility/viable。
- `true_utility = margin * reliability * demand * (1-risk) * (1-comp)`。
- Oracle 最优 = max(true_utility, viable)。

## 3. 确定性

同一 (spec, seed, world_id) → 完全相同的世界（config hash 相同）。
测试：`test_generation_deterministic`。

## 4. 行为验证

| 检查 | 测试 |
|---|---|
| 参数改变行为 | `test_mechanism_parameters_change_behavior` |
| 隐藏真值隔离 | `test_hidden_truth_not_in_agent_view` |
| ID/位置防泄漏 | `test_product_id_order_no_leak` |
| 噪声/可靠性 | `test_source_noise_and_reliability` |
| 时间漂移 | `test_time_drift_creates_stale_and_fresh` |
| 预算不透支 | `test_action_costs_do_not_overrun_budget` |
| 证据不足无 Valid GO | `test_insufficient_evidence_no_valid_go` |
| Oracle 正确 | `test_oracle_correct` |
| 可解性匹配 | `test_solvability_matches_budget` |

## 5. 生成版本

`world_version = "v3-{family}-{spec_hash[:8]}"`。family + spec hash 标识
机制组合，用于 manifest 与 replay 索引。
