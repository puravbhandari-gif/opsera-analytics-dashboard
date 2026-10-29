"""Turn David's Salesforce exports into data/salesforce_pipeline.json for the Pipeline tab: counts and totals only.
The exports hold names, emails and companies, so they stay in ~/Desktop/Data/salesforce-exports, never in the repo.
Run by hand when new exports arrive (they aren't part of the Monday update):
    .venv/bin/python scripts/build_salesforce_pipeline.py

Agreed with Purav on 28 Oct 2026:
- Open and won opportunities only; closed lost is left out.
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
- Campaign IDs (from "All Campaigns with Campaign ID") are turned into names.
- Events: people in each event's Salesforce campaign who then had a meeting set.
- Anything based on Primary Campaign Source is an estimate (David: a starting point, not reliable on its own).
- Deals with no contact linked are their own group, "No contact linked", not sales.
- A "To review" list: deals with a campaign joined just outside the 90-day window (91 to 120 days), or whose campaigns
  match more than one source (marketing, booking agency, SDR or AE outreach).
"""
import collections
import datetime as dt
import glob
import json
import os
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

EXPORTS = Path(os.path.expanduser("~/Desktop/Data/salesforce-exports"))
OUT = Path(__file__).resolve().parent.parent / "data" / "salesforce_pipeline.json"
START = dt.date(2026, 4, 1)
SALES = re.compile(r"sdr|\bae\b", re.I)                       # SDR-Meeting-Set, DG-SDR Outreach (Cold), AE Prospecting, AE Internal Referral
# Not marketing either (agreed 28 Oct 2026): a test campaign, a lead-status flag and a bought LinkedIn contact list
NOT_MARKETING = {"X2-Tracking-Test-Campaign", "DG-FY27 Promoted to X2 Status", "DG-FY27 Wiza LinkedIn Exports", "DG-2025-Lantern_Records"}
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
FILES = {"opportunities": "Open Oppty Opportunities-*.xls", "touches": "Mktg#05 Multi-Attrib Opportunities-*.xls",
         "meetings": "02a Campaigns with Meetings (members)-*.xls", "campaign_ids": "All Campaigns with Campaign ID-*.xls"}


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


def read(kind):
    """The newest export of one kind, as a list of dicts, and the date in its file name."""
    found = sorted(glob.glob(str(EXPORTS / FILES[kind])), key=lambda p: re.search(r"(\d{4}-\d{2}-\d{2}-\d{2}-\d{2}-\d{2})", p).group(1))
    if not found:
        sys.exit(f"No {kind} export in {EXPORTS}")
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


def marketing(campaign):
    return bool(campaign) and not SALES.search(campaign) and not AGENCY.search(campaign) and campaign.strip() not in NOT_MARKETING


def public(campaign):
    return "Target-account campaign" if TARGET_ACCOUNTS.search(campaign) else campaign


def fiscal_quarter(d):
    """Opsera's fiscal year starts in February: FY27 Q2 is May to July 2026."""
    q = ((d.month + 10) % 12) // 3 + 1
    return f"FY{(d.year + (1 if d.month >= 2 else 0)) % 100} Q{q}"


def main():
    opps, opps_on = read("opportunities")
    opps_cover_from = read.covers_from
    touches, touches_on = read("touches")
    meets, meets_on = read("meetings")
    ids, _ = read("campaign_ids")
    id_names = {r["Campaign ID"][:15]: r["Campaign Name"] for r in ids if r.get("Campaign ID")}
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

    BUCKETS = ("sourced", "influenced", "agency", "nocontact")
    by_month = collections.defaultdict(lambda: {b: [0, 0] for b in BUCKETS})
    by_day = collections.defaultdict(lambda: {b: [0, 0] for b in BUCKETS})   # for the period switch
    by_campaign = collections.defaultdict(lambda: [0, 0])
    counted = no_contact = unknown_join = dropped_by_window = 0
    review = []
    for o in opps:
        created = day(o["Created Date"])
        if not created or created < START or "lost" in o["Stage"].lower():
            continue
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
        if not bucket:
            dropped_by_window += had_marketing
            if not has_contact:
                bucket, campaign = "nocontact", ""
        sources = {"marketing" for c in [primary, *others] if marketing(c)} | {"booking agency" for c in [primary, *others] if AGENCY.search(c)} | \
                  {"SDR or AE outreach" for c in [primary, *others] if c and SALES.search(c)}
        reasons = ([f"Joined {', '.join(sorted(public(c) for c in near))} 91 to {NEAR_DAYS} days before the deal"] if near else []) + \
                  ([f"Matches more than 1 source: {', '.join(sorted(sources))}"] if len(sources) > 1 else [])
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

    out = {
        "source": "Salesforce reports",
        "exports": {"opportunities": opps_on, "campaign_touches": touches_on, "meetings": meets_on},
        "opportunities_cover_from": opps_cover_from or START.isoformat(),
        "opportunities_from": min(day(o["Created Date"]) for o in opps if o["Created Date"]).isoformat(),
        "opportunities_to": max(day(o["Created Date"]) for o in opps if o["Created Date"]).isoformat(),
        "share_without_contact_pct": round(no_contact / counted * 100) if counted else None,
        "window_days": WINDOW_DAYS, "deals_join_date_unknown": unknown_join, "deals_left_out_by_window": dropped_by_window,
        "months": [{"month": k, "quarter": fiscal_quarter(day(f"{k[5:]}/01/{k[:4]}")),
                    **{f"{b}_{w}": v[b][i] for b in BUCKETS for i, w in enumerate(("deals", "value")) if (b, w) != ("nocontact", "value")}}
                   for k, v in sorted(by_month.items())],
        "days": [{"date": k, **{f"{b}_{w}": v[b][i] for b in BUCKETS for i, w in enumerate(("deals", "value")) if (b, w) != ("nocontact", "value")}}
                 for k, v in sorted(by_day.items())],   # no contact linked: count only, never the value (agreed 29 Oct 2026)
        "campaigns": [{"bucket": b, "campaign": c, "deals": v[0], "value": v[1]} for (b, c), v in sorted(by_campaign.items(), key=lambda x: -x[1][1])],
        "to_review": sorted(review, key=lambda r: r["date"]),
        "event_meetings": [{"key": k, "campaign": c, "people": len(event_people[c]),
                            "held": sum(1 for o in event_people[c].values() if o == "Meeting Held")} for k, c in EVENT_CAMPAIGNS.items()],
        "meetings": {"since": START.isoformat(),
                     "days": [{"date": k, "people": sum(v.values()), "outcomes": dict(v)} for k, v in sorted(meet_days.items())],
                     "months": [{"month": k, "people": sum(v.values()), "outcomes": dict(v)} for k, v in sorted(meet_months.items())],
                     "campaigns": [{"campaign": c, "people": n} for c, n in meet_campaigns.most_common()],
                     "people": len(people)},
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    s, i, a, n = (sum(m[f"{b}_deals"] for m in out["months"]) for b in BUCKETS)
    print(f"Wrote {OUT.name}: {counted} open and won opportunities since {START}, {s} marketing sourced, {i} influenced, {a} booking agency, "
          f"{n} no contact linked, {len(review)} to review, "
          f"{out['share_without_contact_pct']}% with no contact, {unknown_join} counted without a known join date, {dropped_by_window} left out by the "
          f"{WINDOW_DAYS}-day rule; {len(people)} people with a campaign-influenced meeting; event meetings "
          + ", ".join(f"{e['key']} {e['people']}" for e in out["event_meetings"]))


if __name__ == "__main__":
    main()
