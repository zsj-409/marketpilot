// Experiment comparison page: pick up to 4 experiments, compare metrics side by side.

import { getJSON } from "../api.js";
import { groupedColumns, ChartColors } from "../charts.js";
import { esc, fmtFixed, fmtNum } from "../format.js";

const METRICS = [
  { key: "mean_regret", label: "平均 regret ↓", unit: "" },
  { key: "mean_top_k_recall", label: "top-k recall ↑", unit: "" },
  { key: "success_rate", label: "成功率 ↑", unit: "" },
  { key: "constraint_satisfaction_rate", label: "约束满足 ↑", unit: "" },
  { key: "mean_verifier_score", label: "verifier 分 ↑", unit: "" },
  { key: "mean_ranking_correlation", label: "排序相关性 ↑", unit: "" },
];

export async function render(container) {
  container.innerHTML = `<div class="loading">加载实验…</div>`;
  let experiments;
  try {
    experiments = await getJSON("/api/experiments");
  } catch (error) {
    container.innerHTML = `<div class="error-box">加载失败：${esc(error.message)}</div>`;
    return;
  }

  container.innerHTML = `
    <div class="page-head">
      <h1>实验对比</h1>
      <p class="sub">勾选 2–4 个实验，横向对比决策质量指标。同一策略不同 N 的实验也可以对比。</p>
    </div>
    <div class="grid cols-3">
      <div class="card">
        <h3>选择实验（${experiments.length}）</h3>
        <div class="compare-picker" id="picker">
          ${experiments.map((exp, index) => `
            <label><input type="checkbox" value="${esc(exp.experiment_id)}" ${index < 2 ? "checked" : ""}>
              <span class="mono">${esc(exp.name)}</span>
              <span class="dim" style="margin-left:auto">${fmtFixed(exp.metrics.mean_regret, 4)}</span>
            </label>`).join("")}
        </div>
      </div>
      <div style="grid-column:span 2" id="charts">
        <div class="loading">等待选择…</div>
      </div>
    </div>
  `;

  const picker = container.querySelector("#picker");
  picker.addEventListener("change", draw);
  draw();

  function selected() {
    const ids = [...picker.querySelectorAll("input:checked")].slice(0, 4).map((node) => node.value);
    return ids.map((id) => experiments.find((exp) => exp.experiment_id === id)).filter(Boolean);
  }

  function draw() {
    const chosen = selected();
    const holder = container.querySelector("#charts");
    if (chosen.length < 1) {
      holder.innerHTML = `<div class="empty">至少选择一个实验</div>`;
      return;
    }
    const series = chosen.map((exp, index) => ({
      name: exp.name,
      color: ChartColors.get(index),
      values: METRICS.map((metric) => {
        const value = exp.metrics[metric.key];
        return value === undefined || value === null ? null : Number(value);
      }),
    }));
    holder.innerHTML = `
      <div class="card">
        <h3>指标对比</h3>
        <div id="grouped"></div>
        <div class="legend">${series.map((s) => `<span><span class="dot" style="background:${s.color}"></span>${esc(s.name)}</span>`).join("")}</div>
      </div>
      <div class="card">
        <h3>数值明细</h3>
        ${diffTable(chosen)}
      </div>
    `;
    holder.querySelector("#grouped").appendChild(
      groupedColumns(METRICS.map((metric) => ({ label: metric.label })), series, { height: 260 }),
    );
  }

  function diffTable(chosen) {
    return `<div class="table-wrap"><table class="data">
      <thead><tr><th>指标</th>${chosen.map((exp) => `<th class="num mono">${esc(exp.name)}</th>`).join("")}</tr></thead>
      <tbody>
        ${METRICS.map((metric) => `
          <tr><td>${esc(metric.label)}</td>
          ${chosen.map((exp) => `<td class="num">${fmtFixed(exp.metrics[metric.key], 4)}</td>`).join("")}</tr>`).join("")}
        <tr><td>任务数</td>${chosen.map((exp) => `<td class="num">${fmtNum(exp.metrics.task_count)}</td>`).join("")}</tr>
        <tr><td>平均工具调用</td>${chosen.map((exp) => `<td class="num">${fmtFixed(exp.metrics.mean_tool_calls, 2)}</td>`).join("")}</tr>
        <tr><td>失败分布</td>${chosen.map((exp) => `<td class="num">${failureSummary(exp.metrics.failure_counts)}</td>`).join("")}</tr>
      </tbody></table></div>`;
  }

  function failureSummary(counts) {
    if (!counts || !Object.keys(counts).length) return "0";
    return Object.entries(counts).map(([key, value]) => `${key}×${value}`).join(", ");
  }
}
