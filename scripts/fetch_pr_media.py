"""Keep data/pr_media.json, the PR and media tab: every article, interview, byline, podcast and press
mention of Opsera from 1 Jul 2026, plus every byline, interview and podcast by Kumar or anyone else at
Opsera from any time. One row each, with the date, outlet, title, link, type, topic, the Opsera people
named, and the PR agency that placed it. Agreed with Purav on 4 Nov 2026.

Rows already in the file stay. Each run adds new ones from:
- Google News and Google web search, read with Apify (needs APIFY_TOKEN, a GitHub secret)
- our newsroom (opsera.ai/newsroom): its press releases from 1 Jul 2026
- a PR agency's list, if one is dropped into ~/Desktop/Data/pr-agency as .csv or .xlsx
  with the columns Date, Outlet, Title, Link, Type and Quoted (Quoted can be blank); the file's name,
  or an Agency column, fills "Placed by". A row already found gets its "Placed by" from the list.
- SamsonPR's own tracker, saved as SamsonPR-tracker-*.xlsx in the same folder (agreed 6 Nov 2026): every piece in its
  "Coverage Tracker 2026" tab is placed by SamsonPR, with its readership from "Circulation or UVM". Its "Account
  Activities" tab gives data/pr_opportunities.json: outlet, ask, status and deadline, with no reporter or customer names.
- A few rows added by hand (MANUAL): briefings, partnerships and pieces still in draft. They show in the list but
  don't count as placements. Nor do pages marked by hand as naming Opsera only in passing (PASSING).

A found page counts only if its own text says Opsera. Job posts, directory and review listings,
company profiles, social media and our own sites are left out. Before 1 Jul 2026 only bylines, interviews
and podcasts with an Opsera person count. A press release that runs on several sites is one row per site,
each typed "Press release"; the page shows it once with the sites it ran on.

    python3 scripts/fetch_pr_media.py                   # Apify and the newsroom (the Monday run)
    python3 scripts/fetch_pr_media.py --agency          # also adds the PR agency lists (run on this Mac)
    python3 scripts/fetch_pr_media.py --from found.json # checks results saved from Apify instead of running it
"""
import csv
import datetime as dt
import html
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

import requests

START = "2026-07-01"
OUT = Path(__file__).resolve().parent.parent / "data" / "pr_media.json"
AGENCY = Path.home() / "Desktop" / "Data" / "pr-agency"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 Chrome/124 Safari/537.36"}
MAX_CHARGE_USD = 1   # each weekly run costs a few cents; this caps a run that goes wrong
TYPES = ("Press release", "Byline", "Interview", "Podcast", "Mention", "Briefing", "Partnership", "Passing mention")
OPPORTUNITIES = Path(__file__).resolve().parent.parent / "data" / "pr_opportunities.json"
# Added by hand (agreed 6 Nov 2026). Not placements: a briefing, a partnership listing and a piece still in draft.
MANUAL = [
    {"date": "2026-10-16", "outlet": "Reuters", "title": "Briefing with Kumar Chivukula", "link": "", "type": "Briefing",
     "topic": "Other", "quoted": "Kumar Chivukula", "placed_by": "SamsonPR", "found_by": "SamsonPR tracker, Account Activities"},
    {"date": "2026-11-06", "outlet": "Forbes", "title": "PHP2Shell byline", "link": "", "type": "Byline", "status": "In draft",
     "topic": "Security", "quoted": "", "placed_by": "", "found_by": "Added by hand"},
]
PARTNERSHIP = {"https://x.ai/news/partnernetworkannouncement", "https://x.ai/partners/marketplace"}   # the xAI partner network
# Pages that name Opsera only in passing: kept in the list, not placements (Purav, 6 Nov 2026)
PASSING = {
    "https://www.rfp.wiki/it-security/service-orchestration-and-automation-platforms/puppet/opsera",
    "https://www.clearhavenpartners.com/news-and-insights/you-cant-sprint-your-way-to-agentic-engineering",
    "https://www.news.aakashg.com/p/pm-to-product-builder-roadmap",
    "https://cognitiveworld.com/articles/2026/9/1/sounds-right-points-wrong-what-expert-judgment-is-actually-worth-when-ai-makes-everything-seem-easy",
}
# One short ask per outlet in SamsonPR's Account Activities tab, written without reporter or customer names
ASKS = {"CIO News/TechTarget": ("Follow-up questions on a customer's modernization story, with Kumar's view first", False),
        "CIO": ("Story on whether faster AI development brings business value, with a customer engineering leader", False),
        "Morning Brew": ("Missed an earlier story on deadline; the reporter wants to talk with Kumar for a later one", True),
        "Reuters": ("Follow-up quotes from Kumar after the 16 Oct briefing, sent in a doc", False),
        "TFiR": ("Video for The Agentic Enterprise series on running AI agents in production", False),
        "AITech365": ("Written Q&A with Kumar, draft ready for review", False),
        "The Information": ("The reporter wants to speak with Kumar", False)}
