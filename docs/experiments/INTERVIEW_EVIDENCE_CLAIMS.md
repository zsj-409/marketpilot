# Interview Evidence Claims — 面试可陈述证据

| Status | Commit | Date |
|---|---|---|
| RELEASED | worktree (pre-commit) | 2026-10-30 |

## 目的

区分**可正式陈述**与**仅工程审计**的结论，供算法面试现场使用。

## 1. 可正式陈述（确认性，有数据支撑）

| 编号 | 陈述 | 证据 |
|---|---|---|
| E1 | 发现并修复共享 View 证据污染，建立每方法独立执行隔离 | ViewPollutionError + order-invariance 测试 |
| E2 | 冻结 Metric Contract v2.1：证据不足 GO 损失 ≥ 合理拒答（修复乱猜红利） | task_loss_v21 + 迁移文档 |
| E3 | 新 200 世界独立复验：adaptive-voi 显著劣于系统化家族 | pooled diff +0.338 CI [0.274, 0.403] |
| E4 | 系统化家族（fixed/missing/uncertainty/contextual）行为等价 | 动作覆盖集 Jaccard 1.0 + 结果一致 |
| E5 | fixed 为推荐默认：0 unsupported + 84/120 Supported + OOD 合理拒答 | per_world_metrics_v21.csv |
| E6 | 成本账本逐动作可重建（sum(steps) == total_cost），0 预算违规 | 动作级重建审计 |
| E7 | Dream-RSI 无独立收益，保留 Experimental（诚实负结果） | Phase 5.7/5.8 归因 + 预算匹配对照 |

## 2. 可陈述但标注探索性

| 编号 | 陈述 | 标注 |
|---|---|---|
| E8 | OOD 退化来自证据可得性（非策略） | 4 组合 OOD 有限，探索性 |
| E9 | 任务级 Bootstrap CI 只代表本测试集 | 不构成跨机制族保证 |
| E10 | 合理拒答率 60/80（OOD 证据受限） | 探索性，拒答识别能力 |

## 3. 仅工程审计（不对外陈述）

- INVALIDATED ORIGINAL 的具体数值（uncertainty 0.25/valid 等假象）。
- POST-AUDIT v2 的旧测试集数字（+0.049 CI 跨 0，非显著）。
- W1/W4 RSI 归因细节（Replay 成本 57.7 等）。

## 4. 诚实原则

- **不隐瞒负结果**：adaptive-voi 显著更差、系统化等价、RSI 无收益——全部如实陈述。
- **不夸大**：84/120 是 Supported（含 16 suboptimal），不是 68/120 optimal。
- **不混淆版本**：三类历史结果始终分离。

## 5. 面试现场演示点

1. 隔离执行器 + 顺序不变性测试（代码演示）。
2. Metric v2.1 合同迁移（v2.0 缺陷 → v2.1 修复）。
3. 独立复验配对统计（Bootstrap CI）。
4. 行为等价性诊断（set vs sequence 陷阱）。
5. 成本重建审计（sum(steps) == total_cost）。
