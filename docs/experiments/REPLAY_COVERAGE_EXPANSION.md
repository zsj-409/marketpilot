# Replay Coverage Expansion — Phase 5.7

| Status | Commit | Date |
|---|---|---|
| PARTIALLY_IMPLEMENTED | worktree (pre-commit) | 2026-10-29 |

## 1. 目标（Task 2）

策略家族扩大后，新候选会请求历史未执行的动作。不能伪造历史观测来提高覆盖——
必须通过**受预算约束的 Generation DEV 真实执行**补充分支。

## 2. 覆盖指标（已实现，见 HistoricalReplaySimulator）

| 指标 | 定义 | 状态 |
|---|---|---|
| Replay Hit | 成功匹配历史状态+动作并得到已记录结果 | ✅ |
| Unsupported Action | 策略请求历史中不存在的动作 | ✅ |
| Attempt Coverage | hits / (hits + unsupported)，不计 STOP | ✅ |
| Episode Support Rate | 完整策略路径都得到支持的任务比例 | ✅ |
| Archive Action Coverage | 已观察动作 / 完整合法动作空间 | ⚠️ 需扩展（合成环境可确定合法空间） |
| Marginal Coverage Gain | 新分支的边际覆盖增益 | ⚠️ 需实现 |

## 3. 已实现的扩展机制

### 3.1 W5 多分支世界（Task 4.1）
W5 从"复用 W1"升级为独立多分支结构（W5-v2）：
- 3 候选（a viable, b/c 非 viable）
- 最优产品 a 的 demand 证据含**双分支**（branch1 t=0: 0.75 / branch2 t=2: 0.45）
- 不同研究顺序/时间获得不同合法观测
- 未观察分支仍被 Replay 拒绝（state_signature 不匹配）

### 3.2 Multi-Family 轨迹多样性
proposer 生成 cross-family 候选 → loop 记录不同家族的轨迹到 Archive → 历史覆盖
自然扩展（不同家族执行不同动作序列）。

## 4. 未实现（已知限制）

- **显式 Generation DEV 探索扩展器**：从冻结 dev 世界用多基线策略真实执行不同路径
  并 append-only 加入 Archive 的独立模块尚未实现（当前靠 loop 内部执行积累）。
- **Marginal Coverage Gain 报告**：新增分支的边际覆盖增益计算未实现。
- **Archive Action Coverage**：完整合法动作空间的覆盖度未实现（需枚举 ResearchAction
  × 产品 × 状态）。

## 5. 状态标记

PARTIALLY_IMPLEMENTED：W5 多分支 + 多家族轨迹多样性已实现；显式探索扩展器与
边际覆盖报告为后续工作。
