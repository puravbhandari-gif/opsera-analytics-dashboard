"""Ahrefs estimates for the PR and media tab, labelled "Ahrefs estimate" on the page: each outlet's Domain
Rating (for the outlet tier), and for each piece its estimated monthly visits from Google, its top searches
and whether it links to opsera.ai. Writes data/pr_media_ahrefs.json.

Our plan is Lite, which isn't known to include API keys, so this doesn't run on Mondays (Purav, 4 Nov 2026).
Once a month Claude Code refreshes the file through its Ahrefs connection. If a plan with API keys comes
later, set AHREFS_API_KEY and run this script; it looks up only pieces older than 28 days or new. Every call
costs at least 50 units.

Outlet tier from Domain Rating: top tier 85 and up, trade press 70 to 84, other below 70.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "pr_media_ahrefs.json"
API = "https://api.ahrefs.com/v3"
REFRESH_DAYS = 28   # look everything up again after this many days


def site(url):
    return urlparse(url).netloc.lower().removeprefix("www.")


def tier(dr):
    return None if dr is None else "Top tier" if dr >= 85 else "Trade press" if dr >= 70 else "Other"


def call(method, path, key, **kw):
    r = requests.request(method, f"{API}/{path}", headers={"Authorization": f"Bearer {key}", "Accept": "application/json"}, timeout=120, **kw)
    if r.status_code != 200:
        sys.exit(f"Ahrefs {path} returned {r.status_code}, so the Ahrefs estimates weren't updated.")
    return r.json()


def main():
    key = os.environ.get("AHREFS_API_KEY")
    if not key:
        sys.exit("The AHREFS_API_KEY secret is missing, so the Ahrefs estimates weren't updated.")
    pr = json.loads((DATA / "pr_media.json").read_text())
    have = json.loads(OUT.read_text()) if OUT.exists() else {"by_domain": {}, "by_link": {}}
    today = dt.date.today()
    fresh = lambda row: row and (today - dt.date.fromisoformat(row["checked"])).days < REFRESH_DAYS
    links = [x["link"] for x in pr["items"] if not fresh(have["by_link"].get(x["link"]))]
    domains = sorted({site(x["link"]) for x in pr["items"]} - {d for d, v in have["by_domain"].items() if fresh(v)})

    if domains:
        res = call("POST", "batch-analysis/batch-analysis", key, json={"select": ["domain_rating"], "targets": [
            {"url": f"https://{d}", "mode": "subdomains", "protocol": "both"} for d in domains]})
        for d, t in zip(domains, res["targets"]):
            have["by_domain"][d] = {"domain_rating": t.get("domain_rating"), "tier": tier(t.get("domain_rating")), "checked": today.isoformat()}
    for i in range(0, len(links), 100):
        part = links[i:i + 100]
        res = call("POST", "batch-analysis/batch-analysis", key, json={"select": ["org_traffic", "org_keywords"], "targets": [
            {"url": u, "mode": "exact", "protocol": "both"} for u in part]})
        linked = call("GET", "site-explorer/all-backlinks", key, params={
            "target": "opsera.ai", "mode": "subdomains", "history": "all_time", "limit": 1000, "select": "url_from,is_dofollow",
            "where": json.dumps({"or": [{"field": "url_from", "is": ["eq", u]} for u in part]})})["backlinks"]
        for u, t in zip(part, res["targets"]):
            top = []
            if t.get("org_keywords"):   # only pieces that rank for something cost a keyword lookup
                top = [k["keyword"] for k in call("GET", "site-explorer/organic-keywords", key, params={
                    "target": u, "mode": "exact", "date": today.isoformat(), "select": "keyword,sum_traffic", "limit": 3,
                    "order_by": "sum_traffic:desc"})["keywords"]]
            links_from = [b for b in linked if b["url_from"] == u]
            have["by_link"][u] = {"org_traffic": t.get("org_traffic"), "top_keywords": top, "links_to_opsera": bool(links_from),
                                  "followed_link": any(b["is_dofollow"] for b in links_from), "checked": today.isoformat()}
    have.update({"source": "Ahrefs estimates", "checked": today.isoformat()})
    OUT.write_text(json.dumps(have, indent=1) + "\n")
    print(f"Ahrefs: looked up {len(domains)} outlets and {len(links)} pieces")


if __name__ == "__main__":
    main()
