# RSI Abstention Evaluation — Phase 5.6

| Status | Commit | Date |
|---|---|---|
| IMPLEMENTED + TESTED | worktree (pre-commit) | 2026-10-29 |

## 1. Outcome 语义（Task A2）

| 结果 | 定义 |
|---|---|
| GO | 满足全部硬约束且完成有效决策（`not refused and not human_review`） |
| REFUSED | 明确因证据不足/预算/安全条件拒绝确定推荐（`refused=True`） |
| INVALID | 违反硬约束、状态非法或执行错误 |

## 2. 关键指标（`AblationOutcome`）

- `decision_success_rate` = GO / total（拒答不算成功）
- `safe_abstention_rate` = REFUSED / total
- `cost_per_successful_decision` = online_cost / n_go（**低成本 REFUSED 不是低成本 GO**）
- n_go / n_refused / n_human_review / n_invalid 计数

## 3. 修复的 REFUSED 误判

**问题**：Phase 5.5 中 `oracle_correct = selected_id == best`，导致 W1 上 adaptive-voi
REFUSED 但 selected_id 碰巧是 best 时被标记 correct=True（误导）。

**修复**（ablations.py）：`oracle_correct = (not refused and not human_review
and selected_id == best)`。REFUSED 的碰巧选中**不算正确决策**。

## 4. W1 低成本拒答（保留的负结果）

W1（隐藏风险）上 adaptive-voi 以 cost 3.8 REFUSED（5 个 seed 全部）：
- 这不是"高效率"——它没有做出决策。
- 系统化策略（fixed/missing/uncertainty）cost 7.6 全部 GO 且正确。
- **结论**：更便宜 ≠ 更优。VOI 排序漏关键 facet 导致证据不足 → 正确拒答，
  但作为"研究策略"它劣于系统化策略（无法完成任务）。

## 5. 测试证据

- `test_refused_is_not_successful_go`：W1 adaptive-voi REFUSED → correct=False
- `test_worse_go_is_regressed`：quality_delta<0 → REGRESSED
- `test_regret_based_quality_delta_different_product_same_utility_is_tie`：
  quality_delta=0 → TIED（同效用不同商品是平局，不是改进）
- `test_tied_does_not_change_active_policy`：TIED 不切换 active

## 6. 状态标记

IMPLEMENTED / TESTED（指标与语义已实现，单元测试通过；多 seed 拒答率见
RSI_PHASE56_RESULTS.md）
