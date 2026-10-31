# Shadow Validation Report — Shadow 模式验证报告

| Status | Commit | Date |
|---|---|---|
| SKELETON VERIFIED (SHADOW_NOT_RUN) | worktree (pre-commit) | 2026-10-30 |

## 1. 状态

**SHADOW_NOT_RUN**：未配置搜索 API Key + 未获授权访问真实只读数据源。

骨架已实现（`scripts/run_shadow_b5.py`）并通过离线 fixture 验证：

| 任务 | 结果 |
|---|---|
| shadow-001 键盘 ≤200 无电池 | rec=p5, gate=PASS |
| shadow-002 机械键盘 ≤300 | rec=p5, gate=PASS |
| shadow-003 游戏鼠标 ≤150 | rec=p5, gate=PASS |
| shadow-004 蓝牙音箱 ≤100 | rec=p5, gate=PASS |
| shadow-005 USB-C Hub ≤120 | rec=p5, gate=PASS |

## 2. 只读保证（Task 4）

- **无采购/下单/支付/库存修改/外部系统写操作**——代码路径只有
  fixture 搜索 + gate 判断。
- 每条运行保存：原始需求 / 结构化约束 / 搜索动作 / 商品实体 / 来源
  + 获取时间 / 证据快照 / 冲突与缺失 / 推荐或拒答 / Token 与工具成本
  / 失败原因。
- 无隐藏效用时不输出 Oracle Regret——只用证据可信度 + 约束满足 +
  人工审核指标。

## 3. 启用条件

1. `.env` 配置 `MARKETPILOT_SEARCH_API_KEY`（只从环境变量读取）。
2. 用户明确授权只读数据源访问。
3. 固定 5 个预注册任务 + 记录实验预算。

启用后：`python scripts/run_shadow_b5.py` → 真实只读搜索 + 证据快照 →
gate 判定 → 报告（status 变 SHADOW_RUN）。

## 4. 诚实声明

未授权 → SHADOW_NOT_RUN。**不制造虚假商品研究结果**。
