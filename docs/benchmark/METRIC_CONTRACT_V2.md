# Metric Contract v2.0 — 指标协议（修订版）

| Status | Commit | Date |
|---|---|---|
| FROZEN (v2.0) | worktree (pre-commit) | 2026-10-29 |

## 1. 与 v1.0 的差异（Task 2）

| 项 | v1.0 | v2.0 |
|---|---|---|
| abstention_cost | 1.0 无条件 | 按结果类型区分 |
| must_abstain 判定 | min_cost 启发式 | **精确可达性 Oracle** |
| Budgeted Oracle | 最便宜优先（误称最优） | 拆分为 3 种方法 |
| 迁移 | — | v1.0 → v2.0：拒答语义修正，旧数据不可直接比较 |

## 2. Task Loss 语义（Task 2.2）

| 结果类型 | Task Loss |
|---|---|
| Valid GO | 归一化 Decision Regret（0 为最优） |
| Wrong GO | Decision Regret（正） |
| Appropriate Abstention | **安全拒答业务代价**（abstention_cost） |
| Unnecessary Abstention | **任务机会损失**（高于安全拒答代价） |
| Constraint Violation | **独立违规代价**（严格） |
| Invalid | **明确失败损失** |

**abstention_cost=1.0 不是错误**——它代表"拒答代价高于任何错误决策"
的保守业务偏好，量纲为业务损失单位（与 decision_regret 的效用量纲
分离说明：decision_regret ∈ [0, best_utility]，abstention_cost 是
独立的业务惩罚）。**合理拒答与不必要拒答价值不同**：unnecessary >
appropriate（机会损失 > 安全代价）。

## 3. 主要指标（不变）

Valid GO Rate / Task-Level Loss / Decision Regret on Valid GO /
Appropriate Abstention Rate / Unnecessary Abstention Rate /
Hard Constraint Violation Rate / Cost per Successful Decision。

## 4. 成本口径（不变）

真实 API 费用 / 合成预算 / 采集费用 / 虚拟 Replay / Replay 计算——分离，
合成预算不冒充美元。

## 5. 非劣容忍度（Task 2.3）

- 质量非劣容忍度：|quality_delta| ≤ 1e-6 → TIED。
- 成本非劣：cost_delta < -1e-6 → EFFICIENCY_GAIN。
- **冻结于本协议，Locked Test 前不再调整**。

## 6. 冻结声明

本协议 v2.0 在查看任何 Locked Test 结果前冻结。修订需新版本号 +
迁移说明。
