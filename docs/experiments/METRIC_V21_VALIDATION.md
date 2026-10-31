# Metric v2.1 Validation — 合同验证

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. v2.1 是否修复 v2.0 缺陷

| v2.0 缺陷 | v2.1 修复 | 验证 |
|---|---|---|
| unsupported_go loss≈0.25 < 拒答 1.0 | **UNSUPPORTED_GO_LOSS=1.0 ≥ 拒答** | 测试：`test_v21_unsupported_go_loss_not_below_abstention` ✓ |
| WRONG_GO 混两类 | reason_code 拆分 | 测试：`test_v21_suboptimal_go_keeps_positive_regret` ✓ |
| 不必要拒答 1.0（无限拒答风险） | 1.5（+机会损失） | 代码 + 文档 ✓ |
| 约束违规未单列 | 1.5 独立 | 代码 + 文档 ✓ |

## 2. 行为影响（独立复验数据）

| 方法 | v2.0 loss（旧集） | v2.1 loss（新集 TEST） | 变化 |
|---|---|---|---|
| fixed | 37.69 | 39.23 | 基本持平 |
| adaptive-voi | 47.62 | **87.57** | **unsupported_go 惩罚生效** |

**adaptive-voi 的 loss 从 47.6 → 87.6**：v2.1 下其 55 个 unsupported_go
各罚 1.0（v2.0 只罚 regret≈0.25）——**乱猜红利彻底消除**。

## 3. 合理性检查

- **非最优 ≠ 无效**：supported_suboptimal_go 保留正 regret（16 个 TEST）✓
- **合理拒答不加重惩罚**：app_abstain loss=1.0（36 TEST）✓
- **无证据推荐受罚**：unsupported_go loss=1.0 ✓
- **不必要拒答有代价**：1.5（本数据 0 例 unn_abstain——系统化家族不会
  证据充分却拒答）✓

## 4. 敏感性（未调参）

常量（1.0/1.0/0.5/1.5）在读取新测试结果前冻结，**未根据任何策略表现
调整**。合理性依据：安全优先（unsupported ≥ abstention）、机会损失
（unnecessary 高于 appropriate）。

## 5. 结论

v2.1 合同达成设计目标：**不再奖励无证据推荐**；adaptive-voi 的劣势在
新合同下显性化（显著更差）；系统化家族等价性不受影响（0 unsupported）。
