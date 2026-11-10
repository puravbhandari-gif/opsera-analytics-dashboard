"""Microsoft Clarity for the Website visits tab: sessions, scroll depth, rage clicks and dead clicks per page, kept day by day
in data/clarity.json. Clarity's Data Export API only gives the last 1 to 3 days, so a daily GitHub run (clarity.yml) calls it
once a day and adds the result to the history (agreed 10 Nov 2026).

The token is a GitHub secret (CLARITY_API_TOKEN), or ~/.config/opsera-dashboard/clarity-token on this Mac. Never printed.
Clarity allows 10 calls a day; this makes 1.
Clarity's page addresses can carry a visitor's email (w_email=... in email links), so only the path is kept, never the query.
    .venv/bin/python scripts/fetch_clarity.py              # call the API and add today's pull
    .venv/bin/python scripts/fetch_clarity.py --from FILE  # add a saved API answer instead (no call)
"""
import collections
import datetime as dt
import json
import os
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

PROJECT = "zb2b12566l"
API = "https://www.clarity.ms/export-data/api/v1/project-live-insights?numOfDays=1&dimension1=URL"
OUT = Path(__file__).resolve().parent.parent / "data" / "clarity.json"
SITE_HOSTS = {"opsera.ai", "www.opsera.ai"}
KEEP_DAYS = 400
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def token():
    t = os.environ.get("CLARITY_API_TOKEN", "").strip()
    path = Path.home() / ".config" / "opsera-dashboard" / "clarity-token"
    if not t and path.exists():
        t = path.read_text().strip()
    if not t:
        sys.exit("No Clarity token: set CLARITY_API_TOKEN or save it in ~/.config/opsera-dashboard/clarity-token.")
    return t


def call():
    req = urllib.request.Request(API, headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def page(url):
    """The page path only: the query and anything after # are dropped, so no email or tracking code is kept."""
    u = urlparse(url or "")
    if u.netloc and u.netloc not in SITE_HOSTS:
        return None
    path = (u.path or "/").rstrip("/") or "/"
    return path


def summarise(metrics):
    by = {m["metricName"]: m.get("information") or [] for m in metrics}
    pages = collections.defaultdict(lambda: {"sessions": 0, "bot_sessions": 0, "scroll_sum": 0.0, "scroll_n": 0,
                                             "rage_clicks": 0, "rage_sessions": 0, "dead_clicks": 0, "dead_sessions": 0})
    for r in by.get("Traffic", []):
        p = page(r.get("Url"))
        if p:
            pages[p]["sessions"] += r.get("totalSessionCount") or 0
            pages[p]["bot_sessions"] += r.get("totalBotSessionCount") or 0
    sessions_at = collections.Counter()
    for r in by.get("Traffic", []):
        sessions_at[r.get("Url")] = r.get("totalSessionCount") or 0
    for r in by.get("ScrollDepth", []):
        p = page(r.get("Url"))
        if p and r.get("averageScrollDepth") is not None:
            w = max(sessions_at.get(r.get("Url"), 0), 1)   # weighted by the address's sessions
            pages[p]["scroll_sum"] += r["averageScrollDepth"] * w
            pages[p]["scroll_n"] += w
    for name, key in (("RageClickCount", "rage"), ("DeadClickCount", "dead")):
        for r in by.get(name, []):
            p = page(r.get("Url"))
            if p:
                pages[p][f"{key}_clicks"] += r.get("subTotal") or 0
                pages[p][f"{key}_sessions"] += round((r.get("sessionsCount") or 0) * (r.get("sessionsWithMetricPercentage") or 0) / 100)
    rows = []
    for p, v in pages.items():
        rows.append({"page": p, "sessions": v["sessions"], "bot_sessions": v["bot_sessions"],
                     "scroll_depth": round(v["scroll_sum"] / v["scroll_n"], 1) if v["scroll_n"] else None,
                     "rage_clicks": v["rage_clicks"], "rage_sessions": v["rage_sessions"],
                     "dead_clicks": v["dead_clicks"], "dead_sessions": v["dead_sessions"]})
    return sorted(rows, key=lambda r: (-r["sessions"], r["page"]))


def main():
    args = sys.argv[1:]
    metrics = json.loads(Path(args[1]).read_text()) if args[:1] == ["--from"] else call()
    now = dt.datetime.now(IST)
    pull = {"date": now.date().isoformat(), "pulled_at": now.isoformat(timespec="minutes"), "window": "the 24 hours before the pull",
            "pages": summarise(metrics)}
    old = json.loads(OUT.read_text()) if OUT.exists() else {}
    days = [d for d in old.get("days", []) if d["date"] != pull["date"]] + [pull]
    days = sorted(days, key=lambda d: d["date"])[-KEEP_DAYS:]
    OUT.write_text(json.dumps({"source": f"Microsoft Clarity, project {PROJECT}, Data Export API", "days": days}, indent=1) + "\n")
    s = sum(r["sessions"] for r in pull["pages"])
    print(f"Clarity {pull['date']}: {s} sessions on {len(pull['pages'])} pages, {len(days)} days kept")


if __name__ == "__main__":
    main()
