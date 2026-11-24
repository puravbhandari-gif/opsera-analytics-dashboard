"""Write a plain-text summary of the key numbers, and a link to every for-claude file, into index.html.

The dashboard draws its numbers with JavaScript, so AI tools that fetch the page without running it saw an empty page
(Sudeepa, 24 Nov 2026). This block sits in the page's HTML between the ai-summary markers. The page hides it once
JavaScript runs, so people still see the normal dashboard. It uses only numbers already on the dashboard:
data/summary.json for the Summary tab's main numbers and data/salesforce_pipeline.json for pipeline by fiscal quarter.
No customer or person names: campaign names and deal lists stay out. scripts/privacy_check.py scans this block too.
Run after build_summary.py and build_for_claude.py: python scripts/build_ai_summary.py
"""
import collections
import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA, FOR_CLAUDE, PAGE = ROOT / "data", ROOT / "for-claude", ROOT / "index.html"
BASE = "https://puravbhandari-gif.github.io/opsera-analytics-dashboard/"
START, END = "<!-- ai-summary:start -->", "<!-- ai-summary:end -->"
VIEWS = [("week", "Last full week"), ("month", "This month so far"), ("cq", "Last full fiscal quarter")]
BOXES = [("well", "Going well"), ("attention", "Needs attention"), ("do", "Do this week")]
LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

e = html.escape


def deals(n):
    return f"{n} deal" + ("" if n == 1 else "s")


def usd(n):
    return f"${n:,.0f}"


def md_line(text):
    """One line of for-claude/index.md as HTML: escape it, then turn its markdown links into real links."""
    out, last = [], 0
    for m in LINK.finditer(text):
        out.append(e(text[last:m.start()]))
        out.append(f'<a href="{e(m.group(2))}">{e(m.group(1))}</a>')
        last = m.end()
    out.append(e(text[last:]))
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", "".join(out))


def summary_views(s):
    parts = []
    for key, label in VIEWS:
        v = s["views"].get(key)
        if not v:
            continue
        before = f", against {e(v['period_before'])}" if v.get("period_before") else ""
        parts.append(f"<h3>{label}: {e(v['period'])}{before}</h3>\n<ul>")
        for a in v["areas"]:
            m = a.get("main")
            if a["key"] == "pipeline" or not m:   # pipeline comes from the quarter table below, so the 2 never disagree
                continue
            was = f", against {e(m['before'])} the period before" if m.get("before") else ""
            other = f" Counted for {e(a['period'])}." if a.get("period") and a["period"] != v["period"] else ""
            parts.append(f"<li>{e(a['title'])}: {e(m['label'])} {e(m['value'])}{was}. Source: {e(a['source'])}.{other}</li>")
        parts.append("</ul>")
        for bkey, blabel in BOXES:
            lines = (v.get("boxes") or {}).get(bkey) or []
            if lines:
                parts.append(f"<p>{blabel}:</p>\n<ul>" + "".join(f"<li>{e(t)}</li>" for t in lines) + "</ul>")
    return "\n".join(parts)


def pipeline(p):
    q = collections.OrderedDict()
    for m in p["months"]:
        t = q.setdefault(m["quarter"], {"months": [], "sd": 0, "sv": 0, "id": 0, "iv": 0})
        t["months"].append(m["month"])
        t["sd"] += m["sourced_deals"]; t["sv"] += m["sourced_value"]
        t["id"] += m["influenced_deals"]; t["iv"] += m["influenced_value"]
    rows = []
    for name, t in q.items():
        first, last = t["months"][0], t["months"][-1]
        a, b = MONTHS[int(first[5:]) - 1], MONTHS[int(last[5:]) - 1]
        span = (f"{a} {last[:4]}" if a == b else f"{a} to {b} {last[:4]}") + (" so far" if len(t["months"]) < 3 and name.endswith("Q4") else "")
        rows.append(f"<li>{e(name)} ({span}): marketing sourced {deals(t['sd'])}, {usd(t['sv'])}. "
                    f"Marketing influenced {deals(t['id'])}, {usd(t['iv'])}.</li>")
    pulled = p.get("exports", {}).get("opportunities", "")
    return ("<h3>Marketing pipeline by fiscal quarter</h3>\n"
            "<p>Fiscal quarters: Q1 is Feb to Apr, Q2 May to Jul, Q3 Aug to Oct, Q4 Nov to Jan. Deals created from 1 Apr 2026. "
            "Deals with a partner listed count as influenced, never sourced. The exec page adds sourced and influenced together; "
            f"nothing else does. Source: Salesforce deals as synced to HubSpot, pulled {e(pulled)}.</p>\n<ul>" + "".join(rows) + "</ul>")


def file_list():
    """Every file in for-claude/, in the guide's own sections and words. Any file the guide leaves out goes at the end."""
    guide = (FOR_CLAUDE / "index.md").read_text()
    sections, linked = [], set()
    for line in guide.splitlines():
        if line.startswith("## "):
            sections.append((line[3:], []))
        elif line.startswith("- ") and LINK.search(line) and sections:
            sections[-1][1].append(f"<li>{md_line(line[2:])}</li>")
            linked.update(Path(u).name for _, u in LINK.findall(line))
    parts = [f"<h4>{e(t)}</h4>\n<ul>" + "".join(items) + "</ul>" for t, items in sections if items]
    files = sorted(p.name for p in FOR_CLAUDE.glob("*.csv"))
    missing = [f for f in files if f not in linked]
    if missing:
        parts.append("<h4>Other files</h4>\n<ul>" + "".join(f'<li><a href="{BASE}for-claude/{e(f)}">{e(f)}</a></li>' for f in missing) + "</ul>")
    gone = sorted(n for n in linked if n.endswith(".csv") and n not in files)
    if gone:
        sys.exit(f"STOPPED: for-claude/index.md links files that don't exist: {', '.join(gone)}")
    return "\n".join(parts), len(files)


def main():
    s = json.loads((DATA / "summary.json").read_text())
    p = json.loads((DATA / "salesforce_pipeline.json").read_text())
    files, count = file_list()
    block = f"""{START}
<section class="ai-summary" id="ai-summary">
<h2>Opsera marketing dashboard, in plain text</h2>
<p>This page draws its charts with JavaScript. This summary is for AI assistants and readers who can't run it. Every number here is also on the dashboard. Summary numbers written {e(s.get('written_on', ''))}. We never add numbers from different sources together.</p>
<p>Start with the guide to the data: <a href="{BASE}for-claude/index.md">{BASE}for-claude/index.md</a>. It explains every file, its source and its dates. All {count} data files are linked below.</p>
<h2>Key numbers</h2>
{summary_views(s)}
{pipeline(p)}
<h2>Every data file</h2>
<p>Small CSV files with a header row. Weeks run Monday to Sunday. Google Analytics and HubSpot dates follow US Pacific time.</p>
{files}
</section>
{END}"""
    page = PAGE.read_text()
    if START in page:
        page = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, page, flags=re.S)
    else:
        page = page.replace("<body>\n", "<body>\n" + block + "\n", 1)
    PAGE.write_text(page)
    print(f"Wrote the plain-text summary into index.html: {count} files linked.")


if __name__ == "__main__":
    main()
