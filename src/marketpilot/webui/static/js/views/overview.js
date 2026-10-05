// Overview page: project story, stats, architecture, strategy summary.

import { getJSON } from "../api.js";
import { esc, fmtFixed, fmtNum, fmtTimeShort, shortId, statusPill, decisionPill } from "../format.js";

export async function render(container) {
  container.innerHTML = `<div class="loading">加载总览数据…</div>`;
  let data;
  try {
    data = await getJSON("/api/overview");
  } catch (error) {
    container.innerHTML = `<div class="error-box">加载失败：${esc(error.message)}</div>`;
    return;
  }

  const env = data.environment;
  const best = data.strategy_table[0];

  container.innerHTML = `
    <section class="hero">
      <h1>MarketPilot · 证据驱动的多智能体商品调研平台</h1>
      <p>可复现的多智能体研究运行时：真实 LLM、只读调研环境、隐藏真值的合成市场基准、
      全链路证据溯源、轨迹回放、验证器引导的 Test-Time Scaling、自适应规划与情景记忆。</p>
      <p>所有基准结果均为<strong>合成环境内的决策质量</strong>，不代表真实市场表现 —— 每个数字都可重放、可审计。</p>
      <div class="actions">
        <a class="btn" href="#/workbench">▶ 运行一次研究</a>
        <a class="btn ghost" href="#/runs">查看研究运行</a>
        <a class="btn ghost" href="#/experiments">查看基准实验</a>
      </div>
      <div class="hero-code">uv run marketpilot workbench &nbsp;→&nbsp; http://127.0.0.1:8600 &nbsp;·&nbsp; 无需任何 API Key</div>
    </section>

    <div class="grid cols-6">
      ${statCard("研究运行", data.research_runs, "runs/", "accent")}
      ${statCard("闭环选品", data.selection_runs, "runs/select-*", "teal")}
      ${statCard("基准实验", data.experiments, "benchmark_runs/", "accent")}
      ${statCard("基准任务执行", data.total_benchmark_tasks, "48 任务 / 套件", "teal")}
      ${statCard("合成商品", env ? env.product_count : "—", env ? `${env.categories.length} 个类目` : "生成数据集", "accent")}
      ${statCard("评审样本", env ? env.review_count : "—", env ? `${env.source_count} 个来源` : "", "teal")}
    </div>

    <h2 class="section">系统架构</h2>
    <div class="card">${architectureSvg()}</div>

    <h2 class="section">策略对比（跨实验聚合）</h2>
    <div class="card">
      ${data.strategy_table.length ? strategyTable(data.strategy_table, best) : `<div class="empty">暂无实验数据，先到 <a href="#/workbench">工作台</a> 跑一个 benchmark</div>`}
      <p class="card-hint" style="margin:10px 0 0">按策略聚合全部实验（任务数加权）。regret 越低越好；关键发现：验证器过程分与隐藏决策效用几乎不相关（Spearman ≈ 0.026），更多计算并不自动带来更好的选品。</p>
    </div>

    <div class="grid cols-2">
      <div>
        <h2 class="section">最近研究运行</h2>
        <div class="card">
          ${data.latest_runs.length ? runList(data.latest_runs) : `<div class="empty">暂无运行记录</div>`}
        </div>
      </div>
      <div>
        <h2 class="section">最近基准实验</h2>
        <div class="card">
          ${data.latest_experiments.length ? experimentList(data.latest_experiments) : `<div class="empty">暂无实验记录</div>`}
        </div>
      </div>
    </div>

    <h2 class="section">阅读这份系统时值得注意的</h2>
    <div class="grid cols-2">
      <div class="card">
        <h3>诚实标签</h3>
        <ul style="margin:0;padding-left:18px;color:var(--text-2);font-size:12.5px;line-height:1.9">
          <li>合成基准结果只描述<strong>确定性合成环境内</strong>的行为，不是真实市场结论。</li>
          <li>Agent 只能看到可观测字段；隐藏的潜在机会/风险分数仅用于评测。</li>
          <li>mock / replay / live 模式的结果在所有产物中都带有模式标签。</li>
          <li>每次实验写入 manifest：git commit、数据集与生成器版本、seed、策略、预算。</li>
        </ul>
      </div>
      <div class="card">
        <h3>一条完整证据链</h3>
        <p style="margin:4px 0 8px;font-size:12.5px;color:var(--text-2)">
          任意一条推荐都可以下钻到发现 → 证据 → 来源快照 → 工具调用 → 轨迹事件。
          打开一次 <a href="#/runs">研究运行</a>，试试任务 DAG、时间线和证据表。
        </p>
        <div class="chip-row">
          <span class="chip">ResearchGoal</span><span class="chip">TaskDAG</span>
          <span class="chip">Evidence</span><span class="chip">Finding</span>
          <span class="chip">RiskFlag</span><span class="chip">Recommendation</span>
          <span class="chip">Verifier</span><span class="chip">Trajectory</span>
        </div>
      </div>
    </div>

    <p class="footer-note">MarketPilot Workbench · 只读展示 + 受控任务提交 · 默认仅监听 127.0.0.1</p>
  `;

  container.querySelectorAll("[data-run-link]").forEach((node) => {
    node.addEventListener("click", () => { location.hash = `#/runs/${node.dataset.runLink}`; });
  });
  container.querySelectorAll("[data-exp-link]").forEach((node) => {
    node.addEventListener("click", () => { location.hash = `#/experiments/${node.dataset.expLink}`; });
  });
}

function statCard(label, value, foot, tone) {
  return `<div class="stat ${tone}"><div class="label">${esc(label)}</div>
    <div class="value">${esc(fmtNum(value))}</div><div class="foot">${esc(foot)}</div></div>`;
}

