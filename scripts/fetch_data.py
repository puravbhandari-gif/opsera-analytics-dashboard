"""Pull opsera.ai numbers from our own Google Search Console and Google Analytics 4
into JSON files under /data. Read-only. Run: python3 scripts/fetch_data.py

The service account key is read from the GOOGLE_APPLICATION_CREDENTIALS path
(locally) or the GOOGLE_SA_KEY env var holding the JSON (in GitHub Actions).
"""
import datetime as dt
import json
import re
import os
import sys
from pathlib import Path
from urllib.parse import quote, urlparse

from google.auth.transport.requests import AuthorizedSession
from google.oauth2 import service_account

START_DATE = "2026-04-01"   # from 1 Apr, so "Last 3 months" can compare with the 3 months before (agreed 22 Oct 2026)
LEADS_START = START_DATE   # Sep added 22 Oct 2026; the old site sent 17 September form fills only to Google, not HubSpot (noted on the page)
GA_PROPERTY_ID = "256856286"
GA_PROPERTY_NAME = "opsera.ai 2026"
GA_MEASUREMENT_ID = "G-63FKQPLYRW"
GSC_DOMAIN = "opsera.ai"
SCOPES = [
    "https://www.googleapis.com/auth/webmasters.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
]
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

# Google estimates each split of visits on its own, so days or sources can add up to
# slightly less than the overall total. Within this gap we show both with a note;
# outside it something is wrong and we stop.
GA_SPLIT_MIN_SHARE = 0.95
GA_SPLIT_MAX_SHARE = 1.01

# Leads: one HubSpot form submission per real fill, sorted by the page it happened on.
# Agreed with Purav on 21 Oct 2026.
FORM_EVENT = "hs_form_submission"
LEAD_LINES = [
    ("demo", "Demo requests", lambda p: p in ("/demo", "/demo/")),
    ("contact", "Contact forms", lambda p: p in ("/contact", "/contact/")),
    ("gartner_offer", "Gartner free modernization offer", lambda p: p.startswith("/gartner-symposium/free-modernization")),
    ("events", "Event sign-ups", lambda p: p.startswith("/events/")
        or p.rstrip("/") in ("/gartner-symposium", "/github-universe-happy-hour")),
]
REMOVED_FORM_PAGES = ["/", "/about", "/platform"]
LEFT_OUT_PAGES = ("/job-application",)   # job applications aren't sales leads

# Visits from LinkedIn: source linkedin.com, lnkd.in, or a UTM source of linkedin (any capitals).
# Three lines, never added together (agreed 22 Oct 2026): company page = utm_campaign "brand-page",
# Kumar = utm_source "linkedin" with utm_campaign "kumar", untagged = everything else from LinkedIn.
LINKEDIN_SOURCES = r"(?i)^(linkedin\.com|lnkd\.in|linkedin)$"
LINKEDIN_LIKE = r"(?i)linkedin|lnkd"


def linkedin_group(source, campaign):
    if campaign.lower() == "brand-page":
        return "company"
    if source.lower() == "linkedin" and campaign.lower() == "kumar":
        return "kumar"
    return "untagged"
NEW_SITE_LIVE = "2026-09-30"


def stop(msg):
    print(f"\nSTOPPED: {msg}", file=sys.stderr)
    sys.exit(1)


def session():
    raw = os.environ.get("GOOGLE_SA_KEY")
    if raw:
        creds = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    else:
        path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not path or not Path(path).exists():
            stop("No key found. Set GOOGLE_APPLICATION_CREDENTIALS to the key file path.")
        creds = service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    print(f"Signed in as {creds.service_account_email}")
    return AuthorizedSession(creds)


def call(s, method, url, body=None):
    r = s.request(method, url, json=body, timeout=60)
    if r.status_code != 200:
        stop(f"{method} {url} returned {r.status_code}: {r.text[:500]}")
    return r.json()


def clean_path(path):
    """Drop anything after "?", and any part that looks like tracking (a=b&c=d), which can identify
    the person who clicked an email. Agreed 22 Oct 2026: the page is public."""
    path = path.split("?")[0].split("#")[0]
    parts = path.split("/")
    for i, part in enumerate(parts):
        if "=" in part or "&" in part or "@" in part:
            return "/".join(parts[:i]) or "/"
    return path


def page_key(path):
    """https://opsera.ai/x and https://opsera.ai/x/ (or /x and /x/) are one page."""
    stripped = clean_path(path).rstrip("/")
    return stripped if stripped and not stripped.endswith(".ai") else stripped + "/"


# ---------- Search Console ----------

def find_gsc_site(s):
    sites = call(s, "GET", "https://searchconsole.googleapis.com/webmasters/v3/sites").get("siteEntry", [])
    urls = [x["siteUrl"] for x in sites]
    for pref in (f"sc-domain:{GSC_DOMAIN}", f"https://{GSC_DOMAIN}/", f"https://www.{GSC_DOMAIN}/"):
        if pref in urls:
            return pref
    stop(f"The service account can't see an opsera.ai Search Console property. It can see: {urls or 'nothing'}")


