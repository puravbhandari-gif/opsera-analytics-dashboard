"""Turn David's Salesforce exports into data/salesforce_pipeline.json for the Pipeline tab: counts and totals only.
The exports hold names, emails and companies, so they stay in ~/Desktop/Data/salesforce-exports, never in the repo.
Run by hand when new exports arrive (they aren't part of the Monday update):
    .venv/bin/python scripts/build_salesforce_pipeline.py

Agreed with Purav on 28 Oct 2026:
- Open and won opportunities only; closed lost is left out. (Replaced 9 Nov 2026: every deal created counts, open, won or lost,
  so a past quarter doesn't drop when deals are lost later. Marketing deals are also split into won, lost and open.)
- Marketing sourced: the Primary Campaign Source is a marketing campaign.
- Marketing influenced: not sourced, but the Attrib First or Attrib Last Campaign, or any campaign touch in the
  multi-attribution export, is a marketing campaign.
- SDR and AE outreach count as sales, not marketing.
- Campaign-influenced meetings: people with a meeting (Date 3 - Meeting Set) since 1 Apr who joined a marketing
  campaign on or before that date. Each person counts once.
- Target-account campaign names are hidden. No company, person or deal name is written.

Agreed with Purav on 29 Oct 2026, from David's answers:
- DG-2025-Lantern_Records is not marketing.
- A campaign only counts if the person joined it within 90 days before the deal was created. Join dates come from
  the meetings export, matched by email (campaign touches) or name (primary contact); where no join date is known
  the campaign still counts, and the page says how many deals that is.
- DoGood and CrestingWave are an outside booking agency: their own group, "Booking agency", not marketing.
- Campaign IDs (from "All Campaigns with Campaign ID") are turned into names. (From 19 Nov 2026, names come from HubSpot's
  synced "Salesforce Campaigns" object first, saved as hubspot-campaign-names.json next to the exports.)
- Events: people in each event's Salesforce campaign who then had a meeting set.
- Anything based on Primary Campaign Source is an estimate (David: a starting point, not reliable on its own).
- Deals with no contact linked are their own group, "No contact linked", not sales.
- Events with their own Salesforce member export (Flutter, Gartner Xpo, GitHub Universe; agreed 3 Nov 2026; Tokenomics from 9 Nov): members
  are matched by email to the meetings export, and count when a meeting was set on or after the event's first day.
- A "To review" list: deals with a campaign joined just outside the 90-day window (91 to 120 days), or whose campaigns
  match more than one source (marketing, booking agency, SDR or AE outreach).
Agreed with Purav on 9 Nov 2026 (replacing the 6 Nov flags): a deal that existed before the event it's credited to counts as
influenced, never sourced, and is flagged "Deal existed before the event; counted as influenced" on the To review list.
- Accounts listed under "influenced_only" in hand-rules.json (names stay out of this repo).
- Any deal credited to an event that started after the deal was created.
Agreed with Purav on 17 Nov 2026, from David's comments on the Q3 deal sheet:
- "Promoted to X2 Status" is a helper campaign, not a real source. When it is the Primary Campaign Source, the first real
  campaign (Attrib First, then Attrib Last) takes its place as the source.
- Deals David named as started with a demo request form count as sourced by DG-Demo Requests. They're listed in
  hand-rules.json next to the exports, so no deal name is in this repo.
Agreed with Purav on 19 Nov 2026, from David: deals are sales, partner or marketing sourced, and partner deals are never
marketing sourced. Any deal with a partner listed on it (from the Opportunity QA report) counts as marketing influenced,
even when its source is a marketing campaign, and goes on the To review list.
"""
import collections
import datetime as dt
import glob
import json
import os
import re
import statistics
import sys
from zoneinfo import ZoneInfo
from html.parser import HTMLParser
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from privacy import customer_pattern  # noqa: E402  (the private customer list)

