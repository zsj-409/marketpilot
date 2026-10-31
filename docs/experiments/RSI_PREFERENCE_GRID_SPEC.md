# RSI Preference Grid Spec — Phase 5.6

| Status | Commit | Date |
|---|---|---|
| IMPLEMENTED + EXPERIMENTALLY_VALIDATED | worktree (pre-commit) | 2026-10-29 |

## 1. ρ 探索偏好（Task D）

ρ ∈ [0, 0.25, 0.5, 0.75, 1.0] 是**探索偏好**，不是实际预算占比。

- ρ 低（0）：强烈成本偏好 → 高 VOI 停止阈值（尽早停止，倾向低成本研究）。
- ρ 高（1）：强烈探索 → 低 VOI 停止阈值（容忍更多研究）。
- 实际预算 B 独立配置（诊断世界用 2/4/8/12）。

## 2. 实现（`ParameterizedPolicy.execute(preference=...)`）

```python
rho = 0.5 if preference is None else clamp(preference, 0, 1)
# 分段线性映射：(0, 8x), (0.5, 1x), (1, 0.25x)
if rho <= 0.5: scale = 8 - 7*(rho/0.5)
else:          scale = 1 - 0.75*((rho-0.5)/0.5)
VOI_THRESHOLD = clamp(base_threshold * scale, 0.001, 1.0)
```

- 默认（None → ρ=0.5）scale=1.0 → 保持原有 base_threshold（向后兼容）。
- ρ **不能**改变真实世界/隐藏真值；**不能**绕过硬预算（`budget` 是硬上限）；
  **不能**绕过安全约束（REFUSE_THRESHOLD 不变）。

## 3. 验证（W2 世界，budget=10，adaptive-voi）

| ρ | decision | cost | steps | refused |
|---|---|---|---|---|
| 0.00 | INSUFFICIENT | 0.5 | 1 | True |
| 0.25 | INSUFFICIENT | 2.5 | 3 | True |
| 0.50 | GO | 8.5 | 5 | False |
| 0.75 | GO | 8.5 | 5 | False |
| 1.00 | GO | 8.5 | 5 | False |

**3 种不同行为**（ρ=0 立即拒答 / ρ=0.25 部分研究 / ρ≥0.5 完整研究）——
ρ 确实改变执行行为。默认无 ρ = ρ=0.5（GO, 8.5）。

## 4. ρ × 预算 网格（W2，数据见 artifacts/phase56/rho_budget_grid.json）

| ρ \ budget | 2 | 4 | 8 | 12 |
|---|---|---|---|---|
| 0.00 | INS 0.5 | INS 0.5 | INS 0.5 | INS 0.5 |
| 0.25 | INS 1.0 | INS 2.5 | INS 2.5 | INS 2.5 |
| 0.50 | INS 1.0 | INS 2.5 | **GO 5.5** | **GO 8.5** |
| 0.75 | INS 1.0 | INS 2.5 | **GO 5.5** | **GO 8.5** |
| 1.00 | INS 1.0 | INS 2.5 | **GO 5.5** | **GO 8.5** |

（INS = INSUFFICIENT；数字 = cost；粗体 = 正确 GO）

**关键结论**：
- ρ 与预算**独立**（ρ=0 即使 budget=12 也拒答；ρ=0.5+budget=8 才 GO）。
- 正确决策需要 ρ≥0.5 且 budget≥8 —— 两者都必要，互不替代。
- 每个世界/ρ/预算设置保留完整结果（JSON）。

## 5. 状态标记

IMPLEMENTED / EXPERIMENTALLY_VALIDATED（ρ 产生真实行为差异，非空转）。