def gsc_query(s, site, start, end, dims):
    url = f"https://searchconsole.googleapis.com/webmasters/v3/sites/{quote(site, safe='')}/searchAnalytics/query"
    rows, start_row = [], 0
    while True:
        body = {"startDate": start, "endDate": end, "dimensions": dims, "rowLimit": 25000, "startRow": start_row}
        batch = call(s, "POST", url, body).get("rows", [])
        rows += batch
        if len(batch) < 25000:
            return rows
        start_row += 25000


def gsc_row(r, name):
    return {name: r["keys"][0], "clicks": r["clicks"], "times_shown": r["impressions"],
            "click_rate_pct": round(r["ctr"] * 100, 2), "avg_spot": round(r["position"], 1)}


def merge_slash_variants(rows):
    merged = {}
    for r in rows:
        page = r["keys"][0]
        m = merged.setdefault(page_key(page), {"page": page_key(page), "clicks": 0, "times_shown": 0, "_pos": 0.0, "variants": []})
        m["clicks"] += r["clicks"]
        m["times_shown"] += r["impressions"]
        m["_pos"] += r["position"] * r["impressions"]
        m["variants"].append(page)
    out = []
    for m in merged.values():
        m["avg_spot"] = round(m.pop("_pos") / m["times_shown"], 1) if m["times_shown"] else None
        m["click_rate_pct"] = round(m["clicks"] / m["times_shown"] * 100, 2) if m["times_shown"] else 0
        out.append(m)
    return sorted(out, key=lambda x: -x["clicks"])


def fetch_gsc(s, end):
    site = find_gsc_site(s)
    print(f"Search Console property: {site}")
    daily = [gsc_row(r, "date") for r in gsc_query(s, site, START_DATE, end, ["date"])]
    if not daily:
        stop("Search Console returned no days of data.")
    pages = merge_slash_variants(gsc_query(s, site, START_DATE, end, ["page"]))
    # searches that contain an email address are left out, because the page is public
    searches = [gsc_row(r, "search") for r in gsc_query(s, site, START_DATE, end, ["query"]) if "@" not in r["keys"][0]]
    return {
        "source": f"Google Search Console, {site}",
        "last_day_with_data": daily[-1]["date"],
        "daily": daily, "pages": pages, "searches": searches,
    }


# ---------- Google Analytics 4 ----------

def check_ga_property(s):
    prop = call(s, "GET", f"https://analyticsadmin.googleapis.com/v1beta/properties/{GA_PROPERTY_ID}")
    if prop.get("displayName") != GA_PROPERTY_NAME:
        stop(f"Property {GA_PROPERTY_ID} is called '{prop.get('displayName')}', expected '{GA_PROPERTY_NAME}'.")
    streams = call(s, "GET", f"https://analyticsadmin.googleapis.com/v1beta/properties/{GA_PROPERTY_ID}/dataStreams")
    ids = [x.get("webStreamData", {}).get("measurementId") for x in streams.get("dataStreams", [])]
    if GA_MEASUREMENT_ID not in ids:
        stop(f"Property {GA_PROPERTY_ID} doesn't have measurement ID {GA_MEASUREMENT_ID}. It has: {ids}")
    print(f"Google Analytics property: {GA_PROPERTY_NAME} ({GA_PROPERTY_ID}, {GA_MEASUREMENT_ID})")
    return prop.get("timeZone")


def ga_report(s, end, dims, metrics, event_names=None, start=START_DATE, flt=None):
    rows, offset = [], 0
    while True:
        body = {
            "dateRanges": [{"startDate": start, "endDate": end}],
            "dimensions": [{"name": d} for d in dims],
            "metrics": [{"name": m} for m in metrics],
            "limit": 100000, "offset": offset,
        }
        filters = []
        if event_names:
            filters.append({"filter": {"fieldName": "eventName", "inListFilter": {"values": event_names}}})
        if flt:
            filters.append(flt)
        if filters:
            body["dimensionFilter"] = filters[0] if len(filters) == 1 else {"andGroup": {"expressions": filters}}
        res = call(s, "POST", f"https://analyticsdata.googleapis.com/v1beta/properties/{GA_PROPERTY_ID}:runReport", body)
        for row in res.get("rows", []):
            rec = {d: v["value"] for d, v in zip(dims, row.get("dimensionValues", []))}
            for m, v in zip(metrics, row["metricValues"]):
                rec[m] = float(v["value"]) if "." in v["value"] else int(v["value"])
            if "date" in rec:
                d = rec["date"]
                rec["date"] = f"{d[:4]}-{d[4:6]}-{d[6:]}"
            rows.append(rec)
        offset += 100000
        if offset >= res.get("rowCount", 0):
            return rows


def split_check(label, rows, total):
    parts = sum(r["sessions"] for r in rows)
    share = parts / total if total else 1
    if not GA_SPLIT_MIN_SHARE <= share <= GA_SPLIT_MAX_SHARE:
        stop(f"GA visits by {label} add up to {parts}, but the total is {total}. That's outside Google's usual gap.")
    return parts


