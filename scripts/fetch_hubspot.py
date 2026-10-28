"""Pull marketing contacts, the meetings and deals linked to them, and event sign-up lists
from HubSpot into data/hubspot.json. Counts and dates only: no names, emails or companies.
Read-only. Needs the HUBSPOT_TOKEN env var (a GitHub secret, a HubSpot Service Key).

Agreed with Purav on 22 Oct 2026:
- Contacts = contacts created by a website form since 1 Sep. Contacts from the Salesforce sync,
  Warmly, the Claude connector, Reo, Clay and other imports are left out.
- Event sign-ups imported from Luma are their own line, never added to form contacts.
- A contact is LinkedIn if any of these say so, counted once: HubSpot's Original Source is LinkedIn,
  its UTM source is linkedin / Kumar link / opseralinkedin / opserasocial, or Luma says LinkedIn.
- Meetings = calendar meetings linked to one of those marketing contacts.
- Event lists are each their own line: Flutter guests (Luma import), Flutter attendees,
  Tokenomics (may overlap with the website event form) and Gartner booth scans (not sign-ups).
"""
import collections
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

API = "https://api.hubapi.com"
START_DATE = "2026-04-01"   # from 1 Apr, so "Last 3 months" can compare with the 3 months before
SINCE = f"{START_DATE}T00:00:00Z"
OUT = Path(__file__).resolve().parent.parent / "data" / "hubspot.json"
PACIFIC = ZoneInfo("America/Los_Angeles")   # same days as Google Analytics
LINKEDIN_UTM = {"linkedin", "kumar link", "opseralinkedin", "opserasocial"}
EVENT_LISTS = [   # (key, line label, exact HubSpot list name, note)
    ("flutter_guests", "Flutter 2026: signed up (Luma import)", "Opsera Flutter 2026_ The AI-SDLC Summit - Guests - 2026-09-02-20-27-29.csv", ""),
    ("flutter_attended", "Flutter 2026: attended", "Flutter 2026 Attendees", ""),
    ("tokenomics", "Tokenomics webinar", "DG-FY27-Q3-Tokenomics-Webinar", "May overlap with the website event form"),
    ("gartner_scans", "Gartner booth scans", "Gartner IT Symposium 2026 booth scans", "Booth scans, not sign-ups"),
]
# One row per event for the Events tab (agreed 28 Oct 2026). Lists are matched by their exact HubSpot name; each
# 2026 webinar and roundtable list is filled by that event's own form. Dates are the event's last day, from the live
# event page or the GTM calendar; None means the date isn't known, so meetings afterwards aren't counted.
# (key, name, kind, first day, last day, sign-up lists, attended lists, event pages, note)
EVENT_ROWS = [
    ("appsec_agents", "Meet the Opsera AppSec agents", "Webinar", "2026-04-08", "2026-04-08",
     ["Meet the Agents workshop registrants"], [], ["/events/meet-the-opsera-appsec-agents-for-ai-builders"], ""),
    ("ai_benchmark", "AI benchmark report", "Webinar", None, None, ["AI BM Report Webinar Registrants"], [], [], "Event date not known"),
    ("ai_adoption", "Copilot, Cursor, Claude Code: what 250k developers revealed", "Webinar", "2026-04-29", "2026-04-29",
     ["DG-FY27-Q1-AI-Adoption-Webinar"], [], ["/events/copilot-cursor-claude-code-what-250k-developers-revealed"],
     "Sign-ups include people who asked for the recording"),
    # The AI budget webinar on 25 Jun was the online Gartner Magic Quadrant roundtable (confirmed by Purav, 28 Oct 2026)
    ("mq_roundtable", "AI budget burning: Gartner Magic Quadrant roundtable", "Webinar", "2026-06-25", "2026-06-25",
     ["DG-FY27-Q2-MQ-Roundtable"], [],
     ["/events/ai-budget-burning-how-to-convert-ai-panic-into-tangible-business-results",
      "/events/ai-budget-burning-how-to-convert-ai-spend-into-tangible-business-results"], "Online executive roundtable"),
    ("tokenomics", "Tokenomics: the currency of enterprise AI", "Webinar", "2026-09-15", "2026-09-15",
     ["DG-FY27-Q3-Tokenomics-Webinar"], [], ["/events/tokenomics-the-currency-of-enterprise-ai"], "Sign-ups may overlap with the event page form"),
    ("flutter", "Flutter 2026: the AI-SDLC Summit", "Event", "2026-10-01", "2026-10-01",
     ["Opsera Flutter 2026_ The AI-SDLC Summit - Guests - 2026-09-02-20-27-29.csv"], ["Flutter 2026 Attendees"], ["/flutter-2026-ai-sdlc-summit"],
     "Sign-ups are the Luma guest list"),
    ("gartner", "Gartner IT Symposium/Xpo, Orlando", "Event", "2026-10-19", "2026-10-22",
     [], ["Gartner IT Symposium 2026 booth scans"], ["/gartner-symposium", "/events/gartner-summit-2026"], "Attended means booth scans"),
    ("github_universe", "GitHub Universe", "Event", "2026-10-28", "2026-10-29", [], [],
     ["/events/github-universe", "/github-universe-happy-hour"], "No HubSpot list yet"),
]
AI_TOOLS = [("chatgpt", r"chatgpt|openai"), ("gemini", r"gemini|bard"), ("perplexity", r"perplexity"),
            ("claude", r"claude|anthropic"), ("copilot", r"copilot")]   # same as scripts/fetch_data.py
