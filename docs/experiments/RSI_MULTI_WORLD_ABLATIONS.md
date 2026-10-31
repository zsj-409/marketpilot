# RSI Multi-World Ablations — Phase 5.6

| Status | Commit | Date |
|---|---|---|
| EXPERIMENTALLY_VALIDATED (exploratory) | worktree (pre-commit) | 2026-10-29 |

## 1. 三种核心比较（Task I 问题 A/B/C）

### A. Full Pool 是否改变策略选择 vs Current-History-Only？

**实验**（W1 隐藏风险，3 rounds，seed=7）：

| pool_mode | promoted | pool_size | round_log |
|---|---|---|---|
| full | b0b94583 (default) | 4 | 3× rollback |
| current | b0b94583 (default) | 4 | 3× rollback |

**结果：无差异**。两者都 3 轮 rollback、active 保持初始 default。

**原因诊断**（Task I 失败分析）：W1 上所有变体都是 adaptive-voi 系（REFUSED），
confirmation 全部失败 → rollback。**pool 机制本身工作正常**（pool_size=4 累积），
但变体空间在 W1 上无法通过确认，所以 pool_mode 差异不显现。

**结论**：Full Pool 未改变策略选择，因为候选变体在该世界族全部失败（非 pool 缺陷）。

### B. 改变后的策略是否在未参与优化的世界改善决策？

本轮未观察到策略改变（见 A）→ 无法评估泛化改善。**负结果**：在当前变体空间
（参数化扰动 adaptive 系）下，RSI 未在 W1 产生可晋级的改进。

### C. Replay 是否减少在线评估成本？

`ExecutionLedger` 分离 `replay_compute_total`（真实离线计算）与
`simulated_action_total`（虚拟历史预算）。消融数据（Phase 5.5）：
full 条件 replay_cost 22.8（W1）vs no-replay 0 —— **Replay 增加离线复杂度**，
未减少在线成本（online 19.0 vs 26.6，full 反而略省在线是因为变体 REFUSED 早停）。
**结论：Replay 当前是纯离线开销，未证明减少在线评估成本**（负结果，需更高效变体）。

## 2. 多 seed 结果矩阵（Task H，数据 artifacts/phase56/multiseed_validation.json）

6 世界 × 5 seeds × 4 策略 = 120 runs。按世界×策略聚合（5 seeds）：

| world | strategy | GO率 | 拒答率 | 正确率 | 均cost |
|---|---|---|---|---|---|
| W0 | fixed/me/unc/voi | 1.0 | 0.0 | 1.0 | 7.6/7.6/7.6/6.3 |
| W1 | fixed/me/unc | 1.0 | 0.0 | 1.0 | 7.6 |
| W1 | adaptive-voi | **0.0** | **1.0** | **0.0** | 3.8 |
| W2 | all | 1.0 | 0.0 | 1.0 | 10/10/10/8.5 |
| W3 | all | 1.0 | 0.0 | 1.0 | 7.6/7.6/7.6/9.3* |
| W4 | fixed/me/unc | **0.0** | 0.0 | 1.0 | 10.7/10.7/10.4 |
| W4 | adaptive-voi | 1.0 | 0.0 | 1.0 | 9.4 |
| W5 | 同 W1 | — | — | — | — |

*W3 adaptive-voi 均 cost 9.3（比 fixed 7.6 高）：refresh 机制让它在 W3 多花 1.7
重新查询 demand（Task E 生效的证据）。

**关键判别力**：
- **W1/W5（隐藏风险）**：adaptive-voi 5/5 seed 全拒答；系统化全成功。
- **W4（多候选）**：系统化 5/5 seed 全 INSUFFICIENT（预算不足）；adaptive-voi 全成功。
- **不同世界族产生不同的策略排序** —— 单策略在所有世界胜出的假设不成立。

## 3. 统计说明（Task I）

- 样本量：6 世界族 × 5 seeds = 30 任务实例（探索性，非最终 Benchmark）。
- 世界数（6）不足以做稳定的世界级 Bootstrap CI → 仅报告探索性估计。
- **不以轨迹节点为独立样本**；聚合按世界族分组。

## 4. 状态标记

EXPERIMENTALLY_VALIDATED（探索性）：机制正确、结果可复现、判别力存在。
NOT_VALIDATED：世界级 Bootstrap CI、正式 Locked Benchmark（样本不足）。
