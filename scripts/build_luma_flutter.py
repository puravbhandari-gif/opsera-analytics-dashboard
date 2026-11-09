"""Turn Valentina's Luma guest list for Flutter 2026 into data/luma_flutter.json for the Events tab: counts only.
The list holds names and emails, so it stays in ~/Desktop/Data, never in the repo. Run by hand when a new list arrives:
    .venv/bin/python scripts/build_luma_flutter.py

Agreed with Purav on 9 Nov 2026:
- Registered is every row in the list. Confirmed is approval status "approved". Attended is a check-in time.
- Opsera staff (ticket "Opsera") are counted on their own, so attended can be shown with and without them.
- Registrations by UTM source; sources with fewer than 5 registrations share one "Other sources" line.
"""
import collections
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

LISTS = Path.home() / "Desktop" / "Data"
OUT = Path(__file__).resolve().parent.parent / "data" / "luma_flutter.json"
SMALL = 5
SOURCE_NAMES = {"": "No source tag", "newsletter": "Newsletter", "aakashnewsletter": "Aakash's newsletter", "execteam": "Exec team",
                "email": "Email", "sv": "sv", "fb": "Facebook", "opsera_staff": "Opsera staff", "ph": "ph",
                "deepview": "The Deep View", "opserasocial": "Opsera social"}


def main():
    found = sorted(LISTS.glob("Opsera Flutter 2026_ The AI-SDLC Summit - Guests - *.csv"))
    if not found:
        sys.exit("No Flutter 2026 Luma guest list in ~/Desktop/Data.")
    path = found[-1]   # the newest, by the date in its name
    rows = list(csv.DictReader(path.open(encoding="utf-8-sig")))
    staff = lambda r: r["ticket_name"] == "Opsera"
    checked = lambda r: bool(r["checked_in_at"].strip())
    status = collections.Counter(r["approval_status"] for r in rows)
    by_source = collections.defaultdict(lambda: [0, 0, 0])   # registered, confirmed, attended
    for r in rows:
        x = by_source[(r["utm_source"] or "").strip().lower()]
        x[0] += 1
        x[1] += r["approval_status"] == "approved"
        x[2] += checked(r)
    sources, other = [], [0, 0, 0]
    for k, v in sorted(by_source.items(), key=lambda kv: -kv[1][0]):
        if v[0] < SMALL:
            other = [a + b for a, b in zip(other, v)]
        else:
            sources.append({"source": SOURCE_NAMES.get(k, k), "registered": v[0], "confirmed": v[1], "attended": v[2]})
    if other[0]:
        sources.append({"source": f"Other sources (under {SMALL} each)", "registered": other[0], "confirmed": other[1], "attended": other[2]})
    exported = re.search(r"(\d{4}-\d{2}-\d{2})-\d{2}-\d{2}-\d{2}\.csv$", path.name).group(1)
    OUT.write_text(json.dumps({
        "source": "Luma guest list for Flutter 2026, from Valentina", "exported": exported, "read": dt.date.today().isoformat(),
        "registered": len(rows), "confirmed": status.get("approved", 0), "waitlist": status.get("pending_approval", 0),
        "declined": status.get("declined", 0), "attended": sum(checked(r) for r in rows),
        "attended_staff": sum(checked(r) and staff(r) for r in rows), "sources": sources,
    }, indent=1) + "\n")
    print(f"Flutter on Luma: {len(rows)} registered, {status.get('approved', 0)} confirmed, {sum(checked(r) for r in rows)} attended")


if __name__ == "__main__":
    main()
