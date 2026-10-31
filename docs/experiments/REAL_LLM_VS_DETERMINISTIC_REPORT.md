# Real LLM vs Deterministic Report — 真实 LLM 与确定性策略对比

| Status | Commit | Date |
|---|---|---|
| REAL_LLM_EXECUTED | worktree (pre-commit) | 2026-10-30 |

## 1. 实验设计

- 24 冻结世界（W0-W5 × seed 7-10）。
- **Fixed** 确定性控制器（ParameterizedPolicy）vs **真实 LLM Agent**
  （deepseek-v4-flash，工具循环：research_facet + final_recommendation）。
- 相同环境快照、相同预算、相同 Safety Gate。
- LLM 工具调用强制 required（前 5 轮），最后一轮 auto。

## 2. 配对结果（24 世界）

| 指标 | Fixed | LLM |
|---|---|---|
| GO | 16/24 (67%) | 15/24 (63%) |
| INSUFFICIENT/REFUSED | 8/24 | 9/24 |
| Gate PASS | — | 15 |
| Gate REFUSED | — | 9 |
| Unsupported GO（pre-gate） | 0 | 0 |
| Schema Failure | 0 | 0 |
| 平均 Tokens/世界 | 0 | 3,626 |
| 平均延迟/世界 | <10ms | ~8-16s |

## 3. 主要发现

### 3.1 完成率相当，无显著差异
Fixed 16/24 vs LLM 15/24 GO——真实 LLM 未表现出优于确定性策略的完成率。

### 3.2 LLM 无 Unsupported GO（工具协议有效）
LLM 的 15 个 GO 全部通过 gate（0 拦截）——`tool_choice=required`
强制研究后再决策，防止了无证据推荐（对比 AdaptiveVOI 的 55/120
unsupported）。

### 3.3 决策一致性 50%（12/24）
LLM 与 Fixed 在 12 个世界选同一商品，12 个不同——但不同选择都有效
（gate PASS）。**决策分歧 ≠ 错误**。

### 3.4 W5 多候选：LLM 更主动
W5（3 候选）确定性 INSUFFICIENT（预算内研究不足），LLM 3/4 GO——
真实模型在预算内研究 10-16 工具覆盖更多候选。这是**真实模型的
信息获取优势**（但也付出 2-3× token 成本）。

### 3.5 W4 预算不足：LLM 正确拒答
W4（scarce 预算）确定性 INSUFFICIENT，LLM 3/4 REFUSED（合理拒答），
1 次超预算未决策（W4-10，12 工具 11k tokens）。

## 4. 成本对比

| 项 | Fixed | LLM |
|---|---|---|
| 工具调用 | ~10 步（合成） | 170 次（真实） |
| Tokens | 0 | 87,041 |
| 延迟 | <10ms | P50 8s / P95 16s |
| 美元费用 | 0 | 未计（无 provider 定价表） |

## 5. 结论

1. **真实 LLM 端到端可行**：模型参与需求→研究→决策全流程，工具调用
   真实执行，gate 保护输出。
2. **无性能优势**：完成率与确定性策略相当；LLM 在 W5 更主动但成本
   高 2-3×。
3. **工具协议是安全关键**：required 强制研究 → 0 Unsupported GO。
4. **确定性策略仍是推荐默认**（成本低、确定、gate 友好）；LLM 作为
   Experimental 研究模式。