def leads(form_rows):
    lines = {key: {"label": label, "count": 0, "pages": {}} for key, label, _ in LEAD_LINES}
    lines["other"] = {"label": "Other forms", "count": 0, "pages": {}}
    daily, left_out = {}, {}
    for r in form_rows:
        page = page_key(r["pagePath"])
        if page.startswith(LEFT_OUT_PAGES):
            left_out[page] = left_out.get(page, 0) + r["eventCount"]
            continue
        key = next((k for k, _, match in LEAD_LINES if match(page)), "other")
        lines[key]["count"] += r["eventCount"]
        lines[key]["pages"][page] = lines[key]["pages"].get(page, 0) + r["eventCount"]
        day = daily.setdefault(r["date"], {k: 0 for k in lines})
        day[key] += r["eventCount"]
    for line in lines.values():
        line["pages"] = [{"page": p, "count": c} for p, c in sorted(line["pages"].items(), key=lambda x: -x[1])]
    removed = sorted({page_key(r["pagePath"]) for r in form_rows if r["date"] >= NEW_SITE_LIVE}
                     & {page_key(p) for p in REMOVED_FORM_PAGES})   # only the new site lost these forms
    if removed:
        stop(f"Pages we thought had no form recorded form fills: {removed}. Check before showing them as removed.")
    return {
        "event": FORM_EVENT,
        "lines": lines,
        "daily": [{"date": d, **v} for d, v in sorted(daily.items())],
        "removed_form_pages": REMOVED_FORM_PAGES,
        "left_out": [{"page": p, "count": c} for p, c in sorted(left_out.items())],
        "new_site_live": NEW_SITE_LIVE,
    }


# Customer journey channels (agreed 22 Oct 2026). A visit can belong to more than one channel
# (an event email is both email and events); channels are only ever shown one at a time.
EVENT_WORDS = ("flutter", "tokenomics", "gartner", "summit", "webinar", "event", "dreamforce", "happy-hour", "happyhour", "flock")
PAID_GROUPS = {"Paid Search", "Paid Social", "Display", "Cross-network", "Paid Other", "Paid Video", "Paid Shopping"}


# Email robots: link checkers that open every link in an email. Found on 8, 22 and 26 Oct 2026 (agreed 28 Oct 2026):
# visits landing on the email subscription pages, from 4 Apple-area cities, or from Safari on a Mac desktop.
# Only the visits in that group that weren't engaged count as robots, so engaged people stay in.
ROBOT_PAGES = "/hs/preferences-center"
ROBOT_CITIES = ["Cupertino", "Palo Alto", "Garner", "Sunnyvale"]


def email_robots(s, end):
    """Visits by day matching any robot sign, each visit once, with how many of them were engaged."""
    exact = lambda field, value: {"filter": {"fieldName": field, "stringFilter": {"matchType": "EXACT", "value": value}}}
    signs = {"orGroup": {"expressions": [
        {"filter": {"fieldName": "landingPage", "stringFilter": {"matchType": "BEGINS_WITH", "value": ROBOT_PAGES}}},
        {"andGroup": {"expressions": [{"filter": {"fieldName": "city", "inListFilter": {"values": ROBOT_CITIES}}}, exact("country", "United States")]}},
        {"andGroup": {"expressions": [exact("browser", "Safari"), exact("operatingSystem", "Macintosh"), exact("deviceCategory", "desktop")]}},
    ]}}
    rows = ga_report(s, end, ["date"], ["sessions", "engagedSessions"], flt=signs)
    return [{"date": r["date"], "visits": r["sessions"], "engaged": r["engagedSessions"], "robots": r["sessions"] - r["engagedSessions"]}
            for r in sorted(rows, key=lambda r: r["date"])]


def journey_channels(group, source, campaign):
    out = {"all"}
    if group == "Organic Search" and source.lower() == "google":
        out.add("search")   # Google only, so it lines up with Search Console
    if re.fullmatch(LINKEDIN_SOURCES[4:], source, re.I):
        out.add("linkedin")
    if group == "Email":
        out.add("email")
    if any(w in campaign.lower() for w in EVENT_WORDS):
        out.add("events")
    if group in PAID_GROUPS:
        out.add("paid")
    if ai_tool(group, source):
        out.add("ai")   # same definition as the AEO tab
    if "youtube" in source.lower() or "youtu.be" in source.lower():
        out.add("youtube")
    if group == "Direct":
        out.add("direct")
    return out


def journey(s, end):
    dims = ["date", "sessionDefaultChannelGroup", "sessionSource", "sessionCampaignName"]
    demo = {"filter": {"fieldName": "pagePath", "inListFilter": {"values": ["/demo", "/demo/"]}}}
    rows = {}
    def add(r, key, value):
        for ch in journey_channels(r["sessionDefaultChannelGroup"], r["sessionSource"], r["sessionCampaignName"]):
            row = rows.setdefault((r["date"], ch), {"date": r["date"], "channel": ch, "visits": 0, "demo_page": 0, "demo_form": 0})
            row[key] += value
    for r in ga_report(s, end, dims, ["sessions"]):
        add(r, "visits", r["sessions"])
    for r in ga_report(s, end, dims, ["sessions"], flt=demo):
        add(r, "demo_page", r["sessions"])
    for r in ga_report(s, end, dims, ["eventCount"], event_names=[FORM_EVENT], flt=demo, start=LEADS_START):
        add(r, "demo_form", r["eventCount"])
    return sorted(rows.values(), key=lambda r: (r["date"], r["channel"]))


