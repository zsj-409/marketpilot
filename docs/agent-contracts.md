# Agent Contracts

Agents are typed roles with explicit responsibilities. They are not chat personas and do not call provider SDKs directly.

Step 2 adds LLM-backed worker, risk, and decision agents. They implement the same `Agent` contract as the deterministic mock agents and return the same `AgentResult` structure. The deterministic evidence verifier remains authoritative.

Step 3 keeps the same agent contracts while research workers gain access to `web_search` and `fetch_page` through the existing `ToolExecutor`. Decision output now references a stable `candidate_id` rather than a candidate name.

## Common interface

```python
async def execute(
    task: TaskNode,
    state: ResearchState,
    context: AgentContext,
) -> AgentResult: ...
```

`AgentContext` injects:

- run ID
- tool executor
- memory store
- trajectory recorder

`AgentResult` returns:

- findings
- evidence
- product candidates
- risk flags
- recommendations
- proposed tasks
- tool calls
- confidence
- status
- structured error
- LLM metrics

## LLM-backed agents

`LLMMarketResearchAgent`, `LLMProductResearchAgent`, `LLMReviewResearchAgent`, `LLMCompetitorResearchAgent`, `LLMRiskAnalysisAgent`, and `LLMDecisionAgent` render a versioned prompt, call the normalized LLM client, optionally request tools through the existing executor, and parse the final JSON into a role-specific output model before producing `AgentResult`.

`LLMMarketResearchAgent` uses `get_market_signal`. Product research uses the product catalog, detail, cost, and margin tools. Review mining uses `search_reviews`. Competitor research uses `web_search`. Risk analysis uses cost and margin tools. Decision produces a recommendation from validated shared state.

## ResearchManagerAgent

**Responsibility**

- Owns the research objective.
- Creates and updates the task DAG.
- Coordinates execution priorities.

**Allowed inputs**

- Research goal
- Task DAG
- Shared state

**Expected outputs**

- Proposed tasks
- State updates

**Eventual tools**

- Planner adapters
- Memory retrieval

**Must not**

- Bypass the DAG
- Mutate state directly
- Hide failures

**Failure behavior**

- Return a structured `AgentError`.

## MarketResearchAgent

**Responsibility**

- Analyze demand, trend, and seasonality signals.

**Allowed inputs**

- Market
- Category
- Constraints

**Expected outputs**

- Market findings
- Evidence

**Eventual tools**

- `get_market_signal`
- `web_search`

**Must not**

- Invent market data without evidence.

**Failure behavior**

- Return a structured error or retryable tool result.

## ProductResearchAgent

**Responsibility**

- Discover and normalize product candidates.
- Aggregate unit economics.

**Allowed inputs**

- Category
- Market
- Existing state

**Expected outputs**

- Product candidates
- Findings
- Evidence

**Eventual tools**

- `search_products`
- `get_product_details`
- `estimate_cost`
- `estimate_margin`

**Must not**

- Assume a specific marketplace provider.

**Failure behavior**

- Return no candidate and a structured error.

## ReviewMiningAgent

**Responsibility**

- Extract recurring customer pain points and unmet needs.

**Allowed inputs**

- Product candidate or category

**Expected outputs**

- Findings
- Evidence

**Eventual tools**

- `search_reviews`
- `web_search`

**Must not**

- Treat anecdote as statistically representative without qualification.

**Failure behavior**

- Return a structured error or insufficient-evidence result.

## CompetitorResearchAgent

**Responsibility**

- Assess competitive intensity and differentiation opportunities.

**Allowed inputs**

- Market
- Category
- Candidate

**Expected outputs**

- Findings
- Evidence

**Eventual tools**

- `web_search`
- `fetch_page`
- `search_products`

**Must not**

- Claim market share without a source.

**Failure behavior**

- Return a structured error.

## RiskAnalysisAgent

**Responsibility**

- Identify execution, competition, regulatory, and operational risks.

**Allowed inputs**

- Candidate
- Findings
- Evidence

**Expected outputs**

- Risk flags
- Findings

**Eventual tools**

- `estimate_margin`
- `estimate_cost`

**Must not**

- Omit risk from a recommendation.

**Failure behavior**

- Return a structured error.

## DecisionAgent

**Responsibility**

- Produce an evidence-grounded recommendation.

**Allowed inputs**

- Candidates
- Findings
- Evidence
- Risk flags
- Constraints

**Expected outputs**

- Recommendation with decision, score, confidence, and rationale

**Eventual tools**

- None in Step 1

**Must not**

- Produce a recommendation without evidence, findings, and risks.

**Failure behavior**

- Return `INSUFFICIENT_EVIDENCE`.

## EvidenceVerifierAgent

**Responsibility**

- Verify that every finding references valid evidence.

**Allowed inputs**

- Shared state

**Expected outputs**

- Verification finding

**Eventual tools**

- `retrieve_memory`

**Must not**

- Approve missing evidence references.

**Failure behavior**

- Return `MISSING_EVIDENCE`.
