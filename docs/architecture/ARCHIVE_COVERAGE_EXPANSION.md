# Archive Coverage Expansion — Generation DEV 主动覆盖扩展

| Status | Commit | Date |
|---|---|---|
| IMPLEMENTED + TESTED | worktree (pre-commit) | 2026-10-29 |

## 1. 实现

新增 `src/marketpilot/optimization/coverage_planner.py`：

- `ArchiveCoveragePlanner`：预算受限的覆盖扩展器
- `CoverageReport`：覆盖报告（机器可读）

流程（对应 Task 3 职责）：
1. 读取 Generation DEV 允许的历史轨迹索引（archive.trajectories_for_world）。
2. 识别已覆盖 (state, action) 对，找出未覆盖动作。
3. 用多种基线策略（fixed/missing/uncertainty/adaptive）从合法初始状态
   执行新研究分支。
4. 保存真实观测（_record_trajectory 记录真实 steps）。
5. append-only 追加到 archive。
6. 更新覆盖率与边际收益。

## 2. 保证

- **只执行合法动作**：策略通过 AgentWorldView 执行，动作受限。
- **不跨状态拼接**：每条轨迹是单一策略从初始状态的真实执行。
- **新执行是新执行**：记录真实 cost（total_collection_cost），不冒充
  Replay Hit。
- **重复不增覆盖**：已覆盖的 (state, action) 对不再计新分支。

## 3. 实测（W1，budget=20，4 家族）

| 指标 | 值 |
|---|---|
| world_count | 1 |
| unique_state_count | 6 |
| unique_supported_action_count | 3 |
| distinct_branch_count | 2 |
| attempt_coverage | 1.0 |
| episode_support_rate | 1.0 |
| unsupported_action_count | 0 |
| coverage_gain_per_new_execution | 4.5 |
| total_collection_cost | 15.2 |
| new_executions | 2 |

## 4. 覆盖报告字段（Task 3 要求）

- world_count ✓
- unique_state_count ✓
- unique_supported_action_count ✓
- distinct_branch_count ✓
- attempt_coverage ✓
- episode_support_rate ✓
- unsupported_action_count ✓
- coverage_gain_per_new_execution ✓
- total_collection_cost ✓

## 5. 测试

`test_coverage_planner_adds_unique_branches`：新分支增加唯一覆盖，重复执行
不增加。
`test_coverage_planner_only_legal_actions`：无非法动作。
`test_duplicate_trajectories_do_not_inflate_coverage`：重复轨迹不增覆盖。

## 6. 状态

IMPLENTED（轻量级，无新 Agent 角色）。
