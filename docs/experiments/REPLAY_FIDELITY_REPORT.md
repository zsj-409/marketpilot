# Replay Fidelity Report — 重放保真与泛化差距分离

| Status | Commit | Date |
|---|---|---|
| FIXED + VERIFIED | worktree (pre-commit) | 2026-10-29 |

## 1. 发现的两个严重 Replay Fidelity 缺陷（Task 2.1）

### 缺陷 A：Replay 盲目 GO，不检查证据充分性（REPLAY_MISMATCH）

**症状**：W4 上 fixed/missing-evidence/uncertainty 真实执行 = INSUFFICIENT
（budget 10.7 仍缺关键 facet），但 `HistoricalReplaySimulator.replay_policy`
重放同一轨迹后返回 **GO**（`decision="GO" if selected else "INSUFFICIENT"`，
selected 非空即 GO）。

**根因**：`replay_policy` 第 524-535 行只按 `scores` 非空判 GO，**不检查
REQUIRED_FACETS 是否全 revealed**——与真实 controller 的 `_sufficient`
语义不一致。

**修复**：replay 最终决策复用证据充分性判定：
- adaptive-voi：检查 **selected 候选**的 required facets（与 `_missing_ratio`
  一致——adaptive 只关心被选商品）。
- 系统化家族（fixed/missing/uncertainty）：检查**所有候选**（与 `_sufficient`
  一致）。

### 缺陷 B：Replay 动作丢失 product_id（REPLAY_MISMATCH）

**症状**：W2/W4（多候选）上 adaptive-voi 真实 GO 但 replay INSUFFICIENT。

**根因**：`_record_trajectory` 只记录动作名（`search_margin`），**丢弃
target product_id**。重放时 `view.take_action(action, None)` 作用在第一个
候选上——多候选世界的轨迹被错误重放。

**修复**：`ObservedStep` 增加 `product_id` 字段；`_record_trajectory` 记录
`step.target_id`；`replay_policy` 用 `step.product_id` 定位目标候选。

## 2. 修复后验证（6 世界 × 4 家族 = 24 组合）

```
W4: fixed✓ missing✓ uncertainty✓ adaptive✓
W1: fixed✓ missing✓ uncertainty✓ adaptive✓
W2: fixed✓ missing✓ uncertainty✓ adaptive✓
W3: fixed✓ missing✓ uncertainty✓ adaptive✓
W5: fixed✓ missing✓ uncertainty✓ adaptive✓
W0: fixed✓ missing✓ uncertainty✓ adaptive✓
```

**24/24 决策一致（Replay Fidelity PASS）**。

## 3. Task 2.2：W4 Dev/Confirmation 差异归因（DEV_CONFIRMATION_GAP）

**同世界同策略 replay 现在一致**（缺陷 A/B 已修）。但 W4 的 dev(seed=7) 与
conf(seed=8) 之间策略表现可能不同——这是**分布变化/泛化差距**，不是
Replay Bug：

| 阶段 | W4-dev (seed=7) | W4-conf (seed=8) |
|---|---|---|
| missing-evidence | INSUFFICIENT | INSUFFICIENT（一致） |
| adaptive-voi | GO | GO（一致） |

两个 seed 上各家族决策一致 → **W4 的搜索-确认偏差不是 seed 差异**，而是
**dream 评分（replay 用 dev 轨迹）与 confirmation（conf 实例）的固有偏差**
（replay 重放 dev 轨迹，confirmation 在新实例执行）。

## 4. Task 2.3 诊断分类

| 类别 | 定义 | 测试/案例 |
|---|---|---|
| REPLAY_MISMATCH | 同世界重放与真实决策不一致 | 缺陷 A/B（已修复+24/24 验证） |
| REPLAY_UNSUPPORTED | 未知动作显式拒绝 | `test_replay_unsupported_marked` |
| DEV_CONFIRMATION_GAP | 同策略 dev vs conf 表现差异 | `test_w4_cross_seed_generalization_gap` |
| CROSS_FAMILY_GENERALIZATION_FAILURE | 家族跨世界不迁移 | W1 需系统化 / W4 需 adaptive（泛化 Pilot） |
| POLICY_SELECTION_ERROR | 优化器选错家族 | W4 Full RSI 收敛到 missing-evidence（0 晋级） |

## 5. 对 Phase 5.7/5.8 结论的影响

- **旧报告的 dream_score 偏高**（replay 盲目 GO 虚增）。修复后 W4 上
  missing-evidence 的 dream_score=0.4 < 0.5 → 不再通过 dream gate →
  直接 rollback（kind=None）。
- **Phase 5.8 的"W4 上 RSI 选错家族（REGRESSED）"结论修正为"W4 上 RSI
  无法通过 dream gate（dream 0.4 < 0.5）"**——更严格，结论不变（RSI 在
  W4 无收益）。
- W1 的结论不受影响（r1 IMPROVED 晋级 missing-evidence 仍然成立）。

## 6. 历史报告勘误

PHASE58_REPLAY_ATTRIBUTION.md 中"W4 r1 REGRESSED"的描述，在 replay
fidelity 修复后实际为 "W4 r1 dream gate 失败（dream 0.4<0.5）"。两者都
说明 RSI 在 W4 无收益，但机制不同。历史原始数据保留，此处勘误。
