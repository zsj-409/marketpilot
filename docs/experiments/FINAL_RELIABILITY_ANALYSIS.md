# Final Reliability Analysis — 最终可靠性分析

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 评测系统可靠性

### 已修复的缺陷
| 缺陷 | 影响 | 状态 |
|---|---|---|
| 共享 AgentWorldView（v1） | 跨方法证据污染 → INVALIDATED | 已修复（独立 view） |
| v2.0 WRONG_GO 混两类 | 乱猜红利（unsupported_go loss≈0.25 < 拒答 1.0） | 已修复（v2.1：≥1.0） |
| GBS 基于污染数据选择 | 无效（uncertainty→fixed） | 已修复（新 DEV 重选=fixed） |

### 隔离保证（v2.1 验证）
- 方法顺序置换 → 结果不变（`run_method_order_invariance` 测试）。
- 脏 view → ViewPollutionError（负控制）。
- PRNG 按 (world, method, repetition) 派生 → 顺序无关。
- 0 预算违规（动作级重建验证）。

## 2. 成本可靠性

- `sum(step_costs) == result.total_cost`（逐动作重建一致）。
- Cost per Valid GO：0 valid → N/A（adaptive OOD 显示 None）。
- 无系统性漏算（200 世界 × 5 方法全部核对）。

## 3. 统计可靠性

- 世界级配对差异 + 分层 Bootstrap（预注册）。
- 抽样单位 = 世界（非轨迹节点）。
- **v2.1 独立复验**：adaptive vs fixed pooled diff=+0.338 CI=[0.274, 0.403]
  ——**显著**（第一次有统计支持的策略差异）。

## 4. 结论可靠性分级

| 结论 | 级别 | 依据 |
|---|---|---|
| adaptive-voi 显著劣于系统化家族 | **确认性** | v2.1 独立复验（新 200 世界） |
| 系统化家族行为等价 | **确认性** | 两轮一致（v2 旧集 + v2.1 新集） |
| OOD 退化来自证据可得性 | **探索性** | OOD 80 世界 4 组合 |
| Replay 无独立收益 | **探索性** | Phase 5.7/5.8 W1/W4 预算匹配 |
| fixed 是可靠默认 | **确认性** | GBS 重选 + 68/120 valid + 0 unsupported |

## 5. 残留风险

1. OOD 拒答任务为 0（预算都够）——OOD 拒答识别能力未验证。
2. 系统化家族等价意味着"4 种方法"实为 1 种行为——报告须如实。
3. RSI 优化效率未在新世界独立复验（W1/W4 探索性）。
4. Cost/Valid 在 OOD 高（53-61）——低可靠性来源成本高。

## 6. 推荐

- **默认生产策略：fixed**（或等价的系统化家族）——可靠、0 unsupported、
  68/120 valid、OOD 16/80（证据受限下的合理拒答）。
- **adaptive-voi 不推荐**（unsupported_go 55/32，显著更差）。
- **RSI 保持 Experimental**（无独立收益证据）。