# Opsera people: named in the "Opsera people" column when a piece is by them or quotes them (shown by name, agreed 4 Nov 2026)
PEOPLE = ["Kumar Chivukula", "Patty Hatter", "Chandra Ranganathan", "Gilbert Martin", "Vishnu Vasudevan", "Ryan Cartwright"]
NAMES = {"Patricia Hatter": "Patty Hatter"}
NEWS_QUERIES = ["Opsera", '"Kumar Chivukula"', '"Patty Hatter" Opsera']
WEB_QUERIES = ['"Opsera" -site:opsera.ai -site:linkedin.com -site:indeed.com -site:glassdoor.com',
               '"Kumar Chivukula" Opsera -site:opsera.ai -site:linkedin.com', '"Opsera" podcast', '"Opsera" interview']
PEOPLE_QUERIES = ['"by Kumar Chivukula"', '"Kumar Chivukula" interview OR podcast', '"Patty Hatter" Opsera interview OR podcast',
                  'site:forbes.com/councils "Kumar Chivukula"']   # all time, for bylines, interviews and podcasts
INTERVIEW_SITES = ("techstrong.tv",)   # video interview shows
TOPICS = [   # first match wins, from the headline; an agency list's Topic column wins over this
    ("Salesforce", r"salesforce|agentforce"),
    ("Forge", r"\bforge\b|software factory"),
    ("Modernization", r"moderni[sz]|legacy|migration|cobol|mainframe"),
    ("Security", r"secur|vulnerab|appsec|devsecops|log4j|secrets"),
    ("Unified Insights", r"unified insights|\bdora\b|developer productivity|engineering metrics|measur|engineering intelligence"),
    ("AI-SDLC", r"ai-sdlc|ai sdlc|ai coding|ai-generated|agentic|ai agents?\b|generative ai|\bai\b"),
]
WIRES = ("prnewswire.com", "globenewswire.com", "businesswire.com", "accesswire.com", "einpresswire.com")
LEFT_OUT = ("opsera.ai", "opsera.io", "linkedin.com", "facebook.com", "x.com", "twitter.com", "instagram.com", "reddit.com",
            "youtube.com", "indeed.com", "glassdoor.", "tracxn.com", "rocketreach.co", "dealroom.co", "crunchbase.com", "zoominfo.com",
            "f6s.com", "g2.com", "capterra.com", "trustradius.com", "itechguides.com", "sourceforge.net", "github.com",
            "marketplace.microsoft.com", "aws.amazon.com", "appexchange.salesforce.com", "bizups.info", "wellfound.com", "builtin.com",
            "pitchbook.com", "cbinsights.com", "owler.com", "apollo.io", "signalhire.com", "lusha.com", "theorg.com",
            "opseragovernance.com")   # opseragovernance.com is another company's site
# Checked by hand and left out, so the weekly run doesn't add them again: a podcast's list of episodes (the episode itself is a row)
STRAIGHT = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})   # straight quotes, as on the rest of the page
NOT_A_PIECE = {"https://firehorse.ai/podcast"}
SIDE_PARTS = re.compile(r"<(aside|nav|footer)\b.*?</\1>|<(ul|ol|div|section)\b[^>]*class=\"[^\"]*(related|sidebar|widget)[^\"]*\".*?</\2>", re.S | re.I)
JOB_WORDS = re.compile(r"\b(job|jobs|careers?|hiring|salary|salaries|vacanc|openings?)\b", re.I)
OUTLETS = {"prnewswire.com": "PR Newswire", "globenewswire.com": "GlobeNewswire", "finance.yahoo.com": "Yahoo Finance",
           "markets.businessinsider.com": "Business Insider", "morningstar.com": "Morningstar", "sdtimes.com": "SD Times",
           "devopsdigest.com": "DEVOPSdigest", "aithority.com": "AiThority", "informationweek.com": "InformationWeek",
           "leaddev.com": "LeadDev", "news.aakashg.com": "Product Growth", "cognitiveworld.com": "Cognitive World", "manilatimes.net": "The Manila Times", "devops.com": "DevOps.com"}