# AI tools (agreed 22 Oct 2026): a visit counts for a tool when its source matches; anything else
# Google files under "AI Assistant" counts as "Other AI tools".
AI_TOOLS = [("chatgpt", r"chatgpt|openai"), ("gemini", r"gemini|bard"), ("perplexity", r"perplexity"),
            ("claude", r"claude|anthropic"), ("copilot", r"copilot")]


def ai_tool(group, source):
    for key, pattern in AI_TOOLS:
        if re.search(pattern, source, re.I):
            return key
    return "other" if group == "AI Assistant" else None


def ai_visits(s, end):
    dims = ["date", "sessionDefaultChannelGroup", "sessionSource"]
    demo = {"filter": {"fieldName": "pagePath", "inListFilter": {"values": ["/demo", "/demo/"]}}}
    daily, landing = {}, {}
    def row(date, tool):
        return daily.setdefault((date, tool), {"date": date, "tool": tool, "visits": 0, "engaged": 0, "demo_page": 0, "demo_form": 0})
    for r in ga_report(s, end, dims, ["sessions", "engagedSessions"]):
        t = ai_tool(r["sessionDefaultChannelGroup"], r["sessionSource"])
        if t:
            x = row(r["date"], t); x["visits"] += r["sessions"]; x["engaged"] += r["engagedSessions"]
    for r in ga_report(s, end, dims, ["sessions"], flt=demo):
        t = ai_tool(r["sessionDefaultChannelGroup"], r["sessionSource"])
        if t:
            row(r["date"], t)["demo_page"] += r["sessions"]
    for r in ga_report(s, end, dims, ["eventCount"], event_names=[FORM_EVENT], flt=demo, start=LEADS_START):
        t = ai_tool(r["sessionDefaultChannelGroup"], r["sessionSource"])
        if t:
            row(r["date"], t)["demo_form"] += r["eventCount"]
    sources = {}
    for r in ga_report(s, end, ["landingPage", "sessionDefaultChannelGroup", "sessionSource"], ["sessions", "engagedSessions"]):
        t = ai_tool(r["sessionDefaultChannelGroup"], r["sessionSource"])
        if not t:
            continue
        page = r["landingPage"] if r["landingPage"] == "(not set)" else page_key(r["landingPage"])
        x = landing.setdefault((page, t), {"page": page, "tool": t, "visits": 0, "engaged": 0})
        x["visits"] += r["sessions"]; x["engaged"] += r["engagedSessions"]
        sources.setdefault(f"{r['sessionSource']} ({r['sessionDefaultChannelGroup']})", t)
    return {"daily": sorted(daily.values(), key=lambda r: (r["date"], r["tool"])),
            "landing": sorted(landing.values(), key=lambda r: -r["visits"]),
            "sources": [{"source": k, "tool": v} for k, v in sorted(sources.items())]}


def google_search_visits(s, end):
    """Google organic visits split into first and return visits, to explain why visits can top Search Console clicks."""
    rows = ga_report(s, end, ["newVsReturning"], ["sessions", "engagedSessions"],
                     flt={"andGroup": {"expressions": [
                         {"filter": {"fieldName": "sessionSource", "stringFilter": {"value": "google"}}},
                         {"filter": {"fieldName": "sessionMedium", "stringFilter": {"value": "organic"}}}]}})
    return [{"kind": r["newVsReturning"], "visits": r["sessions"], "engaged": r["engagedSessions"]} for r in rows]


