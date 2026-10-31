# Budgeted Oracle Audit — 预算约束 Oracle 审计

| Status | Commit | Date |
|---|---|---|
| AUDITED + FIXED | worktree (pre-commit) | 2026-10-29 |

## 1. 三种方法区分（Task 1.1）

| 方法 | 定义 | 性质 |
|---|---|---|
| CheapestFirstHeuristic | 预算内最便宜优先研究 | **启发式**（非最优） |
| FullInformationOracle | 隐藏真值直接选最优 | 理论上界 |
| ExactBudgetedReachabilityOracle | 精确枚举预算内合法路径 | **精确可达性**（离线审计） |

## 2. 实际实现

- `CheapestFirstHeuristic`（validity.py `_cheapest_first_heuristic`）：
  按成本升序研究 (facet, product)，预算内停止，用 revealed evidence 评分
  决策。**可能错过可行 GO 路径**（动作顺序非最优）。
- `FullInformationOracle`（`_full_info_oracle`）：直接选 oracle best，
  revealed_facets 全填（evidence-sufficient）。
- `ExactBudgetedReachabilityOracle`（新增类）：Dijkstra 式搜索
  (revealed-set, spent) 状态空间，**第一个 GO 即最小成本路径**。判定
  GO_REACHABLE / ABSTENTION_REQUIRED（全空间穷举证明）/ UNRESOLVED
  （状态上限，不伪造拒答）。

## 3. 旧实现的错误

**v3 的 `_budget_oracle` 被当作"预算约束最优 Oracle"报告，实际是
CheapestFirstHeuristic**——它不是最优：动作顺序影响可达性。

v3.1 修正：改名 CheapestFirstHeuristic + 新增精确 Oracle（Task 1.2）。

## 4. 精确可达性语义（Task 1.2）

- 枚举合法研究动作，严格执行 budget + max_steps。
- 状态 = 已揭示证据集（facet, product）——重复研究被集合去重（防循环）。
- 记忆化：同一 revealed 集只访问一次（Dijkstra 按成本优先）。
- 判定：
  - GO_REACHABLE：存在预算内合法 GO 路径（min_cost 精确）。
  - ABSTENTION_REQUIRED：**全空间穷举**无路径（证明性）。
  - UNRESOLVED：状态上限命中（**不将"没找到"解释为"必须拒答"**）。

## 5. 测试

`test_exit_gate` / `test_benchmark_v3::test_solvability_matches_budget`：
scarce budget=2.0 → ABSTENTION_REQUIRED；generous → GO_REACHABLE。
