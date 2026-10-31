# Evaluation Hardening Report — 评测加固报告

| Status | Commit | Date |
|---|---|---|
| COMPLETED (Milestone A) | worktree (pre-commit) | 2026-10-30 |

## 1. 隔离修复（Task 1）

### 统一执行入口
`src/marketpilot/benchmark/isolation.py`：
- `isolated_execute()`：每方法独立 AgentWorldView，执行前验证初始状态
  （state_signature == fresh），不干净则抛 `ViewPollutionError`。
- PRNG 由 (world_id, method, repetition) 派生 → 执行顺序不影响随机方法。
- `run_method_order_invariance()`：置换不变性测试（4 种顺序）。

### 负控制
- 脏 view 检测：已揭示证据的 view 签名 ≠ fresh 签名（测试验证）。
- Runner 拒绝脏初始 view（不静默继续）。

### 成本审计（Task 1.4）
- 每动作真实成本来自 result.steps（facet × cost）。
- `sum(step_costs) == result.total_cost`（重建验证一致）。
- Cost per Valid GO：0 valid → **N/A**（非 0）。

## 2. Metric Contract v2.1（Task 2）

- reason_code 拆分 GO：supported_valid / supported_suboptimal / unsupported。
- **UNSUPPORTED_GO_LOSS(1.0) ≥ abstention_cost(1.0)**——修复 v2.0 乱猜漏洞。
- 不必要拒答 1.5（+0.5 机会损失）。
- 约束违规 1.5。
- 文档：METRIC_CONTRACT_V21.md / .json / METRIC_MIGRATION_V20_TO_V21.md。

## 3. 行为等价性诊断（Task 3）

- DEV 160 世界：fixed/missing/uncertainty/contextual 均 101 valid（相同
  覆盖集）——**预算充足时行为等价**（都研究全部候选）。
- balanced-100 有序序列：fixed 按 facet 外循环，missing 按候选补全——
  **顺序不同但最终 (facet, candidate) 覆盖相同**。
- **结论**：当前预算（12，够研究全部）下系统化家族等价；差异仅在预算
  不足时显现。不得宣称它们代表独立算法收益。

## 4. 新独立数据集（Task 5）

- 200 世界（120 ID + 80 OOD），seed 500-511 / 700-719。
- 0 重复 hash、0 seed 重叠旧分区。
- Manifest 冻结（`independent_dataset_manifest.json`）。

## 5. 预注册（Task 4）

- `preregistration.json`：协议 v2.1，读取结果前冻结。
- `INDEPENDENT_REPLICATION_PROTOCOL.md`。

## 6. 测试

+9 隔离/合同测试（test_hardening.py），289 passed 全绿。

## 7. 三类历史结果

1. INVALIDATED ORIGINAL（共享 view）。
2. POST-AUDIT REANALYSIS v2（旧集修复执行）。
3. INDEPENDENT REPLICATION v2.1（新集，待运行）。
