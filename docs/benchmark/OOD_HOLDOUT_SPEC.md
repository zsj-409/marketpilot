# OOD Holdout Spec — 分布外测试规格

| Status | Commit | Date |
|---|---|---|
| FROZEN (pre-registered) | worktree (pre-commit) | 2026-10-29 |

## 1. 定义（Task 5）

OOD Stress TEST = 80 世界，4 类**预先声明的结构性变化**（机制组合），
在正式测试前注册，开发集不包含这些完全相同的组合。

## 2. 四类 OOD 组合

| ID | 组合 | 参数 | 结构变化 |
|---|---|---|---|
| O1 | temporal drift + evidence conflict | drift 0.5, conflict 0.5, noise 0.2 | 时间漂移与冲突同时存在 |
| O2 | hidden risk + asymmetric cost | risk 0.6, asym 0.9, cost 1.8 | 隐藏风险 + 成本不对称 |
| O3 | multi-candidate + entity ambiguity | 8 候选, gap 0.05, noise 0.25, bias 0.15 | 多候选 + 高歧义 |
| O4 | source reliability shift + tool failure | reliability 0.4, missing 0.5, conflict 0.3 | 低可靠性 + 高缺失 |

## 3. 与 ID 测试的区分

- ID 测试（DEV/Conf/TEST）覆盖**抽象机制类别**（单机制家族）。
- OOD 是**机制组合**（多机制叠加）——结构性差异，非仅换 Seed。
- 不同 seed 的 ID 世界**不伪装为 OOD**。

## 4. 独立性

- OOD seed 400-419，与 ID 分区 seed 范围（100-311）完全不相交。
- OOD spec hash 与任何 ID spec hash 不同（组合参数不同）。
- 验证：440 世界全 unique hash，0 跨分区重复。

## 5. 本轮状态

OOD 世界已生成（80），**未运行任何算法评价**（符合"禁止提前运行
Locked Test"）。结构变化已预注册，正式测试前冻结此规格。
