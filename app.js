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
const day = (s) => toDate(s).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
const dayYear = (s) => toDate(s).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
const range = (a, b) => `${day(a)} to ${dayYear(b)}`;
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
        ticks: { color: t.muted, callback: cfg.yfmt || ((v) => nf.format(v)) },
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
  const src = `Source: ${d.source}`;
  $("search-source").textContent = `${src}. ${range(d.start_date, last)} (last day Google has reported so far).`;
  const t = sumSearch(d.daily);
  $("search-cards").innerHTML =
    card("Clicks", num(t.clicks), "People who clicked through to opsera.ai from Google") +
    card("Times Google showed us", num(t.shown), "Times opsera.ai appeared in Google results") +
    card("Click rate", pct(t.rate), "Clicks divided by times shown, x 100") +
    card("Average spot on Google", spot(t.spot), "Lower is better. 1 is the top result");

  const thisStart = addDays(last, -6), prevStart = addDays(last, -13), prevEnd = addDays(last, -7);
  const cur = sumSearch(d.daily.filter((r) => r.date >= thisStart && r.date <= last));
  const prevRows = d.daily.filter((r) => r.date >= prevStart && r.date <= prevEnd);
  const prev = prevRows.length === 7 ? sumSearch(prevRows) : {};
  $("search-week-source").textContent = `${src}. This week: ${range(thisStart, last)}. Last week: ${range(prevStart, prevEnd)}.`;
  $("search-week").innerHTML =
    card("Clicks", num(cur.clicks), `Last week: ${num(prev.clicks)}`, delta(cur.clicks, prev.clicks)) +
    card("Times Google showed us", num(cur.shown), `Last week: ${num(prev.shown)}`, delta(cur.shown, prev.shown)) +
    card("Click rate", pct(cur.rate), `Last week: ${pct(prev.rate)}`, delta(cur.rate, prev.rate)) +
    card("Average spot on Google", spot(cur.spot), `Last week: ${spot(prev.spot)}. Lower is better`, delta(cur.spot, prev.spot, true));

  $("search-daily-source").textContent = `${src}. ${range(d.start_date, last)}.`;
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
    reverse: metrics[m].reverse, yfmt: metrics[m].yfmt,
    tooltip: { label: (c) => ` ${metrics[m].label}: ${metrics[m].fmt(c.parsed.y)}` },
  }));
  const setNote = () => { $("search-daily-note").textContent = m === "avg_spot" ? "Lower spot numbers are better, so this chart is flipped: a line going up means a better spot on Google." : ""; };
  setNote();
  $("search-metric").addEventListener("click", (e) => {
    const b = e.target.closest("button"); if (!b) return;
    m = b.dataset.m;
    $("search-metric").querySelectorAll("button").forEach((x) => x.classList.toggle("on", x === b));
    draw(charts.find((c) => c.id === "search-daily")); setNote();
  });

  const cols = (first) => [
    first,
    { key: "clicks", label: "Clicks", num: true, fmt: num },
    { key: "times_shown", label: "Times shown", num: true, fmt: num },
    { key: "click_rate_pct", label: "Click rate", num: true, fmt: (v) => pct(v) },
    { key: "avg_spot", label: "Average spot", num: true, fmt: spot },
  ];
  $("search-pages-source").textContent = `${src}. ${range(d.start_date, last)}.`;
  table($("search-pages"), {
    rows: d.pages.map((p) => ({ ...p, path: shortPage(p.page) })), search: "pages", sortKey: "clicks",
    columns: cols({ key: "path", label: "Page", search: true, fmt: (v) => esc(v) }),
  });
  $("search-queries-source").textContent = `${src}. ${range(d.start_date, last)}.`;
  table($("search-queries"), { rows: d.searches, search: "searches", sortKey: "clicks",
    columns: cols({ key: "search", label: "Search", search: true }) });
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
  const src = `Source: ${d.source}`;
  const when = `${range(d.start_date, d.end_date)}. Days follow US Pacific time, the property's setting`;
  const t = d.totals;
  $("visits-source").textContent = `${src}. ${when}.`;
  $("visits-cards").innerHTML =
    card("Visits", num(t.sessions), "Every visit, including robots") +
    card("People visiting", num(t.totalUsers), "Different browsers that visited") +
    card("Share who engaged", pct((t.engagedSessions / t.sessions) * 100, 1), `${num(t.engagedSessions)} visits stayed 10+ seconds, saw 2+ pages, or filled a form`);
  $("visits-split-note").textContent =
    `Google estimates visits separately for each way of splitting them, so the parts come out a little lower than the total. ` +
    `Days add up to ${num(d.split_sums.daily)} and sources to ${num(d.split_sums.channels)}, against the total of ${num(t.sessions)}. ` +
    `Both are shown as Google reports them.`;

  $("visits-daily-source").textContent = `${src}. ${when}.`;
  chart("visits-daily", (th) => ({
    type: "line",
    data: { labels: d.daily.map((r) => day(r.date)), datasets: [
      line("Visits", d.daily.map((r) => r.sessions), th.s[0]),
      line("People visiting", d.daily.map((r) => r.totalUsers), th.s[1]),
    ] },
  }));

  $("visits-channels-source").textContent = `${src}. ${when}.`;
  const ch = d.channels.map((r) => ({ ...r, name: channelName(r.sessionDefaultChannelGroup), engaged: (r.engagedSessions / r.sessions) * 100 }));
  chart("visits-channels", (th) => ({
    type: "bar", horizontal: true,
    data: { labels: ch.map((r) => r.name), datasets: [bar("Visits", ch.map((r) => r.sessions), th.s[0])] },
  }));
  table($("visits-channels-table"), { rows: ch, sortKey: "sessions", pageSize: 20, columns: [
    { key: "name", label: "Came from" },
    { key: "sessions", label: "Visits", num: true, fmt: num },
    { key: "totalUsers", label: "People", num: true, fmt: num },
    { key: "engaged", label: "Share who engaged", num: true, fmt: (v) => pct(v, 0) },
    { key: "averageSessionDuration", label: "Average time", num: true, fmt: (v) => `${Math.round(v)}s` },
  ] });

  $("visits-robots-source").textContent = `${src}. ${when}.`;
  const email = d.channels.find((r) => r.sessionDefaultChannelGroup === "Email");
  $("visits-robots-cards").innerHTML =
    card("All visits", num(t.sessions), "Includes robots") +
    card("Engaged visits", num(t.engagedSessions), "Suggested \"people only\" number") +
    card("Visits from email", num(email ? email.sessions : 0), email ? `${pct((email.engagedSessions / email.sessions) * 100, 0)} engaged. Most of the rest are likely email robots` : "");
  const emailByDay = Object.fromEntries(d.channel_daily.filter((r) => r.sessionDefaultChannelGroup === "Email").map((r) => [r.date, r.sessions]));
  chart("visits-robots", (th) => ({
    type: "line",
    data: { labels: d.daily.map((r) => day(r.date)), datasets: [
      line("All visits", d.daily.map((r) => r.sessions), th.s[0]),
      line("Engaged visits (suggested people only)", d.daily.map((r) => r.engagedSessions), th.s[1]),
      line("Visits from email", d.daily.map((r) => emailByDay[r.date] || 0), th.s[2]),
    ] },
  }));

  $("visits-sources-source").textContent = `${src}. ${when}.`;
  table($("visits-sources"), {
    rows: d.sources.map((r) => ({ ...r, name: channelName(r.sessionDefaultChannelGroup), engaged: (r.engagedSessions / r.sessions) * 100 })),
    search: "sources", sortKey: "sessions", columns: [
      { key: "sessionSource", label: "Source", search: true },
      { key: "sessionMedium", label: "Type", search: true },
      { key: "name", label: "Group", search: true },
      { key: "sessions", label: "Visits", num: true, fmt: num },
      { key: "engaged", label: "Share who engaged", num: true, fmt: (v) => pct(v, 0) },
    ] });

  $("visits-pages-source").textContent = `${src}. ${when}.`;
  table($("visits-pages"), { rows: d.pages, search: "pages", sortKey: "views", columns: [
    { key: "page", label: "Page", search: true },
    { key: "views", label: "Times viewed", num: true, fmt: num },
  ] });
}

