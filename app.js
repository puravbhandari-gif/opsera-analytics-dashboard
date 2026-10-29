"use strict";

// ---------- small helpers ----------

const $ = (id) => document.getElementById(id);
const nf = new Intl.NumberFormat("en-US");
const num = (v) => (v == null ? "-" : nf.format(Math.round(v)));
const pct = (v, d = 2) => (v == null ? "-" : `${v.toFixed(d)}%`);
const spot = (v) => (v == null ? "-" : v.toFixed(1));
const toDate = (s) => new Date(`${s}T00:00:00Z`);
const iso = (d) => d.toISOString().slice(0, 10);
const addDays = (s, n) => { const d = toDate(s); d.setUTCDate(d.getUTCDate() + n); return iso(d); };
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const day = (s) => { const d = toDate(s); return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}`; };
const dayYear = (s) => `${day(s)} ${toDate(s).getUTCFullYear()}`;
const range = (a, b) => (a === b ? dayYear(a) : a.slice(0, 7) === b.slice(0, 7) ? `${toDate(a).getUTCDate()} to ${dayYear(b)}` : `${day(a)} to ${dayYear(b)}`);
const month = (m) => toDate(`${m}-01`).toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
const shortPage = (p) => p.replace(/^https?:\/\/(www\.)?opsera\.ai/, "") || "/";
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const loaded = {};   // each data file is fetched once, even when 2 tabs use it
function load(name) {
  if (!loaded[name]) loaded[name] = fetch(`data/${name}`, { cache: "no-cache" }).then((r) => {
    if (!r.ok) throw new Error(`Couldn't load data/${name} (${r.status})`);
    return r.json();
  });
  return loaded[name];
}

// Key numbers count up to their value when shown. Off for anyone who has asked their device for less motion.
const calm = matchMedia("(prefers-reduced-motion: reduce)");
let countRun = 0;
function countUp(root) {
  if (calm.matches || !root) return;
  root.querySelectorAll(".value").forEach((el) => {
    const final = el.textContent;
    const m = final.match(/^([^\d]*?)(\d[\d,]*(?:\.\d+)?)(.*)$/);
    if (!m) return;
    const target = Number(m[2].replace(/,/g, ""));
    if (!target) return;
    const dec = (m[2].split(".")[1] || "").length;
    const show = (v) => m[1] + (m[2].includes(",") ? v.toLocaleString("en-US", { minimumFractionDigits: dec, maximumFractionDigits: dec }) : v.toFixed(dec)) + m[3];
    const run = String(++countRun), t0 = performance.now();
    el.dataset.run = run; el.setAttribute("aria-label", final);
    const tick = (now) => {
      if (!el.isConnected || el.dataset.run !== run) return;
      const k = Math.min(1, (now - t0) / 700);
      el.textContent = k < 1 ? show(target * (1 - (1 - k) ** 3)) : final;
      if (k < 1) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
}

function card(label, value, sub = "", extra = "") {
  return `<div class="card"><div class="label">${label}</div><div class="value">${value}</div>${extra}${sub ? `<div class="sub">${sub}</div>` : ""}</div>`;
}

// ---------- tables: sortable and searchable ----------

function table(el, { columns, rows, search, sortKey, sortDir = -1, pageSize = 25 }) {
  let q = "", key = sortKey, dir = sortDir, shown = pageSize;
  el.innerHTML = `<div class="table-tools">${search ? `<input type="search" placeholder="Search ${search}" aria-label="Search ${search}"><span class="muted"></span>` : ""}<button class="ghost csv" type="button">Download CSV</button></div>
    <div class="table-wrap"><table><thead><tr>${columns.map((c) =>
      `<th class="${c.num ? "num " : ""}${c.sort === false ? "" : "sortable"}" data-k="${c.key}" scope="col">${c.label}</th>`).join("")}</tr></thead><tbody></tbody></table></div>
    <button class="more" type="button" hidden>Show more</button>`;
  const body = el.querySelector("tbody"), more = el.querySelector(".more"), count = el.querySelector(".table-tools .muted");

  let list = rows;
  function render() {
    list = rows.filter((r) => !q || columns.some((c) => c.search && String(r[c.key]).toLowerCase().includes(q)));
    if (key) list = [...list].sort((a, b) => {
      const x = a[key], y = b[key];
      if (x == null) return 1; if (y == null) return -1;
      return (typeof x === "number" ? x - y : String(x).localeCompare(String(y))) * dir;
    });
    body.innerHTML = list.slice(0, shown).map((r) => `<tr>${columns.map((c) =>
      `<td class="${c.num ? "num" : "wrap"}">${c.fmt ? c.fmt(r[c.key], r) : esc(r[c.key])}</td>`).join("")}</tr>`).join("")
      || `<tr><td colspan="${columns.length}" class="muted">Nothing matches.</td></tr>`;
    more.hidden = list.length <= shown;
    if (count) count.textContent = `${num(Math.min(shown, list.length))} of ${num(list.length)} rows`;
    el.querySelectorAll("th").forEach((th) => {
      th.removeAttribute("aria-sort");
      if (th.dataset.k === key) th.setAttribute("aria-sort", dir > 0 ? "ascending" : "descending");
      th.textContent = columns.find((c) => c.key === th.dataset.k).label + (th.dataset.k === key ? (dir > 0 ? " (low to high)" : " (high to low)") : "");
    });
  }
  el.querySelectorAll("th.sortable").forEach((th) => th.addEventListener("click", () => {
    dir = key === th.dataset.k ? -dir : (columns.find((c) => c.key === th.dataset.k).num ? -1 : 1);
    key = th.dataset.k; render();
  }));
  const input = el.querySelector("input");
  if (input) input.addEventListener("input", () => { q = input.value.trim().toLowerCase(); shown = pageSize; render(); });
  more.addEventListener("click", () => { shown += pageSize * 4; render(); });
  // the rows as the table has them (search and sort applied), every row, not just the ones on screen
  el.querySelector(".csv").addEventListener("click", () => {
    const text = (h) => { const div = document.createElement("div"); div.innerHTML = String(h ?? "").replace(/<br\s*\/?>/gi, " | "); return div.textContent.trim(); };
    const cell = (c, r) => {
      if (c.csv) return c.csv(r);
      const v = r[c.key];
      if (c.num && typeof v === "number") return Number.isInteger(v) ? v : Math.round(v * 100) / 100;
      return text(c.fmt ? c.fmt(v, r) : v);
    };
    const quote = (v) => (/[",\n]/.test(String(v)) ? `"${String(v).replace(/"/g, '""')}"` : String(v));
    const csv = [columns.map((c) => quote(text(c.label) || "Measure")), ...list.map((r) => columns.map((c) => quote(cell(c, r))))].map((l) => l.join(",")).join("\n");
    const heading = el.closest(".panel, section")?.querySelector("h3, h2")?.textContent || el.id;
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob(["\ufeff" + csv], { type: "text/csv;charset=utf-8" }));
    a.download = `opsera-${heading.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "table"}.csv`;
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
  });
  render();
}

// ---------- charts: rebuilt when the theme changes ----------

const charts = [];
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
Chart.defaults.font.family = '"DM Sans", ui-sans-serif, system-ui, sans-serif';
Chart.defaults.font.size = 10.8;   // 10% smaller than Chart.js's 12, like the rest of the page

function chart(id, build) {
  charts.push({ id, build });
  draw(charts[charts.length - 1]);
}
function draw(c) {
  if (c.instance) c.instance.destroy();
  const t = { ink: css("--ink-2"), muted: css("--muted"), grid: css("--grid"), axis: css("--axis"), surface: css("--surface"),
    s: [css("--s1"), css("--s2"), css("--s3"), css("--s4"), css("--s5")] };
  const cfg = c.build(t);
  const base = {
    responsive: true, maintainAspectRatio: false, animation: false,
    interaction: { mode: "index", intersect: false },
    plugins: {
      legend: { display: cfg.data.datasets.length > 1, position: "top", align: "start",
        labels: { color: t.ink, boxWidth: 12, boxHeight: 12, useBorderRadius: true, borderRadius: 2, font: { size: 10.8 } } },
      tooltip: { backgroundColor: t.surface, titleColor: t.ink, bodyColor: t.ink, borderColor: t.axis, borderWidth: 1, padding: 10,
        callbacks: cfg.tooltip || {} },
    },
    scales: {
      x: { stacked: cfg.stacked, grid: { display: false }, border: { color: t.axis }, ticks: { color: t.muted, maxRotation: 0, autoSkipPadding: 12 } },
      y: { stacked: cfg.stacked, beginAtZero: cfg.reverse ? false : true, reverse: !!cfg.reverse, grid: { color: t.grid }, border: { display: false },
        ticks: { color: t.muted, precision: cfg.whole ? 0 : undefined, callback: cfg.yfmt || ((v) => nf.format(v)) },
        title: cfg.ytitle ? { display: true, text: cfg.ytitle, color: t.muted } : undefined },
    },
  };
  if (cfg.horizontal) {
    base.indexAxis = "y";
    base.interaction = { mode: "nearest", axis: "y", intersect: false };
    base.scales = { x: { ...base.scales.y, reverse: false }, y: { grid: { display: false }, border: { color: t.axis }, ticks: { color: t.ink } } };
  }
  if (cfg.dates) {   // [start, end] for each label, so calendar markers can find their spot
    base.plugins.gtm = { dates: cfg.dates, color: css("--accent"), line: t.muted };
    base.layout = { padding: { bottom: 16 } };
  }
  c.instance = new Chart($(c.id), { type: cfg.type, data: cfg.data, options: base, plugins: [gtmMarkers] });
}

const line = (label, data, color) => ({ label, data, borderColor: color, backgroundColor: color, borderWidth: 2, pointRadius: 0, pointHoverRadius: 5, tension: 0.25 });
const bar = (label, data, color) => ({ label, data, backgroundColor: color, borderColor: css("--surface"), borderWidth: { top: 0, left: 0, right: 0, bottom: 0 }, borderRadius: 4, borderSkipped: "start", maxBarThickness: 44 });

// ---------- Week by week / month by month, one switch for every tab ----------

let periodMode = "week";
try { const saved = localStorage.getItem("period"); if (["day", "month", "quarter"].includes(saved)) periodMode = saved; } catch (e) {}

// The view lives in the address after "#", so a link opens the same view:
// #journey?period=month&channel=linkedin&funnelmonth=2026-08&person=…&type=blog&q=gartner
const PERIOD_IN_ADDRESS = { day: "day", week: "week", month: "month", quarter: "3months" };
const view = (() => {
  const [tab, query] = location.hash.slice(1).split("?");
  const a = new URLSearchParams(query || "");
  const period = Object.keys(PERIOD_IN_ADDRESS).find((k) => PERIOD_IN_ADDRESS[k] === a.get("period"));
  if (period) periodMode = period;   // a link's period wins over the one this browser last used
  return { tab: tab || "", channel: a.get("channel") || "all", funnelmonth: a.get("funnelmonth") || "", person: a.get("person") || "",
    type: a.get("type") || "all", q: a.get("q") || "", markers: a.get("markers") !== "off", mtype: a.get("mtype") || "all" };
})();
function viewAddress() {
  const a = new URLSearchParams({ period: PERIOD_IN_ADDRESS[periodMode] });
  if (view.channel !== "all") a.set("channel", view.channel);
  if (view.funnelmonth) a.set("funnelmonth", view.funnelmonth);
  if (view.person) a.set("person", view.person);
  if (view.type !== "all") a.set("type", view.type);
  if (view.q) a.set("q", view.q);
  if (!gtm.on) a.set("markers", "off");
  if (gtm.type !== "all") a.set("mtype", gtm.type);
  return `#${view.tab || "team"}?${a.toString()}`;
}
function saveView() { history.replaceState(null, "", viewAddress()); }

// ---------- GTM calendar markers: a small diamond under each dated chart, on each item's ship date ----------

const gtm = { items: [], on: view.markers, type: view.mtype, source: "" };
const gtmTip = document.createElement("div");
gtmTip.className = "gtm-tip"; gtmTip.hidden = true; gtmTip.setAttribute("role", "tooltip");
document.body.appendChild(gtmTip);
const gtmShown = () => (gtm.on ? gtm.items.filter((i) => gtm.type === "all" || i.types.includes(gtm.type)) : []);
const gtmWhen = (i) => (i.end ? range(i.date, i.end) : dayYear(i.date));
// Markers for one chart: one spot per label that has items, with every item that falls in it
function gtmSpots(chart) {
  const o = chart.options.plugins.gtm;
  if (!o || !o.dates) return [];
  const x = chart.scales.x, y = chart.chartArea.bottom + (x.height || 0) + 9, spots = [];
  o.dates.forEach(([a, b], i) => {
    const items = gtmShown().filter((it) => it.date >= a && it.date <= b);
    if (items.length) spots.push({ x: x.getPixelForValue(i), y, items });
  });
  return spots;
}
const gtmMarkers = {
  id: "gtm",
  afterDraw(chart) {
    const o = chart.options.plugins.gtm, spots = gtmSpots(chart);
    if (!spots.length) return;
    const ctx = chart.ctx, area = chart.chartArea;
    ctx.save();
    for (const s of spots) {
      if (chart.$gtmHover === s.x) {   // a faint line up through the chart for the marker under the mouse
        ctx.strokeStyle = o.color; ctx.globalAlpha = 0.5; ctx.setLineDash([3, 3]); ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(s.x, area.top); ctx.lineTo(s.x, area.bottom); ctx.stroke();
        ctx.setLineDash([]); ctx.globalAlpha = 1;
      }
      const r = s.items.length > 1 ? 5.5 : 4.5;
      ctx.fillStyle = o.color;
      ctx.beginPath(); ctx.moveTo(s.x, s.y - r); ctx.lineTo(s.x + r, s.y); ctx.lineTo(s.x, s.y + r); ctx.lineTo(s.x - r, s.y); ctx.closePath(); ctx.fill();
      if (s.items.length > 1) {
        ctx.fillStyle = o.line; ctx.font = '600 9px "DM Sans", sans-serif'; ctx.textBaseline = "middle";
        ctx.fillText(String(s.items.length), s.x + r + 3, s.y);
      }
    }
    ctx.restore();
  },
  afterEvent(chart, args) {
    const e = args.event;
    if (!["mousemove", "click", "mouseout"].includes(e.type)) return;
    const hit = e.type === "mouseout" ? null : gtmSpots(chart).find((s) => Math.abs(e.x - s.x) <= 8 && Math.abs(e.y - s.y) <= 10);
    const was = chart.$gtmHover;
    chart.$gtmHover = hit ? hit.x : null;
    if (was !== chart.$gtmHover) args.changed = true;
    if (!hit) { if (was != null) gtmTip.hidden = true; return; }
    gtmTip.innerHTML = hit.items.map((i) => `<div><strong>${esc(i.name)}</strong><span>${esc(i.types.join(", "))}. ${gtmWhen(i)}</span></div>`).join("") +
      `<p>Source: ${esc(gtm.source)}</p>`;
    gtmTip.hidden = false;
    const box = chart.canvas.getBoundingClientRect(), w = gtmTip.offsetWidth, h = gtmTip.offsetHeight;
    const left = Math.min(Math.max(8, box.left + hit.x - w / 2), document.documentElement.clientWidth - w - 8);
    const top = box.top + hit.y - h - 12;
    gtmTip.style.left = `${left + scrollX}px`;
    gtmTip.style.top = `${(top < 8 ? box.top + hit.y + 14 : top) + scrollY}px`;
  },
};
function redrawDated() { charts.forEach((c) => { if (c.instance?.options.plugins.gtm) c.instance.update("none"); }); }
function fillGtmControls() {
  const types = [...new Set(gtm.items.flatMap((i) => i.types))].sort();
  if (gtm.type !== "all" && !types.includes(gtm.type)) gtm.type = "all";
  $("gtm-type").innerHTML = `<option value="all">All types</option>` + types.map((t) => `<option${t === gtm.type ? " selected" : ""}>${esc(t)}</option>`).join("");
  $("gtm-type").disabled = !gtm.on;
  $("gtm-toggle").textContent = `Calendar markers: ${gtm.on ? "On" : "Off"}`;
  $("gtm-toggle").setAttribute("aria-pressed", String(gtm.on));
}
load("gtm_calendar.json").then((d) => {
  gtm.items = d.items;
  gtm.source = `${d.source}, pulled ${dayYear(d.pulled_at.slice(0, 10))}`;
  $("gtm-controls").hidden = false;
  fillGtmControls(); redrawDated();
}).catch(() => {});   // no calendar file yet: the charts show no markers
addEventListener("scroll", () => { gtmTip.hidden = true; }, { passive: true });
$("gtm-toggle").addEventListener("click", () => { gtm.on = !gtm.on; gtmTip.hidden = true; fillGtmControls(); redrawDated(); saveView(); });
$("gtm-type").addEventListener("change", () => { gtm.type = $("gtm-type").value; fillGtmControls(); redrawDated(); saveView(); });
const addMonths = (d, n) => { const x = toDate(d); const day0 = x.getUTCDate(); x.setUTCDate(1); x.setUTCMonth(x.getUTCMonth() + n);
  x.setUTCDate(Math.min(day0, toDate(monthEnd(iso(x))).getUTCDate())); return iso(x); };
// Last 3 months: the 3 months up to the last full day, against the 3 months before
const quarterOf = (last) => ({ start: addDays(addMonths(last, -3), 1), end: last });
const comparisons = [];
const MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
const weekStart = (d) => addDays(d, -((toDate(d).getUTCDay() + 6) % 7));
const monthStart = (d) => `${d.slice(0, 7)}-01`;
const monthEnd = (d) => { const x = toDate(monthStart(d)); x.setUTCMonth(x.getUTCMonth() + 1); x.setUTCDate(0); return iso(x); };
const monthName = (d) => MONTH_NAMES[toDate(d).getUTCMonth()];
const lastFullDayPacific = (end, pulledAt) => {   // Google Analytics days follow US Pacific time
  const pt = new Date(pulledAt).toLocaleDateString("en-CA", { timeZone: "America/Los_Angeles" });
  return pt > end ? end : addDays(end, -1);
};

// The two periods each tab compares: the last full Monday-to-Sunday week against the week before,
// or this month so far against the whole of last month.
function periodsFor(mode, start, last) {
  if (mode === "quarter") {
    const cur = quarterOf(last);
    const prev = quarterOf(addDays(cur.start, -1));
    return { cur: cur.start >= start ? cur : { start, end: last }, prev: prev.start >= start ? prev : null,
      prevName: "3 months before", none: "No earlier 3 months yet" };
  }
  if (mode === "day") {
    const prev = addDays(last, -1);
    return { cur: { start: last, end: last }, prev: prev >= start ? { start: prev, end: prev } : null,
      prevName: "Day before", none: "No earlier day yet" };
  }
  if (mode === "week") {
    const curEnd = toDate(last).getUTCDay() === 0 ? last : addDays(weekStart(last), -1);
    const cur = { start: addDays(curEnd, -6), end: curEnd };
    const prev = { start: addDays(cur.start, -7), end: addDays(cur.start, -1) };
    return { cur: cur.start >= start ? cur : null, prev: prev.start >= start ? prev : null,
      prevName: "Week before", none: "No full week before this one yet" };
  }
  const cur = { start: monthStart(last), end: last };
  const pStart = monthStart(addDays(cur.start, -1));
  const prev = { start: pStart, end: monthEnd(pStart) };   // always the whole previous month
  return { cur, prev: prev.start >= start ? prev : null,
    prevName: `${monthName(pStart)}, full month`,
    none: `Comparison starts in ${MONTH_NAMES[(toDate(cur.start).getUTCMonth() + 1) % 12]}` };
}

// One bar per week or month from the start to the last full day, the last one marked "so far" if unfinished.
function periodBuckets(mode, start, last) {
  const out = [];
  if (mode === "quarter") {   // back from the last full day in 3-month blocks
    for (let q = quarterOf(last); q.end >= start; q = quarterOf(addDays(q.start, -1))) {
      const a = q.start < start ? start : q.start;
      out.unshift({ start: a, end: q.end, label: `${day(a)} to ${day(q.end)}${q.start < start ? " (part)" : ""}` });
    }
    return out;
  }
  for (let s = mode === "week" ? weekStart(start) : mode === "day" ? start : monthStart(start); s <= last;) {
    const e = mode === "week" ? addDays(s, 6) : mode === "day" ? s : monthEnd(s);
    const a = s < start ? start : s, b = e > last ? last : e;
    const label = mode === "day" ? day(a) : mode === "week" ? `${day(a)} to ${day(b)}` : `${monthName(s).slice(0, 3)} ${s.slice(0, 4)}`;
    out.push({ start: a, end: b, label: e > last ? `${label} (so far)` : label });
    s = addDays(e, 1);
  }
  return out;
}

function cmpDelta(cur, prev, lowerIsBetter) {
  if (cur == null || prev == null || !prev) return "";
  const change = ((cur - prev) / prev) * 100;
  if (Math.abs(change) < 0.05) return `<div class="delta flat">No change</div>`;
  const better = lowerIsBetter ? change < 0 : change > 0;
  return `<div class="delta ${better ? "good" : "bad"}">${change > 0 ? "+" : ""}${change.toFixed(1)}% (${better ? "better" : "worse"})</div>`;
}

// spec: { id, source, start, last, metrics: [{ label, value(a, b), fmt, lowerIsBetter, sub }], monthlyOnly }
function compare(spec) {
  comparisons.push(spec);
  spec.metricIndex = 0;
  const seg = $(`${spec.id}-cmp-metric`);
  if (seg && !spec.together) {
    seg.innerHTML = spec.metrics.length > 1 ? spec.metrics.map((m, i) => `<button data-i="${i}" class="${i ? "" : "on"}">${esc(m.label)}</button>`).join("") : "";
    seg.addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      spec.metricIndex = Number(b.dataset.i);
      seg.querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
      draw(charts.find((c) => c.id === `${spec.id}-cmp-chart`));
    });
  }
  if ($(`${spec.id}-cmp-chart`)) chart(`${spec.id}-cmp-chart`, (th) => {
    const m = spec.metrics[spec.metricIndex];
    const bk = periodBuckets(periodMode, spec.start, spec.last);
    if (spec.together) {
      return { type: "bar", whole: true, dates: bk.map((b) => [b.start, b.end]), data: { labels: bk.map((b) => b.label),
        datasets: spec.metrics.map((mm, i) => bar(mm.label, bk.map((b) => mm.value(b.start, b.end)), th.s[i])) } };
    }
    const values = bk.map((b) => m.value(b.start, b.end));
    const asLine = m.whole === false;
    return { type: asLine ? "line" : "bar", whole: m.whole !== false, yfmt: m.yfmt, dates: bk.map((b) => [b.start, b.end]), reverse: m.lowerIsBetter && m.flip,
      ytitle: m.lowerIsBetter && m.flip ? "Higher on the chart is a better spot" : undefined,
      data: { labels: bk.map((b) => b.label), datasets: [asLine ? { ...line(m.label, values, th.s[0]), pointRadius: 4 } : bar(m.label, values, th.s[0])] },
      tooltip: { label: (c) => ` ${m.label}: ${m.fmt(c.parsed.y ?? c.parsed.x)}` } };
  });
  fillCompare(spec);
}

function fillCompare(spec) {
  const p = periodsFor(periodMode, spec.start, spec.last);
  const title = $(`${spec.id}-cmp-chart`)?.closest(".panel").querySelector(".period-title");
  if (title) title.textContent = { day: "Day by day", week: "Week by week", month: "Month by month", quarter: "3 months at a time" }[periodMode];
  if (!p.cur) {
    $(`${spec.id}-cmp-cards`).innerHTML = `<div class="card"><div class="label">Not enough days yet</div><div class="sub">${p.none}</div></div>`;
    $(`${spec.id}-cmp-source`).textContent = spec.source(spec.start, spec.last);
  } else {
    $(`${spec.id}-cmp-cards`).innerHTML = spec.metrics.map((m) => {
      const cur = m.value(p.cur.start, p.cur.end), prev = p.prev ? m.value(p.prev.start, p.prev.end) : null;
      const sub = p.prev ? `${p.prevName}: ${m.fmt(prev)}` : p.none;
      const note = typeof m.sub === "function" ? m.sub(p.cur.start, p.cur.end) : m.sub;   // a note can depend on the period
      return card(m.label, m.fmt(cur), [sub, note].filter(Boolean).join(". "), cmpDelta(cur, prev, m.lowerIsBetter));
    }).join("");
    $(`${spec.id}-cmp-source`).textContent = spec.source(p.cur.start, p.cur.end) +
      (p.prev ? ` Compared with ${range(p.prev.start, p.prev.end)}.` : "");
  }
  if ($(`${spec.id}-cmp-chart-source`)) $(`${spec.id}-cmp-chart-source`).textContent = spec.source(spec.start, spec.last);
  if (!$(`${spec.id}-cmp-cards`).closest(".tab").hidden) countUp($(`${spec.id}-cmp-cards`));
}

function setPeriodMode(mode) {
  periodMode = mode;
  try { localStorage.setItem("period", mode); } catch (e) {}
  $("period-mode").querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));
  comparisons.forEach((spec) => { fillCompare(spec); const c = charts.find((x) => x.id === `${spec.id}-cmp-chart`); if (c) draw(c); });
  monthlyTabs.forEach((fn) => fn());
  saveView();   // last, after the funnel has let go of a picked month
}
const monthlyTabs = [];
$("period-mode").addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) setPeriodMode(b.dataset.mode); });
$("period-mode").querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.mode === periodMode));

