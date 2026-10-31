# Final Locked Provenance Audit — 执行溯源审计

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 时间线（Task 8）

| 事件 | 版本/时间 |
|---|---|
| Benchmark v3.1 封存 | 16c7e87（440 世界，404 GO + 36 ABSTAIN + 0 UNRESOLVED） |
| 首次 Locked Evaluation 执行 | 2522aec 提交前（**含未提交的 P0 修正**） |
| — 其中 world-budget 修复（dream_rsi.py） | 执行前已改 |
| — 其中 drift 精确性降级（validity.py） | 执行前已改 |
| — **共享 view 缺陷（run_locked_evaluation.py）** | **执行时存在，提交 2522aec 时未发现** |
| 审计发现共享 view | 本轮（2522aec 之后） |
| v2 重新评价（独立 view） | 本轮（新目录 artifacts/locked_eval_v2/） |

**关键事实**：2522aec 提交的 `per_world_metrics_final.csv` 是用**含共享
view 缺陷**的脚本生成的。提交快照与执行时代码一致（bug 被提交），但
bug 使结果无效。

## 2. UNRESOLVED 溯源（Task 5）

- 封存（16c7e87）时：**0 UNRESOLVED**（404 GO + 36 ABSTAIN）。
- Task 1.1 预检发现：drift 家族 + ood-drift-conflict 有**多版本时间证据**，
  可达性状态键不含时间 → 精确性不可证。
- 修正后：**56 UNRESOLVED**（drift 36 + ood-drift-conflict 20）。

### 分区

| Split | UNRESOLVED |
|---|---|
| DEV | 16（drift × 16 seed） |
| Confirmation | 8（drift × 8） |
| Held-out TEST | 12（drift × 12） |
| OOD | 20（ood-drift-conflict × 20） |

### 指标处理

- **UNRESOLVED 不视为 GO_REACHABLE**（不可用"存在路径"推断）。
- **也不视为必须拒答**（不可用"无证明"推断 abstain）。
- 评价按**执行时证据充分性**报告（真实执行结果不受影响）。
- **Protocol Amendment**：可解性标签从"全部精确"修正为"非 drift 世界
  精确 + drift 世界 UNRESOLVED"。此修正发生在**首次 Locked Test 执行前**
  （Task 1.1 预检阶段），不是执行后调参。

## 3. 修改前后 Evaluator Hash

- 修改前（16c7e87）：validity.py 无 `_has_time_versions` 检查。
- 修改后（本轮）：`ExactBudgetedReachabilityOracle.solve()` 对多版本证据
  世界返回 UNRESOLVED。
- **没有为"修改后评价"打新的 evaluator_version** —— 这是审计发现的
  版本管理缺口（应在 v2 评价中记录 evaluator_version=0.3）。

## 4. 执行版本一致性（Task 8）

- 原始执行：2522aec 代码（含共享 view bug）→ **结果无效**。
- v2 执行：本轮修复后代码（独立 view）→ 结果有效，但**尚未提交**。
- **披露限制**：无法证明 2522aec 的原始结果有效（已知 bug）；v2 结果
  以当前工作区为准，提交后固定。

## 5. 结论

- 原始 Locked Evaluation **INVALIDATED**（共享 view）。
- v2 需作为**新数据版本**（不是"同一批任务的重新声明"）——它修正了
  执行正确性，但**同一批世界**（冻结数据不变）。按 Task 8：修复执行
  bug 属正确性修复，允许；不得据此调整策略/指标。
