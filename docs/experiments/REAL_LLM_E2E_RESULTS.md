# Real LLM E2E Results — 真实 LLM 端到端实验结果

| Status | Commit | Date |
|---|---|---|
| REAL_LLM_EXECUTED | worktree (pre-commit) | 2026-10-30 |

## 1. 执行状态

**REAL_LLM_EXECUTED** — 使用 Hermes 运行时同款 Provider（volcengine-ark /
deepseek-v4-flash），API Key 从 Hermes .env（ARK_API_KEY）运行时读取，
**绝不写入代码、Git、日志或前端**。

| 项 | 值 |
|---|---|
| Provider | volcengine-ark |
| Model | deepseek-v4-flash |
| Base URL | https://ark.cn-beijing.volces.com/api/plan/v3 |
| Prompt Hash | 2ea3f0fb6d635e6b |
| Temperature | 0.0 |
| Max Output Tokens | 800 |
| Max Turns | 6 |
| Tool Choice | required（研究轮）/ auto（决策轮） |

## 2. Smoke Test（B1，4 任务）

| 世界 | 决策 | Calls | Tools | Tokens | Gate |
|---|---|---|---|---|---|
| W1-7 | GO | 2 | 7 | 3181 | PASS |
| W2-8 | GO | 2 | 7 | 3038 | PASS |
| W4-9 | REFUSED | 1 | 0 | 1526 | REFUSED |
| W0-7 | GO | 2 | 7 | 2985 | PASS |

Smoke 验证：模型真实参与需求解析→研究动作→工具执行→决策→结构化输出；
ToolExecutor 返回真实世界证据；Structured Outputs 校验（0 schema 失败）；
Safety Gateway 保护最终输出。

**过程中发现并修复的 Runtime 缺陷**：
1. `ToolArguments` 固定 schema 截断模型返回的 `facet` 参数 → 加
   `extra="allow"` 保留任意字段。
2. `finish_reason` 比较用 `"tool_calls"`（小写）≠ `LLMFinishReason.TOOL_CALLS.value`
   （`"TOOL_CALLS"` 大写）→ 工具调用分支永不执行 → 改用枚举成员比较。
3. 火山方舟在 12 个并行 tool_calls 时截断最后一个 arguments → adapter
   跳过截断调用（response_id 标记 `+truncated:N`）而非使整轮失败。

## 3. 正式实验（B2，24 世界）

### 汇总

| 指标 | 值 |
|---|---|
| Deterministic GO | 16/24 |
| LLM GO | 15/24 |
| LLM Gate Pass | 15 |
| LLM Gate Interceptions | 0 |
| LLM Calls | 50 |
| LLM Tool Calls | 170 |
| Tokens in / out | 59,254 / 27,787 |
| Schema Failures | 0 |
| Latency P50 / P95 | 7,969ms / 15,922ms |
| 决策一致性（det vs LLM） | 12/24 |

### 关键行为差异

- **W5 系列（3 候选）**：确定性 INSUFFICIENT（研究不足），LLM 3/4 GO
  （研究 10-16 工具后给出推荐）——**真实模型在预算内主动研究更多候选**。
- **W4 系列（预算不足世界）**：确定性 INSUFFICIENT，LLM 3/4 REFUSED
  （正确拒答）；W4-10 模型 12 工具 11k tokens 未给决策（截断/超预算）。
- **W1-8 / W2-10 / W3-7**：LLM REFUSED 但确定性 GO——真实模型更保守。

### 配对结论

- 完成率相当（16 vs 15），**无显著差异**。
- LLM 的 GO 全部有证据支持（0 拦截）——工具调用协议（required）有效
  防止了无证据推荐。
- 决策一致性 50%：模型与确定性策略选择不同商品，但都通过 gate。

## 4. 诚实声明

- 全部数字来自**真实模型执行**（火山方舟 API），非 Mock/Fixture。
- Token/延迟为真实计费口径（费用估算因无 provider 定价表标注 None）。
- 未调整任何冻结策略或 Benchmark 结果。
