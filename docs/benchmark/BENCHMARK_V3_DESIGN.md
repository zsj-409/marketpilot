# Benchmark v3 Design — 独立市场世界生成与评测环境

| Status | Commit | Date |
|---|---|---|
| IMPLEMENTED + PILOTED | worktree (pre-commit) | 2026-10-29 |

## 1. 架构（Task 1.1：四层分离）

```
Hidden World State   TrueProduct (真实属性/风险/效用)
Observation Model    ObservableProduct + Evidence (噪声/偏差/来源/时间)
Action Environment   ResearchAction / costs / state transitions
Hidden Evaluator     WorldOracle (仅 evaluator 侧)
```

- 隐藏状态只存在于 `World.products`（TrueProduct），`AgentWorldView`
  只暴露 observables + 动作揭示的证据。
- `WorldOracle` 是独立对象，策略/控制器/Agent 永远拿不到。
- 防泄漏测试验证：observable 里无 true_utility/true_risk/viable 键。

## 2. WorldGenerationSpec（Task 1.2）

`src/marketpilot/world/generator.py` 的 `WorldGenerationSpec` 提供 16 个
参数，每个都有**可测试的行为效应**：

| 参数 | 行为效应 |
|---|---|
| product_count | 候选数 |
| candidate_utility_gap | 最优与次优的效用差（决策难度） |
| hidden_risk_strength | 干扰项的隐藏风险幅度 |
| evidence_noise_level | 观测/证据噪声（gauss σ） |
| source_reliability | 主来源可靠概率 |
| source_bias | 系统性偏差（加到观测值） |
| evidence_redundancy | 每 facet 证据副本数 |
| conflict_probability | 冲突来源概率 |
| evidence_missingness | 初始缺失比例 |
| information_acquisition_cost | 基础动作成本 |
| action_cost_asymmetry | facet 间成本不对称 |
| temporal_drift | 时间漂移概率（产生 stale+refresh） |
| market_constraint_difficulty | 可行性阈值（不可行品比例） |
| research_budget | 研究预算 |
| abstention_requirement | 需要拒答的比例 |

**验证**：`test_mechanism_parameters_change_behavior`（quiet vs noisy 产生
不同 config hash + 冲突证据）；`test_generation_deterministic`（同配置
同 seed 完全一致）。

## 3. 观测与隐藏状态的联系（Task 1.3）

- 可观察证据 = 隐藏真值 + gauss(0, noise) + bias（clamped）。
- 关键证据**不是**与效用完全独立：研究 margin/demand/risk 能改变决策
  （Pilot 60/60 世界 research_changes_decision=True）。
- 单个公开字段不泄漏 Oracle：观测值含噪声，best 商品的 ID/位置随机
  （anti-leak shuffle + 随机标签）。

## 4. 机制组合（Task 1.4）

10 个机制家族（conflict/noisy/asym-cost/redundant/drift/scarce/multi-cand/
strict/cheap/balanced），每个是**参数组合**而非重命名模板。Pilot 验证
它们产生结构不同的世界（config hash 不同、冲突/漂移/冗余证据分布不同）。

## 5. 文件

- `src/marketpilot/world/generator.py` — 参数化生成器
- `src/marketpilot/benchmark/validity.py` — Validity Suite
- `src/marketpilot/world/manifest.py` — BenchmarkManifest（数据冻结）
- `scripts/run_benchmark_v3_pilot.py` — 60 世界 Pilot
