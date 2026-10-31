# Final Evaluation Readiness — 最终 Benchmark 就绪度

| Status | Commit | Date |
|---|---|---|
| READY (with gaps) | worktree (pre-commit) | 2026-10-29 |

## 1. Exit Gate 七项检查

| 检查项 | 状态 | 证据 |
|---|---|---|
| 结果评价语义一致 | ✅ | TASK_OUTCOME_CONTRACT.md（6 类结果 + 分离 regret/abstention） |
| Replay Fidelity 与 Generalization Gap 分离 | ✅ | REPLAY_FIDELITY_REPORT.md（24/24 一致 + 分类） |
| Promotion Gate 通过回归测试 | ✅ | test_exit_gate.py（REGRESSED/TIED/EXHAUSTED 不晋级） |
| Baseline 对照公平 | ✅ | PHASE58_BASELINE_PROTOCOL.md（Global Best Static 定义 + No-Replay 补齐） |
| 成本与 Coverage 定义正确 | ✅ | TASK_OUTCOME_CONTRACT.md + PHASE5_EXIT_AUDIT.md §7 |
| 最终 Benchmark Protocol 冻结 | ✅（提案） | FINAL_BENCHMARK_PROTOCOL.md |
| 全量测试与静态检查通过 | ✅ | 260 passed, ruff/mypy 绿 |

## 2. 是否可冻结进入 Locked Test

**部分就绪**。评测正确性（P0 项）已收口，但正式 Benchmark 需先：

1. **扩展世界生成器独立性**：现有 W0-W5 + M1-M6 模板不足以支撑 160/80/
   120/80 规模且互相独立（不能只用 6 模板换 seed）。
2. **生成正式数据划分**：Generation DEV 160 / Confirmation DEV 80 /
   TEST 120 / OOD 80，冻结隐藏真值与划分 hash。
3. **冻结 Manifest**：Commit/Generator/Evaluator/Policy/Dataset/Budget/
   Seed/Metric 版本记录。
4. **预注册非劣容忍度**：查看 Locked Test 结果前确定。

## 3. RSI 状态

**RSI 标记为 Experimental Research Module**：
- W1 上跨家族搜索有效（找到 missing-evidence，IMPROVED 晋级）。
- W4 上无收益（dream gate 拦截，0 晋级）。
- Full Pool / Replay 无独立收益（No-Replay 对照证实）。
- **不为了正向结果继续调参**；保留为可审计的实验模块。
- 已验证有效的默认研究控制器：missing-evidence（W1 GO 正确）。

## 4. 建议

1. 下一阶段（Phase 5.9 或 Benchmark）优先做**世界生成器扩展**（参数化
   组合机制 + 独立隐藏真值），而非 RSI 算法增强。
2. Locked Test 仅在数据划分 + Manifest 冻结后执行。
3. 最终结论可如实报告：**RSI 在 W1 有跨家族搜索收益，但 Replay 机制无
   独立收益；决策质量与成本的"历史经验增益"未被证明**。
