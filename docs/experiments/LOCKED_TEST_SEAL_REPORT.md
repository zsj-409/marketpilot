# Locked Test Seal Report — 数据封存证明

| Status | Commit | Date |
|---|---|---|
| SEALED (v3.1) | worktree (pre-commit) | 2026-10-29 |

## 1. 封存内容

| 项 | 值 |
|---|---|
| benchmark_version | v3.1 |
| 世界总数 | 440（DEV 160 / Conf 80 / TEST 120 / OOD 80） |
| generator_version | 0.2 |
| evaluator_version | 0.2 |
| metric_contract_version | 2.0 |
| execution_mode | frozen |
| dataset_split_hash | 见 benchmark_v31_manifest.json |

## 2. 数据完整性校验（Task 7）

- **440 个 world_config_hash 全唯一**（无重复市场实例）。
- **0 跨分区 spec+seed 重复**（独立性）。
- **0 UNRESOLVED**（全部世界精确可达性判定）。
- Manifest 的 `verify_world(world_id, config_hash)` 可检测数据被修改。

## 3. 隔离保证（Task 7.1）

- Generation DEV：允许开发反馈。
- Confirmation DEV：仅策略确认。
- Held-out TEST + OOD：隐藏真值仅供独立 Evaluator，优化器不可经
  文件路径/运行时对象/Archive/调试接口读取。
- 测试轨迹不进入 Dream Archive。

## 4. 禁止事项（Task 7.2）

- ❌ 未根据 Held-out/OOD 调整策略。
- ❌ 未输出测试集算法性能。
- ❌ 未用测试集选择候选。
- ❌ 未修改损失权重。
- ✅ 仅执行结构完整性检查（hash/重复/可达性/schema）。

## 5. 生成命令（可复现）

```
.venv/Scripts/python.exe scripts/generate_benchmark_v31.py
.venv/Scripts/python.exe scripts/run_benchmark_v3_pilot.py
```

## 6. 版本失效规则

若发现测试集生成 Bug：作废旧版本、创建新版本（v3.2）、记录影响，
**不得静默修改后重新宣称同一次测试有效**。

## 7. 就绪度结论

**数据已封存，评测协议已冻结（v2.0），可以进入正式 Locked Benchmark
（下一轮执行 Held-out TEST + OOD 算法比较）。** 本轮按要求未运行。
