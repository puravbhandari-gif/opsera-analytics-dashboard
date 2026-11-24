"""Write data/linkedin_to_site.json for the "LinkedIn to website" tab (asked for by Purav, 24 Nov 2026).

From LinkedIn post to demo form, split by who posted. Each post's link carries UTM tags (from 27 Oct 2026 for the brand
page, 17 Nov 2026 for Kumar), and Google Analytics sees the same tags on the visit, so visits are matched to posts by tag:
  utm_content brand-post, or utm_campaign brand-page (the profile button)  -> brand page
  utm_content kumar, or utm_campaign kumar (the profile button)            -> Kumar
  utm_content vishnu                                                        -> other Opsera people
  medium cpc or paidsocial                                                  -> LinkedIn ads
  anything else from LinkedIn                                               -> LinkedIn, account unknown
Steps, each counted as visits (sessions): landed, reached a product page, reached /demo, sent the demo form.
Times seen and clicks come from LinkedIn's exports (data/linkedin.json); links and their tags from data/linkedin_posts.json.
Sources are never added together: LinkedIn's numbers and Google Analytics' numbers sit side by side.
Needs the Google Analytics key, like fetch_data.py. Run: python scripts/build_linkedin_to_site.py
"""
import datetime as dt
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_data as f   # noqa: E402  (the same Google Analytics sign-in, filters and page rules)

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "linkedin_to_site.json"
DAYS = 120   # enough for the last 90 days and this fiscal quarter
PRODUCT = r"(?i)^/(software-factory|forge|unified-insights|agents|agentic-devops|salesforce-devops|brickforge)(/.*)?/?$"   # the site menu's product pages
DEMO = r"(?i)^/demo/?$"
TAGS_FROM = {"brand": "2026-10-27", "kumar": "2026-11-17"}   # first visit from a tagged post link, found 24 Nov 2026
ACCOUNTS = {"brand": "Brand page", "kumar": "Kumar", "vishnu": "Other Opsera people", "ads": "LinkedIn ads", "unknown": "LinkedIn, account unknown"}


def group(src, med, camp, content):
    """The same rule as every other LinkedIn panel: fetch_data.linkedin_group (agreed 24 Nov 2026)."""
    return {"company": "brand", "people": "vishnu", "untagged": "unknown"}.get(g := f.linkedin_group(src, camp, med, content), g)


def tag(camp, content, g):
    return f"{camp} / {content}" if g in ("brand", "kumar", "vishnu") else ""


def ga_rows(s, start, end):
    li = {"filter": {"fieldName": "sessionSource", "stringFilter": {"matchType": "FULL_REGEXP", "value": f.LINKEDIN_SOURCES, "caseSensitive": False}}}
    page = lambda rx: {"filter": {"fieldName": "pagePath", "stringFilter": {"matchType": "FULL_REGEXP", "value": rx, "caseSensitive": False}}}
    both = lambda x: {"andGroup": {"expressions": [li, x]}}
    dims = ["date", "sessionSource", "sessionMedium", "sessionCampaignName", "sessionManualAdContent"]
    key = lambda r: (r["date"], group(r["sessionSource"], r["sessionMedium"], r["sessionCampaignName"], r["sessionManualAdContent"]),
                     tag(r["sessionCampaignName"], r["sessionManualAdContent"], group(r["sessionSource"], r["sessionMedium"], r["sessionCampaignName"], r["sessionManualAdContent"])))
    landed, opened, steps = {}, {}, {}
    for r in f.ga_report(s, end, dims + ["landingPage"], ["sessions", "engagedSessions"], flt=li, start=start):
        lp = r["landingPage"] if r["landingPage"] == "(not set)" else f.page_key(r["landingPage"])
        v = landed.setdefault(key(r) + (lp,), [0, 0])
        v[0] += r["sessions"]; v[1] += r["engagedSessions"]
    for r in f.ga_report(s, end, dims + ["pagePath"], ["sessions"], flt=li, start=start):
        k = key(r) + (f.page_key(r["pagePath"]),)
        opened[k] = opened.get(k, 0) + r["sessions"]
    # each step counts a visit once, however many product pages it opened
    for i, (flt, ev) in enumerate([(both(page(PRODUCT)), None), (both(page(DEMO)), None), (page(r"(?i)^/demo/?$"), [f.FORM_EVENT])]):
        rows = f.ga_report(s, end, dims, ["sessions"], flt=flt if ev is None else both(flt), start=start, event_names=ev)
        for r in rows:
            steps.setdefault(key(r), [0, 0, 0])[i] += r["sessions"]
    return ([[*k, *v] for k, v in sorted(landed.items())], [[*k, v] for k, v in sorted(opened.items())],
            [[*k, *v] for k, v in sorted(steps.items())])


def activity_id(url):
    m = re.search(r"(?:activity[:-])(\d{15,})", url or "")
    return m.group(1) if m else None


def slug(url):
    s = (url or "").rsplit("/", 1)[-1].split("_", 1)[-1]
    return re.sub(r"-(share|ugcPost|activity)-\d+.*$", "", s)[:30]