// Sums over a run of daily rows, for any period.
const rangeSum = (rows, key) => (a, b) => rows.reduce((t, r) => (r.date >= a && r.date <= b ? t + (typeof key === "function" ? key(r) : r[key] || 0) : t), 0);

// ---------- Tab 1: Google Search ----------

function sumSearch(rows) {
  const clicks = rows.reduce((a, r) => a + r.clicks, 0);
  const shown = rows.reduce((a, r) => a + r.times_shown, 0);
  const spotW = rows.reduce((a, r) => a + r.avg_spot * r.times_shown, 0);
  return { clicks, shown, rate: shown ? (clicks / shown) * 100 : null, spot: shown ? spotW / shown : null };
}

function delta(cur, prev, lowerIsBetter = false) {
  if (prev == null || cur == null || prev === 0) return `<div class="delta flat">No earlier week to compare</div>`;
  const change = ((cur - prev) / prev) * 100;
  if (Math.abs(change) < 0.05) return `<div class="delta flat">No change from last week</div>`;
  const better = lowerIsBetter ? change < 0 : change > 0;
  return `<div class="delta ${better ? "good" : "bad"}">${change > 0 ? "+" : ""}${change.toFixed(1)}% on last week (${better ? "better" : "worse"})</div>`;
}

function renderSearch(d) {
  const last = d.last_day_with_data;
  const src = "Source: Google Search Console";
  $("search-source").textContent = `${src}, ${range(d.start_date, last)}.`;
  const t = sumSearch(d.daily);
  $("search-cards").innerHTML =
    card("Clicks", num(t.clicks)) +
    card("Times Google showed us", num(t.shown)) +
    card("Click rate", pct(t.rate), "Clicks divided by times shown") +
    card("Average spot on Google", spot(t.spot), "Lower is better");

  $("search-daily-source").textContent = `${src}, ${range(d.start_date, last)}.`;
  const metrics = {
    clicks: { label: "Clicks", fmt: num },
    times_shown: { label: "Times Google showed us", fmt: num },
    click_rate_pct: { label: "Click rate", fmt: (v) => pct(v), yfmt: (v) => `${v}%` },
    avg_spot: { label: "Average spot on Google", fmt: spot, reverse: true },
  };
  let m = "clicks";
  chart("search-daily", (th) => ({
    type: "line", dates: d.daily.map((r) => [r.date, r.date]), 
    data: { labels: d.daily.map((r) => day(r.date)), datasets: [line(metrics[m].label, d.daily.map((r) => r[m]), th.s[0])] },
    reverse: metrics[m].reverse, yfmt: metrics[m].yfmt, ytitle: metrics[m].reverse ? "Higher on the chart is a better spot" : undefined,
    tooltip: { label: (c) => ` ${metrics[m].label}: ${metrics[m].fmt(c.parsed.y)}` },
  }));
  $("search-metric").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    m = b.dataset.m;
    $("search-metric").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    draw(charts.find((c) => c.id === "search-daily"));
  });

  const cols = (first) => [
    first,
    { key: "clicks", label: "Clicks", num: true, fmt: num },
    { key: "times_shown", label: "Times shown", num: true, fmt: num },
    { key: "click_rate_pct", label: "Click rate", num: true, fmt: (v) => pct(v) },
    { key: "avg_spot", label: "Average spot", num: true, fmt: spot },
  ];
  $("search-pages-source").textContent = `${src}, ${range(d.start_date, last)}.`;
  table($("search-pages"), {
    rows: d.pages.map((p) => ({ ...p, path: shortPage(p.page) })), search: "pages", sortKey: "clicks",
    columns: cols({ key: "path", label: "Page", search: true, fmt: (v) => esc(v) }),
  });
  $("search-queries-source").textContent = `${src}, ${range(d.start_date, last)}.`;
  table($("search-queries"), { rows: d.searches, search: "searches", sortKey: "clicks",
    columns: cols({ key: "search", label: "Search", search: true }) });

  const clicks = rangeSum(d.daily, "clicks"), shown = rangeSum(d.daily, "times_shown");
  const spotWeight = rangeSum(d.daily, (r) => r.avg_spot * r.times_shown);
  compare({ id: "search", start: d.start_date, last, source: (a, b) => `${src}, ${range(a, b)}.`, metrics: [
    { label: "Clicks", value: clicks, fmt: num },
    { label: "Times Google showed us", value: shown, fmt: num },
    { label: "Click rate", value: (a, b) => (shown(a, b) ? (clicks(a, b) / shown(a, b)) * 100 : null), fmt: (v) => pct(v), whole: false, yfmt: (v) => `${v}%` },
    { label: "Average spot on Google", value: (a, b) => (shown(a, b) ? spotWeight(a, b) / shown(a, b) : null), fmt: spot, whole: false,
      lowerIsBetter: true, flip: true, sub: "Lower is better" },
  ] });
}

// ---------- Tab 2: Website visits ----------

const CHANNELS = {
  "Direct": "Direct (typed in, or unknown)",
  "Organic Search": "Search engines (mostly Google)",
  "Email": "Email",
  "Referral": "Other websites",
  "Organic Social": "Social media (LinkedIn and others)",
  "AI Assistant": "AI tools (ChatGPT, Gemini, Perplexity)",
  "Unassigned": "Unlabelled",
  "Paid Search": "Paid search ads",
  "Paid Social": "Paid social ads",
  "Organic Shopping": "Shopping search",
  "Organic Video": "Video sites",
  "Display": "Display ads",
  "Cross-network": "Google ad network",
};
const channelName = (c) => CHANNELS[c] || c;

function renderVisits(d) {
  const src = "Source: Google Analytics";
  const when = `${range(d.start_date, d.end_date)} (Pacific time)`;
  const t = d.totals;
  const email = d.channels.find((r) => r.sessionDefaultChannelGroup === "Email");
  $("visits-source").textContent = `${src}, ${when}.`;
  $("visits-cards").innerHTML =
    card("Engaged visits", num(t.engagedSessions), "Stayed 10+ seconds, saw 2+ pages, or filled a form") +
    card("All visits", num(t.sessions), "Includes robots") +
    card("Visits from email", num(email ? email.sessions : 0), email ? `${pct((email.engagedSessions / email.sessions) * 100, 0)} engaged` : "") +
    card("Share who engaged", pct((t.engagedSessions / t.sessions) * 100, 1));
  $("visits-more-cards").innerHTML = card("People visiting", num(t.totalUsers), "Includes robots");
  $("visits-more-source").textContent = `${src}, ${when}.`;

  $("visits-daily-source").textContent = `${src}, ${when}.`;
  const emailByDay = Object.fromEntries(d.channel_daily.filter((r) => r.sessionDefaultChannelGroup === "Email").map((r) => [r.date, r.sessions]));
  chart("visits-daily", (th) => ({
    type: "line", dates: d.daily.map((r) => [r.date, r.date]), 
    data: { labels: d.daily.map((r) => day(r.date)), datasets: [
      line("Engaged visits", d.daily.map((r) => r.engagedSessions), th.s[0]),
      line("All visits", d.daily.map((r) => r.sessions), th.s[1]),
      line("Visits from email", d.daily.map((r) => emailByDay[r.date] || 0), th.s[2]),
    ] },
  }));

  $("visits-channels-source").textContent = `${src}, ${when}.`;
  $("visits-channels-table-source").textContent = `${src}, ${when}.`;
  // Groups under 20 visits share one "Small sources" line; the Every source table still lists each one.
  const SMALL = 20;
  const small = d.channels.filter((r) => r.sessions < SMALL);
  const grouped = d.channels.filter((r) => r.sessions >= SMALL).map((r) => ({ ...r, name: channelName(r.sessionDefaultChannelGroup) }));
  if (small.length) {
    const add = (k) => small.reduce((t2, r) => t2 + r[k], 0);
    grouped.push({ name: `Small sources (under ${SMALL} visits each)`, sessions: add("sessions"), engagedSessions: add("engagedSessions"), totalUsers: null,
      averageSessionDuration: add("sessions") ? small.reduce((t2, r) => t2 + r.averageSessionDuration * r.sessions, 0) / add("sessions") : 0 });
  }
  const ch = grouped.map((r) => ({ ...r, engaged: (r.engagedSessions / r.sessions) * 100 }))
    .sort((a, b) => b.engagedSessions - a.engagedSessions);
  chart("visits-channels", (th) => ({
    type: "bar", horizontal: true,
    data: { labels: ch.map((r) => r.name), datasets: [
      bar("Engaged visits", ch.map((r) => r.engagedSessions), th.s[0]),
      bar("All visits", ch.map((r) => r.sessions), th.s[1]),
    ] },
  }));
  table($("visits-channels-table"), { rows: ch, sortKey: "engagedSessions", pageSize: 20, columns: [
    { key: "name", label: "Came from" },
    { key: "engagedSessions", label: "Engaged visits", num: true, fmt: num },
    { key: "sessions", label: "All visits", num: true, fmt: num },
    { key: "engaged", label: "Share who engaged", num: true, fmt: (v) => pct(v, 0) },
    { key: "totalUsers", label: "People", num: true, fmt: num },
    { key: "averageSessionDuration", label: "Average time", num: true, fmt: (v) => `${Math.round(v)}s` },
  ] });

  $("visits-sources-source").textContent = `${src}, ${when}.`;
  table($("visits-sources"), {
    rows: d.sources.map((r) => ({ ...r, name: channelName(r.sessionDefaultChannelGroup), engaged: (r.engagedSessions / r.sessions) * 100 })),
    search: "sources", sortKey: "engagedSessions", columns: [
      { key: "sessionSource", label: "Source", search: true },
      { key: "sessionMedium", label: "Type", search: true },
      { key: "name", label: "Group", search: true },
      { key: "engagedSessions", label: "Engaged visits", num: true, fmt: num },
      { key: "sessions", label: "All visits", num: true, fmt: num },
      { key: "engaged", label: "Share who engaged", num: true, fmt: (v) => pct(v, 0) },
    ] });

  $("visits-pages-source").textContent = `${src}, ${when}.`;
  table($("visits-pages"), { rows: d.pages, search: "pages", sortKey: "views", columns: [
    { key: "page", label: "Page", search: true },
    { key: "views", label: "Times viewed", num: true, fmt: num },
  ] });

  const all = rangeSum(d.daily, "sessions"), engaged = rangeSum(d.daily, "engagedSessions");
  const robots = rangeSum(d.email_robots_daily || [], "robots");   // non-engaged visits with an email-robot sign (see fetch_data.py)
  const emailRows = d.daily.map((r) => ({ date: r.date, visits: emailByDay[r.date] || 0 }));
  compare({ id: "visits", start: d.start_date, last: lastFullDayPacific(d.end_date, d.pulled_at),
    source: (a, b) => `${src}, ${range(a, b)} (Pacific time).`, metrics: [
      { label: "Engaged visits", value: engaged, fmt: num },
      { label: "All visits", value: all, fmt: num, sub: (a, b) => `Includes robots. Without email robots: ${num(all(a, b) - robots(a, b))}` },
      { label: "Visits from email", value: rangeSum(emailRows, "visits"), fmt: num },
      { label: "Share who engaged", value: (a, b) => (all(a, b) ? (engaged(a, b) / all(a, b)) * 100 : null), fmt: (v) => pct(v, 1), whole: false, yfmt: (v) => `${v}%` },
    ] });
}

// ---------- Tab 3: Leads ----------

const LEAD_ORDER = ["demo", "contact", "events", "gartner_offer", "other"];
const LEAD_NOTES = {
  demo: "Form on /demo",
  contact: "Form on /contact",
  events: "Event pages on the website",
  gartner_offer: "Form on /gartner-symposium/free-modernization",
  other: "Reports, webinars and other forms",
};

function renderLeads(d) {
  const src = "Sources: Google Analytics and HubSpot form fills";
  const when = `${range(d.start_date, d.end_date)} (Pacific time)`;
  $("leads-source").textContent = `${src}, ${when}.`;
  const leadCard = (k) => card(d.lines[k].label, num(d.lines[k].count), LEAD_NOTES[k]);
  $("leads-cards").innerHTML = ["demo", "events", "gartner_offer", "contact"].map(leadCard).join("");
  const jobs = (d.left_out || []).reduce((t, r) => t + r.count, 0);
  $("leads-more-cards").innerHTML = leadCard("other") + card("Job application form fills", num(jobs), "Not counted as leads");
  $("leads-more-source").textContent = `${src}, ${when}.`;

  $("leads-core-source").textContent = `${src}, ${when}.`;
  const removed = "We removed this form at the 30 Sep launch. Visitors now go to Book a demo.";
  const names = { "/": "Homepage", "/about": "About", "/platform": "Platform" };
  const core = [
    ...d.removed_form_pages.map((p) => ({ name: names[p] || p, page: p, status: removed })),
    { name: "Contact", page: "/contact", status: `${num(d.lines.contact.count)} form fill${d.lines.contact.count === 1 ? "" : "s"}, now sent to Book a demo` },
    { name: "Book a demo", page: "/demo", status: `${num(d.lines.demo.count)} demo requests` },
  ];
  table($("leads-core"), { rows: core, columns: [
    { key: "name", label: "Page", sort: false },
    { key: "page", label: "Address", sort: false },
    { key: "status", label: "Form fills", sort: false },
  ] });

  // Monday-to-Sunday weeks, clipped to the date range.
  const weeks = {};
  for (const r of d.daily) {
    const dt = toDate(r.date), start = addDays(r.date, -((dt.getUTCDay() + 6) % 7));
    const w = weeks[start] || (weeks[start] = Object.fromEntries(LEAD_ORDER.map((k) => [k, 0])));
    LEAD_ORDER.forEach((k) => { w[k] += r[k] || 0; });
  }
  for (let s = addDays(d.start_date, -((toDate(d.start_date).getUTCDay() + 6) % 7)); s <= d.end_date; s = addDays(s, 7)) {
    weeks[s] = weeks[s] || Object.fromEntries(LEAD_ORDER.map((k) => [k, 0]));
  }
  const starts = Object.keys(weeks).sort();
  const label = (s) => { const a = s < d.start_date ? d.start_date : s, b = addDays(s, 6) > d.end_date ? d.end_date : addDays(s, 6); return `${day(a)} to ${day(b)}`; };
  $("leads-weekly-source").textContent = `${src}, ${when}.`;
  chart("leads-weekly", (th) => ({
    type: "bar", dates: starts.map((s) => [s, addDays(s, 6)]),
    data: { labels: starts.map(label), datasets: LEAD_ORDER.map((k, i) => bar(d.lines[k].label, starts.map((s) => weeks[s][k]), th.s[i])) },
  }));

  $("leads-pages-source").textContent = `${src}, ${when}.`;
  const rows = LEAD_ORDER.flatMap((k) => d.lines[k].pages.map((p) => ({ line: d.lines[k].label, page: p.page, count: p.count })));
  table($("leads-pages"), { rows, search: "pages", sortKey: "count", columns: [
    { key: "line", label: "Kind of form", search: true },
    { key: "page", label: "Page", search: true },
    { key: "count", label: "Form fills", num: true, fmt: num },
  ] });

  compare({ id: "leads", start: d.start_date, last: lastFullDayPacific(d.end_date, d.pulled_at),
    source: (a, b) => `${src}, ${range(a, b)} (Pacific time).`,
    metrics: ["demo", "events", "gartner_offer", "contact"].map((k) => ({ label: d.lines[k].label, value: rangeSum(d.daily, k), fmt: num })) });
}