EVENT_WORDS = ("event", "webinar", "summit", "flutter", "gartner", "tokenomics", "dreamforce")
CONTACT_PROPS = ["createdate", "hs_object_source", "hs_analytics_source", "hs_analytics_source_data_1", "hs_analytics_source_data_2",
                 "hs_analytics_first_referrer", "utm_source", "utm_source_fc", "utm_source_rc", "luma_referrer",
                 "first_conversion_event_name", "recent_conversion_event_name", "hs_analytics_first_url",
                 "utm_campaign_fc", "hs_analytics_first_touch_converting_campaign"]

# How each deal came in (agreed 27 Oct 2026): one line per marketing deal, open or won, with no company,
# person or job title. HubSpot has no product field, so the product comes from words in the deal name;
# only the product is kept, never the name. Checked in order; a deal can name more than 1 product.
PRODUCTS = [(r"sfdc|salesforce|agentforce|agentforge", "Salesforce DevOps"), (r"brickforge", "BrickForge"),
            (r"(?<!brick)(?<!agent)forge", "Forge"), (r"unified insights|dora", "Unified Insights"),
            (r"copilot", "Copilot"), (r"platform|sdlc", "Platform"), (r"\bagents?\b", "Agents"), (r"pipeline", "Pipelines")]
SOURCE_NAMES = {"ORGANIC_SEARCH": "Search engines", "DIRECT_TRAFFIC": "Direct", "PAID_SEARCH": "Paid search", "PAID_SOCIAL": "Paid social",
                "SOCIAL_MEDIA": "Social media", "EMAIL_MARKETING": "Email", "REFERRALS": "Other websites", "AI_REFERRALS": "AI tools",
                "OTHER_CAMPAIGNS": "Other campaigns", "OFFLINE": "Offline (import, event or sales tool)"}


def first_came_from(p):
    """Where the person first came from, in plain words."""
    src = p.get("hs_analytics_source") or ""
    detail = f"{p.get('hs_analytics_source_data_1') or ''} {p.get('hs_analytics_first_referrer') or ''}".lower()
    if linkedin_fields(p):
        return "LinkedIn"
    if src == "ORGANIC_SEARCH" and "google" in detail:
        return "Google search"
    if src == "AI_REFERRALS":
        return f"AI tools ({ai_tool(p)})" if ai_tool(p) not in (None, "other") else "AI tools"
    return SOURCE_NAMES.get(src, "Not recorded")


def first_page(url):
    """The first page as an opsera.ai address, cut at "?" (no tracking codes)."""
    if not url:
        return "Not recorded"
    u = urlparse(url)
    path = (u.path.split("@")[0].rstrip("/") or "/")
    return path if u.netloc in ("opsera.ai", "www.opsera.ai") else f"{u.netloc}{path}"


def products_in(name):
    found = [label for pattern, label in PRODUCTS if re.search(pattern, (name or "").lower())]
    if "Salesforce DevOps" in found and "Pipelines" in found:
        found.remove("Pipelines")   # Salesforce pipelines are part of Salesforce DevOps
    return ", ".join(dict.fromkeys(found)) or "Not named in the deal"


def stop(msg):
    print(f"\nSTOPPED: {msg}", file=sys.stderr)
    sys.exit(1)


def session():
    token = os.environ.get("HUBSPOT_TOKEN")
    if not token:
        stop("The HUBSPOT_TOKEN secret is missing.")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    return s


def call(s, method, path, partial_ok=False, **kw):
    r = s.request(method, API + path, timeout=60, **kw)
    if r.status_code == 207 and partial_ok:
        j = r.json()   # some records simply have no associations; anything else is a real problem
        bad = [e for e in j.get("errors", []) if e.get("subCategory") != "crm.associations.NO_ASSOCIATIONS_FOUND"]
        if bad:
            stop(f"HubSpot {method} {path} returned errors: {str(bad[:2])[:300]}")
        return j
    if r.status_code != 200:
        stop(f"HubSpot {method} {path} returned {r.status_code}: {r.text[:300]}")
    return r.json()


EMAIL_ADDRESS = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def marketing_emails(s, since):
    """Marketing emails sent since `since`, with HubSpot's own send, open and click counts (for Look up).
    Only the email's name and subject are kept, never who it went to. Optional: a problem here is reported
    in the file instead of stopping the whole HubSpot update (added 28 Oct 2026)."""
    rows, after = [], None
    while True:
        r = s.get(f"{API}/marketing/v3/emails", params={"limit": 100, "includeStats": "true", **({"after": after} if after else {})}, timeout=60)
        if r.status_code != 200:
            return {"error": f"HubSpot marketing emails returned {r.status_code}: {r.text[:200]}", "rows": []}
        j = r.json()
        for e in j.get("results", []):
            sent_on = (e.get("publishDate") or "")[:10]
            counters = (e.get("stats") or {}).get("counters") or {}
            if not sent_on or sent_on < since or not counters.get("sent"):
                continue   # drafts and emails never sent have no numbers
            name, subject = e.get("name") or "", e.get("subject") or ""
            if EMAIL_ADDRESS.search(name) or EMAIL_ADDRESS.search(subject):
                continue   # never publish an email address
            delivered = counters.get("delivered") or counters.get("sent")
            rows.append({"sent_on": sent_on, "name": name, "subject": subject, "kind": e.get("type") or "", "campaign_id": e.get("campaign") or "",
                         "sends": counters.get("sent", 0), "opens": counters.get("open", 0), "clicks": counters.get("click", 0),
                         "open_rate_pct": round(counters.get("open", 0) / delivered * 100, 1) if delivered else None,
                         "click_rate_pct": round(counters.get("click", 0) / delivered * 100, 1) if delivered else None})
        after = (j.get("paging") or {}).get("next", {}).get("after")
        if not after:
            return {"error": None, "rows": sorted(rows, key=lambda x: x["sent_on"])}


