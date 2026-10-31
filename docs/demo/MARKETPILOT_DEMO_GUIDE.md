# MarketPilot Demo Guide — 面试演示指南

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 从全新仓库环境启动（真实命令）

```bash
# 1. 安装依赖（Windows）
cd <repo-root>                # 仓库根目录（克隆后所在路径）
uv sync                          # 或 python -m pip install -e .

# 2. 离线健康检查
.venv/Scripts/python.exe -m pytest tests/ -q     # 311 passed, 1 skipped
.venv/Scripts/ruff.exe check src tests scripts    # All checks passed
.venv/Scripts/python.exe -m mypy src              # no issues

# 3. 启动 Workbench（默认离线，无需 API Key）
.venv/Scripts/python.exe scripts/serve_workbench.py
# 打开 http://127.0.0.1:8000/workbench.html

# 4. 执行成功案例（场景 A）
#   Workbench: 选 W1-7 + fixed → Run
#   → GO + Gate PASS + cost 7.6 + 证据链 margin/demand/risk
#   或命令行:
curl -s -X POST http://127.0.0.1:8000/api/run \
  -d '{"world":"W1-7","strategy":"fixed"}'

# 5. 执行 Safety Gate 拒绝案例（场景 B）
#   Workbench: 选 W4-8 + adaptive-voi → Run
#   → gate REFUSED + evidence_insufficient（Unsupported GO 被拦截）
curl -s -X POST http://127.0.0.1:8000/api/run \
  -d '{"world":"W4-8","strategy":"adaptive-voi"}'

# 6. 查看证据链：Workbench 的 runOut JSON（evidence_chain 字段）
# 7. 查看独立 Benchmark 对照：Experiment Lab 面板（TEST/OOD 全策略表）
# 8. 查看 RSI 晋级/回滚历史：RSI Evolution Observatory 面板
```

## 离线演示模式（无需 API Key）

- 全部 Workbench 功能离线可用（合成世界 + 确定性策略 + Safety Gate）。
- B4.1/B4.2 显示 `REAL_LLM_NOT_RUN`（诚实标记，不用 Mock 冒充）。
- Shadow 显示 `SHADOW_NOT_RUN`。

## 真实 LLM 模式（需授权与费用）

1. 配置 `.env`：`MARKETPILOT_LLM_PROVIDER=openai`、
   `MARKETPILOT_LLM_MODEL=gpt-4o-mini`、`MARKETPILOT_LLM_API_KEY=...`。
2. 明确授权 + 设置实验预算（`llm_max_calls_per_task`、
   `llm_total_call_limit`）。
3. 运行 `python scripts/run_llm_b41.py` → 真实 LLM 数字落盘。
4. API Key 只从环境变量读取，绝不写入前端/日志/截图/Git。

## 3-5 分钟面试讲解词（要点）

1. **为什么需要独立 Evaluation Harness**：确定性、可复现、隐藏真值
   与 Agent 视图隔离；评测结果可审计。
2. **如何发现共享 View 污染**：原始 Locked Evaluation 各方法共享一个
   AgentWorldView → 后方法白嫖前方法证据（cost=0 假 GO）→ 整体
   INVALIDATED；修复 = 每方法独立 view + 顺序不变性测试。
3. **为什么 AdaptiveVOI 在独立测试上退化**：VOI 排序只研究部分 facet →
   大量 unsupported_go（TEST 55/120）；v2.1 合同惩罚无证据推荐 →
   配对 diff +0.338 CI [0.274, 0.403] 显著更差。
4. **为什么不能把 Gate 拦截率当成推荐成功率**：Unsupported GO 被 gate
   拦截 = 安全拦截（好事），但**不是**有效推荐；两层指标
   （pre_gate_outcome / post_gate_outcome）分开记录。
5. **为什么 RSI 暂时不作为默认策略**：W1 仅 1 次真实晋级、W4 0 次、
   Replay 无独立收益（Task 4.3 三问全否定）→ EXPERIMENTAL。
6. **如何用证据和成本支持系统决策**：Cost per Supported GO（fixed
   14.73 vs adaptive 34.71）+ 证据链展示 + 门控 reason_code。

## 技术声明 → 代码/实验对应

| 声明 | 对应 |
|---|---|
| 每方法独立 view | `benchmark/isolation.py` + 测试 |
| Metric v2.1 | `evaluation/outcomes.py::task_loss_v21` |
| Safety Gate 全路径 | `safety/gateway.py` + `test_gateway_paths.py` |
| 独立复验结果 | `artifacts/locked_eval_v21/` |
| RSI 诚实状态 | `docs/experiments/FINAL_RSI_ATTRIBUTION_REPORT.md` |