// ---------- Tab 3: Leads ----------

const LEAD_ORDER = ["demo", "contact", "events", "gartner_offer", "other"];
const LEAD_NOTES = {
  demo: "Form on /demo",
  contact: "Form on /contact. /contact now goes to the Book a demo page",
  events: "Event pages on the website. Luma sign-ups are missing",
  gartner_offer: "Form on /gartner-symposium/free-modernization",
  other: "Report downloads, webinars and other forms",
};

function renderLeads(d) {
  const src = `Source: ${d.source}`;
  const when = `${range(d.start_date, d.end_date)}. Days follow US Pacific time`;
  $("leads-source").textContent = `${src}. ${when}. One HubSpot form submission is counted per form fill.`;
  $("leads-cards").innerHTML = LEAD_ORDER.map((k) => card(d.lines[k].label, num(d.lines[k].count), LEAD_NOTES[k])).join("");

  $("leads-core-source").textContent = `${src}. ${when}.`;
  const removed = "Form removed when the new site went live on 30 Sep. Visitors now go to Book a demo.";
  const names = { "/": "Homepage", "/about": "About", "/platform": "Platform" };
  const core = [
    ...d.removed_form_pages.map((p) => ({ name: names[p] || p, page: p, status: removed })),
    { name: "Contact", page: "/contact", status: `${num(d.lines.contact.count)} form fill${d.lines.contact.count === 1 ? "" : "s"}. /contact now goes to the Book a demo page.` },
    { name: "Book a demo", page: "/demo", status: `${num(d.lines.demo.count)} demo requests.` },
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
  $("leads-weekly-source").textContent = `${src}. ${when}. Weeks run Monday to Sunday.`;
  chart("leads-weekly", (th) => ({
    type: "bar",
    data: { labels: starts.map(label), datasets: LEAD_ORDER.map((k, i) => bar(d.lines[k].label, starts.map((s) => weeks[s][k]), th.s[i])) },
  }));

  $("leads-pages-source").textContent = `${src}. ${when}.`;
  const rows = LEAD_ORDER.flatMap((k) => d.lines[k].pages.map((p) => ({ line: d.lines[k].label, page: p.page, count: p.count })));
  table($("leads-pages"), { rows, search: "pages", sortKey: "count", columns: [
    { key: "line", label: "Kind of form", search: true },
    { key: "page", label: "Page", search: true },
    { key: "count", label: "Form fills", num: true, fmt: num },
  ] });
}

// ---------- Tab 4: Kahoots ----------

function renderKahoots(monthly, quarter) {
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
    const [gsc, ga, leads, km, kq, inf] = await Promise.all(
      ["search_console.json", "analytics.json", "leads.json", "kahoots_monthly.json", "kahoots_quarter.json", "infrasity_monthly.json"].map(load));
    showTab(location.hash.slice(1));
    $("pulled").textContent = `Google numbers last pulled ${dayYear(gsc.pulled_at.slice(0, 10))}, ${gsc.pulled_at.slice(11, 16)} India time.`;
    renderSearch(gsc);
    renderVisits(ga);
    renderLeads(leads);
    renderKahoots(km, kq);
    renderInfrasity(inf);
  } catch (err) {
    $("error").hidden = false;
    $("error").textContent = `Something went wrong loading the numbers: ${err.message}`;
    console.error(err);
  }
})();