// ---------- LinkedIn: company page and Kumar, never mixed ----------

// Monday-to-Sunday weeks, clipped to the date range, for one LinkedIn source.
function weekly(rows, key, start, end) {
  const out = {};
  for (const r of rows) {
    const s = addDays(r.date, -((toDate(r.date).getUTCDay() + 6) % 7));
    out[s] = (out[s] || 0) + r[key];
  }
  return Object.keys(out).sort().map((s) => ({
    label: `${day(s < start ? start : s)} to ${day(addDays(s, 6) > end ? end : addDays(s, 6))}`, value: out[s], start: s, end: addDays(s, 6),
  }));
}

function metricChart(id, segId, rows, metrics, colors) {
  let m = Object.keys(metrics)[0];
  chart(id, (th) => ({
    type: "line", dates: rows.map((r) => [r.date, r.date]), 
    data: { labels: rows.map((r) => day(r.date)), datasets: metrics[m].map(([label, key], i) => line(label, rows.map((r) => r[key]), th.s[colors[i]])) },
  }));
  $(segId).addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    m = b.dataset.m;
    $(segId).querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    draw(charts.find((c) => c.id === id));
  });
}

const postLink = (v, r) => `<a href="${esc(r.link)}" target="_blank" rel="noopener">${esc(v)}</a>`;

function renderLinkedIn(d) {
  const when = range(d.start_date, d.end_date);
  const co = d.company, k = d.kumar;
  const coSrc = `Source: ${co.source}, ${range(co.start_date, co.end_date)}.`;
  const kSrc = `Source: ${k.source}, ${when}.`;
  const sum = (rows, key) => rows.reduce((a, r) => a + r[key], 0);

  $("li-k-key-cards").innerHTML =
    card("Times seen", num(k.seen)) +
    card("People reached", num(k.reached), "Members who saw a post") +
    card("Engagements", num(sum(k.daily, "engagements")), "Reactions, comments, shares and clicks") +
    card("Followers gained", num(sum(k.followers_daily, "gained")));
  $("li-k-key-source").textContent = kSrc;

  // Company page
  $("li-co-source").textContent = coSrc;
  const split = (key) => `Unpaid ${num(sum(co.daily, `${key}_unpaid`))}, paid ${num(sum(co.daily, `${key}_paid`))}`;
  $("li-co-cards").innerHTML =
    card("Times seen", num(sum(co.daily, "seen_total")), split("seen")) +
    card("Clicks", num(sum(co.daily, "clicks_total")), split("clicks")) +
    card("Reactions", num(sum(co.daily, "reactions_total")), split("reactions")) +
    card("Comments", num(sum(co.daily, "comments_total")), split("comments")) +
    card("Followers gained", num(sum(co.followers_daily, "gained"))) +
    card("Company page views", num(sum(co.visitors_daily, "views_total")), `Overview ${num(sum(co.visitors_daily, "views_overview"))}, Jobs ${num(sum(co.visitors_daily, "views_jobs"))}`);

  metricChart("li-co-daily", "li-co-metric", co.daily, {
    seen: [["Times seen, unpaid", "seen_unpaid"], ["Times seen, paid", "seen_paid"]],
    clicks: [["Clicks, unpaid", "clicks_unpaid"], ["Clicks, paid", "clicks_paid"]],
    reactions: [["Reactions, unpaid", "reactions_unpaid"], ["Reactions, paid", "reactions_paid"]],
    comments: [["Comments, unpaid", "comments_unpaid"], ["Comments, paid", "comments_paid"]],
  }, [0, 1]);
  $("li-co-daily-source").textContent = coSrc;

  const coWeeks = weekly(co.followers_daily, "gained", co.start_date, co.end_date);
  chart("li-co-followers", (th) => ({
    type: "bar", dates: coWeeks.map((w) => [w.start, w.end]), data: { labels: coWeeks.map((w) => w.label), datasets: [bar("Followers gained", coWeeks.map((w) => w.value), th.s[0])] },
  }));
  $("li-co-followers-source").textContent = coSrc;

  chart("li-co-visits", (th) => ({
    type: "line",
    dates: co.visitors_daily.map((r) => [r.date, r.date]), data: { labels: co.visitors_daily.map((r) => day(r.date)), datasets: [
      line("All company page views", co.visitors_daily.map((r) => r.views_total), th.s[0]),
      line("Overview page views", co.visitors_daily.map((r) => r.views_overview), th.s[1]),
      line("Jobs page views", co.visitors_daily.map((r) => r.views_jobs), th.s[2]),
    ] },
  }));
  $("li-co-visits-source").textContent = coSrc;

  table($("li-co-posts"), { rows: co.posts, search: "posts", sortKey: "seen", columns: [
    { key: "title", label: "Post", search: true, fmt: postLink },
    { key: "created", label: "Posted on", fmt: (v) => dayYear(v) },
    { key: "seen", label: "Times seen", num: true, fmt: num },
    { key: "clicks", label: "Clicks", num: true, fmt: num },
    { key: "likes", label: "Likes", num: true, fmt: num },
    { key: "comments", label: "Comments", num: true, fmt: num },
  ] });
  $("li-co-posts-source").textContent = coSrc;

  const b = co.breakdowns;
  const order = ["job_function", "seniority", "company_size", "location", "industry"];
  $("li-co-breakdowns").innerHTML = order.map((key) => `<div><h4>${b[key].label}</h4><div id="li-bd-${key}"></div></div>`).join("");
  order.forEach((key) => table($(`li-bd-${key}`), { rows: b[key].top, pageSize: 10, columns: [
    { key: "name", label: b[key].label, sort: false },
    { key: "followers", label: "Followers", num: true, fmt: num, sort: false },
  ] }));
  $("li-co-breakdowns-source").textContent = `Source: ${co.source}, as exported on ${dayYear(co.breakdowns_as_of)}.`;

  // Kumar Chivukula
  $("li-k-source").textContent = kSrc;
  $("li-k-cards").innerHTML =
    card("Times seen", num(k.seen)) +
    card("People reached", num(k.reached), "Members who saw a post") +
    card("Engagements", num(sum(k.daily, "engagements")), "Reactions, comments, shares and clicks") +
    card("Followers gained", num(sum(k.followers_daily, "gained"))) +
    card("Total followers", num(k.total_followers), `On ${dayYear(k.total_followers_date)}`);

  metricChart("li-k-daily", "li-k-metric", k.daily, {
    seen: [["Times seen", "seen"]], engagements: [["Engagements", "engagements"]],
  }, [0]);
  $("li-k-daily-source").textContent = kSrc;

  const kWeeks = weekly(k.followers_daily, "gained", d.start_date, d.end_date);
  chart("li-k-followers", (th) => ({
    type: "bar", dates: kWeeks.map((w) => [w.start, w.end]), data: { labels: kWeeks.map((w) => w.label), datasets: [bar("Followers gained", kWeeks.map((w) => w.value), th.s[0])] },
  }));
  $("li-k-followers-source").textContent = kSrc;

  const topCols = (key, label) => [
    { key: "name", label: "Post", search: true, fmt: postLink },
    { key: "published", label: "Published", fmt: (v) => dayYear(v) },
    { key, label, num: true, fmt: num },
  ];
  table($("li-k-top-seen"), { rows: k.top_by_seen, search: "posts", sortKey: "seen", pageSize: 10, columns: topCols("seen", "Times seen") });
  table($("li-k-top-eng"), { rows: k.top_by_engagements, search: "posts", sortKey: "engagements", pageSize: 10, columns: topCols("engagements", "Engagements") });
  $("li-k-top-seen-source").textContent = kSrc;
  $("li-k-top-eng-source").textContent = kSrc;

  // Kumar's October: each export is its own period, shown one at a time, never added together
  const oct = d.kumar_october;
  const periods = Object.fromEntries(oct.periods.map((p) => [p.key, p]));
  // the buttons name each export by its dates
  $("li-ko-period").querySelectorAll("button").forEach((btn) => { if (periods[btn.dataset.p]) btn.textContent = periods[btn.dataset.p].label; });
  let period = "7d";
  const drawPeriod = () => {
    const p = periods[period];
    const counting = (p.still_counting || oct.still_counting).map(dayYear).join(" and ");
    $("li-ko-counting").textContent = counting ? `LinkedIn was still counting ${counting} when we exported this, so its numbers may change.` : "";
    const pSrc = `Source: LinkedIn export, Kumar Chivukula's profile, ${range(p.start_date, p.end_date)}.`;
    $("li-ko-cards").innerHTML =
      card("Times seen", num(p.seen)) +
      card("People reached", num(p.reached), "Members who saw a post") +
      card("Engagements", num(sum(p.daily, "engagements")), "Reactions, comments, shares and clicks") +
      card("Followers gained", num(sum(p.followers_daily, "gained")));
    $("li-ko-more-cards").innerHTML = card("Total followers", num(p.total_followers), `On ${dayYear(p.total_followers_date)}`);
    ["li-ko-source", "li-ko-chart-source", "li-ko-more-source", "li-ko-top-seen-source", "li-ko-top-eng-source"].forEach((id) => { $(id).textContent = pSrc; });
    $("li-ko-top-title").textContent = `Top posts, ${p.label[0].toLowerCase()}${p.label.slice(1)}`;
    table($("li-ko-top-seen"), { rows: p.top_by_seen, search: "posts", sortKey: "seen", pageSize: 10, columns: topCols("seen", "Times seen") });
    table($("li-ko-top-eng"), { rows: p.top_by_engagements, search: "posts", sortKey: "engagements", pageSize: 10, columns: topCols("engagements", "Engagements") });
  };
  drawPeriod();
  chart("li-ko-chart", (th) => ({
    type: "bar", whole: true,
    dates: periods[period].daily.map((r) => [r.date, r.date]), data: { labels: periods[period].daily.map((r) => day(r.date)), datasets: [bar("Times seen", periods[period].daily.map((r) => r.seen), th.s[0])] },
  }));
  $("li-ko-period").addEventListener("click", (e) => {
    const btn = e.target.closest("button"); if (!btn) return;
    period = btn.dataset.p;
    $("li-ko-period").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === btn));
    drawPeriod(); draw(charts.find((c) => c.id === "li-ko-chart"));
  });

  compare({ id: "li-co", start: co.start_date, last: co.end_date, source: (a, b) => `Source: ${co.source}, ${range(a, b)}.`, metrics: [
    { label: "Times seen", value: rangeSum(co.daily, "seen_total"), fmt: num },
    { label: "Clicks", value: rangeSum(co.daily, "clicks_total"), fmt: num },
    { label: "Followers gained", value: rangeSum(co.followers_daily, "gained"), fmt: num },
    { label: "Posts published", value: rangeSum(co.posts.map((x) => ({ date: x.created })), () => 1), fmt: num },
  ] });

  const ka = d.kumar_all;
  const kLast = ka.still_counting.includes(ka.end_date) ? addDays(ka.end_date, -1) : ka.end_date;
  compare({ id: "li-k2", start: ka.start_date, last: kLast, source: (a, b) => `Source: ${k.source}, ${range(a, b)}.`, metrics: [
    { label: "Times seen", value: rangeSum(ka.daily, "seen"), fmt: num },
    { label: "Engagements", value: rangeSum(ka.daily, "engagements"), fmt: num },
    { label: "Followers gained", value: rangeSum(ka.followers_daily, "gained"), fmt: num },
  ] });
}

// Kumar's own posts and reposts: counted by month from his profile, two separate lines, never added together
function renderKumarPosts(kp) {
  const src = kp.as_of ? `Source: ${kp.source}, checked ${dayYear(kp.as_of)}. Months follow UTC.` : `Source: ${kp.source}`;
  const months = kp.months, cur = months[months.length - 1], prev = months[months.length - 2];
  const curName = `${monthName(cur.month + "-01")}${cur.so_far ? " so far" : ""}`;
  const fill = () => {
    $("li-k2-posts").innerHTML = [["Own posts", "own_posts"], ["Reposts", "reposts"]].map(([label, key]) =>
      card(`${label}, ${curName}`, num(cur[key]), `${monthName(prev.month + "-01")}: ${num(prev[key])}`)).join("");
    $("li-k2-posts-note").textContent = periodMode !== "month" ? "Apify counts posts by month, so the period switch doesn't change them." : "";
  };
  fill(); monthlyTabs.push(fill);
  $("li-k2-posts-source").textContent = src;
  table($("li-k2-posts-table"), { rows: months.map((m) => ({ ...m, name: `${monthName(m.month + "-01")} ${m.month.slice(0, 4)}${m.so_far ? " (so far)" : ""}` })), columns: [
    { key: "name", label: "Month", sort: false },
    { key: "own_posts", label: "Own posts", num: true, fmt: num, sort: false },
    { key: "reposts", label: "Reposts", num: true, fmt: num, sort: false },
  ] });
  $("li-k2-posts-table-source").textContent = src;
}

// Visits to opsera.ai from all of LinkedIn: company page, Kumar and untagged, three lines never added together
function renderLinkedInVisits(ga) {
  const li = ga.linkedin;
  const GROUPS = [["company", "Company page"], ["kumar", "Kumar"], ["untagged", "Untagged"]];
  const src = "Source: Google Analytics";
  const when = (a, b) => `${range(a, b)} (Pacific time)`;
  compare({ id: "li-web", together: true, start: ga.start_date, last: lastFullDayPacific(ga.end_date, ga.pulled_at),
    source: (a, b) => `${src}, ${when(a, b)}.`,
    metrics: GROUPS.map(([g, label]) => ({ label: `${label}: visits`, value: rangeSum(li.daily.filter((r) => r.group === g), "visits"), fmt: num })) });

  const all = (rows, g, key) => rows.filter((r) => r.group === g).reduce((t2, r) => t2 + r[key], 0);
  const forms = (g, line) => li.forms.filter((r) => r.group === g && r.line === line).reduce((t2, r) => t2 + r.count, 0);
  table($("li-web-groups"), { rows: GROUPS.map(([g, label]) => ({ name: label, visits: all(li.daily, g, "visits"), engaged: all(li.daily, g, "engaged"),
    demo: forms(g, "demo"), events: forms(g, "events"), gartner: forms(g, "gartner_offer"), contact: forms(g, "contact"), other: forms(g, "other") })),
    columns: [
      { key: "name", label: "From", sort: false },
      { key: "visits", label: "Visits", num: true, fmt: num, sort: false },
      { key: "engaged", label: "Engaged visits", num: true, fmt: num, sort: false },
      { key: "demo", label: "Demo requests", num: true, fmt: num, sort: false },
      { key: "events", label: "Event sign-ups", num: true, fmt: num, sort: false },
      { key: "gartner", label: "Gartner offer", num: true, fmt: num, sort: false },
      { key: "contact", label: "Contact forms", num: true, fmt: num, sort: false },
      { key: "other", label: "Other forms", num: true, fmt: num, sort: false },
    ] });
  $("li-web-groups-source").textContent = `Sources: Google Analytics and HubSpot form fills, ${when(ga.start_date, ga.end_date)}.`;
  const otherTags = li.tags.filter((r) => r.group === "untagged" && !["(referral)", "(not set)", ""].includes(r.sessionCampaignName));
  $("li-web-other-tags").textContent = otherTags.length
    ? `Untagged also holds ${num(otherTags.reduce((t2, r) => t2 + r.visits, 0))} visits with other tags. The LinkedIn sources and tags table below lists them all.` : "";

  const groupName = Object.fromEntries(GROUPS);
  table($("li-web-landing"), { rows: li.landing.map((r) => ({ ...r, from: groupName[r.group] })), search: "pages", sortKey: "visits", columns: [
    { key: "page", label: "Landing page", search: true },
    { key: "from", label: "From", search: true },
    { key: "visits", label: "Visits", num: true, fmt: num },
    { key: "engaged", label: "Engaged visits", num: true, fmt: num },
  ] });
  $("li-web-landing-source").textContent = `${src}, ${when(ga.start_date, ga.end_date)}.`;
  table($("li-web-tags"), { rows: li.tags.map((r) => ({ ...r, from: groupName[r.group], campaign: r.sessionCampaignName || "(blank)", content: r.content || "(blank)" })), sortKey: "visits", columns: [
    { key: "sessionSource", label: "Source" },
    { key: "sessionMedium", label: "Type" },
    { key: "campaign", label: "utm_campaign" },
    { key: "content", label: "utm_content" },
    { key: "from", label: "Counted as" },
    { key: "visits", label: "Visits", num: true, fmt: num },
  ] });
  $("li-web-tags-source").textContent = `${src}, ${when(ga.start_date, ga.end_date)}. It counts ${li.sources_counted.slice(0, -1).join(", ")} and ${li.sources_counted.slice(-1)} as LinkedIn.`;
}

// ---------- Customer journey: visit -> demo page -> demo form (Google Analytics) -> contact -> meeting -> deal (HubSpot) ----------

const JOURNEY_CHANNELS = { all: "All", search: "Google search", linkedin: "LinkedIn", email: "Email", events: "Events",
  paid: "Paid ads", ai: "AI tools", youtube: "YouTube", direct: "Direct" };
// the same channels, written mid-sentence in funnel titles
const FUNNEL_NAMES = { all: "all channels", search: "Google search", linkedin: "LinkedIn", email: "email", events: "events",
  paid: "paid ads", ai: "AI tools", youtube: "YouTube", direct: "direct visits" };
const money = (v) => (v == null ? "-" : `$${nf.format(Math.round(v))}`);

function funnelHtml(steps) {
  const top = Math.max(1, ...steps.map((st) => st.value || 0));
  return steps.map((st, i) => {
    // widths on a log scale so the small steps at the end stay visible
    const w = st.value == null ? 12 : 12 + 88 * (Math.log10(st.value + 1) / Math.log10(top + 1));
    const prev = steps[i - 1];
    let dropText = "&nbsp;";
    if (i && prev.value && st.value != null && st.value > prev.value) dropText = st.higherNote || "Higher than the step above, because the tools count differently";
    else if (i && prev.value && st.value != null) dropText = `${Math.round((st.value / prev.value) * 100)}% of the step above`;
    const drop = i ? `<div class="funnel-step"><div></div><div class="funnel-drop">${dropText}</div></div>` : "";
    return `${drop}<div class="funnel-step"><div class="funnel-label">${st.label}<small>${st.src}</small></div>
      <div><div class="funnel-bar" style="width:${w}%">${st.value == null ? "-" : num(st.value)}</div>${st.extra && st.value ? `<div class="funnel-extra">${st.extra}</div>` : ""}</div></div>` +
      (st.note ? `<div class="funnel-step"><div></div><div class="funnel-note">${esc(st.note)}</div></div>` : "");
  }).join("");
}

// Deals are stored only as totals per week, month and 3 months (the page is public). Closed Lost is left out.
// mode "all" adds up every month. Returns null when the period isn't one that's stored, such as a single day.
function dealsIn(hub, mode, a, keep = () => true) {
  const rows = { week: hub.deals_weekly, month: hub.deals_monthly, quarter: hub.deals_quarters, all: hub.deals_monthly }[mode];
  if (!rows) return null;
  if (mode === "week" && a !== weekStart(a)) return null;
  if (mode === "month" && a !== monthStart(a)) return null;
  let start = a;
  let end = mode === "week" ? addDays(a, 6) : mode === "month" ? (monthEnd(a) < hub.end_date ? monthEnd(a) : hub.end_date) : hub.end_date;
  if (mode === "quarter") {
    // the stored 3 months end on the HubSpot pull day; a funnel that ends a day or two earlier uses the nearest one
    const q = quarterOf(hub.end_date);
    const p = quarterOf(addDays(q.start, -1));
    const near = [q, p].find((x) => Math.abs(toDate(x.start) - toDate(a)) <= 7 * 864e5);
    if (!near) return null;
    ({ start, end } = near);
  }
  if (mode === "all") start = hub.start_date;
  const out = { open_count: 0, open_amount: 0, won_count: 0, won_amount: 0, start, end };
  rows.filter((r) => (mode === "all" || r.start === start) && keep(r)).forEach((r) => ["open_count", "open_amount", "won_count", "won_amount"].forEach((k) => { out[k] += r[k]; }));
  return out;
}

