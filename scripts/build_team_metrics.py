"""Work out the Team metrics tab from team.json and the data the dashboard already has, into
data/team_metrics.json. Makes no calls to Google, HubSpot or LinkedIn. Runs every Monday after the pulls:
    python3 scripts/build_team_metrics.py

For each metric: the baseline (the monthly average over the months in team.json), this month so far,
the goal (null shows as "To set", never a guess) and how far along it is.
Agreed with Purav on 27 Oct 2026. His baselines were checked against what he sent: 11,142 visits,
3,749 search and AI visits, 41 asset downloads, 8 demo requests, 22,862 unpaid impressions,
449 LinkedIn visits and 3 LinkedIn asset downloads.
"""
import calendar
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ASSET_PAGES = ("/resources/report/", "/resources/white-papers/", "/resources/ebooks/", "/resources/comparison-guides/")
load = lambda name: json.loads((DATA / name).read_text())


def stop(msg):
    print(f"\nSTOPPED: {msg}", file=sys.stderr)
    sys.exit(1)


def last_full_day_pacific(end, pulled_at):
    """The same rule as the page: Google Analytics days follow US Pacific time."""
    pt = dt.datetime.fromisoformat(pulled_at).astimezone(ZoneInfo("America/Los_Angeles")).date().isoformat()
    return end if pt > end else (dt.date.fromisoformat(end) - dt.timedelta(days=1)).isoformat()


def metrics():
    """Every metric a person can track: label, source, first day, last full day and its daily rows (date, value)."""
    ga, leads, li, look = load("analytics.json"), load("leads.json"), load("linkedin.json"), load("lookup.json")
    ga_last = last_full_day_pacific(ga["end_date"], ga["pulled_at"])
    start = dt.date.fromisoformat(look["start_date"])
    asset = lambda page: (page + "/").startswith(ASSET_PAGES)
    co = li["company"]
    return {
        "website_visits": ("Website visits, overall", "Google Analytics", ga["start_date"], ga_last,
                           [(r["date"], r["sessions"]) for r in ga["daily"]]),
        # Search engines are Google Analytics' Organic Search group. AI tools are counted by source, as on the AEO tab.
        "search_and_ai_visits": ("Visits from search engines and AI tools", "Google Analytics", ga["start_date"], ga_last,
                                 [(r["date"], r["sessions"]) for r in ga["channel_daily"] if r["sessionDefaultChannelGroup"] == "Organic Search"]
                                 + [(r["date"], r["visits"]) for r in ga["ai"]["daily"]]),
        "asset_downloads": ("Asset downloads (reports, white papers, ebooks, comparison guides)", "Google Analytics", look["start_date"], ga_last,
                            [((start + dt.timedelta(days=r[0])).isoformat(), r[3]) for r in look["forms"] if asset(look["pages"][r[1]])]),
        "demo_requests": ("Demo requests", "Google Analytics", leads["start_date"], ga_last,
                          [(r["date"], r["demo"]) for r in leads["daily"]]),
        "linkedin_unpaid_impressions": ("Impressions, unpaid", "LinkedIn exports", co["start_date"], co["end_date"],
                                        [(r["date"], r["seen_unpaid"]) for r in co["daily"]]),
        "linkedin_visits": ("Visits to opsera.ai from LinkedIn", "Google Analytics", ga["start_date"], ga_last,
                            [(r["date"], r["visits"]) for r in ga["linkedin"]["daily"]]),
        "linkedin_asset_downloads": ("Asset downloads from LinkedIn visits", "Google Analytics", ga["start_date"], ga_last,
                                     [(r["date"], r["count"]) for r in ga["linkedin"]["forms"] if r.get("asset")]),
    }, ga_last


def main():
    team = json.loads((ROOT / "team.json").read_text())
    known, ga_last = metrics()
    ga = load("analytics.json")
    base = team["baseline"]
    months = []
    m = dt.date.fromisoformat(base["start"])
    while m.isoformat() <= base["end"]:
        months.append(m.isoformat()[:7])
        m = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    this_month = ga_last[:7]
    month_start = f"{this_month}-01"
    days_in_month = calendar.monthrange(int(this_month[:4]), int(this_month[5:]))[1]
    out = {"baseline": {**base, "months": months}, "month": this_month, "month_days": days_in_month, "people": []}
    for person in team["people"]:
        sections = []
        for sec in person["sections"]:
            rows = []
            for item in sec["metrics"]:
                if item["metric"] not in known:
                    stop(f"{person['name']} has a metric the dashboard doesn't know: {item['metric']}. Known: {', '.join(known)}")
                label, source, first, last, daily = known[item["metric"]]
                if first > base["start"] or last < base["end"]:
                    stop(f"{label} only has data from {first} to {last}, which doesn't cover the baseline months.")
                by_month = {mo: sum(v for d, v in daily if d[:7] == mo) for mo in months}
                so_far = sum(v for d, v in daily if month_start <= d <= last) if last >= month_start else None
                goal = item.get("goal")
                rows.append({"metric": item["metric"], "label": label, "source": source,
                             "baseline": round(sum(by_month.values()) / len(months), 1), "baseline_by_month": by_month,
                             "so_far": so_far, "so_far_start": month_start, "so_far_end": last if last >= month_start else None,
                             "days_counted": int(last[8:]) if last >= month_start else 0,
                             "goal": goal, "goal_share_pct": round(so_far / goal * 100, 1) if goal and so_far is not None else None})
                if item["metric"] == "website_visits":
                    # the same visits without email robots: non-engaged visits with a robot sign (see fetch_data.py)
                    robots = [(r["date"], r["robots"]) for r in ga.get("email_robots_daily", [])]
                    if robots:
                        free = lambda a, b: sum(v for d, v in daily if a <= d <= b) - sum(v for d, v in robots if a <= d <= b)
                        rows[-1]["without_email_robots"] = {
                            "baseline": round(free(base["start"], base["end"]) / len(months), 1),
                            "so_far": free(month_start, last) if last >= month_start else None}
            sections.append({"title": sec["title"], "metrics": rows})
        out["people"].append({"name": person["name"], "sections": sections})
    (DATA / "team_metrics.json").write_text(json.dumps(out, indent=1))
    for p in out["people"]:
        print(p["name"])
        for s in p["sections"]:
            for r in s["metrics"]:
                print(f"  {r['label'][:45]:45} baseline {r['baseline']:>9,.1f}  so far {r['so_far'] if r['so_far'] is not None else '-':>7}  "
                      f"goal {r['goal'] or 'To set'}  {str(r['goal_share_pct']) + '%' if r['goal_share_pct'] is not None else ''}")


if __name__ == "__main__":
    main()
