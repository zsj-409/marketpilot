// Hand-rolled SVG chart builders (no external dependencies).

const NS = "http://www.w3.org/2000/svg";

export function svgEl(tag, attrs = {}, children = []) {
  const node = document.createElementNS(NS, tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value === null || value === undefined) continue;
    node.setAttribute(key, String(value));
  }
  for (const child of children) node.appendChild(child);
  return node;
}

const PALETTE = ["#4f6df5", "#0e9f8d", "#d97706", "#7c3aed", "#dc2626", "#2563eb", "#0d9488", "#b45309"];

export class ChartColors {
  static get(i) { return PALETTE[i % PALETTE.length]; }
}

/* ------------------------------------------------------------------ */
/* Task DAG: layered layout, colored by status, clickable nodes.       */
/* ------------------------------------------------------------------ */

const NODE_W = 188;
const NODE_H = 56;
const GAP_X = 66;
const GAP_Y = 22;
const PAD = 18;

export function dagChart(tasks, { selectedId = null, onSelect = null } = {}) {
  const byId = new Map(tasks.map((task) => [String(task.task_id), task]));
  const levels = new Map();
  const levelOf = (id) => {
    if (levels.has(id)) return levels.get(id);
    const task = byId.get(id);
    let level = 0;
    if (task && task.dependencies && task.dependencies.length) {
      level = Math.max(...task.dependencies.map((dep) => levelOf(String(dep)) + 1));
    }
    levels.set(id, level);
    return level;
  };
  tasks.forEach((task) => levelOf(String(task.task_id)));

  const columns = new Map();
  tasks.forEach((task) => {
    const level = levels.get(String(task.task_id));
    if (!columns.has(level)) columns.set(level, []);
    columns.get(level).push(task);
  });

  const ordered = [...columns.keys()].sort((a, b) => a - b);
  const maxRows = Math.max(...ordered.map((level) => columns.get(level).length));
  const width = PAD * 2 + ordered.length * NODE_W + (ordered.length - 1) * GAP_X;
  const height = PAD * 2 + maxRows * NODE_H + Math.max(maxRows - 1, 0) * GAP_Y;

  const positions = new Map();
  ordered.forEach((level, colIndex) => {
    const columnTasks = columns.get(level);
    const columnHeight = columnTasks.length * NODE_H + (columnTasks.length - 1) * GAP_Y;
    const startY = (height - columnHeight) / 2;
    columnTasks.forEach((task, rowIndex) => {
      positions.set(String(task.task_id), {
        x: PAD + colIndex * (NODE_W + GAP_X),
        y: startY + rowIndex * (NODE_H + GAP_Y),
      });
    });
  });

  const svg = svgEl("svg", {
    viewBox: `0 0 ${width} ${height}`,
    width, height, class: "chart-svg", role: "img",
  });

  // Edges first (under nodes).
  for (const task of tasks) {
    for (const dep of task.dependencies || []) {
      const from = positions.get(String(dep));
      const to = positions.get(String(task.task_id));
      if (!from || !to) continue;
      const x1 = from.x + NODE_W;
      const y1 = from.y + NODE_H / 2;
      const x2 = to.x;
      const y2 = to.y + NODE_H / 2;
      const midX = (x1 + x2) / 2;
      svg.appendChild(svgEl("path", {
        d: `M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`,
        class: "dag-edge",
      }));
    }
  }

  const statusColor = { SUCCEEDED: "#16a34a", COMPLETED: "#16a34a", FAILED: "#dc2626", RUNNING: "#2563eb", READY: "#d97706", PENDING: "#94a3b8", BLOCKED: "#cbd5e1", CANCELLED: "#94a3b8" };
  const roleLabels = {
    MARKET_RESEARCH: "市场调研", PRODUCT_RESEARCH: "商品调研", REVIEW_MINING: "评论挖掘",
    COMPETITOR_RESEARCH: "竞品调研", RISK_ANALYSIS: "风险分析", DECISION: "决策",
    EVIDENCE_VERIFIER: "证据校验", RESEARCH_MANAGER: "研究管理",
  };

  for (const task of tasks) {
    const id = String(task.task_id);
    const pos = positions.get(id);
    const group = svgEl("g", { class: `dag-node${selectedId === id ? " selected" : ""}` });
    group.appendChild(svgEl("rect", {
      class: "dag-box", x: pos.x, y: pos.y, width: NODE_W, height: NODE_H,
      fill: "#ffffff", stroke: statusColor[task.status] || "#94a3b8",
      "stroke-width": 1.5,
    }));
    group.appendChild(svgEl("circle", {
      cx: pos.x + 16, cy: pos.y + 18, r: 5,
      fill: statusColor[task.status] || "#94a3b8",
    }));
    const typeLabel = svgEl("text", { x: pos.x + 29, y: pos.y + 22, "font-weight": 600, "font-size": 12.5, fill: "#1c2740" });
    typeLabel.textContent = roleLabels[task.assigned_role] || task.task_type;
    group.appendChild(typeLabel);
    const statusLabel = svgEl("text", { x: pos.x + 16, y: pos.y + 41, "font-size": 11, fill: "#5a6b85" });
    statusLabel.textContent = `${task.status} · ${task.attempt_count ?? 0} 次尝试`;
    group.appendChild(statusLabel);
    if (onSelect) {
      group.addEventListener("click", () => onSelect(id, task));
    }
    svg.appendChild(group);
  }
  return svg;
}