// the deal step's note when the stored totals cover other dates than the rest of the funnel
const dealNote = (d, a, b) => (!d ? "We store deals as weekly and monthly totals, so there's no figure for a single day."
  : d.start !== a || d.end !== b ? `We store deals as weekly and monthly totals, so this step covers ${range(d.start, d.end)}.` : "");

// The Google Ads panel lives on the Campaigns tab and is drawn for that tab's dates
let adsDraw = null, adsPending = null;
function drawAdsFor(cur) { if (adsDraw) adsDraw(cur); else adsPending = cur; }

function renderJourney(ga, leads, hub, gsc) {
  const gaLast = lastFullDayPacific(ga.end_date, ga.pulled_at);
  const start = ga.start_date;
  const hubWhen = `updated ${dayYear(hub.pulled_at.slice(0, 10))}`;
  const booked = hub.meetings_daily.filter((r) => r.kind === "booked");

  // Top: marketing-driven demo requests, meetings and new pipeline, against the period before
  compare({ id: "journey", start, last: gaLast,
    source: (a, b) => `Sources: Google Analytics for demo requests and HubSpot for meetings and deals, ${range(a, b)} (Pacific time).`,
    metrics: [
      { label: "Demo requests", value: rangeSum(leads.daily, "demo"), fmt: num, sub: "Website demo form" },
      { label: "Meetings booked", value: rangeSum(booked, "count"), fmt: num, sub: "With marketing contacts" },
      { label: "Open pipeline", value: (a) => dealsIn(hub, periodMode, a)?.open_amount ?? null, fmt: money },
      { label: "Won", value: (a) => dealsIn(hub, periodMode, a)?.won_amount ?? null, fmt: money },
    ] });

  // One funnel, for the chosen channel and the period the switch at the top is set to
  const step = (ch, a, b, mode) => {
    const inCh = (r) => ch === "all" || r.channel === ch;
    const inRange = (r) => r.date >= a && r.date <= b;
    const gaSum = (k) => ga.journey.filter((r) => r.channel === ch && inRange(r)).reduce((t2, r) => t2 + r[k], 0);
    const hubSum = (rows, k) => rows.filter((r) => inCh(r) && r.demo && inRange(r)).reduce((t2, r) => t2 + r[k], 0);
    // AI tools in HubSpot use the same source match as the AEO tab
    const aiSum = (rows, k, demoOnly) => rows.filter((r) => inRange(r) && (!demoOnly || r.demo)).reduce((t2, r) => t2 + r[k], 0);
    const contacts = ch === "ai" ? aiSum(hub.ai_contacts_daily, "count", true) : hubSum(hub.contacts_daily.filter((r) => r.line === "form"), "count");
    const d = dealsIn(hub, mode, a, (r) => r.demo && (ch === "all" || (ch === "ai" ? !!r.tool : r.channel === ch)));
    // the All funnel starts from the same visits total as the Website visits tab
    const visits = ch === "all" ? ga.daily.filter(inRange).reduce((t2, r) => t2 + r.sessions, 0) : gaSum("visits");
    const steps = [
      { label: "Visits", value: visits, src: "Google Analytics", higherNote: "Higher than clicks, because Google Analytics also counts return visits" },
      { label: "Saw the demo page", value: gaSum("demo_page"), src: "Google Analytics" },
      { label: "Filled the demo form", value: gaSum("demo_form"), src: "Google Analytics" },
      { label: "New contact", value: contacts, src: "HubSpot" },
      { label: "Meeting", value: hubSum(booked, "count"), src: "HubSpot",
        note: "Only meetings with demo form contacts. The top numbers count any marketing contact." },
      { label: "Deal", value: d ? d.open_count + d.won_count : null, src: "HubSpot",
        extra: d ? `${money(d.open_amount)} open, ${money(d.won_amount)} won` : "",
        note: mode === "all" ? "" : dealNote(d, a, b) },
    ];
    if (ch === "search") {
      const g = gsc.daily.filter(inRange);
      steps.unshift({ label: "Showed up on Google", value: g.reduce((t2, r) => t2 + r.times_shown, 0), src: "Search Console" },
                    { label: "Clicked", value: g.reduce((t2, r) => t2 + r.clicks, 0), src: "Search Console" });
    }
    return steps;
  };
  let channel = JOURNEY_CHANNELS[view.channel] ? view.channel : "all";   // from the address, if it names one
  let month = "";   // a picked month ("2026-06-01"), or "" to follow the period switch
  // Google search ends every step on the last day Search Console covers, so all steps use the same dates
  const lastFor = (ch) => (ch === "search" && gsc.last_day_with_data < gaLast ? gsc.last_day_with_data : gaLast);
  const monthPick = $("journey-month");
  for (let m = monthStart(start); m <= gaLast; m = addDays(monthEnd(m), 1)) {
    monthPick.insertAdjacentHTML("beforeend", `<option value="${m}">${monthName(m)} ${m.slice(0, 4)}${monthEnd(m) > gaLast ? " (so far)" : ""}</option>`);
  }
  const drawFunnel = () => {
    const last = lastFor(channel);
    let cur, mode = periodMode;
    if (month) {
      cur = { start: month < start ? start : month, end: monthEnd(month) < last ? monthEnd(month) : last };
      mode = "month";
    } else {
      cur = periodsFor(periodMode, start, last).cur || { start, end: last };
    }
    const steps = step(channel, cur.start, cur.end, mode);
    $("journey-funnel-title").textContent = `Funnel for ${FUNNEL_NAMES[channel]}, ${range(cur.start, cur.end)}`;
    $("journey-funnel").innerHTML = funnelHtml(steps);
    const gscNote = channel === "search" ? "Search Console, " : "";
    $("journey-funnel-source").textContent = `Sources: ${gscNote}Google Analytics and HubSpot, ${range(cur.start, cur.end)} (Pacific time). Bars use a log scale.`;
    $("journey-linkedin").hidden = channel !== "linkedin";
    $("journey-linkedin-hint").textContent = {
      linkedin: "More detail splits these visits into company page, Kumar and untagged, post by post.",
      paid: "Google and HubSpot mark \"paid\" differently, so the steps don't line up." }[channel] || "";
    if (channel === "linkedin") charts.forEach((c) => c.instance && c.instance.resize());
  };
  // Google Ads by campaign (on the Campaigns tab, for that tab's dates). Spend and ad clicks come from Google Ads
  // through Google Analytics' link; visits and demo requests from Google Analytics. Rows stay per campaign.
  const ads = ga.google_ads_daily || [];
  const adsLast = ads.filter((r) => r.spend > 0).map((r) => r.date).sort().pop();
  const adTotals = (a, b) => {
    const by = {};
    for (const r of ads) {
      if (r.date < a || r.date > b) continue;
      const x = by[r.campaign] || (by[r.campaign] = { campaign: r.campaign, spend: 0, ad_clicks: 0, visits: 0, demo_requests: 0 });
      x.spend += r.spend; x.ad_clicks += r.ad_clicks; x.visits += r.visits; x.demo_requests += r.demo_requests;
    }
    return Object.values(by).map((x) => ({ ...x, per_demo: x.demo_requests ? x.spend / x.demo_requests : null }));
  };
  const adCards = (rows) => {
    const t = (k) => rows.reduce((s2, r) => s2 + r[k], 0);
    const demos = t("demo_requests");
    return card("Spend", money(t("spend"))) + card("Ad clicks", num(t("ad_clicks")), "Counted by Google Ads") +
      card("Visits from Google Ads", num(t("visits")), "Counted by Google Analytics") + card("Demo requests", num(demos)) +
      card("Cost per demo request", demos ? money(t("spend") / demos) : "-", demos ? "" : "No demo requests from ads");
  };
  function drawAds(cur) {
    const rows = adTotals(cur.start, cur.end);
    $("journey-ads-title").textContent = `Google Ads by campaign, ${range(cur.start, cur.end)}`;
    const since = adTotals(start, gaLast), sinceSpend = since.reduce((s2, r) => s2 + r.spend, 0), sinceDemos = since.reduce((s2, r) => s2 + r.demo_requests, 0);
    const sinceLine = `Since ${dayYear(start)}: ${money(sinceSpend)} spent, ${num(sinceDemos)} demo request${sinceDemos === 1 ? "" : "s"} from ads.`;
    if (!rows.length) {
      $("journey-ads-cards").innerHTML = `<div class="card"><div class="label">No Google Ads in this period</div><div class="sub">${adsLast ? `The last ad spend was on ${dayYear(adsLast)}. ` : ""}${sinceLine}</div></div>`;
      $("journey-ads").innerHTML = "";
    } else {
      $("journey-ads-cards").innerHTML = adCards(rows);
      table($("journey-ads"), { rows, sortKey: "spend", columns: [
        { key: "campaign", label: "Campaign" },
        { key: "spend", label: "Spend", num: true, fmt: money },
        { key: "ad_clicks", label: "Ad clicks", num: true, fmt: num },
        { key: "visits", label: "Visits", num: true, fmt: num },
        { key: "demo_requests", label: "Demo requests", num: true, fmt: num },
        { key: "per_demo", label: "Cost per demo request", num: true, fmt: (v) => (v == null ? "No demo requests" : money(v)) },
      ] });
      countUp($("journey-ads-cards"));
    }
    // brand search's ad clicks stopped arriving as visits on 16 Jun 2026 (found 28 Oct 2026)
    $("journey-ads-brand").hidden = !(cur.end >= "2026-06-16" && rows.some((r) => r.campaign === "Brand - Search - M+D"));
    $("journey-ads-source").textContent = `Source: Google Analytics, opsera.ai 2026, with spend and ad clicks from the linked Google Ads account, ${range(cur.start, cur.end)} (Pacific time). ${rows.length ? sinceLine : ""}`.trim();
  }
  adsDraw = drawAds;
  drawAds(adsPending || periodsFor(periodMode, start, gaLast).cur || { start, end: gaLast });
  if ([...monthPick.options].some((o) => o.value && o.value === view.funnelmonth)) { month = view.funnelmonth; monthPick.value = month; }
  $("journey-channel").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x.dataset.ch === channel));
  drawFunnel();
  // the period switch above takes over again from a picked month
  monthlyTabs.push(() => { month = ""; monthPick.value = ""; view.funnelmonth = ""; drawFunnel(); });
  monthPick.addEventListener("change", () => { month = monthPick.value; view.funnelmonth = month; saveView(); drawFunnel(); });
  $("journey-channel").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    channel = b.dataset.ch;
    view.channel = channel; saveView();
    $("journey-channel").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    drawFunnel();
  });

  // More detail
  table($("journey-channels"), { rows: Object.entries(JOURNEY_CHANNELS).map(([ch, name]) => {
    const st = step(ch, start, lastFor(ch), "all");
    return { name, visits: st[0].value, page: st[1].value, form: st[2].value, contact: st[3].value, meeting: st[4].value, deal: st[5].value };
  }), columns: [
    { key: "name", label: "Channel", sort: false },
    { key: "visits", label: "Visits", num: true, fmt: num, sort: false },
    { key: "page", label: "Demo page", num: true, fmt: num, sort: false },
    { key: "form", label: "Demo form", num: true, fmt: num, sort: false },
    { key: "contact", label: "Contact", num: true, fmt: num, sort: false },
    { key: "meeting", label: "Meeting", num: true, fmt: num, sort: false },
    { key: "deal", label: "Deal", num: true, fmt: num, sort: false },
  ] });
  $("journey-channels-source").textContent = `Sources: Google Analytics and HubSpot, ${range(start, gaLast)} (Pacific time). Google search stops at ${dayYear(lastFor("search"))}, the last day in Search Console.`;

  const gv = Object.fromEntries(ga.google_search_visits.map((r) => [r.kind, r.visits]));
  $("journey-google-visits").innerHTML = card("First visits", num(gv.new || 0)) + card("Return visits", num(gv.returning || 0)) +
    card("Not labelled", num((gv["(not set)"] || 0) + (gv[""] || 0)), "Almost none engaged");
  $("journey-google-visits-source").textContent = `Source: Google Analytics, Google organic visits from ${range(start, ga.end_date)} (Pacific time). Search Console counted ${num(gsc.daily.reduce((t2, r) => t2 + r.clicks, 0))} clicks from ${range(gsc.daily[0].date, gsc.last_day_with_data)}.`;
  const mk = (k) => hub.meetings_daily.filter((r) => r.kind === k).reduce((t2, r) => t2 + r.count, 0);
  $("journey-meetings").innerHTML = card("Meetings booked", num(mk("booked")), "After sign-up, through yesterday") +
    card("Upcoming", num(mk("upcoming")), "Booked for later") + card("With existing customers", num(mk("existing_customer")), "Left out") +
    card("Before sign-up", num(mk("before_signup")), "Not counted");
  $("journey-meetings-source").textContent = `Source: HubSpot calendar meetings since ${dayYear(start)}, ${hubWhen}. ${num(hub.meetings_all_calendar)} meetings in total.`;
  const dt2 = hub.deals_total;
  $("journey-deals").innerHTML = card("Open deals", num(dt2.open_count), `${money(dt2.open_amount)} pipeline. ${hub.deals_by_stage.map(([st, n]) => `${st}: ${n}`).join(", ")}`) +
    card("Won deals", num(dt2.won_count), money(dt2.won_amount)) +
    card("Closed lost", num(hub.deals_lost.count), "Not counted") +
    card("Older deals for these contacts", num(hub.existing_deals.count), `${money(hub.existing_deals.amount)}, from before sign-up. Not counted`);
  $("journey-deals-source").textContent = `Source: HubSpot deals created since ${dayYear(start)}, ${hubWhen}.`;
  // One line per marketing deal: where the person first came from, their first page and form, and the product
  const lines = hub.deal_lines || [];
  const pageCell = (v) => (v.startsWith("/") ? `<a href="https://opsera.ai${encodeURI(v)}" target="_blank" rel="noopener">${esc(v)}</a>` : esc(v));
  if (lines.length) {
    table($("journey-deal-lines"), { rows: lines.map((d) => ({ ...d, monthName: `${MONTH_NAMES[Number(d.month.slice(5, 7)) - 1]} ${d.month.slice(0, 4)}` })), pageSize: 25, columns: [
      { key: "monthName", label: "Month", sort: false },
      { key: "came_from", label: "First came from", sort: false },
      { key: "first_page", label: "First page", sort: false, fmt: pageCell },
      { key: "first_form", label: "First form", sort: false },
      { key: "product", label: "Product", sort: false },
      { key: "status", label: "Open or won", sort: false },
      { key: "amount", label: "Amount", num: true, fmt: money, sort: false },
    ] });
  } else {
    $("journey-deal-lines").innerHTML = `<p class="muted">No marketing deals yet.</p>`;
  }
  const openSum = lines.filter((d) => d.status === "Open").reduce((t2, d) => t2 + d.amount, 0);
  const wonSum = lines.filter((d) => d.status === "Won").reduce((t2, d) => t2 + d.amount, 0);
  $("journey-deal-lines-source").textContent = `Source: HubSpot deals created since ${dayYear(start)}, ${hubWhen}. ${num(lines.length)} deals: ${money(openSum)} open and ${money(wonSum)} won.`;
  const contacts = (line) => hub.contacts_daily.filter((r) => r.line === line).reduce((t2, r) => t2 + r.count, 0);
  $("journey-contacts").innerHTML = card("Form contacts", num(contacts("form")), `Demo form: ${num(hub.contacts_daily.filter((r) => r.line === "form" && r.demo).reduce((t2, r) => t2 + r.count, 0))}`) +
    card("Luma event sign-ups", num(contacts("luma")), "Imported from Luma") +
    card("Job applicants (people)", num(hub.job_applicants_left_out), "Not counted");
  $("journey-contacts-source").textContent = `Source: HubSpot contacts created by a form since ${dayYear(start)}, plus the Flutter Luma import. Updated ${dayYear(hub.pulled_at.slice(0, 10))}.`;
  table($("journey-contacts-table"), { rows: hub.first_forms.map(([form, n]) => ({ form, n })).filter((r) => !/job application/i.test(r.form)), sortKey: "n", columns: [
    { key: "form", label: "First form" }, { key: "n", label: "Contacts", num: true, fmt: num },
  ] });
  $("journey-contacts-table-source").textContent = `Source: HubSpot, ${hubWhen}.`;
  if (Array.isArray(hub.campaigns)) {
    table($("journey-campaigns"), { rows: hub.campaigns.filter((c) => /FY27|2026/i.test(c.name)), sortKey: "influencedContacts", columns: [
      { key: "name", label: "Campaign" },
      { key: "contactFirstTouch", label: "First touch", num: true, fmt: num },
      { key: "influencedContacts", label: "Influenced", num: true, fmt: num },
      { key: "influencedContacts_also_flutter_guests", label: "Also Flutter guests", num: true, fmt: num },
    ] });
    $("journey-campaigns-source").textContent = `Source: HubSpot, ${num(hub.campaigns_checked)} campaigns checked. Updated ${dayYear(hub.pulled_at.slice(0, 10))}.`;
  }
  table($("journey-li-fields"), { rows: hub.linkedin_fields.map(([field, n]) => ({ field, n })), sortKey: "n", columns: [
    { key: "field", label: "Matched on" }, { key: "n", label: "Contacts", num: true, fmt: num },
  ] });
  $("journey-li-fields-source").textContent = `Source: HubSpot, ${hubWhen}. ${num(hub.linkedin_contacts)} LinkedIn contacts. A contact matching several fields counts once.`;
}

// ---------- AEO: visits from AI tools, and what they led to ----------

const AI_TOOL_NAMES = { all: "All AI tools", chatgpt: "ChatGPT", gemini: "Gemini", perplexity: "Perplexity", claude: "Claude", copilot: "Copilot", other: "Other AI tools" };

function renderAeo(ga, hub) {
  const ai = ga.ai;
  const start = ga.start_date, last = lastFullDayPacific(ga.end_date, ga.pulled_at);
  const src = "Source: Google Analytics";
  let tool = "all";
  const pick = (rows) => rows.filter((r) => tool === "all" || r.tool === tool);
  const spec = { id: "aeo", start, last, source: (a, b) => `${src}, ${tool === "all" ? "all AI tools" : AI_TOOL_NAMES[tool]}, ${range(a, b)} (Pacific time).`,
    metrics: [
      { label: "Visits from AI tools", value: (a, b) => rangeSum(pick(ai.daily), "visits")(a, b), fmt: num },
      { label: "Engaged visits", value: (a, b) => rangeSum(pick(ai.daily), "engaged")(a, b), fmt: num },
      { label: "Demo requests", value: (a, b) => rangeSum(pick(ai.daily), "demo_form")(a, b), fmt: num, sub: "Website demo form" },
    ] };
  compare(spec);
  const drawFunnel = () => {
    const p = periodsFor(periodMode, start, last);
    const cur = p.cur || { start, end: last };
    const inRange = (r) => r.date >= cur.start && r.date <= cur.end;
    const sum = (rows, k) => pick(rows).filter(inRange).reduce((t2, r) => t2 + r[k], 0);
    $("aeo-funnel-title").textContent = `Funnel for ${tool === "all" ? "all AI tools" : AI_TOOL_NAMES[tool]}, ${range(cur.start, cur.end)}`;
    $("aeo-funnel").innerHTML = funnelHtml([
      { label: "AI visit", value: sum(ai.daily, "visits"), src: "Google Analytics" },
      { label: "Saw the demo page", value: sum(ai.daily, "demo_page"), src: "Google Analytics" },
      { label: "Filled the demo form", value: sum(ai.daily, "demo_form"), src: "Google Analytics" },
      { label: "New contact", value: sum(hub.ai_contacts_daily.filter((r) => r.demo), "count"), src: "HubSpot" },
      (() => {
        const d = dealsIn(hub, periodMode, cur.start, (r) => r.demo && (tool === "all" ? !!r.tool : r.tool === tool));
        return { label: "Deal", value: d ? d.open_count + d.won_count : null, src: "HubSpot", extra: d ? `${money(d.open_amount)} open, ${money(d.won_amount)} won` : "",
          note: dealNote(d, cur.start, cur.end) };
      })(),
    ]);
    $("aeo-funnel-source").textContent = `Sources: Google Analytics and HubSpot, ${range(cur.start, cur.end)} (Pacific time). Bars use a log scale.`;
  };
  drawFunnel(); monthlyTabs.push(drawFunnel);
  $("aeo-tool").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    tool = b.dataset.tool;
    $("aeo-tool").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    fillCompare(spec); drawFunnel();
  });

  // More detail
  const tools = Object.keys(AI_TOOL_NAMES).filter((t) => t !== "all" && (t !== "other" || ai.daily.some((r) => r.tool === "other")));
  table($("aeo-tools"), { rows: tools.map((t) => {
    const rows = ai.daily.filter((r) => r.tool === t);
    const s2 = (k) => rows.reduce((t2, r) => t2 + r[k], 0);
    return { name: AI_TOOL_NAMES[t], visits: s2("visits"), engaged: s2("engaged"), page: s2("demo_page"), form: s2("demo_form"),
      contact: hub.ai_contacts_daily.filter((r) => r.tool === t && r.demo).reduce((t2, r) => t2 + r.count, 0) };
  }), sortKey: "visits", columns: [
    { key: "name", label: "AI tool" },
    { key: "visits", label: "Visits", num: true, fmt: num },
    { key: "engaged", label: "Engaged", num: true, fmt: num },
    { key: "page", label: "Demo page", num: true, fmt: num },
    { key: "form", label: "Demo form", num: true, fmt: num },
    { key: "contact", label: "Contact", num: true, fmt: num },
  ] });
  $("aeo-tools-source").textContent = `Sources: Google Analytics and HubSpot for contacts, ${range(start, last)} (Pacific time).`;
  table($("aeo-landing"), { rows: ai.landing.map((r) => ({ ...r, name: AI_TOOL_NAMES[r.tool] })), search: "pages", sortKey: "visits", columns: [
    { key: "page", label: "Landing page", search: true },
    { key: "name", label: "AI tool", search: true },
    { key: "visits", label: "Visits", num: true, fmt: num },
    { key: "engaged", label: "Engaged", num: true, fmt: num },
  ] });
  $("aeo-landing-source").textContent = `${src}, ${range(start, ga.end_date)} (Pacific time).`;
  table($("aeo-sources"), { rows: ai.sources.map((r) => ({ ...r, name: AI_TOOL_NAMES[r.tool] })), sortKey: "name", sortDir: 1, columns: [
    { key: "source", label: "Source in Google Analytics" }, { key: "name", label: "Counted as" },
  ] });
  $("aeo-sources-source").textContent = `${src}, ${range(start, ga.end_date)}.`;
}

