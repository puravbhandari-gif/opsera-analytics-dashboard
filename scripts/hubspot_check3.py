"""Third HubSpot check: campaigns, lists and imports named after Flutter, Tokenomics, Gartner or Luma,
and how the 448 imported contacts since 1 Sep are tagged. Names of lists and campaigns, and counts only."""
import collections
import json
import os

import requests

API = "https://api.hubapi.com"
SINCE = "2026-09-01T00:00:00Z"
TERMS = ["flutter", "tokenomics", "gartner", "luma"]
s = requests.Session()
s.headers["Authorization"] = f"Bearer {os.environ['HUBSPOT_TOKEN']}"
out = {}

out["lists"] = {}
for t in TERMS:
    r = s.post(f"{API}/crm/v3/lists/search", json={"query": t, "count": 100, "additionalProperties": ["hs_list_size"]}, timeout=60)
    out["lists"][t] = [{"name": l.get("name"), "size": (l.get("additionalProperties") or {}).get("hs_list_size"), "id": l.get("listId"),
                        "created": l.get("createdAt"), "type": l.get("processingType")} for l in r.json().get("lists", [])] if r.ok else f"{r.status_code}: {r.text[:150]}"

r = s.get(f"{API}/marketing/v3/campaigns", params={"limit": 100, "properties": "hs_name,hs_start_date,hs_end_date"}, timeout=60)
out["campaigns_access"] = r.status_code
if r.ok:
    out["campaigns"] = [{"name": (c.get("properties") or {}).get("hs_name"), "id": c.get("id"), "start": (c.get("properties") or {}).get("hs_start_date")}
                        for c in r.json().get("results", []) if any(t in ((c.get("properties") or {}).get("hs_name") or "").lower() for t in TERMS)]
else:
    out["campaigns"] = r.text[:200]


def all_rows(filters, props):
    rows, after = [], None
    while True:
        body = {"filterGroups": [{"filters": filters}], "properties": props, "limit": 200}
        if after:
            body["after"] = after
        r = s.post(f"{API}/crm/v3/objects/contacts/search", json=body, timeout=60)
        if not r.ok:
            return rows
        j = r.json(); rows += j.get("results", [])
        after = (j.get("paging") or {}).get("next", {}).get("after")
        if not after or len(rows) >= 10000:
            return rows


props = ["hs_object_source", "hs_object_source_detail_1", "hs_analytics_source", "hs_analytics_source_data_1", "hs_analytics_source_data_2",
         "campaign", "utm_campaign", "utm_source", "luma_referrer", "hs_latest_source_data_1", "leadsource", "lead_source_detail__c", "createdate"]
rows = all_rows([{"propertyName": "createdate", "operator": "GTE", "value": SINCE}], props)
c = collections.Counter
imp = [r["properties"] for r in rows if r["properties"].get("hs_object_source") == "IMPORT"]
out["imports_since"] = len(imp)
for p in ("hs_analytics_source_data_2", "campaign", "utm_campaign", "luma_referrer", "leadsource", "lead_source_detail__c", "hs_latest_source_data_1"):
    out[f"imports_by_{p}"] = c((x.get(p) or "(blank)")[:80] for x in imp).most_common(15)
out["imports_by_week"] = sorted(c(x["createdate"][:10] for x in imp).items())
luma = [r["properties"] for r in rows if r["properties"].get("luma_referrer")]
out["luma_referrer_contacts_by_creation"] = c(f"{x.get('hs_object_source')} / {x.get('hs_object_source_detail_1')}" for x in luma).most_common(10)
out["luma_referrer_contacts_by_campaign"] = c(f"{x.get('hs_analytics_source_data_1')} | campaign={x.get('campaign')}" for x in luma).most_common(10)
named = [r["properties"] for r in rows if any(t in " ".join(str(r["properties"].get(p) or "") for p in ("hs_analytics_source_data_1", "hs_analytics_source_data_2", "campaign", "utm_campaign")).lower() for t in TERMS)]
out["contacts_tagged_with_event_names"] = c(f"{x.get('hs_object_source')} | {x.get('hs_analytics_source_data_1')} | campaign={x.get('campaign')}" for x in named).most_common(20)
json.dump(out, open("hubspot_check3.json", "w"), indent=1, default=str)
print("done", len(rows), len(imp), len(luma), len(named))
