"""Visits to opsera.ai from each PR and media piece, from Google Analytics: visits, engaged visits and
demo requests (demo form fills). Writes data/pr_media_ga.json. Runs every Monday after fetch_pr_media.py.

Most sites send only their name, not the article's address, so a visit counts for the newest piece on
that site published on or before the visit day. Visits before the first piece on a site aren't counted.
Google Analytics data starts on 1 Apr 2026, so older pieces show no numbers, and nor do pieces on YouTube
or Spotify, whose visits can't be told apart from our own channels there. Agreed with Purav on 4 Nov 2026.
Uses the same Google key as fetch_data.py.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_data import FORM_EVENT, START_DATE, ga_report, session  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "pr_media_ga.json"
SHARED = ("youtube.com", "spotify.com")   # visits from these can't be told apart from our own channels, so they get no numbers


def site(url):
    return urlparse(url).netloc.lower().removeprefix("www.")


def main():
    pr = json.loads((DATA / "pr_media.json").read_text())
    ga = json.loads((DATA / "analytics.json").read_text())
    end = ga["end_date"]
    sites = sorted({site(x["link"]) for x in pr["items"] if not site(x["link"]).endswith(SHARED)})
    flt = {"filter": {"fieldName": "sessionSource", "inListFilter": {"values": sites + [f"www.{s}" for s in sites]}}}
    demo = {"filter": {"fieldName": "pagePath", "inListFilter": {"values": ["/demo", "/demo/"]}}}
    s = session()
    daily = {}
    for r in ga_report(s, end, ["date", "sessionSource"], ["sessions", "engagedSessions"], flt=flt):
        row = daily.setdefault((r["date"], r["sessionSource"].removeprefix("www.")), {"visits": 0, "engaged": 0, "demos": 0})
        row["visits"] += r["sessions"]
        row["engaged"] += r["engagedSessions"]
    for r in ga_report(s, end, ["date", "sessionSource"], ["eventCount"], event_names=[FORM_EVENT],
                       flt={"andGroup": {"expressions": [flt, demo]}}):
        daily.setdefault((r["date"], r["sessionSource"].removeprefix("www.")), {"visits": 0, "engaged": 0, "demos": 0})["demos"] += r["eventCount"]

    by_link = {}
    for host in sites:
        pieces = sorted((x for x in pr["items"] if site(x["link"]) == host), key=lambda x: x["date"])
        for i, x in enumerate(pieces):
            until = pieces[i + 1]["date"] if i + 1 < len(pieces) else "9999-12-31"   # the next piece on the same site takes over
            if x["date"] < START_DATE and until <= START_DATE:
                continue   # before Google Analytics data starts
            t = {"visits": 0, "engaged": 0, "demos": 0}
            for (date, src), v in daily.items():
                if src == host and x["date"] <= date < until:
                    for k in t:
                        t[k] += v[k]
            by_link[x["link"]] = {**t, "from": max(x["date"], START_DATE), "to": min(end, until)}
    OUT.write_text(json.dumps({"source": "Google Analytics, visits by referring site", "ga_start": START_DATE, "ga_end": end,
                               "checked": dt.date.today().isoformat(), "by_link": by_link}, indent=1) + "\n")
    print(f"Wrote {OUT.name}: {len(by_link)} pieces, {sum(v['visits'] for v in by_link.values())} visits, "
          f"{sum(v['demos'] for v in by_link.values())} demo requests")


if __name__ == "__main__":
    main()