def stop(msg):
    print(f"\nSTOPPED: {msg}", file=sys.stderr)
    sys.exit(1)


def site(url):
    return urlparse(url).netloc.lower().removeprefix("www.")


def outlet_for(url, given=""):
    s = site(url)
    return next((v for k, v in OUTLETS.items() if s == k or s.endswith("." + k)), None) or given or s


def left_out(url, title):
    s = site(url)
    return any(s == d or s.endswith("." + d) or d.endswith(".") and s.startswith(d) for d in LEFT_OUT) or bool(JOB_WORDS.search(title or ""))


def read_page(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code in (202, 429, 503):   # a busy or checking site: one more try after a pause
            time.sleep(10)
            r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException:
        return None, None, None, {}
    if r.status_code != 200:
        return None, None, None, {}
    m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', r.text) or \
        re.search(r'(?:article:published_time|pubdate|publish-date)"\s+content="(\d{4}-\d{2}-\d{2})', r.text)
    t = re.search(r'<meta property="og:title" content="([^"]*)"', r.text)
    d = re.search(r'<meta (?:property="og:description"|name="description") content="([^"]*)"', r.text)
    authors = re.findall(r'"author"\s*:\s*(?:\[\s*)?\{[^}]*?"name"\s*:\s*"([^"]+)"', r.text)
    # related-links lists, sidebars and footers are left out, so a link to an old piece doesn't count as a mention
    text = SIDE_PARTS.sub(" ", re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S))
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", text)))
    return text, (m.group(1) if m else None), (html.unescape(t.group(1)).strip() if t else None), \
        {"summary": html.unescape(d.group(1)) if d else "", "authors": " ".join(authors)}


def words(title):
    return " ".join(re.findall(r"[a-z0-9]+", (title or "").lower()))


def same_release(title, release_titles):
    """The same press release on another site: the same title, word for word. A news story with its own headline stays a mention."""
    return bool(words(title)) and words(title) in release_titles


def kind(url, title, text, release_titles, authors=""):
    t = (title or "").lower()
    if site(url).endswith(WIRES) or same_release(title, release_titles) or re.search(r"/PRNewswire/|GLOBE NEWSWIRE|Business Wire\)", text or ""):
        return "Press release"
    if "podcast" in t or "podcast" in url.lower():
        return "Podcast"
    if re.search(r"\binterview\b|\bq&a\b", t) or site(url).endswith(INTERVIEW_SITES):
        return "Interview"
    by = "|".join(PEOPLE)
    if any(p in authors for p in PEOPLE) or re.search(rf"\bBy\s?({by})\b|Written by\s?({by})", text or ""):
        return "Byline"
    return "Mention"


def topic(title):
    return next((name for name, rule in TOPICS if re.search(rule, (title or "").lower())), "Other")


def quoted(text):
    found = [p for p in PEOPLE if p in (text or "")] + [v for k, v in NAMES.items() if k in (text or "")]
    return ", ".join(dict.fromkeys(found))


def run_apify(actor, payload, token):
    r = requests.post(f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items",
                      params={"token": token, "maxTotalChargeUsd": MAX_CHARGE_USD, "clean": "true"}, json=payload, timeout=600)
    if r.status_code not in (200, 201):
        stop(f"Apify {actor} returned {r.status_code}.")
    return r.json()


