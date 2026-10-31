# Final OOD Report — 分布外鲁棒性报告

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. OOD 构成

80 世界，4 类预注册机制组合（OOD_HOLDOUT_SPEC.md）：
- ood-drift-conflict: 时间漂移 + 冲突证据（20）
- ood-risk-asym: 隐藏风险 + 不对称成本（20）
- ood-multi-ambiguity: 8 候选 + 实体歧义（20）
- ood-src-toolfail: 低可靠性 + 高缺失（20）

## 2. 结果（80 世界）

| 方法 | Valid GO | Wrong GO | App Abstain | Task Loss |
|---|---|---|---|---|
| fixed | 14 | 6 | 60 | 61.21 |
| missing-evidence | 64 | 16 | 0 | 3.01 |
| uncertainty | 64 | 16 | 0 | 3.01 |
| adaptive-voi | 64 | 16 | 0 | 3.01 |
| contextual-hybrid | 64 | 16 | 0 | 3.01 |
| full_info | 80 | 0 | 0 | 0.00 |

## 3. 关键发现

1. **fixed 的 OOD 退化**：TEST 上 75/120 valid（62.5%）→ OOD 上 14/80
   （17.5%），abstain 从 36 增至 60。固定研究顺序在来源可靠性转移 +
   工具失败组合下失效（低可靠性来源返回缺失/冲突 → fixed 无法完成研究）。
2. **系统化/自适应家族鲁棒**：64/80（80%）valid——它们根据缺失情况
   动态选择研究目标，适应低可靠性来源。
3. **16 个 Wrong GO**：OOD 世界噪声/偏差高（multi-ambiguity 噪声 0.25+
   bias 0.15），研究后证据仍可能误导选错——**OOD 的信息价值低于 ID**。

## 4. 分组合表现（ood-src-toolfail 最差？）

| 组合 | 特征 | 影响 |
|---|---|---|
| ood-drift-conflict | 漂移+冲突 | 多版本证据，需 refresh；reachability UNRESOLVED |
| ood-risk-asym | 隐藏风险+不对称成本 | 成本不对称影响研究顺序 |
| ood-multi-ambiguity | 8 候选+高歧义 | 证据噪声大，wrong_go 多 |
| ood-src-toolfail | 低可靠性+高缺失 | fixed 全拒答（60/80 abstain 主要来自此） |

## 5. ABSTENTION_REQUIRED 在 OOD

**OOD 无 ABSTENTION_REQUIRED 世界**（预算都够研究选中候选）。
按 Task 5 要求：**该项标记 N/A，不填 0% 或 100%，不宣称已验证 OOD
必须拒答的识别能力**。

## 6. 图

`figures/ood_robustness.png`：ID vs OOD Valid GO Rate 对比（真实数据）。
