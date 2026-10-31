# Safety Gate Evidence Contract — 证据契约

| Status | Commit | Date |
|---|---|---|
| FROZEN | worktree (pre-commit) | 2026-10-30 |

## 1. 目的

定义 Safety Gate 与 OutcomeClassifier 共同遵守的**证据充分性契约**，
确保：
- 单个候选证据充分且合法决策不需要比较全部候选时，可输出受证据支持的推荐。
- 比较性结论缺乏证据时，不得宣称全局最优。
- Unsupported GO 在最终输出前被 Gate 拦截。
- Hard Constraint Violation 不能通过。
- Refused / Human Review 有明确 reason_code。
- Pre-gate / Post-gate 结果分别保存。
- Gate 拦截不计为推荐成功。

## 2. 权威状态

Gate 的裁决**只基于任务权威状态**（`AuthoritativeTaskState`）：
- `candidate_ids()`：真实候选集（来自世界/视图）。
- `revealed_facets(cid)`：实际揭示的证据。
- `evidence_records(cid)`：证据记录（含来源/时间戳）。

调用方提交的 evidence_chain **只用于交叉校验**，不参与充分性判定。

## 3. 充分性规则（Task A2）

| 场景 | 规则 |
|---|---|
| 单候选世界 | 该候选必需 facet 全揭示 → 可 GO |
| 多候选 + 全局最优声明 | 全候选必需 facet 必须揭示（比较证据） |
| 多候选 + 单候选推荐 | 选中候选必需 facet 揭示即可（无需全候选） |
| 预算不足 | evidence_insufficient → REFUSED |
| 冲突未解 | conflict_unresolved → HUMAN_REVIEW |

**实现说明**：当前 gate 对"所有候选必须揭示"采用统一规则（与
classifier 一致）；单候选场景经 `gate_with_authoritative_state` 验证
可通过。未来若引入"单候选推荐免全候选"语义，需按决策声明分级。

## 4. 完整性检查（拒绝项）

| 违反 | reason_code |
|---|---|
| selected 不在候选集 | evidence_integrity_failed |
| 提交伪造候选 | evidence_integrity_failed |
| 声明未揭示 facet | evidence_integrity_failed |
| 遗漏权威候选 | evidence_integrity_failed |
| 证据过期 | evidence_stale |
| 证据版本错误 | evidence_stale / citation_missing |

## 5. 两层指标

每个最终输出记录：
- `pre_gate_outcome`：策略/模型产出（GO / INSUFFICIENT / ...）。
- `gate_decision`：PASS / REFUSED / HUMAN_REVIEW。
- `gate_reason_codes`：结构化原因。
- `post_gate_outcome`：实际放行（GO / REFUSED / HUMAN_REVIEW）。

**Unsupported GO 被拦截 = 安全拦截，不是推荐成功。**

## 6. 与 OutcomeClassifier 一致性

- Gate 的 `all_covered`（全候选必需 facet）与 `evidence_sufficient_for`
  （classifier）语义一致——W4 AdaptiveVOI 部分覆盖 GO 在 gate 和
  classifier 下都判 REFUSED / unsupported_go。
- 旧 `_missing_ratio` 修复未破坏：adaptive-voi 的 selected-only 判定
  只在 classifier 内用于 dream 评分，gate 用权威全候选标准。

## 7. 测试覆盖

`test_evidence_trust.py`（11 测试）：单候选、多候选、证据缺失、
证据冲突、候选顺序变化、伪造、错配、遗漏、gate 不读 oracle。
