# RSI Diagnostic Worlds Report — Phase 5.5

| Status | Commit | Date |
|---|---|---|
| EXPERIMENTAL (offline) | worktree (pre-commit) | 2026-10-29 |

## 1. 目的

验证六种诊断世界（W0..W5）的机制是否真实可区分研究策略。每个世界由预先定义的
机制 + 固定 seed 生成，**不**针对任何策略调参。数据位置：
`artifacts/phase55/world_strategy_validation.json`。

## 2. 环境

Windows 11 / Python 3.12.14（.venv）/ 无 API key / 离线确定性（固定 seed=7）。

## 3. 世界机制（见 `RSI_DIAGNOSTIC_WORLDS_SPEC.md` 扩展实现）

| kind | 机制 | 关键参数 |
|---|---|---|
| W0 | 信息完整负控制 | 所有关键证据可见，无偏差 |
| W1 | 隐藏风险 | observable 偏向坏产品；risk 证据需研究揭示（key=RISK） |
| W2 | 预算与信息价值 | margin 昂贵(3.0)、demand 便宜(0.5) |
| W3 | 时间漂移 | demand 证据 t=0 高(0.7)、t=2 低(0.4) |
| W4 | 多候选+冲突 | 4 候选；产品 C 的 demand 证据与真值冲突 |
| W5 | 真实历史分支 | 复用 W1 机制 + 分支世界 id |

## 4. 运行命令

```bash
cd <repo-root>                # 仓库根目录
# 生成诊断世界 + 六世界 x 四策略验证
.venv/Scripts/python.exe -c "
from pathlib import Path
import json
from marketpilot.world.core import build_diagnostic_world, AgentWorldView, WorldOracle
from marketpilot.optimization.dream_rsi import ParameterizedPolicy
kinds = ['W0','W1','W2','W3','W4','W5']
strategies = ['fixed','missing-evidence','uncertainty','adaptive-voi']
# ... (见仓库内脚本，产物 world_strategy_validation.json)
"
# 测试
.venv/Scripts/python.exe -m pytest tests/unit/test_diagnostic_worlds.py -q   # 11 passed
.venv/Scripts/python.exe -m pytest tests/unit/test_replay_pool.py -q        # 10 passed
```

## 5. 真实结果（六世界 x 四策略，seed=7，budget=10.0）

### W0（负控制：全证据可见）
| strategy | decision | refused | correct | cost |
|---|---|---|---|---|
| fixed | GO | False | True | 7.6 |
| missing-evidence | GO | False | True | 7.6 |
| uncertainty | GO | False | True | 7.6 |
| adaptive-voi | GO | False | True | **6.3** |

**结论**：所有策略正确；adaptive-voi 最省（6.3 vs 7.6）。**无虚假质量改善**（负控制通过）。

### W1（隐藏风险：observable 偏向坏产品）
| strategy | decision | refused | correct | cost |
|---|---|---|---|---|
| fixed | GO | False | True | 7.6 |
| missing-evidence | GO | False | True | 7.6 |
| uncertainty | GO | False | True | 7.6 |
| adaptive-voi | **INSUFFICIENT** | **True** | **False** | 3.8 |

**结论**：W1 **成功区分策略**——adaptive-voi 的贪婪 VOI 排序漏掉关键 facet（A 的
margin/demand），只花 3.8 就 REFUSED；系统化策略（研究全部必需 facet）cost 7.6 正确。
**更便宜 ≠ 更优**：adaptive-voi 的省钱是以放弃决策为代价。

### W2（预算/价值：margin 3.0, demand 0.5）
| strategy | decision | refused | correct | cost |
|---|---|---|---|---|
| fixed | GO | False | True | 10.0 |
| missing-evidence | GO | False | True | 10.0 |
| uncertainty | GO | False | True | 10.0 |
| adaptive-voi | GO | False | True | **8.5** |

**结论**：所有策略正确；adaptive-voi 因 VOI 归一化（voi/cost）优先低成本高价值动作，
cost 8.5 最省。预算网格验证（budget 1/2/4/8/12）：budget<4 REFUSED，>=8 GO 正确
（见 RSI_PHASE55_RESULTS.md §5）。

### W3（时间漂移：demand t0=0.7, t2=0.4）
| strategy | decision | refused | correct | cost |
|---|---|---|---|---|
| fixed | GO | False | True | 7.6 |
| missing-evidence | GO | False | True | 7.6 |
| uncertainty | GO | False | True | 7.6 |
| adaptive-voi | GO | False | True | **6.3** |

**结论**：所有策略正确；adaptive-voi 省 1.3。时间漂移机制本身已验证（t0=0.7 ≠ t2=0.4），
但当前策略未利用时间信息（无重研究动作）——**W3 机制生效但策略无差异**。

### W4（多候选+冲突）
| strategy | decision | refused | correct | cost |
|---|---|---|---|---|
| fixed | INSUFFICIENT | False | True | 10.7 |
| missing-evidence | INSUFFICIENT | False | True | 10.7 |
| uncertainty | INSUFFICIENT | False | True | 10.4 |
| adaptive-voi | GO | False | True | **9.4** |

**结论**：W4 上 fixed/missing/uncertainty 因预算 10.0 不足以研究 4 候选×3 facet 而
INSUFFICIENT；adaptive-voi 用 VOI 排序只研究关键 facet，GO 且正确。**adaptive-voi 在
高维世界胜出**（信息价值排序有效）。

### W5（真实历史分支 = W1 机制）
与 W1 相同：adaptive-voi REFUSED，其余 GO 正确。

## 6. 关键结论

1. **W0 负控制通过**：无虚假质量改善（所有策略同等正确，仅成本差异）。
2. **W1/W5 证明"更便宜 ≠ 更优"**：adaptive-voi 省钱但 REFUSED（放弃决策）。
3. **W2 证明预算敏感**：不同预算产生不同决策质量（<4 拒答，>=8 正确）。
4. **W4 证明信息价值排序在高维世界有效**：adaptive-voi 用 VOI 排序以 9.4 成本正确
   决策，系统化策略预算不足。
5. **W3 机制生效但策略未利用**：需要"重研究"动作才能体现时间价值（已知限制）。

## 7. 已知限制

- W3 策略未利用时间信息（无重研究动作）→ 无法区分
- W4 的 INSUFFICIENT 是预算限制，不是策略缺陷（需更高预算验证）
- 所有世界 seed 固定（seed=7），未做多 seed 统计（Task 7 部分）
- 策略只在单次执行，未做配对 Bootstrap（样本量不足）

## 8. 数据隔离

- dev/confirmation/test 三划分（`build_diagnostic_worlds`，seed=7/8/9）
- oracle 只 evaluator-side；策略/控制器只消费 `AgentWorldView`
- 验证只用了 dev 世界；test 世界未参与