def linkedin_visits(s, end):
    li = {"filter": {"fieldName": "sessionSource", "stringFilter": {"matchType": "FULL_REGEXP", "value": LINKEDIN_SOURCES, "caseSensitive": False}}}
    like = {"filter": {"fieldName": "sessionSource", "stringFilter": {"matchType": "PARTIAL_REGEXP", "value": LINKEDIN_LIKE, "caseSensitive": False}}}
    tag_dims = ["sessionSource", "sessionMedium", "sessionCampaignName"]
    daily = {}
    for r in ga_report(s, end, ["date"] + tag_dims, ["sessions", "engagedSessions"], flt=li):
        g = linkedin_group(r["sessionSource"], r["sessionCampaignName"])
        row = daily.setdefault((r["date"], g), {"date": r["date"], "group": g, "visits": 0, "engaged": 0})
        row["visits"] += r["sessions"]
        row["engaged"] += r["engagedSessions"]
    landing = {}
    for r in ga_report(s, end, ["landingPage"] + tag_dims, ["sessions", "engagedSessions"], flt=li):
        g = linkedin_group(r["sessionSource"], r["sessionCampaignName"])
        page = r["landingPage"] if r["landingPage"] == "(not set)" else page_key(r["landingPage"])
        row = landing.setdefault((page, g), {"page": page, "group": g, "visits": 0, "engaged": 0})
        row["visits"] += r["sessions"]
        row["engaged"] += r["engagedSessions"]
    landing_daily = {}
    for r in ga_report(s, end, ["date", "landingPage"] + tag_dims, ["sessions", "engagedSessions"], flt=li):
        g = linkedin_group(r["sessionSource"], r["sessionCampaignName"])
        page = r["landingPage"] if r["landingPage"] == "(not set)" else page_key(r["landingPage"])
        row = landing_daily.setdefault((r["date"], page, g), {"date": r["date"], "page": page, "group": g, "visits": 0, "engaged": 0})
        row["visits"] += r["sessions"]
        row["engaged"] += r["engagedSessions"]
    tags = [{**{k: r[k] for k in tag_dims}, "content": r["sessionManualAdContent"], "group": linkedin_group(r["sessionSource"], r["sessionCampaignName"]),
             "visits": r["sessions"], "engaged": r["engagedSessions"]}
            for r in ga_report(s, end, tag_dims + ["sessionManualAdContent"], ["sessions", "engagedSessions"], flt=li)]
    forms = {}
    for r in ga_report(s, end, ["date", "pagePath"] + tag_dims, ["eventCount"], event_names=[FORM_EVENT], start=LEADS_START, flt=li):
        page = page_key(r["pagePath"])
        if page.startswith(LEFT_OUT_PAGES):
            continue
        line = next((k for k, _, match in LEAD_LINES if match(page)), "other")
        g = linkedin_group(r["sessionSource"], r["sessionCampaignName"])
        asset = (page + "/").startswith(ASSET_PAGES)   # a report, white paper, ebook or comparison guide download
        row = forms.setdefault((r["date"], g, line, asset), {"date": r["date"], "group": g, "line": line, "asset": asset, "count": 0})
        row["count"] += r["eventCount"]
    # The path homepage -> /demo -> demo form, per visit, for each LinkedIn line
    path = {}
    def step(date, g):
        return path.setdefault((date, g), {"date": date, "group": g, "landed_home": 0, "home_then_demo": 0, "home_demo_form": 0,
                                           "any_demo": 0, "any_demo_form": 0})
    for r in ga_report(s, end, ["date", "landingPage"] + tag_dims, ["sessions"], flt=li):
        if page_key(r["landingPage"]) == "/":
            step(r["date"], linkedin_group(r["sessionSource"], r["sessionCampaignName"]))["landed_home"] += r["sessions"]
    for r in ga_report(s, end, ["date", "landingPage", "pagePath"] + tag_dims, ["sessions"], flt=li):
        if page_key(r["pagePath"]) == "/demo":
            row = step(r["date"], linkedin_group(r["sessionSource"], r["sessionCampaignName"]))
            row["any_demo"] += r["sessions"]
            if page_key(r["landingPage"]) == "/":
                row["home_then_demo"] += r["sessions"]
    for r in ga_report(s, end, ["date", "landingPage", "pagePath"] + tag_dims, ["eventCount"], event_names=[FORM_EVENT], flt=li):
        if page_key(r["pagePath"]) == "/demo":
            row = step(r["date"], linkedin_group(r["sessionSource"], r["sessionCampaignName"]))
            row["any_demo_form"] += r["eventCount"]
            if page_key(r["landingPage"]) == "/":
                row["home_demo_form"] += r["eventCount"]
    for r in path.values():
        if r["home_then_demo"] > r["any_demo"] or r["home_demo_form"] > r["any_demo_form"]:
            stop(f"The LinkedIn demo path doesn't add up on {r['date']} ({r['group']}).")

    counted = {r["sessionSource"] for r in tags}
    look_alikes = sorted({r["sessionSource"] for r in ga_report(s, end, ["sessionSource"], ["sessions"], flt=like)} - counted)
    return {
        "sources_counted": sorted(counted), "look_alikes_not_counted": look_alikes,
        "daily": sorted(daily.values(), key=lambda r: (r["date"], r["group"])),
        "landing": sorted(landing.values(), key=lambda r: -r["visits"]),
        "landing_daily": sorted(landing_daily.values(), key=lambda r: (r["date"], r["page"], r["group"])),
        "demo_path": sorted(path.values(), key=lambda r: (r["date"], r["group"])),
        "tags": sorted(tags, key=lambda r: -r["visits"]),
        "forms": sorted(forms.values(), key=lambda r: (r["date"], r["group"])),
    }


