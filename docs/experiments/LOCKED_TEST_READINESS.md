# Locked Test Readiness — 正式 Benchmark 就绪度

| Status | Commit | Date |
|---|---|---|
| NOT_READY (blocker identified) | worktree (pre-commit) | 2026-10-29 |

## 1. 已完成

- ✅ Generator（WorldGenerationSpec 16 参数 + 10 机制家族）。
- ✅ Validity Suite（Random/Heuristic/Oracle 自检 + 正负控制 + 防泄漏）。
- ✅ 60 世界 Pilot（48 GO + 12 拒答，正控制 60/60）。
- ✅ BenchmarkManifest（版本/哈希/种子/预算/时间戳 + verify_world）。
- ✅ 数据划分方案（family 分组，pilot split_plan.json）。
- ✅ 指标注册表 v1.0。
- ✅ 预算不透支修复（4 控制器）。
- ✅ 273 passed + ruff/mypy 全绿。

## 2. 阻断问题（Locked Test 前必须解决）

1. **世界规模扩展**：现有 10 家族 × 6 seed = 60 世界，需扩展至
   440（DEV 160 + Confirmation 80 + TEST 120 + OOD 80）且保持独立性
   （需更多家族组合与参数区域，不能仅加 seed）。
2. **abstention_cost 量纲**：`abstention_cost=1.0` vs decision_regret
   ∈ [0, ~0.4]——拒答惩罚偏重。需在 Locked Test 前决策（保持 1.0 作为
   保守业务假设，或归一化到效用量纲），修订需新协议版本。
3. **OOD 结构变化定义**：OOD 80 世界需"事先定义的未见机制组合"
   （如 drift+conflict+asym-cost 三重组合），需在数据生成前冻结定义。
4. **Manifest 冻结流程**：正式数据生成后需冻结 Manifest（git commit +
   dataset_split_hash），验证未修改（verify_world）。

## 3. 不阻断项（已就绪）

- 评测语义（OutcomeClassifier 6 类）。
- Replay Fidelity（24/24）。
- Promotion Gate（REGRESSED/TIED/EXHAUSTED 不晋级）。
- 基线方法集（10 个，Task 7）。
- 统计方案（配对 Bootstrap + 分层，Task 8 协议在 FINAL_BENCHMARK_PROTOCOL）。

## 4. 建议

**暂缓 Locked Test**，下一轮优先：
1. 扩展生成器家族网格至目标规模（可新增机制组合参数）。
2. 冻结 abstention_cost 量纲决策 + OOD 定义。
3. 生成完整数据集 + 冻结 Manifest。
4. 预注册统计容忍度。
5. 然后执行正式 Held-out TEST（本轮禁止）。