function renderLeadsHubspot(hub) {
  $("leads-hubspot-events").innerHTML = hub.events.map((e) => card(e.label, num(e.members),
    [e.note, e.joined_daily.length ? `Added ${e.joined_daily.length > 1 ? `${dayYear(e.joined_daily[0].date)} to ${dayYear(e.joined_daily[e.joined_daily.length - 1].date)}` : dayYear(e.joined_daily[0].date)}` : ""].filter(Boolean).join(". "))).join("");
  $("leads-hubspot-events-source").textContent = `Source: HubSpot lists, updated ${dayYear(hub.pulled_at.slice(0, 10))}.`;
}

// From LinkedIn to the demo form: homepage -> /demo -> demo form, for each LinkedIn line, never added together
function renderLinkedInPath(ga) {
  const rows = ga.linkedin.demo_path;
  const GROUPS = [["company", "Company page"], ["kumar", "Kumar"], ["untagged", "Untagged"]];
  const src = "Sources: Google Analytics and the HubSpot demo form on /demo";
  const start = ga.start_date, last = lastFullDayPacific(ga.end_date, ga.pulled_at);
  const share = (part, whole) => (whole ? `${num(part)} (${Math.round((part / whole) * 100)}%)` : num(part));
  const build = (el, a, b) => {
    const sum = (g, k) => rows.reduce((t2, r) => (r.group === g && r.date >= a && r.date <= b ? t2 + r[k] : t2), 0);
    table($(el), { rows: GROUPS.map(([g, label]) => ({ name: label, home: sum(g, "landed_home"), demo: sum(g, "home_then_demo"),
      form: sum(g, "home_demo_form"), anyDemo: sum(g, "any_demo"), anyForm: sum(g, "any_demo_form") })), columns: [
      { key: "name", label: "From", sort: false },
      { key: "home", label: "Landed on homepage", num: true, fmt: num, sort: false },
      { key: "demo", label: "Then /demo", num: true, fmt: (v, r) => share(v, r.home), sort: false },
      { key: "form", label: "Then demo form", num: true, fmt: (v, r) => share(v, r.demo), sort: false },
      { key: "anyDemo", label: "/demo, any page", num: true, fmt: num, sort: false },
      { key: "anyForm", label: "Demo forms, any page", num: true, fmt: num, sort: false },
    ] });
  };
  const fill = () => {
    const p = periodsFor(periodMode, start, last);
    const cur = p.cur || { start, end: last };
    $("li-path-title").textContent = { day: "Last full day", week: "Last full week", month: "This month so far", quarter: "Last 3 months" }[periodMode];
    build("li-path", cur.start, cur.end);
    $("li-path-source").textContent = `${src}, ${range(cur.start, cur.end)} (Pacific time).`;
  };
  fill(); monthlyTabs.push(fill);
  build("li-path-all", start, last);
  $("li-path-all-source").textContent = `${src}, ${range(start, last)} (Pacific time).`;
}

// Estimated: Untagged LinkedIn visits matched to posts. Best guesses, never added to the tagged lines.
function renderLinkedInEstimate(est, ga) {
  const GROUPS = [["estimated_company", "Estimated: company page"], ["estimated_kumar", "Estimated: Kumar"], ["cant_tell", "Can't tell"]];
  const src = "Source: Google Analytics visits matched to LinkedIn posts";
  const when = (a, b) => `${range(a, b)} (Pacific time)`;
  const estLast = lastFullDayPacific(est.end_date || ga.end_date, est.pulled_at || ga.pulled_at);
  $("li-est-stale").textContent = est.end_date && est.end_date < ga.end_date
    ? `The estimate wasn't updated this week, so it stops at ${dayYear(estLast)}.` : "";
  compare({ id: "li-est", together: true, start: est.start_date || ga.start_date, last: estLast,
    source: (a, b) => `${src}, ${when(a, b)}.`,
    metrics: GROUPS.map(([g, label]) => ({ label, value: rangeSum(est.daily.filter((r) => r.group === g), "visits"), fmt: num })) });

  const name = Object.fromEntries(GROUPS);
  const who = { company: "Company page", kumar: "Kumar" };
  table($("li-est-matches"), { rows: est.matches.map((m) => ({ ...m, counted: name[m.group], linked: m.accounts.map((a) => who[a]).join(" and "),
    days: m.dates.length > 1 ? range(m.dates[0], m.dates[m.dates.length - 1]) : dayYear(m.dates[0]) })), sortKey: "visits", columns: [
    { key: "page", label: "Landing page" },
    { key: "days", label: "Visit days" },
    { key: "linked", label: "Linked by" },
    { key: "counted", label: "Counted as" },
    { key: "visits", label: "Visits", num: true, fmt: num },
  ] });
  $("li-est-matches-source").textContent = `${src}, ${when(ga.start_date, ga.end_date)}.`;
  $("li-est-rule").textContent = `A visit goes to an account only when it alone linked to the page on the day or in the ${est.window_days} days before.`;
  table($("li-est-posts"), { rows: est.linked_posts.map((p) => ({ ...p, from: who[p.account], name: dayYear(p.date) })), sortKey: "date", sortDir: 1, columns: [
    { key: "name", label: "Posted", sort: false, fmt: (v, r) => `<a href="${esc(r.post)}" target="_blank" rel="noopener">${esc(v)}</a>` },
    { key: "from", label: "From", sort: false },
    { key: "page", label: "Links to", sort: false },
  ] });
  $("li-est-posts-source").textContent = `Source: LinkedIn posts found with Apify since ${dayYear("2026-09-01")}. Last checked ${dayYear(est.posts_pulled_at.slice(0, 10))}.`;
}

// ---------- YouTube: Shorts and long videos never added together ----------

const mmss = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;

// Every Monday-to-Sunday week from start to end, even weeks with no views.
function weeksFilled(rows, keys, start, end) {
  const weekOf = (date) => addDays(date, -((toDate(date).getUTCDay() + 6) % 7));
  const out = {};
  for (let s = weekOf(start); s <= end; s = addDays(s, 7)) out[s] = Object.fromEntries(keys.map((k) => [k, 0]));
  for (const r of rows) if (out[weekOf(r.date)]) keys.forEach((k) => { out[weekOf(r.date)][k] += r[k]; });
  return Object.keys(out).sort().map((s) => ({
    label: `${day(s < start ? start : s)} to ${day(addDays(s, 6) > end ? end : addDays(s, 6))}`, ...out[s], start: s, end: addDays(s, 6),
  }));
}

function renderYouTube(d, ga) {
  const last = d.last_day_with_data || d.end_date;
  const src = `Source: YouTube Analytics, Opsera channel, ${range(d.start_date, last)}.`;
  const c = d.channel;

  $("yt-ch-cards").innerHTML =
    card("Subscribers gained", num(c.subs_gained)) +
    card("Subscribers lost", num(c.subs_lost)) +
    card("Card clicks", num(c.card_clicks), `Card teaser clicks ${num(c.card_teaser_clicks)}`) +
    card("Shorts published", num(c.published.filter((v) => v.type === "shorts").length), "Public videos") +
    (c.published.some((v) => v.type === "unknown") ? card("Videos not yet watched", num(c.published.filter((v) => v.type === "unknown").length), "Public, but YouTube can't tell Shorts from long videos until someone watches them") : "");
  $("yt-ch-source").textContent = src;

  const subWeeks = weeksFilled(c.subs_daily, ["gained", "lost"], d.start_date, last);
  chart("yt-subs", (th) => ({
    type: "bar", whole: true, dates: subWeeks.map((w) => [w.start, w.end]), data: { labels: subWeeks.map((w) => w.label), datasets: [
      bar("Subscribers gained", subWeeks.map((w) => w.gained), th.s[0]),
      bar("Subscribers lost", subWeeks.map((w) => w.lost), th.s[1]),
    ] },
  }));
  $("yt-subs-source").textContent = src;

  table($("yt-searches"), { rows: c.search_terms, search: "searches", sortKey: "views", columns: [
    { key: "term", label: "Search", search: true },
    { key: "views", label: "Views", num: true, fmt: num },
  ] });
  $("yt-searches-source").textContent = src;
  const named = c.search_terms.reduce((a, r) => a + r.views, 0);
  $("yt-searches-note").textContent = `YouTube names the search term for ${num(named)} of the ${num(c.search_views)} views from its search box.`;

  const fromYt = ga.sources.filter((r) => /youtube\.com|youtu\.be/i.test(r.sessionSource));
  const gaSum = (k) => fromYt.reduce((a, r) => a + r[k], 0);
  $("yt-ga-cards").innerHTML =
    card("Visits from YouTube", num(gaSum("sessions"))) +
    card("Engaged visits from YouTube", num(gaSum("engagedSessions")));
  $("yt-ga-source").textContent = `Source: Google Analytics, ${range(ga.start_date, ga.end_date)} (Pacific time).`;

  const sections = [["long", "Long videos"], ["shorts", "Shorts"]];
  $("yt-types").innerHTML = sections.map(([t, title]) => `
    <h3 class="section-title">${title}</h3>
    <div class="cards" id="yt-${t}-cards"></div>
    <p class="source">${src}</p>
    <div class="panel">
      <div class="panel-head">
        <h3>Week by week</h3>
        <div class="seg" id="yt-${t}-metric" role="group" aria-label="Choose what the chart shows">
          <button data-m="views" class="on">Views</button>
          <button data-m="minutes">Watch time</button>
        </div>
      </div>
      <div class="chart-box short"><canvas id="yt-${t}-weekly" aria-label="${title} views and watch time by week"></canvas></div>
      <p class="source">${src}</p>
      <p class="note" id="yt-${t}-round"></p>
    </div>
    <div class="panel">
      <h3>Where views came from</h3>
      <div class="chart-box short"><canvas id="yt-${t}-sources" aria-label="${title} views by where they came from"></canvas></div>
      <p class="source">${src}</p>
    </div>
    <div class="panel">
      <h3>Top videos by views</h3>
      <div id="yt-${t}-top-views"></div>
      <p class="source">${src}</p>
      <h3 style="margin-top:20px">Top videos by watch time</h3>
      <div id="yt-${t}-top-time"></div>
      <p class="source">${src}</p>
      <p class="note" id="yt-${t}-listed"></p>
    </div>`).join("");

  for (const [t] of sections) {
    const v = d.types[t];
    $(`yt-${t}-cards`).innerHTML =
      card("Views", num(v.views)) +
      card("Watch time", `${num(v.minutes)} min`) +
      card("Average time watched", mmss(v.avg_seconds), "Per view");

    const weeks = weeksFilled(v.daily, ["views", "minutes"], d.start_date, last);
    const labels = { views: "Views", minutes: "Watch time (minutes)" };
    let m = "views";
    chart(`yt-${t}-weekly`, (th) => ({
      type: "bar", whole: true, dates: weeks.map((w) => [w.start, w.end]), data: { labels: weeks.map((w) => w.label), datasets: [bar(labels[m], weeks.map((w) => w[m]), th.s[0])] },
    }));
    $(`yt-${t}-round`).textContent = weeks.reduce((a, w) => a + w.minutes, 0) === v.minutes ? "" :
      "YouTube rounds each day's watch time, so the weeks add up to a little less than the total.";
    $(`yt-${t}-metric`).addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      m = b.dataset.m;
      $(`yt-${t}-metric`).querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
      draw(charts.find((ch) => ch.id === `yt-${t}-weekly`));
    });

    chart(`yt-${t}-sources`, (th) => ({
      type: "bar", horizontal: true, whole: true,
      data: { labels: v.sources.map((r) => r.source), datasets: [bar("Views", v.sources.map((r) => r.views), th.s[0])] },
    }));

    const videoLink = (val, r) => `<a href="https://www.youtube.com/watch?v=${encodeURIComponent(r.id)}" target="_blank" rel="noopener">${esc(val)}</a>`;
    const cols = [
      { key: "title", label: "Video", search: true, fmt: videoLink },
      { key: "views", label: "Views", num: true, fmt: num },
      { key: "minutes", label: "Watch time (min)", num: true, fmt: num },
      { key: "avg_seconds", label: "Average time watched", num: true, fmt: mmss },
    ];
    table($(`yt-${t}-top-views`), { rows: v.videos, search: "videos", sortKey: "views", pageSize: 10, columns: cols });
    table($(`yt-${t}-top-time`), { rows: v.videos, search: "videos", sortKey: "minutes", pageSize: 10, columns: cols });
    const l = v.videos_listed;
    $(`yt-${t}-listed`).textContent = l.views === v.views && l.minutes === v.minutes ? "" :
      `YouTube lists ${num(l.views)} of ${num(v.views)} views and ${num(l.minutes)} of ${num(v.minutes)} minutes by video.`;
  }

  const published = (t) => rangeSum(c.published.filter((v) => v.type === t), () => 1);
  compare({ id: "yt", start: d.start_date, last, source: (a, b) => `Source: YouTube Analytics, Opsera channel, ${range(a, b)}.`, metrics: [
    { label: "Long videos: views", value: rangeSum(d.types.long.daily, "views"), fmt: num },
    { label: "Long videos: watch time", value: rangeSum(d.types.long.daily, "minutes"), fmt: (v) => `${num(v)} min` },
    { label: "Shorts: views", value: rangeSum(d.types.shorts.daily, "views"), fmt: num },
    { label: "Long videos published", value: published("long"), fmt: num, sub: "Public videos" },
  ] });
}

// ---------- Tab 4: Kahoots ----------

function renderKahoots(monthly, quarter) {
  const m = (key, month) => monthly.find((r) => r.month === month)[key];
  const q = (metric) => quarter.find((r) => r.metric === metric);
  const fillKahoots = () => {
    if (periodMode === "quarter") {
      const qCard = (label, metric) => card(label, num(q(metric).q3), `Q2: ${num(q(metric).q2)}`, cmpDelta(q(metric).q3, q(metric).q2));
      $("kahoots-cards").innerHTML = qCard("Website visits", "Website visits") + qCard("Visits from people", "Visits from people, no robots") +
        qCard("Form fills", "All form fills");
      $("kahoots-monthly-note").textContent = "Kahoots reported by quarter too, so this compares Q3 (Jul to Sep) with Q2 (Apr to Jun).";
      $("kahoots-cards-source").textContent = "Source: Kahoots Q3 2026 report, Q3 2026 compared with Q2 2026.";
      return;
    }
    const monthCard = (label, key) => card(label, num(m(key, "2026-09")), `August: ${num(m(key, "2026-08"))}`, cmpDelta(m(key, "2026-09"), m(key, "2026-08")));
    $("kahoots-cards").innerHTML = monthCard("Website visits", "visits") + monthCard("Visits from people", "people_visits") + monthCard("Form fills", "form_fills");
    $("kahoots-monthly-note").textContent = periodMode !== "month" ? "Kahoots reported by month, so this tab compares September with August." : "";
    $("kahoots-cards-source").textContent = "Source: Kahoots Q3 2026 report, Sep 2026 compared with Aug 2026.";
  };
  fillKahoots(); monthlyTabs.push(fillKahoots);
  chart("kahoots-visits", (th) => ({
    type: "bar", stacked: true,
    dates: monthly.map((r) => [`${r.month}-01`, monthEnd(`${r.month}-01`)]), data: { labels: monthly.map((r) => month(r.month)), datasets: [
      bar("Visits from people", monthly.map((r) => r.people_visits), th.s[0]),
      { ...bar("Robots (visits minus people)", monthly.map((r) => r.visits - r.people_visits), th.s[1]), borderWidth: { top: 0, bottom: 2, left: 0, right: 0 } },
    ] },
    tooltip: { footer: (items) => `All visits: ${num(monthly[items[0].dataIndex].visits)}` },
  }));
  chart("kahoots-forms", (th) => ({
    type: "bar",
    dates: monthly.map((r) => [`${r.month}-01`, monthEnd(`${r.month}-01`)]), data: { labels: monthly.map((r) => month(r.month)), datasets: [bar("Form fills", monthly.map((r) => r.form_fills), th.s[0])] },
  }));
  table($("kahoots-quarter"), { rows: quarter, columns: [
    { key: "metric", label: "", sort: false },
    { key: "q2", label: "Q2 2026", num: true, fmt: num, sort: false },
    { key: "q3", label: "Q3 2026", num: true, fmt: num, sort: false },
  ] });
}

// ---------- Tab 5: Infrasity ----------

function renderInfrasity(monthly) {
  const sep = monthly.find((r) => r.month === "2026-09"), aug = monthly.find((r) => r.month === "2026-08");
  // where the report rounds or states its own change, show it exactly as reported
  const shown = (r, key, fmt) => (r.reported && r.reported[key]) || fmt(r[key]);
  const reportedChange = (key) => { const c = sep.reported && sep.reported[`${key}_change`]; return c ? `<div class="delta ${c.startsWith("+") ? "good" : "bad"}">${c} (${c.startsWith("+") ? "better" : "worse"})</div>` : null; };
  const monthCard = (label, key, fmt, lower) => card(label, shown(sep, key, fmt), `August: ${shown(aug, key, fmt)}${lower ? ". Lower is better" : ""}`, reportedChange(key) || cmpDelta(sep[key], aug[key], lower));
  $("infrasity-cards").innerHTML =
    monthCard("Clicks", "google_clicks", num) +
    monthCard("Times Google showed us", "times_shown", num) +
    monthCard("Click rate", "click_rate_pct", (v) => pct(v)) +
    monthCard("Average spot on Google", "avg_spot", spot, true);
  const note = () => { $("infrasity-monthly-note").textContent = periodMode !== "month" ? "Infrasity reported by month, so this tab compares September with August." : ""; };
  note(); monthlyTabs.push(note);
  table($("infrasity-table"), { rows: monthly.map((r) => ({ ...r, name: month(r.month) })), columns: [
    { key: "name", label: "Month", sort: false },
    { key: "google_clicks", label: "Clicks", num: true, fmt: num, sort: false },
    { key: "times_shown", label: "Times Google showed us", num: true, fmt: (v, r) => (r.reported && r.reported.times_shown) || num(v), sort: false },
    { key: "click_rate_pct", label: "Click rate", num: true, fmt: (v) => pct(v), sort: false },
    { key: "avg_spot", label: "Average spot on Google", num: true, fmt: spot, sort: false },
  ] });
  chart("infrasity-forge", (th) => ({
    type: "bar",
    dates: monthly.map((r) => [`${r.month}-01`, monthEnd(`${r.month}-01`)]), data: { labels: monthly.map((r) => month(r.month)), datasets: [bar("Google clicks on Forge pages", monthly.map((r) => r.forge_page_clicks), th.s[0])] },
  }));
}