def google_ads(s, end):
    """Google Ads spend, ad clicks, visits and demo requests per campaign per day, from GA4's Google Ads link.
    Always pulled by day: GA4 inflates ad cost and ad clicks when they're asked for by month (checked 28 Oct 2026,
    about 30 times too high), while day, week and whole-period totals agree."""
    rows = {}
    def row(r):
        return rows.setdefault((r["date"], r["sessionGoogleAdsCampaignName"]), {
            "date": r["date"], "campaign": r["sessionGoogleAdsCampaignName"],
            "spend": 0.0, "ad_clicks": 0, "visits": 0, "engaged": 0, "demo_requests": 0})
    dims = ["date", "sessionGoogleAdsCampaignName"]
    for r in ga_report(s, end, dims, ["advertiserAdCost", "advertiserAdClicks", "sessions", "engagedSessions"]):
        if r["sessionGoogleAdsCampaignName"] == "(not set)":
            continue
        x = row(r)
        x["spend"] += r["advertiserAdCost"]; x["ad_clicks"] += r["advertiserAdClicks"]
        x["visits"] += r["sessions"]; x["engaged"] += r["engagedSessions"]
    demo = {"filter": {"fieldName": "pagePath", "inListFilter": {"values": ["/demo", "/demo/"]}}}
    for r in ga_report(s, end, dims, ["eventCount"], event_names=[FORM_EVENT], flt=demo):
        if r["sessionGoogleAdsCampaignName"] != "(not set)":
            row(r)["demo_requests"] += r["eventCount"]
    out = sorted(rows.values(), key=lambda r: (r["date"], r["campaign"]))
    for r in out:
        r["spend"] = round(r["spend"], 2)
    # the check: the daily rows must add up to GA4's own whole-period total
    whole = sum(r["advertiserAdCost"] for r in ga_report(s, end, ["sessionGoogleAdsCampaignName"], ["advertiserAdCost"]))
    if abs(sum(r["spend"] for r in out) - whole) > 1:
        stop(f"Google Ads spend by day ({sum(r['spend'] for r in out):.2f}) doesn't match the whole period ({whole:.2f}).")
    return out


def fetch_ga(s, end):
    tz = check_ga_property(s)
    base = ["sessions", "totalUsers", "engagedSessions"]
    totals = ga_report(s, end, [], base)[0]
    daily = sorted(ga_report(s, end, ["date"], base), key=lambda r: r["date"])
    channels = sorted(ga_report(s, end, ["sessionDefaultChannelGroup"], base + ["averageSessionDuration"]),
                      key=lambda r: -r["sessions"])
    channel_daily = ga_report(s, end, ["date", "sessionDefaultChannelGroup"], ["sessions", "engagedSessions"])
    sources = sorted(ga_report(s, end, ["sessionDefaultChannelGroup", "sessionSource", "sessionMedium"],
                               base + ["averageSessionDuration"]), key=lambda r: -r["sessions"])
    views = {}
    for r in ga_report(s, end, ["pagePath"], ["screenPageViews"]):
        key = page_key(r["pagePath"])
        views[key] = views.get(key, 0) + r["screenPageViews"]
    pages = [{"page": p, "views": v} for p, v in sorted(views.items(), key=lambda x: -x[1])]
    form_rows = ga_report(s, end, ["date", "pagePath"], ["eventCount"], event_names=[FORM_EVENT], start=LEADS_START)

    return {
        "source": f"Google Analytics 4, {GA_PROPERTY_NAME} (property {GA_PROPERTY_ID})",
        "time_zone": tz,
        "totals": totals,
        "split_sums": {"daily": split_check("day", daily, totals["sessions"]),
                       "channels": split_check("source", channels, totals["sessions"])},
        "daily": daily, "channels": channels, "channel_daily": channel_daily,
        "sources": sources, "pages": pages,
        "linkedin": linkedin_visits(s, end),
        "journey": journey(s, end),
        "ai": ai_visits(s, end),
        "google_search_visits": google_search_visits(s, end),
        "email_robots_daily": email_robots(s, end),
        "google_ads_daily": google_ads(s, end),
    }, leads(form_rows)


# ---------- Look up tab: one page or campaign at a time ----------

# Form fills on these pages are downloads of a report, white paper, ebook or comparison guide.
ASSET_PAGES = ("/resources/report/", "/resources/white-papers/", "/resources/ebooks/", "/resources/comparison-guides/")
NOT_CAMPAIGNS = {"(direct)", "(organic)", "(referral)", "(not set)", "(none)", ""}


# Left out of the public page (agreed 28 Oct 2026): target-account campaigns, sales outreach codes ("ET-...") and spam sites
LEFT_OUT_CAMPAIGNS = re.compile(r"\b(abm|abx|microsite)\b|^(\d+-)?ET-|^[a-z0-9-]+\.[a-z]{2,}$", re.I)


def not_campaign(name):
    """Google's own placeholders, such as "(organic)", aren't campaigns. Names with "@" are left out (the page is public),
    and so are the campaigns in LEFT_OUT_CAMPAIGNS."""
    return name in NOT_CAMPAIGNS or (name.startswith("(") and name.endswith(")")) or "@" in name or bool(LEFT_OUT_CAMPAIGNS.search(name))


def live_title(path):
    """The <title> of a page on opsera.ai as it loads today, or None."""
    import html
    import requests
    try:
        r = requests.get(f"https://opsera.ai{path}", headers={"User-Agent": "Mozilla/5.0 (opsera-analytics-dashboard)"}, timeout=15)
    except requests.RequestException:
        return None
    m = re.search(r"<title[^>]*>(.*?)</title>", r.text, re.S | re.I) if r.status_code == 200 else None
    return " ".join(html.unescape(m.group(1)).split()) if m else None


