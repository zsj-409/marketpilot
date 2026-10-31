# Behavioral Equivalence Report — 策略行为等价性诊断

| Status | Commit | Date |
|---|---|---|
| COMPLETED (diagnostic) | worktree (pre-commit) | 2026-10-30 |

## 1. 问题

v2 修复后 Fixed/MissingEvidence/Uncertainty/ContextualHybrid 在 TEST 均
75/120 valid、OOD 均 14/80——**是否实际退化为同一种算法？**

## 2. 方法（Task 3）

在 Generation DEV（160 世界）对比 5 种策略：
- 动作序列（facet, target）。
- 研究成本 / 停止位置。
- Outcome / reason_code。
- 序列重合度。

## 3. 结果（behavioral_equivalence.csv）

### 聚合（DEV 160）

| 方法 | avg_cost | avg_actions | valid_go | wrong_go | abstain |
|---|---|---|---|---|---|
| fixed | 10.31 | 10.7 | 101 | 11 | 48 |
| missing-evidence | 10.32 | 10.5 | 101 | 11 | 48 |
| uncertainty | 10.32 | 10.5 | 101 | 11 | 48 |
| contextual-hybrid | 10.31 | 10.7 | 101 | 11 | 48 |
| adaptive-voi | 9.85 | 10.1 | **48** | 72 | 40 |

### 序列身份（balanced-100）

- 5 策略都研究 12 步（预算 12 够全部）→ (facet, candidate) **覆盖集相同**
  （set-Jaccard 1.0）。
- **顺序不同**：fixed 按 facet 外循环（demand→demand→demand...）；
  missing/contextual 按候选补全（demand→risk→margin 同候选）；
  uncertainty/adaptive 按分歧/VOI 排序。

## 4. 结论

1. **预算充足时（12 够研究全部候选×必需 facet），系统化家族
   （fixed/missing/uncertainty/contextual）行为等价**——最终覆盖相同 →
   相同决策（101 valid）。
2. **顺序差异真实存在**但**不影响预算充足的结果**；只在预算不足时
   （scarce 2.0）体现差异（missing 按候选补全 vs fixed 按 facet 循环）。
3. **adaptive-voi 不等价**：只研究 VOI 高的部分 → 覆盖不足 → 48 valid
   + 72 wrong（明显不同）。
4. **不得宣称 fixed/missing/uncertainty/contextual 代表独立算法收益**
   ——当前任务分布下它们是**同一行为的参数化变体**。
5. ContextualHybrid 在预算充足时选 fixed 行为 → 与 fixed 完全一致
   （diff=0.0，v2 已验证）。

## 5. 对独立复验的意义

- 新测试（v2.1）应区分：**行为等价组**（系统化 4 家族）与 **adaptive-voi**。
- 若新测试仍显示系统化家族相同，应报告"无独立算法差异"，而非重复
  宣称 4 种方法 4 种收益。
