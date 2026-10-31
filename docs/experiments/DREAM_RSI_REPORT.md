# Dream-RSI Report — MarketPilot Phase 5

| Status | Commit | Date |
|---|---|---|
| EXPERIMENTAL (offline) | worktree (pre-commit) | 2026-10-29 |

## 1. 目的

在 MarketPilot V2 上实现 Dream-RSI（Recursive Self-Improvement through Evolving Worlds）
的最小可验证版本：预算感知的递归策略优化，通过**已观察历史的重放**（dream）评估候选策略，
独立 Confirmation DEV 后晋级/回滚。本报告记录实现、真实运行结果、负结果解释与已知限制。

## 2. 环境与版本

- 平台：Windows 11，git-bash 终端
- Python：3.12.14（`.venv`，uv 管理，editable 安装已修复）
- MarketPilot HEAD：`617e1e4`（phase5 核心）；本报告基于 worktree 未提交修改
- 数据：`datasets/synthetic-market-v3/`（seed=7，dev/confirmation/test 三世界，已提交）
- 无 API key；全部离线确定性（mock provider，固定 seed）

## 3. 实现（`src/marketpilot/optimization/dream_rsi.py`）

- `ParameterizedPolicy`：prefix-only 参数向量策略（8 维：6 个 facet 权重 + voi/refuse 阈值），
  只消费 `AgentWorldView`（不读 oracle）
- `ExplorationTree`：只记录已观察的 (world, state) -> actions（无未来分支）
- `ReplayWorldArchive`：append-only 存档（世界 + 轨迹，按 policy_hash 覆盖最新）
- `HistoricalReplaySimulator`：只重放已记录 state 转移；未知动作**拒绝**（V2 规则 4）；
  显式报告 coverage（分母=可重放动作，排除 stop）
- `DreamEvaluator`：dream score = coverage*(0.5+0.5*success) - 0.1*rejected - 0.1*disagreement
- `PolicyRegistry`：propose → dream_evaluated → promote/rollback；本轮新增
  `PromotionKind`（IMPROVED/EFFICIENCY_GAIN/TIED/REGRESSED/INVALID）+ `classify_outcome`
- `ExecutionLedger`：严格分离 online（真实 controller 执行）与 replay（离线重放）成本
- `RecursiveOptimizationLoop`：init 记录 active dev 轨迹 → 每轮 propose 变体 → dream 重放 →
  confirmation DEV → 晋级/回滚（带分类）

## 4. 实际运行命令

```bash
cd <repo-root>                # 仓库根目录
# 单轮 loop 验证（3 rounds）
.venv/Scripts/python.exe -m pytest tests/unit/test_dream_rsi.py -q
# 全量验证
.venv/Scripts/ruff.exe check src tests && .venv/Scripts/python.exe -m mypy src \
  && .venv/Scripts/python.exe -m pytest tests/
# 消融（含 DREAM/ABLATION 报告数据源）
.venv/Scripts/python.exe -c "
from pathlib import Path
from marketpilot.optimization.ablations import run_all_ablations, write_ablation_report
from marketpilot.world.core import load_worlds
worlds = load_worlds(Path('datasets/synthetic-market-v3'))
outcomes = run_all_ablations(worlds['minimal-dev'], worlds['minimal-confirmation'], worlds['minimal-test'], Path('artifacts/ablations_report'), rounds=3, seed=7)
write_ablation_report(outcomes, Path('artifacts/ablations_report'))
"
```

## 5. 策略配置

- 默认参数：`weight_margin=0.5, weight_demand=0.3, weight_risk=-0.2, weight_reliability=0.1,
  weight_competition=-0.15, weight_market=0.0, voi_threshold=0.04, refuse_threshold=0.20`
- 变体生成：`_propose_variant` 用 `random.Random(1000 + round_index)` 确定性扰动前 6 个权重
  ±0.1
- Dream 阈值：0.5（`dream_threshold`）；分歧惩罚 0.1（本轮从 0.3 下调）
- Budget：controller budget=10.0，max_steps=12；消融统一 `DEFAULT_ABLATION_BUDGET=30.0`

## 6. 真实结果（minimal world, seed=7, rounds=3）

### 6.1 单 loop 分类（本轮新增）