def found_by_apify(token):
    """Google News and Google web search results as {title, link, outlet, date}."""
    out = []
    for q in NEWS_QUERIES:
        for it in run_apify("lhotanova~google-news-scraper", {"query": q, "language": "US:en", "dateFrom": START, "maxItems": 200,
                                                              "fetchArticleDetails": True, "fetchArticlePage": False}, token):
            out.append({"title": it.get("title"), "link": it.get("loadedUrl") or it.get("link"), "outlet": it.get("source"),
                        "date": (it.get("publishedAt") or "")[:10]})
    for queries, after in ((WEB_QUERIES, START), (PEOPLE_QUERIES, None)):
        payload = {"queries": "\n".join(queries), "maxPagesPerQuery": 3 if after else 1, "countryCode": "us", "saveHtmlToKeyValueStore": False}
        if after:
            payload["afterDate"] = after
        for page in run_apify("apify~google-search-scraper", payload, token):
            for it in page.get("organicResults") or []:
                out.append({"title": it.get("title"), "link": it.get("url"), "outlet": it.get("websiteTitle"), "date": (it.get("date") or "")[:10]})
    return out


def found_in_newsroom():
    """Our own press releases from 1 Jul 2026: newsroom items marked "Press release"."""
    try:
        r = requests.get("https://opsera.ai/newsroom", headers=HEADERS, timeout=60)
    except requests.RequestException:
        return []
    text = html.unescape(re.sub(r"<script.*?</script>|<style.*?</style>", " ", r.text, flags=re.S))
    lines = [l.strip() for l in re.sub(r"<[^>]+>", "\n", text).split("\n") if l.strip()]
    links = {html.unescape(t).strip(): u for u, t in re.findall(r'href="(/newsroom/[^"]+)"[^>]*>\s*(?:<[^>]+>\s*)*([^<]{10,})', r.text)}
    out = []
    for i, l in enumerate(lines):
        m = re.fullmatch(r"(\d{1,2}) (January|February|March|April|May|June|July|August|September|October|November|December) (\d{4})", l)
        if m and i >= 2 and lines[i - 1] == "Press release":
            date = dt.datetime.strptime(l, "%d %B %Y").date().isoformat()
            title = next((lines[j] for j in range(i - 2, max(i - 5, -1), -1) if lines[j] in links), None)
            if title and date >= START:
                out.append({"title": title, "link": "https://opsera.ai" + links[title], "outlet": "Opsera newsroom", "date": date,
                            "type": "Press release", "own": True})
    return out


def key(x):
    """Rows are kept by link; a row with no link (a briefing, a draft) by its date, outlet and title."""
    return x["link"] or f"{x['date']} {x['outlet']} {x['title']}"


def samson_tracker():
    """SamsonPR's tracker: coverage rows (placed by SamsonPR, with readership) and open and missed opportunities."""
    found = sorted(AGENCY.glob("SamsonPR-tracker-*.xlsx")) if AGENCY.exists() else []
    if not found:
        return [], None
    import openpyxl
    wb = openpyxl.load_workbook(found[-1])   # the newest, by the date in its name
    ws = wb["Coverage Tracker 2026"]
    rows, head = [], None
    for r in ws.iter_rows():
        vals = [c.value for c in r]
        if head is None:
            if "Date" in vals and "Publication" in vals:
                head = [str(v or "").strip() for v in vals]
            continue
        rec = dict(zip(head, r))
        when, pub, cell = rec["Date"].value, rec["Publication"].value, rec["Hyperlinked Headline"]
        if not (when and pub and cell.value):
            continue
        reach = rec["Circulation or UVM"].value
        rows.append({"date": when.date().isoformat() if hasattr(when, "date") else str(when)[:10], "outlet": str(pub).strip(),
                     "title": str(cell.value).strip().translate(STRAIGHT), "link": cell.hyperlink.target if cell.hyperlink else "",
                     "readership": int(reach) if isinstance(reach, (int, float)) else None, "placed_by": "SamsonPR",
                     "found_by": f"SamsonPR tracker ({found[-1].name})"})
    ops, part, seen = [], None, 0
    for r in wb["Account Activities"].iter_rows(values_only=True):   # columns: outlet, details, link, timing, status
        first = str(r[0] or "").strip()
        if first == "Media Opportunities":   # the 1st is the tab's title; the outlets follow the 2nd
            seen += 1
            part = "media" if seen == 2 else None
        elif first == "Media Outreach":
            part = None
        elif part == "media" and first:
            outlet = first.split("|")[0].strip().rstrip(".")
            ask, missed = ASKS.get(outlet, ("New: see SamsonPR's tracker", False))
            if outlet not in ASKS:
                print(f"  SamsonPR tracker: no short ask written yet for {outlet}")
            when = r[3]
            if hasattr(when, "date"):
                deadline = when.date().isoformat()
            else:
                deadline = re.sub(r"(?i)^(deadline|requested responses before)\s*", "", str(when or "").strip()) or "None given"
                deadline = re.sub(r"^([A-Z][a-z]{2}) (\d{1,2})$", r"\2 \1", deadline).replace("open", "Open")
            ops.append({"outlet": outlet, "ask": ask, "status": "Missed" if missed else str(r[4] or "Not given").strip(),
                        "follow_up": str(r[4] or "").strip(), "deadline": deadline})
    return rows, {"source": f"SamsonPR tracker, Account Activities ({found[-1].name})", "read": dt.date.today().isoformat(), "items": ops}