// ---------- Look up: one page or campaign, its numbers for the period above ----------

let lookupLoad = null;   // data/lookup.json is loaded the first time the tab is opened
// Words as short scrambled codes, the same as the pull scripts make (FNV-1a, 32 bits), so emails, lists and
// posts can be matched without the public files holding their names or text
function wordCode(w) {
  let h = 0x811c9dc5;
  for (const b of new TextEncoder().encode(w)) h = Math.imul(h ^ b, 0x01000193) >>> 0;
  return h.toString(16).padStart(8, "0");
}

// Emails, lists and LinkedIn posts for a search, each its own section, never added into the website numbers
function lookupExtras(el, q, hub, li, kp) {
  el.innerHTML = "";
  const words = [...new Set(q.toLowerCase().replace(/^https?:\/\//, "").split(/[^a-z0-9]+/).filter((w) => w.length >= 3))];
  if (!words.length) return;
  const codes = words.map(wordCode);
  const hit = (list) => codes.every((c) => list.includes(c));
  const pct = (v) => (v == null ? "-" : `${v.toFixed(1)}%`);
  // HubSpot's personal placeholders, shown as plain words: "{{ contact.firstname }}" becomes [first name]
  const readable = (subject) => subject.replace(/\{\{\s*contact\.firstname\s*\}\}/g, "[first name]")
    .replace(/\{\{\s*personalization_token\('[^']*',\s*'([^']*)'\)\s*\}\}/g, "[$1]").replace(/\{\{[^}]*\}\}/g, "[personal detail]");
  const said = `"${esc(q.trim())}"`;
  const sections = [];
  const section = (id, title, rows, empty, source, spec) => {
    sections.push(`<div class="panel"><h3>${title}</h3><div id="${id}">${rows.length ? "" : `<p class="muted">${empty}</p>`}</div><p class="source">${source}</p></div>`);
    return () => { if (rows.length) table($(id), { rows, pageSize: 15, ...spec }); };
  };
  const emails = (hub.emails && hub.emails.rows || []).filter((e) => hit(e.words)).map((e) => ({ ...e, subject: readable(e.subject) }));
  const lists = (hub.lists && hub.lists.rows || []).filter((l) => hit(l.words)).map((l, i) => ({ ...l, label: `List ${i + 1}` }));
  // Kumar's times seen comes from the LinkedIn exports' top posts, matched by the post's address
  const slug = (url) => (url || "").replace(/[?#].*$/, "").replace(/-(share|activity|ugcPost)-.*$/, "");
  const seenBy = {};
  [["Jul to Sep", li.kumar.top_by_seen], ...li.kumar_october.periods.map((p) => [p.label, p.top_by_seen])].forEach(([label, rows]) =>
    (rows || []).forEach((r) => { const k = slug(r.link); if (!seenBy[k] || r.seen > seenBy[k].seen) seenBy[k] = { seen: r.seen, label }; }));
  const posts = [
    ...(li.company.posts || []).filter((p) => hit(p.words || [])).map((p) => ({ date: p.created, from: "Company page", title: p.title, link: p.link,
      seen: p.seen, seenText: num(p.seen), clicks: p.clicks, reactions: p.likes, comments: p.comments })),
    ...(kp.posts || []).filter((p) => hit(p.words || [])).map((p) => { const s2 = seenBy[slug(p.link)];
      return { date: p.date, from: "Kumar", title: p.title, link: p.link, seen: s2 ? s2.seen : null, seenText: s2 ? `${num(s2.seen)} (${s2.label})` : "-",
        clicks: null, reactions: p.reactions, comments: p.comments }; }),
  ];
  const n0 = (v) => (v == null ? "-" : num(v));
  const draws = [
    section("lookup-emails", `HubSpot marketing emails matching ${said}`, emails, "No marketing emails match.",
      `Source: HubSpot, emails sent since ${dayYear(hub.start_date)}, updated ${dayYear(hub.pulled_at.slice(0, 10))}. Rates are opens and clicks out of emails delivered. The subject line shows, never who it went to. Emails aimed at named target accounts are left out.`,
      { search: "subjects", sortKey: "sent_on", columns: [
        { key: "sent_on", label: "Sent", fmt: (v) => dayYear(v), csv: (r) => r.sent_on },
        { key: "subject", label: "Subject", search: true },
        { key: "sends", label: "Sends", num: true, fmt: num }, { key: "opens", label: "Opens", num: true, fmt: num }, { key: "clicks", label: "Clicks", num: true, fmt: num },
        { key: "open_rate_pct", label: "Open rate", num: true, fmt: pct }, { key: "click_rate_pct", label: "Click rate", num: true, fmt: pct } ] }),
    section("lookup-lists", `HubSpot lists matching ${said}`, lists, "No lists match.",
      `Source: HubSpot lists updated since ${dayYear(hub.start_date)}, counted ${dayYear(hub.pulled_at.slice(0, 10))}. List names often hold people's and companies' names, so they don't show. Target-account and automatic lists are left out.`,
      { sortKey: "people", columns: [
        { key: "label", label: "List", sort: false }, { key: "kind", label: "Kind" }, { key: "people", label: "People", num: true, fmt: n0 },
        { key: "updated_on", label: "Last updated", fmt: (v) => dayYear(v), csv: (r) => r.updated_on } ] }),
    section("lookup-posts", `LinkedIn posts mentioning ${said}`, posts, "No company page or Kumar posts mention it.",
      `Sources: company page posts from LinkedIn exports, ${range(li.company.start_date, li.company.end_date)}. Kumar's posts from his public profile, read with Apify on ${dayYear(kp.as_of)}. His times seen comes from LinkedIn exports, only for posts in their top posts, for the period named.`,
      { search: "posts", sortKey: "date", columns: [
        { key: "date", label: "Posted", fmt: (v) => dayYear(v), csv: (r) => r.date },
        { key: "from", label: "From", search: true },
        { key: "title", label: "Post", search: true, fmt: (v, r) => `<a href="${esc(r.link)}" target="_blank" rel="noopener">${esc(v)}</a>`, csv: (r) => `${r.title} (${r.link})` },
        { key: "seen", label: "Times seen", num: true, fmt: (v, r) => esc(r.seenText), csv: (r) => r.seenText },
        { key: "clicks", label: "Clicks", num: true, fmt: n0 }, { key: "reactions", label: "Reactions", num: true, fmt: n0 },
        { key: "comments", label: "Comments", num: true, fmt: n0 } ] }),
  ];
  el.innerHTML = sections.join("");
  draws.forEach((f) => f());
}

function openLookup() {
  if (!lookupLoad) lookupLoad = Promise.all(["lookup.json", "hubspot.json", "linkedin.json", "kumar_post_list.json"].map(load))
    .then(([d, hub, li, kp]) => renderLookup(d, { hub, li, kp }))
    .catch((err) => { $("lookup-status").textContent = `Couldn't load the look up numbers: ${err.message}`; });
  return lookupLoad;
}

function renderLookup(d, extra) {
  const gaLast = lastFullDayPacific(d.end_date, d.pulled_at);
  const idx = (date) => Math.round((toDate(date) - toDate(d.start_date)) / 864e5);
  const isAsset = (path) => d.asset_pages.some((a) => `${path}/`.startsWith(a));
  const plain = (t) => t.toLowerCase().replace(/[^a-z0-9]+/g, " ");
  const SHOW = 15;        // never more than this many matches on screen
  const WAIT_MS = 350;    // search once typing pauses this long

  // Prepared once, when the tab opens: the text each page and campaign is found by, and each one's
  // own rows, so a search only adds up the rows of what it found.
  // Pages match on their address and their title; the homepage also goes by these names.
  const HOME = ["home", "homepage", "home page", "opsera.ai", "/"];
  const pageText = d.pages.map((p, i) => plain(`${p} ${d.titles[i]}${p === "/" ? " home homepage" : ""}`));
  const pageLower = d.pages.map((p) => p.toLowerCase());
  const campText = d.campaigns.map(plain);
  const campLower = d.campaigns.map((c) => c.toLowerCase());
  const asset = d.pages.map(isAsset);
  const group = (rows, col, size) => {
    const out = Array.from({ length: size }, () => []);
    rows.forEach((r) => { if (r[col] >= 0) out[r[col]].push(r); });
    return out;
  };
  const P = d.pages.length, C = d.campaigns.length;
  const rows = {
    pageVisits: group(d.visits, 1, P), campVisits: group(d.campaign_visits, 1, C),
    pageForms: group(d.forms, 1, P), campForms: group(d.forms, 2, C),
    pageClicks: group(d.gsc, 1, P), both: group(d.page_campaign_visits, 1, P),
  };
  const sum = (list, col, per, keep) => {
    if (!per) return null;
    const a = idx(per.start), b = idx(per.end);
    let t = 0;
    for (const r of list) if (r[0] >= a && r[0] <= b && (!keep || keep(r))) t += r[col];
    return t;
  };

  // The chosen period for Google Analytics and for Search Console, and what each page and campaign did in it,
  // worked out once per period
  let now = null;
  const period = () => {
    if (now && now.mode === periodMode) return now;
    const p = periodsFor(periodMode, d.start_date, gaLast), g = periodsFor(periodMode, d.start_date, d.gsc_last_day);
    const cur = p.cur || { start: d.start_date, end: gaLast }, gcur = g.cur || { start: d.start_date, end: d.gsc_last_day };
    const t = { mode: periodMode, p, g, cur, gcur,
      page: { visits: new Array(P).fill(0), engaged: new Array(P).fill(0), forms: new Array(P).fill(0), clicks: new Array(P).fill(0) },
      camp: { visits: new Array(C).fill(0), engaged: new Array(C).fill(0), forms: new Array(C).fill(0) } };
    const [a, b, ga, gb] = [idx(cur.start), idx(cur.end), idx(gcur.start), idx(gcur.end)];
    d.visits.forEach((r) => { if (r[0] >= a && r[0] <= b) { t.page.visits[r[1]] += r[3]; t.page.engaged[r[1]] += r[4]; } });
    d.campaign_visits.forEach((r) => { if (r[0] >= a && r[0] <= b) { t.camp.visits[r[1]] += r[3]; t.camp.engaged[r[1]] += r[4]; } });
    d.forms.forEach((r) => { if (r[0] >= a && r[0] <= b) { t.page.forms[r[1]] += r[3]; if (r[2] >= 0) t.camp.forms[r[2]] += r[3]; } });
    d.gsc.forEach((r) => { if (r[0] >= ga && r[0] <= gb) t.page.clicks[r[1]] += r[2]; });
    return (now = t);
  };
  const of = (m, t) => (m.kind === "page"
    ? { visits: t.page.visits[m.i], engaged: t.page.engaged[m.i], forms: t.page.forms[m.i], clicks: t.page.clicks[m.i] }
    : { visits: t.camp.visits[m.i], engaged: t.camp.engaged[m.i], forms: t.camp.forms[m.i], clicks: 0 });

  const find = (q) => {
    const bare = q.trim().toLowerCase().replace(/^https?:\/\//, "").replace(/^www\./, "");
    const rest = bare.startsWith("opsera.ai") ? bare.slice("opsera.ai".length) || "/" : bare;
    const home = HOME.includes(bare.replace(/(.)\/$/, "$1"));
    const path = home ? "/" : rest.split("?")[0].replace(/(.)\/$/, "$1");
    const words = plain(rest).split(" ").filter(Boolean);
    if (!words.length && !home) return [];
    const all = (text) => words.length > 0 && words.every((w) => text.includes(w));
    const out = [];
    for (let i = 0; i < P; i++) {
      const exact = pageLower[i] === path;
      if (exact || all(pageText[i])) out.push({ kind: "page", i, exact });
    }
    for (let i = 0; i < C; i++) {
      const exact = campLower[i] === q.trim().toLowerCase();
      if (exact || all(campText[i])) out.push({ kind: "campaign", i, exact });
    }
    return out;
  };
  const name = (m) => (m.kind === "page" ? d.pages[m.i] : d.campaigns[m.i]);
  const label = (m) => `${m.kind === "page" ? "Page" : "Campaign"}: ${name(m)}`;
  // a page name opens the live page on opsera.ai in a new tab; campaigns and "(not set)" aren't pages
  const pageLink = (path) => (path.startsWith("/")
    ? `<a href="https://opsera.ai${encodeURI(path)}" target="_blank" rel="noopener">${esc(path)}</a>` : esc(path));
  const tile = (title, value, sub, per, curPer) => {
    const a = value(per.cur || curPer), b = per.prev ? value(per.prev) : null;
    return card(title, num(a), [per.prev ? `${per.prevName}: ${num(b)}` : "", sub].filter(Boolean).join(". "), cmpDelta(a, b));
  };
  const sources = (t, showGsc) => {
    $("lookup-source").textContent = `Source: Google Analytics, ${range(t.cur.start, t.cur.end)} (Pacific time).` +
      (t.p.prev ? ` Compared with ${range(t.p.prev.start, t.p.prev.end)}.` : "");
    $("lookup-gsc-source").textContent = showGsc ? `Google clicks: Search Console, ${range(t.gcur.start, t.gcur.end)}.` +
      (t.g.prev ? ` Compared with ${range(t.g.prev.start, t.g.prev.end)}.` : "") : "Search Console counts Google clicks by page, so campaigns don't have them.";
  };

  let options = [], chosen = null, live = [];

  // One page or campaign
  const showOne = (m) => {
    $("lookup-from-panel").hidden = false; $("lookup-each-panel").hidden = true;
    const t = period(), page = m.kind === "page";
    const visits = page ? rows.pageVisits[m.i] : rows.campVisits[m.i];
    const forms = page ? rows.pageForms[m.i] : rows.campForms[m.i];
    const clicks = page ? rows.pageClicks[m.i] : [];
    $("lookup-title").innerHTML = page ? pageLink(name(m)) : esc(name(m));
    $("lookup-subtitle").textContent = page ? (d.titles[m.i] || "Page on opsera.ai") : "Campaign (utm_campaign in Google Analytics)";
    $("lookup-cards").innerHTML =
      tile("Visits", (per) => sum(visits, 3, per), page ? "Landed on this page" : "From this campaign", t.p, t.cur) +
      tile("Engaged visits", (per) => sum(visits, 4, per), "", t.p, t.cur) +
      (page && asset[m.i] ? tile("Downloads", (per) => sum(forms, 3, per), "Form fills on this asset page", t.p, t.cur)
        : tile("Form fills", (per) => sum(forms, 3, per), "", t.p, t.cur) +
          (page ? "" : tile("Downloads", (per) => sum(forms, 3, per, (r) => asset[r[1]]), "On report, white paper, ebook and guide pages", t.p, t.cur))) +
      (page ? tile("Google clicks", (per) => sum(clicks, 2, per), `Times shown: ${num(sum(clicks, 3, t.gcur))}`, t.g, t.gcur) : "");
    sources(t, page);
    const from = {};
    const a = idx(t.cur.start), b = idx(t.cur.end);
    visits.forEach((r) => {
      if (r[0] < a || r[0] > b) return;
      const key = page ? channelName(d.channels[r[2]]) : d.sources[r[2]];
      const row = from[key] || (from[key] = { name: key, visits: 0, engaged: 0 });
      row.visits += r[3]; row.engaged += r[4];
    });
    const list = Object.values(from);
    if (list.length) {
      table($("lookup-from"), { rows: list, sortKey: "visits", pageSize: SHOW, columns: [
        { key: "name", label: page ? "Came from" : "Source / type" },
        { key: "visits", label: "Visits", num: true, fmt: num },
        { key: "engaged", label: "Engaged visits", num: true, fmt: num },
      ] });
    } else {
      $("lookup-from").innerHTML = `<p class="muted">No visits in this period.</p>`;
    }
    $("lookup-from-source").textContent = `Source: Google Analytics, ${range(t.cur.start, t.cur.end)} (Pacific time).`;
  };

  // All matches: every matching page and campaign added up, each visit and form fill counted once
  const showAll = (list) => {
    $("lookup-from-panel").hidden = true; $("lookup-each-panel").hidden = false;
    const t = period();
    const pageIds = list.filter((m) => m.kind === "page").map((m) => m.i), campIds = list.filter((m) => m.kind === "campaign").map((m) => m.i);
    const pageSet = new Set(pageIds), campSet = new Set(campIds);
    const visitsIn = (col) => (per) => {
      let v = 0;
      for (const i of pageIds) v += sum(rows.pageVisits[i], col, per) - sum(rows.both[i], col, per, (r) => campSet.has(r[2]));
      for (const i of campIds) v += sum(rows.campVisits[i], col, per);
      return per ? v : null;
    };
    const formsIn = (assetsOnly) => (per) => {
      const keep = (r) => !assetsOnly || asset[r[1]];
      let f = 0;
      for (const i of pageIds) f += sum(rows.pageForms[i], 3, per, keep);
      for (const i of campIds) f += sum(rows.campForms[i], 3, per, (r) => !pageSet.has(r[1]) && keep(r));   // not already counted with its page
      return per ? f : null;
    };
    const clicksIn = (per) => { let c = 0; for (const i of pageIds) c += sum(rows.pageClicks[i], 2, per); return per ? c : null; };
    $("lookup-title").textContent = `All matches for "${$("lookup-q").value.trim()}"`;
    $("lookup-subtitle").textContent = `${num(pageIds.length)} page${pageIds.length === 1 ? "" : "s"} and ${num(campIds.length)} campaign${campIds.length === 1 ? "" : "s"}, added up`;
    $("lookup-cards").innerHTML = tile("Visits", visitsIn(3), "Each visit counted once", t.p, t.cur) + tile("Engaged visits", visitsIn(4), "", t.p, t.cur) +
      tile("Form fills", formsIn(false), "", t.p, t.cur) + tile("Downloads", formsIn(true), "On report, white paper, ebook and guide pages", t.p, t.cur) +
      (pageIds.length ? tile("Google clicks", clicksIn, "Matching pages only", t.g, t.gcur) : "");
    sources(t, pageIds.length > 0);
    if (!pageIds.length) $("lookup-gsc-source").textContent = "";
    const top = list.slice(0, SHOW).map((m) => ({ name: label(m), path: m.kind === "page" ? d.pages[m.i] : null,
      title: m.kind === "page" ? d.titles[m.i] : "", ...of(m, t), clicks: m.kind === "page" ? t.page.clicks[m.i] : null }));
    table($("lookup-each"), { rows: top, sortKey: "visits", pageSize: SHOW, columns: [
      { key: "name", label: "Match", fmt: (v, r) => (r.path ? `Page: ${pageLink(r.path)}` : esc(v)) },
      { key: "title", label: "Page title" },
      { key: "visits", label: "Visits", num: true, fmt: num },
      { key: "engaged", label: "Engaged visits", num: true, fmt: num },
      { key: "forms", label: "Form fills", num: true, fmt: num },
      { key: "clicks", label: "Google clicks", num: true, fmt: num },
    ] });
    $("lookup-each-source").textContent = (list.length > SHOW ? `The ${SHOW} busiest of ${num(list.length)} matches. The totals above add up all ${num(list.length)}. ` : "") +
      `Source: Google Analytics, ${range(t.cur.start, t.cur.end)} (Pacific time). Google clicks: Search Console, ${range(t.gcur.start, t.gcur.end)}.`;
  };

  const show = () => {
    $("lookup-result").hidden = !chosen;
    if (chosen) (chosen.kind === "all" ? showAll(chosen.list) : showOne(chosen));
  };

  const search = (keep) => {
    const q = $("lookup-q").value;
    if (view.q !== q.trim()) { view.q = q.trim(); saveView(); }
    const t = period();
    const found = find(q);
    const busy = (m) => { const s = of(m, t); return s.visits + s.forms + s.clicks > 0; };
    live = found.filter(busy).sort((a, b) => b.exact - a.exact || of(b, t).visits - of(a, t).visits);
    const left = found.length - live.length;
    // "All matches" comes first, and is picked unless the search names one page or campaign exactly
    options = live.length > 1 ? [{ kind: "all", list: live }, ...live.slice(0, 8)] : live;
    let pick = live.length > 1 && !live[0].exact ? 0 : options.indexOf(live[0]);
    if (keep && chosen) {   // a new period keeps what was picked, when it's still there
      const same = options.findIndex((m) => m.kind === chosen.kind && m.i === chosen.i);
      if (same >= 0) pick = same;
    }
    chosen = options[pick] || null;
    // a page option is "Page", which picks it, then its address, which opens it (a link can't sit inside a button)
    $("lookup-matches").innerHTML = options.length > 1 ? options.map((m, i) => (m.kind === "page"
      ? `<span class="match-opt${i === pick ? " on" : ""}" data-opt="${i}"><button data-i="${i}" aria-label="Show ${esc(name(m))}">Page:</button>${pageLink(name(m))}</span>`
      : `<button data-i="${i}" data-opt="${i}" class="${i === pick ? "on" : ""}">${m.kind === "all" ? `All matches (${num(m.list.length)})` : esc(label(m))}</button>`)).join("") : "";
    $("lookup-status").textContent = !q.trim() ? "Type above to look something up."
      : !found.length ? `No data for "${q.trim()}".`
      : !live.length ? `No data for "${q.trim()}" in this period.`
      : left ? `Not showing ${num(left)} match${left === 1 ? "" : "es"} with no visits, form fills or Google clicks in this period.` : "";
    if (extra) lookupExtras($("lookup-extras"), q, extra.hub, extra.li, extra.kp); else $("lookup-extras").innerHTML = "";
    show();
  };

  let timer;
  $("lookup-q").addEventListener("input", () => {
    clearTimeout(timer);
    $("lookup-status").textContent = $("lookup-q").value.trim() ? "Searching when you pause typing..." : "";
    timer = setTimeout(search, WAIT_MS);
  });
  $("lookup-q").addEventListener("keydown", (e) => { if (e.key === "Enter") { clearTimeout(timer); search(); } });
  $("lookup-matches").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;   // the page address is a link and opens the page instead
    chosen = options[Number(b.dataset.i)];
    $("lookup-matches").querySelectorAll("[data-opt]").forEach((x) => x.classList.toggle("on", x.dataset.opt === b.dataset.i));
    show();
  });
  monthlyTabs.push(() => search(true));
  if (view.q) $("lookup-q").value = view.q;   // a search from the address
  search();
}

// ---------- Team metrics: each person's metrics against their baseline and goal ----------

let teamLoad = null;   // data/team_metrics.json is loaded the first time the tab is opened
function openTeam() {
  if (!teamLoad) teamLoad = load("team_metrics.json").then(renderTeam)
    .catch((err) => { $("team-status").textContent = `Couldn't load the team metrics: ${err.message}`; });
  return teamLoad;
}

function renderTeam(t) {
  const monthName = (m) => MONTH_NAMES[toDate(`${m}-01`).getUTCMonth()];
  const baseLabel = `${monthName(t.baseline.months[0]).slice(0, 3)} to ${monthName(t.baseline.months[t.baseline.months.length - 1]).slice(0, 3)} average`;
  const zone = { "Google Analytics": "Pacific time", "LinkedIn exports": "UTC" };
  const tile = (m) => {
    const along = m.goal && m.so_far != null
      ? `<div class="goal-bar" aria-hidden="true"><span style="width:${Math.min(100, m.goal_share_pct)}%"></span></div>
         <div class="sub">${m.goal_share_pct.toFixed(0)}% of goal, with ${m.days_counted} of ${t.month_days} days counted</div>`
      : "";
    return `<div class="card"><div class="label">${esc(m.label)}</div>
      <div class="value">${m.so_far == null ? "-" : num(m.so_far)}</div>
      <div class="sub">This month so far. Baseline: ${num(m.baseline)} a month (${baseLabel})</div>
      <div class="sub">Goal: ${m.goal ? `${num(m.goal)} a month` : "To set"}</div>${along}${m.without_email_robots
        ? `<div class="sub">Without email robots: ${num(m.without_email_robots.so_far)} so far. Baseline: ${num(m.without_email_robots.baseline)} a month</div>` : ""}</div>`;
  };
  const sources = (metrics) => {
    const seen = new Map();
    metrics.forEach((m) => seen.set(m.source, m));
    return [...seen.values()].map((m) => (m.so_far_end
      ? `${m.source}, ${range(m.so_far_start, m.so_far_end)} (${zone[m.source] || "Pacific time"})`
      : `${m.source}, no data for ${monthName(t.month)} yet`)).join(". ");
  };
  const person = (p) => `<h3 class="section-title person-name">${esc(p.name)}</h3>` + (p.sections.length ? "" : `<p class="muted">Metrics coming</p>`) + p.sections.map((sec) => `
    <h4>${esc(sec.title)}</h4>
    <div class="cards">${sec.metrics.map(tile).join("")}</div>
    <p class="source">${sec.metrics.length > 1 && new Set(sec.metrics.map((m) => m.source)).size > 1 ? "Sources" : "Source"}: ${esc(sources(sec.metrics))}. Baseline: ${monthName(t.baseline.months[0])} to ${monthName(t.baseline.months[t.baseline.months.length - 1])} ${t.baseline.months[0].slice(0, 4)}.</p>`).join("");
  // the person in the address, or the first person in team.json
  let who = [...t.people.map((p) => p.name), "Everyone"].includes(view.person) ? view.person : (t.people[0] ? t.people[0].name : "");
  const draw = () => {
    $("team-body").innerHTML = t.people.filter((p) => who === "Everyone" || p.name === who).map(person).join("");
  };
  $("team-people").innerHTML = [...t.people.map((p) => p.name), "Everyone"].map((n) =>
    `<button data-who="${esc(n)}" class="${n === who ? "on" : ""}">${esc(n)}</button>`).join("");
  $("team-people").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    who = b.dataset.who;
    view.person = who; saveView();
    $("team-people").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    draw();
  });
  $("team-status").textContent = "";
  draw();
}

// ---------- Content: one row per blog post, report, white paper, eBook, guide and comparison page ----------

const CONTENT_TYPES = [
  ["blog", "Blog", /^\/blog\/[a-z0-9-]+$/],
  ["report", "Report", /^\/resources\/report\/[a-z0-9-]+$/],
  ["white_paper", "White paper", /^\/resources\/white-papers\/[a-z0-9-]+$/],
  ["ebook", "eBook", /^\/resources\/ebooks\/[a-z0-9-]+$/],
  ["guide", "Guide (knowledge base)", /^\/knowledge-base\/(?!category\/)[a-z0-9-]+\/[a-z0-9-]+$/],
  ["comparison", "Comparison", /^\/(resources\/comparison-guides|comparison-guides|comparison)\/[a-z0-9-]+$/],
];

let contentLoad = null;   // loads the page and deal data the first time the tab is opened
// ---------- Events: one row per event. HubSpot lists and meetings, and Google Analytics form fills, side by side ----------

function renderEvents(hub, leads, sf) {
  const rows = hub.event_rows || [];
  if (!rows.length) { $("events-table").innerHTML = `<p class="muted">No data</p>`; return; }
  const fills = {};
  Object.values(leads.lines).forEach((l) => l.pages.forEach((p) => { fills[p.page] = (fills[p.page] || 0) + p.count; }));
  const list = rows.map((e) => ({ ...e,
    when: e.first_day ? (e.first_day === e.last_day ? dayYear(e.first_day) : range(e.first_day, e.last_day)) : "Date not known",
    form_fills: e.pages.length ? e.pages.reduce((t, p) => t + (fills[p] || 0), 0) : null,
    sf_meetings: sf?.event_meetings?.find((x) => x.key === e.key)?.people ?? null }));
  const dash = (v) => (v == null ? "-" : num(v));
  table($("events-table"), { rows: list, search: "events", sortKey: "first_day", columns: [
    { key: "name", label: "Event", search: true, fmt: (v, r) => `${esc(v)}<br><span class="muted">${esc(r.kind)}. ${r.when}</span>`, csv: (r) => `${r.name} | ${r.kind} | ${r.first_day || "Date not known"}${r.last_day && r.last_day !== r.first_day ? ` to ${r.last_day}` : ""}` },
    { key: "signed_up", label: "Signed up", num: true, fmt: dash },
    { key: "attended", label: "Attended", num: true, fmt: dash },
    { key: "form_fills", label: "Event page form fills", num: true, fmt: dash },
    { key: "meetings_after", label: "Meetings afterwards", num: true, fmt: dash },
    { key: "people_with_meeting", label: "People with a meeting", num: true, fmt: dash },
    { key: "meetings_upcoming", label: "Meetings booked for later", num: true, fmt: dash },
    { key: "sf_meetings", label: "Meetings from this event (Salesforce)", num: true, fmt: dash },
    { key: "note", label: "Note", search: true, sort: false },
  ] });
  $("events-source").textContent = `Sources: HubSpot lists and calendar meetings, updated ${dayYear((hub.event_rows_pulled_at || hub.pulled_at).slice(0, 10))}. Event page form fills: Google Analytics, ${range(leads.start_date, leads.end_date)} (Pacific time).`;
}

// ---------- Campaigns: 1 row per campaign. Google Analytics link tags and HubSpot, side by side ----------

let campaignsLoad = null;
function openCampaigns() {
  if (!campaignsLoad) campaignsLoad = Promise.all(["lookup.json", "hubspot.json"].map(load)).then(([d, hub]) => renderCampaigns(d, hub))
    .catch((err) => { $("campaigns-status").textContent = `Couldn't load the campaign numbers: ${err.message}`; });
  return campaignsLoad;
}
// HubSpot puts its campaign number in front of the name in link tags ("50406442-DG-FY27-..."); one name per campaign
const campaignKey = (n) => { const x = n.replace(/^\d+-/, "").trim(); return /\s/.test(x) ? x : x.replace(/\+/g, " "); };   // "Magic+Quadrant+2026" is a link tag with + for spaces
const leftOutCampaign = (n) => /\b(abm|abx|microsite)\b/i.test(n) || /^ET-/.test(n) || /^[a-z0-9-]+\.[a-z]{2,}$/i.test(n);
function renderCampaigns(d, hub) {
  const gaLast = lastFullDayPacific(d.end_date, d.pulled_at);
  const dayOf = (i) => addDays(d.start_date, i);
  let mode = "period";
  const draw = () => {
    const cur = mode === "all" ? { start: d.start_date, end: gaLast } : (periodsFor(periodMode, d.start_date, gaLast).cur || { start: d.start_date, end: gaLast });
    const rows = {};
    const row = (name) => rows[campaignKey(name)] || (rows[campaignKey(name)] = { name: campaignKey(name), visits: 0, engaged: 0, forms: 0,
      emails: 0, sends: 0, opens: 0, clicks: 0, deals: 0, amount: 0 });
    const inRange = (date) => date >= cur.start && date <= cur.end;
    for (const [day, c, , v, e] of d.campaign_visits) {
      if (!inRange(dayOf(day)) || leftOutCampaign(campaignKey(d.campaigns[c]))) continue;
      const r = row(d.campaigns[c]); r.visits += v; r.engaged += e;
    }
    for (const [day, , c, n] of d.forms) {
      if (c < 0 || !inRange(dayOf(day)) || leftOutCampaign(campaignKey(d.campaigns[c]))) continue;
      row(d.campaigns[c]).forms += n;
    }
    for (const e of (hub.emails?.rows || [])) {
      if (!e.campaign || !inRange(e.sent_on) || leftOutCampaign(e.campaign)) continue;
      const r = row(e.campaign); r.emails += 1; r.sends += e.sends; r.opens += e.opens; r.clicks += e.clicks;
    }
    for (const x of (hub.campaign_deals || [])) {
      if (!x.campaign || !inRange(x.date) || leftOutCampaign(x.campaign)) continue;
      const r = row(x.campaign); r.deals += 1; r.amount += x.amount;
    }
    const list = Object.values(rows).filter((r) => r.visits || r.forms || r.sends || r.deals);
    $("campaigns-status").textContent = list.length ? "" : "No campaigns in this period.";
    $("campaigns-title").textContent = `Every campaign, ${range(cur.start, cur.end)}`;
    table($("campaigns-table"), { rows: list, search: "campaigns", sortKey: "visits", columns: [
      { key: "name", label: "Campaign", search: true },
      { key: "visits", label: "Visits", num: true, fmt: num },
      { key: "engaged", label: "Engaged visits", num: true, fmt: num },
      { key: "forms", label: "Form fills", num: true, fmt: num },
      { key: "emails", label: "Emails sent", num: true, fmt: num },
      { key: "sends", label: "Email sends", num: true, fmt: num },
      { key: "opens", label: "Email opens", num: true, fmt: num },
      { key: "clicks", label: "Email clicks", num: true, fmt: num },
      { key: "deals", label: "Deals", num: true, fmt: num },
      { key: "amount", label: "Deal amount", num: true, fmt: money },
    ] });
    $("campaigns-source").textContent = `Visits, engaged visits and form fills: Google Analytics, ${range(cur.start, cur.end)} (Pacific time). Form fills leave out job applications.`;
    drawAdsFor(cur);
    $("campaigns-hub-source").textContent = `Emails and deals: HubSpot, updated ${dayYear(hub.pulled_at.slice(0, 10))}. Emails by the day they were sent; deals by the day they were created, open or won.`;
  };
  $("campaigns-range").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    mode = b.dataset.r;
    $("campaigns-range").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    draw();
  });
  monthlyTabs.push(draw);   // follows the period switch
  draw();
}

