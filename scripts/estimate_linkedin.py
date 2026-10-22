"""Best-guess split of Untagged LinkedIn visits into company page, Kumar and Can't tell.
Reads data/analytics.json and data/linkedin_posts.json, writes data/linkedin_estimate.json.

Agreed with Purav on 22 Oct 2026: an Untagged visit goes to the company page or to Kumar
only when just one of them posted a link to that landing page on the day of the visit or
the 3 days before. If both did, or neither did, it stays "Can't tell". These lines are kept
apart from the tagged numbers and are never added to them.
"""
import datetime as dt
import json
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"
WINDOW_DAYS = 3   # the day of the post and the 3 days after


def stop(msg):
    print(f"\nSTOPPED: {msg}", file=sys.stderr)
    sys.exit(1)


def same_page(visit_page, link_page):
    """Same page, or the same blog slug cut short (the old site trimmed some blog addresses)."""
    if visit_page == link_page:
        return True
    if "/" in (visit_page, link_page) or visit_page == "(not set)":
        return False
    short, long_ = sorted((visit_page, link_page), key=len)
    return long_.startswith(short + "-")


def main():
    ga = json.loads((DATA / "analytics.json").read_text())
    posts = json.loads((DATA / "linkedin_posts.json").read_text())
    li = ga["linkedin"]
    links = [(p["account"], p["date_pacific"], x["lands_on"], p["post"]) for p in posts["posts"] for x in p["opsera_pages"]]
    links += [(p["account"], c["date_pacific"], c["lands_on"], p["post"]) for p in posts["posts"] for c in p.get("comment_pages", [])]

    daily, matches = {}, {}
    for v in li["landing_daily"]:
        if v["group"] != "untagged" or v["date"] < posts["start_date"]:
            continue   # posts are only checked from their start date, so earlier visits aren't estimated
        day = dt.date.fromisoformat(v["date"])
        who = {acct for acct, posted, page, _ in links
               if same_page(v["page"], page) and 0 <= (day - dt.date.fromisoformat(posted)).days <= WINDOW_DAYS}
        group = f"estimated_{next(iter(who))}" if len(who) == 1 else "cant_tell"
        row = daily.setdefault((v["date"], group), {"date": v["date"], "group": group, "visits": 0, "engaged": 0})
        row["visits"] += v["visits"]
        row["engaged"] += v["engaged"]
        if who:
            m = matches.setdefault((v["page"], group), {"page": v["page"], "group": group, "visits": 0, "engaged": 0,
                                                       "accounts": sorted(who), "dates": set()})
            m["visits"] += v["visits"]
            m["engaged"] += v["engaged"]
            m["dates"].add(v["date"])

    untagged = sum(r["visits"] for r in li["daily"] if r["group"] == "untagged" and r["date"] >= posts["start_date"])
    split = sum(r["visits"] for r in daily.values())
    if abs(split - untagged) > max(2, untagged * 0.01):
        stop(f"Untagged visits by landing page add up to {split}, but Untagged by day is {untagged}.")
    out = {
        "source": "Google Analytics, opsera.ai 2026, matched to LinkedIn posts found through Apify",
        "window_days": WINDOW_DAYS, "posts_pulled_at": posts["pulled_at"],
        "daily": sorted(daily.values(), key=lambda r: (r["date"], r["group"])),
        "matches": sorted(({**m, "dates": sorted(m["dates"])} for m in matches.values()), key=lambda m: -m["visits"]),
        "linked_posts": [{"account": a, "date": d, "page": pg, "post": url} for a, d, pg, url in sorted(links, key=lambda x: x[1])],
        "untagged_total": untagged,
        "start_date": posts["start_date"], "end_date": ga["end_date"], "pulled_at": ga["pulled_at"],   # the estimate only covers days up to here
    }
    (DATA / "linkedin_estimate.json").write_text(json.dumps(out, indent=1))
    for g in ("estimated_company", "estimated_kumar", "cant_tell"):
        print(f"{g}: {sum(r['visits'] for r in daily.values() if r['group'] == g)} visits")
    print(f"(Untagged by landing page: {split}; Untagged by day: {untagged})")


if __name__ == "__main__":
    main()
