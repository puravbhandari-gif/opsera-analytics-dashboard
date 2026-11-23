"""Turn David's "DG-Demo Requests" Salesforce export into data/demo_requests.json for the Leads tab: what happened
to each demo request, as counts per day only. The export holds names and emails, so it stays in
~/Desktop/Data/salesforce-exports, never in the repo. Run by hand when a new export arrives:
    .venv/bin/python scripts/build_demo_requests.py

Agreed with Purav on 5 Nov 2026: groups from Lead Status.
Made stricter the same day: 5 groups.
- Qualified: Meeting Set, Engaging
- Not reviewed yet: Open, Assigned
- Already a contact: the person is already a Salesforce contact
- Not now: Nurture
- Disqualified: Disqualified
From the 5 Nov export, which has X-Factor: an X4 Basic Lead counts as Disqualified, whatever its Lead Status. Each request
counts once. Every demo request gets X1 automatically, so X1 isn't a quality signal; X-Factor is also shown on its own.
Each request counts on the day the person joined the campaign (Member First Associated Date). Each person counts once.

Agreed with Purav on 19 Nov 2026 (David's targets: 40 to 50% of demo requests to a meeting, 50% of meetings to a deal):
- Meeting set: the person has a "Date 3 - Meeting Set" on or after their request, in any "02a Campaigns with Meetings"
  export, matched by email. Only SDRs fill in the meeting fields, so AE meetings aren't counted.
- On a deal: the person is a contact on a deal created on or after their request, matched by email in the newest
  "Mktg#05 Multi-Attrib Opportunities" export or by name as the Primary Contact in the newest opportunities export.
"""
import collections
import datetime as dt
import glob
import json
import os
import re
import sys
from html import unescape
from pathlib import Path

EXPORTS = Path(os.path.expanduser("~/Desktop/Data/salesforce-exports"))
OUT = Path(__file__).resolve().parent.parent / "data" / "demo_requests.json"
HUBSPOT_MEMBERS = EXPORTS / "hubspot" / "members_demo_and_meetings.json"   # pulled through the HubSpot connection; private
DEMO_CAMPAIGN_ID = "7014Q000002aJSeQAM"
GROUPS = {"Meeting Set": "qualified", "Engaging": "qualified", "Open": "open", "Assigned": "open", "Contact": "contact",
          "Nurture": "not_now", "Disqualified": "disqualified"}
ORDER = ("qualified", "open", "contact", "not_now", "disqualified")
X_FACTORS = {"x1": "X1", "x2": "X2", "x3": "X3", "x4": "X4"}   # X1 Sales Ready, X2 Hot Lead, X3 Mid-Quality, X4 Basic Lead


