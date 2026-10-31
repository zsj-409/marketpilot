# Phase 5.7 Benchmark Protocol — 强基线对照协议

| Status | Commit | Date |
|---|---|---|
| DEFINED + PARTIALLY_RUN | worktree (pre-commit) | 2026-10-29 |

## 1. 方法集（Task 5）

| # | 方法 | 说明 |
|---|---|---|
| 1 | Fixed | 静态：研究全部必需 facet |
| 2 | MissingEvidence | 静态：只补缺失 facet |
| 3 | Uncertainty | 静态：按分歧驱动 |
| 4 | AdaptiveVOI | 静态：VOI 归一化排序 |
| 5 | Best Static Policy | 在 **Generation DEV** 上用相同评价规范选最优静态（不用测试集） |
| 6 | Random Multi-Family Search | 与 RSI 相同候选空间，随机采样，无 replay |
| 7 | Full Multi-Family Dream-RSI | 全历史池 + 跨家族搜索 |
| 8 | Current-History-Only Dream-RSI | 仅最近轮历史 + 跨家族搜索 |
| 9 | No-Replay Policy Optimization | 候选真实执行评价（非 replay） |

## 2. 两类比较（Task 5）

- **A. 相同新增在线执行预算下的决策质量**：所有方法在线执行次数相同
- **B. 满足预设质量标准时，不同方法的完整优化成本**：含 Archive 采集成本

## 3. 预算协议

- 候选提议预算：每轮 ≤ 4 候选（Manifest 控制）
- 在线探索预算：每个候选 1 次真实执行（confirmation 配对）
- Replay 成本：incremental_replay（离线）单列，不计入在线预算
- 所有方法同一 seed / 任务 / 配置

## 4. 数据隔离

- Generation DEV：轨迹收集、策略提议、参数搜索
- Confirmation DEV：晋级判定（shard 隔离，Fail-Closed）
- Locked Test：**不参与**（本轮不运行）

## 5. 已运行（W1 + W4 初步对照）

数据：`artifacts/phase57/baseline_comparison.json`（见 PHASE57_RESULTS.md §3）。
