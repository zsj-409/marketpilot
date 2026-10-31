# Benchmark Validity Report — 有效性自检结果

| Status | Commit | Date |
|---|---|---|
| VALIDATED (pilot) | worktree (pre-commit) | 2026-10-29 |

## 1. 自检结果（60 开发世界，来自 pilot_validity.json）

| 检查 | 结果 |
|---|---|
| 生成确定性 | ✅ 60/60 可复现（同 spec+seed 同 config hash） |
| 正控制：研究改变决策 | ✅ **60/60**（所有世界获取关键证据后决策可改变） |
| Full-Info Oracle 正确 | ✅ 60/60 |
| 可完成 GO | 48/60 |
| 必须拒答（预算不足） | **12/60**（scarce 家族 budget 3.5 < min_cost） |
| 结构多样性 | ✅ 10 家族 × 6 seed = 60 个 config hash 各异的世界 |

## 2. Task 2.1 基线自检

| 方法 | 定义 | 状态 |
|---|---|---|
| Random Selection | 随机选商品（不研究） | 已实现 |
| Simple Heuristic | 观测值最高分（不研究） | 已实现 |
| Full-Information Oracle | 隐藏真值选最优 | ✅ 60/60 |
| Budget-Constrained Oracle | 预算内最便宜优先研究 | 已实现 |
| Fixed/MissingEvidence/AdaptiveVOI | 冻结策略 | 复用 |

## 3. Task 2.2 正/负控制

**正控制**（已实现）：
- 研究改变决策：60/60（Pilot）。
- 研究顺序影响结果：W2 机制（action_costs 不对称）。
- 过期证据刷新：W3（temporal_drift → stale + refresh）。
- 冲突处理：W4/conflict 家族（conflict_with_truth 标志）。

**负控制**（已实现）：
- 信息完整无凭空收益：W0 负控制世界。
- 候选顺序不制造虚假提升：anti-leak shuffle + `test_product_id_order_no_leak`。
- 拒答+lucky selected ≠ Valid GO：`test_refused_with_lucky_selection_is_not_valid_go`。
- 重复证据不无限增价值：evidence_redundancy 参数有界行为。

## 4. Task 2.3 可解性

每个世界记录：feasible_go_path / min_cost_for_best / budget / must_abstain。
Pilot：48 可解 + 12 不可解（拒答必需）。这些信息只供 Evaluator/审计，
不进 Agent 状态。

## 5. Task 2.4 防泄漏

| 泄漏通道 | 防护 |
|---|---|
| world_id | 随机 ID，不编码真值 |
| random seed | 不暴露给 Agent（仅 generator 持有） |
| product_id | 随机 hex + 随机标签前缀（best 无固定位置/前缀） |
| 模板名称 | family 名不参与策略输入 |
| 文件路径 | Agent 无文件访问 |
| 隐藏评分字段 | observable 无 true_utility/true_risk/viable 键（测试验证） |
| 未来观测 | W3 时间戳只暴露当前时间证据 |

**结论**：Benchmark 具有真实信息价值（研究改变决策 60/60），任务难度
分布合理（48 GO + 12 拒答），防泄漏措施有效。
