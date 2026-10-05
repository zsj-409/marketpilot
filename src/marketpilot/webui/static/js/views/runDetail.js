// Run detail page: DAG, evidence chain, recommendation, evaluation, trajectory.

import { getJSON } from "../api.js";
import { dagChart, radarChart } from "../charts.js";
import {
  DECISION_TONES, EVENT_CATEGORIES, EVENT_TONES, TASK_TYPE_LABELS,
  decisionPill, esc, eventCategory, fmtFixed, fmtMs, fmtNum, fmtPct, fmtTime,
  fmtTimeShort, pill, shortId, statusPill,
} from "../format.js";

const SCORE_AXES = [
  { key: "demand", label: "需求" },
  { key: "trend", label: "趋势" },
  { key: "estimated_margin", label: "毛利" },
  { key: "competition", label: "竞争" },
  { key: "customer_pain_opportunity", label: "痛点机会" },
  { key: "operational_complexity", label: "运营复杂度" },
  { key: "regulatory_risk", label: "合规风险" },
  { key: "overall_score", label: "综合分" },
];

export async function render(container, params) {
  container.innerHTML = `<div class="loading">加载运行详情…</div>`;
  let detail;
  try {
    detail = await getJSON(`/api/runs/${encodeURIComponent(params.id)}`);
  } catch (error) {
    container.innerHTML = `
      <div class="error-box">加载失败：${esc(error.message)}</div>
      <a class="btn ghost" href="#/runs">← 返回运行列表</a>`;
    return;
  }
  if (detail.kind === "selection") {
    renderSelection(container, detail);
  } else {
    renderResearch(container, detail);
  }
}

/* ------------------------------------------------------------------ */
/* Research run                                                        */
/* ------------------------------------------------------------------ */

