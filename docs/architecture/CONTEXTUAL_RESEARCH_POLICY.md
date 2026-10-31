# Contextual Research Policy — Phase 5.7

| Status | Commit | Date |
|---|---|---|
| IMPLEMENTED + TESTED | worktree (pre-commit) | 2026-10-29 |

## 1. 设计（Task 1.3）

轻量级确定性 Meta-Controller，不训练 LLM，根据**已观察状态**选择下一步研究方式。
`src/marketpilot/optimization/proposer.py::ContextualHybridPolicy`

## 2. 状态特征（允许）

- 关键证据缺失程度：`missing_ratio`（未揭示必需 facet / 总 facet）
- 未解决冲突数：`conflicts`（已揭示证据 vs observable 基线分歧 > 0.15）
- 剩余预算：`budget_left`
- 证据时效：W3 refresh（`_has_time_drift` 自动启用）

## 3. 禁止特征

- world_id / seed（策略选择捷径）
- Oracle 最优商品 ID / 隐藏真实效用
- 未来研究结果 / 最终测试集指标

## 4. 决策规则（确定性）

```python
conflict_threshold = max(1.0, 3.0 - conflict_weight * 2.0)  # conflict_weight 调敏感性
if missing_ratio > 0.5 and budget_left > 3.0:  return "missing-evidence"  # 补关键证据
if conflicts >= conflict_threshold:             return "uncertainty"       # 冲突→核验
if budget_left < 2.0:                           return "fixed"             # 低预算→系统化
return "adaptive-voi"                                                    # 默认
```

## 5. 执行

`ContextualHybridPolicy.execute(view, budget, max_steps)` 选择模式后委托给对应
controller（`controller_for(kind)`），配置世界成本 + W3 refresh + 权重评分。

## 6. 测试证据

- `test_contextual_policy_uses_only_observed_state`: 不同 world_id 相同状态 → 相同决策
- `test_contextual_policy_executes`: 返回有效 ControllerResult
- `test_parameterized_policy_executes_contextual`: ParameterizedPolicy(strategy=
  "contextual-hybrid") 端到端执行

## 7. 状态标记

IMPLEMENTED / TESTED。条件式策略的**独立任务收益**未验证（负结果可能，见
PHASE57_RESULTS.md 基线对照——RSI 在 W4 上收敛到错误家族，条件式未超越最佳静态）。
