# Ablation Report — MarketPilot Phase 5 Dream-RSI

| Status | Commit | Date |
|---|---|---|
| EXPERIMENTAL (offline) | worktree (pre-commit) | 2026-10-29 |

## 1. 目的

按 V2 规格 §9，对 Dream-RSI 递归优化做**预算可比**的四项消融（+ full 对照），
回答：去掉 Replay、固定探索、去掉历史诊断、去掉世界池扩展后，行为/成本如何变化。

## 2. 消融定义（`src/marketpilot/optimization/ablations.py`）

| condition | 算法行为 |
|---|---|
| `full` | 完整 RSI loop：init 记录 active dev 轨迹 → 每轮 propose 变体 → dream 重放（对 active 的已观察轨迹）→ confirmation DEV → 晋级/回滚（带分类） |
| `no-replay` | 去掉 archive/dream：每轮变体**在线**跑 dev + confirmation，无重放；通过即晋级 |
| `fixed` | 固定探索：每轮随机扰动变体在线跑 dev，**从不晋级**（不更新策略） |
| `no-diagnostics` | RSI loop 但 `dream_threshold=-1.0`（dream 只做重放，不做分歧诊断门控） |
| `no-world-pool` | RSI loop 但用 `dev_world` 同时当 confirmation（无独立世界池） |

**预算可比**：所有条件 `rounds=3`、`DEFAULT_ABLATION_BUDGET=30.0`（在线预算），
同一 seed=7、同一组世界（minimal-dev/confirmation/test）。

## 3. 环境

同 DREAM_RSI_REPORT.md §2：Windows 11、Python 3.12.14、无 API key、离线确定性。

## 4. 实际运行命令

```bash
cd <repo-root>                # 仓库根目录
.venv/Scripts/python.exe -c "
from pathlib import Path
from marketpilot.optimization.ablations import run_all_ablations, write_ablation_report
from marketpilot.world.core import load_worlds
worlds = load_worlds(Path('datasets/synthetic-market-v3'))
outcomes = run_all_ablations(worlds['minimal-dev'], worlds['minimal-confirmation'], worlds['minimal-test'], Path('artifacts/ablations_report'), rounds=3, seed=7)
write_ablation_report(outcomes, Path('artifacts/ablations_report'))
"
# 测试
.venv/Scripts/python.exe -m pytest tests/unit/test_ablations.py -q   # 14 passed
```

## 5. 真实结果（minimal world, seed=7, rounds=3）

| condition | online | replay | total | decision | oracle_correct | regret | promoted |
|---|---|---|---|---|---|---|---|
| full | 48.8 | 36.6 | 85.4 | GO | True | 0.0 | 3 |
| no-replay | 42.7 | 0.0 | 42.7 | GO | True | 0.0 | 3 |
| fixed | 15.0 | 0.0 | 15.0 | GO | True | 0.0 | 0 |
| no-diagnostics | 48.8 | 36.6 | 85.4 | GO | True | 0.0 | 3 |
| no-world-pool | 48.8 | 36.6 | 85.4 | GO | True | 0.0 | 3 |

CSV/JSON 产物：`artifacts/ablations_report/ablation_results.{csv,json}`

## 6. 成本口径（Task A 修复后）

- **online** = 真实 controller episodes（`ControllerResult.total_cost`），经 `ExecutionLedger`
  逐笔记录（round/phase/policy_hash），绝不重复累计（修复了原 3× 虚高 bug）
- **replay** = 离线 dream 重放，用记录的 `ObservedStep.cost` 累加（非估算）
- **total** = online + replay；`budget=30.0` 只约束在线（replay 不花在线预算，单列）
- 死代码（`cost_so_far`/`track_executions`/`_loop_execution_costs`/`_estimate_cost`）已删除

## 7. 结果解读

- **fixed 最便宜**（online 15.0）且决策正确 —— 在 minimal world 上，固定探索 + 随机变体
  就足够找到正确商品。**RSI（full）多花 33.8 online + 36.6 replay 却无质量收益**。
- **no-replay 与 full 同样晋级 3 次**（42.7 online，无 replay）—— 去掉重放不影响
  minimal world 的晋级（因为所有变体在线跑也通过确认）。
- **no-diagnostics / no-world-pool 与 full 成本完全相同**（48.8/36.6）—— 在 minimal world
  上 dream 分歧诊断和独立确认世界都不产生差异（所有变体都一致、都通过）。
- 五种条件 oracle_correct 全 True、regret 全 0.0 → **诚实负结果**：minimal world 无法区分
  策略质量（V2 规则 10）。

**不要把这解读为"消融无差异所以 RSI 无效"**，也不解读为"RSI 有效"——这是**简单世界
缺乏判别力**的必然结果。需要困难分层世界（Task F：RSI_DIAGNOSTIC_WORLDS_SPEC.md）才能
让不同策略产生可区分的 regret/cost 信号。

## 8. 失败案例

1. `test_fixed_does_not_update_policy` 首版断言失败（假设 3×GO，实际有 INSUFFICIENT）：
   修正为"不 promote + 3 次执行"。
2. 账本 3× 重复累计（full 曾显示 134.2 online）：`run_ablation` 每轮新建 loop 累加全部
   ledger。修复：loop 只跑一次。
3. `promoted_hashes` 恒空：`str(s)=="PolicyStatus.PROMOTED"` 永不匹配（实际 `str` 是
   `"promoted"`）。修复：`s is PolicyStatus.PROMOTED`。

## 9. 数据隔离与防泄漏

- test 世界只在最终评价使用（evaluator-side `WorldOracle`）；loop/策略从不读
- 每条件独立 archive 目录（`base_dir/<condition>/`），worlds 由 `register_world` 持久化
- 结果可复现：`test_reproducible_under_fixed_manifest` 断言两次运行 online/replay/decision/
  promoted 完全一致（seed=7, rounds=3）

## 10. 已知限制

- minimal world 无判别力 → 本报告结果**不能**作为 RSI 有效/无效的证据
- `no-replay` 的变体只在 dev+confirmation 在线跑，无 dream；与 full 的行为差异仅在
  minimal world 上不显现（需困难世界）
- replay 世界池不累积（见 RSI_CORRECTNESS_AUDIT.md §4.2）

## 11. 结论

消融 harness 本身正确（预算可比、成本分离、可复现），当前结果 = minimal world 上的
诚实负结果：**所有条件同等正确、成本差异真实但无质量差异**。进入 Task F 困难世界后，
同一 harness 应能产出可区分的 regret/cost 曲线。
