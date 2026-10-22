"""Turn LinkedIn analytics exports into data/linkedin.json for the LinkedIn tab.

The original exports stay private in ~/Desktop/Data and are never added to this
public repo. Only the numbers the tab shows are written out. Run locally:
    .venv/bin/pip install openpyxl xlrd
    .venv/bin/python scripts/convert_linkedin.py

Agreed with Purav on 21 Oct 2026: company and Kumar's numbers stay separate,
reposts are left out (LinkedIn's two sheets disagree: 251 vs 29), unpaid and
paid are shown side by side, and Life page views are left out (0 every day).
Agreed on 22 Oct 2026: Kumar's October exports are shown as LinkedIn gave them,
including 22 Oct while it was still being counted, using the 7-day copy whose
summary matches its daily rows.
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

import openpyxl
import xlrd

SRC = Path.home() / "Desktop" / "Data"
OUT = Path(__file__).resolve().parent.parent / "data" / "linkedin.json"
COMPANY = {
    "content": "opsera_content_1792593547678.xls",
    "followers": "opsera_followers_1792593581955.xls",
    "visitors": "opsera_visitors_1792593572597.xls",
}
COMPANY_OCTOBER = {   # 1 to 20 Oct 2026 (LinkedIn's company data runs about 2 days behind)
    "content": "opsera_content_1792662558792.xls",
    "followers": "opsera_followers_1792662636565.xls",
    "visitors": "opsera_visitors_1792662616762.xls",
}
COMPANY_OCTOBER_RANGE = ("2026-10-01", "2026-10-20")
EXPORTED_ON = {"company": "2026-10-22"}
KUMAR = "AggregateAnalytics_Kumar Chivukula_2026-07-01_2026-09-30.xlsx"
START, END = "2026-07-01", "2026-09-30"
KUMAR_OCTOBER = [   # (key, label, start, end); each export is its own period, never added together
    ("7d", "Last 7 days", "2026-10-16", "2026-10-22"),
    ("14d", "Last 14 days", "2026-10-09", "2026-10-22"),
    ("oct", "Since 1 Oct", "2026-10-01", "2026-10-22"),
]


def stop(msg):
    print(f"\nSTOPPED: {msg}", file=sys.stderr)
    sys.exit(1)


def iso(us_date):
    m, d, y = (int(x) for x in us_date.split("/"))
    return dt.date(y, m, d).isoformat()


def xls_sheet(name, sheet):
    ws = xlrd.open_workbook(SRC / name).sheet_by_name(sheet)
    return [ws.row_values(i) for i in range(ws.nrows)]


def by_header(rows, header_row):
    head = rows[header_row]
    return [dict(zip(head, r)) for r in rows[header_row + 1:] if any(c != "" for c in r)]


def check_days(label, dates, start=START, end=END):
    first, last = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    want = [(first + dt.timedelta(days=i)).isoformat() for i in range((last - first).days + 1)]
    if dates != want:
        stop(f"{label} doesn't cover every day from {start} to {end}.")


def company(files=COMPANY, start=START, end=END):
    metrics = by_header(xls_sheet(files["content"], "Metrics"), 1)
    check_days("Company content sheet", [iso(r["Date"]) for r in metrics], start, end)
    daily = []
    for r in metrics:
        row = {"date": iso(r["Date"])}
        for key, name in (("seen", "Impressions"), ("clicks", "Clicks"), ("reactions", "Reactions"), ("comments", "Comments")):
            unpaid, paid, total = (int(r[f"{name} ({k})"]) for k in ("organic", "sponsored", "total"))
            if unpaid + paid != total:
                stop(f"{name} on {row['date']}: unpaid {unpaid} + paid {paid} isn't LinkedIn's total {total}.")
            row.update({f"{key}_unpaid": unpaid, f"{key}_paid": paid, f"{key}_total": total})
        daily.append(row)

    posts = []
    for r in by_header(xls_sheet(files["content"], "All posts"), 1):
        title = " ".join(r["Post title"].split())
        posts.append({
            "title": title[:100] + ("..." if len(title) > 100 else ""),
            "link": r["Post link"], "created": iso(r["Created date"]),   # who posted it is left out: the page is public
            "paid": r["Post type"] != "Organic", "video": r["Content Type"] == "Video",
            "seen": int(r["Impressions"]), "clicks": int(r["Clicks"]),
            "likes": int(r["Likes"]), "comments": int(r["Comments"]),
        })

    followers = by_header(xls_sheet(files["followers"], "New followers"), 0)
    check_days("Company followers sheet", [iso(r["Date"]) for r in followers], start, end)
    followers_daily = []
    for r in followers:
        parts = int(r["Sponsored followers"]) + int(r["Organic followers"]) + int(r["Auto-invited followers"])
        if parts != int(r["Total followers"]):
            stop(f"New followers on {r['Date']} don't add up.")
        followers_daily.append({"date": iso(r["Date"]), "gained": int(r["Total followers"])})

    breakdowns = {}
    for sheet, key in (("Job function", "job_function"), ("Seniority", "seniority"), ("Location", "location"),
                       ("Industry", "industry"), ("Company size", "company_size")):
        rows = by_header(xls_sheet(files["followers"], sheet), 0)
        rows = sorted(({"name": r[sheet], "followers": int(r["Total followers"])} for r in rows), key=lambda x: -x["followers"])
        breakdowns[key] = {"label": sheet, "adds_up_to": sum(r["followers"] for r in rows), "top": rows[:10]}

    visitors = by_header(xls_sheet(files["visitors"], "Visitor metrics"), 0)
    check_days("Company visitors sheet", [iso(r["Date"]) for r in visitors], start, end)
    visitors_daily = [{
        "date": iso(r["Date"]), "views_total": int(r["Total page views (total)"]),
        "views_overview": int(r["Overview page views (total)"]), "views_jobs": int(r["Jobs page views (total)"]),
    } for r in visitors]
    if any(int(r["Life page views (total)"]) for r in visitors):
        stop("Life page views are no longer 0. Check with Purav before showing or hiding them.")

    if any(not start <= p["created"] <= end for p in posts):
        stop(f"The company post list has posts created outside {start} to {end}.")
    return {
        "source": "LinkedIn export, Opsera company page",
        "dates_note": "LinkedIn gives these dates in UTC",
        "start_date": start, "end_date": end,
        "daily": daily, "posts": posts, "followers_daily": followers_daily,
        "breakdowns": breakdowns, "visitors_daily": visitors_daily,
    }


def post_name(url):
    slug = url.rstrip("/").split("/")[-1]
    slug = re.sub(r"-(share|ugcPost|activity)-\d+.*$", "", slug.split("_", 1)[-1])
    return slug.replace("-", " ").strip().capitalize()


def us(d):
    y, m, dd = (int(x) for x in d.split("-"))
    return f"{m}/{dd}/{y}"


def kumar(name=KUMAR, start=START, end=END):
    wb = openpyxl.load_workbook(SRC / name, read_only=True, data_only=True)
    sheet = lambda name: [list(r) for r in wb[name].iter_rows(values_only=True) if any(c not in (None, "") for c in r)]

    disc = {r[0]: r[1] for r in sheet("DISCOVERY")}
    if disc.get("Overall Performance") != f"{us(start)} - {us(end)}":
        stop(f"{name} covers {disc.get('Overall Performance')}, not {start} to {end}.")
    seen, reached = int(disc["Impressions"]), int(disc["Members reached"])

    eng = sheet("ENGAGEMENT")
    daily = [{"date": iso(r[0]), "seen": int(r[1]), "engagements": int(r[2])} for r in eng[1:]]
    check_days("Kumar's engagement sheet", [r["date"] for r in daily], start, end)
    if sum(r["seen"] for r in daily) != seen:
        stop(f"Kumar's daily times seen add up to {sum(r['seen'] for r in daily)}, but the summary says {seen}.")

    fol = sheet("FOLLOWERS")
    m = re.match(r"Total followers on (\S+)", fol[0][0])
    if not m or iso(m.group(1)) != end:
        stop(f"Kumar's follower total isn't for {end}: '{fol[0][0]}'.")
    followers_daily = [{"date": iso(r[0]), "gained": int(r[1])} for r in fol[2:]]
    check_days("Kumar's followers sheet", [r["date"] for r in followers_daily], start, end)

    top = sheet("TOP POSTS")[2:]
    by_eng = [{"name": post_name(r[0]), "link": r[0], "published": iso(r[1]), "engagements": int(r[2])} for r in top if r[0]]
    by_seen = [{"name": post_name(r[4]), "link": r[4], "published": iso(r[5]), "seen": int(r[6])} for r in top if len(r) > 6 and r[4]]

    return {
        "source": "LinkedIn export, Kumar Chivukula's profile",
        "start_date": start, "end_date": end,
        "seen": seen, "reached": reached, "total_followers": int(fol[0][1]), "total_followers_date": end,
        "daily": daily, "followers_daily": followers_daily,
        "top_by_engagements": by_eng, "top_by_seen": by_seen,
    }


def main():
    oct_files = {key: f"AggregateAnalytics_Kumar Chivukula_{a}_{b}.xlsx" for key, _, a, b in KUMAR_OCTOBER}
    missing = [n for n in [*COMPANY.values(), *COMPANY_OCTOBER.values(), KUMAR, *oct_files.values()] if not (SRC / n).exists()]
    if missing:
        stop(f"Can't find these in {SRC}: {missing}")
    october = [{"key": key, "label": label, **kumar(oct_files[key], a, b)} for key, label, a, b in KUMAR_OCTOBER]
    days = {}
    for period in october:
        for r in period["daily"]:
            days.setdefault(r["date"], set()).add((r["seen"], r["engagements"]))
    clash = sorted(d for d, v in days.items() if len(v) > 1)
    if clash != [max(days)] and clash:
        stop(f"Kumar's October exports disagree on these days: {clash}")
    # The company page: July to September and October exports joined into one run of days (same source, no overlap)
    q3, octo = company(), company(COMPANY_OCTOBER, *COMPANY_OCTOBER_RANGE)
    co = {**q3, "end_date": octo["end_date"], "breakdowns": octo["breakdowns"], "breakdowns_as_of": EXPORTED_ON["company"]}
    for key in ("daily", "posts", "followers_daily", "visitors_daily"):
        co[key] = q3[key] + octo[key]
    # Kumar: July to September and the since-1-Oct export joined into one run of days
    since = next(p for p in october if p["key"] == "oct")
    k = kumar()
    k_daily, k_followers = k["daily"] + since["daily"], k["followers_daily"] + since["followers_daily"]
    check_days("Kumar's joined days", [r["date"] for r in k_daily], START, since["end_date"])
    out = {"start_date": START, "end_date": END, "company": co, "kumar": k,
           "kumar_october": {"periods": october, "still_counting": clash},
           "kumar_all": {"start_date": START, "end_date": since["end_date"], "daily": k_daily, "followers_daily": k_followers,
                         "still_counting": clash}}
    OUT.write_text(json.dumps(out, indent=1))
    c, k = out["company"], out["kumar"]
    print(f"Company: seen {sum(r['seen_total'] for r in c['daily'])}, posts {len(c['posts'])}, "
          f"followers gained {sum(r['gained'] for r in c['followers_daily'])}")
    print(f"Kumar: seen {k['seen']}, reached {k['reached']}, engagements {sum(r['engagements'] for r in k['daily'])}, "
          f"followers gained {sum(r['gained'] for r in k['followers_daily'])}, total {k['total_followers']}")
    for o in out["kumar_october"]["periods"]:
        print(f"Kumar {o['label']} ({o['start_date']} to {o['end_date']}): seen {o['seen']}, reached {o['reached']}, "
              f"engagements {sum(r['engagements'] for r in o['daily'])}, followers gained {sum(r['gained'] for r in o['followers_daily'])}")


if __name__ == "__main__":
    main()
