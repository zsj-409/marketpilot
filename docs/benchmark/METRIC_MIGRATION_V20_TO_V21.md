# Metric Migration v2.0 → v2.1

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 迁移原因

**v2.0 缺陷**：WRONG_GO 混合两类现象（证据充分非最优 + 证据不足乱猜），
且证据不足的错误 GO 损失仅 regret（≈0.25）远低于合理拒答（1.0）——
**奖励无证据乱猜、惩罚正确拒答**。

审计发现：adaptive-voi 在 12 个 ABSTENTION_REQUIRED 世界 9 次错误 GO
（利用此漏洞）。

## 2. 语义变更

| 旧（v2.0） | 新（v2.1） |
|---|---|
| WRONG_GO（证据不足）= regret | **unsupported_go** = max(regret, 1.0) |
| WRONG_GO（非最优）= regret | **supported_suboptimal_go** = regret（有效推荐） |
| 合理拒答 = 1.0 | 不变（1.0） |
| 不必要拒答 = 1.0 | **1.5**（+0.5 机会损失） |
| 约束违规 = 未单列 | **1.5**（独立） |

## 3. 历史数据兼容

- v2.0 的旧结果（含 INVALIDATED 原始 + POST-AUDIT v2）保留，**不重算**。
- 新 reason_code 只影响**新**评价（v2.1 独立复验）。
- 旧 `task_loss`（v2.0 语义）与 `task_loss_v21` 并存，聚合时按版本选择。

## 4. 诊断口径拆分（Task 2.2）

旧 WRONG_GO 拆分为：
- supported_suboptimal_go（证据充分，非最优）——**有效推荐**。
- unsupported_go（证据不足）——**不安全推荐**。

历史诊断报告（FINAL_OUTCOME_RECONCILIATION）的"wrong_go_sufficient_evidence"
现对应 supported_suboptimal_go；"证据不足乱猜"对应 unsupported_go。

## 5. 影响

- **adaptive-voi 在 scarce 世界的 9 个错误 GO**：v2.1 下 loss 从 0.25 →
  1.0（与拒答相同）——不再有乱猜红利。
- **系统化家族**：无 unsupported_go（都正确拒答或研究充分）——不受影响。
- v2.1 下策略排名可能变化（惩罚不安全推荐），**新独立测试验证**。
