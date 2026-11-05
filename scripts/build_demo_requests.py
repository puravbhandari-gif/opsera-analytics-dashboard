"""Turn David's "DG-Demo Requests" Salesforce export into data/demo_requests.json for the Leads tab: what happened
to each demo request, as counts per day only. The export holds names and emails, so it stays in
~/Desktop/Data/salesforce-exports, never in the repo. Run by hand when a new export arrives:
    .venv/bin/python scripts/build_demo_requests.py

Agreed with Purav on 5 Nov 2026: groups from Lead Status.
Made stricter the same day: 5 groups.
- Qualified: Meeting Set, Engaging
- Not reviewed yet: Open, Assigned
- Already a contact: the person is already a Salesforce contact
- Not now: Nurture
- Disqualified: Disqualified
From the 5 Nov export, which has X-Factor: an X4 Basic Lead counts as Disqualified, whatever its Lead Status. Each request
counts once. Every demo request gets X1 automatically, so X1 isn't a quality signal; X-Factor is also shown on its own.
Each request counts on the day the person joined the campaign (Member First Associated Date). Each person counts once.
"""
import collections
import datetime as dt
import glob
import json
import os
import re
import sys
from html import unescape
from pathlib import Path

EXPORTS = Path(os.path.expanduser("~/Desktop/Data/salesforce-exports"))
OUT = Path(__file__).resolve().parent.parent / "data" / "demo_requests.json"
GROUPS = {"Meeting Set": "qualified", "Engaging": "qualified", "Open": "open", "Assigned": "open", "Contact": "contact",
          "Nurture": "not_now", "Disqualified": "disqualified"}
ORDER = ("qualified", "open", "contact", "not_now", "disqualified")
X_FACTORS = {"x1": "X1", "x2": "X2", "x3": "X3", "x4": "X4"}   # X1 Sales Ready, X2 Hot Lead, X3 Mid-Quality, X4 Basic Lead


def main():
    files = sorted(glob.glob(str(EXPORTS / "DG-Demo Requests-*.xls")))
    if not files:
        sys.exit("No DG-Demo Requests export in ~/Desktop/Data/salesforce-exports.")
    path = files[-1]   # the newest, by the date in its name
    text = Path(path).read_text(encoding="latin-1")
    rows = [[unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            for r in re.findall(r"<tr>(.*?)</tr>", text, re.S)]
    head, rows = rows[0], [dict(zip(rows[0], r)) for r in rows[1:]]
    status = lambda r: "Contact" if r["Member Type"] == "Contact" else r["Lead/Contact Status"]
    unknown = {status(r) for r in rows} - set(GROUPS)
    if unknown:   # a new Lead Status needs a group before the page can show it
        sys.exit(f"Lead Status not in any group yet: {', '.join(sorted(unknown))}. Nothing was written.")
    xf = lambda r: (r.get("X-Factor") or "")[:2].lower()   # "X4 Basic Lead" -> "x4"
    days, statuses = collections.defaultdict(collections.Counter), collections.Counter()
    for r in rows:
        d = dt.datetime.strptime(r["Member First Associated Date"], "%m/%d/%Y").date().isoformat()
        days[d]["disqualified" if xf(r) == "x4" else GROUPS[status(r)]] += 1
        if xf(r) in X_FACTORS:
            days[d][xf(r)] += 1
        statuses[status(r)] += 1
    exported = re.search(r"(\d{4}-\d{2}-\d{2})-\d{2}-\d{2}-\d{2}\.xls$", path).group(1)
    OUT.write_text(json.dumps({
        "source": "Salesforce campaign DG-Demo Requests, Lead Status",
        "exported": exported, "start_date": min(days), "end_date": (dt.date.fromisoformat(exported) - dt.timedelta(days=1)).isoformat(),
        "statuses": dict(statuses.most_common()),
        "has_x_factor": "X-Factor" in head,
        "x4_by_status": dict(collections.Counter(status(r) for r in rows if xf(r) == "x4").most_common()),
        "daily": [{"date": d, **{g: days[d][g] for g in ORDER + tuple(X_FACTORS)}} for d in sorted(days)],
    }, indent=1) + "\n")
    print(f"Demo requests: {len(rows)} people, {dict(statuses.most_common())}")


if __name__ == "__main__":
    main()