function renderResearch(container, detail) {
  const summary = detail.summary || {};
  const metrics = detail.metrics || {};
  const tasks = detail.tasks || [];
  const recommendation = (detail.recommendations || [])[0] || null;
  const selectedTask = { id: null };

  container.innerHTML = `
    <div class="page-head">
      <div class="row">
        <h1>研究运行 <span class="mono" style="font-size:15px;color:var(--text-3)">${esc(shortId(detail.run_id))}</span></h1>
        ${statusPill(detail.status)}
        ${decisionPill(summary.decision || "NONE")}
        ${detail.evaluation ? pill(detail.evaluation.passed ? "评测 PASS" : "评测 FAIL", detail.evaluation.passed ? "ok" : "bad") : ""}
      </div>
      <p class="sub">${esc(detail.goal.objective)}</p>
      <div class="chip-row" style="margin-top:6px">
        <span class="chip">市场 ${esc(detail.goal.market)}</span>
        <span class="chip">类目 ${esc(detail.goal.category)}</span>
        <span class="chip">模式 ${esc(summary.mode || "—")}${summary.research_mode ? ` / ${esc(summary.research_mode)}` : ""}</span>
        <span class="chip">模型 ${esc(summary.llm_provider || "—")}:${esc(summary.llm_model || "—")}</span>
        <span class="chip">约束 margin≥${esc(fmtPct(detail.goal.constraints.minimum_margin))} risk≤${esc(fmtPct(detail.goal.constraints.maximum_risk))}</span>
        <span class="chip">预算 工具≤${esc(fmtNum(detail.goal.budget.max_tool_calls))} · ${esc(fmtNum(detail.goal.budget.max_wall_clock_seconds))}s</span>
      </div>
    </div>

    <div class="grid cols-6">
      ${stat("任务", `${metrics.tasks_successful ?? 0}/${metrics.tasks_total ?? 0}`, "成功/总数")}
      ${stat("证据", fmtNum((detail.evidence || []).length), "EvidenceItem")}
      ${stat("发现", fmtNum((detail.findings || []).length), "Finding")}
      ${stat("风险", fmtNum((detail.risk_flags || []).length), "RiskFlag")}
      ${stat("工具调用", fmtNum(metrics.tool_calls ?? 0), `失败 ${fmtNum(metrics.tool_failures ?? 0)}`)}
      ${stat("LLM 调用", fmtNum(metrics.llm_calls ?? 0), `tokens ${fmtNum(metrics.llm_total_tokens ?? 0)} · $${fmtFixed(metrics.llm_estimated_cost ?? 0, 4)}`)}
    </div>

    <h2 class="section">任务 DAG</h2>
    <div class="card">
      <p class="card-hint">点击节点可过滤时间线中该任务的事件。颜色：绿=成功，蓝=运行中，黄=就绪，灰=待处理。</p>
      <div class="dag-wrap" id="dag"></div>
      <div class="chip-row" style="margin-top:8px">
        ${tasks.map((task) => `<span class="chip clickable" data-task-chip="${esc(task.task_id)}">
          ${esc(TASK_TYPE_LABELS[task.task_type] || task.task_type)} · ${esc(task.status)}</span>`).join("")}
      </div>
    </div>

    <div class="grid cols-2" id="rec-and-eval">
      <div class="card" id="recommendation-card"></div>
      <div class="card" id="evaluation-card"></div>
    </div>

    <h2 class="section">发现与证据链</h2>
    <div class="grid cols-2">
      <div class="card">
        <h3>发现 Findings（${(detail.findings || []).length}）</h3>
        <div class="table-wrap"><table class="data">
          <thead><tr><th>主张</th><th class="num">置信度</th><th>证据</th></tr></thead>
          <tbody>${(detail.findings || []).map((finding) => `
            <tr>
              <td>${esc(finding.claim)}</td>
              <td class="num">${fmtPct(finding.confidence, 0)}</td>
              <td class="mono dim">${(finding.evidence_ids || []).map((id) => esc(shortId(id))).join(", ")}</td>
            </tr>`).join("")}
          </tbody></table></div>
      </div>
      <div class="card">
        <h3>风险标记 Risk Flags（${(detail.risk_flags || []).length}）</h3>
        ${(detail.risk_flags || []).length ? (detail.risk_flags || []).map((risk) => `
          <div class="score-line">
            <div class="name">${esc(risk.label)}</div>
            <div class="track"><div class="fill" style="width:${(risk.severity ?? 0) * 100}%;background:var(--warn)"></div></div>
            <div class="val">${fmtPct(risk.severity, 0)}</div>
          </div>
          <p class="excerpt" style="margin:0 0 8px">${esc(risk.rationale)}</p>`).join("")
        : `<div class="empty">无风险标记</div>`}
      </div>
    </div>

    <div class="card">
      <h3>证据 Evidence（${(detail.evidence || []).length}）</h3>
      <div class="table-wrap"><table class="data">
        <thead><tr><th>ID</th><th>类型</th><th>来源</th><th>摘录</th><th class="num">置信度</th><th>关联发现</th></tr></thead>
        <tbody>${(detail.evidence || []).map((item) => `
          <tr>
            <td class="mono">${esc(shortId(item.evidence_id))}</td>
            <td><span class="pill pill-muted">${esc(item.source_type)}</span> ${pill(item.kind, "muted")}</td>
            <td class="mono dim" style="max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${esc(item.source_uri)}">${esc(item.source_uri)}</td>
            <td class="excerpt" style="max-width:320px">${esc(item.excerpt)}</td>
            <td class="num">${fmtPct(item.confidence, 0)}</td>
            <td class="mono dim">${evidenceFindings(detail, item.evidence_id)}</td>
          </tr>`).join("")}
        </tbody></table></div>
    </div>

    <div class="grid cols-2">
      <div class="card">
        <h3>来源 Sources（${(detail.sources || []).length}）</h3>
        ${(detail.sources || []).length ? `<div class="table-wrap"><table class="data">
          <thead><tr><th>域名</th><th>标题</th><th>URL</th></tr></thead>
          <tbody>${(detail.sources || []).map((source) => `
            <tr>
              <td class="mono dim">${esc(source.domain)}</td>
              <td>${esc(source.title || "—")}</td>
              <td class="mono dim" style="max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(source.url)}</td>
            </tr>`).join("")}
          </tbody></table></div>
          <p class="card-hint" style="margin:8px 0 0">检索 ${(detail.retrievals || []).length} 次 · 快照 ${(detail.snapshots || []).length} 份</p>`
        : `<div class="empty">本次运行未记录来源（无 research-mode 产物）</div>`}
      </div>
      <div class="card">
        <h3>评测指标（SystemEvaluator）</h3>
        ${evaluationMetrics(detail)}
      </div>
    </div>

    <h2 class="section">轨迹时间线（${(detail.trajectory || []).length} 事件）</h2>
    <div class="card" id="timeline-card">
      <div class="tl-toolbar">
        <span class="chip on" data-cat="">全部</span>
        ${EVENT_CATEGORIES.map((cat) => `<span class="chip clickable" data-cat="${cat.key}">${esc(cat.label)}</span>`).join("")}
        <select id="tl-actor" style="width:auto;min-width:130px"></select>
        <input type="text" id="tl-search" placeholder="搜索事件…" style="min-width:170px">
      </div>
      <div class="timeline" id="timeline"></div>
      <div style="margin-top:10px;text-align:center">
        <button class="btn subtle sm" id="tl-more" style="display:none">显示更多</button>
      </div>
    </div>

    <p class="footer-note">产物目录：runs/${esc(detail.run_id)} · trajectory.jsonl · final_state.json · summary.json</p>
  `;

  const timelineState = { category: "", query: "", shown: 100 };

  function syncTaskChips() {
    container.querySelectorAll("[data-task-chip]").forEach((node) => {
      node.classList.toggle("on", node.dataset.taskChip === selectedTask.id);
    });
  }

  renderDag();
  renderRecommendationCard();
  renderEvaluationCard();
  setupTimeline();

  container.querySelectorAll("[data-task-chip]").forEach((chip) => {
    chip.addEventListener("click", () => {
      selectedTask.id = selectedTask.id === chip.dataset.taskChip ? null : chip.dataset.taskChip;
      syncTaskChips();
      renderDag();
      drawTimeline();
      container.querySelector("#timeline-card").scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  function renderDag() {
    const holder = container.querySelector("#dag");
    holder.innerHTML = "";
    holder.appendChild(dagChart(tasks, {
      selectedId: selectedTask.id,
      onSelect: (taskId) => {
        selectedTask.id = selectedTask.id === taskId ? null : taskId;
        syncTaskChips();
        renderDag();
        drawTimeline();
        container.querySelector("#timeline-card").scrollIntoView({ behavior: "smooth", block: "start" });
      },
    }));
    holder.querySelectorAll(".dag-node").forEach((node, index) => {
      if (tasks[index] && selectedTask.id === String(tasks[index].task_id)) {
        node.classList.add("selected");
      }
    });
  }

  function renderRecommendationCard() {
    const card = container.querySelector("#recommendation-card");
    if (!recommendation) {
      card.innerHTML = `<h3>最终推荐</h3><div class="empty">本次运行未产生推荐</div>`;
      return;
    }
    const candidate = recommendation.candidate || {};
    const scores = recommendation.scores || {};
    card.innerHTML = `
      <h3>最终推荐</h3>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <strong style="font-size:15px">${esc(candidate.name || "—")}</strong>
        ${decisionPill(recommendation.decision)}
        <span class="chip">置信度 ${fmtPct(recommendation.confidence, 0)}</span>
      </div>
      <p class="excerpt" style="margin:8px 0 2px">${esc(candidate.brand || "")} · ${esc(candidate.category || "")} / ${esc(candidate.market || "")} · provider: ${esc(candidate.provider || "")}</p>
      <p style="font-size:13px;color:var(--text-2);border-left:3px solid var(--accent);padding-left:10px;margin:10px 0">${esc(recommendation.rationale)}</p>
      <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap">
        <div style="flex:0 0 260px" id="radar"></div>
        <div style="flex:1;min-width:200px">
          ${SCORE_AXES.map((axis) => `
            <div class="score-line">
              <div class="name">${esc(axis.label)}</div>
              <div class="track"><div class="fill" style="width:${(scores[axis.key] ?? 0) * 100}%"></div></div>
              <div class="val">${fmtFixed(scores[axis.key], 2)}</div>
            </div>`).join("")}
        </div>
      </div>
      <div class="chip-row" style="margin-top:10px">
        <span class="chip">支撑发现 ${(recommendation.findings || []).length}</span>
        <span class="chip">支撑证据 ${(recommendation.supporting_evidence || []).length}</span>
        <span class="chip">风险标记 ${(recommendation.risk_flags || []).length}</span>
      </div>
    `;
    card.querySelector("#radar").appendChild(radarChart(SCORE_AXES,
      SCORE_AXES.map((axis) => ({ key: axis.key, value: scores[axis.key] ?? 0 })), { size: 250 }));
  }

  function renderEvaluationCard() {
    const card = container.querySelector("#evaluation-card");
    if (!detail.evaluation) {
      card.innerHTML = `<h3>评测</h3><div class="empty">轨迹中无评测事件</div>`;
      return;
    }
    card.innerHTML = `
      <h3>评测检查（${detail.evaluation.passed ? "全部通过" : "存在失败"}）</h3>
      <div class="check-list">
        ${detail.evaluation.checks.map((check) => `
          <div class="check">
            <span class="${check.passed ? "ok" : "fail"}">${check.passed ? "✓" : "✗"}</span>
            <span>${esc(check.name)}<br><span class="d">${esc(check.details || "")}</span></span>
          </div>`).join("")}
      </div>
    `;
  }

  function evaluationMetrics(detailArg) {
    const evaluation = detailArg.evaluation;
    if (!evaluation || !evaluation.metrics || !Object.keys(evaluation.metrics).length) {
      return `<div class="empty">无评测指标</div>`;
    }
    const rows = [
      ["task_success_rate", "任务成功率"],
      ["evidence_coverage", "证据覆盖率"],
      ["unsupported_claim_rate", "无支撑主张率"],
      ["tool_success_rate", "工具成功率"],
      ["retry_rate", "重试率"],
      ["recommendation_confidence", "推荐置信度"],
      ["execution_latency_seconds", "执行延迟 (s)"],
      ["cost_per_run", "成本 ($)"],
    ];
    return rows.map(([key, label]) => `
      <div class="score-line">
        <div class="name">${esc(label)}</div>
        <div class="track"><div class="fill" style="width:${clamp01(evaluation.metrics[key]) * 100}%"></div></div>
        <div class="val">${fmtFixed(evaluation.metrics[key], 3)}</div>
      </div>`).join("");
  }

  function drawTimeline() {
    const timeline = container.querySelector("#timeline");
    const actorSelect = container.querySelector("#tl-actor");
    const events = (detail.trajectory || []).filter((event) => {
      if (timelineState.category && eventCategory(event.event_type) !== timelineState.category) return false;
      if (actorSelect.value && event.actor !== actorSelect.value) return false;
      if (selectedTask.id && event.task_id && event.task_id !== selectedTask.id) return false;
      if (selectedTask.id && !event.task_id) return false;
      if (timelineState.query) {
        const haystack = `${event.event_type} ${event.actor} ${event.input_summary || ""} ${event.output_summary || ""}`.toLowerCase();
        if (!haystack.includes(timelineState.query)) return false;
      }
      return true;
    });
    const slice = events.slice(0, timelineState.shown);
    timeline.innerHTML = slice.length ? slice.map((event) => timelineRow(event)).join("")
      : `<div class="empty">没有匹配的事件</div>`;
    const more = container.querySelector("#tl-more");
    more.style.display = events.length > timelineState.shown ? "inline-flex" : "none";
    more.textContent = `显示更多（${events.length - timelineState.shown} 条未显示）`;
    timeline.querySelectorAll(".tl-group").forEach((group) => {
      const item = group.querySelector(".tl-item");
      const detailBox = group.querySelector(".tl-detail");
      if (!item || !detailBox) return;
      item.addEventListener("click", () => {
        detailBox.style.display = detailBox.style.display === "none" ? "block" : "none";
      });
    });
  }

  function setupTimeline() {
    const actors = [...new Set((detail.trajectory || []).map((event) => event.actor))].sort();
    const actorSelect = container.querySelector("#tl-actor");
    actorSelect.innerHTML = `<option value="">全部 actor</option>${actors.map((actor) => `<option>${esc(actor)}</option>`).join("")}`;

    container.querySelectorAll("[data-cat]").forEach((chip) => {
      chip.addEventListener("click", () => {
        container.querySelectorAll("[data-cat]").forEach((node) => node.classList.remove("on"));
        chip.classList.add("on");
        timelineState.category = chip.dataset.cat;
        timelineState.shown = 100;
        drawTimeline();
      });
    });
    actorSelect.addEventListener("change", () => { timelineState.shown = 100; drawTimeline(); });
    container.querySelector("#tl-search").addEventListener("input", (event) => {
      timelineState.query = event.target.value.trim().toLowerCase();
      timelineState.shown = 100;
      drawTimeline();
    });
    container.querySelector("#tl-more").addEventListener("click", () => {
      timelineState.shown += 150;
      drawTimeline();
    });

    drawTimeline();
  }
}

function timelineRow(event) {
  const cat = eventCategory(event.event_type);
  const hasDetail = event.output_summary || event.input_summary || event.error
    || (event.metadata && Object.keys(event.metadata).length);
  const summary = truncate(event.output_summary || event.input_summary || "", 120);
  return `
    <div class="tl-group">
    <div class="tl-item" ${hasDetail ? 'style="cursor:pointer"' : ""}>
      <span class="tl-seq">${event.sequence_number}</span>
      <span class="tl-time">${esc(fmtTimeShort(event.timestamp))}</span>
      <span class="tl-type">${pill(event.event_type, EVENT_TONES[cat] || "muted")}</span>
      <span class="tl-actor">${esc(event.actor)}</span>
      <span class="tl-summary">${summary ? esc(summary) : '<span class="dim">—</span>'}
        ${event.duration_ms ? `<span class="dim">· ${esc(fmtMs(event.duration_ms))}</span>` : ""}
        ${event.error ? `<span class="tl-err">✗ ${esc(truncate(event.error.message || "", 80))}</span>` : ""}
      </span>
    </div>
    ${hasDetail ? `<div class="tl-detail" style="display:none;padding:2px 8px 10px 190px;font-size:11.5px;color:var(--text-2)">
      ${event.input_summary ? `<div><strong>in:</strong> ${esc(truncate(event.input_summary, 400))}</div>` : ""}
      ${event.output_summary ? `<div><strong>out:</strong> ${esc(truncate(event.output_summary, 600))}</div>` : ""}
      ${event.error ? `<div class="tl-err"><strong>error:</strong> ${esc(event.error.code || "")} ${esc(event.error.message || "")}</div>` : ""}
      ${event.metadata && Object.keys(event.metadata).length ? `<div><strong>meta:</strong> ${esc(JSON.stringify(event.metadata))}</div>` : ""}
    </div>` : ""}
    </div>`;
}

/* ------------------------------------------------------------------ */
/* Selection run                                                       */
/* ------------------------------------------------------------------ */

function renderSelection(container, detail) {
  const result = detail.result || {};
  container.innerHTML = `
    <div class="page-head">
      <div class="row">
        <h1>闭环选品 <span class="mono" style="font-size:15px;color:var(--text-3)">${esc(shortId(detail.run_id))}</span></h1>
        ${statusPill(detail.termination)}
        ${decisionPill(result.final_verdict || "NONE")}
      </div>
      <p class="sub">DecisionCritic + TerminationController 驱动的闭环选品：评估 → 批评 → 定向补研 → 终止判定</p>
    </div>

    <div class="grid cols-4">
      ${stat("研究轮次", fmtNum(result.research_rounds), "research_rounds")}
      ${stat("初始候选", fmtNum(result.initial_candidates), "candidates")}
      ${stat("定向补研", fmtNum(result.followup_investigations), "follow-up investigations")}
      ${stat("未解决缺口", fmtNum(result.unresolved_gaps), "unresolved gaps")}
    </div>

    <h2 class="section">最终候选</h2>
    <div class="card">
      ${result.final_candidate_id
        ? `<p>候选 ID：<span class="mono">${esc(shortId(result.final_candidate_id))}</span> · 最终判定 ${decisionPill(result.final_verdict)}</p>
           ${candidateCard(detail, result.final_candidate_id)}`
        : `<div class="empty">未选出最终候选</div>`}
    </div>

    <h2 class="section">候选与证据面</h2>
    <div class="grid cols-2">
      ${(detail.candidates || []).map((candidate) => candidateCard(detail, candidate.candidate_id, candidate)).join("")}
    </div>

    <h2 class="section">轮次过程</h2>
    ${(result.rounds || []).map((round) => `
      <div class="card">
        <h3>第 ${esc(round.round_number)} 轮 · 终止原因 ${pill(round.termination_reason, "info")}</h3>
        ${round.unresolved_gaps && round.unresolved_gaps.length ? `
          <p class="card-hint">未解决缺口</p>
          <div class="table-wrap"><table class="data">
            <thead><tr><th>候选</th><th>证据面</th><th>原因</th><th class="num">优先级</th></tr></thead>
            <tbody>${round.unresolved_gaps.map((gap) => `
              <tr><td class="mono">${esc(shortId(gap.candidate_id))}</td><td>${pill(gap.facet, "accent")}</td>
              <td>${esc(gap.reason)}</td><td class="num">${esc(gap.priority)}</td></tr>`).join("")}
            </tbody></table></div>` : `<p class="card-hint">本轮无未解决缺口</p>`}
        ${round.conflicts && round.conflicts.length ? `
          <p class="card-hint">证据冲突</p>
          ${round.conflicts.map((conflict) => `<p class="excerpt">✗ ${esc(conflict.explanation || conflict.facet || "")}</p>`).join("")}` : ""}
        ${round.completed_followup_tasks && round.completed_followup_tasks.length ? `
          <p class="card-hint">完成的补研任务：${round.completed_followup_tasks.map((task) => `<span class="chip">${esc(task)}</span>`).join(" ")}</p>` : ""}
      </div>`).join("")}

    <p class="footer-note">产物目录：runs/${esc(detail.run_id)} · recommendation.json · candidates.json</p>
  `;
}

function candidateCard(detail, candidateId, candidate = null) {
  const candidates = detail.candidates || [];
  const item = candidate || candidates.find((c) => c.candidate_id === candidateId) || {};
  const facets = Object.keys(item).filter((key) => Array.isArray(item[key]));
  return `
    <div class="card" style="margin-bottom:0">
      <h3>${esc(item.title || shortId(candidateId))} ${item.price ? `<span class="chip">$${esc(item.price)}</span>` : ""} ${item.battery ? '<span class="chip">含电池</span>' : ""}</h3>
      ${facets.length ? facets.map((facet) => `
        <div class="score-line">
          <div class="name">${esc(facet)}</div>
          <div style="grid-column:span 2;font-size:12px;color:var(--text-2)">${item[facet].map((obs) => esc(obs)).join(" · ")}</div>
        </div>`).join("")
      : `<p class="excerpt">无证据面记录</p>`}
    </div>`;
}

/* ------------------------------------------------------------------ */
/* shared helpers                                                      */
/* ------------------------------------------------------------------ */

function stat(label, value, foot) {
  return `<div class="stat"><div class="label">${esc(label)}</div>
    <div class="value" style="font-size:18px">${esc(value)}</div>
    <div class="foot">${esc(foot)}</div></div>`;
}

function truncate(text, length) {
  const value = String(text ?? "");
  return value.length > length ? `${value.slice(0, length)}…` : value;
}

function evidenceFindings(detail, evidenceId) {
  const ids = (detail.findings || [])
    .filter((finding) => (finding.evidence_ids || []).includes(evidenceId))
    .map((finding) => shortId(finding.finding_id));
  return ids.join(", ") || "—";
}

function clamp01(value) {
  const num = Number(value);
  if (!Number.isFinite(num)) return 0;
  return Math.max(0, Math.min(1, num));
}
