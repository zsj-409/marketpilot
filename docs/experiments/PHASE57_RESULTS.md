# Phase 5.7 Results — 综合报告

| Status | Commit | Date |
|---|---|---|
| EXPERIMENTAL (offline) | worktree (pre-commit) | 2026-10-29 |

## 1. 范围

Phase 5.7 完成：Multi-Family Policy Search（PolicyConfig + MultiFamilyProposer +
ContextualHybridPolicy）、W5 独立多分支、强基线对照实验。

## 2. 环境

Windows 11 / Python 3.12.14（.venv）/ 无 API key / 离线确定性。
结果：`artifacts/phase57/baseline_comparison.json`。

## 3. 基线对照（W1 + W4，真实运行）

### W1（隐藏风险）
| 方法 | decision | correct | cost |
|---|---|---|---|
| fixed / missing / uncertainty | GO | True | 7.6 |
| adaptive-voi | INSUFFICIENT | False | 3.8 |
| **Best Static** | fixed | True | 7.6 |
| **Random Search** | missing-evidence | True | 7.6 |
| **Full RSI** | missing-evidence | True | 7.6 |

### W4（多候选冲突）
| 方法 | decision | correct | cost |
|---|---|---|---|
| fixed / missing / uncertainty | INSUFFICIENT | True* | 10.7/10.7/10.4 |
| adaptive-voi | GO | True | 9.4 |
| **Best Static** | adaptive-voi | True | 9.4 |
| **Random Search** | adaptive-voi | True | 9.4 |
| **Full RSI** | missing-evidence | True* | 10.7 |

*INSUFFICIENT 但 selected 碰巧正确（决策未完成，不算有效 GO）。

## 4. 核心科学结论

### 4.1 跨家族搜索产生真实收益（W1）
Phase 5.6 单家族（adaptive 系）在 W1 上 3× rollback；Phase 5.7 跨家族搜索
**3× promote 并收敛到 missing-evidence**。搜索空间扩大是解锁晋级的必要条件。

### 4.2 RSI 不总是优于静态（W4，负结果）
W4 上 Full RSI 收敛到 missing-evidence（INSUFFICIENT 10.7），**劣于 Best Static
（adaptive-voi 9.4）**。根因：replay 评价信号（基于 dev 轨迹）与 confirmation
真实评价存在偏差（搜索-确认 gap）。

### 4.3 无普适最优家族
W1 系统化家族胜、W4 adaptive-voi 胜。**跨世界经验迁移（Full Pool）未产生收益**：
RSI 的家族选择在不同世界族间不迁移。

## 5. W5 独立多分支（Task 4.1）

W5 从"复用 W1"升级为独立多分支（W5-v2）：3 候选 + 最优产品双分支 demand
（branch1 0.75 / branch2 0.45）。测试验证：`test_w5_branch_world_has_multiple_branches`
（2 个 observed_at 分支）。

## 6. 测试

237 passed（+9 Multi-Family Proposer 测试 + 更新 W5 测试）。

## 7. 是否满足进入 Phase 5.8 Locked Benchmark 的条件

**部分具备**：
- ✅ 跨家族候选生成（PolicyConfig + MultiFamilyProposer）
- ✅ 条件式策略（ContextualHybridPolicy，只用可观察状态）
- ✅ W5 独立多分支
- ✅ 强基线对照协议（Best Static / Random / Full RSI）
- ❌ RSI 家族选择不优于静态（W4 负结果）——需修复搜索-确认 gap
- ❌ 显式 Generation DEV 覆盖扩展器未实现（见 REPLAY_COVERAGE_EXPANSION.md）

**建议**：进入 Locked Benchmark 前，先解决搜索-确认 gap（如用 confirmation 结果
反馈到候选排序，而非仅依赖 replay 信号）。

## 8. 状态标记

- IMPLEMENTED: PolicyConfig / MultiFamilyProposer / ContextualHybridPolicy / W5-v2
- TESTED: 237 passed
- EXPERIMENTALLY_VALIDATED: W1 跨家族晋级、W4 RSI 负结果、基线对照
- NOT_VALIDATED: 多世界统计、Locked Benchmark、RSI 优于静态的证明
