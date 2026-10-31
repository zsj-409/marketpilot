# Phase 5.8 Promotion Audit — 3× Promotion 逐轮审计

| Status | Commit | Date |
|---|---|---|
| AUDITED (fixed) | worktree (pre-commit) | 2026-10-29 |

## 1. 审计结论

**W1 上报告的"3× promote"不是 3 次独立质量改进。**

修复前（Phase 5.7）：`registry.promote(proposed.hash)` 在 confirmation 通过后
**无条件执行**，`classify_outcome` 算出的 kind 只写日志、不阻止晋级。

修复后（Phase 5.8）：Promotion Gate 拦截 REGRESSED 与 TIED。

## 2. W1 逐轮审计（修复后真实数据）

| round | incumbent | challenger | incumbent_outcome (regret) | challenger_outcome (regret) | quality_delta | kind | action |
|---|---|---|---|---|---|---|---|
| 1 | adaptive-voi | missing-evidence | INSUFFICIENT (0.4035) | GO (0.0) | +0.4035 | **IMPROVED** | promote |
| 2 | missing-evidence | missing-evidence | GO (0.0) | GO (0.0) | 0.0 | TIED | rollback |
| 3 | missing-evidence | missing-evidence | GO (0.0) | GO (0.0) | 0.0 | TIED | rollback |

**W1 真实有效晋级：1 次**（r1：adaptive REFUSED → missing-evidence GO）。
r2/r3 是同家族同质量平局，TIED 不切换 Active Policy（保留 missing-evidence）。

## 3. W4 逐轮审计（修复后真实数据）

| round | incumbent | challenger | incumbent_outcome (regret) | challenger_outcome (regret) | quality_delta | kind | action |
|---|---|---|---|---|---|---|---|
| 1 | adaptive-voi | missing-evidence | GO (0.0) | INSUFFICIENT (0.43) | -0.43 | **REGRESSED** | rollback |
| 2 | adaptive-voi | adaptive-voi | GO (0.0) | GO (0.0) | 0.0 | TIED | rollback |
| 3 | adaptive-voi | adaptive-voi | GO (0.0) | GO (0.0) | 0.0 | TIED | rollback |

**W4 真实有效晋级：0 次**（adaptive incumbent 保持；missing-evidence 候选因
INSUFFICIENT 被正确判定 REGRESSED 并拒绝）。

## 4. 修复前 vs 修复后

| 指标 | 修复前 (Phase 5.7) | 修复后 (Phase 5.8) |
|---|---|---|
| W1 promotions | 3 (含 2 个假 TIED) | **1 (真实 IMPROVED)** |
| W4 promotions | 3 (全假) | **0** |
| TIED 是否切换 active | 是（错误） | 否 ✓ |
| REGRESSED 是否晋级 | 是（错误） | 否 ✓ |
| REFUSED/INSUFFICIENT regret | 碰巧选中=0 | **全额 best_utility（拒答代价）** |

## 5. 关键修复

1. **INSUFFICIENT 也按拒答计**：`_effective_regret` 判定扩展到
   `refused or human_review or decision == "INSUFFICIENT"`——INSUFFICIENT 不给
   有效推荐，selected_id 碰巧正确不能享受零 regret。
2. **Promotion Gate**：`classify_outcome` 后，REGRESSED/TIED 调
   `registry.rollback`（不晋级），只有 IMPROVED/EFFICIENCY_GAIN 才 promote。
3. **round_log 审计字段**：每轮记录 incumbent/challenger hash、family、
   outcome、regret、quality_delta、cost_delta、kind、action。

## 6. 测试

新增 `test_regressed_challenger_not_promoted`（W4 上 challenger INSUFFICIENT →
rollback+regressed）与 `test_refused_incumbent_replaced_by_go_is_improved`、
`test_tied_not_counted_as_improvement`。

## 7. Task 1.3 逐案例诊断：搜索-确认偏差 vs 泛化失败

对 W4 的 missing-evidence 做三阶段评分：

| 阶段 | 评分 | 结果 |
|---|---|---|
| A. Dream/Replay（W4-dev 轨迹） | GO | ✓ |
| B. Confirmation（W4-conf 实例） | INSUFFICIENT | ✗ |
| C. W1 训练策略在 W4-conf | INSUFFICIENT | ✗ |

**A ≠ B：搜索-确认偏差（非泛化失败）**。根因：Replay 使用 dev 轨迹
（seed=7）评价候选，但 Confirmation 在 conf 实例（seed=8）上执行——两个
W4 实例的冲突证据结构不同，导致 Replay 评分（GO）与真实确认（INSUFFICIENT）
不一致。这是 **Replay 评分与 Confirmation 评价的固有偏差**，不是状态覆盖
错误（replay support=SUPPORTED，重放正确）。

C 与 B 一致说明：跨世界（W1→W4）迁移没有额外恶化——策略本身在 W4 上
INSUFFICIENT，与 A/B 偏差无关。**因此 Promotion Gate（REGRESSED 拦截）
是必要的正确性修复，不是对 Replay 评分的过度惩罚。**
