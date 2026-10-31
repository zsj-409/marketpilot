# Architecture Walkthrough — 架构讲解

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 分层架构

```
┌─ 输入层 ─────────────────────────────────────────────┐
│ input/ (normalization, constraints, entities,        │
│         isolation: injection scan, perturbation)     │
├─ Agent Runtime ──────────────────────────────────────┤
│ agents/ (planner, research, decision — LLM 或 mock)  │
│ orchestration/ (DAGRunner, planner)                  │
│ product_selection/ (ClosedLoopRunner, critic,        │
│                    decision, workers)                │
├─ 研究层 ─────────────────────────────────────────────┤
│ research/ (providers, store, replay, dedup, budget)  │
│ tools/ (registry, research tools, mock)              │
│ synthetic/ (world generator, sources, environment)   │
├─ 安全层（本轮新增）──────────────────────────────────┤
│ safety/gate.py        — 确定性 Final Decision Gate   │
│ safety/gateway.py     — 全路径统一接入 + 两层指标     │
├─ 评测层 ─────────────────────────────────────────────┤
│ evaluation/ (outcomes, task_loss_v21)                │
│ benchmark/ (isolation, validity, runner, models)     │
├─ 展示层 ─────────────────────────────────────────────┤
│ reporting/ (report, benchmark_html)                  │
│ scripts/serve_workbench.py + workbench.html          │
└──────────────────────────────────────────────────────┘
```

## 2. 数据流（一个研究任务）

1. 用户需求 → `input/normalization`（货币/数量/时间规范化）→
   `input/isolation`（注入扫描）→ 结构化 ResearchTaskSpec。
2. 研究策略（fixed/missing/uncertainty/adaptive/contextual）通过
   `ParameterizedPolicy.execute(view)` 在合成世界上执行，view 记录证据。
3. 证据 → `evaluation/outcomes`（classify_outcome + task_loss_v21）。
4. **最终推荐 → `safety/gateway`（唯一出口）**：CLI/Workbench/Agent
   三条路径全部经 `gate_recommendation` / `gate_workbench_run`。
5. gate 通过 → 输出推荐 + 两层指标（pre_gate/post_gate）。
6. Workbench `/api/run`（POST）→ JSON 含 evidence_chain + gate 结果。

## 3. 隔离保证

- 每方法独立 AgentWorldView（`benchmark/isolation.py`）。
- 方法顺序不变性（permutation 测试）。
- 共享 view 污染 → `ViewPollutionError`。
- Gate 不读隐藏 Oracle（只看 view 证据）。

## 4. 安全边界

- `serve_workbench.py` 只监听 127.0.0.1。
- world/strategy 白名单（无任意路径/动态代码）。
- POST /api/run 执行；GET 只读静态。
- 请求体 ≤64KB、步数 ≤24、时间 ≤10s。
- 无 CORS、无 API Key 下发、X-Content-Type-Options: nosniff。
- 服务端错误返回结构化 reason_code。