def table(path):
    text = Path(path).read_text(encoding="latin-1")
    rows = [[unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            for r in re.findall(r"<tr>(.*?)</tr>", text, re.S)]
    return [dict(zip(rows[0], r)) for r in rows[1:] if len(r) == len(rows[0])]


def newest(pattern):
    found = sorted(glob.glob(str(EXPORTS / pattern)), key=lambda p: re.search(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})", p).group(1))
    return found


def date_of(s):
    try:
        return dt.datetime.strptime((s or "").split()[0], "%m/%d/%Y").date()
    except (ValueError, IndexError):
        return None


def funnel(rows):
    """Per request: (meeting set on or after the request, on a deal created on or after the request)."""
    meetings = collections.defaultdict(list)   # email -> meeting set dates, from every meetings export
    for f in newest("02a Campaigns with Meetings (members)-*.xls"):
        for m in table(f):
            d = date_of(m.get("Date 3 - Meeting Set"))
            if d and m.get("Email"):
                meetings[m["Email"].lower()].append(d)
    deals_by_email, deals_by_name = collections.defaultdict(list), collections.defaultdict(list)
    touches = newest("Mktg#05 Multi-Attrib Opportunities-*.xls")
    if touches:
        # every campaign-touch export, since the 22 Nov 2026 one only covers deals from 3 Nov (frozen exports, 23 Nov 2026)
        for t in [t for f in touches for t in table(f)]:
            d = date_of(t.get("Opportunity: Created Date"))
            if d and t.get("Email"):
                deals_by_email[t["Email"].lower()].append(d)
    opps = newest("Open Oppty Opportunities-*.xls")
    if opps:
        for o in table(opps[-1]):
            d = date_of(o.get("Created Date"))
            if d and o.get("Primary Contact"):
                deals_by_name[o["Primary Contact"].strip().lower()].append(d)
    out = []
    for r in rows:
        asked = date_of(r["Member First Associated Date"])
        email, name = (r.get("Email") or "").lower(), f"{r.get('First Name', '')} {r.get('Last Name', '')}".strip().lower()
        met = any(d >= asked for d in meetings.get(email, []))
        deal = any(d >= asked for d in deals_by_email.get(email, []) + deals_by_name.get(name, []))
        out.append((met, deal))
    used = {"meetings": [re.search(r"(\d{4}-\d{2}-\d{2})", f).group(1) for f in newest("02a Campaigns with Meetings (members)-*.xls")],
            "campaign_touches": re.search(r"(\d{4}-\d{2}-\d{2})", touches[-1]).group(1) if touches else None,
            "opportunities": re.search(r"(\d{4}-\d{2}-\d{2})", opps[-1]).group(1) if opps else None}
    return out, used


def main():
    files = sorted(glob.glob(str(EXPORTS / "DG-Demo Requests-*.xls")))
    if not files:
        sys.exit("No DG-Demo Requests export in ~/Desktop/Data/salesforce-exports.")
    path = files[-1]   # the newest, by the date in its name
    text = Path(path).read_text(encoding="latin-1")
    rows = [[unescape(re.sub(r"<[^>]+>", "", c)).strip() for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            for r in re.findall(r"<tr>(.*?)</tr>", text, re.S)]
    head, rows = rows[0], [dict(zip(rows[0], r)) for r in rows[1:]]
    exported = re.search(r"(\d{4}-\d{2}-\d{2})-\d{2}-\d{2}-\d{2}\.xls$", path).group(1)
    source = "Salesforce campaign DG-Demo Requests, Lead Status"
    # From 23 Nov 2026 (Purav, after David asked to rely on HubSpot): the campaign's members come from HubSpot's synced
    # Salesforce campaign members, which matched David's export person for person (56). The export is the fallback.
    if HUBSPOT_MEMBERS.exists():
        snap = json.loads(HUBSPOT_MEMBERS.read_text())
        hs = [m for m in snap["members"] if (m.get("campaignid") or "")[:15] == DEMO_CAMPAIGN_ID[:15]]
        if hs:
            rows = [{"Member Type": m.get("type") or "", "Lead/Contact Status": m.get("lead_contact_status__c") or "",
                     "X-Factor": m.get("x_factor__c") or "", "Email": m.get("email") or "",
                     "First Name": m.get("firstname") or "", "Last Name": m.get("lastname") or "",
                     "Member First Associated Date": dt.date.fromisoformat(m["added_to_campaign"]).strftime("%m/%d/%Y")}
                    for m in hs if m.get("added_to_campaign")]
            head = list(rows[0])
            exported, source = snap["pulled"], "Salesforce campaign DG-Demo Requests as synced to HubSpot, Lead Status"
    status = lambda r: "Contact" if r["Member Type"] == "Contact" else r["Lead/Contact Status"]
    unknown = {status(r) for r in rows} - set(GROUPS)
    if unknown:   # a new Lead Status needs a group before the page can show it
        sys.exit(f"Lead Status not in any group yet: {', '.join(sorted(unknown))}. Nothing was written.")
    xf = lambda r: (r.get("X-Factor") or "")[:2].lower()   # "X4 Basic Lead" -> "x4"
    days, statuses = collections.defaultdict(collections.Counter), collections.Counter()
    steps, used = funnel(rows)
    for r, (met, deal) in zip(rows, steps):
        d = dt.datetime.strptime(r["Member First Associated Date"], "%m/%d/%Y").date().isoformat()
        days[d]["meeting"] += met
        days[d]["deal"] += deal
        days[d]["deal_after_meeting"] += met and deal
    for r in rows:
        d = dt.datetime.strptime(r["Member First Associated Date"], "%m/%d/%Y").date().isoformat()
        days[d]["disqualified" if xf(r) == "x4" else GROUPS[status(r)]] += 1
        if xf(r) in X_FACTORS:
            days[d][xf(r)] += 1
        statuses[status(r)] += 1
    OUT.write_text(json.dumps({
        "source": source,
        "exported": exported, "start_date": min(days), "end_date": (dt.date.fromisoformat(exported) - dt.timedelta(days=1)).isoformat(),
        "statuses": dict(statuses.most_common()),
        "has_x_factor": "X-Factor" in head,
        "x4_by_status": dict(collections.Counter(status(r) for r in rows if xf(r) == "x4").most_common()),
        "funnel_exports": used,
        "daily": [{"date": d, **{g: days[d][g] for g in ORDER + tuple(X_FACTORS) + ("meeting", "deal", "deal_after_meeting")}} for d in sorted(days)],
    }, indent=1) + "\n")
    print(f"Demo requests: {len(rows)} people, {dict(statuses.most_common())}; meeting set {sum(m for m, _ in steps)}, "
          f"on a deal {sum(d for _, d in steps)}, both {sum(m and d for m, d in steps)}")


if __name__ == "__main__":
    main()
