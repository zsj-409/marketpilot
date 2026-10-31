# Final Results Integrity Audit — 最终结果完整性审计

| Status | Commit | Date |
|---|---|---|
| **INVALIDATED (original) → re-evaluated (v2)** | worktree (pre-commit) | 2026-10-30 |

## 1. 审计结论

**原始 Locked Evaluation（Commit 2522aec 的 `per_world_metrics_final.csv`）存在 P0 执行正确性缺陷，核心性能结论无效。**

**验收状态：INVALIDATED（原始结果作废）→ 已用正确执行重新评价（v2）。**

## 2. P0 缺陷：共享 AgentWorldView（证据泄漏）

`run_locked_evaluation.py` 的 `_eval_world` 和 `run_locked_baselines.py` 在
方法循环**外**创建**一个** `AgentWorldView(w)`，然后 fixed / missing-evidence /
uncertainty / adaptive-voi / contextual-hybrid **全部共享**。

后果：
- fixed 先执行 → revealed 全部证据（cost 12.0）。
- 后续方法复用已污染的 view → `_sufficient(view)` 已 True → **0 步直接 GO，
  cost=0.0**。
- 原始 CSV 中 missing/uncertainty/adaptive/contextual 的 **cost=0.0 且
  valid_go=97** 是假数据（白嫖 fixed 的研究成果）。

**证据**：balanced-300 原始 CSV 显示 uncertainty cost=0.0 valid_go；正确
重建显示 cost=12.0（12 步真实研究）。

## 3. 影响范围

| 项 | 原始（无效） | v2（正确） |
|---|---|---|
| TEST valid_go（uncertainty） | 97 | 75 |
| TEST valid_go（adaptive-voi） | 97 | **28** |
| OOD valid_go（adaptive-voi） | 64 | **0** |
| GBS（DEV 选择） | uncertainty | **fixed** |
| 配对 A（adaptive vs fixed） | diff=-0.44（显著优） | diff=+0.049（不显著，方向反转） |
| 配对 B（contextual vs GBS） | diff=-0.023（略优） | diff=0.0（无差异） |
| cost/valid（uncertainty） | 0.25 | 16.47 |

## 4. 修复

- 每方法新建 `AgentWorldView(w)`（两个脚本）。
- 新结果写入独立目录 `artifacts/locked_eval_v2/`（原始保留）。
- v2 数据文件：`per_world_metrics_v2.csv` / `dev_baselines.csv` /
  `method_summary.json` / `paired_comparisons.csv` / `figures/` /
  `failure_cases.json` / `frozen_policy_registry.json`（GBS=fixed）。

## 5. v2 核心结果（正确执行）

### TEST (120)
| 方法 | Valid | Wrong | Abstain | Loss | Cost/Valid |
|---|---|---|---|---|---|
| fixed | 75 | 9 | 36 | 37.69 | 16.5 |
| missing-evidence | 75 | 9 | 36 | 37.69 | 16.5 |
| uncertainty | 75 | 9 | 36 | 37.69 | 16.47 |
| contextual-hybrid | 75 | 9 | 36 | 37.69 | 16.5 |
| adaptive-voi | **28** | 58 | 34 | 47.62 | 42.6 |
| full_info | 120 | 0 | 0 | 0.00 | 0.0 |

### OOD (80)
| 方法 | Valid | Wrong | Abstain | Loss |
|---|---|---|---|---|
| 系统化家族（fixed/me/unc/ctx） | 14 | 6 | 60 | 61.21 |
| adaptive-voi | **0** | 25 | 55 | 61.02 |
| full_info | 80 | 0 | 0 | 0.00 |

## 6. 关键结论（v2）

1. **adaptive-voi 在正确执行下是最差方法**（TEST 28/120 valid，OOD 0/80）——
   它按 VOI 排序只研究部分 facet，预算内研究不足 → 大量 abstain/wrong。
2. **系统化家族（fixed/missing/uncertainty/contextual）质量相同**（75/120）——
   在预算 12 下都研究全部候选 → 相同决策。
3. **ContextualHybrid 与 GBS(fixed) 无差异**（diff=0.0）——预算充足时
   contextual 的规则总是选 fixed 行为。
4. **无任何方法显著优于其他**（配对 CI 均含 0）。

## 7. 对先前结论的作废

- ❌ "adaptive-voi 最优（loss 7.18）" → 作废（实际最差）。
- ❌ "uncertainty 默认推荐（0.25/valid）" → 作废（实际 16.47，与 fixed 同）。
- ❌ "配对 A/B 显著" → 作废（v2 不显著）。
- ✅ "fixed 在 OOD 退化" → 保留（v2 仍显示 60/80 abstain）。
- ✅ "cheapest_first 全拒答" → 保留。
- ✅ "random/heuristic 无研究=WRONG_GO" → 保留。