EXPORTS = Path(os.path.expanduser("~/Desktop/Data/salesforce-exports"))
OUT = Path(__file__).resolve().parent.parent / "data" / "salesforce_pipeline.json"
START = dt.date(2026, 4, 1)
SALES = re.compile(r"sdr|\bae\b", re.I)                       # SDR-Meeting-Set, DG-SDR Outreach (Cold), AE Prospecting, AE Internal Referral
# Not marketing either (agreed 28 Oct 2026): a test campaign, a lead-status flag and a bought LinkedIn contact list.
# Partner deal registrations too, until David confirms (Purav, 18 Nov 2026). Customer and partner expansion, the third-party
# vendor campaign and any campaign named after a partner (the "partners" list in hand-rules.json) aren't marketing either
# (Purav, 18 Nov 2026, from David's Opportunity QA report).
NOT_MARKETING = {"Current Customer Expansion", "Partner Account Expansion", "DG-FY27-3rd Party Vendor Other", "DG-F27 - Partner Deal Reg", "X2-Tracking-Test-Campaign", "DG-FY27 Promoted to X2 Status", "DG-FY27 Wiza LinkedIn Exports", "DG-2025-Lantern_Records"}
AGENCY = re.compile(r"dogood|crestingwave", re.I)              # outside booking agency (David's "c")
WINDOW_DAYS = 90
NEAR_DAYS = 120   # joined 91 to 120 days before: just outside the window, for the To review list
CAMPAIGN_ID = re.compile(r"^701[A-Za-z0-9]{12}([A-Za-z0-9]{3})?$")
# Each event row on the Events tab (keys from scripts/fetch_hubspot.py) and its Salesforce campaign
EVENT_CAMPAIGNS = {"appsec_agents": "DG-FY27-Q1-Meet-the-Agents-Webinar", "ai_benchmark": "DG-FY27-Q1-AI-BM-Report-Webinar",
                   "ai_adoption": "DG-FY27-Q1-AI-Adoption-Webinar", "mq_roundtable": "DG-FY27-Q2-MQ-Roundtable",
                   "tokenomics": "DG-FY27-Q3-Tokenomics-Webinar", "flutter": "DG-FY27-Q3-SC-Flutter-Summit",
                   "gartner": "DG-FY27-Q3-Gartner-Xpo", "github_universe": "DG-FY27-Q3-GitHub-Universe-2026"}
TARGET_ACCOUNTS = re.compile(r"\b(abm|abx|microsite)\b", re.I)
FILES = {"opportunities": "Open Oppty Opportunities-*.xls", "qa": "Opportunity QA-*.xls", "touches": "Mktg#05 Multi-Attrib Opportunities-*.xls",
         "meetings": "02a Campaigns with Meetings (members)-*.xls", "campaign_ids": "All Campaigns with Campaign ID-*.xls",
         "event_flutter": "DG-FY27-Q3-SC-Flutter-Summit-*.xls", "event_gartner": "DG-FY27-Q3-Gartner-Xpo-*.xls",
         "event_github_universe": "DG-FY27-Q3-GitHub-Universe-2026-*.xls", "event_tokenomics": "DG-FY27-Q3-Tokenomics-Webinar-*.xls"}
HELPERS = {"DG-FY27 Promoted to X2 Status"}   # helper campaigns: never the source (David, 17 Nov 2026)
HAND_RULES = EXPORTS / "hand-rules.json"     # private: deal names stay out of the repo
FROZEN_OPPS_ON = "2026-11-22"   # David's last opportunities export; nothing newer will come (23 Nov 2026)
HUBSPOT_DEALS = EXPORTS / "hubspot" / "deals.json"   # HubSpot deals snapshot, pulled through the HubSpot connection; private
HUBSPOT_EVENT_MEMBERS = EXPORTS / "hubspot" / "event_members.json"
EVENT_CAMPAIGN_IDS = {"flutter": "701UR00000vIfboYAC", "gartner": "701UR00000vaGzyYAE", "github_universe": "701UR00000vvO3BYAU", "tokenomics": "701UR00000tWqi9YAC"}
HUBSPOT_NAMES = EXPORTS / "hubspot-campaign-names.json"   # Salesforce campaign ID -> name, from HubSpot; private (partner names)
EXISTED_BEFORE = "Deal existed before the event; counted as influenced"
PARTNER_ON_DEAL = "Partner on the deal; counted as influenced"
EVENT_FIRST_DAY = {"flutter": dt.date(2026, 10, 1), "gartner": dt.date(2026, 10, 19), "github_universe": dt.date(2026, 10, 28),
                   "tokenomics": dt.date(2026, 9, 15)}


