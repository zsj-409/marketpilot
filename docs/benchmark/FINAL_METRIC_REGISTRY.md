# Final Metric Registry — 正式指标注册表

| Status | Commit | Date |
|---|---|---|
| FROZEN (v1.0) | worktree (pre-commit) | 2026-10-29 |

## 1. 主要指标（Task 3，预注册）

| 指标 | 定义 | 来源 |
|---|---|---|
| Valid GO Rate | VALID_GO / 总任务 | OutcomeClassifier |
| Task-Level Loss | task_loss 均值 | outcomes.py |
| Decision Regret on Valid GO | 仅 VALID_GO 的 regret 均值 | WorldOracle |
| Appropriate Abstention Rate | APPROPRIATE_ABSTENTION / 总任务 | OutcomeClassifier |
| Unnecessary Abstention Rate | UNNECESSARY_ABSTENTION / 总任务 | OutcomeClassifier |
| Hard Constraint Violation Rate | CONSTRAINT_VIOLATION / 总任务 | OutcomeClassifier |
| Cost per Successful Decision | online cost / VALID_GO | ExecutionLedger |

## 2. 次要指标

Evidence Sufficiency / Evidence Precision / Citation Validity /
Source Freshness / Tool Failure Rate / Replay Support / Action Cost /
Runtime Latency / Replay Coverage / Episode Support / Candidate Evaluability /
Promotion-Tie-Regression / P50-P95 Latency / Total Dev Cost /
Archive Collection Cost / Replay Compute Cost。

## 3. Outcome reason_code（Task 3）

区分商品选择错误 vs 证据不足：
- `wrong_product`：证据充分但选错商品（WRONG_GO）。
- `insufficient_evidence`：证据不足导致无效推荐（APPROPRIATE/WRONG）。
- `constraint_violation`：硬约束违规。
- `execution_error`：执行失败。

## 4. 成本口径（Task 3）

| 类别 | 定义 |
|---|---|
| 真实 API 费用 | 无真实 API（离线 mock）——**不得声称合成预算=美元** |
| 合成环境动作预算 | World.action_costs（研究动作成本） |
| 历史轨迹采集费用 | ArchiveCoveragePlanner.total_collection_cost |
| 虚拟 Replay Action Cost | replay 的 simulated_action 预算 |
| Replay 实际计算费用 | ExecutionLedger.replay_total（离线计算） |

## 5. 冻结规则

- `abstention_cost=1.0`：审查量纲——decision_regret ∈ [0, best_utility]
  （~0-0.4），abstention_cost=1.0 偏大（拒答惩罚 > 最差决策 regret）。
  **修订建议**：abstention_cost 应在 Locked Test 前调整为与效用归一化
  同量纲（如 best_utility 均值），或保留 1.0 作为"拒答代价高于任何错误
  决策"的保守业务假设。**需在正式 Benchmark 前决策**（v1.0 冻结）。
- 不得事后静默调整；修订需新协议版本。

## 6. 状态

v1.0 冻结（Pilot 用）。abstention_cost 量纲问题标记为**待决策项**，
必须在 Locked Test 前解决。
