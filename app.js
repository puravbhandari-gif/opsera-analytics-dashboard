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
const range = (a, b) => (a === b ? dayYear(a) : `${day(a)} to ${dayYear(b)}`);
const month = (m) => toDate(`${m}-01`).toLocaleDateString("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });
const shortPage = (p) => p.replace(/^https?:\/\/(www\.)?opsera\.ai/, "") || "/";
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

async function load(name) {
  const r = await fetch(`data/${name}`, { cache: "no-cache" });
  if (!r.ok) throw new Error(`Couldn't load data/${name} (${r.status})`);
  return r.json();
}

function card(label, value, sub = "", extra = "") {
  return `<div class="card"><div class="label">${label}</div><div class="value">${value}</div>${extra}${sub ? `<div class="sub">${sub}</div>` : ""}</div>`;
}

// ---------- tables: sortable and searchable ----------

function table(el, { columns, rows, search, sortKey, sortDir = -1, pageSize = 25 }) {
  let q = "", key = sortKey, dir = sortDir, shown = pageSize;
  el.innerHTML = `${search ? `<div class="table-tools"><input type="search" placeholder="Search ${search}" aria-label="Search ${search}"><span class="muted"></span></div>` : ""}
    <div class="table-wrap"><table><thead><tr>${columns.map((c) =>
      `<th class="${c.num ? "num " : ""}${c.sort === false ? "" : "sortable"}" data-k="${c.key}" scope="col">${c.label}</th>`).join("")}</tr></thead><tbody></tbody></table></div>
    <button class="more" type="button" hidden>Show more</button>`;
  const body = el.querySelector("tbody"), more = el.querySelector(".more"), count = el.querySelector(".table-tools .muted");

  function render() {
    let list = rows.filter((r) => !q || columns.some((c) => c.search && String(r[c.key]).toLowerCase().includes(q)));
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
  render();
}

// ---------- charts: rebuilt when the theme changes ----------

const charts = [];
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

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
        labels: { color: t.ink, boxWidth: 12, boxHeight: 12, useBorderRadius: true, borderRadius: 2, font: { size: 12 } } },
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
  c.instance = new Chart($(c.id), { type: cfg.type, data: cfg.data, options: base });
}
const line = (label, data, color) => ({ label, data, borderColor: color, backgroundColor: color, borderWidth: 2, pointRadius: 0, pointHoverRadius: 5, tension: 0.25 });
const bar = (label, data, color) => ({ label, data, backgroundColor: color, borderColor: css("--surface"), borderWidth: { top: 0, left: 0, right: 0, bottom: 0 }, borderRadius: 4, borderSkipped: "start", maxBarThickness: 44 });

// ---------- Week by week / month by month, one switch for every tab ----------

let periodMode = "week";
try { const saved = localStorage.getItem("period"); if (saved === "month" || saved === "day") periodMode = saved; } catch (e) {}
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
      return { type: "bar", whole: true, data: { labels: bk.map((b) => b.label),
        datasets: spec.metrics.map((mm, i) => bar(mm.label, bk.map((b) => mm.value(b.start, b.end)), th.s[i])) } };
    }
    const values = bk.map((b) => m.value(b.start, b.end));
    const asLine = m.whole === false;
    return { type: asLine ? "line" : "bar", whole: m.whole !== false, yfmt: m.yfmt, reverse: m.lowerIsBetter && m.flip,
      ytitle: m.lowerIsBetter && m.flip ? "Higher on chart = better spot" : undefined,
      data: { labels: bk.map((b) => b.label), datasets: [asLine ? { ...line(m.label, values, th.s[0]), pointRadius: 4 } : bar(m.label, values, th.s[0])] },
      tooltip: { label: (c) => ` ${m.label}: ${m.fmt(c.parsed.y ?? c.parsed.x)}` } };
  });
  fillCompare(spec);
}

