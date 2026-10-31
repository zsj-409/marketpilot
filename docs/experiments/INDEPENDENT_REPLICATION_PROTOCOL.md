# Independent Replication Protocol v2.1

| Status | Commit | Date |
|---|---|---|
| FROZEN (pre-registered) | worktree (pre-commit) | 2026-10-30 |

## 1. 目标

在**从未查看结果的新市场世界**上，用 Metric Contract v2.1 独立复验各
研究策略，形成可信的算法结论。

## 2. 数据集（Task 5）

- **120 ID 世界**：10 家族 × 12 seed（500-511）。
- **80 OOD 世界**：4 组合 × 20 seed（700-719）。
- 独立于 v3.1 全部分区（seed 100-311, 400-419 不重叠）。
- 新 seed → 新隐藏商品真值（无跨数据集复用）。
- Manifest + 全部 hash 在运行前冻结（`independent_dataset_manifest.json`）。

## 3. 方法（Task 6）

- Fixed / MissingEvidence / Uncertainty / AdaptiveVOI / ContextualHybrid。
- **Global Best Static 在新 DEV 上重新选择**（v2.1 seed，不用旧无效选择）。
- 每个方法冻结 policy_hash 后进入测试。

## 4. 隔离（Task 7.1）

- `marketpilot.benchmark.isolation.isolated_execute`：每方法独立 view。
- 执行前验证 view 初始状态（state_signature 匹配 fresh）。
- 顺序不变性测试先通过（方法置换不改变结果）。
- 无跨方法证据/预算/时钟共享。

## 5. 主要指标（Task 8）

Valid GO Rate / Unsupported GO Rate / Constraint Violation Rate /
Appropriate & Unnecessary Abstention Rate / Decision Regret on Supported GO /
Task-Level Loss v2.1 / Total Research Cost / Cost per Valid GO /
Budget Violation Rate。

## 6. 统计（预注册）

- 世界级配对差异，按机制家族分层 Bootstrap（2000 次，95% CI）。
- 抽样单位 = 世界（非轨迹节点）。
- 主比较：A（系统化家族间差异）、B（adaptive vs 系统化）、C（v2.1 下
  完成率/风险/损失）、D（OOD 退化来源）。
- **旧 v2 的差异（+0.049 等）不得描述为显著**——显著性只来自新实验。

## 7. 禁止

- 测试期间更新策略 / 根据已跑任务调整 / 测试轨迹入 Archive /
  根据 TEST 调 Metric / 挑选样本 / 覆盖首跑记录。

## 8. 失败处理

- 运行时错误：保存日志 + 一次重试，不选择性重跑。
- 执行正确性错误：STOP + 保存 + BLOCKED。
- 严重正确性错误修复后**不得**把同一批已查看任务重跑称为首次独立验证。

## 9. 三类历史结果分离

1. **INVALIDATED ORIGINAL**（2522aec，共享 view）。
2. **POST-AUDIT REANALYSIS v2**（861c16e 后，旧测试集修复执行）。
3. **INDEPENDENT REPLICATION v2.1**（本轮，新世界集）。
