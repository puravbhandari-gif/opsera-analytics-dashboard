"""Pull the Opsera GTM calendar from Notion into data/gtm_calendar.json, for the markers on dated charts.
Read-only. Needs the NOTION_TOKEN env var (a GitHub secret, a Notion internal integration with
"Read content" only and "No user information", shared with the GTM Calendar database).

Agreed with Purav on 28 Oct 2026:
- Only the item name, its types and its ship date are kept. Owner, Assignee, Latest, links and
  everything else are never stored.
- Items with no ship date or no type are left out.
- Names are cleaned so no person shows: text in brackets and anything after " with " are cut,
  and any team member's first name is taken out.
"""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import requests

DATABASE = "3959f3f977cd80088f52cd4a84574140"
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "gtm_calendar.json"
SOURCE = "Opsera GTM calendar in Notion, ship dates"


def first_names():
    team = json.loads((ROOT / "team.json").read_text())
    return {p["name"].split()[0] for p in team["people"]}


def clean_name(name, names):
    name = re.sub(r"\s*\([^)]*\)", "", name)            # "(sponsor, Kumar on panel)", "(SamsonPR)"
    name = re.sub(r"\s+with\s+.*$", "", name, flags=re.I)  # "podcast with <guest>"
    for n in names:
        name = re.sub(rf"\b{re.escape(n)}\b(\s+and\b)?", "", name)
    return re.sub(r"\s{2,}", " ", name).strip(" ,:-")


def clean_items(rows):
    """rows: dicts with name, types (list), date, end. Returns the public list, oldest first."""
    names = first_names()
    out = []
    for r in rows:
        if not r.get("date") or not r.get("types"):
            continue
        item = {"name": clean_name(r["name"], names), "types": sorted(r["types"]), "date": r["date"][:10]}
        if r.get("end") and r["end"][:10] != item["date"]:
            item["end"] = r["end"][:10]
        out.append(item)
    return sorted(out, key=lambda i: (i["date"], i["name"]))


def pull(token):
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {token}", "Notion-Version": "2022-06-28"})
    rows, cursor = [], None
    while True:
        body = {"page_size": 100, "filter": {"property": "Ship date", "date": {"is_not_empty": True}}}
        if cursor:
            body["start_cursor"] = cursor
        r = s.post(f"https://api.notion.com/v1/databases/{DATABASE}/query", json=body, timeout=60)
        r.raise_for_status()
        page = r.json()
        for p in page["results"]:
            props = p["properties"]   # only the 3 fields below are read
            ship = (props.get("Ship date") or {}).get("date") or {}
            rows.append({
                "name": "".join(t["plain_text"] for t in props["Name"]["title"]),
                "types": [o["name"] for o in (props.get("Type") or {}).get("multi_select", [])],
                "date": ship.get("start"),
                "end": ship.get("end"),
            })
        if not page.get("has_more"):
            return rows
        cursor = page["next_cursor"]


def write(items):
    OUT.write_text(json.dumps({
        "source": SOURCE,
        "pulled_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "items": items,
    }, indent=1) + "\n")
    print(f"Wrote {len(items)} calendar items to {OUT.relative_to(ROOT)}")


def main():
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        sys.exit("NOTION_TOKEN is not set, so the GTM calendar was not pulled.")
    write(clean_items(pull(token)))


if __name__ == "__main__":
    main()