# Privacy for Look up (agreed 28 Oct 2026). Internal email and list names often hold staff first names and
# target companies, so they're stored only as scrambled word codes for matching. Emails show their subject
# line (what recipients saw); lists show only a plain label and the number of people. Target-account
# emails and lists, and HubSpot's automatic lists, are left out entirely, so a company name can't be probed.
TARGET_ACCOUNTS = re.compile(r"\b(abm|abx|microsite)\b", re.I)
LEFT_OUT_CAMPAIGN = re.compile(r"^(\d+-)?ET-|^[a-z0-9-]+\.[a-z]{2,}$", re.I)   # sales outreach codes and spam sites (agreed 28 Oct 2026)
AUTOMATIC_LISTS = re.compile(r"^\s*(\[abm\]|abm\b|abx\b|\[email\]|\[workflows\]|\[ads\]|target\b)", re.I)


def word_index(text):
    """Words as short scrambled codes (FNV-1a, 32 bits): Look up can match a word without the file holding the text."""
    out = []
    for w in dict.fromkeys(re.findall(r"[a-z0-9]+", (text or "").lower())):
        if len(w) < 3:
            continue
        h = 0x811C9DC5
        for b in w.encode():
            h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
        out.append(f"{h:08x}")
    return out


def public_emails(found):
    if found["error"]:
        return found
    rows = [{k: v for k, v in e.items() if k not in ("name", "campaign_id")} | {"words": word_index(f"{e['name']} {e['subject']}")}
            for e in found["rows"] if not TARGET_ACCOUNTS.search(e["name"]) and not e["subject"].startswith("Built for ")]
    return {"error": None, "left_out_target_accounts": len(found["rows"]) - len(rows), "rows": rows}


def public_lists(found, since):
    if found["error"]:
        return found
    rows = [{"people": l["people"], "kind": l["kind"], "updated_on": l["updated_on"], "words": word_index(l["name"])}
            for l in found["rows"] if not AUTOMATIC_LISTS.search(l["name"]) and l["updated_on"] >= since]
    return {"error": None, "rows": sorted(rows, key=lambda x: -(x["people"] or 0))}


def all_lists(s):
    """Every HubSpot list's name and how many people are on it (for Look up). No members are read."""
    rows, offset = [], 0
    while True:
        r = s.post(f"{API}/crm/v3/lists/search", json={"query": "", "count": 500, "offset": offset, "additionalProperties": ["hs_list_size"]}, timeout=60)
        if r.status_code != 200:
            return {"error": f"HubSpot lists returned {r.status_code}: {r.text[:200]}", "rows": []}
        j = r.json()
        for l in j.get("lists", []):
            name = l.get("name") or ""
            if EMAIL_ADDRESS.search(name):
                continue
            size = (l.get("additionalProperties") or {}).get("hs_list_size")
            rows.append({"name": name, "people": int(size) if size not in (None, "") else None,
                         "kind": {"DYNAMIC": "Active", "MANUAL": "Static", "SNAPSHOT": "Static"}.get(l.get("processingType"), l.get("processingType") or ""),
                         "updated_on": (l.get("updatedAt") or "")[:10]})
        if not j.get("hasMore"):
            return {"error": None, "rows": sorted(rows, key=lambda x: x["name"].lower())}
        offset = j.get("offset", offset + 500)


def search(s, obj, filters, props):
    rows, after = [], None
    while True:
        body = {"filterGroups": [{"filters": filters}], "properties": props, "limit": 200, "sorts": [{"propertyName": "hs_object_id", "direction": "ASCENDING"}]}
        if after:
            body["after"] = after
        j = call(s, "POST", f"/crm/v3/objects/{obj}/search", json=body)
        rows += j.get("results", [])
        after = (j.get("paging") or {}).get("next", {}).get("after")
        if not after:
            return rows
        if len(rows) >= 9800:
            stop(f"More than 9,800 {obj} match; HubSpot search can't page further. Split the date range.")


def associations(s, frm, to, ids):
    out = collections.defaultdict(set)
    ids = list(ids)
    for i in range(0, len(ids), 100):
        j = call(s, "POST", f"/crm/v4/associations/{frm}/{to}/batch/read", partial_ok=True, json={"inputs": [{"id": str(x)} for x in ids[i:i + 100]]})
        for r in j.get("results", []):
            for t in r.get("to", []):
                out[str(r["from"]["id"])].add(str(t["toObjectId"]))
    return out


def pacific_day(stamp):
    return dt.datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(PACIFIC).date().isoformat()


