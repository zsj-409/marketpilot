# Metric Contract v2.1

| Status | Commit | Date |
|---|---|---|
| FROZEN (pre-registered) | worktree (pre-commit) | 2026-10-30 |

## 1. 与 v2.0 的差异（Task 2）

| 项 | v2.0 | v2.1 |
|---|---|---|
| GO 语义 | WRONG_GO 混两类 | **reason_code 拆分**（supported_valid / supported_suboptimal / unsupported） |
| 非最优 GO | 计 WRONG_GO（无区分） | **SUPPORTED_SUBOPTIMAL_GO**（有效推荐 + 正 regret） |
| 证据不足 GO 损失 | regret（≈0.25，低于拒答） | **UNSUPPORTED_GO_LOSS ≥ abstention_cost**（安全优先） |
| 不必要拒答 | 1.0 | **1.0 + OPPORTUNITY_LOSS(0.5)** |
| 约束违规 | 未单独罚 | **CONSTRAINT_VIOLATION_LOSS(1.5)** |
| 主要指标 | Task Loss v2.0 | **Task Loss v2.1**（task_loss_v21） |

## 2. 结果分类（Task 2.1，reason_code）

| reason_code | 含义 | 损失 |
|---|---|---|
| supported_valid_go | 硬约束满足 + 证据充分 + Oracle 最优 | 0 |
| supported_suboptimal_go | 合法 + 证据充分 + 非最优 | decision_regret |
| unsupported_go | 证据不足却输出推荐 | **max(regret, 1.0)** |
| constraint_violation | 硬约束违规 | 1.5 |
| appropriate_abstention | 合理拒答（证据不足） | 1.0 |
| unnecessary_abstention | 应完成却过早拒答 | 1.5 |
| invalid | 运行异常 | 1.0 |

## 3. 关键原则（Task 2.2/2.3）

- **非最优 ≠ 无效**：证据充分的非最优 GO 是有效推荐（regret 正）。
- **安全优先**：UNSUPPORTED_GO 损失 ≥ 合理拒答（不得因碰巧高效用获低损失）。
- **合理拒答不被过度惩罚**：与不安全推荐同代价。
- **不必要拒答不完全免费**：+0.5 机会损失（防无限拒答）。
- **多指标优先**：Valid GO Rate / Unsupported GO Rate / Constraint Violation
  Rate / Regret / Cost 均报告；Task Loss v2.1 为预注册综合辅助指标。

## 4. 冻结声明

- 常量（ABSTENTION_COST_V21=1.0, UNSUPPORTED_GO_LOSS=1.0,
  OPPORTUNITY_LOSS=0.5, CONSTRAINT_VIOLATION_LOSS=1.5）在读取新独立
  测试结果前冻结。
- **不得**根据旧 TEST 哪个策略获胜选择权重（旧 TEST 已 INVALIDATED）。
- 修订需新版本号 + 迁移说明。

## 5. 实现

`src/marketpilot/evaluation/outcomes.py`：
- `TaskOutcome.reason_code`（新字段）。
- `classify_outcome` 填充 reason_code。
- `task_loss_v21(outcome)`（v2.1 损失函数）。

机器可读：`METRIC_CONTRACT_V21.json`。