class _Tables(HTMLParser):
    """Salesforce's .xls export is an HTML table."""
    def __init__(self):
        super().__init__()
        self.tables, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None and self.row is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None and self.tables:
            self.tables[-1].append(self.row)
            self.row = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def read(kind, back=0):
    """The newest export of one kind (or the one `back` places before it), as a list of dicts, and the date in its file name."""
    found = sorted(glob.glob(str(EXPORTS / FILES[kind])), key=lambda p: re.search(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})", p).group(1))
    if len(found) <= back:
        sys.exit(f"No {kind} export in {EXPORTS}")
    found = found[:len(found) - back]
    raw = Path(found[-1]).read_bytes()
    text = next(raw.decode(e) for e in ("utf-8", "cp1252", "latin-1") if _decodes(raw, e))
    p = _Tables()
    p.feed(text)
    table = max(p.tables, key=len)
    head = table[0]
    stamp = re.search(r"(\d{4}-\d{2}-\d{2})-\d{2}-\d{2}-\d{2}", found[-1]).group(1)
    since = re.search(r"-(\d{2})-(\d{2})-(\d{4})\.xls$", found[-1])   # "…-05-01-2026.xls": the report starts on 1 May 2026
    read.covers_from = f"{since.group(3)}-{since.group(1)}-{since.group(2)}" if since else None
    return [dict(zip(head, r)) for r in table[1:] if any(r)], stamp


def _decodes(raw, enc):
    try:
        raw.decode(enc)
        return True
    except UnicodeDecodeError:
        return False


def day(s):
    return dt.datetime.strptime(s, "%m/%d/%Y").date() if s else None


def partner_named():
    names = json.loads(HAND_RULES.read_text()).get("partners", []) if HAND_RULES.exists() else []
    return re.compile("|".join(re.escape(n) for n in names), re.I) if names else re.compile(r"(?!x)x")


PARTNER_NAMED = partner_named()


def marketing(campaign):
    return bool(campaign) and not SALES.search(campaign) and not AGENCY.search(campaign) and campaign.strip() not in NOT_MARKETING \
        and not PARTNER_NAMED.search(campaign)


COMPANY_NAMED = customer_pattern()


def public(campaign):
    """Target-account campaigns, and campaigns named after a customer or partner, are never named (18 Nov 2026)."""
    if TARGET_ACCOUNTS.search(campaign):
        return "Target-account campaign"
    return "Campaign named after a company" if COMPANY_NAMED.search(campaign) else campaign


def fiscal_quarter(d):
    """Opsera's fiscal year starts in February: FY27 Q2 is May to July 2026."""
    q = ((d.month + 10) % 12) // 3 + 1
    return f"FY{(d.year + (1 if d.month >= 2 else 0)) % 100} Q{q}"


def event_members(meets):
    """Members of each event's own Salesforce export, and how many had a meeting set on or after the event's first day.
    Matched by email in memory; only counts are written."""
    set_on = collections.defaultdict(list)   # email -> (meeting set date, outcome)
    for m in meets:
        e, when = (m.get("Email") or "").lower(), day(m.get("Date 3 - Meeting Set") or "")
        if e and when:
            set_on[e].append((when, m.get("Meeting Outcome") or "Not recorded"))
    out = []
    # From 23 Nov 2026 members come from HubSpot's synced Salesforce campaign members (they matched the 4 exports exactly)
    hs_members, hs_on = collections.defaultdict(list), ""
    if HUBSPOT_EVENT_MEMBERS.exists():
        snap = json.loads(HUBSPOT_EVENT_MEMBERS.read_text())
        hs_on = snap["pulled"]
        ids = {v[:15]: k for k, v in EVENT_CAMPAIGN_IDS.items()}
        for m in snap["members"]:
            k = ids.get((m.get("campaignid") or "")[:15])
            if k:
                hs_members[k].append({"Email": m.get("email") or "", "Member Status": m.get("status") or ""})
    for key, first in EVENT_FIRST_DAY.items():
        if hs_members.get(key):
            rows, stamp = hs_members[key], hs_on
        else:
            try:
                rows, stamp = read(f"event_{key}")
            except SystemExit:
                continue   # no members for this event yet
        emails = {(r.get("Email") or "").lower() for r in rows if r.get("Email")}
        met = {e: [o for d, o in set_on[e] if d >= first] for e in emails}
        met = {e: o for e, o in met.items() if o}
        out.append({"key": key, "campaign": EVENT_CAMPAIGNS[key], "export": stamp, "from": "HubSpot" if hs_members.get(key) else "export", "members": len(rows),
                    "statuses": dict(collections.Counter(r.get("Member Status") or "Not recorded" for r in rows)),
                    "people_with_meeting": len(met), "held": sum(1 for o in met.values() if "Meeting Held" in o)})
    return out


