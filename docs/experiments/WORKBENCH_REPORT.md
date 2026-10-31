# Agent Workbench Report — 面试现场演示工作台

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 交付物

### workbench.html（自包含单页，49KB）
- **现场运行**：选合成世界（W0-W5 × seed 7-10）+ 策略（5 种）→ 执行真实
  确定性策略 → 展示决策 / 选中商品 / 成本 / 步数 / Outcome / reason_code。
- **Safety Gate 面板**：每次运行显示独立安全门控结果（PASS/REFUSED/
  HUMAN_REVIEW + reason_code）。
- **独立复验结果表**：TEST/OOD 全策略 Supported GO / Optimal / Subopt /
  Unsupported / Abstain / Loss21 / Cost per Supported（来自
  `method_summary_v21.json`，真实数据）。
- **稳定性实验**（B4.2）：status / n_runs / decision_consistency /
  gate_pass_rate（来自 `b42_stability.json`）。
- **真实 LLM 对比**（B4.1）：status / worlds / LLM GO 数 / calls / tokens /
  cost（来自 `b41_llm_vs_strategies.json`）。
- 三版本分离标注（INVALIDATED / v2 / v2.1）。

### serve_workbench.py（本地演示服务器）
- `GET /workbench.html`：静态页。
- `GET /run?world=W1-7&strategy=fixed`：执行真实策略 → JSON
  （decision / selected / cost / steps / outcome / reason / evidence_chain /
  oracle_best / gate / gate_reason）。
- 已验证：W1-7 fixed → valid_go + gate PASS；W4-8 adaptive →
  unsupported_go；W3-7 contextual → valid_go。

### 用法
```
python scripts/build_workbench.py   # 生成 artifacts/milestone_c/workbench.html
python scripts/serve_workbench.py   # http://127.0.0.1:8000/workbench.html
```

## 2. 面试演示流程

1. 打开 workbench → 选 W1-7 + fixed → 显示 valid_go + gate PASS。
2. 切 adaptive-voi（W4-8）→ 显示 unsupported_go（证据不足被 gate 拦）。
3. 展示独立复验表：系统化家族 84/120 Supported vs adaptive 34/120。
4. 展示 Stability：decision_consistency=1.0（确定性）。
5. 说明 B4.1/B4.2 为离线 fixture（REAL_LLM_NOT_RUN），真实 LLM 待 key。

## 3. 数据真实性

- 所有表格/图表数据来自真实实验产物（JSON/CSV），**无伪造**。
- 现场运行调用真实策略代码（ParameterizedPolicy + Safety Gate）。
- 三版本历史结果始终分离展示。

## 4. 产物

- `artifacts/milestone_c/workbench.html`
- `scripts/build_workbench.py`
- `scripts/serve_workbench.py`