```
round 0 promote kind: improved dream: 1.0
round 1 promote kind: tied     dream: 1.0
round 2 promote kind: tied     dream: 1.0
```

- round 0 的 `improved` 是因为初始 active 从未被 dream 过（`_last_dream_score=0.0`），
  变体 dream=1.0 → delta=1.0 被分类为 improved。
- round 1/2 的 `tied` 是诚实的：变体与历史一致（dream=1.0），与上一 active 无质量差异。

**关键结论：3/3 晋级不代表持续性能改进。** 在 minimal world 上所有变体都正确决策、
dream 无分歧，晋级只是"与历史一致 + 通过确认"的平局（round 1-2 明确分类为 TIED）。
将 3/3 晋级解读为"RSI 持续提升"是错误的（V2 规则 10：允许负结果）。

### 6.2 消融（五条件，预算可比，seed=7）

| condition | online | replay | total | decision | oracle_correct | regret | promoted |
|---|---|---|---|---|---|---|---|
| full | 48.8 | 36.6 | 85.4 | GO | True | 0.0 | 3 |
| no-replay | 42.7 | 0.0 | 42.7 | GO | True | 0.0 | 3 |
| fixed | 15.0 | 0.0 | 15.0 | GO | True | 0.0 | 0 |
| no-diagnostics | 48.8 | 36.6 | 85.4 | GO | True | 0.0 | 3 |
| no-world-pool | 48.8 | 36.6 | 85.4 | GO | True | 0.0 | 3 |

### 6.3 成本口径

- `online` = 真实 controller episodes（init/proposal/confirmation/promote_dev/test），
  来自 `ControllerResult.total_cost`
- `replay` = 离线 dream 重放（模拟动作，用记录的 `ObservedStep.cost`），不计入在线预算
- `total` = online + replay；两者**严格分离**，估算成本不混入实际（Task A.4/A.7）

## 7. 负结果解释

在 minimal world（所有候选可被少量证据区分，无噪声/冲突/时效）上：
- 五种条件**全部**作出正确决策（oracle_correct=True, regret=0.0）
- full 相比 fixed 多花 70.4（48.8 vs 15.0 online）且无质量收益 → **RSI 在简单世界无优势**
- 这不是缺陷，而是预期的**负结果**：需要困难分层世界（Task F）才能产生可区分的信号。
  不得为了得到提升而修改最终测试集（V2 规则 10）。

## 8. 失败案例

- `test_fixed_does_not_update_policy` 首版断言 `["GO","GO","GO"]` 失败：`_random_variant`
  扰动可能使变体在 easy world 上信息不足 → INSUFFICIENT。修正为"不 promote + 3 次执行"。
  这是测试假设错误，不是实现 bug。
- 账本 3× 重复累计（Task C 修复 #1）：`run_ablation` 每轮新建 loop 导致 online 成本 3×
  虚高（134.2 vs 实际 48.8）。已修复。

## 9. 数据隔离

- dev/confirmation/test 三世界独立（`build_dev_conf_test_worlds(seed=7)`）
- loop 只用 dev + confirmation；**test 世界从不参与** loop（`run()` 只收 dev/confirmation）
- oracle（`WorldOracle`）只在消融的**最终评价**（test 世界）evaluator-side 使用，
  控制器/策略/loop 均不读隐藏真值
- `ExecutionLedger` 记录每笔成本，含 round/phase/policy_hash，可审计

## 10. 已知限制（见 RSI_CORRECTNESS_AUDIT.md §4）

1. 无 ρ 预算偏好网格（官方 Eq.1 用 ρ ∈ {0,.25,.5,.75,1}）
2. `ReplayWorldArchive` 每策略只存最新轨迹，不累积多轮历史（官方 trace_pool 累积全部）
3. Confirmation DEV 每轮复用同一 confirmation 世界 → 潜在选择偏差
4. `prev_active_cost` 是占位（恒 0），成本对比未真实生效（默认 TIED）

## 11. 结论

Dream-RSI 最小版本实现正确（统一环境接口、prefix-only、未知动作拒绝、coverage 显式、
成本分离、晋级分类），在 minimal world 上产生诚实的负结果。**当前不具备"证明 RSI 提升"
的证据**；进入困难世界实验（Task F）前需先补齐 ρ 网格与 replay 世界池累积两个扩展。
