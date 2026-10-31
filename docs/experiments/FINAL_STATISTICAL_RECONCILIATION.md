# Final Statistical Reconciliation — 统计对账

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 原始配对统计（无效）

| 比较 | 原始 diff | 原始 CI95 | 结论（无效） |
|---|---|---|---|
| A: adaptive vs fixed | -0.4436 | [-0.513, -0.375] | "显著优于" |
| B: contextual vs GBS | -0.0228 | [-0.042, -0.007] | "略优" |

原始差异基于**共享 view 的假数据**（adaptive/contextual 0 步 GO）→ 作废。

## 2. v2 配对统计（正确，per_world_metrics_v2.csv）

| 比较 | v2 diff (A-B) | CI95 | 结论 |
|---|---|---|---|
| A: adaptive vs fixed | **+0.0487** | [-0.026, +0.130] | **不显著，方向反转**（adaptive 更差） |
| B: contextual vs GBS(fixed) | **0.0** | [0.0, 0.0] | **无差异**（同 75 valid 同 loss） |
| C/D/E | NOT_EVALUATED | — | 优化效率另报 |

**v2 中无任何主比较显著**（CI 均含 0）。

## 3. TEST-only / OOD-only / pooled 拆分（Task 4 要求）

机器可读：`artifacts/locked_eval_audit/split_specific_paired_differences.csv`。

| 比较 | TEST-only | OOD-only | pooled (120:80) |
|---|---|---|---|
| adaptive vs fixed | +0.099（adaptive 更差） | -0.005 | +0.049 |
| contextual vs GBS | 0.0 | 0.0 | 0.0 |

- **pooled = (120×TEST_diff + 80×OOD_diff)/200**，权重 120:80。
- TEST-only 显示 adaptive 在 TEST 明显更差（loss 47.6 vs 37.7）。

## 4. 组成指标差异（Task 4）

| 指标 | adaptive vs fixed (TEST) |
|---|---|
| Valid GO Rate diff | -0.39（28/120 vs 75/120） |
| Wrong GO Rate diff | +0.41（58 vs 9） |
| Abstention Rate diff | -0.02（34 vs 36） |
| Task Loss diff | +9.93（47.6 vs 37.7） |
| Cost diff | +25.1/valid |

**adaptive 的"低 loss"改善从未发生**——v2 中它 valid 更少、wrong 更多、
成本更高。

## 5. ContextualHybrid 与 AdaptiveVOI 的 loss 是否来自 abstention→wrong

- 原始：是（假数据）。
- v2：adaptive 的 wrong_go 从 9 增至 58（真实执行研究不足），abstain 34；
  **无"低 loss"现象**——adaptive loss 47.6 高于系统化 37.7。

## 6. 统计方法合规

- Bootstrap：世界级配对差异，2000 次，95% CI，seed=42——合规。
- 分层分析：未作为主检验（EXPLORATORY 标记）。
- 抽样单位：世界（非轨迹/Replay 节点）——合规。

## 7. 结论

原始统计结论（A/B 显著）**作废**。v2：无显著差异；adaptive-voi 方向性更差。
