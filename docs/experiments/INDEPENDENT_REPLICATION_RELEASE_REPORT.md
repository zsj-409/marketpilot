# Independent Replication Release Report — 独立复验发布报告

| Status | Commit | Date |
|---|---|---|
| RELEASED | worktree (pre-commit) | 2026-10-30 |

## 1. 版本状态

| 版本 | 状态 | 依据 |
|---|---|---|
| INVALIDATED ORIGINAL | 作废 | 共享 AgentWorldView 证据污染（2522aec） |
| POST-AUDIT REANALYSIS v2 | 探索性 | 旧测试集修复执行（861c16e） |
| **INDEPENDENT REPLICATION v2.1** | **确认性** | 新 200 世界 + Metric v2.1（5c122cf, d417f98） |

旧数据全部保留，未覆盖。

## 2. 发布内容

- **数据集**：120 ID + 80 OOD 全新世界（seed 500-511 / 700-719），
  `independent_dataset_manifest.json` 冻结于运行前。
- **隔离**：`isolated_execute()` 独立 view/方法；顺序不变性测试通过。
- **Metric v2.1**：reason_code 拆分 + task_loss_v21（unsupported_go ≥ 拒答）。
- **GBS**：fixed（新 DEV seed 900-911 重选，未用旧无效选择）。

## 3. 发布指标（完整版见 FINAL_METRIC_DICTIONARY.md）

### 主表

| 方法 | TEST Supported | OOD Supported | TEST Unsup | OOD Unsup | Cost/Supported (TEST) |
|---|---|---|---|---|---|
| fixed | 84/120 (70%) | 20/80 (25%) | 0 | 0 | 14.73 |
| missing-evidence | 84/120 | 20/80 | 0 | 0 | 14.73 |
| uncertainty | 84/120 | 20/80 | 0 | 0 | 14.73 |
| contextual-hybrid | 84/120 | 20/80 | 0 | 0 | 14.73 |
| adaptive-voi | 34/120 (28%) | 0/80 (0%) | 55 | 32 | 34.71 |

### 配对统计（任务级 Bootstrap 2000×，95% CI）

| 比较 | TEST diff | OOD diff | pooled diff | 结论 |
|---|---|---|---|---|
| adaptive vs fixed | +0.403 [0.316, 0.491] | +0.241 [0.153, 0.338] | +0.338 [0.274, 0.403] | **显著更差** |
| contextual vs fixed | 0.0 | 0.0 | 0.0 | 等价 |
| uncertainty vs fixed | 0.0 | 0.0 | 0.0 | 等价 |

**CI 解读**：任务级 Bootstrap → 仅代表本测试集条件下策略差异；
不扩展到未知机制族（需新机制分层抽样）。

## 4. 科学结论

1. **adaptive-voi 显著劣于系统化家族**（新世界 + v2.1 合同，首次统计支持）。
2. **系统化家族行为等价**（两轮一致：同一覆盖集 → 同一决策）。
3. **OOD 退化主要来自证据可得性**（所有方法同受低可靠性来源限制；
   系统化家族 60/80 合理拒答，adaptive 32 unsupported 乱猜）。
4. **fixed 为推荐默认**（0 unsupported + 84/120 TEST + 合理拒答）。

## 5. 数据与产物

- `per_world_metrics_v21.csv`（200×5 逐任务）
- `method_summary_v21.json`
- `paired_comparisons_v21.csv`
- `final_metric_dictionary.json`
- `preregistration.json`、`independent_dataset_manifest.json`
