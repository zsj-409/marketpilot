# RSI Diagnostic Worlds Spec — MarketPilot Phase 5/6 衔接

| Status | SPEC (design) | Commit | Date |
|---|---|---|---|
| DESIGNED | worktree (pre-commit) | 2026-10-29 |

## 1. 目的

minimal world 的负结果（ABLATION_REPORT.md §7）证明：**简单世界无法区分研究策略**。
本规格设计至少四类能区分策略的开发世界 + 一个信息完整的负控制世界，为 Phase 6 正式
实验提供世界层基础。本轮**只完成规格与必要的最小机制验证**，不开始大规模调参。

## 2. 世界生成规则（通用）

所有世界由 `build_dev_conf_test_worlds(seed=7)` 风格的三划分（dev/confirmation/test）
生成，但**参数化**困难度：

- `n_products`：候选数（minimal=2；诊断世界=4~8）
- `noise_level`：可观察证据与真值的噪声/偏差幅度（0.0=无噪声，0.3=强偏差）
- `conflict_rate`：证据面之间冲突的概率（0.0=无冲突，0.5=半数冲突）
- `stale_rate`：时效变化（可观察值随"时间步"漂移，0.0=静态）
- `missing_rate`：初始缺失的关键证据面比例（0.0=全可见，0.6=大部分需研究动作揭示）
- `action_cost`：每研究动作成本（可配置，控制 budget 约束的松紧）

真值生成（隐藏）：每个产品 `TrueProduct`（true_margin/reliability/demand/competition/risk
→ true_utility → viable），只有 `WorldOracle` 可读。
可观察生成：`ObservableProduct`（observed_* = true_* + noise + bias），Agent 只能看到这些
+ 通过研究动作逐步揭示的证据（`EvidenceFacet`）。

## 3. 四类判别世界

### 3.1 World-A: Evidence-Dependent Decision（证据依赖决策）

- **机制**：决策正确性**强依赖**获取特定证据面（如 margin）。初始可观察值有强偏差
  （noise=0.3），误导选择；只有 `search_margin` 揭示真值后才能正确决策。
- **预期区分**：预算感知策略（adaptive-VOI）在**低预算**下应比固定策略更早获取关键
  证据 → 更低的 regret/cost。fixed（随机顺序）在低预算下会漏掉关键证据 → 高 regret。
- **参数**：n=2（A 真 viable 但 observed_margin 低、B 真非 viable 但 observed_margin 高，
  同 minimal 但噪声更强），noise=0.3, conflict=0, missing=margin
- **最小机制验证**（2026-10-29 实测）：
  - `build_minimal_world` 不研究时，`ParameterizedPolicy._scored` 对 A/B 得**相同分 0.275**
    （未揭示 facet 全部回退 0.5，权重对称），`max()` 平局选第一个 → **碰巧选对**。
  - 因此 minimal world 上"不研究必选错"的前提**不成立**——这是消融五条件全部正确的根因。
  - World-A 必须**打破平局**：给 B 更高的 observed_demand/competition（误导性吸引力），
    使不研究时基于 observable 的评分**明确偏向错误产品**，研究 margin 后才转向正确。
  - ✅ 机制部分验证（发现平局问题），需在 Phase 6 生成时修正偏差参数。

### 3.2 World-B: Conflict-Rich（冲突丰富）

- **机制**：证据面之间**冲突**（如 margin 说 GO、risk 说 NO_GO）。策略必须权衡冲突、
  决定是否继续研究。`_conflicts` 信号（VOI 公式第二项）应驱动 adaptive 策略多花一步
  解决冲突；fixed 会草率决策。
- **预期区分**：adaptive-VOI（含 0.1*conflicts 项）在冲突世界应比 uncertainty/fixed
  更早解决冲突 → 更低 regret。cost 略高但质量更高。
- **参数**：n=4, conflict_rate=0.5, noise=0.15, missing=0
- **验证**：需检查 `_conflicts` 在 `AgentWorldView` 上对 conflict 产品的返回值非空。

### 3.3 World-C: Stale/Time-Varying（时效变化）

- **机制**：可观察证据随"研究轮次"漂移（stale_rate>0）。**先获取的证据可能过时**，
  重研究（re-search）才有价值。策略需要判断"何时重新获取"。
- **预期区分**：adaptive-VOI（基于当前揭示值 vs 基线差异）应在漂移后再研究；
  fixed/uncertainty 可能基于过时证据决策 → 高 regret。
