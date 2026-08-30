# Tool Contracts

Tools are provider-neutral capabilities with structured input and output. Step 1 contains deterministic offline implementations only.

Step 2 keeps the same tool contract. LLM agents request tools as normalized `LLMToolCall` objects that are routed through the `ToolExecutor`; no provider SDK calls Python tool functions directly.

Step 3 adds two real read-only research tools behind the same boundary: `web_search` and `fetch_page`. They normalize search hits and retrieved pages, record source provenance, and participate in replay and budget enforcement.

## Common interface

```python
async def execute(
    arguments: ToolArguments,
    context: ToolContext,
) -> ToolOutput: ...
```

## Tool result statuses

```text
SUCCESS
RETRYABLE_ERROR
PERMANENT_ERROR
PERMISSION_DENIED
RATE_LIMITED
TIMEOUT
INVALID_INPUT
```

Failures are represented by `ToolError` or a structured `ToolResult`; they are not silently swallowed.

## Tool metadata

Every tool exposes:

- name
- description
- version
- input schema
- risk level
- timeout policy
- retry policy

## Deterministic mock tools

| Tool | Purpose | Required input | Risk |
| --- | --- | --- | --- |
| `web_search` | Search a mock web index | `query` | medium |
| `fetch_page` | Fetch a normalized mock page | `url` | medium |
| `search_products` | Search a mock product catalog | `category`, `market` | low |
| `get_product_details` | Return mock product details | `product_id` | low |
| `search_reviews` | Search mock review themes | `product_name` | low |
| `get_market_signal` | Return a deterministic market signal | `category`, `market` | low |
| `estimate_cost` | Estimate unit cost | `product_name` | low |
| `estimate_margin` | Estimate gross margin | `product_name` | low |
| `retrieve_memory` | Retrieve a memory record | `memory_key` | low |
| `store_memory` | Store a memory record | `memory_key`, `memory_value` | low |
| `web_search` (research) | Search a real provider and normalize results | `query` | medium |
| `fetch_page` (research) | Fetch and normalize one page into a snapshot | `url` | medium |

## Future real tools

Future implementations will preserve the same interface while adding:

- permission checks
- budget enforcement
- rate limiting
- caching
- source attribution
- content hashing
- normalization pipelines