def agency_rows():
    """Rows from the PR agency lists, each with "Placed by": the Agency column, or the file's name."""
    rows = []
    for f in sorted(AGENCY.glob("*")) if AGENCY.exists() else []:
        if f.name.startswith("SamsonPR-tracker-"):
            continue   # read by samson_tracker()
        if f.suffix.lower() == ".csv":
            with f.open(newline="", encoding="utf-8-sig") as fh:
                recs = list(csv.DictReader(fh))
        elif f.suffix.lower() == ".xlsx":
            import openpyxl
            ws = openpyxl.load_workbook(f, read_only=True, data_only=True).active
            vals = list(ws.values)
            recs = [dict(zip([str(h or "").strip() for h in vals[0]], r)) for r in vals[1:]]
        else:
            continue
        for r in recs:
            r = {k.strip().lower(): v for k, v in r.items() if k}
            date = r.get("date")
            date = date.date().isoformat() if hasattr(date, "date") else str(date or "").strip()[:10]
            if not (r.get("link") and r.get("title") and re.fullmatch(r"\d{4}-\d{2}-\d{2}", date)):
                print(f"  {f.name}: skipped a row without a date (YYYY-MM-DD), title and link: {r}")
                continue
            t = str(r.get("type") or "").strip().capitalize()
            agency = str(r.get("agency") or re.sub(r"[-_]+", " ", f.stem)).strip()
            rows.append({"date": date, "outlet": str(r.get("outlet") or site(r["link"])).strip(), "title": str(r["title"]).strip(),
                         "link": str(r["link"]).strip(), "type": t if t in TYPES else "Mention", "topic": str(r.get("topic") or "").strip()
                         or topic(str(r["title"])), "quoted": str(r.get("quoted") or "").strip(), "placed_by": agency,
                         "found_by": f"PR agency list ({f.name})"})
    return rows


