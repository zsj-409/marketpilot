# Phase 5.8 Baseline Protocol — 全局最佳静态策略对照

| Status | Commit | Date |
|---|---|---|
| IMPLEMENTED | worktree (pre-commit) | 2026-10-29 |

## 1. 命名修正（Task 4）

- **Per-World Static Oracle Upper Bound**（诊断用，不可部署）：每个世界
  单独选最优家族。
- **Globally Selected Best Static Policy**（可部署）：Generation DEV 上
  选一个固定配置，不按测试世界切换。

## 2. 全局 Best Static 选择协议

1. 只使用 Generation DEV（冻结的开发世界）。
2. 在所有允许开发世界上评价相同静态候选（fixed/missing/uncertainty/
   adaptive-voi）。
3. 预先定义质量优先协议：max correct → min cost。
4. 选一个固定配置。
5. 不在 Confirmation/Test 世界选择。
6. 在独立 Confirmation DEV 上执行并报告。

## 3. 实测结果

### Generation DEV 选择（W1-dev + W4-dev，seed=7）

| 家族 | correct (6 world) | cost |
|---|---|---|
| fixed | 4 | 53.8 |
| missing-evidence | 4 | 53.8 |
| uncertainty | 4 | 53.2 |
| adaptive-voi | **4** | **41.0** ← 选中（成本 tie-break） |

**Global Best Static = adaptive-voi**（W1 上 INSUFFICIENT regret 0.4035，
W4 上 GO regret 0.0）。

### Per-World Oracle UB（诊断，不可部署）

| 世界 | 最优家族 |
|---|---|
| W1-conf | fixed/missing/uncertainty (GO) |
| W4-conf | adaptive-voi (GO) |

## 4. 公平预算协议（Task 5）

| 资源 | 协议 |
|---|---|
| 策略提议数量 | 每方法 3 轮（Random/Full/Current/No-Replay 相同） |
| 新增环境执行预算 | 每轮 1 次 confirmation 执行（相同） |
| Confirmation 预算 | 同 world 同 budget |
| 可用历史数据 | Full Pool 共享同一 Archive |
| 最大优化轮次 | 3 |
| 模型版本 | 确定性启发式（无 LLM） |
| 数据划分 | DEV/Confirmation 隔离 |

## 5. 关键结论

- **Global Best Static 在 W1 上失败**（adaptive INSUFFICIENT），在 W4 上
  成功——单一家族无法同时覆盖两种机制。
- **Per-World Oracle UB 逐世界选家族优于任何单一家族**，但不可部署
  （需 oracle 知道哪个世界）。
- 这是 Contextual Hybrid 的存在理由：用可观察状态近似"per-world 选择"。
