# Final Reproducibility Report — 可复现性报告

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 版本记录

| 组件 | 版本 |
|---|---|
| Benchmark | v3.1（冻结于 16c7e87） |
| Generator | 0.2 |
| Evaluator | 0.2 |
| Metric Contract | 2.0 |
| Evaluation Plan | 1.0（预注册） |
| 数据集 hash | 734f0283…（440 世界） |

## 2. 复现命令

```
# 1. 数据完整性校验（440/440 内容哈希）
#    (split 参数必须与 manifest 一致)
# 2. DEV 基线 + Global Best Static + 冻结策略注册表
.venv/Scripts/python.exe scripts/run_locked_baselines.py
# 3. Held-out TEST + OOD 评价（200 世界 × 9 方法）
.venv/Scripts/python.exe scripts/run_locked_evaluation.py
# 4. 配对统计（Bootstrap 2000 次）
.venv/Scripts/python.exe scripts/run_locked_stats.py
# 5. 5 张核心图
.venv/Scripts/python.exe scripts/run_locked_figures.py
# 6. 失败案例集
.venv/Scripts/python.exe scripts/run_failure_casebook.py
```

## 3. 确定性

- 世界生成：同 (spec, seed, world_id, split) → 相同 config hash
  （440/440 校验通过）。
- 策略执行：确定性启发式（无 LLM、无随机性）→ 结果可精确复现。
- Random 基线：固定 seed=42 → 可复现。
- Bootstrap：固定 seed=42 → CI 可复现。

## 4. 产物清单（artifacts/locked_eval/）

| 文件 | 内容 |
|---|---|
| evaluation_plan.json | 预注册计划（不可变） |
| frozen_policy_registry.json | 冻结策略 + Global Best Static |
| dev_baselines.csv | DEV 基线（160 世界 × 9 方法） |
| per_world_metrics_final.csv | TEST+OOD 逐世界指标（200 × 9） |
| method_summary.json | 方法汇总（TEST/OOD） |
| paired_comparisons.csv | 配对比较 + CI |
| failure_cases.json | 失败案例 |
| figures/*.png | 5 张核心图 |

## 5. 数据完整性

- 冻结数据 440/440 内容哈希校验通过（split 参数一致时）。
- 测试结果未反向进入策略生成/Memory/Archive。
- 本轮未修改任何冻结世界/真值/评分规则。
