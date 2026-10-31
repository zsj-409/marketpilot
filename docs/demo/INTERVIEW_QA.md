# Interview QA — 面试问答准备

| Status | Commit | Date |
|---|---|---|
| COMPLETED | worktree (pre-commit) | 2026-10-30 |

## Q1: 为什么需要独立 Evaluation Harness？
**A**: 评测必须与优化分离。确定性合成世界 + 隐藏真值隔离（controller
只看 AgentWorldView，oracle regret 在 evaluator 侧算）→ 可复现、可审计。
没有独立 harness，策略优化会过拟合评测漏洞（如乱猜红利）。

## Q2: 共享 View 污染是怎么发现的？
**A**: 审计成本账本时发现 uncertainty cost/valid=0.25 不合理——重算
per-step 成本发现后执行方法 0 步白嫖前方法证据。根因：一个
AgentWorldView 传给所有方法。修复：isolated_execute + 顺序不变性测试
+ ViewPollutionError 负控制。

## Q3: 为什么 AdaptiveVOI 独立测试退化？
**A**: VOI 阈值排序只研究部分 facet → 大量无证据 GO。v2.1 合同把
unsupported_go 损失提到 ≥ 拒答成本（1.0），乱猜红利消失。新 200 世界：
TEST 26 valid + 55 unsupported；配对 diff +0.338 CI [0.274,0.403] 显著更差；
OOD 0 valid。

## Q4: Gate 拦截率为什么不是成功率？
**A**: 拦截 = 阻止了不安全推荐（安全事件），不是完成了任务。两层指标：
pre_gate_outcome（策略产出）vs post_gate_outcome（实际放行）。一个
Unsupported GO 被 gate 拦截应计安全拦截，永远不算商品推荐成功。

## Q5: 为什么 RSI 不是默认策略？
**A**: W1 仅 1 次真实晋级（r1 IMPROVED，r2/r3 TIED），W4 0 次晋级
（search-confirmation 偏差）；Task 4.3 三问全否定（Replay 不改变决策
质量、不减少在线评价、计入采集成本后无优势）。→ EXPERIMENTAL。

## Q6: 如何用证据和成本支持决策？
**A**: 每个推荐有完整证据链（facet × 候选 × 来源）；Cost per Supported
GO 用真实执行成本（fixed 14.73 vs adaptive 34.71）；gate 的 reason_code
结构化记录拒绝原因。

## Q7: 系统化家族为什么行为等价？
**A**: 预算充足（12 够研究全部 facet×候选）时，fixed/missing/uncertainty/
contextual 的 (facet, candidate) 覆盖集相同 → 相同决策（84/120
Supported 完全一致）。仅顺序不同（fixed 按 facet 循环 vs missing 按候选
补全），预算受限时才有差异。诚实报告：它们是一个行为的参数化变体。

## Q8: 无 API Key 时如何证明真实 LLM 能力？
**A**: 不伪造。REAL_LLM_NOT_RUN 标记 + 完整运行清单（llm_run_manifest
记录 5 个 LLM 参与阶段 + 16 项必记录指标）。框架就绪：OpenAI adapter +
structured outputs + retry/backoff + token/费用记录 + Safety Gate 接入。

## Q9: 安全加固做了什么？
**A**: 执行从 GET /run 迁到 POST /api/run（白名单、64KB 限流、24 步/10s
限制）；只监听 127.0.0.1；无 CORS；错误返回 reason_code；gate 无法绕过
（所有输出路径统一 gateway）。

## Q10: 最诚实的负结果是什么？
**A**: RSI 无独立收益（EXPERIMENTAL）、系统化家族等价（非 4 种独立
算法）、AdaptiveVOI 显著更差、原始 Locked Evaluation INVALIDATED。
全部如实报告，不隐瞒。
