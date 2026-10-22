"""Check what the HUBSPOT_TOKEN can read, and summarise the fields the journey needs.
Writes counts only (no names, emails or other personal details) to hubspot_check.json.
Run by the "HubSpot check" workflow, which never changes the live page.

    HUBSPOT_TOKEN=... python3 scripts/hubspot_check.py
"""
import collections
import json
import os
import sys
from urllib.parse import parse_qs, urlparse

import requests

API = "https://api.hubapi.com"
SINCE = "2026-09-01T00:00:00Z"
OUT = "hubspot_check.json"
SOURCE_HINTS = ("source", "utm", "campaign", "referrer", "first_url", "channel", "lead")


def session():
    token = os.environ.get("HUBSPOT_TOKEN")
    if not token:
        sys.exit("STOPPED: HUBSPOT_TOKEN is missing.")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {token}"
    return s


def call(s, method, path, **kw):
    r = s.request(method, API + path, timeout=60, **kw)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else r.text[:300])


def search_all(s, obj, props, filters, cap=10000):
    rows, after = [], None
    while True:
        body = {"filterGroups": [{"filters": filters}], "properties": props, "limit": 200}
        if after:
            body["after"] = after
        code, j = call(s, "POST", f"/crm/v3/objects/{obj}/search", json=body)
        if code != 200:
            return code, j, rows
        rows += j.get("results", [])
        after = (j.get("paging") or {}).get("next", {}).get("after")
        if not after or len(rows) >= cap:
            return 200, None, rows


def top(counter, n=40):
    return [{"value": k, "count": v} for k, v in counter.most_common(n)]


def main():
    s = session()
    out = {"since": SINCE, "access": {}}

    # What each part of HubSpot lets this key read
    for name, path in [("contacts", "/crm/v3/objects/contacts?limit=1"), ("deals", "/crm/v3/objects/deals?limit=1"),
                       ("meetings", "/crm/v3/objects/meetings?limit=1"), ("contact properties", "/crm/v3/properties/contacts"),
                       ("deal properties", "/crm/v3/properties/deals"), ("deal pipelines", "/crm/v3/pipelines/deals"),
                       ("lists", "/crm/v3/lists/search")]:
        code, j = call(s, "POST" if name == "lists" else "GET", path, **({"json": {"query": "", "count": 1}} if name == "lists" else {}))
        out["access"][name] = code if code == 200 else f"{code}: {str(j)[:200]}"

    # Contact fields that look like they hold a source
    code, props = call(s, "GET", "/crm/v3/properties/contacts")
    candidates = []
    if code == 200:
        for p in props["results"]:
            if any(h in p["name"].lower() or h in (p.get("label") or "").lower() for h in SOURCE_HINTS):
                candidates.append({"name": p["name"], "label": p.get("label"), "type": p.get("type"),
                                   "options": [o["value"] for o in p.get("options", [])][:40]})
    out["source_fields"] = candidates

    # Contacts created since 1 Sep: how the source fields are filled in
    names = [c["name"] for c in candidates][:60] + ["createdate", "lifecyclestage"]
    code, err, contacts = search_all(s, "contacts", names, [{"propertyName": "createdate", "operator": "GTE", "value": SINCE}])
    out["contacts"] = {"status": code if code == 200 else f"{code}: {str(err)[:200]}", "count": len(contacts)}
    values = {n: collections.Counter() for n in names}
    utm = collections.Counter()
    for c in contacts:
        for n in names:
            v = (c["properties"].get(n) or "").strip()
            if v and n not in ("createdate",):
                values[n][v if len(v) < 80 else v[:80]] += 1
        for n in ("hs_analytics_first_url", "hs_analytics_last_url"):
            u = c["properties"].get(n)
            if u:
                for src in parse_qs(urlparse(u).query).get("utm_source", []):
                    utm[f"{n}: utm_source={src}"] += 1
    out["contact_values"] = {n: top(v) for n, v in values.items() if v and n not in ("hs_analytics_first_url", "hs_analytics_last_url", "hs_analytics_first_referrer", "hs_analytics_last_referrer")}
    out["utm_sources_in_first_and_last_url"] = top(utm)
    out["referrer_hosts"] = top(collections.Counter(urlparse(c["properties"].get("hs_analytics_first_referrer") or "").netloc
                                                    for c in contacts if c["properties"].get("hs_analytics_first_referrer")))

    # Deals created since 1 Sep: counts and amounts by pipeline and stage
    code, err, deals = search_all(s, "deals", ["amount", "dealstage", "pipeline", "createdate", "hs_analytics_source", "hs_analytics_source_data_1", "dealtype"],
                                  [{"propertyName": "createdate", "operator": "GTE", "value": SINCE}])
    out["deals"] = {"status": code if code == 200 else f"{code}: {str(err)[:200]}", "count": len(deals),
                    "with_amount": sum(1 for d in deals if d["properties"].get("amount")),
                    "amount_total": round(sum(float(d["properties"].get("amount") or 0) for d in deals), 2),
                    "by_stage": top(collections.Counter(f"{d['properties'].get('pipeline')} / {d['properties'].get('dealstage')}" for d in deals)),
                    "by_source": top(collections.Counter(f"{d['properties'].get('hs_analytics_source')} / {d['properties'].get('hs_analytics_source_data_1')}" for d in deals))}

    # Meetings created since 1 Sep, if this key can read them
    code, err, meetings = search_all(s, "meetings", ["hs_meeting_start_time", "hs_meeting_outcome", "hs_createdate", "hs_meeting_source"],
                                     [{"propertyName": "hs_createdate", "operator": "GTE", "value": SINCE}])
    out["meetings"] = {"status": code if code == 200 else f"{code}: {str(err)[:200]}", "count": len(meetings),
                       "by_outcome": top(collections.Counter(m["properties"].get("hs_meeting_outcome") for m in meetings)),
                       "by_source": top(collections.Counter(m["properties"].get("hs_meeting_source") for m in meetings))}

    # Lists that look like event or Luma sign-ups
    code, j = call(s, "POST", "/crm/v3/lists/search", json={"query": "", "count": 500, "additionalProperties": ["hs_list_size"]})
    if code == 200:
        out["event_lists"] = [{"name": l.get("name"), "size": (l.get("additionalProperties") or {}).get("hs_list_size"),
                               "type": l.get("processingType"), "created": l.get("createdAt")}
                              for l in j.get("lists", []) if any(k in (l.get("name") or "").lower() for k in ("luma", "event", "flutter", "gartner", "webinar", "tokenomics", "happy hour"))]
    else:
        out["event_lists"] = f"{code}: {str(j)[:200]}"

    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps({k: out[k] for k in ("access", "contacts", "deals")}, indent=1))
    print("meetings:", out["meetings"]["status"], out["meetings"]["count"])


if __name__ == "__main__":
    main()
