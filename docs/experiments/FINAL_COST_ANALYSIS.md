# Final Cost Analysis — 成本分析报告

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 成本口径（Metric Contract v2.0）

合成环境预算单位，**不换算为真实美元**（无真实 API 调用）。

## 2. 执行成本（TEST 120 + OOD 80，冻结策略）

| 方法 | TEST 总成本 | TEST Cost/Valid | OOD 总成本 | OOD Cost/Valid |
|---|---|---|---|---|
| fixed | 1237.2 | 16.50 | 无 | 61.14 |
| missing-evidence | 178.8 | 1.84 | 无 | 8.38 |
| uncertainty | 24.0 | 0.25 | 0.0 | 0.00 |
| adaptive-voi | 167.6 | 1.73 | 无 | 3.75 |
| contextual-hybrid | 36.0 | 0.37 | 0.0 | 0.00 |
| cheapest_first | 1244.4 | —（0 valid） | 无 | — |

**uncertainty 成本最低**（TEST 24.0 总量 / 0.25 per valid）——它只研究
分歧最大的 facet，通常 1-2 步就够。

## 3. 优化效率成本（Phase 5.7/5.8 预算匹配）

| 方法 | W1 Online | W1 Replay | W4 Online |
|---|---|---|---|
| Full RSI | 53.2 | 41.8 | 57.7 |
| Current-Only RSI | 45.6 | 34.2 | 48.3 |
| Random Search | 22.8 | 0 | 31.8 |
| No-Replay | 22.8 | 0 | 31.8 |

**Replay 计算成本（41.8-57.7）未带来质量收益**——这是 RSI 的额外开销
而非独立优势。

## 4. 成本—质量权衡（Task 6）

- **TEST 上**：adaptive-voi 质量最优（loss 7.18）但成本中等（1.73/valid）；
  uncertainty 质量次优（loss 14.01）但成本极低（0.25/valid）。
- **OOD 上**：uncertainty/contextual 成本 0.0（0.25/valid 级）且质量
  与 adaptive 相同（64 valid）。
- **Pareto 前沿**（figures/quality_cost_pareto.png）：uncertainty 在
  低成本端，adaptive-voi 在高质量端；无单一方同时最优。

## 5. 结论

- **推荐默认生产控制器：uncertainty**（质量 80%+，成本最低，OOD 鲁棒）。
- **adaptive-voi**：质量最优（TEST loss 最低）但成本更高，适合质量敏感
  场景。
- **fixed**：成本高（16.5/valid）且 OOD 退化——不推荐。
- **RSI**：额外 41-58 预算的 Replay 计算无独立收益——保持 Experimental。
