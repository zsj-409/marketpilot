# Final Metric Dictionary — 全局指标字典

| Status | Commit | Date |
|---|---|---|
| FROZEN (release v1.0) | worktree (pre-commit) | 2026-10-30 |

## 1. 唯一指标定义（Task A1/A2）

| 指标 | 定义 | 量纲 |
|---|---|---|
| **Supported GO Rate** | (Supported Optimal + Supported Suboptimal) / N | [0,1] |
| Oracle-Optimal Supported GO Rate | 证据充分且 == oracle best / N | [0,1] |
| Supported Suboptimal Rate | 证据充分但 != oracle best / N | [0,1] |
| Unsupported GO Rate | 证据不足的 GO / N | [0,1] |
| Appropriate Abstention Rate | 合理拒答 / N | [0,1] |
| Unnecessary Abstention Rate | 应完成却拒答 / N | [0,1] |
| Hard Constraint Violation Rate | 硬约束违规 / N | [0,1] |
| Task Loss | task_loss_v21 均值（按世界） | [0,∞) |
| Decision Regret | 仅 Supported GO：oracle_best - selected | [0,1] |
| **Cost per Supported GO** | 总执行研究成本 / Supported GO 数 | 成本单位 |
| Cost per Oracle-Optimal | 总执行研究成本 / Optimal GO 数（辅助诊断） | 成本单位 |

**关系**：`Supported GO = Oracle-Optimal Supported GO + Supported Suboptimal GO`。

**0 分母**：无 Supported GO 时 Cost per Supported GO = **N/A**（None），禁止写 0。

## 2. 数值（独立复验 v2.1，新 200 世界）

### TEST (120)

| 方法 | Supported | Optimal | Subopt | Unsup | Abstain | Cost/Supported | Cost/Optimal | Loss |
|---|---|---|---|---|---|---|---|---|
| fixed | **84** | 68 | 16 | 0 | 0.30 | **14.73** | 18.19 | 0.327 |
| missing-evidence | 84 | 68 | 16 | 0 | 0.30 | 14.73 | 18.19 | 0.327 |
| uncertainty | 84 | 68 | 16 | 0 | 0.30 | 14.73 | 18.20 | 0.327 |
| contextual-hybrid | 84 | 68 | 16 | 0 | 0.30 | 14.73 | 18.19 | 0.327 |
| adaptive-voi | **34** | 26 | 8 | 55 | 0.26 | 34.71 | 45.40 | 0.730 |

### OOD (80)

| 方法 | Supported | Optimal | Subopt | Unsup | Abstain | Cost/Supported | Cost/Optimal | Loss |
|---|---|---|---|---|---|---|---|---|
| fixed/me/unc/ctx | **20** | 16 | 4 | 0 | 0.75 | 42.80 | 53.50 | 0.759 |
| adaptive-voi | **0** | 0 | 0 | 32 | 0.60 | **N/A** | N/A | 1.000 |

## 3. 计数闭合（Task A1）

- TEST fixed：68+16+36 = **120** ✓；adaptive：26+8+55+31 = **120** ✓
- OOD fixed：16+4+60 = **80** ✓（未说明的 4 个 = supported suboptimal）
- OOD adaptive：0+0+32+48 = **80** ✓
- closure_ok = True（脚本断言）

## 4. 溯源（Task A3）

- 数据源：`per_world_metrics_v21.csv`（逐任务，从未重算）。
- 新 DEV（seed 900-911）与新 TEST/OOD（500-511 / 700-719）**独立**。
- GBS=fixed 仅依据新 DEV。
- v2.1 在读取新结果前冻结。
- 策略 Hash 评测期间未变。
- Bootstrap 为**任务级**配对（世界为单位）——CI 仅代表本测试集条件，
  **不构成**对所有未知市场机制的统计保证。

机器可读：`final_metric_dictionary.json`。
