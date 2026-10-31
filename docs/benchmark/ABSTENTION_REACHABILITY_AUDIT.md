# Abstention Reachability Audit — 拒答标签可达性审计

| Status | Commit | Date |
|---|---|---|
| AUDITED + CORRECTED | worktree (pre-commit) | 2026-10-29 |

## 1. 旧标签错误（Task 1.3）

**Benchmark v3 Pilot 报告的"12 个 MUST_ABSTAIN"全部错误。**

旧逻辑：`min_cost = Σ(所有候选 × 3 个关键 facet 成本)`，若 > budget 则
must_abstain。这误把"研究所有候选"当作必要前提——**实际只需研究最终
选中候选的 3 个关键 facet**（margin+demand+risk ≈ 3.0），即可作出合法
推荐。

验证：scarce budget=3.5 时，精确可达性 Oracle 判定 **GO_REACHABLE
（min_cost=3.0）**——12/12 全部可 GO，不是拒答。

## 2. 修正

- v3.1：scarce 家族 budget 降至 2.0（< 最小 3.0）。
- 精确 Oracle 验证：**6/6 scarce 世界 ABSTENTION_REQUIRED**（全空间
  穷举证明无预算内 GO 路径）。
- solvability.must_abstain 改用精确 Oracle 判定（非 min_cost 启发式）。

## 3. 440 世界拒答分布（精确验证）

| Split | GO_REACHABLE | ABSTENTION_REQUIRED | UNRESOLVED |
|---|---|---|---|
| Generation DEV (160) | 144 | 16 | 0 |
| Confirmation DEV (80) | 72 | 8 | 0 |
| Held-out TEST (120) | 108 | 12 | 0 |
| OOD (80) | 80 | 0 | 0 |
| **总计** | **404** | **36** | **0** |

- 36 个 ABSTENTION_REQUIRED 全部来自 scarce 家族（budget=2.0）。
- **0 UNRESOLVED**：所有世界状态空间可穷举（小型确定性世界）。

## 4. 关键语义

- **ABSTENTION_REQUIRED**：全状态空间穷举证明不存在预算内合法 GO 路径。
- **GO_REACHABLE**：存在合法路径（min_cost 精确）。
- **UNRESOLVED**：不伪造——未找到 ≠ 必须拒答（440 世界无此情况）。

## 5. 旧报告勘误

BENCHMARK_V3_PILOT_REPORT.md 的"48 GO + 12 拒答"是 v3 旧标签。v3.1 修正
为 54 GO + 6 拒答（60 世界 Pilot）。新旧不可直接比较（标签语义不同）。