def fix_titles(pages, titles):
    """Google Analytics sometimes gives a page the homepage's title, or none. For those pages, use the title
    the live page shows (agreed 28 Oct 2026). A page that really shows the homepage, or is gone, keeps Google's."""
    home = {titles[pages.index("/")]} if "/" in pages else set()
    home.add(live_title("/") or "")
    fixed = 0
    for i, (path, title) in enumerate(zip(pages, titles)):
        if path == "/" or not re.fullmatch(r"(/[a-z0-9-]+)+", path) or (title and title not in home and title != "(not set)"):
            continue
        live = live_title(path)
        if live and live not in home and not live.lower().startswith("page not found"):
            titles[i] = live
            fixed += 1
    print(f"Page titles taken from the live page: {fixed}")
    return titles


# The product pages in the site's own menu (checked 28 Oct 2026), plus the homepage
KEY_PAGES = [("/", "Homepage"), ("/software-factory", "Product"), ("/forge", "Product"), ("/forge/modernization", "Product"),
             ("/unified-insights", "Product"), ("/agents", "Product"), ("/agentic-devops", "Product"),
             ("/salesforce-devops", "Product"), ("/brickforge", "Product")]
TOP_CONTENT = 20


def rankings(s, end, gsc_site):
    """Average Google spot week by week for the key pages and the top 20 blogs and resources, with each page's
    top searches. Blogs and resources are picked by visits (landing page) since the new site went live."""
    def is_content(p):
        parts = p.strip("/").split("/")
        return (parts[0] == "blog" and len(parts) >= 2) or (parts[0] == "resources" and len(parts) >= 3)
    visits = {}
    for r in ga_report(s, end, ["landingPage"], ["sessions"], start=NEW_SITE_LIVE):
        p = page_key(r["landingPage"])
        if is_content(p):
            visits[p] = visits.get(p, 0) + r["sessions"]
    top = sorted(visits, key=lambda p: -visits[p])[:TOP_CONTENT]
    pages = KEY_PAGES + [(p, "Blog" if p.startswith("/blog/") else "Resource") for p in top]
    keys = {p for p, _ in pages}

    weekly = {}
    last = START_DATE
    for r in gsc_query(s, gsc_site, START_DATE, end, ["date", "page"]):
        p = page_key(urlparse(r["keys"][1]).path or "/")
        if p not in keys:
            continue
        d = dt.date.fromisoformat(r["keys"][0])
        last = max(last, r["keys"][0])
        wk = (d - dt.timedelta(days=d.weekday())).isoformat()
        w = weekly.setdefault((p, wk), [0, 0, 0.0])
        w[0] += r["clicks"]; w[1] += r["impressions"]; w[2] += r["position"] * r["impressions"]
    q_start = (dt.date.fromisoformat(end) - dt.timedelta(days=89)).isoformat()
    searches = {}
    for r in gsc_query(s, gsc_site, q_start, end, ["page", "query"]):
        p = page_key(urlparse(r["keys"][0]).path or "/")
        if p in keys:
            x = searches.setdefault(p, {}).setdefault(r["keys"][1], [0, 0, 0.0])
            x[0] += r["clicks"]; x[1] += r["impressions"]; x[2] += r["position"] * r["impressions"]
    titles = {}
    for r in ga_report(s, end, ["pagePath", "pageTitle"], ["screenPageViews"], start=NEW_SITE_LIVE):
        p = page_key(r["pagePath"])
        if p in keys and r["screenPageViews"] > titles.get(p, ("", -1))[1]:
            titles[p] = (r["pageTitle"], r["screenPageViews"])
    order = [p for p, _ in pages]
    fixed = fix_titles(order, [titles.get(p, ("", 0))[0] for p in order])
    titles = {p: (t, 0) for p, t in zip(order, fixed)}
    out = []
    for p, group in pages:
        weeks = [{"week": wk, "clicks": c, "times_shown": n, "avg_spot": round(pos / n, 1)}
                 for (pp, wk), (c, n, pos) in sorted(weekly.items()) if pp == p and n]
        top_q = sorted(searches.get(p, {}).items(), key=lambda kv: (-kv[1][0], -kv[1][1]))[:10]
        out.append({"page": p, "group": group, "title": titles.get(p, ("", 0))[0], "visits_since_new_site": visits.get(p),
                    "weeks": weeks,
                    "searches": [{"search": q, "clicks": c, "times_shown": n, "avg_spot": round(pos / n, 1)} for q, (c, n, pos) in top_q if n]})
    return {"pages": out, "last_day_with_data": last, "searches_from": q_start, "new_site_live": NEW_SITE_LIVE}


