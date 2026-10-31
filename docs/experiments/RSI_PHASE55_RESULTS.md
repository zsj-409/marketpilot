# RSI Phase 5.5 Results — 综合报告

| Status | Commit | Date |
|---|---|---|
| EXPERIMENTAL (offline) | worktree (pre-commit) | 2026-10-29 |

## 1. 范围

Phase 5.5 完成：困难诊断世界（W0-W5）、累积 Replay World Pool、Incumbent/Challenger
配对晋级、六类成本账本、Confirmation Shards、预算网格、小规模消融。

## 2. 环境与版本

- Windows 11 / Python 3.12.14（.venv）/ 无 API key / 离线确定性
- 数据：`datasets/synthetic-market-v3/`（seed=7）+ `build_diagnostic_worlds`（W0-W5，
  seed=7/8/9）
- 结果文件：`artifacts/phase55/world_strategy_validation.json`、
  `artifacts/phase55/diagnostic_ablation_results.json`

## 3. 预算网格（W2，Task 4）

同一 `ParameterizedPolicy`（adaptive-voi）在 W2（margin 3.0 / demand 0.5）不同预算：

| budget | decision | selected==best | cost | refused |
|---|---|---|---|---|
| 1.0 | INSUFFICIENT | False | 1.0 | True |
| 2.0 | INSUFFICIENT | False | 1.0 | True |
| 4.0 | INSUFFICIENT | False | 2.5 | True |
| 8.0 | GO | True | 5.5 | False |
| 12.0 | GO | True | 8.5 | False |

**Regret vs Budget 曲线数据**：budget<4 拒答（无决策），>=8 正确。预算偏好
（ρ）与预算上限分离（Task 4）：`budget` 是硬上限，`voi_threshold` 是偏好参数。

## 4. 六世界 x 四策略（Task 6，详见 RSI_DIAGNOSTIC_WORLDS_REPORT.md）

| 世界 | 区分点 | 结果 |
|---|---|---|
| W0 负控制 | 无 | 全正确，仅成本差异（无虚假改善 ✅） |
| W1 隐藏风险 | **adaptive-voi REFUSED** | 系统化策略 7.6 正确；adaptive 3.8 放弃决策 |
| W2 预算 | adaptive 8.5 最省 | 全正确；VOI 归一化有效 |
| W3 时间漂移 | 机制生效 | 全正确；策略未利用时间（无重研究） |
| W4 多候选 | **adaptive GO, 其余 INSUFFICIENT** | VOI 排序在高维世界胜出 |
| W5 分支 | 同 W1 | adaptive REFUSED |

**核心发现**：W1/W5 证明"更便宜 ≠ 更优"（adaptive 省钱但放弃决策）；W4 证明
信息价值排序在高维世界有效。

## 5. 消融（六条件，W0-W4，rounds=3）

| condition | W0 | W1 | W2 | W3 | W4 |
|---|---|---|---|---|---|
| full | 69.3/37.8/3 | 19.0/22.8/0 | 93.5/51.0/3 | 69.3/37.8/3 | 103.4/56.4/3 |
| no-replay | 41.1/0/3 | 26.6/0/0 | 59.5/0/3 | 44.1/0/3 | 65.8/0/3 |
| fixed | 19.5/0/0 | 16.0/0/0 | 26.5/0/0 | 19.5/0/0 | 27.0/0/0 |
| no-diagnostics | 69.3/37.8/3 | 19.0/22.8/0 | 93.5/51.0/3 | 69.3/37.8/3 | 103.4/56.4/3 |
| no-world-pool | 69.3/37.8/3 | 19.0/22.8/0 | 93.5/51.0/3 | 69.3/37.8/3 | 103.4/56.4/3 |
| current-history-only | 69.3/37.8/3 | 19.0/15.2/0 | 93.5/51.0/3 | 69.3/37.8/3 | 103.4/56.4/3 |

（格式：online/replay/promoted）

**解读**：
- 所有 RSI 变体（full/no-diag/no-pool/current）成本几乎相同——minimal 与多数诊断
  世界在默认预算 10 下所有策略都达到正确 → **promoted=3 是平局，不是改进**。
- W1 上全部 0 promoted（adaptive REFUSED → 无法晋级）——**RSI 在 W1 失败**（诚实负结果）。
- fixed 最便宜但永不晋级（固定探索不更新策略，预期）。

## 6. 累积池行为（Task 3）

- `full` 与 `current-history-only` 在 W0-W4 上成本相同（replay 略异：W1 22.8 vs 15.2）
  —— 说明**当前实现中历史池大小对结果无显著影响**（因 dream 只取 active 的最新轨迹
  打分，全历史池虽累积但未被真正用于多轨迹 dream）。
- **已知限制**：pool 累积了，但 dream 打分仍基于单条 observed trajectory；
  "全历史多轨迹 dream"未实现（需对每条历史轨迹分别 replay 再聚合）。

## 7. 负结果

1. **W1 上 RSI 全部 0 晋级**：adaptive-voi 固有 VOI 排序缺陷 → REFUSED。系统化
   （fixed）策略反而成功。这是真实负结果：**RSI 的变体空间（adaptive 系）在隐藏风险
   世界劣于固定策略**。
2. **promoted=3 不代表改进**：所有变体在简单/多数诊断世界都正确决策 → 晋级是平局。
3. **full vs current pool 无差异**：历史池累积未产生行为差异（实现限制）。

## 8. 数据隔离

- oracle 只 evaluator-side（WorldOracle）；策略只消费 AgentWorldView
- test 世界从不进 confirmation shards（`test_locked_test_not_in_shards`）
- 每条件独立 archive 目录；结果可复现（固定 seed）

## 9. 已知限制与未解决风险

1. **dream 打分只用单条轨迹**：全历史池累积但未聚合多轨迹 → full vs current 无差异
2. **无 ρ 预算偏好网格**：官方用 ρ∈{0,.25,.5,.75,1} 多点打分，我们单点
3. **W3 时间信息未利用**：策略无"重研究"动作
4. **多 seed 统计未做**：单 seed 结果，样本量不足以做配对 Bootstrap
5. **Confirmation shard 耗尽只是跳过**：EXHAUSTED 时用 fallback 世界（见代码注释），
   应显式终止而非降级

## 10. 是否满足进入正式多世界 RSI Benchmark 的条件

**部分满足**：
- ✅ 世界机制（W0-W5）真实可区分策略（W1/W4 是关键证据）
- ✅ 成本账本可信（六类分离，无重复计费）
- ✅ Incumbent/Challenger 配对晋级 + PromotionKind 分类
- ✅ Confirmation Shards + Locked Test 隔离
- ❌ 全历史多轨迹 dream 未实现（pool 累积无行为差异）
- ❌ 无 ρ 预算网格、无多 seed 统计

**结论**：机制验证正确，但"累积历史是否真正改善策略"的科学问题**尚未回答**——
需要先实现多轨迹 dream 聚合 + ρ 网格 + 多 seed，才能进入正式 Benchmark。
