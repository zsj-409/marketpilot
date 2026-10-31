# Final Benchmark Protocol — 独立 Benchmark 冻结协议

| Status | Commit | Date |
|---|---|---|
| FROZEN (proposal) | worktree (pre-commit) | 2026-10-29 |

## 1. 数据划分（Task 6.1）

| Split | 目标规模 | 用途 | 隔离 |
|---|---|---|---|
| Generation DEV | 160 | 策略优化/选择 | 冻结，不参与测试 |
| Confirmation DEV | 80 | 晋级确认（新 shard 每轮） | 与 Generation 隔离 |
| Held-out TEST | 120 | 最终 Locked Benchmark | 全程隔离 |
| OOD Stress TEST | 80 | 分布外压力测试 | 全程隔离 |

**约束**：
- 不得用六个模板反复换 Seed 组成全部任务——需要在世界配置、商品属性
  结构、来源模板、风险分布和机制组合层面独立。
- 不同划分不得复用相同隐藏真值或可识别世界实例。
- Generator 参数与划分规则在正式运行前冻结。

## 2. 主要指标（Task 6.2，预注册）

| 指标 | 定义 |
|---|---|
| Valid GO Rate | VALID_GO / 总任务 |
| Task-Level Loss | task_loss 均值（decision_regret 或 abstention_cost） |
| Decision Regret on Valid GO | 仅 VALID_GO 的 regret 均值 |
| Appropriate Abstention Rate | APPROPRIATE_ABSTENTION / 总任务 |
| Unnecessary Abstention Rate | UNNECESSARY_ABSTENTION / 总任务 |
| Hard Constraint Violation Rate | CONSTRAINT_VIOLATION / 总任务 |
| Cost per Successful Decision | online cost / VALID_GO 数 |

## 3. 次要指标（Task 6.3）

Replay Coverage / Episode Support / Candidate Evaluability /
Promotion-Tie-Regression 计数 / P50-P95 Latency / Total Development Cost /
Archive Collection Cost / Replay Compute Cost / Evidence Precision /
Citation Validity / Input Robustness。

## 4. 统计方法（Task 6.4）

- 相同世界上的**配对比较**优先。
- 多 Seed 与共享生成机制任务用分组统计/层级 Bootstrap。
- 同一世界内的轨迹节点**不是**独立样本。
- 独立世界族过少时报告不确定性，限制泛化结论。
- 所有非劣容忍度在查看 Locked Test 结果前确定。

## 5. 数据隔离与冻结（Task 6.5）

Manifest 记录：Commit Hash / World Generator Version / Evaluator Version /
Policy Hash / Dataset Split Hash / Budget Settings / Model Version /
Prompt Hash / Random Seeds / Metric Definitions / Evaluation Script Version。

Locked Test 结果**不得反向进入**策略生成、Memory、Skill 或 Meta-Optimizer。

## 6. 冻结方法集（Task 4）

1. Fixed
2. MissingEvidence
3. Uncertainty
4. AdaptiveVOI
5. ContextualHybrid
6. Globally Selected Best Static（仅 Generation DEV 选择，全局固定）
7. Random Multi-Family Search
8. Full Dream-RSI
9. Current-History-Only RSI
10. No-Replay Online Optimization

**命名**：逐世界最优静态 = `Per-World Static Oracle Upper Bound`（诊断，
不可部署）；全局固定 = `Globally Selected Best Static`（可部署）。

**History Feedback 基线**：当前为固定策略占位实现，**不得描述为完整
历史反馈优化算法**（保留为占位标记）。

## 7. 公平预算协议（Task 4.2）

所有方法控制：初始策略 / 候选空间 / 提议数量 / 历史轨迹访问 / 新增在线
预算 / Confirmation 预算 / 最大轮数 / 世界生成配置 / 模型版本 / 数据划分。
若某方法可逐世界优化，其他方法需可比适配或明确列入研究问题。

## 8. 本轮状态

协议冻结为**提案**，正式 Benchmark 数据生成需扩展世界生成器（独立性），
Locked Test 未运行（Task 10：冻结后执行）。
