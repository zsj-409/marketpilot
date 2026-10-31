# Workbench Release Report — 工作台发布报告

| Status | Commit | Date |
|---|---|---|
| RELEASED (BROWSER_VERIFIED) | worktree (pre-commit) | 2026-10-30 |

## 1. 发布状态

| 能力 | 状态 |
|---|---|
| workbench.html 生成 | ✅ COMPLETED |
| 本地服务器（加固） | ✅ E2E_VERIFIED |
| **浏览器真实交互验收** | ✅ **BROWSER_VERIFIED**（Playwright headless Chromium） |
| 真实 LLM 执行 | ❌ REAL_LLM_NOT_RUN（无 API Key） |
| Shadow 执行 | ❌ SHADOW_NOT_RUN（未授权） |

## 2. 浏览器验收结果（Task 6）

| 检查项 | 结果 |
|---|---|
| 首屏加载 | ✅ title 正确、24 世界 + 5 策略下拉 |
| 场景 A：fixed W1-7 | ✅ GO + Gate PASS + cost 7.6 + 6 步 |
| 场景 B：adaptive W4-8 | ✅ **Gate REFUSED + evidence_insufficient**（Unsupported GO 拦截） |
| 场景 D：非法 world/strategy | ✅ 400 + reason_code INVALID_ARGUMENT |
| 窄屏（390px） | ✅ 无横向滚动（table 内部滚动） |
| 桌面（1280px） | ✅ 布局正常 |
| 可访问性 | ✅ label + tab 焦点 + 可见按钮 |
| 4 个展示面板 | ✅ Experiment Lab / Evidence Explorer / RSI Observatory / Runtime Status |

截图：`artifacts/milestone_c/browser_check/01-05_*.png`

## 3. 安全加固（Task 5）

- GET /run → **POST /api/run**（执行与只读分离）。
- world/strategy 白名单（`VALID_WORLDS` / `STRATEGIES`）。
- 请求体 ≤64KB、步数 ≤24、耗时 ≤10s。
- 只监听 127.0.0.1、无 CORS、X-Content-Type-Options: nosniff。
- 所有执行结果经 Safety Gate（无法绕过）。
- 错误返回结构化 reason_code。
- 无 API Key 下发、无敏感信息入日志。

## 4. 展示能力（Task 7）

- **Experiment Lab**：v2.1 独立复验全表（Supported/Unsupported/Abstain/
  Loss/Cost per Supported + OOD 分布）。
- **Evidence Influence Explorer**：W1-7 证据链 + gate 反事实演示
  （明确标注"合成反事实，非真实因果"）。
- **RSI Evolution Observatory**：W1/W4 真实轨迹 + 
  **EXPERIMENTAL — NO VERIFIED INDEPENDENT REPLAY GAIN**（无虚构提升图）。
- **Runtime Status**：SYNTHETIC / REPLAY / REAL_LLM_NOT_RUN 标签 +
  三版本历史（INVALIDATED / v2 / v2.1）。

## 5. 启动

```bash
python scripts/serve_workbench.py   # http://127.0.0.1:8000/workbench.html
```