def posts(start):
    li = json.loads((DATA / "linkedin.json").read_text())
    scraped = json.loads((DATA / "linkedin_posts.json").read_text())["posts"]
    links = {}
    for p in scraped:
        pages = p["opsera_pages"] + [c for c in p.get("comment_pages", []) if "lands_on" in c]
        links[(p["account"], activity_id(p["post"]) or slug(p["post"]))] = (p, pages)
    out = []
    for c in li["company"]["posts"]:
        if c["created"] < start:
            continue
        p, pages = links.get(("company", activity_id(c["link"])), (None, []))
        out.append({"date": c["created"], "account": "brand", "title": c["title"], "post": c["link"], "seen": c["seen"], "clicks": c["clicks"],
                    "clicks_note": "LinkedIn counts every click on the post", "paid": c.get("paid", False), "links": link_rows(pages), "scraped": bool(p)})
    # Kumar: times seen from the newest export listing the post; link visits only for his 3 latest posts
    seen, visits = {}, {}
    for per in sorted(li["kumar_october"]["periods"], key=lambda x: x["end_date"]):
        for r in per.get("top_by_seen", []) + [x for x in per.get("recent_posts", []) if x.get("seen") is not None]:
            seen[(r["published"], slug(r["link"]))] = max(seen.get((r["published"], slug(r["link"])), 0), r["seen"])
        for r in per.get("recent_posts", []):
            if r.get("link_visits") is not None:
                visits[(r["published"], slug(r["link"]))] = r["link_visits"]
    kumar_scraped = sorted((p for p in scraped if p["account"] == "kumar" and p["date_pacific"] >= start), key=lambda p: p["date_pacific"])
    near = lambda k, p: abs((dt.date.fromisoformat(k[0]) - dt.date.fromisoformat(p["date_pacific"])).days) <= 1
    # 1: the same words in both addresses. 2: what's left, by day, when exactly 1 post on each side is within a day
    match = {}
    for p in kumar_scraped:
        k = next((k for k in seen if k not in match.values() and slug(p["post"])[:20] == k[1][:20] and near(k, p)), None)
        if k:
            match[p["post"]] = k
    for p in kumar_scraped:
        if p["post"] in match:
            continue
        ks = [k for k in seen if k not in match.values() and near(k, p)]
        ps = [q for q in kumar_scraped if q["post"] not in match and ks and near(ks[0], q)]
        if len(ks) == 1 and len(ps) == 1:
            match[p["post"]] = ks[0]
    used = set(match.values())
    kp = DATA / "kumar_post_list.json"
    titles = {activity_id(x["link"]): x["title"] for x in (json.loads(kp.read_text())["posts"] if kp.exists() else [])}
    for p in kumar_scraped:
        k = match.get(p["post"])
        pages = p["opsera_pages"] + [c for c in p.get("comment_pages", []) if "lands_on" in c]
        out.append({"date": p["date_pacific"], "account": "kumar", "title": titles.get(activity_id(p["post"])) or slug(p["post"]).replace("-", " ").capitalize(), "post": p["post"],
                    "seen": seen.get(k), "clicks": visits.get(k), "clicks_note": "Visits to links, only in LinkedIn's list of his 3 latest posts",
                    "links": link_rows(pages), "scraped": True})
    for k, n in seen.items():
        if k not in used and k[0] >= start:
            out.append({"date": k[0], "account": "kumar", "title": k[1].replace("-", " ").capitalize(), "post": "", "seen": n, "clicks": visits.get(k),
                        "clicks_note": "Visits to links, only in LinkedIn's list of his 3 latest posts", "links": [], "scraped": False})
    return sorted(out, key=lambda x: (x["date"], x["account"]), reverse=True)


def link_rows(pages):
    seen, rows = set(), []
    for x in pages:
        u = x.get("utm") or {}
        k = (x["lands_on"], u.get("utm_campaign", ""), u.get("utm_content", ""))
        if k in seen:
            continue
        seen.add(k)
        g = group(u.get("utm_source", ""), u.get("utm_medium", ""), u.get("utm_campaign", ""), u.get("utm_content", "")) if u else ""
        rows.append({"page": x["lands_on"], "tag": tag(u.get("utm_campaign", ""), u.get("utm_content", ""), g) if u else "", "tagged": bool(u.get("utm_source"))})
    return rows


def main():
    s = f.session()
    end = (dt.datetime.now(f.PACIFIC).date() - dt.timedelta(days=1)).isoformat() if hasattr(f, "PACIFIC") else (dt.date.today() - dt.timedelta(days=1)).isoformat()
    start = (dt.date.fromisoformat(end) - dt.timedelta(days=DAYS)).isoformat()
    landed, opened, steps = ga_rows(s, start, end)
    li = json.loads((DATA / "linkedin.json").read_text())
    out = {
        "source": "Google Analytics for visits and pages, LinkedIn exports for times seen and clicks, LinkedIn posts read with Apify for links",
        "start_date": start, "end_date": end, "pulled_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "tags_from": TAGS_FROM, "accounts": ACCOUNTS, "product_pages": PRODUCT, "demo_page": "/demo",
        "linkedin_ends": {"brand": li["company"]["end_date"], "kumar": li["kumar_all"]["end_date"]},
        "landed": landed, "opened": opened, "steps": steps, "posts": posts(start),
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    tot = lambda g: sum(r[4] for r in landed if r[1] == g)
    print(f"LinkedIn to website, {start} to {end}: " + ", ".join(f"{ACCOUNTS[g]} {tot(g)}" for g in ACCOUNTS) + f"; {len(out['posts'])} posts")


if __name__ == "__main__":
    main()
