# Benchmark v3.1 Report — 科学性校准与 440 任务构建

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-29 |

## 1. 本轮核心修正

### 1.1 Budget-Constrained Oracle 拆分（Task 1）
- 旧 `_budget_oracle`（最便宜优先）**不是最优 Oracle** → 改名
  CheapestFirstHeuristic。
- 新增 **ExactBudgetedReachabilityOracle**：Dijkstra 式精确枚举，判定
  GO_REACHABLE / ABSTENTION_REQUIRED / UNRESOLVED。
- 性能：multi-cand 世界 11s → 0.07s（首个 GO 即返回）。

### 1.2 拒答标签修正（Task 1.3）
- **旧 12 个 MUST_ABSTAIN 全部错误**：只需研究选中候选（min 3.0），
  budget 3.5 够 GO。
- v3.1：scarce budget → 2.0，精确验证 **6/6 ABSTENTION_REQUIRED**。
- solvability 改用精确 Oracle（feasible_go_path = GO_REACHABLE）。

### 1.3 信息价值正负控制（Task 3.2/3.3）
- 正控制：成对世界（同 spec 不同 seed，噪声 0.15）——无研究时 heuristic
  不能两世界都对；研究后可分别正确。
- 负控制：冗余研究不增价值、初始充分时 research 非必需。

### 1.4 防泄漏增强（Task 4）
- 440 世界验证：全 unique hash、0 跨分区重复、ID/位置/标签无固定对应。
- Full-Info Oracle 现在填充 revealed_facets（evidence-sufficient 语义）。

## 2. 440 世界生成（Task 6）

| Split | 数量 | GO | ABSTAIN | UNRESOLVED |
|---|---|---|---|---|
| DEV | 160 | 144 | 16 | 0 |
| Conf | 80 | 72 | 8 | 0 |
| TEST | 120 | 108 | 12 | 0 |
| OOD | 80 | 80 | 0 | 0 |
| 总计 | **440** | **404** | **36** | **0** |

- 10 ID 家族 × (16/8/12 seed) + 4 OOD 组合 × 20 seed。
- seed 范围分区不相交（100-115 / 200-207 / 300-311 / 400-419）。
- 全部世界精确可达性判定（0 UNRESOLVED）。

## 3. Manifest 冻结（Task 7）

- `benchmark_v31_manifest.json`：完整版本/哈希/种子/预算。
- `split_manifest_v31.json`：440 行（每世界 reachability 判定）。
- dataset_split_hash 基于 world_ids + config hashes + seeds。

## 4. 测试

277 passed + 4 新信息价值测试。Ruff/mypy 全绿（142 文件）。

## 5. 未运行

- ❌ Held-out TEST 算法评价（本轮禁止）。
- ❌ OOD 算法评价（本轮禁止）。
- ✅ 仅结构性检查（hash/重复/可达性/schema）。
