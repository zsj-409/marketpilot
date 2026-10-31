# RSI Confirmation Protocol — Phase 5.5

| Status | Commit | Date |
|---|---|---|
| DEFINED | worktree (pre-commit) | 2026-10-29 |

## 1. 三层数据分区（Task 5）

| 分区 | 用途 | 禁止用途 |
|---|---|---|
| Generation DEV | 轨迹收集、策略提议、参数搜索、调试 | — |
| Confirmation DEV | 判断候选策略是否有晋级依据（shard 隔离） | 不可无限复用同一世界 |
| Locked Test | 最终正式评价（算法冻结后） | 不得进入策略生成/Memory/Skill/Dream Archive/调参循环 |

## 2. Confirmation Shards（世界级隔离）

- **预先分配**：`RecursiveOptimizationLoop(confirmation_shards=[...])` 传入多个独立
  confirmation 世界（不同 seed/world_id）。
- **每轮消耗一个**：round i 用 `shards[i-1]`；`shard_usage` 记录每轮用了哪个 world_id。
- **绝不复用**：同一 shard 不会在多轮出现（测试 `test_confirmation_shards_are_consumed_per_round`
  验证 3 轮用 3 个不同 world_id）。
- **耗尽即停**：shards 用完的轮次 `conf_ok=False`（标记 `EXHAUSTED`），**不允许**无限
  搜索直到晋级（测试 `test_confirmation_shard_exhaustion_blocks_promotion`）。
- 历史确认结果仅用于**审计**，不作为下一轮策略提议器的输入。

## 3. Incumbent/Challenger 配对比较（Task 1.1）

每轮晋级判定 = **配对确认运行**（同一 shard、同一预算、同一 seed）：
1. Challenger 在 shard 上执行（`conf_result`）
2. Incumbent（上一 active）在同一 shard 上执行（`inc_result`，记入 ledger
   `incumbent_confirmation`）
3. `quality_delta` = challenger 与 incumbent 的 selected_id 是否不同（且都 GO）
4. `cost_delta` = challenger cost − incumbent cost（负 = challenger 更省）
5. `classify_outcome` 按预定义规则分类（见下）

**禁止**：用上一轮不兼容的历史评分充当当前比较；初始基线未评估时**不得**把 0 当基线
并宣布改进（缺失基线返回 NOT_EVALUABLE）。

## 4. PromotionKind 判定规则（Task 1.2，预先定义不后调）

| 分类 | 判定规则 |
|---|---|
| IMPROVED | quality_delta > 0（challenger 选出不同且两者都 GO） |
| EFFICIENCY_GAIN | quality_delta ≈ 0 且 cost_delta < -1e-6（同质量更省） |
| TIED | 无足够证据证明质量或效率改善（默认，不切换 active） |
| REGRESSED | quality_delta < 0（challenger 质量退化） |
| INVALID | 越权/泄漏/不可重放/违反硬约束/评价不合法 |

**TIED 不切换 active**；旧策略保留为候选，不因每轮必须更新而强制晋级。

## 5. 验证

- `test_locked_test_not_in_shards`：Locked Test world 从不进入 confirmation shards。
- `test_confirmation_shards_are_consumed_per_round`：每轮不同 shard。
- `test_confirmation_shard_exhaustion_blocks_promotion`：耗尽即停。
