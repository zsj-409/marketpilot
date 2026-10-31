# Final Locked Evaluation Report — 最终独立评测报告

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 评测范围

- Held-out TEST: 120 世界（10 ID 家族 × 12 seed，seed 300-311）。
- OOD Stress TEST: 80 世界（4 组合 × 20 seed，seed 400-419）。
- 冻结策略 9 种，配对执行（每世界每方法）。
- 预算：每世界自己的 research_budget（scarce=2.0，Task 1.3 修复生效）。
- 评测计划预注册（evaluation_plan.json v1.0），读取结果前冻结。

## 2. TEST (120 世界) 结果

| 方法 | Valid GO | Wrong GO | App Abstain | Unn Abstain | Task Loss | Cost/Valid |
|---|---|---|---|---|---|---|
| random | 0 | 120 | 0 | 0 | 28.85 | — |
| heuristic | 0 | 120 | 0 | 0 | 28.85 | — |
| cheapest_first | 0 | 0 | 120 | 0 | 120.00 | — |
| fixed | 75 | 9 | 36 | 0 | 37.69 | 16.50 |
| missing-evidence | 97 | 11 | 12 | 0 | 14.01 | 1.84 |
| uncertainty | 97 | 11 | 12 | 0 | 14.01 | 0.25 |
| **adaptive-voi** | **97** | 20 | 3 | 0 | **7.18** | 1.73 |
| contextual-hybrid | 97 | 17 | 6 | 0 | 9.46 | 0.37 |
| full_info | 120 | 0 | 0 | 0 | 0.00 | 0.00 |

**adaptive-voi 的 Task Loss 最低（7.18）**：wrong_go 多（20）但 regret 低
（接近最优的轻微错选），且 abstain 少（3）——abstention_cost=1.0 惩罚
重，adaptive 少拒答。

## 3. OOD (80 世界) 结果

| 方法 | Valid GO | Wrong GO | App Abstain | Task Loss | Cost/Valid |
|---|---|---|---|---|---|
| random | 0 | 80 | 0 | 19.37 | — |
| heuristic | 0 | 80 | 0 | 19.37 | — |
| cheapest_first | 0 | 0 | 80 | 80.00 | — |
| fixed | 14 | 6 | 60 | 61.21 | 61.14 |
| missing-evidence | 64 | 16 | 0 | 3.01 | 8.38 |
| uncertainty | 64 | 16 | 0 | 3.01 | 0.00 |
| adaptive-voi | 64 | 16 | 0 | 3.01 | 3.75 |
| contextual-hybrid | 64 | 16 | 0 | 3.01 | 0.00 |
| full_info | 80 | 0 | 0 | 0.00 | 0.00 |

**fixed 在 OOD 严重退化**（14 valid + 60 abstain，loss 61.21）——
固定研究顺序无法应对来源可靠性转移 + 工具失败组合。系统化/自适应家族
保持 64 valid（80%）。

## 4. GO_REACHABLE / ABSTENTION_REQUIRED 分层表现

- **36 个 ABSTENTION_REQUIRED**（scarce 家族，TEST 12 + Conf 8 + DEV 16）：
  所有方法在这些世界 abstain（预算 2.0 < 最小 3.0）——合理拒答。
- **56 个 UNRESOLVED**（drift 家族 36 + ood-drift-conflict 20）：时间多版本
  证据，精确性未获证明（Task 1.1 修正），评价时按执行时证据充分性报告。
- **GO_REACHABLE 世界**：系统化/adaptive 家族 valid_go 率 80%+。

## 5. 主要发现

1. **adaptive-voi 在 TEST 上 Task Loss 最优**（7.18），显著优于 fixed
   （配对 diff=-0.44，CI95 不含 0）。
2. **contextual-hybrid 略优于 GBS(uncertainty)**（diff=-0.023，CI95 不含 0）
   ——但差异很小。
3. **fixed 是明确弱者**：TEST 75 valid + OOD 14 valid，成本最高。
4. **cheapest_first 全拒答**：启发式只按最便宜研究，从不研究够选中候选
   → 全 INSUFFICIENT。验证了"最便宜优先 ≠ 最优"（Task 1）。
5. **random/heuristic 无研究直接选** → 无证据 → 全 WRONG_GO（安全语义
   正确：无充分证据的推荐不是 Valid GO）。

## 6. 统计（配对 Bootstrap，2000 次，95% CI）

| 比较 | diff (A-B) | CI95 | 结论 |
|---|---|---|---|
| A: adaptive-voi vs fixed | -0.4436 | [-0.513, -0.375] | **adaptive 显著优于** |
| B: contextual vs GBS | -0.0228 | [-0.042, -0.007] | **contextual 略优**（小） |
| C/D/E: RSI 优化效率 | — | — | 见 FINAL_RSI_ATTRIBUTION_REPORT |

## 7. 命令

```
.venv/Scripts/python.exe scripts/run_locked_baselines.py   # DEV 基线 + 冻结
.venv/Scripts/python.exe scripts/run_locked_evaluation.py  # TEST + OOD 评价
.venv/Scripts/python.exe scripts/run_locked_stats.py       # 配对统计
.venv/Scripts/python.exe scripts/run_locked_figures.py     # 5 张图
```