// ---------- Pipeline tab: marketing sourced and influenced pipeline, and campaign-influenced meetings ----------
// From Salesforce exports, counts and totals only. Sales-only deals and every name stay out of the file.

function renderPipeline(sf) {
  // Counts and totals only, built from Salesforce exports kept outside the repo (scripts/build_salesforce_pipeline.py)
  const months = sf.months, sum = (list, k) => list.reduce((t, r) => t + r[k], 0);
  const days = [...new Set(Object.values(sf.exports))].sort();
  const exports = days.length === 2 && days[0].slice(0, 7) === days[1].slice(0, 7) ? `${Number(days[0].slice(8))} and ${dayYear(days[1])}` : days.map(dayYear).join(" and ");
  const when = range(sf.opportunities_from, sf.opportunities_to);
  // The cards follow the period switch, by the day each deal was created, against the period before
  const dealsLast = addDays(sf.exports.opportunities, -1), deals = (n) => `${num(n)} deal${n === 1 ? "" : "s"}`;
  const bucketMetric = (label, k) => ({ label, value: rangeSum(sf.days, `${k}_deals`), fmt: deals,
    sub: (a, b) => `${money(rangeSum(sf.days, `${k}_value`)(a, b))} pipeline` });
  compare({ id: "pipe", start: sf.opportunities_cover_from, last: dealsLast,
    source: (a, b) => `Source: Salesforce opportunities created ${range(a, b)}, open and won, exported ${exports}. The export starts on ${dayYear(sf.opportunities_cover_from)}. Updated when new exports arrive, not on Mondays.`,
    metrics: [bucketMetric("Marketing sourced (estimate)", "sourced"), bucketMetric("Marketing influenced", "influenced"), bucketMetric("Booking agency", "agency"),
      { label: "No contact linked", value: rangeSum(sf.days, "nocontact_deals"), fmt: deals, lowerIsBetter: true, sub: "Count only" }] });   // more deals without a contact is a data gap
  $("pipe-undercount").textContent = "Marketing sourced is an estimate: it rests on Salesforce's Primary Campaign Source, a starting point that isn't reliable on its own. " +
    `Marketing numbers are undercounted: ${sf.share_without_contact_pct}% of open and won opportunities have no contact attached in Salesforce, so their campaigns can't be seen. ` +
    `A campaign counts only if the person joined it within ${sf.window_days} days before the deal was created; ${num(sf.deals_left_out_by_window)} deal${sf.deals_left_out_by_window === 1 ? " was" : "s were"} left out by this rule. ` +
    `For ${num(sf.deals_join_date_unknown)} deals the exports don't show when the person joined, so those still count.`;

  let group = "month";
  const drawTime = () => {
    const by = {};
    for (const m of months) {
      const key = group === "month" ? m.month : m.quarter;
      const x = by[key] || (by[key] = { key, label: group === "month" ? month(m.month) : m.quarter.replace(/ Q(\d)/, (q, n) => ` Q${n} (${["Feb to Apr", "May to Jul", "Aug to Oct", "Nov to Jan"][n - 1]})`),
        sourced_deals: 0, sourced_value: 0, influenced_deals: 0, influenced_value: 0, agency_deals: 0, agency_value: 0, nocontact_deals: 0 });
      ["sourced_deals", "sourced_value", "influenced_deals", "influenced_value", "agency_deals", "agency_value", "nocontact_deals"].forEach((k) => { x[k] += m[k] || 0; });
    }
    table($("pipe-time"), { rows: Object.values(by), sortKey: "key", columns: [
      { key: "key", label: group === "month" ? "Month" : "Quarter", fmt: (v, r) => esc(r.label), csv: (r) => r.label },
      { key: "sourced_deals", label: "Sourced deals (estimate)", num: true, fmt: num },
      { key: "sourced_value", label: "Sourced value (estimate)", num: true, fmt: money },
      { key: "influenced_deals", label: "Influenced deals", num: true, fmt: num },
      { key: "influenced_value", label: "Influenced value", num: true, fmt: money },
      { key: "agency_deals", label: "Booking agency deals", num: true, fmt: num },
      { key: "agency_value", label: "Booking agency value", num: true, fmt: money },
      { key: "nocontact_deals", label: "No contact linked deals", num: true, fmt: num },
    ] });
  };
  $("pipe-period").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    group = b.dataset.g;
    $("pipe-period").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    drawTime();
  });
  drawTime();
  $("pipe-time-source").textContent = `Source: Salesforce opportunities created ${when}, exported ${exports}. Sourced and influenced are never added together.`;

  table($("pipe-campaigns"), { rows: sf.campaigns.map((c) => ({ ...c, bucket: { sourced: "Marketing sourced (estimate)", influenced: "Marketing influenced", agency: "Booking agency" }[c.bucket] })),
    search: "campaigns", sortKey: "value", columns: [
      { key: "bucket", label: "Counts as", search: true },
      { key: "campaign", label: "Campaign", search: true, fmt: (v, r) => esc(v) + (r.flag ? `<br><span class="muted">Counted as marketing for now, ${esc(r.flag)}</span>` : "") },
      { key: "deals", label: "Deals", num: true, fmt: num },
      { key: "value", label: "Value", num: true, fmt: money },
    ] });
  $("pipe-campaigns-source").textContent = `Source: Salesforce Primary Campaign Source, Attrib First and Last Campaign, and campaign touches on each opportunity, created ${when}. Target-account campaign names are hidden.`;

  // Deals a person still needs to check: a campaign joined just outside the 90 days, or more than 1 source
  table($("pipe-review"), { rows: sf.to_review || [], sortKey: "date", columns: [
    { key: "date", label: "Created", fmt: (v) => dayYear(v), csv: (r) => r.date },
    { key: "amount", label: "Amount", num: true, fmt: money },
    { key: "stage", label: "Stage", search: true },
    { key: "counted_as", label: "Counted as now", search: true },
    { key: "campaigns", label: "Campaigns", fmt: (v) => v.map(esc).join("<br>"), csv: (r) => r.campaigns.join(" | ") },
    { key: "reasons", label: "Why it needs a check", fmt: (v) => v.map(esc).join("<br>"), csv: (r) => r.reasons.join(" | ") },
  ] });
  $("pipe-review-source").textContent = `Source: Salesforce opportunities created ${when}, open and won. ${num((sf.to_review || []).length)} deals. No company or person names.`;

  const mt = sf.meetings, OUT = ["Meeting Held", "Meeting Cancelled", "Meeting No Show - New Date TBD", "Meeting Changed", "Not recorded"];
  const outcome = (k) => rangeSum(mt.days, (r) => r.outcomes[k] || 0);
  compare({ id: "pipe-meet", start: mt.since, last: addDays(sf.exports.meetings, -1),
    source: (a, b) => `Source: Salesforce campaign members with a meeting on ${range(a, b)}, exported ${dayYear(sf.exports.meetings)}.`,
    metrics: [{ label: "People with a meeting", value: rangeSum(mt.days, "people"), fmt: num, sub: "After joining a marketing campaign" },
      { label: "Held", value: outcome("Meeting Held"), fmt: num }, { label: "Cancelled", value: outcome("Meeting Cancelled"), fmt: num, lowerIsBetter: true },
      { label: "No outcome recorded", value: outcome("Not recorded"), fmt: num, lowerIsBetter: true }] });
  table($("pipe-meet-months"), { rows: mt.months.map((m) => ({ key: m.month, label: month(m.month), people: m.people, ...Object.fromEntries(OUT.map((k) => [k, m.outcomes[k] || 0])) })),
    sortKey: "key", columns: [
      { key: "key", label: "Month of the meeting", fmt: (v, r) => esc(r.label), csv: (r) => r.label },
      { key: "people", label: "People", num: true, fmt: num },
      { key: "Meeting Held", label: "Held", num: true, fmt: num },
      { key: "Meeting Cancelled", label: "Cancelled", num: true, fmt: num },
      { key: "Meeting No Show - New Date TBD", label: "No show", num: true, fmt: num },
      { key: "Meeting Changed", label: "Moved", num: true, fmt: num },
      { key: "Not recorded", label: "No outcome recorded", num: true, fmt: num },
    ] });
  $("pipe-meet-source").textContent = `Source: Salesforce campaign members with a meeting, since ${dayYear("2026-04-01")}, exported ${dayYear(sf.exports.meetings)}.`;
  table($("pipe-meet-campaigns"), { rows: mt.campaigns, search: "campaigns", sortKey: "people", columns: [
    { key: "campaign", label: "Campaign", search: true, fmt: (v, r) => esc(v) + (r.flag ? `<br><span class="muted">Counted as marketing for now, ${esc(r.flag)}</span>` : "") },
    { key: "people", label: "People with a meeting", num: true, fmt: num },
  ] });
}

