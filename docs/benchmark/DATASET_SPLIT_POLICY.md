# Dataset Split Policy — 数据划分与独立性

| Status | Commit | Date |
|---|---|---|
| DESIGNED (pilot) | worktree (pre-commit) | 2026-10-29 |

## 1. 目标规模（保留自 FINAL_BENCHMARK_PROTOCOL）

| Split | 规模 | 用途 |
|---|---|---|
| Generation DEV | 160 | 策略优化/选择 |
| Confirmation DEV | 80 | 晋级确认 |
| Held-out TEST | 120 | 最终 Locked Benchmark |
| OOD Stress TEST | 80 | 未见机制泛化 |

## 2. 划分原则（Task 5）

- **按市场实例/商品家族/来源模板/机制组合分组**，不随机分配 task_id。
- **同一潜在市场实例不能进入不同数据集**（世界实例唯一）。
- **同一隐藏商品真值的重命名版本不能跨分区**（config hash 校验）。
- 测试集结果/轨迹不进入优化器/Memory/Archive。
- Confirmation 数据不无限重复用于自适应调参。
- OOD 包含**事先定义的未见结构变化**（机制组合未在 DEV 出现）。

## 3. Pilot 划分方案（split_plan.json）

10 个机制家族按族分组：
- Generation DEV: conflict / noisy / asym-cost / redundant / drift / scarce
- Confirmation DEV: multi-cand / strict
- Held-out TEST: cheap / balanced
- OOD: **未见机制组合**（如 drift+conflict+asym-cost 三重组合）

**规则**：同一 family 永不跨 dev/test；市场实例唯一。

## 4. 重复检测

- 精确重复：config hash 相同 → 剔除。
- 高度近似：同 (spec_hash, seed) 不同 world_id → 实例唯一（config hash
  含 world_id，天然区分）。
- 验证：`test_old_vs_new_worlds_no_cross_split_reuse`。

## 5. 状态

划分机制已设计并在 Pilot 验证（60 世界 10 家族分组）。正式 440 世界
生成需扩展家族/参数网格，达到质量后冻结。
