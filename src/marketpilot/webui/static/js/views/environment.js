// Synthetic environment explorer: categories, observable products, evidence facets.

import { getJSON } from "../api.js";
import { esc, fmtFixed, fmtNum } from "../format.js";

export async function render(container) {
  container.innerHTML = `<div class="loading">加载合成环境…</div>`;
  let env;
  try {
    env = await getJSON("/api/environment");
  } catch (error) {
    container.innerHTML = `
      <div class="error-box">加载失败：${esc(error.message)}</div>
      <p class="sub">数据集尚未生成。到 <a href="#/workbench">工作台</a> 提交一次「生成数据集」任务即可。</p>`;
    return;
  }

  container.innerHTML = `
    <div class="page-head">
      <h1>合成市场环境 <span class="mono" style="font-size:15px;color:var(--text-3)">${esc(env.dataset)} · v${esc(env.version)}</span></h1>
      <p class="sub">确定性生成器（seed ${env.seed}，generator v${esc(env.generator_version)}）：${env.product_count} 商品 · ${env.review_count} 评审 · ${env.source_count} 来源</p>
    </div>
    <div class="note">${esc(env.note)}</div>

    <h2 class="section">证据面（sources_v2 · 面向 Agent 的检索切面）</h2>
    <div class="card">
      <div class="chip-row">
        ${env.evidence_facets.map((facet) => `<span class="chip">${esc(facet)}</span>`).join("")}
      </div>
      <p class="card-hint" style="margin:10px 0 0">每个类目 8 个切面来源：broad / constraints / performance / price / reliability / downside / uncertainty / distractor。其中 distractor 是刻意的干扰项，用于检验 Agent 的甄别能力。</p>
    </div>

    <h2 class="section">类目概览</h2>
    <div class="grid cols-4">
      ${env.categories.map((category) => `
        <div class="card" style="margin-bottom:0">
          <h3>${esc(category.category)}</h3>
          <div class="score-line"><div class="name">商品数</div><div class="track"></div><div class="val">${category.product_count}</div></div>
          <div class="score-line"><div class="name">平均毛利</div>
            <div class="track"><div class="fill" style="width:${category.mean_gross_margin * 100}%"></div></div>
            <div class="val">${fmtPct(category.mean_gross_margin)}</div></div>
          <div class="score-line"><div class="name">平均机会分</div>
            <div class="track"><div class="fill" style="width:${category.mean_opportunity * 100}%;background:var(--accent)"></div></div>
            <div class="val">${fmtFixed(category.mean_opportunity, 2)}</div></div>
          <div class="chip-row" style="margin-top:8px">
            ${Object.entries(category.regimes).slice(0, 4).map(([regime, count]) => `<span class="chip">${esc(regime)}×${count}</span>`).join("")}
          </div>
          <p class="card-hint" style="margin:8px 0 4px">机会分最高的商品（可观测）</p>
          ${category.top_products.map((product) => `
            <div style="font-size:12px;margin-bottom:4px">
              <strong>${esc(product.title)}</strong>
              <span class="dim">· ${esc(product.brand)}</span>
              <span class="pill pill-teal" style="margin-left:4px">${fmtFixed(product.opportunity_score, 2)}</span>
            </div>`).join("")}
          <button class="btn subtle sm" data-category="${esc(category.category)}" style="margin-top:8px">查看全部商品 →</button>
        </div>`).join("")}
    </div>

    <h2 class="section">商品明细</h2>
    <div class="card">
      <div class="filters">
        <select id="prod-category">
          <option value="">全部类目</option>
          ${env.categories.map((category) => `<option>${esc(category.category)}</option>`).join("")}
        </select>
        <select id="prod-sort">
          <option value="opportunity_score">按机会分排序</option>
          <option value="gross_margin">按毛利排序</option>
          <option value="selling_price">按售价排序</option>
          <option value="demand_score">按需求分排序</option>
          <option value="risk_score">按风险分排序</option>
          <option value="monthly_search_volume">按月搜索量排序</option>
        </select>
        <input type="text" id="prod-query" placeholder="搜索标题 / 品牌…">
        <span class="chip" id="prod-count"></span>
      </div>
      <div class="table-wrap"><table class="data" id="prod-table"><tbody><tr><td class="loading">加载中…</td></tr></tbody></table></div>
    </div>
  `;

  const categorySelect = container.querySelector("#prod-category");
  const sortSelect = container.querySelector("#prod-sort");
  const queryInput = container.querySelector("#prod-query");
  categorySelect.addEventListener("change", loadProducts);
  sortSelect.addEventListener("change", loadProducts);
  queryInput.addEventListener("input", () => drawProducts());
  container.querySelectorAll("[data-category]").forEach((button) => {
    button.addEventListener("click", () => {
      categorySelect.value = button.dataset.category;
      loadProducts();
      container.querySelector("#prod-table").scrollIntoView({ behavior: "smooth" });
    });
  });

  let cache = { products: [] };
  await loadProducts();

  async function loadProducts() {
    const table = container.querySelector("#prod-table");
    table.innerHTML = `<tbody><tr><td class="loading">加载商品…</td></tr></tbody>`;
    try {
      const params = new URLSearchParams({ sort: sortSelect.value, limit: "300" });
      if (categorySelect.value) params.set("category", categorySelect.value);
      cache = await getJSON(`/api/environment/products?${params.toString()}`);
      drawProducts();
    } catch (error) {
      table.innerHTML = `<tbody><tr><td><div class="error-box">${esc(error.message)}</div></td></tr></tbody>`;
    }
  }

  function drawProducts() {
    const table = container.querySelector("#prod-table");
    const query = queryInput.value.trim().toLowerCase();
    const rows = cache.products.filter((product) => {
      if (!query) return true;
      return `${product.title} ${product.brand} ${product.subcategory}`.toLowerCase().includes(query);
    });
    container.querySelector("#prod-count").textContent = `${rows.length} / ${cache.products.length}`;
    table.innerHTML = `
      <thead><tr>
        <th>商品</th><th>品牌</th><th>子类</th><th>阶段</th>
        <th class="num">售价</th><th class="num">毛利</th>
        <th class="num">需求</th><th class="num">竞争</th><th class="num">风险</th><th class="num">机会</th>
        <th class="num">月搜索</th><th>标签</th>
      </tr></thead>
      <tbody>${rows.map((product) => `
        <tr>
          <td style="max-width:250px"><strong>${esc(product.title)}</strong></td>
          <td class="dim">${esc(product.brand)}</td>
          <td class="dim">${esc(product.subcategory)}</td>
          <td><span class="pill pill-muted">${esc(product.regime)}</span></td>
          <td class="num">$${fmtFixed(product.selling_price, 2)}</td>
          <td class="num">${fmtPct(product.gross_margin)}</td>
          <td class="num">${fmtFixed(product.demand_score, 2)}</td>
          <td class="num">${fmtFixed(product.competition_score, 2)}</td>
          <td class="num">${fmtFixed(product.risk_score, 2)}</td>
          <td class="num"><strong>${fmtFixed(product.opportunity_score, 2)}</strong></td>
          <td class="num">${fmtNum(product.monthly_search_volume)}</td>
          <td>${[
            product.battery ? '<span class="chip">电池</span>' : "",
            product.fragile ? '<span class="chip">易碎</span>' : "",
            product.liquid ? '<span class="chip">液体</span>' : "",
            product.oversize ? '<span class="chip">超尺寸</span>' : "",
          ].join(" ")}</td>
        </tr>`).join("")}
      </tbody>`;
  }

  function fmtPct(value) {
    return `${(value * 100).toFixed(1)}%`;
  }
}