def main():
    have = json.loads(OUT.read_text()) if OUT.exists() else {"items": []}
    items = {key(x): x for x in have["items"]}
    release_titles = {words(x["title"]) for x in items.values() if x["type"] == "Press release"}

    if "--from" in sys.argv:
        found = json.loads(Path(sys.argv[sys.argv.index("--from") + 1]).read_text())
        how = "Apify (saved results)"
    else:
        token = os.environ.get("APIFY_TOKEN")
        if not token:
            stop("The APIFY_TOKEN secret is missing. Add it in GitHub under Settings > Secrets and variables > Actions.")
        found = found_by_apify(token)
        how = "Apify, Google News and Google search"
    found += found_in_newsroom()
    found.sort(key=lambda c: not (c.get("own") or site(c.get("link") or "").endswith(WIRES)))   # press releases first, so their pickups match them

    added, skipped = 0, {"left out": 0, "no Opsera on the page": 0, "before 1 Jul 2026 and not by an Opsera person": 0, "page wouldn't open": 0}
    for c in found:
        link = (c.get("link") or "").split("#")[0]
        if not link or link in items or link in NOT_A_PIECE:
            continue
        if not (c.get("own") or c.get("checked_by_hand")) and left_out(link, c.get("title")):
            skipped["left out"] += 1
            continue
        text, page_date, page_title, extra = read_page(link)
        if text is None and c.get("checked_by_hand"):   # opened by hand in a browser: the site blocks scripts
            text, extra = "", {}
        elif text is None:
            skipped["page wouldn't open"] += 1
            continue
        if not c.get("checked_by_hand") and "Opsera" not in text:
            skipped["no Opsera on the page"] += 1
            continue
        date = c.get("date") if c.get("checked_by_hand") and c.get("date") else page_date or c.get("date") or ""
        title = c.get("title") or ""
        if (not title or title.endswith(("...", "\u2026"))) and page_title:   # search results cut long titles short
            title = re.sub(r"\s+[|\-\u2013\u2014]\s+[^|\u2013\u2014]{2,40}$", "", page_title)   # drop " | Outlet" at the end
        title = title.translate(STRAIGHT)
        t = c.get("type") or kind(link, title, text, release_titles, extra.get("authors", ""))
        people = c.get("quoted") or quoted(f"{text} {extra.get('authors', '')}")
        if not date or (date < START and not (t in ("Byline", "Interview", "Podcast") and people)):
            skipped["before 1 Jul 2026 and not by an Opsera person"] += 1
            continue
        items[link] = {"date": date, "outlet": outlet_for(link, c.get("outlet") or ""), "title": title or link, "link": link,
                       "type": t, "topic": c.get("topic") or topic(title), "quoted": people, "placed_by": "",
                       "found_by": "Opsera newsroom" if c.get("own") else c.get("found_by") or how}
        if t == "Press release":
            release_titles.add(words(title))
        added += 1
        print(f"  added {date} {t}: {items[link]['outlet']}, {items[link]['title'][:70]}")

    if "--agency" in sys.argv:
        coverage, ops = samson_tracker()
        for r in coverage:
            have_it = items.get(r["link"])
            if have_it:   # already found: the tracker says who placed it and its readership
                have_it["placed_by"], have_it["readership"] = r["placed_by"], r["readership"]
                continue
            r["outlet"] = outlet_for(r["link"], r["outlet"]) if r["link"] else r["outlet"]
            r["type"] = "Press release" if same_release(r["title"], release_titles) else "Mention"
            r["topic"], r["quoted"] = topic(r["title"]), ""
            if r["link"]:
                text, _, _, extra = read_page(r["link"])
                r["quoted"] = quoted(f"{text or ''} {extra.get('authors', '') if extra else ''}")
            items[key(r)] = r
            added += 1
            print(f"  added from SamsonPR's tracker: {r['date']} {r['type']}: {r['outlet']}, {r['title'][:70]}")
        if ops:
            OPPORTUNITIES.write_text(json.dumps(ops, indent=1) + "\n")
            print(f"  SamsonPR opportunities: {len(ops['items'])}")
        for r in agency_rows():
            if r["link"] in items:   # already found: the list only says who placed it
                items[r["link"]]["placed_by"] = r["placed_by"]
            elif r["date"] >= START or (r["type"] in ("Byline", "Interview", "Podcast") and r["quoted"]):
                items[r["link"]] = r
                added += 1
                print(f"  added from the PR agency list: {r['date']} {r['type']}: {r['outlet']}, {r['title'][:70]}")

    for m in MANUAL:
        items.setdefault(key(m), dict(m))
    for x in items.values():   # rows from before these columns existed
        x.setdefault("placed_by", "")
        if x["link"] in PARTNERSHIP:
            x["type"] = "Partnership"
        if x["link"] in PASSING:
            x["type"] = "Passing mention"
        if not x["found_by"].startswith(("PR agency", "Added by hand", "SamsonPR")):
            x["topic"] = topic(x["title"])
    for x in items.values():   # a pickup found before its press release
        if x["type"] == "Mention" and x["found_by"] != "Checked by hand" and same_release(x["title"], release_titles):
            x["type"] = "Press release"
    rows = sorted(items.values(), key=lambda x: (x["date"], x["outlet"]), reverse=True)
    OUT.write_text(json.dumps({"source": "Google News and Google search read with Apify, our newsroom, and PR agency lists",
                               "start_date": START, "checked": dt.date.today().isoformat(), "items": rows}, indent=1) + "\n")
    print(f"PR and media: {len(rows)} rows, {added} new. Not added: " + ", ".join(f"{v} {k}" for k, v in skipped.items()))


if __name__ == "__main__":
    main()
