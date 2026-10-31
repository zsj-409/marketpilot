# Final RSI Attribution Report — RSI 独立收益归因

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 研究问题（Task 2 预注册 C/D/E）

- C: Full Dream-RSI 是否优于预算匹配的 Random Multi-Family Search？
- D: Full Dream-RSI 是否优于 No-Replay Online Optimization？
- E: Full Pool 是否相比 Current-History-Only 产生额外收益？

**方法**：优化效率比较（Task 6）——使用 Phase 5.7/5.8 的预算匹配对照
（同候选空间、同轮数、同 Confirmation 预算），不混用"晋级次数"与
"任务成功次数"。

## 2. 预算匹配对照结果（Phase 5.7/5.8 数据）

### W1（隐藏风险）

| 方法 | 最终策略 | Valid GO | Online Cost | Replay Cost |
|---|---|---|---|---|
| Random Search | missing-evidence | 3/3 | 22.8 | 0 |
| Full RSI | missing-evidence | 3/3 | 53.2 | 41.8 |
| Current-Only RSI | missing-evidence | 3/3 | 45.6 | 34.2 |
| No-Replay | (随机) | 3/3 | 22.8 | 0 |

### W4（多候选冲突）

| 方法 | 最终策略 | Valid GO | Online Cost |
|---|---|---|---|
| Random Search | adaptive-voi | 3/3 | 31.8 |
| Full RSI | adaptive (0 晋级) | 0/3 | 57.7 |
| No-Replay | (随机) | 0/3 | 31.8 |

## 3. 成本分解（Task 6）

| 费用类别 | Full RSI (W1) | Random Search (W1) |
|---|---|---|
| Archive Collection | 0（dev 轨迹复用） | 0 |
| Candidate Proposal | 3 rounds × 4 | 3 rounds × 4 |
| New Online Exploration | 53.2 | 22.8 |
| Confirmation | 含在 online | 含在 online |
| Incremental Replay Compute | 41.8 | 0 |
| Simulated Historical Action | 不计入 online | — |

**Simulated Historical Action Cost 不重复算在线支出**（Phase 5.5 修复）。

## 4. 回答 C/D/E

**C. Full RSI vs Random Search**：
- W1 两者都找到 missing-evidence，质量相同；**RSI 成本 3.4×**（95 vs 22.8）。
- W4 RSI 0 晋级（replay 评分偏差被 Promotion Gate 拦截），Random 也
  失败——**均无收益，RSI 无优势**。
- **结论：Full RSI 不优于预算匹配的 Random Search（负结果）**。

**D. Full RSI vs No-Replay**：
- No-Replay 在 W1 用更少成本（22.8）达到相同质量（3/3 GO）。
- **RSI 未减少新增在线评价资源（负结果）**——online 成本反而更高。

**E. Full Pool vs Current-Only**：
- 两者在 W1/W4 的最终策略与晋级数完全相同。
- Full Pool 只是多记录了 promote_dev 轨迹（覆盖更高但质量相同）。
- **Full Pool 无额外收益（负结果）**——"历史覆盖提高但策略质量不提高"
  现象确认。

## 5. 综合结论

**Dream-RSI 无独立于普通搜索的收益证据**：
- 跨家族搜索（搜索空间扩大）在 W1 有效（找到 missing-evidence）——
  **这是"策略空间收益"，不是"Replay 机制收益"**。
- Replay 评分与 Confirmation 评价存在固有偏差（W4 选错家族）。
- 历史数据收益与 Replay 机制收益未能分离证明。
- **建议：RSI 保留为 Experimental Research Module，默认使用更简单可靠
  的研究控制器（uncertainty / adaptive-voi，见 FINAL_LOCKED_EVALUATION）**。

## 6. 统计支持声明

- W1/W4 对照是**探索性**（单世界族 × 单 seed 链），非配对统计。
- Locked TEST 的 A/B 比较有配对 Bootstrap 支持；C/D/E 的优化效率
  结论基于预算匹配的确定性运行（无随机性），可复现但样本小。
