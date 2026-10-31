# Phase 5 Exit Audit — 评测正确性收口审计

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-29 |

## 1. 本轮修复清单

| 问题 | 严重性 | 修复 |
|---|---|---|
| Replay 盲目 GO（不查证据充分性） | P0 (Task 2.1) | replay 复用家族充分性判定 |
| Replay 丢 product_id（多候选错重放） | P0 (Task 2.1) | ObservedStep.product_id + 记录/重放 |
| 无统一结果分类（INSUFFICIENT 混淆） | P0 (Task 1.1) | evaluation/outcomes.py 6 类分类器 |
| Regret 与 Abstention 混用 | P0 (Task 1.2) | decision_regret / abstention_cost / task_loss 分离 |
| W4 dream 虚高（replay 修复前） | P0 (Task 2.3) | 修复后 dream=0.4 < 0.5 → gate 拦截 |

## 2. Task 1 统一语义结论

- **6 类结果**：VALID_GO / WRONG_GO / APPROPRIATE_ABSTENTION /
  UNNECESSARY_ABSTENTION / CONSTRAINT_VIOLATION / INVALID（outcomes.py）。
- **INSUFFICIENT 永不成功**：refused=False 也进 abstention 分支。
- **REFUSED+lucky selected ≠ 零 regret**：abstention_cost=1.0 替代。
- **证据不足的 GO = WRONG_GO**（不安全推荐）。
- ABSTENTION_COST/WEIGHT 已冻结（实验前）。

## 3. Task 1.3：M6 审查

**M6 实际是 W1 的别名**（`build_diagnostic_world(kind="W1")`），不是独立
的"证据不足"机制。3 seed 上：
- 系统化家族 3/3 GO 且 **evidence_sufficient=True**（真研究全部关键
  facet）→ **真正有效**，不是碰巧选中。
- adaptive 3/3 INSUFFICIENT（refused=True）且 evidence_sufficient=False →
  **APPROPRIATE_ABSTENTION（合理拒答）**。
- **结论**：系统化 3/3 GO 有效，adaptive 拒答合理。但"M6 证据不足"标签
  有误导性——真正的证据不足机制需预算严格受限让所有策略无法获取充分
  证据。**报告勘误**：M6 标签改为"W1 别名（隐藏风险）"，旧结果保留。

## 4. Task 2 Replay Fidelity 结论

见 REPLAY_FIDELITY_REPORT.md：两个 P0 缺陷已修复，24/24 决策一致。
W4 差异归因为 DEV_CONFIRMATION_GAP（dream 评分 vs confirmation 实例），
非 Replay Bug。

## 5. Task 3 Promotion Gate 结论

- REGRESSED / TIED → rollback（active hash 不变）✓
- IMPROVED / EFFICIENCY_GAIN → promote（active 切换）✓
- CONFIRMATION_EXHAUSTED → fail-closed（不晋级）✓
- 单元级 + 集成级测试覆盖（test_exit_gate.py）。

## 6. Task 4 No-Replay 对照（Task 4.3）

| 世界 | No-Replay | Full RSI | 结论 |
|---|---|---|---|
| W1 | 3/3 GO, online 22.8 | 1 promo, online 53.2+41.8 | No-Replay 更便宜同质量 |
| W4 | 0/3, online 31.8 | 0 promo, online 57.7+57.7 | 两者同失败 |

**A. 历史重放改变策略选择？** W1 是，但质量无差异（No-Replay 也 3/3 GO）。
**B. 减少在线评价？** 否（RSI online > No-Replay）。
**C. 计入采集成本后总成本优势？** 否（RSI 95+ vs No-Replay 22.8）。

## 7. Task 5 Coverage 真实性

- Unique Transition / Distinct Branch / Attempt Coverage / Episode Support /
  Coverage Gain per New Execution 已区分。
- W5 上 fixed vs adaptive 产生不同 (action, product_id) 分支（`test_new_branch_not_duplicate_counted`）。
- 重复轨迹不增覆盖（已有测试）。
- **Attempt Coverage=1.0 只表示被尝试动作获支持，不代表全合法动作空间
  被探索**——需负控制测试（未观察动作显式 UNSUPPORTED，`test_replay_unsupported_marked`）。

## 8. Task 7 输入稳定性

复用已有测试：test_input_layer.py（货币/数量/库存/时间戳/约束）、
test_canonicalization.py（同义 URL 规范化）、test_diagnostic_worlds.py
（W3 过期证据 refresh、W4 冲突来源）。未新增重复测试。

## 9. 测试

260 passed, 1 skipped（+5 exit-gate 新测试）。Ruff/mypy 全绿（139 源文件）。
