# Final Outcome Reconciliation — Outcome 与 Reachability 对账

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. Outcome × Reachability 交叉表（Task 1）

机器可读：`artifacts/locked_eval_audit/outcome_by_reachability.csv`。

### TEST 12 个 ABSTENTION_REQUIRED（scarce, budget=2.0）真实决策

| 方法 | Appropriate Abstain | Wrong GO | Valid GO |
|---|---|---|---|
| fixed | 12 | 0 | 0 |
| missing-evidence | 12 | 0 | 0 |
| uncertainty | 12 | 0 | 0 |
| contextual-hybrid | 6 | 6 | 0 |
| **adaptive-voi** | **3** | **9** | 0 |
| full_info | 0 | 0 | 12（人工填充） |

**关键发现**：
- 系统化家族在 12 个必须拒答世界**全部正确拒答**（预算 2.0 < min 3.0）。
- **adaptive-voi 9/12 错误 GO**（证据不足但被计 WRONG_GO，loss 0.21-0.28
  远低于 abstain 的 1.0）——**它利用 abstention_cost=1.0 > wrong regret
  的漏洞：乱猜比拒答"便宜"**。
- **没有预算违规**：所有方法 spent ≤ 2.0（重建验证 0 违规）。

## 2. WRONG_GO 精确定义（Task 2）

`classify_outcome` 中 WRONG_GO 覆盖**两类混在一起的现象**：

1. **非最优但合法**：证据充分（evidence_sufficient=True）、选非最优商品
   → decision_regret = 正（正确）。
2. **证据不足的错误推荐**：evidence_sufficient=False（含 ABSTENTION_REQUIRED
   世界乱猜）→ 也计 WRONG_GO，loss = regret（0.2-0.3）**而非拒答惩罚**。

**缺陷**：类型 2（不安全推荐）的惩罚（regret≈0.25）远低于合理拒答
（abstention_cost=1.0）——**奖励无证据乱猜、惩罚正确拒答**。

### v2 数量

| 方法 | TEST wrong_go | OOD wrong_go |
|---|---|---|
| fixed/me/unc/ctx | 9 | 6 |
| adaptive-voi | 58（含 9 个证据不足） | 25（全部证据不足？） |
| random/heuristic | 120 | 80 |

## 3. 最小验证测试（Task 2 要求）

- 证据不足但 selected 正确 → 非 Valid GO（已有 `test_insufficient_evidence_no_valid_go`）。
- REFUSED+lucky ≠ 成功（已有）。
- 合理 vs 不必要拒答区分（已有）。

**新增缺口**：WRONG_GO 的"证据不足"子类应有独立 reason_code 与更高
损失（abstention 语义）。**这是 Metric Contract 需修订项**（新版本 v2.1），
不静默修改 v2.0。

## 4. UNRESOLVED 处理（Task 1 末尾）

- 56 UNRESOLVED（drift 36 + ood-drift-conflict 20）在评价中按执行时
  证据充分性报告，**不当作 GO_REACHABLE 也不当作必须拒答**。
- 见 FINAL_LOCKED_PROVENANCE_AUDIT.md 的协议修订说明。