/* ------------------------------------------------------------------ */
/* Radar chart for recommendation scores.                              */
/* ------------------------------------------------------------------ */

export function radarChart(axes, values, { size = 300 } = {}) {
  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 44;
  const svg = svgEl("svg", { viewBox: `0 0 ${size} ${size}`, width: size, height: size, class: "chart-svg" });

  const angleOf = (i) => (Math.PI * 2 * i) / axes.length - Math.PI / 2;
  const pointAt = (i, ratio) => [
    cx + Math.cos(angleOf(i)) * radius * ratio,
    cy + Math.sin(angleOf(i)) * radius * ratio,
  ];

  for (const ring of [0.25, 0.5, 0.75, 1.0]) {
    svg.appendChild(svgEl("polygon", {
      points: axes.map((_, i) => pointAt(i, ring).join(",")).join(" "),
      fill: "none", stroke: "#e3e8f0", "stroke-width": 1,
    }));
  }
  for (let i = 0; i < axes.length; i += 1) {
    const [x, y] = pointAt(i, 1);
    svg.appendChild(svgEl("line", { x1: cx, y1: cy, x2: x, y2: y, stroke: "#e3e8f0", "stroke-width": 1 }));
  }

  const valueByKey = new Map(values.map((item) => [item.key, item.value]));
  const points = axes.map((axis, i) => pointAt(i, Math.max(0.04, Math.min(1, valueByKey.get(axis.key) ?? 0))));
  svg.appendChild(svgEl("polygon", {
    points: points.map((p) => p.join(",")).join(" "),
    fill: "rgba(14,159,141,0.22)", stroke: "#0e9f8d", "stroke-width": 2,
  }));
  for (const [x, y] of points) {
    svg.appendChild(svgEl("circle", { cx: x, cy: y, r: 3.2, fill: "#0e9f8d" }));
  }

  axes.forEach((axis, i) => {
    const [x, y] = pointAt(i, 1.17);
    const label = svgEl("text", {
      x, y, "text-anchor": Math.abs(x - cx) < 12 ? "middle" : x > cx ? "start" : "end",
      "dominant-baseline": "middle", "font-size": 10.5, fill: "#5a6b85",
    });
    label.textContent = axis.label;
    svg.appendChild(label);
  });
  return svg;
}

/* ------------------------------------------------------------------ */
/* Donut chart with legend.                                            */
/* ------------------------------------------------------------------ */

export function donutChart(items, { size = 190, centerLabel = "" } = {}) {
  const total = items.reduce((sum, item) => sum + item.value, 0);
  const svg = svgEl("svg", { viewBox: `0 0 ${size} ${size}`, width: size, height: size, class: "chart-svg" });
  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 12;
  const inner = radius * 0.62;

  if (!total) {
    svg.appendChild(svgEl("circle", { cx, cy, r: radius, fill: "none", stroke: "#e3e8f0", "stroke-width": radius - inner }));
    const label = svgEl("text", { x: cx, y: cy, "text-anchor": "middle", "dominant-baseline": "middle", "font-size": 12, fill: "#8794ab" });
    label.textContent = "无失败";
    svg.appendChild(label);
    return svg;
  }

  let angle = -Math.PI / 2;
  for (const [index, item] of items.entries()) {
    const sweep = (item.value / total) * Math.PI * 2;
    const end = angle + sweep;
    const large = sweep > Math.PI ? 1 : 0;
    const [x1, y1] = [cx + Math.cos(angle) * radius, cy + Math.sin(angle) * radius];
    const [x2, y2] = [cx + Math.cos(end) * radius, cy + Math.sin(end) * radius];
    const [x3, y3] = [cx + Math.cos(end) * inner, cy + Math.sin(end) * inner];
    const [x4, y4] = [cx + Math.cos(angle) * inner, cy + Math.sin(angle) * inner];
    svg.appendChild(svgEl("path", {
      d: `M ${x1} ${y1} A ${radius} ${radius} 0 ${large} 1 ${x2} ${y2} L ${x3} ${y3} A ${inner} ${inner} 0 ${large} 0 ${x4} ${y4} Z`,
      fill: item.color || ChartColors.get(index), opacity: 0.92,
    }));
    angle = end;
  }
  const totalLabel = svgEl("text", { x: cx, y: cy - 4, "text-anchor": "middle", "font-size": 17, "font-weight": 700, fill: "#1c2740" });
  totalLabel.textContent = String(total);
  svg.appendChild(totalLabel);
  const subLabel = svgEl("text", { x: cx, y: cy + 15, "text-anchor": "middle", "font-size": 10.5, fill: "#8794ab" });
  subLabel.textContent = centerLabel || "总数";
  svg.appendChild(subLabel);
  return svg;
}

