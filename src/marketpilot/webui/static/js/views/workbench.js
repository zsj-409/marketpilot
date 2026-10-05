// Workbench page: submit MarketPilot jobs and watch them run.

import { getJSON, postJSON } from "../api.js";
import { esc, fmtTime, pill, shortId, statusPill } from "../format.js";

const STRATEGIES = [
  ["baseline", "baseline · 单次基线"],
  ["best-of-n", "best-of-n · N 候选扩展"],
  ["verifier-best-of-n", "verifier-best-of-n · 验证器引导"],
  ["adaptive-planner", "adaptive-planner · 自适应规划"],
  ["episodic-memory", "episodic-memory · 情景记忆"],
  ["skill-memory", "skill-memory · 技能记忆"],
];

const KIND_LABELS = {
  demo: "研究运行", benchmark: "基准实验", dataset: "生成数据集", "select-product": "闭环选品",
};

export async function render(container) {
  container.innerHTML = `
    <div class="page-head">
      <h1>运行工作台</h1>
      <p class="sub">在本机提交 MarketPilot 任务（mock 模式无需任何 API Key）· 任务以子进程执行并落盘日志</p>
    </div>

    <div class="grid cols-2">
      <div class="card">
        <h3>研究运行（demo）</h3>
        <p class="card-hint">完整多智能体研究流水线：规划 → 8 角色执行 → 证据 → 推荐 → 评测 → 轨迹落盘</p>
        <label class="field"><span>研究目标</span>
          <textarea id="demo-goal">Find promising pet products in the US market</textarea></label>
        <div class="form-row">
          <label class="field"><span>执行模式</span>
            <select id="demo-mode">
              <option value="mock">mock · 确定性智能体（离线）</option>
              <option value="llm">llm · 真实 LLM（需已配置 Key）</option>
            </select></label>
          <label class="field"><span>调研环境</span>
            <select id="demo-research">
              <option value="mock">mock · 合成调研</option>
              <option value="live">live · 真实网络（需 Search Key）</option>
            </select></label>
        </div>
        <button class="btn" id="demo-submit" data-kind="demo">提交研究运行</button>
      </div>

      <div class="card">
        <h3>基准实验（benchmark）</h3>
        <p class="card-hint">48 任务合成基准 · 策略在完全相同的环境上对比</p>
        <label class="field"><span>策略</span>
          <select id="bm-strategy">${STRATEGIES.map(([value, label]) => `<option value="${value}">${label}</option>`).join("")}</select></label>
        <div class="form-row">
          <label class="field"><span>候选数 N（1–8）</span><input type="number" id="bm-n" value="4" min="1" max="8"></label>
          <label class="field"><span>Seed</span><input type="number" id="bm-seed" value="42" min="0"></label>
        </div>
        <button class="btn" id="bm-submit" data-kind="benchmark">提交基准实验</button>
      </div>

      <div class="card">
        <h3>合成数据集（dataset）</h3>
        <p class="card-hint">重新生成 synthetic-market-v1：144 商品 + 评审 + 来源 + 隐藏真值</p>
        <label class="field"><span>Seed</span><input type="number" id="ds-seed" value="42" min="0"></label>
        <button class="btn" id="ds-submit" data-kind="dataset">提交数据集生成</button>
      </div>

      <div class="card">
        <h3>闭环选品（select-product）</h3>
        <p class="card-hint">DecisionCritic 闭环：评估 → 批评 → 定向补研 → 终止判定</p>
        <label class="field"><span>选品目标</span>
          <textarea id="sp-goal">Find a promising pet product</textarea></label>
        <label class="field"><span>最大轮数（1–6）</span><input type="number" id="sp-rounds" value="3" min="1" max="6"></label>
        <button class="btn" id="sp-submit" data-kind="select-product">提交闭环选品</button>
      </div>
    </div>

    <h2 class="section">任务队列</h2>
    <div class="card">
      <div class="table-wrap"><table class="data" id="jobs-table">
        <tbody><tr><td class="loading">加载任务…</td></tr></tbody></table></div>
    </div>
    <div class="card" id="log-card" style="display:none">
      <h3 id="log-title">任务日志</h3>
      <pre class="log" id="log-view"></pre>
    </div>
  `;

  const buttons = container.querySelectorAll("[data-kind]");
  buttons.forEach((button) => {
    button.addEventListener("click", () => submit(button.dataset.kind));
  });

  await refresh();

  async function submit(kind) {
    const payload = {};
    try {
      if (kind === "demo") {
        payload.goal = container.querySelector("#demo-goal").value.trim();
        payload.mode = container.querySelector("#demo-mode").value;
        payload.research_mode = container.querySelector("#demo-research").value;
      } else if (kind === "benchmark") {
        payload.strategy = container.querySelector("#bm-strategy").value;
        payload.n = Number(container.querySelector("#bm-n").value) || 1;
        payload.seed = Number(container.querySelector("#bm-seed").value) || 42;
      } else if (kind === "dataset") {
        payload.seed = Number(container.querySelector("#ds-seed").value) || 42;
      } else if (kind === "select-product") {
        payload.goal = container.querySelector("#sp-goal").value.trim();
        payload.max_rounds = Number(container.querySelector("#sp-rounds").value) || 3;
      }
      await postJSON(`/api/jobs/${kind}`, payload);
      toast("任务已提交", false);
    } catch (error) {
      toast(`提交失败：${error.message}`, true);
      return;
    }
    await refresh();
  }

  async function refresh() {
    let jobs;
    try {
      jobs = await getJSON("/api/jobs");
    } catch {
      return;
    }
    const table = container.querySelector("#jobs-table");
    if (!jobs.length) {
      table.innerHTML = `<tbody><tr><td><div class="empty" style="border:none;background:none">还没有任务 —— 提交一个试试</div></td></tr></tbody>`;
      return;
    }
    table.innerHTML = `
      <thead><tr><th>任务</th><th>类型</th><th>状态</th><th>提交时间</th><th>结束时间</th><th class="num">退出码</th><th></th></tr></thead>
      <tbody>${jobs.map((job) => `
        <tr>
          <td class="mono">${esc(shortId(job.job_id))}</td>
          <td>${esc(KIND_LABELS[job.kind] || job.kind)}</td>
          <td>${statusPill(job.status)}</td>
          <td class="dim">${esc(fmtTime(job.created_at))}</td>
          <td class="dim">${esc(fmtTime(job.finished_at))}</td>
          <td class="num">${job.return_code ?? "—"}</td>
          <td><button class="btn subtle sm" data-log="${esc(job.job_id)}">日志</button>
            ${job.status === "SUCCEEDED" && job.kind === "demo" ? '<a class="btn sm" href="#/runs" style="margin-left:6px">看结果 →</a>' : ""}
            ${job.status === "SUCCEEDED" && job.kind === "benchmark" ? '<a class="btn sm" href="#/experiments" style="margin-left:6px">看结果 →</a>' : ""}
          </td>
        </tr>`).join("")}
      </tbody>`;
    table.querySelectorAll("[data-log]").forEach((button) => {
      button.addEventListener("click", () => showLog(button.dataset.log));
    });

    if (jobs.some((job) => job.status === "QUEUED" || job.status === "RUNNING")) {
      setTimeout(refresh, 2000);
    }
  }

  async function showLog(jobId) {
    const card = container.querySelector("#log-card");
    const view = container.querySelector("#log-view");
    card.style.display = "block";
    view.textContent = "加载日志…";
    try {
      const payload = await getJSON(`/api/jobs/${jobId}/log`);
      view.textContent = payload.log || "（暂无输出）";
      container.querySelector("#log-title").textContent = `任务日志 · ${shortId(jobId)}`;
      view.scrollTop = view.scrollHeight;
    } catch (error) {
      view.textContent = `日志加载失败：${error.message}`;
    }
  }
}

function toast(message, isError) {
  const node = document.getElementById("toast");
  node.textContent = message;
  node.classList.toggle("err", Boolean(isError));
  node.classList.remove("hidden");
  clearTimeout(node._timer);
  node._timer = setTimeout(() => node.classList.add("hidden"), 3200);
}