def linkedin_fields(p):
    hits = []
    if (p.get("hs_analytics_source") == "SOCIAL_MEDIA" and (p.get("hs_analytics_source_data_1") or "").lower() == "linkedin"):
        hits.append("Original Source: LinkedIn")
    for f in ("utm_source", "utm_source_fc", "utm_source_rc"):
        v = (p.get(f) or "").strip()
        if v.lower() in LINKEDIN_UTM:
            hits.append(f"UTM source: {v}")
    if (p.get("luma_referrer") or "").lower() == "linkedin":
        hits.append("Luma: LinkedIn")
    return sorted(set(hits))


def channel(p):
    if linkedin_fields(p):
        return "linkedin"
    src = p.get("hs_analytics_source") or ""
    detail = f"{p.get('hs_analytics_source_data_1') or ''} {p.get('hs_analytics_first_referrer') or ''}".lower()
    if "youtube" in detail or "youtu.be" in detail:
        return "youtube"
    return {"ORGANIC_SEARCH": "search", "EMAIL_MARKETING": "email", "PAID_SEARCH": "paid", "PAID_SOCIAL": "paid",
            "AI_REFERRALS": "ai", "DIRECT_TRAFFIC": "direct",
            "OTHER_CAMPAIGNS": "events" if any(w in detail for w in EVENT_WORDS) else "other"}.get(src, "other")


def ai_tool(p):
    text = f"{p.get('hs_analytics_source_data_1') or ''} {p.get('hs_analytics_first_referrer') or ''}"
    for key, pattern in AI_TOOLS:
        if re.search(pattern, text, re.I):
            return key
    return "other" if p.get("hs_analytics_source") == "AI_REFERRALS" else None


def add_months(d, n):
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    last = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1)).day
    return dt.date(y, m, min(d.day, last))


# All pipeline (agreed 28 Oct 2026): every open and won deal created since 1 Apr, worked backwards from its contacts.
# Sourced: a contact on the deal was first brought in by a HubSpot campaign (First Touch Converting Campaign) or a
# marketing form, before the deal was created. Influenced: not sourced, but a contact touched a campaign before the
# deal was created (marketing email click, form fill, event list, visit from a campaign link). Sales only: neither.
# "Meetings Link" booking forms and job applications don't count as marketing forms.
PIPELINE_PROPS = ["createdate", "hs_object_source", "hs_analytics_first_touch_converting_campaign", "hs_analytics_last_touch_converting_campaign",
                  "first_conversion_date", "first_conversion_event_name", "recent_conversion_date", "recent_conversion_event_name",
                  "hs_email_first_click_date", "utm_campaign_fc", "hs_analytics_first_timestamp"]
NOT_MARKETING_FORM = re.compile(r"^meetings link|job application", re.I)


def ms(stamp):
    """HubSpot dates come as ISO text or epoch milliseconds; both become epoch milliseconds."""
    if not stamp:
        return None
    if str(stamp).isdigit():
        return int(stamp)
    return int(dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).timestamp() * 1000)


def all_pipeline(s, campaign_names, event_joins):
    deals = search(s, "deals", [{"propertyName": "createdate", "operator": "GTE", "value": SINCE}],
                   ["createdate", "amount", "dealstage", "pipeline"])
    stages = {st["id"]: (pl["label"], st["label"], st["metadata"].get("isClosed") == "true", float(st["metadata"].get("probability") or 0))
              for pl in call(s, "GET", "/crm/v3/pipelines/deals")["results"] for st in pl["stages"]}
    keep = []
    for d in deals:
        pipeline, stage, closed, prob = stages.get(d["properties"].get("dealstage"), ("Unknown", "Unknown", False, 0))
        if closed and prob == 0:
            continue   # closed lost isn't pipeline
        keep.append((d, pipeline, stage, closed and prob >= 1))
    d_contacts = associations(s, "deals", "contacts", [d["id"] for d, *_ in keep])
    ids = sorted({c for cs in d_contacts.values() for c in cs})
    people = {}
    for i in range(0, len(ids), 100):
        j = call(s, "POST", "/crm/v3/objects/contacts/batch/read", json={"inputs": [{"id": x} for x in ids[i:i + 100]], "properties": PIPELINE_PROPS})
        for c in j.get("results", []):
            people[c["id"]] = c["properties"]
    name = lambda guid: campaign_names.get(guid or "", "") or ("Unnamed HubSpot campaign" if guid else "")
    public = lambda n: "Target-account campaign" if TARGET_ACCOUNTS.search(n) else "Sales outreach" if LEFT_OUT_CAMPAIGN.search(n) else n
    rows = []
    for d, pipeline, stage, won in keep:
        created = ms(d["properties"]["createdate"])
        bucket, campaign = "Sales only", ""
        for c in sorted(d_contacts.get(d["id"], [])):
            p = people.get(c, {})
            if (ms(p.get("createdate")) or created) > created:
                continue
            form = p.get("first_conversion_event_name") or ""
            if p.get("hs_analytics_first_touch_converting_campaign"):
                bucket, campaign = "Marketing sourced", name(p["hs_analytics_first_touch_converting_campaign"])
                break
            if p.get("hs_object_source") == "FORM" and form and not NOT_MARKETING_FORM.search(form) and (ms(p.get("first_conversion_date")) or created + 1) <= created:
                bucket, campaign = "Marketing sourced", "Form: " + form.split(" — ")[0].split(" - Opsera")[0].strip()
                break
        if bucket == "Sales only":
            for c in sorted(d_contacts.get(d["id"], [])):
                p = people.get(c, {})
                touch = None
                if p.get("hs_analytics_last_touch_converting_campaign") and (ms(p.get("createdate")) or created + 1) <= created:
                    touch = name(p["hs_analytics_last_touch_converting_campaign"])
                elif p.get("utm_campaign_fc") and (ms(p.get("hs_analytics_first_timestamp")) or created + 1) <= created:
                    touch = re.sub(r"^\d+-", "", p["utm_campaign_fc"])
                elif any(at <= created for lst, at in event_joins.get(c, [])):
                    touch = next(lst for lst, at in sorted(event_joins[c], key=lambda x: x[1]) if at <= created)
                elif (ms(p.get("hs_email_first_click_date")) or created + 1) <= created:
                    touch = "Marketing email click"
                else:
                    for k in ("first", "recent"):
                        f = p.get(f"{k}_conversion_event_name") or ""
                        if f and not NOT_MARKETING_FORM.search(f) and (ms(p.get(f"{k}_conversion_date")) or created + 1) <= created:
                            touch = "Form: " + f.split(" — ")[0].split(" - Opsera")[0].strip()
                            break
                if touch:
                    bucket, campaign = "Marketing influenced", touch
                    break
        rows.append({"date": pacific_day(d["properties"]["createdate"]), "bucket": bucket, "campaign": public(campaign) if campaign else "",
                     "status": "Won" if won else "Open", "stage": stage, "pipeline": pipeline,
                     "amount": round(float(d["properties"].get("amount") or 0)), "contacts": len(d_contacts.get(d["id"], []))})
    return sorted(rows, key=lambda r: r["date"])


