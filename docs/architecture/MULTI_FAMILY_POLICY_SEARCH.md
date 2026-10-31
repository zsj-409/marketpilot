# Multi-Family Policy Search — Phase 5.7

| Status | Commit | Date |
|---|---|---|
| IMPLEMENTED + TESTED | worktree (pre-commit) | 2026-10-29 |

## 1. 目标（Task 1）

将 RSI 候选空间从"AdaptiveVOI 参数扰动"扩展到**跨策略家族搜索**，使优化器能发现
Fixed / MissingEvidence / Uncertainty / AdaptiveVOI / Contextual-Hybrid 中更适合
当前任务家族的策略。

## 2. PolicyConfig（强类型配置）

```python
PolicyConfig(strategy, weights, schedule)
```

- `strategy`: fixed / missing-evidence / uncertainty / adaptive-voi / contextual-hybrid
- `weights`: facet 评分权重（PARAM_KEYS 子集）
- `schedule`: 可解释调度参数（voi_threshold / refuse_threshold / conflict_weight /
  research_cost_weight / min_required_evidence / max_research_steps / ...）
- 强类型校验：未知 strategy / weight key / schedule key → ValueError
- 稳定 hash：`sha256(strategy + sorted(weights) + sorted(schedule))`

## 3. MultiFamilyProposer（两阶段候选搜索）

### 阶段 1：离散家族采样
- 从 4 个静态家族（fixed/missing/uncertainty/adaptive-voi）随机采样
- 权重随机扰动（40% 概率每权重 ±[-0.3, 0.9]）

### 阶段 2：家族内扰动 + 条件式
- `param-perturbation`：在 incumbent 家族内扰动权重 ±0.1
- `contextual`：构建 ContextualHybridPolicy（20% 概率）

### 候选来源记录（provenance）
```
incumbent / cross-family:<family> / param-perturbation:<family> / contextual:<hash>
```
每轮批次 = incumbent + 3 个新候选（n_candidates=4，Manifest 控制）。

## 4. ContextualHybridPolicy（Task 1.3）

轻量级确定性元控制器，**只用可观察状态特征**选择研究模式：
- 关键证据缺失度（missing_ratio）
- 未解决冲突数（conflicts，conflict_weight 调阈值）
- 剩余预算（budget_left）

```python
if missing_ratio > 0.5 and budget_left > 3.0: return "missing-evidence"
if conflicts >= threshold:                      return "uncertainty"
if budget_left < 2.0:                           return "fixed"
return "adaptive-voi"
```

**禁止**：world_id / seed / oracle best id / 隐藏效用 / 未来结果 / 测试集指标。

## 5. 关键验证结果

**Multi-Family RSI 在 W1 上首次产生跨家族晋级**（对比 Phase 5.6 的 3× rollback）：
```
round 1 promote tied (cross-family:missing-evidence)
round 2 promote tied
round 3 promote tied (param-perturbation:missing-evidence)
promoted family: missing-evidence
```
跨家族候选（missing-evidence/fixed）在 W1 上通过 confirmation（adaptive-voi 全 REFUSED），
搜索找到了能工作的家族。**这是 Phase 5.7 的核心突破**：策略搜索空间扩大产生真实行为差异。

## 6. 测试证据（test_multi_family_proposer.py, 9 项）

- `test_cross_family_candidates_generated`: 批次含 >1 家族
- `test_incumbent_always_retained`: batch[0] = incumbent
- `test_policy_config_hash_stable_and_distinct`: hash 稳定/区分
- `test_contextual_policy_uses_only_observed_state`: world_id 不影响决策
- `test_contextual_policy_executes` / `test_parameterized_policy_executes_contextual`
- `test_strategy_families_cover_four_baselines`
- `test_different_families_different_behavior`: W1 fixed 成功 vs adaptive REFUSED
- `test_loop_with_proposer_runs`: loop + proposer 端到端

## 7. 状态标记

IMPLEMENTED / TESTED（单元测试通过）。真实实验收益见 PHASE57_RESULTS.md。
