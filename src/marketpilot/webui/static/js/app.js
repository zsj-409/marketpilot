// SPA router: hash-based, static imports of all views.

import { esc } from "./format.js";
import * as overview from "./views/overview.js";
import * as runs from "./views/runs.js";
import * as runDetail from "./views/runDetail.js";
import * as experiments from "./views/experiments.js";
import * as experimentDetail from "./views/experimentDetail.js";
import * as compare from "./views/compare.js";
import * as environment from "./views/environment.js";
import * as workbench from "./views/workbench.js";

const routes = [
  { pattern: /^#\/$/, view: overview.render, nav: "#/" },
  { pattern: /^#\/runs\/([\w-]+)$/, view: runDetail.render, nav: "#/runs", params: (match) => ({ id: match[1] }) },
  { pattern: /^#\/runs$/, view: runs.render, nav: "#/runs" },
  { pattern: /^#\/experiments\/([\w-]+)$/, view: experimentDetail.render, nav: "#/experiments", params: (match) => ({ id: match[1] }) },
  { pattern: /^#\/experiments$/, view: experiments.render, nav: "#/experiments" },
  { pattern: /^#\/compare$/, view: compare.render, nav: "#/compare" },
  { pattern: /^#\/environment$/, view: environment.render, nav: "#/environment" },
  { pattern: /^#\/workbench$/, view: workbench.render, nav: "#/workbench" },
];

const page = document.getElementById("page");

async function route() {
  const hash = location.hash || "#/";
  const match = routes.find((route_) => route_.pattern.test(hash));
  document.querySelectorAll("#nav a").forEach((link) => {
    link.classList.toggle("active", match ? link.dataset.route === match.nav : false);
  });
  if (!match) {
    page.innerHTML = `
      <div class="empty" style="margin-top:60px">
        <p style="font-size:15px;margin:0 0 6px">页面不存在：${esc(hash)}</p>
        <a href="#/">← 返回总览</a>
      </div>`;
    return;
  }
  const params = match.params ? match.params(hash.match(match.pattern)) : {};
  try {
    await match.view(page, params);
  } catch (error) {
    page.insertAdjacentHTML("beforeend", `<div class="error-box">页面渲染出错：${esc(error.message)}</div>`);
  }
  window.scrollTo(0, 0);
}

window.addEventListener("hashchange", route);
route();
