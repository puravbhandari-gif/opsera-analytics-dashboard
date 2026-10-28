"""After the Monday update, post the top numbers and the dashboard link to #core-marketing-team in Slack.
Needs the SLACK_WEBHOOK_URL env var (a GitHub secret: a Slack incoming webhook for that channel).
Run with --dry-run to print the message instead of posting it.

Agreed with Purav on 28 Oct 2026:
- The numbers are the last full Monday-to-Sunday week against the week before, the same as the dashboard's cards.
- Each line names its source. Sources are never added together. No emojis.
- If a number doesn't add up, or this week's Google numbers are missing, nothing is posted and the run says why.
"""
import json
import os
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_for_claude import last_full_day_pacific, periods, total  # noqa: E402  (the dashboard's own week rules)

DATA = Path(__file__).resolve().parent.parent / "data"
DASHBOARD = "https://puravbhandari-gif.github.io/opsera-analytics-dashboard/"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def stop(msg):
    print(f"Not posting to Slack: {msg}", file=sys.stderr)
    sys.exit(1)


def day_name(d):
    return f"{int(d[8:])} {MONTHS[int(d[5:7]) - 1]}"


def week_name(a, b):
    first = str(int(a[8:])) if a[5:7] == b[5:7] else day_name(a)   # "19 to 25 Oct 2026", like the dashboard
    return f"{first} to {day_name(b)} {b[:4]}"


def line(label, cur, prev, source):
    if prev:
        change = (cur - prev) / prev * 100
        trend = "no change" if abs(change) < 0.05 else f"{change:+.1f}%"
        return f"- {label}: {cur:,} (week before {prev:,}, {trend}). {source}."
    return f"- {label}: {cur:,} (week before {prev:,}). {source}."


def message():
    ga = json.loads((DATA / "analytics.json").read_text())
    leads = json.loads((DATA / "leads.json").read_text())
    gsc = json.loads((DATA / "search_console.json").read_text())
    hub = json.loads((DATA / "hubspot.json").read_text())

    last = last_full_day_pacific(ga["end_date"], ga["pulled_at"])
    full = [w for w in periods("week", ga["start_date"], last) if w["so_far"] == "no"]
    if len(full) < 2:
        stop("there aren't 2 full weeks of Google Analytics numbers yet.")
    cur, prev = full[-1], full[-2]
    if gsc["last_day_with_data"] < cur["end"]:
        stop(f"Search Console only goes to {gsc['last_day_with_data']}, before the week ends on {cur['end']}.")

    def both(rows, key, keep=lambda r: True):
        return [round(total(rows, key, w["start"], w["end"], keep)) for w in (cur, prev)]

    visits, engaged = both(ga["daily"], "sessions"), both(ga["daily"], "engagedSessions")
    robots = both(ga.get("email_robots_daily", []), "robots")   # the dashboard's "Without email robots" rule
    without = [v - r for v, r in zip(visits, robots)]
    if engaged[0] > visits[0] or engaged[1] > visits[1]:
        stop("engaged visits are higher than all visits, which can't be right.")
    if min(without) < 0:
        stop("there are more email robot visits than visits, which can't be right.")
    demos = both(leads["daily"], "demo")
    clicks = both(gsc["daily"], "clicks")
    meetings = both(hub["meetings_daily"], "count", lambda r: r["kind"] == "booked")

    hub_day = hub["pulled_at"][:10]
    return "\n".join([
        f"Opsera marketing numbers, week of {week_name(cur['start'], cur['end'])}",
        "",
        line("Website visits", *visits, "Google Analytics, includes robots"),
        line("Website visits without email robots", *without, "Google Analytics"),
        line("Engaged visits", *engaged, "Google Analytics"),
        line("Demo requests", *demos, "Google Analytics, demo form"),
        line("Clicks from Google search", *clicks, "Search Console"),
        line("Meetings booked with marketing contacts", *meetings, f"HubSpot, updated {day_name(hub_day)}"),
        "",
        f"Week before: {week_name(prev['start'], prev['end'])}. Google Analytics days follow US Pacific time.",
        f"Dashboard: {DASHBOARD}",
    ])


def main():
    text = message()
    if "--dry-run" in sys.argv:
        print(text)
        return
    url = os.environ.get("SLACK_WEBHOOK_URL")
    if not url:
        sys.exit("SLACK_WEBHOOK_URL is not set, so nothing was posted to Slack.")
    r = requests.post(url, json={"text": text}, timeout=30)
    if r.status_code != 200:
        sys.exit(f"Slack returned {r.status_code}: {r.text[:200]}")
    print("Posted to Slack:\n" + text)


if __name__ == "__main__":
    main()