function strategyTable(rows, best) {
  const maxRegret = Math.max(...rows.map((row) => row.mean_regret), 1e-9);
  return `<div class="table-wrap"><table class="data">
    <thead><tr>
      <th>策略</th><th class="num">实验数</th><th class="num">任务数</th>
      <th class="num">平均 regret ↓</th><th class="num">top-k recall ↑</th>
      <th class="num">verifier 分</th><th class="num">工具调用</th><th>regret 对比</th>
    </tr></thead>
    <tbody>${rows.map((row) => `
      <tr>
        <td><strong>${esc(row.strategy)}</strong>${best && row.strategy === best.strategy ? ' <span class="pill pill-teal">最优</span>' : ""}</td>
        <td class="num">${row.experiment_count}</td>
        <td class="num">${fmtNum(row.task_count)}</td>
        <td class="num">${fmtFixed(row.mean_regret, 4)}</td>
        <td class="num">${fmtFixed(row.mean_top_k_recall, 3)}</td>
        <td class="num">${fmtFixed(row.mean_verifier_score, 3)}</td>
        <td class="num">${fmtFixed(row.mean_tool_calls, 2)}</td>
        <td style="min-width:130px"><div class="bar-track" style="height:9px"><div class="bar-fill" style="width:${(row.mean_regret / maxRegret) * 100}%;background:${row.strategy === (best && best.strategy) ? "var(--teal)" : "var(--accent)"}"></div></div></td>
      </tr>`).join("")}
    </tbody></table></div>`;
}

function runList(runs) {
  return `<div class="table-wrap"><table class="data">
    <thead><tr><th>Run</th><th>状态</th><th>决策</th><th>时间</th></tr></thead>
    <tbody>${runs.map((run) => `
      <tr class="clickable" data-run-link="${esc(run.run_id)}">
        <td class="mono">${esc(shortId(run.run_id))} <span class="dim">${run.kind === "selection" ? "选品" : esc(run.category || "")}</span></td>
        <td>${statusPill(run.status)}</td>
        <td>${decisionPill(run.decision)}</td>
        <td class="dim">${esc(fmtTimeShort(run.started_at))}</td>
      </tr>`).join("")}
    </tbody></table></div>`;
}

function experimentList(experiments) {
  return `<div class="table-wrap"><table class="data">
    <thead><tr><th>实验</th><th>策略</th><th class="num">regret</th><th class="num">top-k</th></tr></thead>
    <tbody>${experiments.map((exp) => `
      <tr class="clickable" data-run-link="#" style="cursor:pointer" data-exp-link="${esc(exp.experiment_id)}">
        <td class="mono">${esc(exp.name)}</td>
        <td><span class="pill pill-accent">${esc(exp.strategy)}</span></td>
        <td class="num">${fmtFixed(exp.metrics.mean_regret, 4)}</td>
        <td class="num">${fmtFixed(exp.metrics.mean_top_k_recall, 3)}</td>
      </tr>`).join("")}
    </tbody></table></div>`;
}

function architectureSvg() {
  return `<svg class="arch" viewBox="0 0 1080 300">
    <defs>
      <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#8794ab"></path>
      </marker>
    </defs>
    ${box(30, 20, 200, 52, "box-dark", "Research Goal", "t-white", "研究目标 · 市场/类目/约束")}
    ${box(280, 20, 200, 52, "box-accent", "Research Planner", "t-accent", "固定 DAG / 自适应 DAG")}
    ${box(530, 20, 220, 52, "box-accent", "Multi-Agent Runtime", "t-accent", "8 角色共享黑板 · DAGRunner")}
    ${box(800, 20, 250, 52, "box", "ToolExecutor", "", "mock / replay / live 三模式")}
    ${arrow(230, 46, 280, 46)}
    ${arrow(480, 46, 530, 46)}
    ${arrow(750, 46, 800, 46)}
    ${box(60, 130, 250, 52, "box", "Synthetic Market", "", "144 商品 · 隐藏潜在真值")}
    ${box(400, 130, 250, 52, "box", "Replay Research", "", "严格回放 · 不回退网络")}
    ${box(740, 130, 280, 52, "box", "Live Research", "", "Tavily 搜索 + 只读抓取")}
    ${arrow(860, 72, 880, 130)}
    ${arrow(560, 72, 530, 130)}
    ${arrow(200, 72, 185, 130)}
    ${box(360, 220, 360, 52, "box-accent", "Evidence Graph → Candidate Set", "t-accent", "证据 → 发现 → 候选 → 风险")}
    ${arrow(200, 182, 380, 220)}
    ${arrow(525, 182, 540, 220)}
    ${arrow(880, 182, 700, 220)}
    ${box(780, 220, 270, 52, "box", "Verifier → Recommendation", "", "确定性验证 · 可检视 issue")}
    ${arrow(720, 246, 780, 246)}
    ${box(30, 220, 280, 52, "box", "Evaluator → Benchmark DB", "", "regret / recall / 失败分类")}
    ${arrow(360, 246, 310, 246)}
  </svg>`;

  function box(x, y, w, h, cls, title, titleCls, sub) {
    return `<g>
      <rect x="${x}" y="${y}" width="${w}" height="${h}" class="${cls}" rx="9" stroke-width="1.4"></rect>
      <text x="${x + w / 2}" y="${y + (sub ? 22 : 30)}" text-anchor="middle" class="${titleCls}">${esc(title)}</text>
      ${sub ? `<text x="${x + w / 2}" y="${y + 40}" text-anchor="middle" font-size="10.5">${esc(sub)}</text>` : ""}
    </g>`;
  }
  function arrow(x1, y1, x2, y2) {
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="arrow" marker-end="url(#arr)"></line>`;
  }
}