function fillCompare(spec) {
  const p = periodsFor(periodMode, spec.start, spec.last);
  const title = $(`${spec.id}-cmp-chart`)?.closest(".panel").querySelector(".period-title");
  if (title) title.textContent = { day: "Day by day", week: "Week by week", month: "Month by month" }[periodMode];
  if (!p.cur) {
    $(`${spec.id}-cmp-cards`).innerHTML = `<div class="card"><div class="label">Not enough days yet</div><div class="sub">${p.none}</div></div>`;
    $(`${spec.id}-cmp-source`).textContent = spec.source(spec.start, spec.last);
  } else {
    $(`${spec.id}-cmp-cards`).innerHTML = spec.metrics.map((m) => {
      const cur = m.value(p.cur.start, p.cur.end), prev = p.prev ? m.value(p.prev.start, p.prev.end) : null;
      const sub = p.prev ? `${p.prevName}: ${m.fmt(prev)}` : p.none;
      return card(m.label, m.fmt(cur), [sub, m.sub].filter(Boolean).join(". "), cmpDelta(cur, prev, m.lowerIsBetter));
    }).join("");
    $(`${spec.id}-cmp-source`).textContent = spec.source(p.cur.start, p.cur.end) +
      (p.prev ? ` Compared with ${range(p.prev.start, p.prev.end)}.` : "");
  }
  if ($(`${spec.id}-cmp-chart-source`)) $(`${spec.id}-cmp-chart-source`).textContent = spec.source(spec.start, spec.last);
}

function setPeriodMode(mode) {
  periodMode = mode;
  try { localStorage.setItem("period", mode); } catch (e) {}
  $("period-mode").querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.mode === mode));
  comparisons.forEach((spec) => { fillCompare(spec); const c = charts.find((x) => x.id === `${spec.id}-cmp-chart`); if (c) draw(c); });
  monthlyTabs.forEach((fn) => fn());
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
  return `<div class="delta ${better ? "good" : "bad"}">${change > 0 ? "+" : ""}${change.toFixed(1)}% vs last week (${better ? "better" : "worse"})</div>`;
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
    type: "line",
    data: { labels: d.daily.map((r) => day(r.date)), datasets: [line(metrics[m].label, d.daily.map((r) => r[m]), th.s[0])] },
    reverse: metrics[m].reverse, yfmt: metrics[m].yfmt, ytitle: metrics[m].reverse ? "Higher on chart = better spot" : undefined,
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
  "Direct": "Direct (typed the address, or Google can't tell)",
  "Organic Search": "Search engines (mostly Google)",
  "Email": "Email",
  "Referral": "Other websites",
  "Organic Social": "Social media (LinkedIn and others)",
  "AI Assistant": "AI tools (ChatGPT, Gemini, Perplexity)",
  "Unassigned": "Not labelled by Google",
  "Paid Search": "Paid search ads",
  "Paid Social": "Paid social ads",
  "Organic Shopping": "Shopping search",
  "Organic Video": "Video sites",
  "Display": "Display ads",
  "Cross-network": "Google ad network",
};
const channelName = (c) => CHANNELS[c] || c;

function renderVisits(d) {
  const src = "Source: Google Analytics, opsera.ai 2026";
  const when = `${range(d.start_date, d.end_date)}, US Pacific time`;
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
    type: "line",
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
  const emailRows = d.daily.map((r) => ({ date: r.date, visits: emailByDay[r.date] || 0 }));
  compare({ id: "visits", start: d.start_date, last: lastFullDayPacific(d.end_date, d.pulled_at),
    source: (a, b) => `${src}, ${range(a, b)}, US Pacific time.`, metrics: [
      { label: "Engaged visits", value: engaged, fmt: num },
      { label: "All visits", value: all, fmt: num, sub: "Includes robots" },
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
  const src = "Source: Google Analytics, opsera.ai 2026, HubSpot form fills";
  const when = `${range(d.start_date, d.end_date)}, US Pacific time`;
  $("leads-source").textContent = `${src}, ${when}.`;
  const leadCard = (k) => card(d.lines[k].label, num(d.lines[k].count), LEAD_NOTES[k]);
  $("leads-cards").innerHTML = ["demo", "events", "gartner_offer", "contact"].map(leadCard).join("");
  const jobs = (d.left_out || []).reduce((t, r) => t + r.count, 0);
  $("leads-more-cards").innerHTML = leadCard("other") + card("Job applications", num(jobs), "Not counted as leads");
  $("leads-more-source").textContent = `${src}, ${when}.`;

  $("leads-core-source").textContent = `${src}, ${when}.`;
  const removed = "Form removed when the new site went live on 30 Sep. Visitors now go to Book a demo.";
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
    type: "bar",
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
    source: (a, b) => `${src}, ${range(a, b)}, US Pacific time.`,
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
    label: `${day(s < start ? start : s)} to ${day(addDays(s, 6) > end ? end : addDays(s, 6))}`, value: out[s],
  }));
}

