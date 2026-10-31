# RSI Phase 5.6 Results — 综合报告

| Status | Commit | Date |
|---|---|---|
| EXPERIMENTAL (offline) | worktree (pre-commit) | 2026-10-29 |

## 1. 范围

Phase 5.6 完成：quality_delta 修复（regret-based）、Multi-World Dream Evaluator、
ρ 探索偏好网格、W3 时间刷新、Confirmation Fail-Closed、多 seed 探索实验。

## 2. 环境

Windows 11 / Python 3.12.14（.venv）/ 无 API key / 离线确定性（固定 seed）。
结果文件：`artifacts/phase56/`（multiseed_validation.json、rho_budget_grid.json、
pool_mode_comparison.json）。

## 3. Task A 修复：quality_delta 与 REFUSED

### A1 quality_delta（原 bug → 已修复）
- **原实现**：`quality_delta = 1.0 if selected_id != inc.selected_id and both GO`
  —— 不同商品 ≠ 质量提升（错误）。
- **修复**：`quality_delta = oracle.regret(incumbent) - oracle.regret(challenger)`
  （evaluator-side `WorldOracle`，策略/控制器不读）。同效用不同商品 → delta=0 →
  TIED；更高 regret → REGRESSED。
- 测试：`test_regret_based_quality_delta_..._is_tie`、`test_worse_go_is_regressed`。

### A2 REFUSED 不算成功
- `oracle_correct` 现在要求 `not refused and not human_review`。
- W1 上 adaptive-voi 低成本 REFUSED（cost 3.8, 5 seed 全拒答）保留为负结果：
  **不是高效率**（未完成决策）。

### A3 晋级计数
- `AblationOutcome` 区分 n_quality_improvements / n_efficiency_improvements /
  n_ties / n_regressions（从 round_log 的 kind 统计）。
- TIED 不切换 active。

### A4 成本拆分
- `ExecutionLedger` 新增 `replay_compute_total`（真实离线计算）与
  `simulated_action_total`（虚拟历史预算）——`replay_total` 合并两者但显式标注
  simulated_action 是虚拟的。

## 4. Task B：Multi-World Dream Evaluator

- 实现：`MultiWorldDreamEvaluator.evaluate_policy_on_pool(policy, pool, worlds, ...)`
- 每条轨迹独立重放；按 world_id 聚合（同世界多轨迹不增权）；UNSUPPORTED 不计真实
  regret；不用 Oracle Best-of-Observed。
- 8 项验收测试（见 MULTI_WORLD_DREAM_EVALUATOR.md）。

## 5. Task D：ρ 网格

ρ ∈ {0, .25, .5, .75, 1} 独立于预算 B ∈ {2,4,8,12}。验证（W2）：
- ρ=0 全拒答（cost 0.5）；ρ=0.25 部分研究；ρ≥0.5+budget≥8 正确 GO。
- **ρ 与预算独立且都必要**（ρ=0 即使 budget=12 也拒答）。
- 3 种不同行为 → ρ 发挥作用（非空转）。

## 6. Task E：W3 时间刷新

- `take_action(..., refresh=True)` 重新查询已揭示 facet 的当前时间值。
- 验证：t0=0.7 → 时间推进后 refresh → t2=0.4（值不同）；state_signature 随
  时间变化（不同时间不命中同一缓存）。
- W3 上 adaptive-voi 均 cost 9.3（refresh 多花 1.7）——机制生效。

## 7. Task F：Confirmation Fail-Closed

- shards 耗尽 → `confirmation_exhausted`，该轮不确认、不晋级、无 fallback。
- 测试：`test_confirmation_shard_exhaustion_blocks_promotion`（EXHAUSTED 出现）。

## 8. Task H/I：多 seed 结果

6 世界 × 5 seeds × 4 策略 = 120 runs（30 任务实例）：
- **W1/W5**：adaptive-voi 全拒答（5/5 seed）；系统化全成功。
- **W4**：系统化全 INSUFFICIENT；adaptive-voi 全成功。
- **W0/W2/W3**：全策略正确，仅成本差异。
- **Full vs Current**（W1）：无差异（都 3× rollback）——变体空间在 W1 全失败。

## 9. 科学结论（诚实）

1. **quality_delta 修复**：晋级评价现在基于真实 regret，不再把"选不同商品"当改进。
2. **Multi-World Evaluator 正确**：全池重放 + 世界级聚合实现并测试。
3. **RSI 在本轮测试条件下未产生改进**：Full Pool 未改变策略选择（变体全失败）；
   Replay 是纯离线开销，未证明减少在线成本。**零提升是有效结论**（规格允许）。
4. **判别力存在**：W1/W4 产生不同的策略排序——历史世界累积的机制验证有效。

## 10. 是否具备进入正式 Locked Benchmark 的条件

**部分具备**：
- ✅ 评价正确性（regret-based 晋级、REFUSED 语义、成本拆分）
- ✅ Multi-World 聚合 + 数据隔离
- ✅ ρ/预算 双网格行为验证
- ✅ Confirmation Fail-Closed
- ❌ 变体空间太窄（参数化扰动 adaptive 系）→ W1 无改进可能
- ❌ 世界数（6）不足以做稳定 Bootstrap CI

**建议**：进入正式 Benchmark 前，先扩展变体空间（如允许策略切换 fixed/uncertainty）
让 RSI 在 W1/W4 有"可晋级的改进"空间，否则 RSI 的改进能力无法被检验。

## 11. 状态标记

- IMPLEMENTED: quality_delta 修复、Multi-World Evaluator、ρ 网格、W3 refresh、
  Fail-Closed、成本拆分
- TESTED: 228 passed（单元测试）
- EXPERIMENTALLY_VALIDATED: ρ 行为差异、W3 刷新、多 seed 判别力矩阵
- NOT_VALIDATED: 正式 Benchmark、世界级 Bootstrap CI、RSI 改进收益（本轮为零）
