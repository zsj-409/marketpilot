# Multi-World Dream Evaluator — Phase 5.6

| Status | Commit | Date |
|---|---|---|
| IMPLEMENTED + TESTED | worktree (pre-commit) | 2026-10-29 |

## 1. 设计目标（Task B）

当前 Archive 能保存多轮历史轨迹，但评分仍基于单条 active trajectory。本设计实现
**真正的 Multi-Trace Replay Evaluator**：对历史世界池中的**每条轨迹独立重放**候选策略，
再按世界聚合。

## 2. 接口（`MultiWorldDreamEvaluator.evaluate_policy_on_pool`）

```python
evaluate_policy_on_pool(policy, pool, worlds, *, preference=0.5, budget=10.0)
    -> {
        "policy_hash": str,
        "pool_size": int,
        "per_trace": [ {world_id, world_version, trace_id, round_id,
                        preference, budget, status, decision, selected,
                        regret, cost, attempt_coverage, episode_supported,
                        unsupported_actions, state_mismatches}, ... ],
        "per_world": { world_id: {n_traces, n_supported, mean_regret,
                                   support_rate, statuses} },
        "aggregate": {n_worlds, n_supported_worlds, n_not_evaluable_worlds,
                      mean_world_regret, median_world_regret, worst_world_regret,
                      overall_support_rate},
    }
```

## 3. 核心规则

### B2 每条轨迹独立重放
- 池中每个 trace 用 `observed_trajectory=trace` 独立重放（只该 trace 的记录转移）。
- **禁止**：跨世界证据合并、不同状态动作拼接、未来节点指导、隐藏评分选择动作。
- 状态兼容性检查：`state_signature` 含 world_id/version/time/revealed facets；
  `s{index}` 占位符（legacy）跳过，真实签名严格匹配。

### B3 全历史聚合评分
- 按 `world_id` 分组：**同世界多轨迹不增加统计权重**（`per_world` 各计一次）。
- 每个世界独立计算 mean regret；聚合 = 世界级 mean/median/worst。
- **不**取 `max(all_scores)`；**不**只对成功世界平均。
- 无有效预算权衡的世界显式记录（`n_not_evaluable_worlds`），不静默排除。
- Regret 仅对 SUPPORTED trace 计算（evaluator-side `WorldOracle`）；UNSUPPORTED
  的 regret=None，不计入真实统计（Task C）。

### B4 不使用 Oracle Best-of-Observed
- 主评价用**策略实际执行后 Decision Engine 选择的商品**（`result.selected_id`）。
- 候选 headroom / oracle-best-of-observed 属于诊断上界，不等于部署质量。

## 4. 公式

- 每世界 mean regret: `mean({oracle.regret(selected) for supported traces in world})`
- 世界级聚合: `mean_world_regret = mean({world.mean_regret for worlds with ≥1 supported})`
- 支持率: `overall_support_rate = Σn_supported / Σn_traces`（跨世界）

## 5. 代码位置

- `src/marketpilot/optimization/dream_rsi.py`: `MultiWorldDreamEvaluator`
- `tests/unit/test_multi_world_evaluator.py`: 8 项验收测试（全池重放、世界权重、
  UNSUPPORTED 不计真实 regret、regret-based quality_delta、TIED 语义、单 vs 全池排序）

## 6. 验收测试证据

- `test_multi_world_evaluator_replays_all_traces`: 2 世界 × 2 策略 → 4 traces 全重放
- `test_duplicate_traces_do_not_distort_world_weight`: 3 traces 世界 + 1 trace 世界
  → n_worlds=2（世界权重均等）
- `test_unsupported_trace_not_counted_as_real_regret`: UNSUPPORTED → regret=None,
  n_not_evaluable_worlds=1
- `test_single_trace_vs_full_pool_can_differ`: 全池含 2 世界（断言 per_world 含两者）

## 7. 状态标记

IMPLEMENTED / TESTED（单元测试通过 ≠ 实验收益证据；真实算法收益见
RSI_PHASE56_RESULTS.md）