function openContent() {
  if (!contentLoad) contentLoad = Promise.all(["lookup.json", "hubspot.json"].map(load)).then(([d, hub]) => renderContent(d, hub))
    .catch((err) => { $("content-status").textContent = `Couldn't load the content numbers: ${err.message}`; });
  return contentLoad;
}

function renderContent(d, hub) {
  const gaLast = lastFullDayPacific(d.end_date, d.pulled_at);
  const idx = (date) => Math.round((toDate(date) - toDate(d.start_date)) / 864e5);
  const typeOf = (path) => CONTENT_TYPES.find(([, , re]) => re.test(path));
  const pieces = d.pages.map((path, i) => ({ i, path, type: typeOf(path) })).filter((x) => x.type);
  const asset = (path) => d.asset_pages.some((a) => `${path}/`.startsWith(a));
  const bare = (title) => (title || "").replace(/\s*[-—|]\s*Opsera\s*$/i, "").trim().toLowerCase();
  let type = CONTENT_TYPES.some(([k]) => k === view.type) ? view.type : "all";   // from the address, if it names one

  const draw = () => {
    const p = periodsFor(periodMode, d.start_date, gaLast), g = periodsFor(periodMode, d.start_date, d.gsc_last_day);
    const cur = p.cur || { start: d.start_date, end: gaLast }, gcur = g.cur || { start: d.start_date, end: d.gsc_last_day };
    const [a, b, ga, gb] = [idx(cur.start), idx(cur.end), idx(gcur.start), idx(gcur.end)];
    const stats = {};
    const row = (i) => stats[i] || (stats[i] = { visits: 0, engaged: 0, forms: 0, clicks: 0, from: {} });
    d.visits.forEach((r) => { if (r[0] >= a && r[0] <= b) { const s2 = row(r[1]); s2.visits += r[3]; s2.engaged += r[4];
      const ch = channelName(d.channels[r[2]]); s2.from[ch] = (s2.from[ch] || 0) + r[3]; } });
    d.forms.forEach((r) => { if (r[0] >= a && r[0] <= b) row(r[1]).forms += r[3]; });
    d.gsc.forEach((r) => { if (r[0] >= ga && r[0] <= gb) row(r[1]).clicks += r[2]; });
    // deals by the month they were created: every month the period touches
    const months = new Set();
    for (let m = cur.start.slice(0, 7); m <= cur.end.slice(0, 7); m = addDays(monthEnd(`${m}-01`), 1).slice(0, 7)) months.add(m);
    const deals = (hub.deal_lines || []).filter((x) => months.has(x.month));
    const dealsFor = (piece, all) => (all ? hub.deal_lines || [] : deals)
      .filter((x) => x.first_page === piece.path || (x.first_form && bare(x.first_form) === bare(d.titles[piece.i])));
    const dealWords = (list) => (list.length ? `${list.length} (${money(list.reduce((t2, z) => t2 + z.amount, 0))})` : "0");
    const rows = pieces.filter((x) => type === "all" || x.type[0] === type).map((x) => {
      const s2 = stats[x.i] || { visits: 0, engaged: 0, forms: 0, clicks: 0, from: {} };
      const dl = dealsFor(x), dlAll = dealsFor(x, true);
      const top = Object.entries(s2.from).sort((u, v) => v[1] - u[1]).slice(0, 3)
        .map(([name, n]) => `${name.replace(/ \(.*\)$/, "")} ${Math.round((n / s2.visits) * 100)}%`).join(", ");
      const title = d.titles[x.i] && !/^page not found/i.test(d.titles[x.i]) ? d.titles[x.i].replace(/\s*[-—|]\s*Opsera\s*$/i, "") : x.path;
      return { kind: x.type[1], title, path: x.path, find: `${title} ${x.path}`, visits: s2.visits, engaged: s2.engaged, clicks: s2.clicks, from: top || "-",
        forms: s2.forms, formsLabel: asset(x.path) ? "downloads" : "form fills", deals: dl.length, dealsAll: dlAll.length,
        dealSort: dlAll.reduce((t2, z) => t2 + z.amount, 0) * 1000 + dl.length,   // sorts by deals since 1 Apr, then this period
        dealText: `This period: ${dealWords(dl)}. Since ${day(hub.start_date)}: ${dealWords(dlAll)}` };
    });
    const shown = rows.filter((r) => r.visits || r.forms || r.clicks || r.deals || r.dealsAll);
    const typeName = type === "all" ? "Every piece" : CONTENT_TYPES.find(([k]) => k === type)[1];
    $("content-title").textContent = `${typeName}, ${range(cur.start, cur.end)}`;
    table($("content-table"), { rows: shown, search: "titles and addresses", sortKey: "visits", pageSize: 25, columns: [
      { key: "find", label: "Piece", search: true, fmt: (v, r) => `<a href="https://opsera.ai${encodeURI(r.path)}" target="_blank" rel="noopener">${esc(r.title)}</a><br><small class="muted">${esc(r.kind)}: ${esc(r.path)}</small>` },
      { key: "visits", label: "Visits", num: true, fmt: num },
      { key: "engaged", label: "Engaged visits", num: true, fmt: num },
      { key: "clicks", label: "Google clicks", num: true, fmt: num },
      { key: "from", label: "Where visits came from", sort: false },
      { key: "forms", label: "Downloads or form fills", num: true, fmt: num },
      { key: "dealSort", label: "Deals it led to", num: true, fmt: (v, r) => esc(r.dealText), csv: (r) => r.dealText },
    ] });
    const left = rows.length - shown.length;
    $("content-status").textContent = left ? `Not showing ${num(left)} piece${left === 1 ? "" : "s"} with no visits, form fills, Google clicks or deals in this period.` : "";
    $("content-source").textContent = `Source: Google Analytics for visits, where they came from and form fills, ${range(cur.start, cur.end)} (Pacific time).`;
    $("content-gsc-source").textContent = `Google clicks: Search Console, ${range(gcur.start, gcur.end)}.`;
    $("content-deals-source").textContent = `Deals: HubSpot marketing deals created in ${[...months].map((m) => month(m)).join(", ")}, updated ${dayYear(hub.pulled_at.slice(0, 10))}. ${num(deals.length)} deal${deals.length === 1 ? "" : "s"} in those months, ${num(shown.reduce((t2, r) => t2 + r.deals, 0))} of them traced to a piece here. Since ${dayYear(hub.start_date)}: ${num((hub.deal_lines || []).length)} deals, ${num(shown.reduce((t2, r) => t2 + r.dealsAll, 0))} traced to a piece.`;
  };

  $("content-type").innerHTML = [["all", "All"], ...CONTENT_TYPES.map(([k, label]) => [k, label])].map(([k, label]) =>
    `<button data-type="${k}" class="${k === type ? "on" : ""}">${esc(label)}</button>`).join("");
  $("content-type").addEventListener("click", (e) => {
    const bt = e.target.closest("button"); if (!bt) return;
    type = bt.dataset.type;
    view.type = type; saveView();
    $("content-type").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === bt));
    draw();
  });
  monthlyTabs.push(draw);
  draw();
}

// ---------- To do: the list in TODO.md, shown as it is (the file is the only copy) ----------

let todoLoad = null;
function openTodo() {
  if (!todoLoad) todoLoad = fetch("TODO.md", { cache: "no-cache" }).then(async (r) => {
    if (!r.ok) throw new Error(`TODO.md (${r.status})`);
    const text = await r.text();
    let html = "", open = false;
    const close = () => { if (open) { html += "</ul>"; open = false; } };
    for (const line of text.split("\n")) {
      const head = line.match(/^##\s+(.+)/), item = line.match(/^- \[( |x|X)\]\s+(.+)/);
      if (head) { close(); html += `<h3>${esc(head[1])}</h3>`; }
      else if (item) {
        if (!open) { html += `<ul class="todo">`; open = true; }
        const done = item[1].toLowerCase() === "x";
        html += `<li class="${done ? "done" : ""}">${done ? "Done: " : ""}${esc(item[2])}</li>`;
      }
    }
    close();
    $("todo").innerHTML = html || `<p class="muted">Nothing on the list.</p>`;
    const items = (text.match(/^- \[[ xX]\]/gm) || []).length, done = (text.match(/^- \[[xX]\]/gm) || []).length;
    $("todo-source").textContent = `Source: TODO.md in the dashboard's repo. ${num(items - done)} to do, ${num(done)} done.`;
  }).catch((err) => { $("todo").innerHTML = `<p class="error">Couldn't load the list: ${esc(err.message)}</p>`; });
  return todoLoad;
}

// ---------- tabs and theme ----------

// ---------- Google rankings for key pages (Google search tab), loaded when the tab opens ----------

let rankingsOpened = false;
function openRankings() {
  if (rankingsOpened) return;
  rankingsOpened = true;
  load("rankings.json").then(renderRankings).catch((e) => { $("rank-chart-source").textContent = e.message; });
}
function renderRankings(d) {
  const last = d.last_day_with_data;
  const weeks = [];
  for (let w = weekStart(d.start_date); w <= last; w = addDays(w, 7)) weeks.push(w);
  const latest = weeks[weeks.length - 1], before = weeks[weeks.length - 5];
  const latestFull = addDays(latest, 6) <= last;
  const wkLabel = (w) => `${day(w < d.start_date ? d.start_date : w)} to ${day(addDays(w, 6) > last ? last : addDays(w, 6))}`;
  const name = (p) => p.title.replace(/\s*[|—–-]\s*Opsera\s*$/i, "").replace(/^Opsera\s*[—–-]\s*/i, "") || p.page;
  const spotOf = (p, w) => p.weeks.find((x) => x.week === w)?.avg_spot ?? null;
  const pageLink = (p) => `<a href="https://opsera.ai${encodeURI(p.page)}" target="_blank" rel="noopener">${esc(name(p))}</a><br><span class="muted">${esc(p.page)}</span>`;
  const src = `Source: Google Search Console, ${range(d.start_date, last)}. Weeks run Monday to Sunday.`;

  const pick = $("rank-page");
  pick.innerHTML = ["Homepage", "Product", "Blog", "Resource"].map((g) => {
    const list = d.pages.filter((p) => p.group === g);
    return list.length ? `<optgroup label="${g === "Homepage" ? "Homepage" : `${g}s`}">${list.map((p) => `<option value="${esc(p.page)}">${esc(name(p))}</option>`).join("")}</optgroup>` : "";
  }).join("");
  let cur = d.pages[0];
  chart("rank-chart", (th) => ({
    type: "line", reverse: true, ytitle: "Higher on the chart is a better spot", yfmt: (v) => v,
    dates: weeks.map((w) => [w, addDays(w, 6)]),
    data: { labels: weeks.map(wkLabel), datasets: [{ ...line("Average spot on Google", weeks.map((w) => spotOf(cur, w)), th.s[0]), pointRadius: 3, spanGaps: false }] },
    tooltip: { label: (c) => ` Average spot: ${spot(c.parsed.y)}`,
      afterLabel: (c) => { const x = cur.weeks.find((w) => w.week === weeks[c.dataIndex]); return x ? ` Shown ${num(x.times_shown)} times, ${num(x.clicks)} clicks` : ""; } },
  }));
  const fillPage = () => {
    $("rank-title").textContent = `Google rankings: ${name(cur)}`;
    $("rank-chart-source").textContent = `${src} A gap means Google didn't show the page that week.`;
    $("rank-searches-title").textContent = `Top searches for ${name(cur)}, last 3 months`;
    table($("rank-searches"), { rows: cur.searches, sortKey: "clicks", columns: [
      { key: "search", label: "Search" },
      { key: "clicks", label: "Clicks", num: true, fmt: num },
      { key: "times_shown", label: "Times Google showed it", num: true, fmt: num },
      { key: "avg_spot", label: "Average spot", num: true, fmt: spot },
    ] });
    $("rank-searches-source").textContent = `Source: Google Search Console, ${range(d.searches_from, last)}. The 10 searches with the most clicks, then the most times shown. Google hides rare searches.`;
    draw(charts.find((c) => c.id === "rank-chart"));
  };
  pick.addEventListener("change", () => { cur = d.pages.find((p) => p.page === pick.value); fillPage(); });
  fillPage();

  const rows = d.pages.map((p) => {
    const now = spotOf(p, latest), then = spotOf(p, before);
    return { p, page: name(p), group: p.group, now, then, change: now != null && then != null ? Math.round((then - now) * 10) / 10 : null,
      clicks: p.weeks.find((x) => x.week === latest)?.clicks ?? 0, visits: p.visits_since_new_site };
  });
  table($("rank-table"), { rows, search: "pages", sortKey: null, columns: [
    { key: "page", label: "Page", search: true, fmt: (v, r) => pageLink(r.p), csv: (r) => `${r.page} | ${r.p.page}` },
    { key: "group", label: "Kind", search: true },
    { key: "now", label: `Spot, ${wkLabel(latest)}`, num: true, fmt: spot },
    { key: "then", label: `Spot, ${wkLabel(before)}`, num: true, fmt: spot },
    { key: "change", label: "Change", num: true, fmt: (v) => (v == null ? "-" : v > 0 ? `Up ${v.toFixed(1)}` : v < 0 ? `Down ${(-v).toFixed(1)}` : "No change"), csv: (r) => r.change ?? "" },
    { key: "clicks", label: `Clicks, ${wkLabel(latest)}`, num: true, fmt: num },
    { key: "visits", label: "Visits since 30 Sep", num: true, fmt: num },
  ] });
  $("rank-table-source").textContent = `Source: Google Search Console for spots and clicks, ${range(d.start_date, last)}${latestFull ? "" : " (the last week isn't finished)"}. Visits since 30 Sep are from Google Analytics, for blogs and resources only. Up means a better spot.`;
}

function showTab(name) {
  if (!$(`tab-${name}`)) name = "team";   // the dashboard opens on Team metrics, the first tab (agreed 28 Oct 2026)
  view.tab = name; saveView();
  document.querySelectorAll(".tab").forEach((s) => { s.hidden = s.id !== `tab-${name}`; });
  document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === name));
  const on = document.querySelector(`.tabs button[data-tab="${name}"]`);   // on phones, slide the row so the open tab shows
  if (on && tabRow.scrollWidth > tabRow.clientWidth) { tabRow.scrollLeft = on.offsetLeft - (tabRow.clientWidth - on.offsetWidth) / 2; tabArrows(); }
  charts.forEach((c) => c.instance && c.instance.resize());
  document.querySelectorAll(`#tab-${name} [id$="-cmp-cards"]`).forEach(countUp);
  if (name === "lookup") openLookup();
  if (name === "team") openTeam();
  if (name === "todo") openTodo();
  if (name === "content") openContent();
  if (name === "search") openRankings();
  if (name === "campaigns") openCampaigns();
  // the footer views have no tab in the row, so start them at the top of the page
  if (!document.querySelector(`.tabs button[data-tab="${name}"]`)) window.scrollTo(0, 0);
}
// Phones scroll the tab row; the arrows show only when there are tabs out of sight on that side
const tabRow = document.querySelector(".tabs");
function tabArrows() {
  const scrollable = tabRow.scrollWidth > tabRow.clientWidth + 1;
  document.querySelector(".tabs-arrow.left").hidden = !scrollable || tabRow.scrollLeft <= 2;
  document.querySelector(".tabs-arrow.right").hidden = !scrollable || tabRow.scrollLeft + tabRow.clientWidth >= tabRow.scrollWidth - 2;
}
document.querySelectorAll(".tabs-arrow").forEach((b) => b.addEventListener("click", () => {
  tabRow.scrollBy({ left: (b.classList.contains("left") ? -1 : 1) * tabRow.clientWidth * 0.7, behavior: calm.matches ? "auto" : "smooth" });
}));
tabRow.addEventListener("scroll", tabArrows, { passive: true });
addEventListener("resize", tabArrows);
tabArrows();
document.querySelectorAll("details.more").forEach((el) => el.addEventListener("toggle", () => charts.forEach((c) => c.instance && c.instance.resize())));
document.querySelector(".tabs").addEventListener("click", (e) => {
  const b = e.target.closest("button"); if (!b) return;
  showTab(b.dataset.tab);
});
// A link with only a tab (the footer links, or an older link) keeps the rest of the view.
// A full link pasted into this page reloads it, so every setting is applied from the start.
addEventListener("hashchange", () => {
  const [tab, query] = location.hash.slice(1).split("?");
  if (query !== undefined && location.hash !== viewAddress()) location.reload();
  else showTab(tab);
});
$("copy-link").addEventListener("click", () => {
  saveView();
  const done = (t) => { $("copy-link").textContent = t; setTimeout(() => { $("copy-link").textContent = "Copy link to this view"; }, 2000); };
  navigator.clipboard.writeText(location.href).then(() => done("Link copied"), () => { window.prompt("Copy this link:", location.href); });
});

const THEMES = ["auto", "light", "dark"];
function applyTheme(t) {
  if (t === "auto") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = t;
  $("theme-toggle").textContent = `Theme: ${t[0].toUpperCase()}${t.slice(1)}`;
  try { localStorage.setItem("theme", t); } catch (e) {}
  charts.forEach(draw);
}
$("theme-toggle").addEventListener("click", () => {
  const cur = document.documentElement.dataset.theme || "auto";
  applyTheme(THEMES[(THEMES.indexOf(cur) + 1) % 3]);
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => charts.forEach(draw));
$("theme-toggle").textContent = `Theme: ${(document.documentElement.dataset.theme || "auto").replace(/^./, (c) => c.toUpperCase())}`;

// ---------- start ----------

(async () => {
  try {
    const [gsc, ga, leads, li, yt, kp, est, hub, km, kq, inf] = await Promise.all(
      ["search_console.json", "analytics.json", "leads.json", "linkedin.json", "youtube.json", "kumar_posts.json", "linkedin_estimate.json", "hubspot.json", "kahoots_monthly.json", "kahoots_quarter.json", "infrasity_monthly.json"].map(load));
    showTab(view.tab);
    $("pulled").textContent = `Google numbers updated ${dayYear(gsc.pulled_at.slice(0, 10))} at ${gsc.pulled_at.slice(11, 16)} IST.`;
    renderSearch(gsc);
    renderVisits(ga);
    renderLeads(leads);
    renderLinkedIn(li);
    renderKumarPosts(kp);
    renderLinkedInVisits(ga);
    renderLinkedInEstimate(est, ga);
    renderLinkedInPath(ga);
    renderJourney(ga, leads, hub, gsc);
    renderAeo(ga, hub);
    renderLeadsHubspot(hub);
    load("salesforce_pipeline.json").catch(() => null).then((sf) => renderEvents(hub, leads, sf));
    load("salesforce_pipeline.json").then(renderPipeline)
      .catch(() => { $("pipe-cmp-cards").innerHTML = `<div class="card"><div class="label">Marketing pipeline</div><div class="sub">No data</div></div>`; });
    renderYouTube(yt, ga);
    renderKahoots(km, kq);
    renderInfrasity(inf);
  } catch (err) {
    $("error").hidden = false;
    $("error").textContent = `Something went wrong loading the numbers: ${err.message}`;
    console.error(err);
  }
})();
