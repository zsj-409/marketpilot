# State Feature Separability Audit — 可观察状态特征能否区分策略

| Status | Commit | Date |
|---|---|---|
| AUDITED | worktree (pre-commit) | 2026-10-29 |

## 1. 可观察特征（ContextualHybridPolicy 实际使用）

以代码为准（`proposer.py` 的 `ContextualHybridPolicy._state_features`）：

| 特征 | 说明 |
|---|---|
| missing_ratio | 关键证据缺失比例（SELECTED 候选） |
| conflicts | 未解决证据冲突数 |
| budget_left | 剩余预算 |
| (score_gap 未用) | 候选评分差距（计算但未参与路由） |
| (uncertainty 未用) | 不确定性（当前实现未用） |
| (estimated_action_cost 未用) | 预计研究成本（未用） |
| (evidence_freshness 未用) | 证据时效（未用） |
| (relevant_action_availability 未用) | 相关动作可用性（未用） |

## 2. 初始状态特征实测（未研究时）

| 世界 | missing_ratio | conflicts | score_gap | n_candidates |
|---|---|---|---|---|
| W1 | 1.00 | 0 | 0.13 | 2 |
| W4 | 1.00 | 0 | 0.08 | 4 |
| W0 | 1.00 | 0 | 0.40 | 2 |

**关键发现**：W1 与 W4 的 missing_ratio/conflicts **完全相同**（1.0/0）。
score_gap（0.13 vs 0.08）和 n_candidates（2 vs 4）是仅有的差异，但不足以
可靠区分——**W1 需要系统化研究（missing-evidence），W4 需要 adaptive
（VOI 排序），而初始状态特征无法揭示这一需求差异**。

## 3. 部分可观测性限制

- **两个不同世界在当前策略可见特征下完全相同，但最优动作不同**：
  W1 初始状态（missing=1.0, conflicts=0, gap=0.13, n=2）与 W4 初始状态
  （missing=1.0, conflicts=0, gap=0.08, n=4）在特征上接近，但最优家族相反
  （W1: systematic; W4: adaptive）。
- 这是**真正的部分可观测性限制**，不是特征工程不足：区分信息（隐藏风险
  的"关键 facet 缺失" vs 多候选的"VOI 排序价值"）只能通过**研究动作揭示**。
- **不允许**通过 world_id/seed 路由（规格禁止）。ContextualHybridPolicy
  不使用 world_id——测试验证。

## 4. 能否通过合法研究动作获取区分信息？

**可以**：W1 中研究 margin/risk 后证据揭示 hidden risk，W4 中研究 demand
后 VOI 排序改变。**但每次研究有成本**（MARGIN 1.5 / RISK 1.3 / DEMAND 1.0）。
要区分 W1 vs W4 至少需要一次带成本的研究动作，且**初始阶段无法知道该
研究是否值得**——这是 Task 2 要求的"测量额外信息是否值得其成本"。

## 5. 结论

1. **不同任务需要不同研究行为时，其观察特征部分可区分**（score_gap/n 有
   差异），但**不足以在初始状态可靠路由**。
2. **特征不同但路由规则没有利用**：score_gap/uncertainty 计算了但未参与
   路由——这是改进空间（可增加"score_gap 小→继续研究"规则）。
3. **隐式泄漏**：无。ContextualHybridPolicy 只用可观察状态，world_id/seed
   不参与决策（测试 `test_no_world_id_leak` 验证）。
4. **诊断动作可行**：一次带成本的研究可提供区分信息，但需权衡成本。

## 6. 改进建议（Phase 5.8 未强制实施）

- 增加 score_gap 到路由特征：score_gap < 0.1 且 n_candidates ≥ 3 → 偏向
  adaptive（多候选需要 VOI 排序）。
- 该规则需在 Generation DEV 上学习阈值，不得针对 W1/W4 写死。
