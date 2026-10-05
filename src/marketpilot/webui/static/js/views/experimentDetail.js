// Experiment detail page: manifest, metrics charts, difficulty/family breakdowns, failures, per-task results.

import { getJSON } from "../api.js";
import { donutChart } from "../charts.js";
import { esc, fmtFixed, fmtNum, fmtTime } from "../format.js";

const FAILURE_LABELS = {
  INSUFFICIENT_EVIDENCE: "证据不足",
  LOW_SOURCE_DIVERSITY: "来源多样性低",
  CONSTRAINT_VIOLATION: "约束违反",
  UNSUPPORTED_CLAIM: "无支撑主张",
  RISK_MISSED: "风险遗漏",
  POOR_RANKING: "排序差",
  BUDGET_EXHAUSTED: "预算耗尽",
  TOOL_FAILURE: "工具失败",
  STRUCTURED_OUTPUT_FAILURE: "结构化输出失败",
  REPLAY_MISS: "回放缺失",
};
const DIFFICULTY_LABELS = { easy: "简单", medium: "中等", hard: "困难" };

export async function render(container, params) {
  container.innerHTML = `<div class="loading">加载实验详情…</div>`;
  let detail;
  try {
    detail = await getJSON(`/api/experiments/${encodeURIComponent(params.id)}`);
  } catch (error) {
    container.innerHTML = `
      <div class="error-box">加载失败：${esc(error.message)}</div>
      <a class="btn ghost" href="#/experiments">← 返回实验列表</a>`;
    return;
  }

  const metrics = detail.metrics || {};
  const results = detail.results || [];
  const difficulties = difficultyRows(metrics.by_difficulty);
  const families = familyRows(metrics.by_family);
  const failureItems = Object.entries(metrics.failure_counts || {})
    .map(([key, value]) => ({ label: FAILURE_LABELS[key] || key, value, key }));

  container.innerHTML = `
    <div class="page-head">
      <div class="row">
        <h1>${esc(detail.name)}</h1>
        <span class="pill pill-accent">${esc(detail.strategy)}</span>
        ${detail.git_commit ? `<span class="chip mono">${esc(detail.git_commit.slice(0, 8))}</span>` : ""}
      </div>
      <p class="sub">${esc(detail.benchmark_suite)} · seed ${detail.seed} · ${esc(detail.provider)}/${esc(detail.model)} · ${esc(fmtTime(detail.started_at))}</p>
    </div>

    <div class="grid cols-6">
      ${stat("任务数", fmtNum(metrics.task_count), "per suite")}
      ${stat("成功率", fmtFixed(metrics.success_rate, 3), "selection ok", "ok")}
      ${stat("平均 regret", fmtFixed(metrics.mean_regret, 4), "越低越好", "accent")}
      ${stat("top-k recall", fmtFixed(metrics.mean_top_k_recall, 3), "越高越好", "accent")}
      ${stat("verifier 分", fmtFixed(metrics.mean_verifier_score, 3), "过程验证", "teal")}
      ${stat("排序相关性", fmtFixed(metrics.mean_ranking_correlation, 3), "Spearman", "teal")}
    </div>

    <div class="grid cols-2">
      <div class="card">
        <h3>按难度分解</h3>
        ${difficulties.length ? `<div class="table-wrap"><table class="data">
          <thead><tr><th>难度</th><th class="num">mean regret</th><th class="num">mean top-k recall</th></tr></thead>
          <tbody>${difficulties.map((row) => `
            <tr><td>${esc(DIFFICULTY_LABELS[row.difficulty] || row.difficulty)}</td>
            <td class="num">${fmtFixed(row.mean_regret, 4)}</td>
            <td class="num">${fmtFixed(row.mean_top_k_recall, 3)}</td></tr>`).join("")}
          </tbody></table></div>` : `<div class="empty">无分难度数据</div>`}
        <p class="card-hint" style="margin:8px 0 0">约束满足率 ${fmtFixed(metrics.constraint_satisfaction_rate, 3)} · 风险召回 ${fmtFixed(metrics.mean_risk_recall, 3)} · 平均工具调用 ${fmtFixed(metrics.mean_tool_calls, 2)}</p>
      </div>
      <div class="card">
        <h3>失败分类</h3>
        <div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap">
          <div id="donut"></div>
          <div style="flex:1;min-width:180px">
            ${failureItems.length ? failureItems.map((item, index) => `
              <div class="score-line">
                <div class="name">${esc(item.label)}</div>
                <div class="track"><div class="fill" style="width:${(item.value / failureTotal(failureItems)) * 100}%;background:var(--warn)"></div></div>
                <div class="val">${item.value}</div>
              </div>`).join("") : `<div class="empty" style="padding:18px">本次实验没有失败任务</div>`}
          </div>
        </div>
      </div>
    </div>

    <h2 class="section">按任务族分解</h2>
    <div class="card">
      ${families.length ? `<div class="table-wrap"><table class="data">
        <thead><tr><th>任务族</th><th class="num">任务数</th><th class="num">mean regret</th><th class="num">mean top-k recall</th></tr></thead>
        <tbody>${families.map((row) => `
          <tr><td>${esc(row.family)}</td><td class="num">${row.task_count}</td>
          <td class="num">${fmtFixed(row.mean_regret, 4)}</td>
          <td class="num">${fmtFixed(row.mean_top_k_recall, 3)}</td></tr>`).join("")}
        </tbody></table></div>` : `<div class="empty">无分任务族数据</div>`}
    </div>

    <h2 class="section">逐任务结果（${results.length}）</h2>
    <div class="card">
      <div class="filters">
        <select id="res-difficulty"><option value="">全部难度</option><option value="easy">简单</option><option value="medium">中等</option><option value="hard">困难</option></select>
        <select id="res-status"><option value="">全部状态</option><option value="COMPLETED">COMPLETED</option><option value="FAILED">FAILED</option></select>
        <input type="text" id="res-query" placeholder="搜索 task_key / 类目…">
        <span class="chip" id="res-count"></span>
      </div>
      <div class="table-wrap"><table class="data" id="res-table"></table></div>
    </div>

    <p class="footer-note">产物目录：benchmark_runs/${esc(detail.experiment_id)} · manifest.json · metrics.json · results.jsonl · failures.jsonl</p>
  `;

  const donutHolder = container.querySelector("#donut");
  donutHolder.appendChild(donutChart(failureItems, { centerLabel: "失败数" }));

  const filters = { difficulty: "", status: "", query: "" };
  const difficultySelect = container.querySelector("#res-difficulty");
  const statusSelect = container.querySelector("#res-status");
  const queryInput = container.querySelector("#res-query");
  difficultySelect.addEventListener("change", () => { filters.difficulty = difficultySelect.value; drawResults(); });
  statusSelect.addEventListener("change", () => { filters.status = statusSelect.value; drawResults(); });
  queryInput.addEventListener("input", () => { filters.query = queryInput.value.trim().toLowerCase(); drawResults(); });
  drawResults();

  function drawResults() {
    const rows = results.filter((result) => {
      if (filters.difficulty && result.difficulty !== filters.difficulty) return false;
      if (filters.status && result.status !== filters.status) return false;
      if (filters.query) {
        const haystack = `${result.task_key} ${result.family} ${result.category}`.toLowerCase();
        if (!haystack.includes(filters.query)) return false;
      }
      return true;
    });
    container.querySelector("#res-count").textContent = `${rows.length} / ${results.length}`;
    container.querySelector("#res-table").innerHTML = `
      <thead><tr>
        <th>任务</th><th>任务族</th><th>类目</th><th>难度</th><th>状态</th>
        <th class="num">regret</th><th class="num">top-k</th><th class="num">verifier</th>
        <th class="num">工具</th><th>失败原因</th>
      </tr></thead>
      <tbody>${rows.map((result) => `
        <tr>
          <td class="mono">${esc(result.task_key)}</td>
          <td class="dim">${esc(result.family)}</td>
          <td>${esc(result.category)}</td>
          <td>${esc(DIFFICULTY_LABELS[result.difficulty] || result.difficulty)}</td>
          <td>${result.status === "COMPLETED" ? '<span class="pill pill-ok">COMPLETED</span>' : `<span class="pill pill-bad">${esc(result.status)}</span>`}</td>
          <td class="num">${fmtFixed(result.regret, 4)}</td>
          <td class="num">${fmtFixed(result.top_k_recall, 2)}</td>
          <td class="num">${fmtFixed(result.verifier_score, 2)}</td>
          <td class="num">${result.tool_calls}</td>
          <td>${result.failure ? `<span class="pill pill-warn">${esc(FAILURE_LABELS[result.failure] || result.failure)}</span>` : '<span class="dim">—</span>'}</td>
        </tr>`).join("")}
      </tbody>`;
  }
}

function stat(label, value, foot, tone = "") {
  return `<div class="stat ${tone}"><div class="label">${esc(label)}</div>
    <div class="value" style="font-size:19px">${esc(value)}</div><div class="foot">${esc(foot)}</div></div>`;
}

function difficultyRows(byDifficulty) {
  return Object.entries(byDifficulty || {}).map(([difficulty, value]) => ({ difficulty, ...value }));
}

function familyRows(byFamily) {
  return Object.entries(byFamily || {}).map(([family, value]) => ({ family, ...value }));
}

function failureTotal(items) {
  return items.reduce((sum, item) => sum + item.value, 0) || 1;
}