def hubspot_opps(frozen):
    """HubSpot deals in the shape of David's opportunities export. `frozen` is the export rows, used only where HubSpot is blank."""
    snap = json.loads(HUBSPOT_DEALS.read_text())
    stages = json.loads((EXPORTS / "hubspot" / "stages.json").read_text())
    pulled = dt.date.fromisoformat(snap["pulled"])
    old = {(o.get("Opportunity ID") or "")[:15]: o for o in frozen}
    last_export = max((day(o["Created Date"]) for o in frozen if o.get("Created Date")), default=dt.date(2000, 1, 1)).isoformat()
    last_export = max(last_export, FROZEN_OPPS_ON)
    pacific = ZoneInfo("America/Los_Angeles")   # Salesforce dates are Pacific; HubSpot's are UTC
    rows, extra = [], 0
    for d in snap["deals"]:
        oid = (d.get("hs_salesforceopportunityid") or "")[:15]
        if not oid:
            continue
        f = old.get(oid, {})
        created = dt.datetime.fromisoformat(d["createdate"].replace("Z", "+00:00")).astimezone(pacific).date()
        # Only the deals David's report listed (Purav, 23 Nov 2026): HubSpot also has older renewals the report left out.
        # Deals created after his last export can't be in it, so those all count.
        if not f and created.isoformat() <= last_export:
            extra += 1
            continue
        pick = lambda hs_key, ex_key: d.get(hs_key) or f.get(ex_key, "")
        rows.append({
            "Opportunity ID": oid,
            "Opportunity Name": f.get("Opportunity Name") or d.get("dealname") or "",
            "Account Name": f.get("Account Name", ""),
            "Primary Campaign Source": pick("primary_campaign_source", "Primary Campaign Source"),
            "Attrib First Campaign": pick("attrib_first_campaign", "Attrib First Campaign"),
            "Attrib Last Campaign": pick("attrib_last_campaign", "Attrib Last Campaign"),
            "Type": d.get("dealtype") or f.get("Type", ""),
            "Stage": stages.get(d.get("dealstage") or "", f.get("Stage", "")),
            "Created Date": created.strftime("%m/%d/%Y"),
            "Amount": d.get("amount") or "0",
            # HubSpot has the contact but not the name the join dates are keyed on; a placeholder still marks "has a contact"
            "Primary Contact": f.get("Primary Contact") or ("(HubSpot contact)" if int(d.get("num_associated_contacts") or 0) else ""),
            "Age": str((pulled - created).days),
            "Entered stage": (d.get("hs_v2_date_entered_current_stage") or "")[:10],
        })
    return rows, snap["pulled"], extra


