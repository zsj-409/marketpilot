# Phase 5.7 Ablation Report — 跨家族搜索消融

| Status | Commit | Date |
|---|---|---|
| EXPERIMENTALLY_VALIDATED (exploratory) | worktree (pre-commit) | 2026-10-29 |

## 1. 消融维度

| 维度 | 对照 |
|---|---|
| 策略家族 | fixed / missing-evidence / uncertainty / adaptive-voi / contextual-hybrid |
| 搜索机制 | 单家族扰动（Phase 5.6） vs 跨家族搜索（Phase 5.7） |
| 历史池 | Full Pool vs Current-History-Only vs No-Replay |
| 候选来源 | incumbent / cross-family / param-perturbation / contextual |

## 2. 核心消融结果

### 2.1 跨家族搜索 vs 单家族扰动（W1）

| 机制 | W1 结果 |
|---|---|
| Phase 5.6 单家族（adaptive 系） | 3× rollback（0 晋级） |
| Phase 5.7 跨家族 | **3× promote**（收敛到 missing-evidence） |

**跨家族搜索在 W1 上解锁了晋级**：adaptive-voi 全 REFUSED，但 missing-evidence /
fixed 能正确 GO —— 搜索空间扩大是晋级的前提。

### 2.2 家族表现（W1 / W4，来自 baseline_comparison.json）

| 家族 | W1 | W4 |
|---|---|---|
| fixed | GO 正确 7.6 | INSUFFICIENT 10.7 |
| missing-evidence | GO 正确 7.6 | INSUFFICIENT 10.7 |
| uncertainty | GO 正确 7.6 | INSUFFICIENT 10.4 |
| adaptive-voi | REFUSED 3.8 | **GO 正确 9.4** |

**不同世界族需要不同家族**：W1 系统化胜、W4 adaptive 胜。**没有普适最优家族**。

### 2.3 RSI 收敛 vs Best Static（诚实负结果）

| 世界 | Best Static | Random Search | Full RSI |
|---|---|---|---|
| W1 | fixed (7.6) | missing-evidence (7.6) | missing-evidence (7.6) ✅ 持平 |
| W4 | adaptive-voi (9.4) | adaptive-voi (9.4) | missing-evidence (10.7) ❌ **劣于静态** |

**W4 上 RSI 选错家族**：replay 评价信号（基于 dev 轨迹）与 confirmation 真实评价
不一致，导致 RSI 收敛到 W4 上无效的 missing-evidence。

## 3. 结论

1. 跨家族搜索**必要且有效**：解锁 W1 晋级。
2. RSI 的**家族选择不总是优于静态/随机**：W4 上劣于 Best Static（负结果）。
3. 根因：replay 信号与真实确认评价的偏差（搜索-确认 gap）。

## 4. 状态标记

EXPERIMENTALLY_VALIDATED（探索性，W1+W4 两个世界族）。NOT_VALIDATED：多世界统计。
