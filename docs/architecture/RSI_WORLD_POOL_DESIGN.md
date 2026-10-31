# RSI World Pool Design — Phase 5.5

| Status | Commit | Date |
|---|---|---|
| DESIGNED+IMPLEMENTED | worktree (pre-commit) | 2026-10-29 |

## 1. 目标（Task 3）

实现跨轮次累积的 Replay World Pool，使变体 Dreaming 基于**全部已探索历史**（而非仅
当前 active 轨迹），并提供 Full Cumulative Pool vs Current History Only 两个消融。

## 2. 数据模型

`ReplayWorldArchive` 轨迹按 `(round, world_id, policy_hash)` 索引：

- **append-only**：同一 policy+world 在 later round 的记录**不覆盖** earlier（测试
  `test_archive_never_silently_deletes`）。
- 索引含 round、world_id、world_version、split、state_hash（view.state_signature()）、
  action_id（ObservedStep.action）。
- 同一状态下的不同已执行分支可分别访问（`trajectories_for_world`）。
- 不同状态**不得**无条件合并（state-compat 检查：replay 只重放 state_signature 匹配的
  转移；`s{index}` 占位符跳过）。
- 未观察动作**不得**合成结果（unknown action → UNSUPPORTED，attempt_coverage 计为分母）。

## 3. 累积逻辑

```
Round 0: init 执行 active -> 保存 H0（round=0）
Round 1: 用 H0（pool_mode=full: 全历史）dream 变体 -> 确认 -> 新探索 H1（round=1）
Round 2: 用 H0+H1 dream -> 确认 -> H2（round=2）
Round 3: 用 H0+H1+H2 dream -> ...
```

- `pool_mode="full"`：dream 用 `trajectories_for_world(dev)` 全历史
- `pool_mode="current"`：dream 用 `trajectories(round_index=round-1)` 仅最近一轮

## 4. 消融条件（Task 3 要求）

| 条件 | pool_mode | 行为 |
|---|---|---|
| `full` | full | 用全部累积历史 dream |
| `current-history-only` | current | 仅最近一轮历史 dream |

两者预算、策略候选生成条件固定，只变历史池大小。`test_full_and_current_pool_both_run`
验证两种模式都能执行。

## 5. 报告指标（Task 3.7）

loop 返回 `pool_size`（archive 内轨迹总数）。单轮内不同历史池大小对 Coverage /
候选可评价数 / 运行成本的影响见 `RSI_PHASE55_RESULTS.md`。

## 6. 边界

- 历史池**上限与去重**机制未实现（当前 append-only 无上限）——已知限制。
- 策略不能读未来节点/隐藏真值/最终评价标签（AgentWorldView 接口隔离）。

## 7. 官方 DREAM-RSI 借鉴（不复制）

官方 `trace_pool/` 累积每轮冻结副本，offline learning 在全部 replay 世界重放候选。
我们实现了等效的按轮索引累积 + pool_mode 消融；未实现的是官方按 ρ 预算偏好
（ρ∈{0,.25,.5,.75,1}）的多点打分（见 RSI_CORRECTNESS_AUDIT.md §4.1，保留为扩展）。