def summarise_deals(deal_rows, end):
    """The page is public, so marketing deals are kept only as totals per week, per month and per 3 months
    (agreed 22 Oct 2026). Closed Lost deals are left out; open and won are kept apart."""
    kept = [d for d in deal_rows if d["counts"] == "marketing" and not d["lost"]]
    end_d, start_d = dt.date.fromisoformat(end), dt.date.fromisoformat(START_DATE)
    weeks, months, quarters = [], [], []
    w = start_d - dt.timedelta(days=start_d.weekday())
    while w <= end_d:
        weeks.append((w, min(w + dt.timedelta(6), end_d))); w += dt.timedelta(7)
    m = start_d.replace(day=1)
    while m <= end_d:
        nxt = add_months(m, 1)
        months.append((m, min(nxt - dt.timedelta(1), end_d))); m = nxt
    q_end = end_d
    for _ in range(2):   # the last 3 months, and the 3 months before
        q_start = add_months(q_end, -3) + dt.timedelta(1)
        if q_start >= start_d:
            quarters.append((q_start, q_end))
        q_end = q_start - dt.timedelta(1)

    def totals(periods):
        out = []
        for a, b in periods:
            groups = collections.defaultdict(lambda: {"open_count": 0, "open_amount": 0.0, "won_count": 0, "won_amount": 0.0})
            for d in kept:
                if a.isoformat() <= d["date"] <= b.isoformat():
                    g = groups[(d["channel"], d.get("demo", False), d.get("tool"))]
                    k = "won" if d["won"] else "open"
                    g[f"{k}_count"] += 1
                    g[f"{k}_amount"] += d["amount"]
            out += [{"start": a.isoformat(), "end": b.isoformat(), "channel": ch, "demo": dm, "tool": tl, **v} for (ch, dm, tl), v in groups.items()]
        return out

    lost = [d for d in deal_rows if d["counts"] == "marketing" and d["lost"]]
    existing = [d for d in deal_rows if d["counts"] == "existing"]
    return {
        "deals_weekly": totals(weeks), "deals_monthly": totals(months), "deals_quarters": totals(quarters),
        "deals_total": {k: sum(d["amount"] if "amount" in k else 1 for d in kept if (d["won"] == k.startswith("won")))
                        for k in ("open_count", "open_amount", "won_count", "won_amount")},
        "deals_lost": {"count": len(lost)},
        "deals_by_stage": collections.Counter(d["stage"] for d in kept).most_common(),
        "existing_deals": {"count": len(existing), "amount": round(sum(d["amount"] for d in existing), 2)},
    }