- **参数**：n=4, stale_rate=0.3, noise=0.1, missing=0.2
- **验证**：`AgentWorldView` 需支持"证据随步数漂移"——当前 `take_action` 是静态的，
  需扩展。**标注为未实现**。

### 3.4 World-D: Sparse Evidence（证据稀疏/昂贵）

- **机制**：关键证据面**高成本**（action_cost 高）且**稀疏**（missing_rate 高）。策略
  必须在预算内决定研究哪些产品、哪些面。预算感知是关键。
- **预期区分**：adaptive-VOI（normalized VOI = voi/cost）在高成本下应优先低成本高价值
  动作；fixed（固定顺序）会浪费预算在低价值动作 → 预算耗尽高 regret。
- **参数**：n=6, missing_rate=0.6, action_cost ×2, budget 收紧（如 15）
- **验证**：`FACET_COST` 已可配置（controller 的 `FACET_COST` dict）。

## 4. 负控制世界（Negative Control）

- **World-N**: 信息完整 + 无噪声（noise=0, conflict=0, missing=0, stale=0）。
  所有策略**不需要研究**就能正确决策（可观察值 = 真值）。
- **预期**：所有策略 regret=0、cost≈0（adaptive-VOI 应立即 stop，VOI=0）。
- **用途**：验证 harness 不会把"预算内不做研究"误判为失败；也验证策略不会在
  无信息价值时无谓花钱（若 adaptive 仍花大钱 = 实现 bug）。

## 5. 研究动作与成本

| 动作 | 揭示 | 默认成本 | 诊断世界 |
|---|---|---|---|
| `search_margin` | MARGIN | 1.5 | World-A/C/D 关键 |
| `search_demand` | DEMAND | 1.0 | 通用 |
| `search_risk` | RISK | 1.3 | World-B 关键 |
| `search_reliability` | RELIABILITY | 1.2 | 通用 |
| `search_competition` | COMPETITION | 1.0 | 通用 |
| `search_market` | MARKET | 1.0 | 通用 |

成本可配置（World-D ×2）。

## 6. Oracle 决策

- `WorldOracle`（evaluator-side）：`best_product_id()`（最高 true_utility 的 viable 产品）、
  `viability()` 等。**只有 evaluator 可用**；controller/policy/loop 不读。
- Regret = 1 - I(selected == best)（当前二元）；Phase 7 可扩展为 utility 差。

## 7. 允许的策略输入（防泄漏）

- 策略只消费 `AgentWorldView`：`candidates()`、`observable(pid)`、`revealed_facets(pid)`、
  `evidence_summary(pid)`（已揭示证据）。
- **禁止**：`TrueProduct`/`WorldOracle`/`ground_truth` 任何字段进策略输入。
- 已有 `test_hidden_truth_never_in_policy_input` 验证 view 不暴露 oracle。

## 8. 防泄漏验证（每世界）

1. `view` 上无 oracle 属性（已有测试）
2. 消融最终评价只用 test 世界 + evaluator-side oracle
3. `ExecutionLedger` 记录每笔成本，可审计
4. 世界 manifest（hash）写入，冻结 corpus

## 9. 与最终 Locked Test 的隔离

- **Locked Test**：`datasets/synthetic-market-v3-test-locked/`（**独立目录，不随实验生成**），
  只用于 Phase 7 最终评价，**不参与**任何策略/prompt/memory/skill 修改（V2 规则 3）。
- 诊断世界（World-A/B/C/D/N）全部在 dev/confirmation 划分内；test 版本**仅在最终评价**
  生成一次并冻结。
- 生成脚本记录 seed + 参数 → manifest；任何对 dev 世界参数的修改**不得**触碰 locked test。

## 10. 已知未实现（需 Phase 6 代码工作）

- World-C 的"证据随步数漂移"：`AgentWorldView.take_action` 当前静态，需扩展为
  `stale_rate` 驱动的时间衰减。
- World-D 的可配置 `FACET_COST`：controller 的 `FACET_COST` 是 ClassVar，需改为实例可调。
- 多产品（n>2）的 `build_*` 函数：当前只有 `build_minimal_world`（n=2）。

## 11. 验收（Phase 6 进入条件）

- 四类世界 + 负控制生成，manifest 冻结
- 每世界跑通 `run_all_ablations`，产出**可区分**的 regret/cost（World-A/D 至少有一项
  策略 vs fixed 显著差异）
- 负控制 World-N 上所有策略 cost≈0、regret=0（验证 harness 不误判）
- 全量 ruff/mypy/pytest 绿 + git 提交
