# Workbench Final Release Report — 工作台最终发布报告

| Status | Commit | Date |
|---|---|---|
| FINAL RELEASE | worktree (pre-commit) | 2026-10-30 |

## 1. 发布状态总览

| 能力 | 状态 |
|---|---|
| Safety Gateway 全路径 | ✅ 所有输出路径统一 gateway |
| **证据信任边界** | ✅ 权威状态裁决（`safety/trust.py`） |
| 浏览器真实验收 | ✅ BROWSER_VERIFIED（Playwright） |
| 真实 LLM 执行 | ✅ **REAL_LLM_EXECUTED**（24 世界） |
| Shadow | ❌ SHADOW_NOT_RUN（未授权） |
| 本地服务安全 | ✅ 13 项 ALL_PASS |
| RSI | ⚠️ EXPERIMENTAL（无独立收益证据） |

## 2. 本轮新增

### 证据信任边界（Task A1/A2）
- `safety/trust.py`：`AuthoritativeTaskState`（权威候选集 + 证据状态）
  + `check_evidence_integrity`（伪造/遗漏/错配检测）
  + `gate_with_authoritative_state`（权威裁决，提交链只做交叉校验）。
- **拒绝**：伪造候选、未揭示的 facet 声明、候选遗漏、伪造 selected。
- 11 个回归测试（`test_evidence_trust.py`）。
- Workbench `/api/run` 已接入权威状态 gate。

### 真实 LLM 执行（Task B1/B2）
- Smoke（4 任务）+ 正式（24 世界）全部 REAL_LLM_EXECUTED。
- 修复 3 个 Runtime 缺陷（ToolArguments 截断 / finish_reason 大小写 /
  并行工具截断容错）。
- 结果：Fixed 16/24 vs LLM 15/24 GO；0 拦截；决策一致性 50%。

### 安全审计（Task A3）
- 13 项 ALL_PASS：回环绑定、无 CORS、白名单、路径遍历/代码注入拒绝、
  步数/时间限制、无凭据泄露、HTML 转义（esc()）、结构化错误、纯合成模式。

## 3. 浏览器验收（重跑确认）

- 场景 A（fixed W1-7）：GO + Gate PASS ✅
- 场景 B（adaptive W4-8）：Gate REFUSED ✅
- 场景 D（非法输入）：400 + reason_code ✅
- 窄屏无横滚 ✅（esc() 改动后仍全过）

## 4. 面试演示流程（更新）

1. **Evidence Trust 演示**：展示 gate 基于权威状态（非调用方提交）裁决。
2. **真实 LLM 演示**：Runtime Status 显示 REAL_LLM_EXECUTED + 24 世界
   真实 token/延迟数据。
3. **安全边界演示**：POST /api/run 白名单 + 非法输入拒绝。
4. **RSI 诚实展示**：EXPERIMENTAL 标签。

## 5. 遗留

- SHADOW_NOT_RUN（需授权真实只读源）。
- LLM 美元费用未计（无 provider 定价表）——token 数据真实可查。
