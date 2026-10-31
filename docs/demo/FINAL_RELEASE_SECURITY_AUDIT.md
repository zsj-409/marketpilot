# Final Release Security Audit — 最终发布安全审计

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 审计范围

- Safety Gateway（全路径）。
- 证据信任边界（safety/trust.py）。
- Workbench 本地服务（POST /api/run）。
- LLM Runtime（真实调用路径）。
- 数据输出与日志脱敏。

## 2. 结果（13 项 ALL_PASS）

| 检查项 | 结果 |
|---|---|
| 绑定 127.0.0.1 only | ✅ |
| GET /api/status 只读 | ✅ |
| 执行要求 JSON Content-Type | ✅ |
| 无 CORS（禁止跨站触发） | ✅ |
| Host header 容忍 | ✅ |
| 路径遍历拒绝（../../etc/passwd → 400） | ✅ |
| 代码注入拒绝（import os → 400） | ✅ |
| 步数限制（MAX_STEPS=24） | ✅ |
| 时间限制（MAX_SECONDS=10） | ✅ |
| 响应无凭据/内部调试 | ✅ |
| HTML 证据转义（esc()） | ✅ |
| 结构化错误（reason_code） | ✅ |
| 纯合成模式（无付费调用） | ✅ |

## 3. 证据信任边界审计（Task A1）

| 要求 | 实现 | 验证 |
|---|---|---|
| 权威候选集来自任务状态 | `AuthoritativeTaskState.candidate_ids()` | ✅ |
| 选中商品属于真实候选集 | 伪造 selected → REFUSED | ✅ test |
| 关键 facet 与选中商品关联 | 声明未揭示 facet → REFUSED | ✅ test |
| 证据关联合法 Evidence ID/快照 | snapshot_ref 校验 | ✅ gate |
| 缺失/伪造/错配/过期拒绝 | integrity 检查 | ✅ 11 tests |
| 硬约束确定性校验 | gate hard_constraints | ✅ |
| 不读隐藏 Oracle | 签名无 oracle 参数 | ✅ inspect |
| 前端/Worker 不可绕过 | 权威状态裁决 | ✅ |

## 4. LLM Runtime 安全（真实调用）

- API Key 从 Hermes .env 运行时读取，**未写入代码/Git/日志/前端**。
- 脱敏：`sanitize_message`（错误信息中 key 被替换）。
- 预算：llm_max_calls_per_task / llm_total_call_limit 配置存在。
- 真实调用记录：provider/model/tokens/latency 全部落盘。

## 5. 结论

本地 Demo 服务**已具备基本安全加固**（非公网生产级，未宣称）。
证据链来源可信（权威状态裁决）；Safety Gate 信任边界明确。
