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
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

API = "https://api.hubapi.com"
START_DATE = "2026-09-01"
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
EVENT_WORDS = ("event", "webinar", "summit", "flutter", "gartner", "tokenomics", "dreamforce")
CONTACT_PROPS = ["createdate", "hs_object_source", "hs_analytics_source", "hs_analytics_source_data_1", "hs_analytics_source_data_2",
                 "hs_analytics_first_referrer", "utm_source", "utm_source_fc", "utm_source_rc", "luma_referrer"]


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


def main():
    s = session()
    end = (dt.datetime.now(PACIFIC).date() - dt.timedelta(days=1)).isoformat()

    # Marketing contacts: created by a website form since 1 Sep
    forms = search(s, "contacts", [{"propertyName": "createdate", "operator": "GTE", "value": SINCE},
                                   {"propertyName": "hs_object_source", "operator": "EQ", "value": "FORM"}], CONTACT_PROPS)
    contacts = {}
    for c in forms:
        p = c["properties"]
        contacts[c["id"]] = {"line": "form", "date": pacific_day(p["createdate"]), "channel": channel(p), "linkedin_fields": linkedin_fields(p)}

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
                                             "linkedin_fields": linkedin_fields(p)}

    # Meetings linked to a marketing contact, dated by when the meeting takes place
    meetings = search(s, "meetings", [{"propertyName": "hs_meeting_start_time", "operator": "GTE", "value": SINCE}], ["hs_meeting_start_time"])
    m_contacts = associations(s, "meetings", "contacts", [m["id"] for m in meetings])
    meeting_rows = []
    for m in meetings:
        linked = [contacts[c] for c in m_contacts.get(m["id"], []) if c in contacts]
        if linked:
            first = min(linked, key=lambda x: x["date"])
            meeting_rows.append({"date": pacific_day(m["properties"]["hs_meeting_start_time"]), "channel": first["channel"], "line": first["line"]})

    # Deals linked to a marketing contact, dated by when the deal was created
    c_deals = associations(s, "contacts", "deals", contacts.keys())
    deal_ids = {d for ds in c_deals.values() for d in ds}
    deal_rows = []
    if deal_ids:
        ids = list(deal_ids)
        stages = {st["id"]: (p["label"], st["label"], st["metadata"].get("isClosed") == "true", float(st["metadata"].get("probability") or 0))
                  for p in call(s, "GET", "/crm/v3/pipelines/deals")["results"] for st in p["stages"]}
        for i in range(0, len(ids), 100):
            j = call(s, "POST", "/crm/v3/objects/deals/batch/read", json={"inputs": [{"id": x} for x in ids[i:i + 100]],
                                                                          "properties": ["createdate", "amount", "dealstage", "pipeline"]})
            for d in j.get("results", []):
                p = d["properties"]
                owners = [contacts[c] for c, ds in c_deals.items() if d["id"] in ds]
                first = min(owners, key=lambda x: x["date"])
                pipeline, stage, closed, prob = stages.get(p.get("dealstage"), ("Unknown", "Unknown", False, 0))
                deal_rows.append({"date": pacific_day(p["createdate"]), "channel": first["channel"], "line": first["line"],
                                  "amount": float(p.get("amount") or 0), "pipeline": pipeline, "stage": stage,
                                  "won": closed and prob >= 1, "lost": closed and prob == 0, "created_before_contact": pacific_day(p["createdate"]) < first["date"]})

    daily = collections.Counter((c["date"], c["line"], c["channel"]) for c in contacts.values())
    out = {
        "source": "HubSpot", "start_date": START_DATE, "end_date": end,
        "pulled_at": dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).isoformat(timespec="minutes"),
        "contacts_daily": [{"date": d, "line": l, "channel": ch, "count": n} for (d, l, ch), n in sorted(daily.items())],
        "linkedin_fields": collections.Counter(f for c in contacts.values() for f in c["linkedin_fields"]).most_common(),
        "linkedin_contacts": sum(1 for c in contacts.values() if c["channel"] == "linkedin"),
        "meetings_daily": [{"date": d, "line": l, "channel": ch, "count": n}
                           for (d, l, ch), n in sorted(collections.Counter((m["date"], m["line"], m["channel"]) for m in meeting_rows).items())],
        "meetings_all_calendar": len(meetings),
        "deals": sorted(deal_rows, key=lambda d: d["date"]),
        "events": events,
    }
    OUT.write_text(json.dumps(out, indent=1))
    by = lambda rows, key: dict(collections.Counter(r[key] for r in rows))
    print(f"HubSpot {START_DATE} to {end}: form contacts {sum(1 for c in contacts.values() if c['line'] == 'form')}, "
          f"Luma-import contacts {sum(1 for c in contacts.values() if c['line'] == 'luma')}")
    print("  contacts by channel:", by(contacts.values(), "channel"))
    print("  LinkedIn fields matched:", out["linkedin_fields"])
    print(f"  meetings with a marketing contact: {len(meeting_rows)} of {len(meetings)} calendar meetings; by channel {by(meeting_rows, 'channel')}")
    print(f"  deals linked to a marketing contact: {len(deal_rows)}, amount {sum(d['amount'] for d in deal_rows):,.0f}; by channel {by(deal_rows, 'channel')}")
    print("  events:", [(e["label"], e["members"]) for e in events])


if __name__ == "__main__":
    main()
