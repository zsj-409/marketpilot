// Runs list page with kind/status filters and search.

import { getJSON } from "../api.js";
import {
  esc, fmtFixed, fmtNum, fmtPct, fmtTime, shortId, statusPill, decisionPill,
} from "../format.js";

const state = { kind: "", status: "", query: "" };

export async function render(container) {
  container.innerHTML = `<div class="loading">加载运行列表…</div>`;
  let runs;
  try {
    runs = await getJSON("/api/runs");
  } catch (error) {
    container.innerHTML = `<div class="error-box">加载失败：${esc(error.message)}</div>`;
    return;
  }

  container.innerHTML = `
    <div class="page-head">
      <h1>研究运行</h1>
      <p class="sub">runs/ 目录下的多智能体研究运行与闭环选品运行 · 点击任意一行查看轨迹、DAG 与证据链</p>
    </div>
    <div class="filters">
      <select id="f-kind">
        <option value="">全部类型</option>
        <option value="research">研究运行</option>
        <option value="selection">闭环选品</option>
      </select>
      <select id="f-status">
        <option value="">全部状态</option>
        <option value="COMPLETED">COMPLETED</option>
        <option value="FAILED">FAILED</option>
        <option value="FINISH">FINISH</option>
        <option value="其他">其他</option>
      </select>
      <input type="text" id="f-query" placeholder="搜索 run id / 类目 / 市场…">
      <span class="chip" id="f-count"></span>
    </div>
    <div class="card" id="runs-table"></div>
  `;

  const kindSelect = container.querySelector("#f-kind");
  const statusSelect = container.querySelector("#f-status");
  const queryInput = container.querySelector("#f-query");
  kindSelect.addEventListener("change", () => { state.kind = kindSelect.value; draw(); });
  statusSelect.addEventListener("change", () => { state.status = statusSelect.value; draw(); });
  queryInput.addEventListener("input", () => { state.query = queryInput.value.trim().toLowerCase(); draw(); });

  draw();

  function draw() {
    const filtered = runs.filter((run) => {
      if (state.kind && run.kind !== state.kind) return false;
      if (state.status) {
        if (state.status === "其他") {
          if (["COMPLETED", "FAILED", "FINISH"].includes(run.status)) return false;
        } else if (run.status !== state.status) return false;
      }
      if (state.query) {
        const haystack = `${run.run_id} ${run.category} ${run.market} ${run.objective} ${run.llm_model}`.toLowerCase();
        if (!haystack.includes(state.query)) return false;
      }
      return true;
    });
    container.querySelector("#f-count").textContent = `${filtered.length} / ${runs.length}`;
    renderTable(container.querySelector("#runs-table"), filtered);
  }
}

function renderTable(node, runs) {
  if (!runs.length) {
    node.innerHTML = `<div class="empty">没有匹配的运行 —— 试试清除筛选，或到 <a href="#/workbench">工作台</a> 发起一次研究</div>`;
    return;
  }
  node.innerHTML = `<div class="table-wrap"><table class="data">
    <thead><tr>
      <th>Run ID</th><th>类型</th><th>类目 / 市场</th><th>目标 / 说明</th>
      <th>状态</th><th>决策</th><th>评测</th>
      <th class="num">任务成功率</th><th class="num">证据覆盖</th>
      <th class="num">LLM</th><th class="num">Tokens</th><th class="num">工具</th>
      <th>开始时间</th><th class="num">耗时</th>
    </tr></thead>
    <tbody>${runs.map((run) => `
      <tr class="clickable" data-run="${esc(run.run_id)}">
        <td class="mono">${esc(shortId(run.run_id))}</td>
        <td>${run.kind === "selection"
          ? '<span class="pill pill-teal">选品</span>'
          : '<span class="pill pill-accent">研究</span>'}</td>
        <td>${esc(run.kind === "selection" ? `候选 ${fmtNum(run.initial_candidates)}` : `${esc(run.category)} / ${esc(run.market)}`)}</td>
        <td class="dim" style="max-width:230px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">
          ${esc(run.kind === "selection" ? `闭环选品 · ${run.research_rounds ?? "?"} 轮` : run.objective)}</td>
        <td>${statusPill(run.status)}</td>
        <td>${decisionPill(run.decision)}</td>
        <td>${run.evaluation_passed === null ? '<span class="dim">—</span>'
          : run.evaluation_passed ? '<span class="pill pill-ok">PASS</span>' : '<span class="pill pill-bad">FAIL</span>'}</td>
        <td class="num">${run.task_success_rate === null || run.task_success_rate === undefined ? "—" : fmtPct(run.task_success_rate)}</td>
        <td class="num">${run.evidence_coverage === null || run.evidence_coverage === undefined ? "—" : fmtPct(run.evidence_coverage)}</td>
        <td class="num">${fmtNum(run.llm_calls)}</td>
        <td class="num">${fmtNum(run.llm_total_tokens)}</td>
        <td class="num">${fmtNum(run.tool_calls)}</td>
        <td class="dim">${esc(fmtTime(run.started_at))}</td>
        <td class="num">${fmtFixed((run.duration_ms || 0) / 1000, 2)}s</td>
      </tr>`).join("")}
    </tbody></table></div>`;

  node.querySelectorAll("[data-run]").forEach((row) => {
    row.addEventListener("click", () => { location.hash = `#/runs/${row.dataset.run}`; });
  });
}
