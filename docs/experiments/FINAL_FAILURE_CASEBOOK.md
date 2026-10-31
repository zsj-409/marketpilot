# Final Failure Casebook — 失败案例集

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 案例统计（failure_cases.json，11 例）

- wrong_go_sufficient_evidence: 10 例（证据充分但选错商品）。
- fixed_ood_degradation: 1 例（聚合）。

## 2. 代表性案例

### 案例 1：wrong_go_sufficient_evidence（TEST）

- 方法：adaptive-voi / missing-evidence / uncertainty
- 场景：证据充分（margin/demand/risk 全 revealed）但**最终评分选错商品**
- 根因：噪声证据使 composite score 排名偏离隐藏真值（候选效用差小
  multi-cand 家族 gap=0.08，噪声 0.3 可翻转排名）
- 影响：regret 正（接近最优的轻微错选）

### 案例 2：fixed_ood_degradation（聚合，OOD）

- 方法：fixed
- 场景：ood-src-toolfail（低可靠性 + 高缺失）60/80 abstain
- 根因：固定研究顺序按"先 margin 后 demand 后 risk"执行，低可靠性
  来源频繁返回缺失/冲突 → fixed 无法完成必需证据 → 全部拒答
- 影响：Task Loss 61.21（OOD），远高于动态策略 3.01

### 案例 3：premature_abstention（潜在）

- 未在最终数据中触发（abstain 的世界 cost 都接近 budget）
- 但 cheapest_first 的 120/120 全拒答是**系统性"研究不足"**：只按最便宜
  顺序研究，从未研究够选中候选的必需证据 → 这是"启发式局限"而非
  "合理拒答"

## 3. 因果归因限制（Task 9）

- 以上失败均来自**受控合成世界**的确定性执行。
- 反事实（如"若研究不同 facet 是否选对"）可用于诊断，但**不得**将
  合成环境干预描述为真实商业环境的因果效应。
- RSI dream 高但确认失败的具体案例见 FINAL_RSI_ATTRIBUTION_REPORT
  （W4: dream 0.4 < 0.5 gate 拦截）。

## 4. 数据结构（每案例）

world_id / split / category / method / budget / cost / task_loss /
regret / evidence_sufficient / detail。