def main():
    opps, opps_on = read("opportunities")
    # the report's start, from "…-05-01-2026.xls" in the file name; newer exports drop it, so use the 1st of the earliest month
    opps_cover_from = read.covers_from or min(day(o["Created Date"]) for o in opps if o["Created Date"]).replace(day=1).isoformat()
    # An export that starts later than the one before it (the 6 Nov 2026 export starts in August): deals created before it
    # starts come from the earlier exports, so earlier months keep their deals (agreed 9 Nov 2026).
    for back in range(1, 10):
        try:
            older, _ = read("opportunities", back)
        except SystemExit:
            break
        older_from = read.covers_from or min(day(o["Created Date"]) for o in older if o["Created Date"]).replace(day=1).isoformat()
        if older_from < opps_cover_from:
            opps += [o for o in older if o["Created Date"] and day(o["Created Date"]).isoformat() < opps_cover_from]
            opps_cover_from = older_from
    # David's Opportunity QA report (from 18 Nov 2026) is the newer list of deals when it's newer than the opportunities export.
    # It has no Attrib First Campaign, so that comes from the opportunities export for deals in both, matched by Opportunity ID;
    # newer deals have none (agreed 18 Nov 2026).
    try:
        qa, qa_on = read("qa")
    except SystemExit:
        qa, qa_on = [], ""
    # Any deal with a partner listed on it (Primary Partner, Partner or Partner Assist 1 in David's QA report) counts as
    # marketing influenced, never sourced, even when its source is a marketing campaign (Purav, 19 Nov 2026).
    partner_deals = {(o.get("Opp ID 18") or "")[:15] for o in qa
                     if any((o.get(k) or "").strip() for k in ("Primary Partner", "Partner", "Partner Assist 1"))} - {""}
    print(f"Partner deals (from the Opportunity QA report of {qa_on or 'none'}): {len(partner_deals)}")
    no_first = 0
    if qa_on > opps_on:
        first = {o["Opportunity ID"][:15]: o.get("Attrib First Campaign", "") for o in opps if o.get("Opportunity ID")}
        qa_from = min(day(o["Created Date"]) for o in qa if o["Created Date"]).replace(day=1).isoformat()
        rows = []
        for o in qa:
            oid = (o.get("Opp ID 18") or "")[:15]
            no_first += oid not in first
            rows.append({**o, "Opportunity ID": oid, "Attrib First Campaign": first.get(oid, "")})
        opps = rows + [o for o in opps if o["Created Date"] and day(o["Created Date"]).isoformat() < qa_from]
        opps_on, opps_cover_from = qa_on, min(opps_cover_from, qa_from)
        print(f"Using the Opportunity QA report of {qa_on}: {len(qa)} deals, {no_first} without an Attrib First Campaign (newer than the opportunities export).")
    # From 23 Nov 2026 (Purav, after David asked to rely on HubSpot): deals come from HubSpot, synced from Salesforce.
    # David's last exports stay frozen for what HubSpot can't give: a blank campaign field, deal and account names
    # (they key the hand rules), the primary contact's name (it keys join dates), and the partner flags above.
    hs_extra = 0
    if HUBSPOT_DEALS.exists():
        opps, opps_on, hs_extra = hubspot_opps(opps)
        print(f"Deals from HubSpot (pulled {opps_on}): {len(opps)}; {hs_extra} older deals David's report didn't list are left out.")
    touches, touches_on = read("touches")
    # The 22 Nov 2026 campaign-touch export only covers deals created from 3 Nov, so older exports fill in every deal
    # the newest one leaves out (the same way older opportunity exports fill earlier months, agreed 9 Nov 2026).
    # A deal in the newest export takes only its rows from there.
    touches_older = []
    for back in range(1, 10):
        try:
            older, older_on = read("touches", back)
        except SystemExit:
            break
        have = {t.get("Opportunity ID") for t in touches}
        add = [t for t in older if t.get("Opportunity ID") not in have]
        if add:
            touches += add
            touches_older.append(older_on)
    if touches_older:
        print(f"Campaign touches: newest export {touches_on}, older exports {', '.join(sorted(touches_older))} fill in the deals it leaves out.")
    meets, meets_on = read("meetings")
    # The 9 Nov 2026 export covers fewer people than the 27 Oct one (it filters on meeting date), so older exports fill in:
    # a person's join date doesn't change, and without it a campaign counts by default (agreed 9 Nov 2026).
    seen = {(m.get("Email", "").lower(), m["Campaign Name"], m["Date 3 - Meeting Set"]) for m in meets}
    meets_older = []   # dates of the older exports used
    for back in range(1, 10):
        try:
            older, older_on = read("meetings", back)
            meets_older.append(older_on)
        except SystemExit:
            break
        for m in older:
            k = (m.get("Email", "").lower(), m["Campaign Name"], m["Date 3 - Meeting Set"])
            if k not in seen:
                seen.add(k)
                meets.insert(0, m)   # older rows first, so the newest export's join date wins
    ids, _ = read("campaign_ids")
    id_names = {r["Campaign ID"][:15]: r["Campaign Name"] for r in ids if r.get("Campaign ID")}
    # Campaign names come from HubSpot first (Purav, 19 Nov 2026): David syncs Salesforce campaigns into HubSpot's
    # "Salesforce Campaigns" object, saved next to the exports as hubspot-campaign-names.json. The 28 Oct list fills any gap.
    if HUBSPOT_NAMES.exists():
        hs = json.loads(HUBSPOT_NAMES.read_text())
        id_names |= {i[:15]: n for i, n in hs["names"].items() if n}
        print(f"Campaign names: {len(hs['names'])} from HubSpot (pulled {hs['pulled_on']}), the 28 Oct list for the rest")
    else:
        print("Campaign names: hubspot-campaign-names.json is missing, so only the 28 Oct list is used")
    name = lambda v: id_names.get(v.strip()[:15], v) if CAMPAIGN_ID.match((v or "").strip()) else (v or "").strip()

    touched = collections.defaultdict(set)   # opportunity -> campaigns it touched (multi-attribution export)
    emails = collections.defaultdict(set)    # opportunity -> its contacts' emails
    for t in touches:
        if t.get("Campaign Name"):
            touched[t["Opportunity Name"]].add(name(t["Campaign Name"]))
        if t.get("Email"):
            emails[t["Opportunity Name"]].add(t["Email"].lower())
    joined, by_person_name = {}, collections.defaultdict(set)   # (email, campaign) -> first joined; "first last" -> emails
    for m in meets:
        e = (m.get("Email") or "").lower()
        if e:
            joined[(e, name(m["Campaign Name"]))] = day(m["Member First Associated Date"])
            by_person_name[f"{m.get('First Name', '')} {m.get('Last Name', '')}".strip().lower()].add(e)

    hand = json.loads(HAND_RULES.read_text()) if HAND_RULES.exists() else {}
    by_demo_request = set(hand.get("sourced_by_demo_request", {}))
    influenced_only = set(hand.get("influenced_only", {}))   # existed before the event it's credited to (Purav, 9 Nov 2026)

    BUCKETS = ("sourced", "influenced", "agency", "nocontact")
    STATUSES = ("won", "lost", "open")
    by_month = collections.defaultdict(lambda: {b: [0, 0] for b in BUCKETS})
    by_day = collections.defaultdict(lambda: {b: [0, 0] for b in BUCKETS})   # for the period switch
    status_day = collections.defaultdict(lambda: {s: [0, 0] for s in STATUSES})   # marketing deals (sourced and influenced) by won, lost, open
    by_campaign = collections.defaultdict(lambda: [0, 0])
    counted = no_contact = unknown_join = dropped_by_window = 0
    review = []
    for o in opps:
        created = day(o["Created Date"])
        if not created or created < START:
            continue
        status = "won" if "won" in o["Stage"].lower() else "lost" if "lost" in o["Stage"].lower() else "open"
        counted += 1
        no_contact += not o.get("Primary Contact")
        amount = round(float(o.get("Amount") or 0))
        people = emails[o["Opportunity Name"]] | by_person_name.get((o.get("Primary Contact") or "").strip().lower(), set())
        has_contact = bool(o.get("Primary Contact") or emails[o["Opportunity Name"]])
        unknown = False
        near = set()   # campaigns joined just outside the window

        def counts(c):
            """A marketing campaign counts if someone on the deal joined it within 90 days before the deal was created.
            When no join date is known for anyone on the deal, it still counts (and is reported)."""
            nonlocal unknown
            dates = [joined[(e, c)] for e in people if (e, c) in joined]
            if not dates:
                unknown = True
                return True
            if any(d and 0 <= (created - d).days <= WINDOW_DAYS for d in dates):
                return True
            if any(d and WINDOW_DAYS < (created - d).days <= NEAR_DAYS for d in dates):
                near.add(c)
            return False

        primary = name(o.get("Primary Campaign Source", ""))
        others = [name(o.get("Attrib First Campaign", "")), name(o.get("Attrib Last Campaign", "")), *sorted(touched.get(o["Opportunity Name"], ()))]
        if primary in HELPERS:
            primary = next((c for c in others[:2] if c and c not in HELPERS), "")
        if o["Opportunity Name"].strip() in by_demo_request and "DG-Demo Requests" in others:
            primary = "DG-Demo Requests"
        had_marketing = any(marketing(c) for c in [primary, *others])
        if marketing(primary) and counts(primary):
            bucket, campaign = "sourced", primary
        elif AGENCY.search(primary):
            bucket, campaign = "agency", primary
        else:
            unknown = False
            campaign = next((c for c in others if marketing(c) and counts(c)), "")
            bucket = "influenced" if campaign else None
            if not bucket:
                campaign = next((c for c in others if AGENCY.search(c)), "")
                bucket = "agency" if campaign else None
        before_event = bucket in ("sourced", "influenced") and (o["Account Name"].strip() in influenced_only or any(
            EVENT_CAMPAIGNS[k] == campaign and created < first for k, first in EVENT_FIRST_DAY.items()))
        if before_event:
            bucket = "influenced"
        partner_deal = bucket == "sourced" and (o.get("Opportunity ID") or "")[:15] in partner_deals
        if partner_deal:
            bucket = "influenced"
        if not bucket:
            dropped_by_window += had_marketing
            if not has_contact:
                bucket, campaign = "nocontact", ""
        sources = {"marketing" for c in [primary, *others] if marketing(c)} | {"booking agency" for c in [primary, *others] if AGENCY.search(c)} | \
                  {"SDR or AE outreach" for c in [primary, *others] if c and SALES.search(c)}
        reasons = ([f"Joined {', '.join(sorted(public(c) for c in near))} 91 to {NEAR_DAYS} days before the deal"] if near else []) + \
                  ([f"Matches more than 1 source: {', '.join(sorted(sources))}"] if len(sources) > 1 else []) + \
                  ([EXISTED_BEFORE] if before_event else []) + \
                  ([PARTNER_ON_DEAL] if partner_deal else [])
        if reasons:
            review.append({"date": created.isoformat(), "amount": amount, "stage": o["Stage"],
                           "counted_as": {"sourced": "Marketing sourced (estimate)", "influenced": "Marketing influenced", "agency": "Booking agency",
                                          "nocontact": "No contact linked", None: "Sales"}[bucket],
                           "campaigns": sorted({public(c) for c in [primary, *others] if c}), "reasons": reasons})
        if not bucket:
            continue   # sales only: not written
        unknown_join += unknown and bucket in ("sourced", "influenced")
        for x in (by_month[created.strftime("%Y-%m")][bucket], by_day[created.isoformat()][bucket]):
            x[0] += 1
            x[1] += amount
        if bucket in ("sourced", "influenced"):
            x = status_day[created.isoformat()][status]
            x[0] += 1
            x[1] += amount
        if bucket != "nocontact":
            c = by_campaign[(bucket, public(campaign))]
            c[0] += 1
            c[1] += amount

    people = {}   # one row per person: their meeting date and the marketing campaigns they joined before it
    event_people = collections.defaultdict(dict)   # event campaign -> person -> outcome, for people who then had a meeting
    for m in meets:
        when, first, campaign = day(m["Date 3 - Meeting Set"]), day(m["Member First Associated Date"]), name(m.get("Campaign Name", ""))
        if campaign in EVENT_CAMPAIGNS.values() and when and first and first <= when:
            event_people[campaign][(m.get("Email") or "").lower() or id(m)] = m.get("Meeting Outcome") or "Not recorded"
        if not when or when < START or not first or first > when or not marketing(campaign):
            continue
        p = people.setdefault((m.get("Email") or "").lower() or id(m), {"date": when, "outcome": m.get("Meeting Outcome") or "Not recorded", "campaigns": set()})
        p["campaigns"].add(public(campaign))
    meet_months = collections.defaultdict(collections.Counter)
    meet_days = collections.defaultdict(collections.Counter)
    meet_campaigns = collections.Counter()
    for p in people.values():
        meet_months[p["date"].strftime("%Y-%m")][p["outcome"]] += 1
        meet_days[p["date"].isoformat()][p["outcome"]] += 1
        for c in p["campaigns"]:
            meet_campaigns[c] += 1

    # Open deals by stage (Purav, 19 Nov 2026, from David: deals mostly stall at Demo). Every open deal created since START,
    # sales, partner or marketing, as counts only. Age is days since the deal was created. Days in the current stage come
    # from HubSpot's date each deal entered its stage (added 23 Nov 2026).
    # the sales stages in order (1 Meeting to 5 Procurement), then the side tracks numbered "01", "03" (partner suspect, renewal)
    stage_order = lambda x: (x[0].startswith("0"), int(re.match(r"\d+", x[0]).group()) if re.match(r"\d+", x[0]) else 99, x[0])
    stage_ages = collections.defaultdict(list)
    stage_days = collections.defaultdict(list)   # days in the current stage, from HubSpot's date each deal entered it (23 Nov 2026)
    as_of = dt.date.fromisoformat(opps_on)
    for o in opps:
        created = day(o["Created Date"]) if o.get("Created Date") else None
        if not created or created < START or "closed" in o["Stage"].lower():
            continue
        if o.get("Entered stage"):
            stage_days[o["Stage"]].append((as_of - dt.date.fromisoformat(o["Entered stage"])).days)
        try:
            stage_ages[o["Stage"]].append(int(float((o.get("Age") or "").replace(",", ""))))
        except ValueError:
            stage_ages[o["Stage"]].append(None)
    open_by_stage = [{"stage": re.sub(r"^\d+\s*", "", s), "deals": len(v), "median_age": statistics.median([a for a in v if a is not None]) if any(a is not None for a in v) else None,
                      "over_90_days": sum(1 for a in v if a is not None and a > 90),
                      "median_days_in_stage": statistics.median(stage_days[s]) if stage_days[s] else None,
                      "in_stage_over_60_days": sum(1 for x in stage_days[s] if x > 60) if stage_days[s] else None}
                     for s, v in sorted(stage_ages.items(), key=stage_order)]

    out = {
        "source": "Salesforce reports",
        "deals_source": "HubSpot" if HUBSPOT_DEALS.exists() else "export",   # deals from HubSpot since 23 Nov 2026
        "exports": {"opportunities": opps_on, "campaign_touches": touches_on, "campaign_touches_older": sorted(touches_older), "meetings": meets_on, "meetings_older": sorted(meets_older)},
        "opportunities_cover_from": max(opps_cover_from or "", START.isoformat()),   # deals before START are never counted
        "opportunities_from": min(day(o["Created Date"]) for o in opps if o["Created Date"]).isoformat(),
        "opportunities_to": max(day(o["Created Date"]) for o in opps if o["Created Date"]).isoformat(),
        "share_without_contact_pct": round(no_contact / counted * 100) if counted else None,
        "window_days": WINDOW_DAYS, "deals_join_date_unknown": unknown_join, "deals_left_out_by_window": dropped_by_window,
        "months": [{"month": k, "quarter": fiscal_quarter(day(f"{k[5:]}/01/{k[:4]}")),
                    **{f"{b}_{w}": v[b][i] for b in BUCKETS for i, w in enumerate(("deals", "value")) if (b, w) != ("nocontact", "value")}}
                   for k, v in sorted(by_month.items())],
        "days": [{"date": k, **{f"{b}_{w}": v[b][i] for b in BUCKETS for i, w in enumerate(("deals", "value")) if (b, w) != ("nocontact", "value")}}
                 for k, v in sorted(by_day.items())],   # no contact linked: count only, never the value (agreed 29 Oct 2026)
        "marketing_status_days": [{"date": k, **{f"{s}_{w}": v[s][i] for s in STATUSES for i, w in enumerate(("deals", "value"))}}
                                  for k, v in sorted(status_day.items())],
        "campaigns": [{"bucket": b, "campaign": c, "deals": v[0], "value": v[1]} for (b, c), v in sorted(by_campaign.items(), key=lambda x: -x[1][1])],
        "to_review": sorted(review, key=lambda r: r["date"]),
        "open_by_stage": {"as_of": opps_on, "since": START.isoformat(), "stages": open_by_stage},
        "event_meetings": [{"key": k, "campaign": c, "people": len(event_people[c]),
                            "held": sum(1 for o in event_people[c].values() if o == "Meeting Held")} for k, c in EVENT_CAMPAIGNS.items()],
        "event_members": event_members(meets),
        "meetings": {"since": START.isoformat(),
                     "days": [{"date": k, "people": sum(v.values()), "outcomes": dict(v)} for k, v in sorted(meet_days.items())],
                     "months": [{"month": k, "people": sum(v.values()), "outcomes": dict(v)} for k, v in sorted(meet_months.items())],
                     "campaigns": [{"campaign": c, "people": n} for c, n in meet_campaigns.most_common()],
                     "people": len(people)},
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    s, i, a, n = (sum(m[f"{b}_deals"] for m in out["months"]) for b in BUCKETS)
    print(f"Wrote {OUT.name}: {counted} opportunities (open, won and lost) since {START}, {s} marketing sourced, {i} influenced, {a} booking agency, "
          f"{n} no contact linked, {len(review)} to review, "
          f"{out['share_without_contact_pct']}% with no contact, {unknown_join} counted without a known join date, {dropped_by_window} left out by the "
          f"{WINDOW_DAYS}-day rule; {len(people)} people with a campaign-influenced meeting; event meetings "
          + ", ".join(f"{e['key']} {e['people']}" for e in out["event_meetings"])
          + "; event exports " + ", ".join(f"{e['key']} {e['members']} members, {e['people_with_meeting']} with a meeting" for e in out["event_members"]))


if __name__ == "__main__":
    main()
