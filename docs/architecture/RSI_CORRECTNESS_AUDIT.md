# RSI Correctness Audit — MarketPilot Phase 5 Dream-RSI vs 官方 DREAM-RSI

| Status | Commit | Date |
|---|---|---|
| AUDITED | (worktree, pre-commit) | 2026-10-29 |

## 1. 审计范围

对照 [google-research/dream-rsi](https://github.com/google-research/dream-rsi)（Apache 2.0，
2026-10 发布，论文方法：通过演化世界递归自改进探索策略），逐项检查 MarketPilot Phase 5
的 `src/marketpilot/optimization/` 实现是否满足相同的实验正确性约束。
只借鉴适合商品研究任务的设计，不复制官方实现。

## 2. 逐项对照

### 2.1 Online/Replay 的统一环境接口

- **官方**：`TraceEnv` 是 online rollout 与 offline replay 共享的决策接口；replay 世界是
  online 轮次结果的冻结副本（`trace_pool/`）。
- **我们**：`AgentWorldView`（`world/core.py`）同时被 `ParameterizedPolicy.execute`（online）
  与 `HistoricalReplaySimulator.replay_policy`（offline）消费。replay 在**全新 view** 上
  重放已记录动作，与 online 用同一套 `take_action`/`revealed_facets` 接口。
- **结论**：✅ 一致。`AgentWorldView` 是统一接口；replay 不依赖存档的副作用，只依赖
  已记录的 state 转移。

### 2.2 已观察节点与合法动作

- **官方**：`ExplorationTree` 只包含 online 实际探索过的节点；离线学习只在这些节点上重放。
- **我们**：`ExplorationTree` 通过 `observe()` 记录已观察的 (world, state) -> actions；
  `HistoricalReplaySimulator` 只重放 archive 里**已记录**的 step；**未知动作显式拒绝**
  （`rejected_actions`），绝不发明结果（V2 规则 4）。
- **结论**：✅ 一致且更强（我们显式报告拒绝列表）。

### 2.3 Prefix-only 信息访问

- **官方**：策略只能看到已探索的轨迹前缀（历史轮次），看不到未来分支。
- **我们**：`ParameterizedPolicy` 只消费 `AgentWorldView`（`candidates()`/`evidence_summary()`
  = 已揭示证据），`HistoricalReplaySimulator` 重放只走 `recorded.steps` 前缀，`coverage`
  显式报告已覆盖的可重放动作比例（分母排除 stop 记账步骤）。
- **结论**：✅ 一致。但注意 `ParameterizedPolicy.execute` 的 `AdaptiveVOIController` 内部
  会按 `REQUIRED_FACETS` 循环——它只能看到已揭示 facet，符合 prefix-only。

### 2.4 策略质量与执行预算

- **官方**：replay objective（Eq.1）按预算偏好 ρ ∈ {0, .25, .5, .75, 1} 对每个策略版本
  打分，选最优版本探索下一轮；**预算偏好是多点的**。
- **我们**：`DreamEvaluator` 单一阈值（`dream_threshold=0.5`）+ 单一 dream score；
  `RecursiveOptimizationLoop` 只做**单一预算偏好**的 replay 重放打分。官方对"预算偏好"
  的网格搜索我们没有实现。
- **差距**：⚠️ 我们的 dream evaluation 没有 ρ 网格；变体只有在**单一** dream score
  超过阈值才晋级。这限制了"成本-质量权衡"的表达——一个更省但质量略降的变体无法通过
  "低 ρ 偏好"晋级。**建议**：后续引入 ρ 网格（Phase 5 扩展），或至少明确记录单一 ρ 的局限。

### 2.5 Replay 世界池

- **官方**：`trace_pool/` 累积**所有**已探索轮次的冻结副本，每次 offline learning 在**全部**
  replay 世界上重放候选。
- **我们**：`ReplayWorldArchive` 只保留 dev/confirmation 两个世界 + 每策略最新轨迹
  （`_trajectories[policy_hash]` 覆盖旧轨迹）。**没有累积多轮历史**。
- **差距**：⚠️ 我们的 archive 是"每策略最新一条"，不是"每轮次的冻结快照"。变体只对
  **当前 active 的轨迹**做 dream（`observed = next(...)`），不对**更早轮次**的轨迹重放。
  这削弱了"演化世界"的累积性。**建议**：Phase 5 扩展中把 archive 改为**按轮次追加**
  （`trajectories/<round>/<hash>.json`），dream 对全部历史轨迹重放。

### 2.6 策略保留、晋级和回滚

- **官方**：`policy/method.py` 是当前策略；`heuristic_history/` 保留每个版本及其 replay 结果；
  `discover_summary.json` 记录选中版本；若改写击败当前策略则复制到 `method.py`。
- **我们**：`PolicyRegistry` 有 `promote`/`rollback`/`history()`，本轮新增
  `PromotionKind`（IMPROVED/EFFICIENCY_GAIN/TIED/REGRESSED/INVALID）+ `classify_outcome`。
- **结论**：✅ 基本一致；本轮补齐了晋级分类（Task C.7）。

### 2.7 执行轨迹和历史重放的一致性

- **官方**：replay 世界是 online 轮次的**冻结副本**，重放与 online 结果必须一致。
- **我们**：`ObservedStep` 记录 `(action, state_before, state_after, cost)`；重放时用
  `step.cost`（**实际记录成本**）累加 replay cost，不重新估算。
- **结论**：✅ 一致。

## 3. 本轮修复的问题（代码级证据）

| # | 问题 | 证据 | 修复 |
|---|---|---|---|
| 1 | 在线成本 3× 重复累计 | `run_ablation` 每轮新建 `RecursiveOptimizationLoop` 并累加全部 ledger | 改为 loop 只跑一次（内部 rounds 驱动），`account()` 只累加一次 |
| 2 | `promoted_hashes` 恒空 | `str(s) == "PolicyStatus.PROMOTED"` 永不匹配（实际 `str` 是 `"promoted"`） | 用 `s is PolicyStatus.PROMOTED` |
| 3 | 死代码（估算混入） | `cost_so_far`/`track_executions`/`_loop_execution_costs`/`_estimate_cost` 未用或基于 archive 事后推断 | 删除；改用 `ExecutionLedger` 精确记账（online vs replay 分离） |
| 4 | replay 成本不可信 | `replay_policy` 不返回成本，`_loop_execution_costs` 靠 archive 推断且漏掉 stop 步骤成本 | `replay_policy` 返回 `cost`（= 记录的 `ObservedStep.cost` 累加，非估算） |
| 5 | Coverage 分母被 stop 稀释 | `coverage = replayed / len(steps)` 含 stop 记账步 | 分母改为 `replayable_steps`（排除 stop） |
| 6 | 0.3 分歧惩罚过度压制创新 | 有分歧的有效新决策被 0.3 惩罚打到 0.7 以下，系统性偏向复制历史 | 降为 0.1（与一次拒绝同量级），保留"有效创新不被压制" |
| 7 | 晋级无分类 | `PolicyRegistry` 无 IMPROVED/EFFICIENCY_GAIN/TIED/REGRESSED/INVALID | 新增 `PromotionKind` + `classify_outcome`，loop 接入 |

## 4. 剩余差距与建议（不改核心，记录备查）

1. **ρ 预算偏好网格缺失**（2.4）：官方按 5 个 ρ 打分；我们单一 ρ。→ Phase 5 扩展项。
2. **Replay 世界池不累积**（2.5）：`_trajectories[policy_hash]` 覆盖旧轨迹，变体只对
   当前 active 轨迹 dream。→ Phase 5 扩展项（按轮次追加 + 全历史重放）。
3. **Confirmation DEV 重复使用**：`run()` 每轮都跑 confirmation（同一 confirmation world），
   多轮后同一世界被反复用于筛选 → 可能造成选择偏差。官方没有 confirmation 概念（只有
   replay 世界池）。**建议**：后续引入多个 confirmation world 轮换，或把 confirmation
   改为"只在晋级前跑一次独立世界"。
4. **`prev_active_cost` 是占位**（恒 0）：成本对比目前是 TIED 默认，未真正比较
   prev/next 的执行成本。**建议**：记录每策略在 confirmation 上的执行成本到 ledger，
   再算 cost_delta。

## 5. 结论

MarketPilot Phase 5 Dream-RSI 的**核心实验正确性**（统一环境接口、已观察节点、prefix-only、
隐藏真值隔离、未知动作拒绝、replay coverage 显式报告、online/replay 成本分离）与官方
DREAM-RSI 一致。差距集中在**预算偏好网格**和**replay 世界池累积**两点，均不影响当前
minimal world 验证的正确性，但影响后续困难世界实验的敏感性——已记录为扩展项。
