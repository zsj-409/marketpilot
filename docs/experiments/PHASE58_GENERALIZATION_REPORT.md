# Phase 5.8 Generalization Report — 泛化 Pilot

| Status | Commit | Date |
|---|---|---|
| EXPLORATORY (pilot) | worktree (pre-commit) | 2026-10-29 |

## 1. Pilot 设计（Task 6）

6 种混合机制模板 × 3 seed（7/8/9）= 18 个开发世界，全部确定性生成：

| 模板 | 机制组合 |
|---|---|
| M1 | 隐藏风险 + 差异化研究费用 |
| M2 | 冲突证据 + 缺失关键事实 + 费用差异 |
| M3 | 时间漂移 + 成本约束 |
| M4 | 多候选 + 来源可靠性差异 |
| M5 | 高信息冗余 + 提前停止 |
| M6 | 证据不足 + 合理拒答 |

机器可读：`artifacts/phase58/generalization_pilot.json`。

## 2. 结果（每模板 3 seed 的正确决策数 / 3）

| 模板 | fixed | missing-evidence | uncertainty | adaptive-voi |
|---|---|---|---|---|
| M1 (隐藏风险+费用) | 3/3 | 3/3 | 3/3 | **0/3** (REFUSED) |
| M2 (冲突+缺失) | 0/3 | 0/3 | 0/3 | **3/3** |
| M3 (漂移+约束) | 3/3 | 3/3 | 3/3 | 3/3 |
| M4 (多候选+可靠性) | 0/3 | 0/3 | 0/3 | **3/3** |
| M5 (冗余+提前停) | 3/3 | 3/3 | 3/3 | 3/3 |
| M6 (证据不足) | 3/3 | 3/3 | 3/3 | **0/3** (REFUSED) |

## 3. 关键结论

1. **无普适最优家族**：系统化家族在 M1/M6 胜（3/3），adaptive 在 M2/M4
   胜（3/3），M3/M5 全部正确（无区分）。
2. **Global Best Static = adaptive-voi**（dev 选择），但在 M1/M6 上全拒答
   ——**单一静态家族无法覆盖所有机制**。
3. **Per-World Oracle UB**（诊断）逐模板选最优家族，优于任何单一家族，
   但不可部署。
4. **部分可观测性限制**：M1（需系统化）与 M2（需 adaptive）初始状态特征
   接近，无法可靠路由（见 STATE_FEATURE_SEPARABILITY.md）。

## 4. 评价指标（Task 6 要求）

| 指标 | 定义 | 状态 |
|---|---|---|
| Valid GO Rate | GO / 总决策 | ✓ 报告 |
| Task-Level Regret | best_utility - selected utility（拒答=best_utility） | ✓ |
| Appropriate Abstention Rate | 合理拒答率（证据不足时） | ✓（M6） |
| Unnecessary Abstention Rate | 不必要拒答率（W1/M1 adaptive） | ✓ 分析 |
| Constraint Violation Rate | 硬约束违规 | 0（无违规） |
| Cost per Successful Decision | online cost / GO | ✓ |

## 5. RSI 诊断指标

| 指标 | W1 | W4 |
|---|---|---|
| Replay Coverage | SUPPORTED | SUPPORTED |
| Episode Support Rate | 1.0 | 1.0 |
| Candidate Evaluability | 3/3 dream-evaluated | 3/3 |
| Policy Selection Accuracy | 1/1 正确 | 0/1（选错家族） |
| Promotion/Tie/Regression | 1/2/0 | 0/2/1 |
| Archive Collection Cost | 15.2 (planner) | — |
| Optimization Online Cost | 53.2 | 67.1 |
| Replay Compute Cost | 41.8 | 57.7 |

## 6. 统计方法

- 样本规模：18 世界（6 模板 × 3 seed）——**探索性**，不足以支持稳定
  配对 Bootstrap。
- 按世界类型保留结果（未平均掩盖 W1/W4 相反行为）。
- 若需要正式统计，需扩大 seed 数（≥10 per template）。

## 7. 结论

- **Contextual Hybrid 无独立收益证据**（当前三特征路由在 M1 vs M2 上
  无法区分；Global Best Static 的 adaptive 在 M1/M6 拒答）。
- **Full RSI 无跨世界收益**（W4 选错家族被 Gate 拦截）。
- **保留负结果**：RSI 未超过 Best Static / Random Search。
- **下一步**：需要更丰富的可观察特征（score_gap/uncertainty）参与路由，
  且需更大样本统计验证。
