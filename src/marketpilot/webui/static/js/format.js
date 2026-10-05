// Formatting helpers shared by all views.

export const esc = (value) =>
  String(value ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));

export const fmtTime = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
};

export const fmtTimeShort = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return String(iso);
  const p = (n) => String(n).padStart(2, "0");
  return `${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`;
};

export const fmtMs = (ms) => {
  if (!ms && ms !== 0) return "—";
  if (ms >= 1000) return `${(ms / 1000).toFixed(2)} s`;
  return `${ms} ms`;
};

export const fmtNum = (n) => (n === null || n === undefined || n === "" ? "—" : Number(n).toLocaleString("zh-CN"));

export const fmtPct = (x, digits = 1) =>
  x === null || x === undefined ? "—" : `${(x * 100).toFixed(digits)}%`;

export const fmtFixed = (x, digits = 3) =>
  x === null || x === undefined ? "—" : Number(x).toFixed(digits);

export const shortId = (id) => String(id ?? "").slice(0, 8);

export const DECISION_TONES = {
  STRONG_GO: "ok", GO: "ok", WATCH: "warn", NO_GO: "bad",
  INSUFFICIENT_EVIDENCE: "muted", NONE: "muted",
};

export const STATUS_TONES = {
  COMPLETED: "ok", SUCCEEDED: "ok", PASSED: "ok", FINISH: "ok", ACCEPT: "ok",
  FAILED: "bad", STOP_NO_VIABLE_PATH: "bad", STOP_BUDGET_EXHAUSTED: "warn",
  RUNNING: "info", QUEUED: "warn",
  WATCH: "warn", CONTINUE_TARGETED_RESEARCH: "info",
  REPLAN_CANDIDATES: "warn", INVESTIGATE_CONFLICT: "warn",
  PENDING: "muted", READY: "info", BLOCKED: "muted", CANCELLED: "muted",
};

export const pill = (text, tone = "muted") =>
  `<span class="pill pill-${esc(tone)}">${esc(text)}</span>`;

export const statusPill = (status) =>
  pill(status ?? "—", STATUS_TONES[status] ?? "muted");

export const decisionPill = (decision) =>
  pill(decision ?? "NONE", DECISION_TONES[decision] ?? "muted");

export const TASK_TYPE_LABELS = {
  MARKET_RESEARCH: "市场调研",
  PRODUCT_DISCOVERY: "商品发现",
  REVIEW_RESEARCH: "评论挖掘",
  COMPETITOR_RESEARCH: "竞品调研",
  CANDIDATE_AGGREGATION: "候选聚合",
  RISK_ANALYSIS: "风险分析",
  DECISION: "决策",
  EVIDENCE_VERIFICATION: "证据校验",
};

export const EVENT_CATEGORIES = [
  { key: "run", label: "运行", types: ["RUN_STARTED", "RUN_COMPLETED", "RUN_FAILED"] },
  { key: "task", label: "任务", types: ["TASK_CREATED", "TASK_READY", "TASK_STARTED", "TASK_COMPLETED", "TASK_FAILED", "TASK_RETRIED"] },
  { key: "agent", label: "智能体", types: ["AGENT_STARTED", "AGENT_COMPLETED", "AGENT_FAILED"] },
  { key: "llm", label: "LLM", types: ["PROMPT_RENDERED", "LLM_REQUESTED", "LLM_COMPLETED", "LLM_FAILED", "LLM_RETRIED", "STRUCTURED_OUTPUT_VALIDATED", "STRUCTURED_OUTPUT_REJECTED"] },
  { key: "tool", label: "工具", types: ["TOOL_CALLED", "TOOL_SUCCEEDED", "TOOL_FAILED", "TOOL_REQUESTED_BY_MODEL"] },
  { key: "research", label: "检索", types: ["SEARCH_REQUESTED", "SEARCH_COMPLETED", "SEARCH_FAILED", "SOURCE_DISCOVERED", "SOURCE_RETRIEVAL_STARTED", "SOURCE_RETRIEVAL_COMPLETED", "SOURCE_RETRIEVAL_FAILED", "SOURCE_SNAPSHOT_CREATED", "SOURCE_DEDUPLICATED", "REPLAY_HIT", "REPLAY_MISS", "RESEARCH_BUDGET_UPDATED", "RESEARCH_BUDGET_EXHAUSTED"] },
  { key: "state", label: "状态", types: ["EVIDENCE_CREATED", "FINDING_CREATED", "RECOMMENDATION_CREATED", "STATE_UPDATED"] },
  { key: "memory", label: "记忆", types: ["MEMORY_READ", "MEMORY_WRITTEN"] },
  { key: "eval", label: "评测", types: ["EVALUATION_COMPLETED"] },
];

export function eventCategory(type) {
  for (const cat of EVENT_CATEGORIES) {
    if (cat.types.includes(type)) return cat.key;
  }
  return "other";
}

export const EVENT_TONES = {
  run: "accent", task: "info", agent: "teal", llm: "warn", tool: "muted",
  research: "info", state: "ok", memory: "muted", eval: "ok", other: "muted",
};
