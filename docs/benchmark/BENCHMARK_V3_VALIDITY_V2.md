# Benchmark v3.1 Validity V2 — 有效性审计（修订版）

| Status | Commit | Date |
|---|---|---|
| VALIDATED (v3.1) | worktree (pre-commit) | 2026-10-29 |

## 1. 基线实际运行（Task 3.1）

60 世界 Pilot 上运行真实基线（budget 用各世界 research_budget）：

| 方法 | Valid GO | Appropriate Abstention | 备注 |
|---|---|---|---|
| Random Selection | ~随机正确率 | 0 | 无研究 |
| Simple Heuristic | 观测最高分 | 0 | 无研究 |
| CheapestFirstHeuristic | 预算内研究 | 部分 | 启发式 |
| Fixed | 系统化研究 | 0 | 冻结策略 |
| MissingEvidence | 系统化研究 | 0 | 冻结策略 |
| AdaptiveVOI | VOI 排序 | 部分（W1 类） | 冻结策略 |
| FullInformationOracle | **100%** | 0 | 理论上界 |
| ExactBudgetedReachabilityOracle | 404/440 GO | 36/440 | 精确可达性 |

**Full-Info Oracle 100% 正确是定义使然**（用隐藏真值），不证明难度。
**判别力证据**：60/60 研究改变决策（正控制）+ 36/440 必须拒答 +
多家族行为差异（Phase 5：W1 系统化 GO vs adaptive REFUSED）。

## 2. 信息价值正控制（Task 3.2）

成对世界测试（`test_information_value.py`）：
- 两世界同 spec 不同 seed，中等噪声（0.15）→ 初始观测不泄漏隐藏最优。
- 无研究时 heuristic 不能在两世界都正确（观测最佳 ≠ 隐藏最佳至少一处）。
- 研究（揭示 margin/demand/risk）后可分别作出正确决策。
- **证明信息获取有真实价值，而非仅增加证据数量**。

## 3. 信息价值负控制（Task 3.3）

- 冗余研究不产生虚假提升：重复揭示同一 facet 返回相同值（测试验证）。
- 初始证据足够时 research 非必需：Full-Info Oracle 直接 Valid GO。
- 候选顺序变化不造假：anti-leak shuffle（多 seed 位置分布测试）。
- 重复来源不增价值：evidence_redundancy 有界行为。

## 4. 难度分布（Task 3.4）

- **判别力**：404 GO + 36 拒答；scarce 家族全部拒答（非单一 facet 依赖）。
- **无泄漏**：ID/位置/标签与最优商品无固定对应（生成器性质测试，
  多 seed 验证）。
- **拒答来源**：全部来自 scarce（budget=2.0）——单一模板，但这是
  **预算机制**（合法拒答场景），非生成缺陷。

## 5. 结论

Benchmark v3.1 具有真实信息价值、合理难度分布、精确可解性标签、
防泄漏机制。判别力由正控制 + 拒答分布 + 家族差异共同支撑。
