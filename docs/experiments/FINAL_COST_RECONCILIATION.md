# Final Cost Reconciliation — 成本对账

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 从真实动作重建成本（Task 3）

机器可读：`artifacts/locked_eval_audit/cost_recomputed_from_actions.csv`
（每世界每方法：n_actions / sum_step_costs / result_total_cost / budget /
outcome）。

**方法**：重跑每个冻结策略，从 `result.steps` 累加每步真实成本
（facet × product_id × cost），独立于 `result.total_cost` 验证。

## 2. 重建结果 vs 原始报告

| 方法 | 原始 TEST cost/valid | 重建（正确）TEST cost/valid | 原始 valid | 重建 valid |
|---|---|---|---|---|
| fixed | 16.50 | 16.50 | 75 | 75 |
| missing-evidence | 1.84 | 16.50 | 97 | 75 |
| uncertainty | 0.25 | 16.47 | 97 | 75 |
| adaptive-voi | 1.73 | 42.60 | 97 | 28 |
| contextual-hybrid | 0.37 | 16.50 | 97 | 75 |

**原始的低 cost/valid（0.25-1.84）是共享 view 假象**——方法 0 步执行
（cost=0）白嫖 fixed 证据。正确执行下所有系统化家族 cost/valid≈16.5
（研究全部候选的必需 facet）。

## 3. Uncertainty 0.25/valid 的真实计算依据

**不存在**。原始 0.25 = 24.0 总成本 / 97 valid（假 valid）。正确：
uncertainty 实际研究全部候选（12 步，cost 12.0/世界），TEST 75 valid，
cost/valid = 1235.4/75 = 16.47。

## 4. 预算违规检查（Task 3）

重建验证 `spent + next_action_cost <= budget`：
**0 违规**（200 世界 × 5 方法全部满足）。Task 1.3 的预算修复（世界
research_budget 生效）在 v2 中确认有效。

## 5. OOD 零成本成功？

原始 OOD 中 uncertainty/contextual cost/valid=0.0 —— **也是假数据**。
正确：OOD 系统化家族 14 valid，cost/valid=61.14（研究成本高因低可靠性
来源频繁返回缺失需重试研究）。

## 6. 结论

- **v2 成本数据可信**（从动作重建，与 result.total_cost 一致）。
- 原始成本指标全部作废（共享 view 导致）。
- 无预算违规（0 例）。
- cost/valid 排名（v2）：系统化家族 16.5（TEST）≈ 61（OOD）；adaptive-voi
  42.6（TEST）最贵且质量最差。
