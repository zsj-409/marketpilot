# RSI Cost Semantics — Phase 5.5

| Status | Commit | Date |
|---|---|---|
| DEFINED | worktree (pre-commit) | 2026-10-29 |

## 1. 六类成本（Task 1.4）

`ExecutionLedger` 严格区分以下成本类型，**绝不混用**：

| 类型 | 含义 | 是否真实支出 | 记入 online_total | 记入 replay_total |
|---|---|---|---|---|
| `archive_collection` | 收集历史探索数据的原始成本（记录轨迹时实际花费） | 是 | ✅ | ❌ |
| `online_execution` | 当前策略新增真实执行（init/propose/promote_dev） | 是 | ✅ | ❌ |
| `policy_proposal` | 生成候选策略的实际成本 | 是 | ✅ | ❌ |
| `confirmation` | 独立确认运行成本（含 incumbent 配对 run） | 是 | ✅ | ❌ |
| `incremental_replay` | 读取历史 + 运行 replay 策略的增量计算 | 否（离线） | ❌ | ✅ |
| `simulated_action` | 重放路径代表的历史动作预算消耗 | **否（虚拟）** | ❌ | ✅ |

## 2. `ObservedStep.cost` 的真实含义

- `ObservedStep.cost` 记录的是**原始工具调用成本**（轨迹被记录时实际发生的）。
- 当 replay 重放该步骤时，其成本记为 `simulated_action`（**虚拟历史预算**），
  **绝不**重新累加为当前轮的真实在线支出（Task 1.4 核心规则）。
- 同一历史采集事件**不得**在同一次比较中重复计入多轮——ledger 按
  (round, phase, cost_type) 记录，replay 的 simulated_action 与原始 archive_collection
  分离，避免重复计费。

## 3. 预算单位

无真实 API 定价（离线 mock），**不伪造美元成本**。报告以下单位：
- 工具调用数量（`steps` 数）
- 模型请求数量（离线=0）
- Token（离线=0）
- 执行耗时（未记录）
- **预算单位**：`budget`（在线预算，默认 10.0；消融统一 30.0）

## 4. 验证

- `test_ledger_separates_online_and_replay`：online_total > 0、replay_total > 0、
  `by_type` 含 `online_execution` 与 `simulated_action`。
- replay 的 `cost` 字段 = 记录的 `ObservedStep.cost` 累加（非估算）。
