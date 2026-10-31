# Task Outcome Contract — 统一结果分类与 Regret/Abstention 语义

| Status | Commit | Date |
|---|---|---|
| FROZEN | worktree (pre-commit) | 2026-10-29 |

## 1. 统一结果分类（Task 1.1）

`src/marketpilot/evaluation/outcomes.py` 定义 6 类业务结果：

| OutcomeStatus | 判定规则 |
|---|---|
| VALID_GO | decision=GO 且证据充分（required facets 全 revealed）且 selected=oracle best |
| WRONG_GO | GO 但 selected≠best，或 GO 但证据不足（不安全推荐） |
| APPROPRIATE_ABSTENTION | refused/human_review/INSUFFICIENT 且证据不足（合理拒答） |
| UNNECESSARY_ABSTENTION | refused/human_review/INSUFFICIENT 且证据已足够（不必要拒答） |
| CONSTRAINT_VIOLATION | 硬约束违规（预算超限等） |
| INVALID | 执行错误 / 非法状态 / UNKNOWN |

### 关键保证

- **INSUFFICIENT 不因 refused=False 计为成功**：`decision == "INSUFFICIENT"` 直接进入 abstention 分支。
- **REFUSED 但 selected_id 碰巧是 Oracle 最优**：**不计为有效 GO**（abstention_cost 替代 decision_regret）。
- **已选正确商品但证据不足**：WRONG_GO（不安全推荐），不自动视为可执行推荐。
- **INVALID 不能通过低费用获晋级优势**：INVALID 的 task_loss=ABSTENTION_COST（固定），不因 cost 低而减少。

## 2. 分离 Regret 与 Abstention Cost（Task 1.2）

| 字段 | 定义 | 适用 |
|---|---|---|
| decision_regret | best_utility - selected_utility | 仅 VALID_GO/WRONG_GO |
| abstention_cost | 预声明拒答代价 = 1.0（冻结） | abstention/INVALID |
| task_loss | 综合损失（decision_regret 或 abstention_cost） | 任务级比较 |
| outcome_status | 实际业务状态 | 全部 |
| evidence_sufficient | required facets 是否全 revealed | 全部 |

**冻结规则**：ABSTENTION_COST=1.0、ABSTENTION_WEIGHT=1.0 在实验前冻结，**不得在看到 Full RSI 结果后调整**。

## 3. 量纲可比性

- decision_regret ∈ [0, best_utility]（世界内归一）。
- abstention_cost = 1.0 固定（业务代价）。
- task_loss 用同一尺度（abstention 也归一为 1.0），跨世界可比。

## 4. 原始多维指标（不只综合分）

每个 episode 同时报告：outcome_status / decision_regret / abstention_cost /
evidence_sufficient / total_cost / selected_id / decision。综合 task_loss
只是辅助。

## 5. 与历史报告的兼容性说明

**新旧指标不可直接比较**：
- 旧报告（Phase 5.7/5.8）用 `oracle.regret(selected_id)`（REFUSED 时也
  用 selected 的 regret，若碰巧正确则 0）。
- 新合同用 abstention_cost（REFUSED 一律 1.0 task_loss）。
- 旧报告 replay 盲目 GO（不查证据充分性）；新合同 replay 与真实
  controller 同规则（INSUFFICIENT 一致）。
- 历史原始结果保留，不覆盖；此合同仅约束**新**实验。

## 6. 测试

`test_exit_gate.py` 覆盖：refused+lucky ≠ VALID_GO、不足证据 GO ≠ 有效、
APPROPRIATE vs UNNECESSARY 区分、WRONG_GO 正 regret。
