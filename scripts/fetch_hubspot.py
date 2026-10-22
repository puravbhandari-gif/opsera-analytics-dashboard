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
AI_TOOLS = [("chatgpt", r"chatgpt|openai"), ("gemini", r"gemini|bard"), ("perplexity", r"perplexity"),
            ("claude", r"claude|anthropic"), ("copilot", r"copilot")]   # same as scripts/fetch_data.py
EVENT_WORDS = ("event", "webinar", "summit", "flutter", "gartner", "tokenomics", "dreamforce")
CONTACT_PROPS = ["createdate", "hs_object_source", "hs_analytics_source", "hs_analytics_source_data_1", "hs_analytics_source_data_2",
                 "hs_analytics_first_referrer", "utm_source", "utm_source_fc", "utm_source_rc", "luma_referrer",
                 "first_conversion_event_name", "recent_conversion_event_name"]


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


def summarise_deals(deal_rows):
    """The page is public, so deals are only kept as daily totals; no single customer's deal is listed."""
    daily = collections.defaultdict(lambda: {"count": 0, "amount": 0.0})
    for d in deal_rows:
        if d["counts"] == "marketing":
            row = daily[(d["date"], d["channel"], d["line"], d.get("demo", False))]
            row["count"] += 1
            row["amount"] += d["amount"]
    existing = [d for d in deal_rows if d["counts"] == "existing"]
    return {
        "deals_daily": [{"date": k[0], "channel": k[1], "line": k[2], "demo": k[3], **v} for k, v in sorted(daily.items())],
        "deals_by_stage": collections.Counter(d["stage"] for d in deal_rows if d["counts"] == "marketing").most_common(),
        "existing_deals": {"count": len(existing), "amount": round(sum(d["amount"] for d in existing), 2)},
    }


def ai_tool(p):
    text = f"{p.get('hs_analytics_source_data_1') or ''} {p.get('hs_analytics_first_referrer') or ''}"
    for key, pattern in AI_TOOLS:
        if re.search(pattern, text, re.I):
            return key
    return "other" if p.get("hs_analytics_source") == "AI_REFERRALS" else None


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
                             "tool": ai_tool(p)}

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
                                             "linkedin_fields": linkedin_fields(p), "demo": False, "first_form": "(Luma import)"}

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
                                                                          "properties": ["createdate", "amount", "dealstage", "pipeline"]})
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
                                  "won": closed and prob >= 1, "lost": closed and prob == 0})

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

    daily = collections.Counter((c["date"], c["line"], c["channel"], c["demo"]) for c in contacts.values())
    out = {
        "source": "HubSpot", "start_date": START_DATE, "end_date": end,
        "pulled_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).isoformat(timespec="minutes"),
        "contacts_daily": [{"date": d, "line": l, "channel": ch, "demo": dm, "count": n} for (d, l, ch, dm), n in sorted(daily.items())],
        "ai_contacts_daily": [{"date": d, "tool": tl, "demo": dm, "count": n} for (d, tl, dm), n in sorted(collections.Counter(
            (c["date"], c["tool"], c["demo"]) for c in contacts.values() if c.get("tool")).items())],
        "ai_deals_daily": [{"date": d, "tool": tl, "count": n, "amount": a} for (d, tl), (n, a) in sorted({
            (x["date"], x["tool"]): (sum(1 for y in deal_rows if y["counts"] == "marketing" and y.get("tool") == x["tool"] and y["date"] == x["date"]),
                                     sum(y["amount"] for y in deal_rows if y["counts"] == "marketing" and y.get("tool") == x["tool"] and y["date"] == x["date"]))
            for x in deal_rows if x["counts"] == "marketing" and x.get("tool")}.items())],
        "first_forms": collections.Counter(c["first_form"] for c in contacts.values() if c["line"] == "form").most_common(30),
        "existing_customers": len(existing),
        "job_applicants_left_out": job_applicants,
        "linkedin_fields": collections.Counter(f for c in contacts.values() for f in c["linkedin_fields"]).most_common(),
        "linkedin_contacts": sum(1 for c in contacts.values() if c["channel"] == "linkedin"),
        "meetings_daily": [{"date": d, "line": l, "channel": ch, "kind": k, "demo": dm, "count": n}
                           for (d, l, ch, k, dm), n in sorted(collections.Counter((m["date"], m["line"], m["channel"], m["kind"], m["demo"]) for m in meeting_rows).items())],
        "meetings_all_calendar": len(meetings),
        **summarise_deals(deal_rows),
        "events": events,
        "campaigns": campaigns,
        "campaigns_checked": len(all_campaigns),
    }
    OUT.write_text(json.dumps(out, indent=1))
    by = lambda rows, key: dict(collections.Counter(r[key] for r in rows))
    print(f"HubSpot {START_DATE} to {end}: form contacts {sum(1 for c in contacts.values() if c['line'] == 'form')}, "
          f"Luma-import contacts {sum(1 for c in contacts.values() if c['line'] == 'luma')}, existing customers among them {len(existing)}")
    print("  contacts by channel:", by(contacts.values(), "channel"))
    print("  LinkedIn fields matched:", out["linkedin_fields"])
    print(f"  meetings linked to marketing contacts: {len(meeting_rows)} of {len(meetings)}; by kind {by(meeting_rows, 'kind')}")
    print(f"  deals: marketing {sum(1 for d in deal_rows if d['counts'] == 'marketing')} "
          f"(${sum(d['amount'] for d in deal_rows if d['counts'] == 'marketing'):,.0f}), existing {sum(1 for d in deal_rows if d['counts'] == 'existing')}")
    print("  events:", [(e["label"], e["members"]) for e in events])
    print("  campaigns:", campaigns)
    print("  first forms of form contacts:", out["first_forms"][:12])
    print(f"  demo-form contacts: {sum(1 for c in contacts.values() if c['demo'])}")
    print("  AI-tool contacts:", dict(collections.Counter(c["tool"] for c in contacts.values() if c.get("tool"))))


if __name__ == "__main__":
    main()
