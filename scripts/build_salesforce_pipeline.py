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
NOT_MARKETING = {"X2-Tracking-Test-Campaign", "DG-FY27 Promoted to X2 Status", "DG-FY27 Wiza LinkedIn Exports"}
# Counted as marketing for now, shown with a flag until the credit rule is confirmed
CHECKING = {"DG-2025-Lantern_Records": "under review"}
TARGET_ACCOUNTS = re.compile(r"\b(abm|abx|microsite)\b", re.I)
FILES = {"opportunities": "Open Oppty Opportunities-*.xls", "touches": "Mktg#05 Multi-Attrib Opportunities-*.xls",
         "meetings": "02a Campaigns with Meetings (members)-*.xls"}


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
    return bool(campaign) and not SALES.search(campaign) and campaign.strip() not in NOT_MARKETING


def public(campaign):
    return "Target-account campaign" if TARGET_ACCOUNTS.search(campaign) else campaign


def fiscal_quarter(d):
    """Opsera's fiscal year starts in February: FY27 Q2 is May to July 2026."""
    q = ((d.month + 10) % 12) // 3 + 1
    return f"FY{(d.year + (1 if d.month >= 2 else 0)) % 100} Q{q}"


def main():
    opps, opps_on = read("opportunities")
    touches, touches_on = read("touches")
    meets, meets_on = read("meetings")

    touched = collections.defaultdict(set)   # opportunity -> campaigns it touched (multi-attribution export)
    for t in touches:
        if t.get("Campaign Name"):
            touched[t["Opportunity Name"]].add(t["Campaign Name"])

    by_month = collections.defaultdict(lambda: {"sourced": [0, 0], "influenced": [0, 0]})
    by_campaign = collections.defaultdict(lambda: [0, 0])
    counted = no_contact = 0
    for o in opps:
        created = day(o["Created Date"])
        if not created or created < START or "lost" in o["Stage"].lower():
            continue
        counted += 1
        no_contact += not o.get("Primary Contact")
        amount = round(float(o.get("Amount") or 0))
        primary = o.get("Primary Campaign Source", "")
        others = [o.get("Attrib First Campaign", ""), o.get("Attrib Last Campaign", ""), *sorted(touched.get(o["Opportunity Name"], ()))]
        if marketing(primary):
            bucket, campaign = "sourced", primary
        else:
            campaign = next((c for c in others if marketing(c)), "")
            bucket = "influenced" if campaign else None
        if not bucket:
            continue   # sales only: not written
        x = by_month[created.strftime("%Y-%m")][bucket]
        x[0] += 1
        x[1] += amount
        c = by_campaign[(bucket, public(campaign))]
        c[0] += 1
        c[1] += amount

    people = {}   # one row per person: their meeting date and the marketing campaigns they joined before it
    for m in meets:
        when, joined, campaign = day(m["Date 3 - Meeting Set"]), day(m["Member First Associated Date"]), m.get("Campaign Name", "")
        if not when or when < START or not joined or joined > when or not marketing(campaign):
            continue
        p = people.setdefault((m.get("Email") or "").lower() or id(m), {"date": when, "outcome": m.get("Meeting Outcome") or "Not recorded", "campaigns": set()})
        p["campaigns"].add(public(campaign))
    meet_months = collections.defaultdict(collections.Counter)
    meet_campaigns = collections.Counter()
    for p in people.values():
        meet_months[p["date"].strftime("%Y-%m")][p["outcome"]] += 1
        for c in p["campaigns"]:
            meet_campaigns[c] += 1

    out = {
        "source": "Salesforce reports",
        "exports": {"opportunities": opps_on, "campaign_touches": touches_on, "meetings": meets_on},
        "opportunities_from": min(day(o["Created Date"]) for o in opps if o["Created Date"]).isoformat(),
        "opportunities_to": max(day(o["Created Date"]) for o in opps if o["Created Date"]).isoformat(),
        "share_without_contact_pct": round(no_contact / counted * 100) if counted else None,
        "months": [{"month": k, "quarter": fiscal_quarter(day(f"{k[5:]}/01/{k[:4]}")),
                    "sourced_deals": v["sourced"][0], "sourced_value": v["sourced"][1],
                    "influenced_deals": v["influenced"][0], "influenced_value": v["influenced"][1]} for k, v in sorted(by_month.items())],
        "campaigns": [{"bucket": b, "campaign": c, "deals": v[0], "value": v[1], "flag": CHECKING.get(c, "")} for (b, c), v in sorted(by_campaign.items(), key=lambda x: -x[1][1])],
        "meetings": {"months": [{"month": k, "people": sum(v.values()), "outcomes": dict(v)} for k, v in sorted(meet_months.items())],
                     "campaigns": [{"campaign": c, "people": n, "flag": CHECKING.get(c, "")} for c, n in meet_campaigns.most_common()],
                     "people": len(people)},
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    s = sum(m["sourced_deals"] for m in out["months"]); i = sum(m["influenced_deals"] for m in out["months"])
    print(f"Wrote {OUT.name}: {counted} open and won opportunities since {START}, {s} marketing sourced, {i} influenced, "
          f"{out['share_without_contact_pct']}% with no contact; {len(people)} people with a campaign-influenced meeting")


if __name__ == "__main__":
    main()
