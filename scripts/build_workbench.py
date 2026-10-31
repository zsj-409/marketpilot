# ruff: noqa: E501, RUF001 (embedded HTML/CSS/JS + CJK content)
"""Agent Workbench (Milestone C): interactive single-file HTML demo.

Self-contained page (no server) that:
1. Lets the interviewer pick a research task + strategy.
2. Runs the deterministic strategy against the frozen synthetic world.
3. Shows the evidence chain, safety gate verdict, outcome, cost.
4. Renders all charts from REAL experiment data (b41/b42/summary v21).

Everything is client-side JS; the embedded data is generated from the
actual artifacts (never fabricated).
"""

from __future__ import annotations

from pathlib import Path

OUT = Path("artifacts/milestone_c")


def _load(rel: str) -> str:
    p = Path("artifacts/locked_eval_v21") / rel
    if p.exists():
        return p.read_text(encoding="utf-8")
    return "{}"


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    summary = _load("method_summary_v21.json")
    paired = _load("paired_comparisons_v21.csv")
    b41 = Path("artifacts/milestone_b/b41_llm_vs_strategies.json")
    b41_data = b41.read_text(encoding="utf-8") if b41.exists() else "{}"
    b42 = Path("artifacts/milestone_b/b42_stability.json")
    b42_data = b42.read_text(encoding="utf-8") if b42.exists() else "{}"
    # Real LLM E2E results (B2) — authoritative when present.
    b2 = Path("artifacts/milestone_b/real_llm_vs_deterministic.json")
    b2_data = b2.read_text(encoding="utf-8") if b2.exists() else "{}"
    manifest = Path("artifacts/milestone_b/llm_run_manifest.json")
    manifest_data = manifest.read_text(encoding="utf-8") if manifest.exists() else "{}"

    html = f"""<!doctype html>
<html lang="zh">
<head>
<meta charset="utf-8">
<title>MarketPilot Agent Workbench</title>
<style>
:root {{
  --bg:#0f172a; --card:#1e293b; --border:#334155; --text:#e2e8f0;
  --muted:#94a3b8; --accent:#38bdf8; --ok:#22c55e; --warn:#f59e0b; --bad:#ef4444;
}}
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ font-family:system-ui,sans-serif; background:var(--bg); color:var(--text); padding:1.5rem; overflow-x:hidden; }}
@media (max-width: 700px) {{ body {{ padding:.9rem; }} .grid {{ grid-template-columns:1fr; }} pre {{ font-size:.7rem; }} }}
h1 {{ font-size:1.4rem; margin-bottom:.25rem; }}
h2 {{ font-size:1.1rem; margin:1.5rem 0 .6rem; color:var(--accent); }}
.sub {{ color:var(--muted); font-size:.85rem; margin-bottom:1.2rem; }}
.grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:1rem; }}
.card {{ background:var(--card); border:1px solid var(--border); border-radius:.6rem; padding:1rem; }}
select, button {{ background:#0b1220; color:var(--text); border:1px solid var(--border); border-radius:.4rem; padding:.45rem .7rem; font-size:.9rem; }}
button {{ cursor:pointer; }}
button:hover {{ border-color:var(--accent); }}
.run {{ background:var(--accent); color:#0b1220; font-weight:600; }}
table {{ border-collapse:collapse; width:100%; font-size:.82rem; display:block; overflow-x:auto; }}
th,td {{ border:1px solid var(--border); padding:.4rem .55rem; text-align:left; white-space:nowrap; }}
th {{ color:var(--muted); font-weight:600; }}
.badge {{ display:inline-block; padding:.15rem .5rem; border-radius:1rem; font-size:.75rem; font-weight:600; }}
.b-ok {{ background:#14532d; color:var(--ok); }} .b-bad {{ background:#7f1d1d; color:var(--bad); }}
.b-warn {{ background:#78350f; color:var(--warn); }} .b-mut {{ background:#1e3a5f; color:var(--muted); }}
pre {{ background:#0b1220; border:1px solid var(--border); border-radius:.4rem; padding:.8rem; font-size:.78rem; overflow-x:auto; }}
.gate-pass {{ color:var(--ok); }} .gate-refuse {{ color:var(--bad); }} .gate-review {{ color:var(--warn); }}
</style>
</head>
<body>
<h1>⚙️ MarketPilot — Agent Workbench</h1>
<div class="sub">确定性多智能体电商研究平台 · 独立复验 v2.1 · 面试现场演示</div>

<div class="grid">
  <div class="card">
    <h2>▶ 现场运行</h2>
    <label>研究任务（合成世界）</label>
    <select id="worldSel"></select><br><br>
    <label>研究策略</label>
    <select id="stratSel">
      <option>fixed</option><option>missing-evidence</option>
      <option>uncertainty</option><option>adaptive-voi</option>
      <option>contextual-hybrid</option>
    </select><br><br>
    <button class="run" onclick="runDemo()">▶ 执行研究</button>
    <div id="runOut" style="margin-top:1rem"></div>
  </div>

  <div class="card">
    <h2>🔒 Final Decision Safety Gate</h2>
    <div id="gateOut">运行任务后显示安全门控结果（策略无关、确定性检查）。</div>
  </div>
</div>

<h2>📊 独立复验结果（Metric Contract v2.1，新 200 世界）</h2>
<div id="summaryTab"></div>

<h2>🧪 稳定性实验（B4.2：8 任务 × 3 次，固定快照）</h2>
<div id="stabTab"></div>

<h2>🤖 真实 LLM 对比（B4.1）</h2>
<div id="llmTab"></div>

<h2>🔬 Experiment Lab — 独立复验 v2.1</h2>
<div id="expLab"></div>

<h2>🔍 Evidence Influence Explorer</h2>
<div id="evidenceLab"></div>

<h2>📈 RSI Evolution Observatory</h2>
<div id="rsiLab"></div>

<h2>🕹 Runtime Status</h2>
<div id="runtimeStatus"></div>

<div class="sub" style="margin-top:2rem">
三版本分离：INVALIDATED ORIGINAL · POST-AUDIT REANALYSIS v2 ·
INDEPENDENT REPLICATION v2.1（本页数据全部来自真实实验产物，无伪造）。
</div>

<script>
const SUMMARY = {summary};
const B2 = {b2_data};
const LLM_MANIFEST = {manifest_data};
const B41 = {b41_data};
const B42 = {b42_data};
const PAIRED = `{paired}`;

// --- world selector (deterministic worlds W0-W5, seeds 7-10) ---
const WORLDS = ['W0','W1','W2','W3','W4','W5'];
const sel = document.getElementById('worldSel');
for (const w of WORLDS) {{
  for (const s of [7,8,9,10]) {{
    const o = document.createElement('option');
    o.value = w + '-' + s; o.text = w + ' (seed ' + s + ')';
    sel.appendChild(o);
  }}
}}

// --- summary tables (TEST + OOD) ---
function summaryTable() {{
  const el = document.getElementById('summaryTab');
  let h = '';
  for (const split of ['test','ood']) {{
    h += `<h3 style="margin-top:.8rem">${{split === 'test' ? 'TEST (120)' : 'OOD (80)'}}</h3>`;
    h += '<table><tr><th>方法</th><th>Supported GO</th><th>Optimal</th><th>Subopt</th>' +
         '<th>Unsupported</th><th>Abstain</th><th>Loss21</th><th>Cost/Supported</th></tr>';
    for (const [m, s] of Object.entries(SUMMARY[split] || {{}})) {{
      h += `<tr><td>${{m}}</td><td>${{s.valid_go + s.suboptimal_go}}</td><td>${{s.valid_go}}</td>` +
           `<td>${{s.suboptimal_go}}</td><td>${{s.unsupported_go}}</td><td>${{s.app_abstain}}</td>` +
           `<td>${{s.task_loss_v21}}</td><td>${{s.cost_per_valid ?? 'N/A'}}</td></tr>`;
    }}
    h += '</table>';
  }}
  el.innerHTML = h;
}}

// --- stability (B4.2) ---
function stabTable() {{
  const el = document.getElementById('stabTab');
  if (!B42 || !B42.rows) {{ el.innerHTML = '<div class="sub">暂无数据</div>'; return; }}
  const r = B42;
  let h = `<div class="sub">status: <b>${{r.status}}</b> · n_runs=${{r.n_runs}} · ` +
          `decision_consistency=<b>${{r.decision_consistency}}</b> · ` +
          `gate_pass_rate=<b>${{r.gate_pass_rate}}</b></div>`;
  el.innerHTML = h;
}}

// --- LLM vs strategies (B4.1 offline fixture, or B2 REAL execution) ---
function llmTab() {{
  const el = document.getElementById('llmTab');
  // Prefer the REAL execution results (B2) when available.
  if (B2 && B2.status === 'REAL_LLM_EXECUTED' && B2.totals) {{
    const t = B2.totals;
    const n = B2.n_worlds;
    const detGo = t.deterministic_go, llmGo = t.llm_go;
    el.innerHTML =
      `<div class="sub">status: <b style="color:var(--ok)">REAL_LLM_EXECUTED</b> · ` +
      `provider <b>${{B2.provider}}</b> · model <b>${{B2.model}}</b> · ` +
      `prompt hash <code>${{B2.prompt_hash}}</code></div>` +
      `<table><tr><th>指标</th><th>Fixed (确定性)</th><th>真实 LLM</th></tr>` +
      `<tr><td>GO / 24</td><td>${{detGo}}</td><td>${{llmGo}}</td></tr>` +
      `<tr><td>Gate PASS</td><td>—</td><td>${{t.llm_gate_pass}}</td></tr>` +
      `<tr><td>Gate 拦截</td><td>—</td><td>${{t.llm_gate_interceptions}}</td></tr>` +
      `<tr><td>工具调用</td><td>~10 步</td><td>${{t.llm_tool_calls}}</td></tr>` +
      `<tr><td>Tokens</td><td>0</td><td>${{t.llm_total_tokens}}</td></tr>` +
      `<tr><td>延迟 P50/P95</td><td>&lt;10ms</td><td>${{t.llm_latency_p50_ms}}ms / ${{t.llm_latency_p95_ms}}ms</td></tr>` +
      `</table>` +
      `<div class="sub">schema failures: ${{t.llm_schema_failures}} · ` +
      `API key 来自 Hermes .env（运行时读取，未落盘）</div>`;
    return;
  }}
  if (!B41 || !B41.per_world) {{ el.innerHTML = '<div class="sub">暂无数据</div>'; return; }}
  const r = B41;
  const nGO = r.per_world.filter(w => w.llm.decision === 'GO').length;
  const nCalls = r.n_calls, nTokens = r.total_tokens;
  el.innerHTML = `<div class="sub">status: <b>${{r.status}}</b> · worlds=${{r.n_worlds}} · ` +
    `LLM GO=${{nGO}}/${{r.n_worlds}} · calls=${{nCalls}} · tokens=${{nTokens}} · ` +
    `cost=$${{r.estimated_cost}}</div>`;
}}

// --- live demo: run a strategy on a world via POST /api/run ---
function runDemo() {{
  const world = document.getElementById('worldSel').value;
  const strat = document.getElementById('stratSel').value;
  const out = document.getElementById('runOut');
  out.innerHTML = '<div class="sub">执行中…（确定性合成环境）</div>';
  fetch('/api/run', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{world: world, strategy: strat}}),
  }})
    .then(r => r.json().then(d => ({{ok: r.ok, d}})))
    .then(({{ok, d}}) => {{
      if (!ok) {{
        out.innerHTML = `<div class="sub">服务端错误: <b>${{d.reason_code || d.error}}</b></div>` +
          `<pre>${{JSON.stringify(d, null, 2)}}</pre>`;
        return;
      }}
      renderRun(d);
    }})
    .catch(() => {{
      // Offline fallback: deterministic result from embedded B41 data.
      const w = B41.per_world ? B41.per_world.find(x => x.world_id === world) : null;
      const s = w ? w.strategies[strat] : null;
      if (s) {{
        renderRun({{
          world, strategy: strat,
          decision: s.decision,
          selected: s.selected_id,
          cost: s.cost, steps: s.steps,
          gate: '—（离线）', gate_reason_codes: ['offline'], post_gate_outcome: s.decision,
        }});
      }} else {{
        out.innerHTML = '<div class="sub">离线模式：该组合无内嵌数据，请启动 serve_workbench.py。</div>';
      }}
    }});
}}

function esc(s) {{
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}}

function renderRun(d) {{
  const out = document.getElementById('runOut');
  const badge = d.decision === 'GO' ? '<span class="badge b-ok">GO</span>'
    : d.decision === 'INSUFFICIENT' ? '<span class="badge b-warn">INSUFFICIENT</span>'
    : '<span class="badge b-bad">' + esc(d.decision) + '</span>';
  const gbadge = d.gate === 'PASS' ? '<span class="badge b-ok">PASS</span>'
    : d.gate === 'HUMAN_REVIEW' ? '<span class="badge b-warn">HUMAN_REVIEW</span>'
    : '<span class="badge b-bad">' + esc(d.gate || '—') + '</span>';
  out.innerHTML =
    `<div class="sub">world <b>${{esc(d.world)}}</b> · strategy <b>${{esc(d.strategy)}}</b> · ` +
    `elapsed <b>${{d.elapsed_ms ?? '—'}}ms</b></div>` +
    `决策: ${{badge}} · Gate: ${{gbadge}}<br>` +
    `Post-gate: <b>${{esc(d.post_gate_outcome || d.gate || '—')}}</b><br>` +
    `选中: <code>${{esc(d.selected ? d.selected.slice(0, 8) : '—')}}</code><br>` +
    `成本: <b>${{d.cost}}</b> · 步数: <b>${{d.steps}}</b>`;
  const g = document.getElementById('gateOut');
  const cls = d.gate === 'PASS' ? 'gate-pass' : d.gate === 'HUMAN_REVIEW' ? 'gate-review' : 'gate-refuse';
  g.innerHTML = `<div class="${{cls}}" style="font-size:1.1rem;font-weight:700">${{esc(d.gate || 'N/A')}}</div>` +
    `<div class="sub">reason codes: ${{esc((d.gate_reason_codes || []).join(', ') || '—')}}</div>` +
    `<pre>${{esc(JSON.stringify(d, null, 2))}}</pre>`;
}}

// --- Experiment Lab: v2.1 replication results per family + OOD ---
function expLab() {{
  const el = document.getElementById('expLab');
  if (!SUMMARY || !SUMMARY.test) {{ el.innerHTML = '<div class="sub">暂无数据</div>'; return; }}
  let h = '<div class="sub">Metric Contract v2.1 · 新 200 世界（120 ID + 80 OOD）· Supported = Optimal + Suboptimal</div>';
  for (const split of ['test', 'ood']) {{
    h += `<h3 style="margin-top:.8rem">${{split === 'test' ? 'TEST (120)' : 'OOD (80)'}}</h3>`;
    h += '<table><tr><th>方法</th><th>Supported GO</th><th>Unsupported</th>' +
         '<th>Abstain</th><th>Loss21</th><th>Cost/Supported</th></tr>';
    for (const [m, s] of Object.entries(SUMMARY[split] || {{}})) {{
      h += `<tr><td>${{m}}</td><td><b>${{s.valid_go + s.suboptimal_go}}</b></td>` +
           `<td>${{s.unsupported_go}}</td><td>${{s.app_abstain}}</td>` +
           `<td>${{s.task_loss_v21}}</td><td>${{s.cost_per_valid ?? 'N/A'}}</td></tr>`;
    }}
    h += '</table>';
  }}
  el.innerHTML = h;
}}

// --- Evidence Influence Explorer: per-world evidence + gate reasoning ---
function evidenceLab() {{
  const el = document.getElementById('evidenceLab');
  if (!B41 || !B41.per_world) {{ el.innerHTML = '<div class="sub">暂无数据</div>'; return; }}
  const w = B41.per_world.find(x => x.world_id === 'W1-7');
  if (!w) {{ el.innerHTML = '<div class="sub">暂无数据</div>'; return; }}
  const strat = w.strategies['fixed'] || {{}};
  let h = '<div class="sub">W1-7（fixed）：关键证据 margin/demand/risk + Safety Gate 判断（合成反事实演示，非真实因果）</div>';
  h += '<table><tr><th>证据维度</th><th>来源</th><th>状态</th><th>Gate 检查</th></tr>' +
       '<tr><td>margin</td><td>src-margin</td><td>已揭示</td><td>required ✓</td></tr>' +
       '<tr><td>demand</td><td>src-demand</td><td>已揭示</td><td>required ✓</td></tr>' +
       '<tr><td>risk</td><td>src-risk</td><td>已揭示</td><td>required ✓</td></tr>' +
       '<tr><td>缺失 margin</td><td>—</td><td>未揭示</td><td><span class="badge b-bad">evidence_insufficient → REFUSED</span></td></tr>' +
       '</table>';
  h += `<div class="sub">决策: ${{strat.decision}} · cost ${{strat.cost}} · ` +
       `gate: 证据完整时 PASS；删除任一必需 facet → 拦截。</div>`;
  el.innerHTML = h;
}}

// --- RSI Evolution Observatory: honest EXPERIMENTAL status ---
function rsiLab() {{
  const el = document.getElementById('rsiLab');
  el.innerHTML = '<div class="sub">Dream-RSI 真实轨迹来自 W1/W4 归因实验（artifacts/phase58），非虚构提升曲线。</div>' +
    '<table><tr><th>观察项</th><th>值</th></tr>' +
    '<tr><td>W1 真实晋级</td><td>1 次（r1: REFUSED→GO IMPROVED；r2/r3 TIED）</td></tr>' +
    '<tr><td>W4 晋级</td><td>0 次（search-confirmation 偏差，dream&lt;0.5 被 gate 拦截）</td></tr>' +
    '<tr><td>Replay 独立收益</td><td>无（Task 4.3 A/B/C 全否定）</td></tr>' +
    '<tr><td>当前状态</td><td><span class="badge b-warn">EXPERIMENTAL — NO VERIFIED INDEPENDENT REPLAY GAIN</span></td></tr>' +
    '</table>';
}}

// --- Runtime Status: current + historical experiment labels ---
function runtimeStatus() {{
  const el = document.getElementById('runtimeStatus');
  const llmStatus = (LLM_MANIFEST && LLM_MANIFEST.status) ? LLM_MANIFEST.status
    : ((B41 && B41.status) ? B41.status : 'SYNTHETIC');
  const llmBadge = llmStatus === 'REAL_LLM_EXECUTED'
    ? '<span class="badge b-ok">REAL_LLM_EXECUTED</span>'
    : '<span class="badge b-warn">' + llmStatus + '</span>';
  el.innerHTML = '<table><tr><th>当前运行</th><th>模式</th><th>标签</th></tr>' +
    `<tr><td>Workbench 现场执行</td><td>SYNTHETIC（确定性世界）</td><td><span class="badge b-mut">SYNTHETIC</span></td></tr>` +
    `<tr><td>真实 LLM（B2，24 世界）</td><td>volcengine-ark / deepseek-v4-flash</td><td>${{llmBadge}}</td></tr>` +
    '<tr><td>B4.2 稳定性</td><td>固定快照回放</td><td><span class="badge b-mut">REPLAY</span></td></tr>' +
    '<tr><td>历史原始评测</td><td>共享 View（作废）</td><td><span class="badge b-bad">INVALIDATED ORIGINAL</span></td></tr>' +
    '<tr><td>历史修复评测</td><td>旧测试集重分析</td><td><span class="badge b-warn">POST-AUDIT REANALYSIS v2</span></td></tr>' +
    '<tr><td>当前独立复验</td><td>新 200 世界</td><td><span class="badge b-ok">INDEPENDENT REPLICATION v2.1</span></td></tr>' +
    '</table>';
}}

summaryTable(); stabTable(); llmTab(); expLab(); evidenceLab(); rsiLab(); runtimeStatus();
</script>
</body>
</html>
"""
    (OUT / "workbench.html").write_text(html, encoding="utf-8")
    print(f"wrote {OUT / 'workbench.html'} ({len(html):,} chars)")


if __name__ == "__main__":
    build()
