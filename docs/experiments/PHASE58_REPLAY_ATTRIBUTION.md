# Phase 5.8 Replay Attribution — Replay 独立价值归因

| Status | Commit | Date |
|---|---|---|
| EXPERIMENTALLY_VALIDATED | worktree (pre-commit) | 2026-10-29 |

## 1. 方法对照（Task 5）

| 方法 | 说明 |
|---|---|
| A. Random Multi-Family Search | 随机家族提议 + live confirmation |
| B. Full Dream-RSI | dream over full pooled history |
| C. Current-History-Only Dream-RSI | dream over current history only |
| D. No-Replay Online Optimization | 提议变体 + live evaluation（无 dream） |
| E. History Feedback (no replay) | 读失败摘要，无 replay simulator |
| F. Global Best Static | Generation DEV 选固定配置 |
| G. Per-World Static Oracle UB | 诊断用 |

机器可读结果：`artifacts/phase58/replay_attribution.json`。

## 2. 结果（confirmation 世界，seed=8）

### W1（隐藏风险）

| 方法 | final decision | correct | regret | promotions |
|---|---|---|---|---|
| Global Best Static (adaptive) | INSUFFICIENT | ✗ | 0.4035 | — |
| Random Search | GO×3 | ✓ | 0.0 | — |
| Full RSI | missing-evidence | ✓ | 0.0 | **1** (r1 IMPROVED) |
| Current-Only RSI | missing-evidence | ✓ | 0.0 | **1** (r1 IMPROVED) |
| History Feedback (fixed) | GO | ✓ | 0.0 | — |

### W4（多候选冲突）

| 方法 | final decision | correct | regret | promotions |
|---|---|---|---|---|
| Global Best Static (adaptive) | GO | ✓ | 0.0 | — |
| Random Search | INSUFFICIENT×3 | ✗ | 0.43 | — |
| Full RSI | adaptive (incumbent) | ✓ | 0.0 | **0** (r1 REGRESSED) |
| Current-Only RSI | adaptive (incumbent) | ✓ | 0.0 | **0** (r1 REGRESSED) |
| History Feedback (fixed) | INSUFFICIENT | ✗ | 0.43 | — |

## 3. 成本账本

| 方法 | W1 online | W1 replay | W4 online | W4 replay |
|---|---|---|---|---|
| Full RSI | 53.2 | 41.8 | 67.1 | 57.7 |
| Current-Only RSI | 45.6 | 34.2 | 48.3 | 38.9 |

- Online = 实际控制器执行（init/proposal/confirmation/promote_dev）。
- Replay = 离线 dream 重放（模拟动作成本）。
- **共享 Archive 的分摊**：Full RSI 与 Current-Only 各自独立建 archive，
  不重复计原始采集成本（同一轨迹重放不重复计费）。

## 4. 回答 Task 5 的 5 个问题

1. **Full RSI 是否比 Random Search 产生更好的独立确认策略？**
   - W1：是（RSI 收敛 missing-evidence GO vs Random 3×GO 也正确，但 RSI
     找到的是**稳定**的正确家族）。
   - W4：**否**（RSI 0 晋级，Random 3×INSUFFICIENT——两者都差于
     adaptive Best Static GO）。**负结果**。
2. **Full RSI 是否比 No-Replay 用更少的新增在线评价资源？**
   - 否——Full RSI online 53.2/67.1 vs Current-Only 45.6/48.3（Full 更多
     因为多一轮 promote_dev 记录）。**无资源效率优势**。
3. **Full Pool 是否比 Current-Only 具有可验证优势？**
   - **否**。W1/W4 上两者 final 策略与晋级数完全相同（Full 只是多记录了
     promote_dev 轨迹）。Full Pool 未带来独立收益。
4. **是否存在历史覆盖提高但策略质量不提高的现象？**
   - **是**。Full RSI 的 archive 覆盖 > Current-Only（多了 promote_dev
     轨迹），但策略质量相同（W1 missing-evidence GO / W4 adaptive GO）。
5. **Contextual Hybrid 是否真正优于统一最佳静态策略？**
   - 见 PHASE58_GENERALIZATION_REPORT.md：泛化 Pilot 上 Global Best Static
     (adaptive) 在 M1/M6 全拒答，而 Contextual Hybrid 未实现多特征路由
     （当前仅 missing_ratio/conflicts/budget_left 三特征），**无独立收益
     证据**（负结果）。

## 5. 结论

**不存在可验证的 Replay 独立收益。** Full Pool 不优于 Current-Only；
RSI 在 W4 上被 Promotion Gate 正确拦截（REGRESSED）；W1 上 RSI 找到的
missing-evidence 与 Random Search 的正确 GO 相同。Replay 机制没有带来
超过普通搜索（Random）的独立收益——**历史数据收益与 Replay 机制收益
未能分离证明**。

**建议**：将 RSI 标记 Experimental；把已验证有效的研究控制器
（missing-evidence，W1 正确 GO）作为默认策略候选。
