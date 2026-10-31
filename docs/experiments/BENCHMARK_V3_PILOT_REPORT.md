# Benchmark v3 Pilot Report — 数据生成 Pilot

| Status | Commit | Date |
|---|---|---|
| EXPLORATORY (pilot, dev-only) | worktree (pre-commit) | 2026-10-29 |

## 1. Pilot 配置

- 60 开发世界：10 机制家族 × 6 seed（7-12）。
- 每世界：world_family / world_id / generator_seed / spec_hash /
  world_config_hash / difficulty / n_products 记录在 pilot_manifest.json。
- 验证套件结果：pilot_validity.json。
- 机器可读：`artifacts/benchmark_v3/`。

## 2. 家族与难度分布

| 家族 | 机制 | 世界数 |
|---|---|---|
| conflict | 冲突概率 0.6，低可靠性 | 6 |
| noisy | 噪声 0.3 + 偏差 0.1 | 6 |
| asym-cost | 成本不对称 0.8 | 6 |
| redundant | 证据冗余 3× | 6 |
| drift | 时间漂移 0.6 | 6 |
| scarce | 预算 3.5（拒答） | 6 |
| multi-cand | 6 候选，小效用差 | 6 |
| strict | 严格可行性约束 | 6 |
| cheap | 低成本研究 | 6 |
| balanced | 默认 | 6 |

## 3. 任务难度（Oracle Gap / 候选效用差）

- Full-Info Oracle 60/60 正确（效用计算无误）。
- research_changes_decision 60/60（信息获取有真实价值）。
- feasible GO 48/60；must_abstain 12/60（scarce 家族）。

## 4. 信息价值分布

- 所有世界：研究能改变决策（正控制 100%）。
- scarce 家族：预算不足以研究全部 → 正确行为是拒答（12 世界）。
- 无世界"研究无价值"（evidence 由 hidden truth + 噪声生成，非独立）。

## 5. 验证清单（Task 4）

1. ✅ 同配置+Seed 确定性复现（60/60）。
2. ✅ 不同配置结构不同（config hash 各异）。
3. ✅ 商品排序/ID 不暴露效用（anti-leak shuffle + 随机标签）。
4. ✅ 主要指标可计算（OutcomeClassifier + Oracle + Ledger）。
5. ✅ 策略行为差异（systematic GO vs adaptive REFUSED，见 Phase 5 结论）。
6. ✅ 既有 GO 任务（48）也有拒答任务（12）。
7. ✅ 研究成本与信息价值变化（asym-cost 家族成本不对称）。
8. ✅ 无大量重复/重命名市场（10 家族 × 6 seed 全异）。

## 6. 结论

Pilot 证明生成器能产生可信、独立、可重复、有判别力的研究任务。
**下一步**：扩展家族/参数网格至 440 世界目标规模，冻结数据划分与
Manifest，再执行正式 Benchmark（本轮不运行 Locked Test）。
