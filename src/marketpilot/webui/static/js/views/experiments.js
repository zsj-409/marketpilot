// Benchmark experiments list page.

import { getJSON } from "../api.js";
import { esc, fmtFixed, fmtNum, fmtTime, shortId } from "../format.js";

export async function render(container) {
  container.innerHTML = `<div class="loading">加载实验列表…</div>`;
  let experiments;
  try {
    experiments = await getJSON("/api/experiments");
  } catch (error) {
    container.innerHTML = `<div class="error-box">加载失败：${esc(error.message)}</div>`;
    return;
  }

  const maxRegret = Math.max(...experiments.map((item) => item.metrics.mean_regret || 0), 1e-9);

  container.innerHTML = `
    <div class="page-head">
      <h1>基准实验</h1>
      <p class="sub">MarketPilot Synthetic Benchmark v1 · 48 任务 × 8 类目 × 6 任务族 · 点击任意一行查看逐任务结果与失败分类</p>
    </div>
    <div class="note teal">全部实验均基于<strong>确定性合成环境</strong>（隐藏潜在真值仅用于评测），regret 越低越好，top-k recall 越高越好。</div>
    <div class="card">
      ${experiments.length ? `<div class="table-wrap"><table class="data">
        <thead><tr>
          <th>实验</th><th>策略</th><th class="num">Seed</th><th>Provider / Model</th>
          <th class="num">任务数</th><th class="num">成功率</th>
          <th class="num">regret ↓</th><th class="num">top-k recall ↑</th>
          <th class="num">verifier</th><th class="num">工具调用</th><th>失败</th><th>完成时间</th>
        </tr></thead>
        <tbody>${experiments.map((exp) => `
          <tr class="clickable" data-exp="${esc(exp.experiment_id)}">
            <td class="mono">${esc(exp.name)}<br><span class="dim">${esc(shortId(exp.experiment_id))}</span></td>
            <td><span class="pill pill-accent">${esc(exp.strategy)}</span></td>
            <td class="num">${exp.seed}</td>
            <td class="dim">${esc(exp.provider)} / ${esc(exp.model)}</td>
            <td class="num">${fmtNum(exp.metrics.task_count)}</td>
            <td class="num">${fmtFixed(exp.metrics.success_rate, 3)}</td>
            <td class="num"><strong>${fmtFixed(exp.metrics.mean_regret, 4)}</strong>
              <div class="bar-track" style="height:6px;margin-top:3px"><div class="bar-fill" style="width:${((exp.metrics.mean_regret || 0) / maxRegret) * 100}%"></div></div></td>
            <td class="num">${fmtFixed(exp.metrics.mean_top_k_recall, 3)}</td>
            <td class="num">${fmtFixed(exp.metrics.mean_verifier_score, 3)}</td>
            <td class="num">${fmtFixed(exp.metrics.mean_tool_calls, 1)}</td>
            <td>${failureChips(exp.metrics.failure_counts)}</td>
            <td class="dim">${esc(fmtTime(exp.completed_at || exp.started_at))}</td>
          </tr>`).join("")}
        </tbody></table></div>`
      : `<div class="empty">暂无实验 —— 到 <a href="#/workbench">工作台</a> 跑一个 benchmark</div>`}
    </div>
    <p class="footer-note">每次实验的 manifest 记录 git commit、数据集版本、生成器版本、seed、策略与预算，保证可复现。</p>
  `;

  container.querySelectorAll("[data-exp]").forEach((row) => {
    row.addEventListener("click", () => { location.hash = `#/experiments/${row.dataset.exp}`; });
  });
}

function failureChips(counts) {
  if (!counts || !Object.keys(counts).length) return '<span class="pill pill-ok">0</span>';
  return Object.entries(counts)
    .map(([key, value]) => `<span class="pill pill-warn">${esc(key)}×${esc(value)}</span>`)
    .join(" ");
}
