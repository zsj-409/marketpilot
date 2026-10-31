# Real LLM End-to-End Validation Report — 真实 LLM 端到端验证报告

| Status | Commit | Date |
|---|---|---|
| HARNESS READY (REAL_LLM_NOT_RUN) | worktree (pre-commit) | 2026-10-30 |

## 1. Runtime 审计（Task B1）

| 能力 | 状态 | 位置 |
|---|---|---|
| LLM Runtime（typed request/response） | ✅ 已有 | `llm/models.py` |
| ToolExecutor（统一工具执行） | ✅ 已有 | `tools/` |
| Research Orchestrator | ✅ 已有 | `research/` |
| Research Workers | ✅ 已有 | `product_selection/workers.py` |
| Evidence Store | ✅ 已有 | `research/store.py` |
| Input Contracts | ✅ 已有 | `research/models.py` + `domain/` |
| Replay/Live 模式 | ✅ 已有 | `research/replay.py` + `live_environment.py` |
| CLI / Web Workbench | ✅ 已有 | `cli.py` |
| **Final Decision Safety Gate** | **🆕 本轮新增** | `safety/gate.py` |

未重复创建框架；复用现有真实 LLM Provider（OpenAI adapter）、统一
ToolExecutor 和 Evidence Graph。

## 2. LLM Gateway 稳定性（Task B2 审计）

| 要求 | 状态 |
|---|---|
| 强类型请求/响应 Schema | ✅ pydantic 冻结模型 |
| Structured Outputs 严格校验 | ✅ `response_format` json_schema + `parse_structured_output` |
| 模型拒绝/截断处理 | ✅ `LLMFinishReason`（LENGTH/CONTENT_FILTER） |
| API 超时 | ✅ `timeout_seconds` + `APITimeoutError` |
| 有限重试 + 指数退避 | ✅ `RetryableLLMClient`（max_attempts/backoff） |
| Rate Limit | ✅ `RateLimitError` 分类 |
| 失败分类 | ✅ 6 类异常（auth/rate/limit/timeout/conn/badrequest/server） |
| Token 记录 | ✅ `LLMUsage` |
| 模型版本 / Prompt Hash | ✅ `metadata` + 配置 |
| 最大调用次数 / 预算 | ✅ `llm_max_calls_per_task` / `budget.py` |
| 真实美元费用 | ✅ `pricing.py`（有定价表时） |
| 幂等恢复 | ✅ 重试 + 结构化重解析 |
| 脱敏 | ✅ `sanitize_message`（密钥不落日志） |

**结论**：Gateway 已具备全部要求的稳定性能力，本轮未重复实现。

## 3. Final Decision Safety Gate（Task B3）

新增 `src/marketpilot/safety/gate.py`：

```
validate_final_decision(task, evidence, selected_candidate, budget_state)
```

检查（全部确定性代码，不依赖 LLM）：
1. candidate 存在 ✅
2. 硬约束（max_price / no_battery / 自定义）✅
3. 必需 facet 证据充分 ✅
4. 证据未过期（freshness window）✅
5. 来源冲突已处理 ✅
6. 引用指向真实快照 ✅
7. 无 Unsupported Claim ✅
8. 预算未超限 ✅
9. 人工审查标记 ✅

失败 → REFUSED 或 HUMAN_REVIEW + 结构化 reason_code
（candidate_missing / constraint_violation / evidence_insufficient /
evidence_stale / conflict_unresolved / citation_missing /
unsupported_claim / budget_exceeded / human_review_required）。

**关键保证**：Unsupported GO（无证据推荐）**永不通过 gate**——即使
Metric Contract 对它的惩罚与拒答相同（测试 `test_unsupported_go_never_passes_gate`）。
13 个单元测试覆盖全部 reason_code 路径；`test_gate_strategy_independent`
验证 gate 不依赖策略家族。

## 4. 分层验证（Task B4）

### B4.1 真实 LLM + 冻结合成工具（24 世界）
- 覆盖：简单研究 / 隐藏风险 / 证据冲突 / 数据过期 / 多候选权衡 /
  预算不足 / 来源异常 / 工具失败（W0-W5 × 4 seeds）。
- LLM 决策 + 工具选择；工具响应由冻结世界提供。
- **无 API key → REAL_LLM_NOT_RUN**（离线 fixture，未伪造真实 LLM 结果）。

### B4.2 Tool Replay + 稳定性（8 任务 × 3 次）
- 固定工具响应快照 + 固定模型配置。
- 结果（离线 fixture）：decision_consistency=1.0、gate_pass_rate=1.0、
  structured_output_success=1.0、tool_call_valid=1.0。
- **REAL_LLM_NOT_RUN**：Token/P50/P95 Latency 需真实模型（留待 key）。

### B5 Shadow Evaluation（骨架）
- 5 个只读研究请求（固定快照，无采购/下单/支付）。
- 每条保存：原始需求 / 结构化约束 / 搜索动作 / 商品实体 / 来源 /
  证据快照 / 冲突缺失 / 推荐或拒答 / Token 与工具成本 / 失败原因。
- **SHADOW_NOT_RUN**（无 key + 未授权）。

## 5. 诚实声明

- 未配置 API key → **没有伪造任何真实 LLM 结果**。
- B4/B5 全部为离线 fixture，明确标记 REAL_LLM_NOT_RUN / SHADOW_NOT_RUN。
- 真实 LLM 数字（Token 成本、P50/P95、决策一致性）留待配置 key 后运行。

## 6. 产物

- `artifacts/milestone_b/b41_llm_vs_strategies.json`
- `artifacts/milestone_b/b42_stability.json`
- `artifacts/milestone_b/b5_shadow_evaluation.json`
- `src/marketpilot/safety/gate.py` + 13 测试

## 7. Release Gate 更新（2026-10-30 第二轮）

| 项 | 状态 |
|---|---|
| Safety Gate 全路径接入（CLI/Workbench/Agent） | ✅ `safety/gateway.py`（唯一出口） |
| 两层指标（pre_gate / gate / post_gate） | ✅ `GatedEmission` 记录 |
| Gate 与 classifier 语义对齐 | ✅ 全候选 evidence_sufficient 前置检查 |
| 对抗性测试 | ✅ `test_gateway_paths.py`（9 测试） |
| LLM 运行清单 | ✅ `llm_run_manifest.json`（5 阶段 + 16 记录项） |
| 输入稳定性（真实路径） | ✅ Neutral Invariance + Material Change + Injection |
| 真实 LLM 执行 | ❌ REAL_LLM_NOT_RUN（无 API Key，未伪造） |
| Shadow 执行 | ❌ SHADOW_NOT_RUN（未授权） |