/* ------------------------------------------------------------------ */
/* Grouped columns for experiment comparison.                          */
/* ------------------------------------------------------------------ */

export function groupedColumns(groups, series, { width = 640, height = 230, unit = "" } = {}) {
  // groups: [{label}], series: [{name, color, values: [number|null]}]
  const pad = { top: 16, right: 12, bottom: 40, left: 12 };
  const innerW = width - pad.left - pad.right;
  const innerH = height - pad.top - pad.bottom;
  const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, width: "100%", class: "chart-svg" });

  const maxValue = Math.max(
    1e-9,
    ...series.flatMap((s) => s.values.filter((v) => v !== null && Number.isFinite(v)).map(Math.abs)),
  );

  const groupW = innerW / Math.max(groups.length, 1);
  const barW = Math.min(30, (groupW * 0.72) / Math.max(series.length, 1));

  // Baseline.
  svg.appendChild(svgEl("line", {
    x1: pad.left, y1: pad.top + innerH, x2: width - pad.right, y2: pad.top + innerH,
    stroke: "#cdd5e1", "stroke-width": 1,
  }));

  groups.forEach((group, gi) => {
    const gx = pad.left + gi * groupW;
    const groupCenter = gx + groupW / 2;
    const totalW = barW * series.length + (series.length - 1) * 4;
    series.forEach((s, si) => {
      const value = s.values[gi];
      if (value === null || value === undefined || !Number.isFinite(value)) return;
      const barH = Math.max(2, (Math.abs(value) / maxValue) * (innerH - 8));
      const x = groupCenter - totalW / 2 + si * (barW + 4);
      svg.appendChild(svgEl("rect", {
        x, y: pad.top + innerH - barH, width: barW, height: barH,
        rx: 3, fill: s.color || ChartColors.get(si), opacity: 0.9,
      }));
      const valueLabel = svgEl("text", {
        x: x + barW / 2, y: pad.top + innerH - barH - 4, "text-anchor": "middle",
        "font-size": 9.5, fill: "#5a6b85",
      });
      valueLabel.textContent = formatValue(value);
      svg.appendChild(valueLabel);
    });
    const groupLabel = svgEl("text", {
      x: groupCenter, y: pad.top + innerH + 16, "text-anchor": "middle",
      "font-size": 11, fill: "#5a6b85",
    });
    groupLabel.textContent = group.label;
    svg.appendChild(groupLabel);
  });
  return svg;

  function formatValue(value) {
    if (unit === "%") return `${(value * 100).toFixed(1)}%`;
    return Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(3);
  }
}

/* ------------------------------------------------------------------ */
/* Sparkline for trend data.                                           */
/* ------------------------------------------------------------------ */

export function sparkline(points, { width = 120, height = 30, color = "#4f6df5" } = {}) {
  if (!points.length) return svgEl("svg", { viewBox: `0 0 ${width} ${height}`, width, height });
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const step = width / Math.max(points.length - 1, 1);
  const coords = points.map((value, i) => [i * step, height - 3 - ((value - min) / span) * (height - 6)]);
  const path = coords.map(([x, y], i) => `${i ? "L" : "M"} ${x.toFixed(1)} ${y.toFixed(1)}`).join(" ");
  return svgEl("svg", { viewBox: `0 0 ${width} ${height}`, width, height, class: "chart-svg" }, [
    svgEl("path", { d: path, fill: "none", stroke: color, "stroke-width": 1.8, "stroke-linejoin": "round" }),
    svgEl("circle", { cx: coords[coords.length - 1][0], cy: coords[coords.length - 1][1], r: 2.6, fill: color }),
  ]);
}