def main():
    s = session()
    end = (dt.datetime.now(PACIFIC).date() - dt.timedelta(days=1)).isoformat()

    # Marketing contacts: created by a website form since 1 Sep
    forms = search(s, "contacts", [{"propertyName": "createdate", "operator": "GTE", "value": SINCE},
                                   {"propertyName": "hs_object_source", "operator": "EQ", "value": "FORM"}], CONTACT_PROPS)
    contacts, job_applicants = {}, 0
    for c in forms:
        p = c["properties"]
        if "job application" in (p.get("first_conversion_event_name") or "").lower():
            job_applicants += 1   # people applying for jobs aren't marketing contacts, same as the Leads tab
            continue
        contacts[c["id"]] = {"line": "form", "date": pacific_day(p["createdate"]), "channel": channel(p), "linkedin_fields": linkedin_fields(p),
                             "demo": "demo" in (p.get("first_conversion_event_name") or "").lower(), "first_form": p.get("first_conversion_event_name") or "(none)",
                             "tool": ai_tool(p), "came_from": first_came_from(p), "first_page": first_page(p.get("hs_analytics_first_url")),
                             "first_form_short": (p.get("first_conversion_event_name") or "Not recorded").split(" — ")[0].split(" - Opsera")[0].strip(),
                             "campaign": p.get("utm_campaign_fc") or "", "campaign_id": p.get("hs_analytics_first_touch_converting_campaign") or ""}

    # Event lists, each its own line. Luma-imported guests also count as marketing contacts (line "luma").
    found = {l["name"]: l for l in call(s, "POST", "/crm/v3/lists/search", json={"query": "", "count": 500}).get("lists", [])}
    for _, _, name, _ in EVENT_LISTS:
        if name not in found:
            hit = call(s, "POST", "/crm/v3/lists/search", json={"query": name[:40], "count": 50}).get("lists", [])
            found.update({l["name"]: l for l in hit})
    events = []
    for key, label, name, note in EVENT_LISTS:
        lst = found.get(name)
        if not lst:
            stop(f"Can't find the HubSpot list \"{name}\". Check whether it was renamed.")
        members, after = [], None
        while True:
            j = call(s, "GET", f"/crm/v3/lists/{lst['listId']}/memberships/join-order", params={"limit": 250, **({"after": after} if after else {})})
            members += j.get("results", [])
            after = (j.get("paging") or {}).get("next", {}).get("after")
            if not after:
                break
        joined = collections.Counter(pacific_day(m["membershipTimestamp"]) for m in members if m.get("membershipTimestamp"))
        events.append({"key": key, "label": label, "list": name, "note": note, "members": len(members),
                       "joined_daily": [{"date": d, "count": n} for d, n in sorted(joined.items())]})
        if key == "flutter_guests":
            ids = [str(m["recordId"]) for m in members]
            for i in range(0, len(ids), 100):
                j = call(s, "POST", "/crm/v3/objects/contacts/batch/read", json={"inputs": [{"id": x} for x in ids[i:i + 100]], "properties": CONTACT_PROPS})
                for c in j.get("results", []):
                    if c["id"] not in contacts:
                        p = c["properties"]
                        joined_on = next((pacific_day(m["membershipTimestamp"]) for m in members if str(m["recordId"]) == c["id"] and m.get("membershipTimestamp")),
                                         pacific_day(p["createdate"]))
                        contacts[c["id"]] = {"line": "luma", "date": joined_on, "channel": "linkedin" if linkedin_fields(p) else "events",
                                             "linkedin_fields": linkedin_fields(p), "demo": False, "first_form": "(Luma import)",
                                             "came_from": first_came_from(p), "first_page": first_page(p.get("hs_analytics_first_url")),
                                             "first_form_short": "Luma event sign-up"}

    # Deals linked to a marketing contact. Only deals created on or after the day the person became a
    # marketing contact count as pipeline; older deals mark the person as an existing customer (agreed 22 Oct 2026).
    c_deals = associations(s, "contacts", "deals", contacts.keys())
    deal_ids = {d for ds in c_deals.values() for d in ds}
    deal_rows, existing = [], set()
    if deal_ids:
        ids = list(deal_ids)
        stages = {st["id"]: (pl["label"], st["label"], st["metadata"].get("isClosed") == "true", float(st["metadata"].get("probability") or 0))
                  for pl in call(s, "GET", "/crm/v3/pipelines/deals")["results"] for st in pl["stages"]}
        for i in range(0, len(ids), 100):
            j = call(s, "POST", "/crm/v3/objects/deals/batch/read", json={"inputs": [{"id": x} for x in ids[i:i + 100]],
                                                                          "properties": ["createdate", "amount", "dealstage", "pipeline", "dealname"]})
            for d in j.get("results", []):
                p = d["properties"]
                owner_ids = [c for c, ds in c_deals.items() if d["id"] in ds]
                first_id = min(owner_ids, key=lambda c: contacts[c]["date"])
                first = contacts[first_id]
                created = pacific_day(p["createdate"])
                if created < first["date"]:
                    existing.update(owner_ids)
                pipeline, stage, closed, prob = stages.get(p.get("dealstage"), ("Unknown", "Unknown", False, 0))
                deal_rows.append({"date": created, "channel": first["channel"], "line": first["line"], "demo": first["demo"], "tool": first.get("tool"),
                                  "counts": "marketing" if created >= first["date"] else "existing",
                                  "amount": float(p.get("amount") or 0), "pipeline": pipeline, "stage": stage,
                                  "won": closed and prob >= 1, "lost": closed and prob == 0,
                                  "came_from": first["came_from"], "first_page": first["first_page"], "first_form": first["first_form_short"],
                                  "product": products_in(p.get("dealname")),   # the deal name itself is never kept
                                  "campaign": first.get("campaign", ""), "campaign_id": first.get("campaign_id", "")})

    # Meetings linked to a marketing contact, dated by when they take place. Each meeting is put in one line:
    # after sign-up (counted), upcoming, existing customer, or before sign-up. Only the first is a meeting booked.
    meetings = search(s, "meetings", [{"propertyName": "hs_meeting_start_time", "operator": "GTE", "value": SINCE}], ["hs_meeting_start_time"])
    m_contacts = associations(s, "meetings", "contacts", [m["id"] for m in meetings])
    meeting_rows = []
    for m in meetings:
        linked = [c for c in m_contacts.get(m["id"], []) if c in contacts]
        if not linked:
            continue
        first_id = min(linked, key=lambda c: contacts[c]["date"])
        first = contacts[first_id]
        day = pacific_day(m["properties"]["hs_meeting_start_time"])
        if any(c in existing for c in linked):
            kind = "existing_customer"
        elif day < first["date"]:
            kind = "before_signup"
        elif day > end:
            kind = "upcoming"
        else:
            kind = "booked"
        meeting_rows.append({"date": day, "channel": first["channel"], "line": first["line"], "kind": kind, "demo": first["demo"]})

    # Events tab: people on each event's lists, and calendar meetings with them after the event's last day
    def members_of(name):
        lst = found.get(name)
        if not lst:
            hit = call(s, "POST", "/crm/v3/lists/search", json={"query": name[:40], "count": 50}).get("lists", [])
            found.update({l["name"]: l for l in hit})
            lst = found.get(name)
        if not lst:
            stop(f"Can't find the HubSpot list \"{name}\". Check whether it was renamed.")
        ids, after = set(), None
        while True:
            j = call(s, "GET", f"/crm/v3/lists/{lst['listId']}/memberships/join-order", params={"limit": 250, **({"after": after} if after else {})})
            ids |= {str(m["recordId"]) for m in j.get("results", [])}
            after = (j.get("paging") or {}).get("next", {}).get("after")
            if not after:
                return ids
    meeting_day = {m["id"]: pacific_day(m["properties"]["hs_meeting_start_time"]) for m in meetings}
    event_rows = []
    for key, name, kind, first_day, last_day, signup_lists, attended_lists, pages, note in EVENT_ROWS:
        signed = set().union(*[members_of(n) for n in signup_lists]) if signup_lists else None
        attended = set().union(*[members_of(n) for n in attended_lists]) if attended_lists else None
        people = (signed or set()) | (attended or set())
        row = {"key": key, "name": name, "kind": kind, "first_day": first_day, "last_day": last_day, "pages": pages, "note": note,
               "signed_up": None if signed is None else len(signed), "attended": None if attended is None else len(attended),
               "meetings_after": None, "people_with_meeting": None, "meetings_upcoming": None}
        if people and last_day:
            after_ids = [m for m, cs in m_contacts.items() if meeting_day.get(m, "") > last_day and people & set(cs)]
            done = [m for m in after_ids if meeting_day[m] <= end]
            row["meetings_after"] = len(done)
            row["meetings_upcoming"] = len(after_ids) - len(done)
            row["people_with_meeting"] = len({c for m in done for c in m_contacts[m] if c in people})
        event_rows.append(row)

    # HubSpot campaigns named after the events, and how many contacts each is tagged with
    campaigns, all_campaigns, after = [], [], None
    while True:
        r = s.get(f"{API}/marketing/v3/campaigns", params={"limit": 100, "properties": "hs_name,hs_start_date,hs_end_date", **({"after": after} if after else {})}, timeout=60)
        if r.status_code != 200:
            break
        all_campaigns += r.json().get("results", [])
        after = (r.json().get("paging") or {}).get("next", {}).get("after")
        if not after:
            break
    if r.status_code == 200:
        guests = {c for c, v in contacts.items() if v["line"] == "luma"}
        for c in all_campaigns:
            name = (c.get("properties") or {}).get("hs_name") or ""
            if not any(w in name.lower() for w in ("flutter", "tokenomics", "gartner", "luma")):
                continue
            row = {"name": name, "start": (c.get("properties") or {}).get("hs_start_date")}
            for kind in ("contactFirstTouch", "influencedContacts"):
                ids, after = set(), None
                while True:
                    rr = s.get(f"{API}/marketing/v3/campaigns/{c['id']}/reports/contacts/{kind}", params={"limit": 100, **({"after": after} if after else {})}, timeout=60)
                    if rr.status_code != 200:
                        ids = None
                        break
                    jj = rr.json()
                    ids |= {str(x.get("id")) for x in jj.get("results", [])}
                    after = (jj.get("paging") or {}).get("next", {}).get("after")
                    if not after:
                        break
                row[kind] = None if ids is None else len(ids)
                row[f"{kind}_also_flutter_guests"] = None if ids is None else len(ids & guests)
            campaigns.append(row)
    else:
        campaigns = f"{r.status_code}: {r.text[:200]}"

    # Campaigns tab: each email's HubSpot campaign, and the campaign each marketing deal's person first came in on
    # (their first link tag in HubSpot, else HubSpot's first-touch campaign). Target-account campaigns are left out.
    campaign_names = {c["id"]: (c.get("properties") or {}).get("hs_name") or "" for c in all_campaigns}
    public = lambda n: n if n and not TARGET_ACCOUNTS.search(n) and not LEFT_OUT_CAMPAIGN.search(n) else ""
    emails = marketing_emails(s, START_DATE)
    for e in emails["rows"]:
        e["campaign"] = public(campaign_names.get(e["campaign_id"], ""))
    # All pipeline: when each contact joined each event list (sign-ups, attendees, booth scans)
    event_joins = collections.defaultdict(list)
    for _key, ename, _kind, _first, _last, signup_lists, attended_lists, _pages, _note in EVENT_ROWS:
        for lname in signup_lists + attended_lists:
            lst = found.get(lname)
            if not lst:
                continue
            after = None
            while True:
                j = call(s, "GET", f"/crm/v3/lists/{lst['listId']}/memberships/join-order", params={"limit": 250, **({"after": after} if after else {})})
                for m in j.get("results", []):
                    event_joins[str(m["recordId"])].append((ename, ms(m.get("membershipTimestamp")) or 0))
                after = (j.get("paging") or {}).get("next", {}).get("after")
                if not after:
                    break
    pipeline_rows = all_pipeline(s, campaign_names, event_joins)
    campaign_deals = [{"date": d["date"], "campaign": public(d["campaign"] or campaign_names.get(d["campaign_id"], "")),
                       "status": "Won" if d["won"] else "Open", "amount": round(d["amount"])}
                      for d in sorted(deal_rows, key=lambda d: d["date"]) if d["counts"] == "marketing" and not d["lost"]]

    daily = collections.Counter((c["date"], c["line"], c["channel"], c["demo"]) for c in contacts.values())
    out = {
        "source": "HubSpot", "start_date": START_DATE, "end_date": end,
        "pulled_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).isoformat(timespec="minutes"),
        "contacts_daily": [{"date": d, "line": l, "channel": ch, "demo": dm, "count": n} for (d, l, ch, dm), n in sorted(daily.items())],
        "ai_contacts_daily": [{"date": d, "tool": tl, "demo": dm, "count": n} for (d, tl, dm), n in sorted(collections.Counter(
            (c["date"], c["tool"], c["demo"]) for c in contacts.values() if c.get("tool")).items())],
        "first_forms": collections.Counter(c["first_form"] for c in contacts.values() if c["line"] == "form").most_common(30),
        "existing_customers": len(existing),
        "job_applicants_left_out": job_applicants,
        "linkedin_fields": collections.Counter(f for c in contacts.values() for f in c["linkedin_fields"]).most_common(),
        "linkedin_contacts": sum(1 for c in contacts.values() if c["channel"] == "linkedin"),
        "meetings_daily": [{"date": d, "line": l, "channel": ch, "kind": k, "demo": dm, "count": n}
                           for (d, l, ch, k, dm), n in sorted(collections.Counter((m["date"], m["line"], m["channel"], m["kind"], m["demo"]) for m in meeting_rows).items())],
        "meetings_all_calendar": len(meetings),
        **summarise_deals(deal_rows, end),
        "deal_lines": [{"month": d["date"][:7], "amount": round(d["amount"]), "status": "Won" if d["won"] else "Open", "stage": d["stage"],
                        "came_from": d["came_from"], "first_page": d["first_page"], "first_form": d["first_form"], "product": d["product"]}
                       for d in sorted(deal_rows, key=lambda d: d["date"]) if d["counts"] == "marketing" and not d["lost"]],
        "events": events,
        "event_rows": event_rows,
        "campaigns": campaigns,
        "campaigns_checked": len(all_campaigns),
        "emails": public_emails(emails),
        "campaign_deals": campaign_deals,
        "all_pipeline": pipeline_rows,
        "lists": public_lists(all_lists(s), START_DATE),
    }
    OUT.write_text(json.dumps(out, indent=1))
    by = lambda rows, key: dict(collections.Counter(r[key] for r in rows))
    print(f"HubSpot {START_DATE} to {end}: form contacts {sum(1 for c in contacts.values() if c['line'] == 'form')}, "
          f"Luma-import contacts {sum(1 for c in contacts.values() if c['line'] == 'luma')}, existing customers among them {len(existing)}")
    print("  contacts by channel:", by(contacts.values(), "channel"))
    print("  LinkedIn fields matched:", out["linkedin_fields"])
    print(f"  meetings linked to marketing contacts: {len(meeting_rows)} of {len(meetings)}; by kind {by(meeting_rows, 'kind')}")
    for key in ("emails", "lists"):
        print(f"  {key}: {len(out[key]['rows'])}" + (f" (problem: {out[key]['error']})" if out[key]["error"] else ""))
    print("  deal lines:", [(d["month"], d["came_from"], d["product"]) for d in out["deal_lines"]])
    t = out["deals_total"]
    print(f"  deals: open {t['open_count']} (${t['open_amount']:,.0f}), won {t['won_count']} (${t['won_amount']:,.0f}), "
          f"closed lost left out {out['deals_lost']['count']}, existing {out['existing_deals']['count']}")
    print("  events:", [(e["label"], e["members"]) for e in events])
    print("  event rows:", [(e["key"], e["signed_up"], e["attended"], e["meetings_after"], e["meetings_upcoming"], e["people_with_meeting"]) for e in event_rows])
    print("  all pipeline:", dict(collections.Counter(r["bucket"] for r in pipeline_rows)), "deals,",
          {b: sum(r["amount"] for r in pipeline_rows if r["bucket"] == b) for b in ("Marketing sourced", "Marketing influenced", "Sales only")},
          "| no contact on deal:", sum(1 for r in pipeline_rows if not r["contacts"]))
    print("  campaign deals:", [(d["date"], d["campaign"], d["status"]) for d in campaign_deals])
    print("  emails with a campaign:", sum(1 for e in emails["rows"] if e.get("campaign")), "of", len(emails["rows"]))
    print("  campaigns:", campaigns)
    print("  first forms of form contacts:", out["first_forms"][:12])
    print(f"  demo-form contacts: {sum(1 for c in contacts.values() if c['demo'])}")
    print("  AI-tool contacts:", dict(collections.Counter(c["tool"] for c in contacts.values() if c.get("tool"))))


if __name__ == "__main__":
    main()