def lookup(s, end, gsc_site):
    """Daily numbers by page and by campaign, packed small (the tab loads them only when opened).
    Each row starts with the day number counted from START_DATE. Sources are never added together."""
    start = dt.date.fromisoformat(START_DATE)
    day = lambda d: (dt.date.fromisoformat(d) - start).days
    index = lambda table, key: table.setdefault(key, len(table))
    pages, channels, campaigns, sources = {}, {}, {}, {}

    def page_of(path):
        return path if path == "(not set)" else page_key(path)

    visits = {}
    for r in ga_report(s, end, ["date", "landingPage", "sessionDefaultChannelGroup"], ["sessions", "engagedSessions"]):
        k = (day(r["date"]), index(pages, page_of(r["landingPage"])), index(channels, r["sessionDefaultChannelGroup"]))
        v = visits.setdefault(k, [0, 0])
        v[0] += r["sessions"]; v[1] += r["engagedSessions"]
    camp_visits = {}
    for r in ga_report(s, end, ["date", "sessionCampaignName", "sessionSource", "sessionMedium"], ["sessions", "engagedSessions"]):
        name = r["sessionCampaignName"]
        if not_campaign(name):
            continue
        k = (day(r["date"]), index(campaigns, name), index(sources, f"{r['sessionSource']} / {r['sessionMedium']}"))
        v = camp_visits.setdefault(k, [0, 0])
        v[0] += r["sessions"]; v[1] += r["engagedSessions"]
    # visits that landed on a page from a campaign, so "All matches" can count each visit once
    both = {}
    for r in ga_report(s, end, ["date", "landingPage", "sessionCampaignName"], ["sessions", "engagedSessions"]):
        if not_campaign(r["sessionCampaignName"]):
            continue
        k = (day(r["date"]), index(pages, page_of(r["landingPage"])), index(campaigns, r["sessionCampaignName"]))
        v = both.setdefault(k, [0, 0])
        v[0] += r["sessions"]; v[1] += r["engagedSessions"]
    forms = {}
    for r in ga_report(s, end, ["date", "pagePath", "sessionCampaignName"], ["eventCount"], event_names=[FORM_EVENT], start=LEADS_START):
        page = page_key(r["pagePath"])
        if page.startswith(LEFT_OUT_PAGES):
            continue   # job applications aren't sales leads, the same as the Leads tab
        name = r["sessionCampaignName"]
        camp = -1 if not_campaign(name) else index(campaigns, name)
        k = (day(r["date"]), index(pages, page), camp)
        forms[k] = forms.get(k, 0) + r["eventCount"]
    gsc = {}
    for r in gsc_query(s, gsc_site, START_DATE, end, ["date", "page"]):
        k = (day(r["keys"][0]), index(pages, page_key(urlparse(r["keys"][1]).path or "/")))
        v = gsc.setdefault(k, [0, 0])
        v[0] += r["clicks"]; v[1] += r["impressions"]
    best = {}
    for r in ga_report(s, end, ["pagePath", "pageTitle"], ["screenPageViews"]):
        key = page_key(r["pagePath"])
        if key in pages and r["screenPageViews"] > best.get(key, ("", -1))[1]:
            best[key] = (r["pageTitle"], r["screenPageViews"])
    order = lambda t: [k for k, _ in sorted(t.items(), key=lambda x: x[1])]
    return {
        "source": f"Google Analytics 4, {GA_PROPERTY_NAME}, and Google Search Console, {gsc_site}",
        "pages": order(pages), "titles": fix_titles(order(pages), [best.get(p, ("", 0))[0] for p in order(pages)]),
        "channels": order(channels), "campaigns": order(campaigns), "sources": order(sources),
        "asset_pages": list(ASSET_PAGES),
        "visits": [[*k, *v] for k, v in sorted(visits.items())],
        "campaign_visits": [[*k, *v] for k, v in sorted(camp_visits.items())],
        "page_campaign_visits": [[*k, *v] for k, v in sorted(both.items())],
        "forms": [[*k, v] for k, v in sorted(forms.items())],
        "gsc": [[*k, *v] for k, v in sorted(gsc.items())],
    }


def write(name, payload, meta, compact=False):
    DATA_DIR.mkdir(exist_ok=True)
    (DATA_DIR / name).write_text(json.dumps({**meta, **payload}, **({"separators": (",", ":")} if compact else {"indent": 1})))


def main():
    end = (dt.datetime.now(IST).date() - dt.timedelta(days=1)).isoformat()
    s = session()
    meta = {"start_date": START_DATE, "end_date": end,
            "pulled_at": dt.datetime.now(IST).isoformat(timespec="minutes")}
    gsc = fetch_gsc(s, end)
    ga, lead_data = fetch_ga(s, end)
    write("search_console.json", gsc, meta)
    write("analytics.json", ga, meta)
    write("leads.json", {"source": f"{ga['source']}, form event {FORM_EVENT}", "time_zone": ga["time_zone"], **lead_data},
          {**meta, "start_date": LEADS_START})
    write("rankings.json", {"source": f"Google Search Console, {gsc['source'].split(', ', 1)[1]}, and Google Analytics 4, {GA_PROPERTY_NAME}",
                            **rankings(s, end, gsc["source"].split(", ", 1)[1])}, meta)
    look = lookup(s, end, gsc["source"].split(", ", 1)[1])
    write("lookup.json", {**look, "gsc_last_day": gsc["last_day_with_data"]}, meta, compact=True)

    print(f"\nRange asked for: {START_DATE} to {end}")
    print(f"Search Console: last day with data {gsc['last_day_with_data']}, "
          f"clicks {sum(r['clicks'] for r in gsc['daily'])}, {len(gsc['pages'])} pages, {len(gsc['searches'])} searches")
    t = ga["totals"]
    print(f"Google Analytics: visits {t['sessions']} (days add up to {ga['split_sums']['daily']}), people {t['totalUsers']}")
    print("Leads: " + ", ".join(f"{l['label']} {l['count']}" for l in lead_data["lines"].values()))


if __name__ == "__main__":
    main()