function metricChart(id, segId, rows, metrics, colors) {
  let m = Object.keys(metrics)[0];
  chart(id, (th) => ({
    type: "line",
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
    card("People reached", num(k.reached), "Different members who saw a post") +
    card("Engagements", num(sum(k.daily, "engagements")), "Reactions, comments, shares and clicks combined") +
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
    type: "bar", data: { labels: coWeeks.map((w) => w.label), datasets: [bar("Followers gained", coWeeks.map((w) => w.value), th.s[0])] },
  }));
  $("li-co-followers-source").textContent = coSrc;

  chart("li-co-visits", (th) => ({
    type: "line",
    data: { labels: co.visitors_daily.map((r) => day(r.date)), datasets: [
      line("All company page views", co.visitors_daily.map((r) => r.views_total), th.s[0]),
      line("Overview page views", co.visitors_daily.map((r) => r.views_overview), th.s[1]),
      line("Jobs page views", co.visitors_daily.map((r) => r.views_jobs), th.s[2]),
    ] },
  }));
  $("li-co-visits-source").textContent = coSrc;

  table($("li-co-posts"), { rows: co.posts, search: "posts", sortKey: "seen", columns: [
    { key: "title", label: "Post", search: true, fmt: postLink },
    { key: "posted_by", label: "Posted by", search: true },
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
    card("People reached", num(k.reached), "Different members who saw a post") +
    card("Engagements", num(sum(k.daily, "engagements")), "Reactions, comments, shares and clicks combined") +
    card("Followers gained", num(sum(k.followers_daily, "gained"))) +
    card("Total followers", num(k.total_followers), `On ${dayYear(k.total_followers_date)}`);

  metricChart("li-k-daily", "li-k-metric", k.daily, {
    seen: [["Times seen", "seen"]], engagements: [["Engagements", "engagements"]],
  }, [0]);
  $("li-k-daily-source").textContent = kSrc;

  const kWeeks = weekly(k.followers_daily, "gained", d.start_date, d.end_date);
  chart("li-k-followers", (th) => ({
    type: "bar", data: { labels: kWeeks.map((w) => w.label), datasets: [bar("Followers gained", kWeeks.map((w) => w.value), th.s[0])] },
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
  const counting = oct.still_counting.map(dayYear).join(", ");
  $("li-ko-counting").textContent = counting ? `${counting} was still being counted when these were exported, so its numbers may change.` : "";
  let period = "7d";
  const drawPeriod = () => {
    const p = periods[period];
    const pSrc = `Source: LinkedIn export, Kumar Chivukula's profile, ${range(p.start_date, p.end_date)}.`;
    $("li-ko-cards").innerHTML =
      card("Times seen", num(p.seen)) +
      card("People reached", num(p.reached), "Different members who saw a post") +
      card("Engagements", num(sum(p.daily, "engagements")), "Reactions, comments, shares and clicks combined") +
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
    data: { labels: periods[period].daily.map((r) => day(r.date)), datasets: [bar("Times seen", periods[period].daily.map((r) => r.seen), th.s[0])] },
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
  const src = `Source: ${kp.source}`;
  const months = kp.months, cur = months[months.length - 1], prev = months[months.length - 2];
  const curName = `${monthName(cur.month + "-01")}${cur.so_far ? " so far" : ""}`;
  const fill = () => {
    $("li-k2-posts").innerHTML = [["Own posts", "own_posts"], ["Reposts", "reposts"]].map(([label, key]) =>
      card(`${label}, ${curName}`, num(cur[key]), `${monthName(prev.month + "-01")}: ${num(prev[key])}`)).join("");
    $("li-k2-posts-note").textContent = periodMode !== "month" ? "Posts are counted by month, so they don't change with the day or week view." : "";
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
  const src = "Source: Google Analytics, opsera.ai 2026";
  const when = (a, b) => `${range(a, b)}, US Pacific time`;
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
  $("li-web-groups-source").textContent = `${src}, HubSpot form fills, ${when(ga.start_date, ga.end_date)}.`;
  const otherTags = li.tags.filter((r) => r.group === "untagged" && !["(referral)", "(not set)", ""].includes(r.sessionCampaignName));
  $("li-web-other-tags").textContent = otherTags.length
    ? `Untagged also holds ${num(otherTags.reduce((t2, r) => t2 + r.visits, 0))} visits with other tags: ${otherTags.map((r) => `"${r.sessionCampaignName}" (${num(r.visits)})`).join(", ")}.` : "";

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
  $("li-web-tags-source").textContent = `${src}, ${when(ga.start_date, ga.end_date)}. Sources counted: ${li.sources_counted.join(", ")}.`;
}

// ---------- Customer journey: visit -> demo page -> demo form (Google Analytics) -> contact -> meeting -> deal (HubSpot) ----------

const JOURNEY_CHANNELS = { all: "All", search: "Google search", linkedin: "LinkedIn", email: "Email", events: "Events",
  paid: "Paid ads", ai: "AI tools", youtube: "YouTube", direct: "Direct" };
const money = (v) => (v == null ? "-" : `$${nf.format(Math.round(v))}`);

function renderJourney(ga, leads, hub) {
  const gaLast = lastFullDayPacific(ga.end_date, ga.pulled_at);
  const start = ga.start_date;
  const hubWhen = `HubSpot, last updated ${dayYear(hub.pulled_at.slice(0, 10))}`;
  const booked = hub.meetings_daily.filter((r) => r.kind === "booked");

  // Top: marketing-driven demo requests, meetings and new pipeline, against the period before
  compare({ id: "journey", start, last: gaLast,
    source: (a, b) => `Sources: Google Analytics (demo requests) and HubSpot (meetings, pipeline), ${range(a, b)}, US Pacific time.`,
    metrics: [
      { label: "Demo requests", value: rangeSum(leads.daily, "demo"), fmt: num, sub: "Website demo form" },
      { label: "Meetings booked", value: rangeSum(booked, "count"), fmt: num, sub: "With marketing contacts" },
      { label: "New pipeline", value: rangeSum(hub.deals_daily, "amount"), fmt: money, sub: "Deals from marketing contacts" },
    ] });

  // One funnel, for the chosen channel and the period the switch at the top is set to
  const step = (ch, a, b) => {
    const inCh = (r) => ch === "all" || r.channel === ch;
    const inRange = (r) => r.date >= a && r.date <= b;
    const gaSum = (k) => ga.journey.filter((r) => r.channel === ch && inRange(r)).reduce((t2, r) => t2 + r[k], 0);
    const hubSum = (rows, k) => rows.filter((r) => inCh(r) && r.demo && inRange(r)).reduce((t2, r) => t2 + r[k], 0);
    return [
      { label: "Visits", value: gaSum("visits"), src: "Google Analytics" },
      { label: "Saw the demo page", value: gaSum("demo_page"), src: "Google Analytics" },
      { label: "Filled the demo form", value: gaSum("demo_form"), src: "Google Analytics" },
      { label: "New contact", value: hubSum(hub.contacts_daily.filter((r) => r.line === "form"), "count"), src: "HubSpot" },
      { label: "Meeting", value: hubSum(booked, "count"), src: "HubSpot",
        note: "Meetings with demo-form contacts only. The summary above counts meetings with any marketing contact." },
      { label: "Deal", value: hubSum(hub.deals_daily, "count"), src: "HubSpot", extra: money(hubSum(hub.deals_daily, "amount")) },
    ];
  };
  let channel = "all";
  const drawFunnel = () => {
    const p = periodsFor(periodMode, start, gaLast);
    const cur = p.cur || { start, end: gaLast };
    const steps = step(channel, cur.start, cur.end);
    const top = Math.max(1, steps[0].value);
    $("journey-funnel-title").textContent = `Funnel, ${JOURNEY_CHANNELS[channel]}, ${range(cur.start, cur.end)}`;
    $("journey-funnel").innerHTML = steps.map((st, i) => {
      // widths on a log scale so the small steps at the end stay visible
      const w = 12 + 88 * (Math.log10(st.value + 1) / Math.log10(top + 1));
      const prev = steps[i - 1];
      const dropText = i && prev.value ? `${Math.round((st.value / prev.value) * 100)}% of the step before` : "&nbsp;";
      const drop = i ? `<div class="funnel-step"><div></div><div class="funnel-drop">${dropText}</div></div>` : "";
      return `${drop}<div class="funnel-step"><div class="funnel-label">${st.label}<small>${st.src}</small></div>
        <div class="funnel-bar" style="width:${w}%">${num(st.value)}${st.extra && st.value ? ` (${st.extra})` : ""}</div></div>` +
        (st.note ? `<div class="funnel-step"><div></div><div class="funnel-note">${esc(st.note)}</div></div>` : "");
    }).join("");
    $("journey-funnel-source").textContent = `Sources: Google Analytics, opsera.ai 2026 (first three steps) and HubSpot (last three), ${range(cur.start, cur.end)}, US Pacific time. Bar widths are on a log scale.`;
    $("journey-linkedin").hidden = channel !== "linkedin";
    $("journey-linkedin-hint").textContent = channel === "linkedin" ? "The company page, Kumar and untagged split, and the post-level detail, are under More detail." : "";
    if (channel === "linkedin") charts.forEach((c) => c.instance && c.instance.resize());
  };
  drawFunnel(); monthlyTabs.push(drawFunnel);
  $("journey-channel").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    channel = b.dataset.ch;
    $("journey-channel").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    drawFunnel();
  });

  // More detail
  table($("journey-channels"), { rows: Object.entries(JOURNEY_CHANNELS).map(([ch, name]) => {
    const st = step(ch, start, gaLast);
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
  $("journey-channels-source").textContent = `Sources: Google Analytics and HubSpot, ${range(start, gaLast)}, US Pacific time.`;

  const mk = (k) => hub.meetings_daily.filter((r) => r.kind === k).reduce((t2, r) => t2 + r.count, 0);
  $("journey-meetings").innerHTML = card("Meetings booked", num(mk("booked")), "After sign-up, up to yesterday") +
    card("Upcoming", num(mk("upcoming")), "Booked for later") + card("With existing customers", num(mk("existing_customer")), "Not counted") +
    card("Before sign-up", num(mk("before_signup")), "Not counted");
  $("journey-meetings-source").textContent = `Source: ${hubWhen}, calendar meetings since ${dayYear(start)}. ${num(hub.meetings_all_calendar)} calendar meetings in all.`;
  const dealCount = hub.deals_daily.reduce((t2, r) => t2 + r.count, 0);
  $("journey-deals").innerHTML = card("Deals from marketing contacts", num(dealCount), hub.deals_by_stage.map(([st, n]) => `${st}: ${n}`).join(", ") || "None yet") +
    card("New pipeline", money(hub.deals_daily.reduce((t2, r) => t2 + r.amount, 0))) +
    card("Existing deals of these contacts", num(hub.existing_deals.count), `${money(hub.existing_deals.amount)}, created before sign-up. Not counted`);
  $("journey-deals-source").textContent = `Source: ${hubWhen}, deals created since ${dayYear(start)}.`;
  const contacts = (line) => hub.contacts_daily.filter((r) => r.line === line).reduce((t2, r) => t2 + r.count, 0);
  $("journey-contacts").innerHTML = card("Form contacts", num(contacts("form")), `Demo form: ${num(hub.contacts_daily.filter((r) => r.line === "form" && r.demo).reduce((t2, r) => t2 + r.count, 0))}`) +
    card("Luma event sign-ups", num(contacts("luma")), "Imported from Luma") +
    card("Job applicants", num(hub.job_applicants_left_out), "Not counted");
  $("journey-contacts-source").textContent = `Source: ${hubWhen}, contacts created by a form since ${dayYear(start)}, and the Flutter Luma import.`;
  table($("journey-contacts-table"), { rows: hub.first_forms.map(([form, n]) => ({ form, n })).filter((r) => !/job application/i.test(r.form)), sortKey: "n", columns: [
    { key: "form", label: "First form" }, { key: "n", label: "Contacts", num: true, fmt: num },
  ] });
  $("journey-contacts-table-source").textContent = `Source: ${hubWhen}.`;
  if (Array.isArray(hub.campaigns)) {
    table($("journey-campaigns"), { rows: hub.campaigns.filter((c) => /FY27|2026/i.test(c.name)), sortKey: "influencedContacts", columns: [
      { key: "name", label: "Campaign" },
      { key: "contactFirstTouch", label: "First touch", num: true, fmt: num },
      { key: "influencedContacts", label: "Influenced", num: true, fmt: num },
      { key: "influencedContacts_also_flutter_guests", label: "Also Flutter guests", num: true, fmt: num },
    ] });
    $("journey-campaigns-source").textContent = `Source: ${hubWhen}, ${num(hub.campaigns_checked)} campaigns checked.`;
  }
  table($("journey-li-fields"), { rows: hub.linkedin_fields.map(([field, n]) => ({ field, n })), sortKey: "n", columns: [
    { key: "field", label: "Counted as LinkedIn because" }, { key: "n", label: "Contacts", num: true, fmt: num },
  ] });
  $("journey-li-fields-source").textContent = `Source: ${hubWhen}. ${num(hub.linkedin_contacts)} LinkedIn contacts; one contact can match more than one field but counts once.`;
}

function renderLeadsHubspot(hub) {
  $("leads-hubspot-events").innerHTML = hub.events.map((e) => card(e.label, num(e.members),
    [e.note, e.joined_daily.length ? `Added ${e.joined_daily.length > 1 ? `${dayYear(e.joined_daily[0].date)} to ${dayYear(e.joined_daily[e.joined_daily.length - 1].date)}` : dayYear(e.joined_daily[0].date)}` : ""].filter(Boolean).join(". "))).join("");
  $("leads-hubspot-events-source").textContent = `Source: HubSpot lists, last updated ${dayYear(hub.pulled_at.slice(0, 10))}.`;
}

// From LinkedIn to the demo form: homepage -> /demo -> demo form, for each LinkedIn line, never added together
function renderLinkedInPath(ga) {
  const rows = ga.linkedin.demo_path;
  const GROUPS = [["company", "Company page"], ["kumar", "Kumar"], ["untagged", "Untagged"]];
  const src = "Source: Google Analytics, opsera.ai 2026, HubSpot demo form on /demo";
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
    $("li-path-title").textContent = { day: "Last full day", week: "Last full week", month: "This month so far" }[periodMode];
    build("li-path", cur.start, cur.end);
    $("li-path-source").textContent = `${src}, ${range(cur.start, cur.end)}, US Pacific time.`;
  };
  fill(); monthlyTabs.push(fill);
  build("li-path-all", start, last);
  $("li-path-all-source").textContent = `${src}, ${range(start, last)}, US Pacific time.`;
}

// Estimated: Untagged LinkedIn visits matched to posts. Best guesses, never added to the tagged lines.
function renderLinkedInEstimate(est, ga) {
  const GROUPS = [["estimated_company", "Estimated: company page"], ["estimated_kumar", "Estimated: Kumar"], ["cant_tell", "Can't tell"]];
  const src = "Source: Google Analytics, opsera.ai 2026, matched to LinkedIn posts";
  const when = (a, b) => `${range(a, b)}, US Pacific time`;
  const estLast = lastFullDayPacific(est.end_date || ga.end_date, est.pulled_at || ga.pulled_at);
  $("li-est-stale").textContent = est.end_date && est.end_date < ga.end_date
    ? `The estimate wasn't updated this week, so it stops at ${dayYear(estLast)}.` : "";
  compare({ id: "li-est", together: true, start: ga.start_date, last: estLast,
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
  $("li-est-rule").textContent = `A visit is only given to one account when just that account linked to the page on the day of the visit or the ${est.window_days} days before.`;
  table($("li-est-posts"), { rows: est.linked_posts.map((p) => ({ ...p, from: who[p.account], name: dayYear(p.date) })), sortKey: "date", sortDir: 1, columns: [
    { key: "name", label: "Posted", sort: false, fmt: (v, r) => `<a href="${esc(r.post)}" target="_blank" rel="noopener">${esc(v)}</a>` },
    { key: "from", label: "From", sort: false },
    { key: "page", label: "Links to", sort: false },
  ] });
  $("li-est-posts-source").textContent = `Source: LinkedIn posts found through Apify, since ${dayYear("2026-09-01")}, last checked ${dayYear(est.posts_pulled_at.slice(0, 10))}.`;
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
    label: `${day(s < start ? start : s)} to ${day(addDays(s, 6) > end ? end : addDays(s, 6))}`, ...out[s],
  }));
}

function renderYouTube(d, ga) {
  const last = d.last_day_with_data || d.end_date;
  const src = `Source: YouTube Analytics API, Opsera channel, ${range(d.start_date, last)}.`;
  const c = d.channel;

  $("yt-ch-cards").innerHTML =
    card("Subscribers gained", num(c.subs_gained)) +
    card("Subscribers lost", num(c.subs_lost)) +
    card("Card clicks", num(c.card_clicks), `Card teaser clicks ${num(c.card_teaser_clicks)}`) +
    card("Shorts published", num(c.published.filter((v) => v.type === "shorts").length), "Public videos") +
    (c.published.some((v) => v.type === "unknown") ? card("Videos not yet watched", num(c.published.filter((v) => v.type === "unknown").length), "Public, but YouTube can't tell Shorts from long videos until they're watched") : "");
  $("yt-ch-source").textContent = src;

  const subWeeks = weeksFilled(c.subs_daily, ["gained", "lost"], d.start_date, last);
  chart("yt-subs", (th) => ({
    type: "bar", whole: true, data: { labels: subWeeks.map((w) => w.label), datasets: [
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
  $("yt-searches-note").textContent = `YouTube names the search for ${num(named)} of the ${num(c.search_views)} views that came from YouTube search.`;

  const fromYt = ga.sources.filter((r) => /youtube\.com|youtu\.be/i.test(r.sessionSource));
  const gaSum = (k) => fromYt.reduce((a, r) => a + r[k], 0);
  $("yt-ga-cards").innerHTML =
    card("Visits from YouTube", num(gaSum("sessions"))) +
    card("Engaged visits from YouTube", num(gaSum("engagedSessions")));
  $("yt-ga-source").textContent = `Source: Google Analytics, opsera.ai 2026, ${range(ga.start_date, ga.end_date)}, US Pacific time.`;

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
      type: "bar", whole: true, data: { labels: weeks.map((w) => w.label), datasets: [bar(labels[m], weeks.map((w) => w[m]), th.s[0])] },
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
  compare({ id: "yt", start: d.start_date, last, source: (a, b) => `Source: YouTube Analytics API, Opsera channel, ${range(a, b)}.`, metrics: [
    { label: "Long videos: views", value: rangeSum(d.types.long.daily, "views"), fmt: num },
    { label: "Long videos: watch time", value: rangeSum(d.types.long.daily, "minutes"), fmt: (v) => `${num(v)} min` },
    { label: "Shorts: views", value: rangeSum(d.types.shorts.daily, "views"), fmt: num },
    { label: "Long videos published", value: published("long"), fmt: num, sub: "Public videos" },
  ] });
}

// ---------- Tab 4: Kahoots ----------

function renderKahoots(monthly, quarter) {
  const m = (key, month) => monthly.find((r) => r.month === month)[key];
  const monthCard = (label, key) => card(label, num(m(key, "2026-09")), `August: ${num(m(key, "2026-08"))}`, cmpDelta(m(key, "2026-09"), m(key, "2026-08")));
  $("kahoots-cards").innerHTML =
    monthCard("Website visits", "visits") +
    monthCard("Visits from people", "people_visits") +
    monthCard("Form fills", "form_fills");
  const note = () => { $("kahoots-monthly-note").textContent = periodMode !== "month" ? "Kahoots reported by month, so this tab compares September with August." : ""; };
  note(); monthlyTabs.push(note);
  chart("kahoots-visits", (th) => ({
    type: "bar", stacked: true,
    data: { labels: monthly.map((r) => month(r.month)), datasets: [
      bar("Visits from people", monthly.map((r) => r.people_visits), th.s[0]),
      { ...bar("Robots (visits minus people)", monthly.map((r) => r.visits - r.people_visits), th.s[1]), borderWidth: { top: 0, bottom: 2, left: 0, right: 0 } },
    ] },
    tooltip: { footer: (items) => `All visits: ${num(monthly[items[0].dataIndex].visits)}` },
  }));
  chart("kahoots-forms", (th) => ({
    type: "bar",
    data: { labels: monthly.map((r) => month(r.month)), datasets: [bar("Form fills", monthly.map((r) => r.form_fills), th.s[0])] },
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
  const monthCard = (label, key, fmt, lower) => card(label, fmt(sep[key]), `August: ${fmt(aug[key])}${lower ? ". Lower is better" : ""}`, cmpDelta(sep[key], aug[key], lower));
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
    { key: "times_shown", label: "Times Google showed us", num: true, fmt: num, sort: false },
    { key: "click_rate_pct", label: "Click rate", num: true, fmt: (v) => pct(v), sort: false },
    { key: "avg_spot", label: "Average spot on Google", num: true, fmt: spot, sort: false },
  ] });
  chart("infrasity-forge", (th) => ({
    type: "bar",
    data: { labels: monthly.map((r) => month(r.month)), datasets: [bar("Google clicks on Forge pages", monthly.map((r) => r.forge_page_clicks), th.s[0])] },
  }));
}

// ---------- Tab 6: To do ----------

const TODO = [
  ["page-two", "Update the pages on page two of Google, starting with the CI/CD pipeline blog (spot 11 for \"ci/cd\", 27,000 searches a month)."],
  ["cursor", "Cursor article: add a next step and a demo button, and find out why its Google clicks fell from 469 in August to 195 in September."],
  ["ai-answers", "Write short answer pages for the AI questions we're missing on (\"what is DevOps orchestration\", \"what is a software factory\")."],
  ["gartner-ad", "Pause or redirect the LinkedIn Gartner ad."],
  ["copado", "Copado page: add a switching section and a demo button."],
  ["slash", "Fix blogs showing up twice on Google, with and without \"/\" at the end."],
  ["waiting", "Waiting on David and Yusra: bot filtering in HubSpot, connecting Luma to HubSpot."],
  ["happy-hour", "Check with David why the GitHub Universe happy hour form shows 7 submits but only 2 in HubSpot."],
  ["salesforce-link", "Fix the broken Salesforce blog link (/blog/why-salesforce-orgs-need-a-headless-devops-platform) that both Opsera and Kumar posted. Needs a redirect on the website."],
];

function renderTodo() {
  let ticks = {};
  try { ticks = JSON.parse(localStorage.getItem("todo-ticks") || "{}"); } catch (e) {}
  $("todo").innerHTML = TODO.map(([id, text]) =>
    `<li class="${ticks[id] ? "done" : ""}"><label><input type="checkbox" data-id="${id}" ${ticks[id] ? "checked" : ""}><span>${esc(text)}</span></label></li>`).join("");
  $("todo").addEventListener("change", (e) => {
    ticks[e.target.dataset.id] = e.target.checked;
    e.target.closest("li").classList.toggle("done", e.target.checked);
    try { localStorage.setItem("todo-ticks", JSON.stringify(ticks)); } catch (err) {}
  });
}

// ---------- tabs and theme ----------

function showTab(name) {
  if (!$(`tab-${name}`)) name = "search";
  document.querySelectorAll(".tab").forEach((s) => { s.hidden = s.id !== `tab-${name}`; });
  document.querySelectorAll(".tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === name));
  charts.forEach((c) => c.instance && c.instance.resize());
}
document.querySelectorAll("details.more").forEach((el) => el.addEventListener("toggle", () => charts.forEach((c) => c.instance && c.instance.resize())));
document.querySelector(".tabs").addEventListener("click", (e) => {
  const b = e.target.closest("button"); if (!b) return;
  history.replaceState(null, "", `#${b.dataset.tab}`); showTab(b.dataset.tab);
});
addEventListener("hashchange", () => showTab(location.hash.slice(1)));

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
  renderTodo();
  try {
    const [gsc, ga, leads, li, yt, kp, est, hub, km, kq, inf] = await Promise.all(
      ["search_console.json", "analytics.json", "leads.json", "linkedin.json", "youtube.json", "kumar_posts.json", "linkedin_estimate.json", "hubspot.json", "kahoots_monthly.json", "kahoots_quarter.json", "infrasity_monthly.json"].map(load));
    showTab(location.hash.slice(1));
    $("pulled").textContent = `Google numbers last pulled ${dayYear(gsc.pulled_at.slice(0, 10))}, ${gsc.pulled_at.slice(11, 16)} India time.`;
    renderSearch(gsc);
    renderVisits(ga);
    renderLeads(leads);
    renderLinkedIn(li);
    renderKumarPosts(kp);
    renderLinkedInVisits(ga);
    renderLinkedInEstimate(est, ga);
    renderLinkedInPath(ga);
    renderJourney(ga, leads, hub);
    renderLeadsHubspot(hub);
    renderYouTube(yt, ga);
    renderKahoots(km, kq);
    renderInfrasity(inf);
  } catch (err) {
    $("error").hidden = false;
    $("error").textContent = `Something went wrong loading the numbers: ${err.message}`;
    console.error(err);
  }
})();
