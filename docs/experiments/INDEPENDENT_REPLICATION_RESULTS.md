# Independent Replication Results — 独立复验结果

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## 1. 数据集

- 120 ID + 80 OOD **全新世界**（seed 500-511 / 700-719），从未查看。
- 0 重复 hash、0 seed 重叠 v3.1 分区。
- Metric Contract v2.1（reason_code + task_loss_v21）。
- GBS 在新 DEV（seed 900-911）重新选择 = **fixed**。

## 2. TEST (120) — Metric v2.1

| 方法 | Valid | Unsupported | Suboptimal | Abstain | Loss21 | Cost/Valid |
|---|---|---|---|---|---|---|
| fixed | 68 | 0 | 16 | 36 | 39.23 | 18.19 |
| missing-evidence | 68 | 0 | 16 | 36 | 39.23 | 18.19 |
| uncertainty | 68 | 0 | 16 | 36 | 39.23 | 18.20 |
| contextual-hybrid | 68 | 0 | 16 | 36 | 39.23 | 18.19 |
| **adaptive-voi** | **26** | **55** | 8 | 31 | **87.57** | 45.40 |

## 3. OOD (80) — Metric v2.1

| 方法 | Valid | Unsupported | Suboptimal | Abstain | Loss21 |
|---|---|---|---|---|---|
| fixed/me/unc/ctx | 16 | 0 | 4 | 60 | 60.75 |
| **adaptive-voi** | **0** | **32** | 0 | 48 | **80.00** |

## 4. 配对统计（世界级配对 Bootstrap，2000 次，95% CI）

| 比较 | TEST diff | OOD diff | pooled diff | 结论 |
|---|---|---|---|---|
| adaptive vs fixed | +0.403 [0.316, 0.491] | +0.241 [0.153, 0.338] | +0.338 [0.274, 0.403] | **adaptive 显著更差** |
| contextual vs fixed | 0.0 | 0.0 | 0.0 | **等价** |
| uncertainty vs fixed | 0.0 | 0.0 | 0.0 | **等价** |

**首次统计支持结论**：adaptive-voi 显著劣于系统化家族（CI 不含 0，三个
split 一致）；系统化家族彼此完全等价。

## 5. 关键发现

1. **adaptive-voi 的 unsupported_go 55/32**：v2.1 下每个损失 1.0（与拒答
   同）——它系统性研究不足（VOI 排序只看部分 facet）→ 大量无证据推荐。
2. **系统化家族行为等价**（68/16/36 完全一致）——预算 12 够研究全部。
3. **OOD 退化来自证据可得性**（不是策略）：系统化家族 60/80 abstain
   （低可靠性来源无法完成研究）——所有策略同受证据限制。
4. **GBS=fixed**（新 DEV 重新选择，valid=70）。

## 6. 与旧结果的关系

- v2（旧测试集）：adaptive 不显著更差（+0.049 CI 跨 0）。
- **v2.1 独立复验：adaptive 显著更差**（+0.338 CI 不含 0）——v2.1 合同
  惩罚 unsupported_go 后，adaptive 的乱猜红利消失，劣势显性化。
- 系统化家族等价在两轮中一致。

## 7. 三类结果分离

1. INVALIDATED ORIGINAL（共享 view）——作废。
2. POST-AUDIT REANALYSIS v2（旧集修复）——探索性。
3. **INDEPENDENT REPLICATION v2.1（新集，本报告）——确认性**。
