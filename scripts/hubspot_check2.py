"""Second HubSpot check: where the old LinkedIn source names appear (any date), what the
integration contacts and meetings come from, and how deals connect to contacts. Counts only."""
import collections
import json
import os

import requests

API = "https://api.hubapi.com"
SINCE = "2026-09-01T00:00:00Z"
s = requests.Session()
s.headers["Authorization"] = f"Bearer {os.environ['HUBSPOT_TOKEN']}"


def search(obj, filters, props=(), limit=200, after=None):
    body = {"filterGroups": [{"filters": filters}], "properties": list(props), "limit": limit}
    if after:
        body["after"] = after
    r = s.post(f"{API}/crm/v3/objects/{obj}/search", json=body, timeout=60)
    return r.status_code, r.json()


def all_rows(obj, filters, props):
    rows, after = [], None
    while True:
        code, j = search(obj, filters, props, after=after)
        if code != 200:
            return rows
        rows += j.get("results", [])
        after = (j.get("paging") or {}).get("next", {}).get("after")
        if not after or len(rows) >= 10000:
            return rows


out = {}
FIELDS = ["utm_source", "utm_source_fc", "utm_source_rc", "utm_medium", "utm_campaign", "leadsource", "lead_source_detail__c", "source_2",
          "macro_source", "macro_source_text", "hs_analytics_source_data_1", "hs_analytics_source_data_2", "hs_latest_source_data_1",
          "hs_latest_source_data_2", "luma_referrer", "warmly_utm_sources", "hs_analytics_first_url", "hs_analytics_first_referrer"]
TERMS = ["linkedin", "kumar", "opseralinkedin", "opserasocial", "lnkd"]
hits = {}
for f in FIELDS:
    for t in TERMS:
        for when, flt in (("any date", []), ("since 1 Sep", [{"propertyName": "createdate", "operator": "GTE", "value": SINCE}])):
            code, j = search("contacts", [{"propertyName": f, "operator": "CONTAINS_TOKEN", "value": f"*{t}*"}] + flt, [f], limit=100)
            if code == 200 and j.get("total"):
                # web addresses can carry personal details in their query string, so only their counts are kept
                vals = collections.Counter() if f in ("hs_analytics_first_url", "hs_analytics_first_referrer") else \
                    collections.Counter((r["properties"].get(f) or "")[:80] for r in j.get("results", []))
                hits.setdefault(f"{f} contains '{t}'", {})[when] = {"total": j["total"], "sample_values": vals.most_common(8)}
out["linkedin_terms"] = hits

since = [{"propertyName": "createdate", "operator": "GTE", "value": SINCE}]
rows = all_rows("contacts", since, ["hs_object_source", "hs_object_source_detail_1", "hs_object_source_detail_2", "luma_referrer",
                                    "engagements_last_meeting_booked_source", "engagements_last_meeting_booked_campaign", "num_associated_deals",
                                    "hs_analytics_source", "lifecyclestage"])
c = collections.Counter
out["contacts_since"] = len(rows)
out["integration_detail"] = c(f"{r['properties'].get('hs_object_source_detail_1')} / {r['properties'].get('hs_object_source_detail_2')}"
                             for r in rows if r["properties"].get("hs_object_source") == "INTEGRATION").most_common(15)
out["luma_referrer"] = c(r["properties"].get("luma_referrer") for r in rows if r["properties"].get("luma_referrer")).most_common(15)
out["meeting_booked_source"] = c(r["properties"].get("engagements_last_meeting_booked_source") for r in rows if r["properties"].get("engagements_last_meeting_booked_source")).most_common(15)
out["with_deals_by_source"] = c(f"{r['properties'].get('hs_object_source')} / {r['properties'].get('hs_analytics_source')}"
                                for r in rows if int(r["properties"].get("num_associated_deals") or 0) > 0).most_common(15)
out["form_contacts_by_original_source"] = c(r["properties"].get("hs_analytics_source") for r in rows if r["properties"].get("hs_object_source") == "FORM").most_common(15)

deals = all_rows("deals", since, ["createdate", "amount", "hs_object_source", "hs_object_source_detail_1", "num_associated_contacts"])
out["deals_by_creation_source"] = c(f"{d['properties'].get('hs_object_source')} / {d['properties'].get('hs_object_source_detail_1')}" for d in deals).most_common(15)
out["deals_with_contacts"] = sum(1 for d in deals if int(d["properties"].get("num_associated_contacts") or 0) > 0)
out["deal_amounts_by_creation_source"] = {k: round(sum(float(d["properties"].get("amount") or 0) for d in deals
                                                     if f"{d['properties'].get('hs_object_source')} / {d['properties'].get('hs_object_source_detail_1')}" == k), 2)
                                          for k, _ in out["deals_by_creation_source"]}
r = s.get(f"{API}/crm/v3/pipelines/deals", timeout=60)
out["pipelines"] = [{"label": p["label"], "stages": [(st["label"], st["metadata"].get("isClosed"), st["metadata"].get("probability")) for st in p["stages"]]}
                    for p in r.json().get("results", [])] if r.ok else r.status_code

meetings = all_rows("meetings", [{"propertyName": "hs_createdate", "operator": "GTE", "value": SINCE}],
                    ["hs_meeting_title", "hs_activity_type", "hs_meeting_external_url", "hs_internal_meeting_notes", "hs_meeting_location_type"])
out["meetings"] = len(meetings)
out["meeting_types"] = c(m["properties"].get("hs_activity_type") for m in meetings).most_common(10)
out["meeting_title_words"] = c(w.lower() for m in meetings for w in (m["properties"].get("hs_meeting_title") or "").split()[:3]
                               if w.isalpha() and len(w) > 3 and not w[0].isupper()).most_common(25)   # common words only, no names
json.dump(out, open("hubspot_check.json", "w"), indent=1, default=str)
print("done", len(rows), len(deals), len(meetings))
