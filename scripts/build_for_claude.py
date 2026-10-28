"""Write the dashboard's numbers as small plain CSV files plus a guide, under /for-claude, so anyone can
paste the dashboard link into Claude (or another AI assistant) and ask about any tab, page or campaign.

Reads only the files in /data that the dashboard itself shows, so every number here is one the page shows.
Makes no calls to Google, HubSpot, LinkedIn, YouTube or Apify. Runs every Monday after the pulls:
    python3 scripts/build_for_claude.py

Same rules as the dashboard: sources are never added together, deals exist only as weekly and monthly
totals, page addresses are cut at "?" and "@", and no names or emails are written beyond what the page shows
(LinkedIn post titles, page titles and campaign names, as on the dashboard).
Agreed with Purav on 27 Oct 2026.
"""
import collections
import csv
import datetime as dt
import io
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = ROOT / "for-claude"
SITE = "https://puravbhandari-gif.github.io/opsera-analytics-dashboard"
MAX_BYTES = 45_000   # each file stays small enough for an AI assistant to read in one go (about 15,000 tokens)
ASSET_PAGES = ("/resources/report/", "/resources/white-papers/", "/resources/ebooks/", "/resources/comparison-guides/")
LEAD_LINES = [("demo", "demo_requests"), ("contact", "contact_forms"), ("gartner_offer", "gartner_offer_forms"),
              ("events", "event_signups"), ("other", "other_forms")]
CHANNELS = [("all", "All channels"), ("search", "Google search"), ("linkedin", "LinkedIn"), ("email", "Email"),
            ("events", "Events"), ("paid", "Paid ads"), ("ai", "AI tools"), ("youtube", "YouTube"), ("direct", "Direct")]
AI_TOOLS = {"chatgpt": "ChatGPT", "gemini": "Gemini", "perplexity": "Perplexity", "claude": "Claude", "copilot": "Copilot", "other": "Other AI tools"}
GA_GROUPS = {"Direct": "Direct (typed in, or unknown)", "Organic Search": "Search engines (mostly Google)", "Referral": "Other websites",
             "Organic Social": "Social media (LinkedIn and others)", "AI Assistant": "AI tools (ChatGPT, Gemini, Perplexity)",
             "Unassigned": "Unlabelled", "Paid Search": "Paid search ads", "Paid Social": "Paid social ads",
             "Organic Shopping": "Shopping search", "Organic Video": "Video sites", "Display": "Display ads", "Cross-network": "Google ad network"}

PAGE_SECTIONS = [("main", "Main pages 1 level deep (the homepage, /demo, /pricing and the like)"), ("blog", "Pages under /blog/"),
                 ("resources", "Pages under /resources/"), ("knowledge_base", "Pages under /knowledge-base/"),
                 ("other", "Pages in other sections such as /newsroom/ and /changelog/")]


def section_of(page):
    for prefix, key in (("/blog/", "blog"), ("/resources/", "resources"), ("/knowledge-base/", "knowledge_base")):
        if page.startswith(prefix):
            return key
    return "main" if page.count("/") <= 1 else "other"


day = dt.date.fromisoformat
iso = lambda d: d.isoformat()
load = lambda name: json.loads((DATA / name).read_text())
files = []   # (name, rows written, bytes, what it holds)


def stop(msg):
    print(f"\nSTOPPED: {msg}", file=sys.stderr)
    sys.exit(1)


def last_full_day_pacific(end, pulled_at):
    """The same rule as the page: Google Analytics days follow US Pacific time."""
    pt = dt.datetime.fromisoformat(pulled_at).astimezone(ZoneInfo("America/Los_Angeles")).date()
    return end if iso(pt) > end else iso(day(end) - dt.timedelta(days=1))


def periods(kind, start, last):
    """Monday-to-Sunday weeks or calendar months from start to last, each cut to that range."""
    out, s = [], day(start)
    s = s - dt.timedelta(days=s.weekday()) if kind == "week" else s.replace(day=1)
    while s <= day(last):
        e = s + dt.timedelta(days=6) if kind == "week" else (s.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
        a, b = max(s, day(start)), min(e, day(last))
        out.append({"start": iso(a), "end": iso(b), "key": iso(s), "so_far": "yes" if e > day(last) else "no"})
        s = e + dt.timedelta(days=1)
    return out


def total(rows, key, a, b, keep=lambda r: True):
    return sum((key(r) if callable(key) else r.get(key, 0)) for r in rows if a <= r["date"] <= b and keep(r))


def write(name, header, rows, about):
    """Write one CSV. A file that would be too big is split into one file per quarter by its first column."""
    def render(rs):
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(header)
        w.writerows(rs)
        return buf.getvalue()
    text = render(rows)
    if len(text.encode()) <= MAX_BYTES:
        (OUT / f"{name}.csv").write_text(text)
        files.append((f"{name}.csv", len(rows), len(text.encode()), about, name, None))
        return
    if not str(rows[0][0])[:4].isdigit():
        # a list without dates: numbered parts in the list's own order (alphabetical for page titles)
        part_rows, parts = [], []
        for r in rows:
            if part_rows and len(render(part_rows + [r]).encode()) > MAX_BYTES:
                parts.append(part_rows); part_rows = []
            part_rows.append(r)
        parts.append(part_rows)
        for n, pr in enumerate(parts, 1):
            text = render(pr)
            (OUT / f"{name}_part{n}.csv").write_text(text)
            files.append((f"{name}_part{n}.csv", len(pr), len(text.encode()), about, name, f"part {n}: {pr[0][0]} to {pr[-1][0]}"))
        return
    # too big: split by quarter, then by month, then by week, only as far as needed
    levels = [("quarter", lambda d: f"{d.year}-Q{(d.month - 1) // 3 + 1}"), ("month", lambda d: d.isoformat()[:7]),
              ("week", lambda d: (d - dt.timedelta(days=d.weekday())).isoformat())]
    def split(rs, level, label):
        if level == len(levels):
            stop(f"{name} for {label} is still too big. Split it further before publishing.")
        parts = {}
        for r in rs:
            parts.setdefault(levels[level][1](day(r[0])), []).append(r)
        for key, part_rows in sorted(parts.items()):
            part = render(part_rows)
            if len(part.encode()) > MAX_BYTES:
                split(part_rows, level + 1, key)
                continue
            (OUT / f"{name}_{key}.csv").write_text(part)
            files.append((f"{name}_{key}.csv", len(part_rows), len(part.encode()), about, name, key))
    split(rows, 0, "all")


def period_cols(p):
    return [p["start"], p["end"], p["so_far"]]


PERIOD_HEAD = ["period_start", "period_end", "period_not_finished"]


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.csv"):
        old.unlink()   # files are rebuilt from scratch each time, so a renamed or split file never lingers
    ga, leads, gsc, hub = load("analytics.json"), load("leads.json"), load("search_console.json"), load("hubspot.json")
    li, kp, yt, est, look = load("linkedin.json"), load("kumar_posts.json"), load("youtube.json"), load("linkedin_estimate.json"), load("lookup.json")
    ga_last = last_full_day_pacific(ga["end_date"], ga["pulled_at"])
    gsc_last = gsc["last_day_with_data"]
    start = ga["start_date"]
    ranges = {"Google Analytics": (start, ga_last), "Search Console": (gsc["start_date"], gsc_last), "HubSpot": (hub["start_date"], ga_last)}

    for kind in ("week", "month"):
        ps = periods(kind, start, ga_last)

        # Website visits
        email = [{"date": r["date"], "v": r["sessions"]} for r in ga["channel_daily"] if r["sessionDefaultChannelGroup"] == "Email"]
        robots = ga.get("email_robots_daily", [])
        write(f"website_visits_by_{kind}", PERIOD_HEAD + ["visits", "visits_without_email_robots", "engaged_visits", "visits_from_email"],
              [period_cols(p) + [total(ga["daily"], "sessions", p["start"], p["end"]),
                                 total(ga["daily"], "sessions", p["start"], p["end"]) - total(robots, "robots", p["start"], p["end"]),
                                 total(ga["daily"], "engagedSessions", p["start"], p["end"]), total(email, "v", p["start"], p["end"])] for p in ps],
              f"Website visits tab, by {kind}. Source: Google Analytics")
        groups = sorted({r["sessionDefaultChannelGroup"] for r in ga["channel_daily"]})
        write(f"visit_sources_by_{kind}", PERIOD_HEAD + ["came_from", "visits", "engaged_visits"],
              [period_cols(p) + [GA_GROUPS.get(g, g), total(ga["channel_daily"], "sessions", p["start"], p["end"], lambda r: r["sessionDefaultChannelGroup"] == g),
                                 total(ga["channel_daily"], "engagedSessions", p["start"], p["end"], lambda r: r["sessionDefaultChannelGroup"] == g)]
               for p in ps for g in groups if total(ga["channel_daily"], "sessions", p["start"], p["end"], lambda r: r["sessionDefaultChannelGroup"] == g)],
              f"Where visits came from (Google Analytics channel groups), by {kind}. Source: Google Analytics")

        # Leads, with asset downloads (form fills on report, white paper, ebook and comparison guide pages) shown inside other forms
        L0 = day(look["start_date"])
        look_forms = [{"date": iso(L0 + dt.timedelta(days=r[0])), "page": look["pages"][r[1]], "n": r[3]} for r in look["forms"]]
        is_asset = lambda page: (page + "/").startswith(ASSET_PAGES)
        write(f"leads_by_{kind}", PERIOD_HEAD + [c for _, c in LEAD_LINES] + ["of_which_asset_downloads"],
              [period_cols(p) + [total(leads["daily"], k, p["start"], p["end"]) for k, _ in LEAD_LINES]
               + [total(look_forms, "n", p["start"], p["end"], lambda r: is_asset(r["page"]))] for p in ps],
              f"Leads tab: form fills by kind of form, by {kind}. Source: Google Analytics (HubSpot form event)")

        # Customer journey: top numbers, then the funnel for each channel (the same steps as the page)
        booked = [r for r in hub["meetings_daily"] if r["kind"] == "booked"]
        drows = hub["deals_weekly"] if kind == "week" else hub["deals_monthly"]
        def deals_for(p, keep):
            rs = [r for r in drows if r["start"] == p["start"] and keep(r)]
            return {k: sum(r[k] for r in rs) for k in ("open_count", "open_amount", "won_count", "won_amount")}
        write(f"customer_journey_summary_by_{kind}", PERIOD_HEAD + ["demo_requests", "meetings_booked", "open_pipeline_usd", "won_usd"],
              [period_cols(p) + [total(leads["daily"], "demo", p["start"], p["end"]), total(booked, "count", p["start"], p["end"]),
                                 round(deals_for(p, lambda r: True)["open_amount"]), round(deals_for(p, lambda r: True)["won_amount"])] for p in ps],
              f"Customer journey tab, top numbers, by {kind}. Sources: Google Analytics (demo requests), HubSpot (meetings and deals)")
        funnel = []
        for p in ps:
            for ch, name in CHANNELS:
                a, b = p["start"], p["end"]
                if ch == "search":
                    b = min(b, gsc_last)   # the page ends every Google search step on Search Console's last day
                    if a > b:
                        continue
                in_ch = lambda r: ch == "all" or r["channel"] == ch
                ga_sum = lambda k: total(ga["journey"], k, a, b, lambda r: r["channel"] == ch)
                if ch == "ai":
                    contacts = total(hub["ai_contacts_daily"], "count", a, b, lambda r: r["demo"])
                else:
                    contacts = total(hub["contacts_daily"], "count", a, b, lambda r: r["line"] == "form" and in_ch(r) and r["demo"])
                d = deals_for(p, lambda r: r["demo"] and (ch == "all" or (bool(r["tool"]) if ch == "ai" else r["channel"] == ch)))
                g = [r for r in gsc["daily"] if a <= r["date"] <= b]
                funnel.append([a, b, p["so_far"] if b == p["end"] else "yes", name,
                               sum(r["times_shown"] for r in g) if ch == "search" else "", sum(r["clicks"] for r in g) if ch == "search" else "",
                               total(ga["daily"], "sessions", a, b) if ch == "all" else ga_sum("visits"), ga_sum("demo_page"), ga_sum("demo_form"),
                               contacts, total(booked, "count", a, b, lambda r: in_ch(r) and r["demo"]),
                               d["open_count"] + d["won_count"], round(d["open_amount"]), round(d["won_amount"])])
        write(f"customer_journey_funnel_by_{kind}", PERIOD_HEAD + ["channel", "google_times_shown", "google_clicks", "visits", "saw_demo_page", "filled_demo_form",
                                                                    "new_contacts", "meetings", "deals_open_or_won", "open_pipeline_usd", "won_usd"],
              funnel, f"The funnel for each channel, by {kind}. Sources: Search Console for the 2 Google columns, Google Analytics from visits to demo form, HubSpot from contacts to deals")

        # AEO: visits from AI tools and what came next, per tool
        aeo = []
        for p in ps:
            for t, name in AI_TOOLS.items():
                row = [total(ga["ai"]["daily"], k, p["start"], p["end"], lambda r: r["tool"] == t) for k in ("visits", "engaged", "demo_page", "demo_form")]
                contacts = total(hub["ai_contacts_daily"], "count", p["start"], p["end"], lambda r: r["tool"] == t and r["demo"])
                d = deals_for(p, lambda r: r["demo"] and r["tool"] == t)
                if any(row) or contacts or d["open_count"] or d["won_count"]:
                    aeo.append(period_cols(p) + [name] + row + [contacts, d["open_count"] + d["won_count"], round(d["open_amount"]), round(d["won_amount"])])
        write(f"aeo_by_{kind}", PERIOD_HEAD + ["ai_tool", "visits", "engaged_visits", "saw_demo_page", "filled_demo_form", "new_contacts",
                                               "deals_open_or_won", "open_pipeline_usd", "won_usd"],
              aeo, f"AEO tab: visits from each AI tool and what came next, by {kind}. Sources: Google Analytics, HubSpot")

        # Google search
        gp = periods(kind, gsc["start_date"], gsc_last)
        def gsc_row(p):
            g = [r for r in gsc["daily"] if p["start"] <= r["date"] <= p["end"]]
            clicks, shown = sum(r["clicks"] for r in g), sum(r["times_shown"] for r in g)
            spot = sum(r["avg_spot"] * r["times_shown"] for r in g) / shown if shown else None
            return period_cols(p) + [clicks, shown, round(clicks / shown * 100, 2) if shown else "", round(spot, 1) if spot else ""]
        write(f"google_search_by_{kind}", PERIOD_HEAD + ["clicks", "times_google_showed_us", "click_rate_pct", "average_spot_on_google"],
              [gsc_row(p) for p in gp], f"Google search tab, by {kind}. Source: Search Console. A lower average spot is better")

        # Pages and campaigns (the Look up tab's numbers)
        lp = periods(kind, look["start_date"], ga_last)
        def bucket(n, last):
            d = day(look["start_date"]) + dt.timedelta(days=n)
            if iso(d) > last:
                return None
            s = d - dt.timedelta(days=d.weekday()) if kind == "week" else d.replace(day=1)
            return iso(s)
        prange = {p["key"]: p for p in lp}
        gprange = {p["key"]: p for p in periods(kind, look["start_date"], look["gsc_last_day"])}
        pages = {}
        def prow(k, i):
            return pages.setdefault((k, i), [0, 0, 0, 0, 0, 0])
        for r in look["visits"]:
            k = bucket(r[0], ga_last)
            if k:
                v = prow(k, r[1]); v[0] += r[3]; v[1] += r[4]
        for r in look["forms"]:
            k = bucket(r[0], ga_last)
            if k:
                v = prow(k, r[1]); v[2] += r[3]
                if is_asset(look["pages"][r[1]]):
                    v[3] += r[3]
        for r in look["gsc"]:
            k = bucket(r[0], look["gsc_last_day"])
            if k:
                v = prow(k, r[1]); v[4] += r[2]; v[5] += r[3]
        rows = []
        for (k, i), v in sorted(pages.items(), key=lambda x: (x[0][0], -x[1][0], look["pages"][x[0][1]])):
            if not (v[0] or v[2] or v[4]):
                continue   # shown on Google but never clicked, visited or used: left out to keep files small
            p = prange.get(k) or gprange[k]
            rows.append([p["start"], p["end"], p["so_far"], look["pages"][i]] + v)
        # one set of files per part of the site, so each stays small
        for section, label in PAGE_SECTIONS:
            write(f"pages_by_{kind}_{section}", PERIOD_HEAD + ["page", "visits_landed_on_page", "engaged_visits", "form_fills", "of_which_asset_downloads",
                                                              "google_clicks", "google_times_shown"],
                  [r for r in rows if section_of(r[3]) == section],
                  f"{label} by {kind}. Every row has a visit, form fill or Google click. Sources: Google Analytics for visits and form fills, Search Console for Google clicks")

        camps = {}
        for r in look["campaign_visits"]:
            k = bucket(r[0], ga_last)
            if k:
                v = camps.setdefault((k, r[1]), [0, 0, 0, 0]); v[0] += r[3]; v[1] += r[4]
        for r in look["forms"]:
            k = bucket(r[0], ga_last)
            if k and r[2] >= 0:
                v = camps.setdefault((k, r[2]), [0, 0, 0, 0]); v[2] += r[3]
                if is_asset(look["pages"][r[1]]):
                    v[3] += r[3]
        write(f"campaigns_by_{kind}", PERIOD_HEAD + ["campaign", "visits", "engaged_visits", "form_fills", "of_which_asset_downloads"],
              [[prange[k]["start"], prange[k]["end"], prange[k]["so_far"], look["campaigns"][i]] + v
               for (k, i), v in sorted(camps.items(), key=lambda x: (x[0][0], -x[1][0], look["campaigns"][x[0][1]]))],
              f"Every campaign (utm_campaign) with visits or form fills, by {kind}. Source: Google Analytics")

        # LinkedIn brand (company page), LinkedIn exec (Kumar) and LinkedIn visits to the site: never added together
        co = li["company"]
        cps = periods(kind, co["start_date"], co["end_date"])
        write(f"linkedin_brand_by_{kind}", PERIOD_HEAD + ["times_seen_unpaid", "times_seen_paid", "times_seen", "clicks", "reactions", "comments",
                                                          "followers_gained", "page_views", "posts_published"],
              [period_cols(p) + [total(co["daily"], k, p["start"], p["end"]) for k in ("seen_unpaid", "seen_paid", "seen_total", "clicks_total", "reactions_total", "comments_total")]
               + [total(co["followers_daily"], "gained", p["start"], p["end"]), total(co["visitors_daily"], "views_total", p["start"], p["end"]),
                  sum(1 for x in co["posts"] if p["start"] <= x["created"] <= p["end"])] for p in cps],
              f"LinkedIn brand tab (Opsera company page), by {kind}. Source: LinkedIn exports, dates in UTC")
        ka = li["kumar_all"]
        k_last = iso(day(ka["end_date"]) - dt.timedelta(days=1)) if ka["end_date"] in ka["still_counting"] else ka["end_date"]
        write(f"linkedin_exec_by_{kind}", PERIOD_HEAD + ["times_seen", "engagements", "followers_gained"],
              [period_cols(p) + [total(ka["daily"], "seen", p["start"], p["end"]), total(ka["daily"], "engagements", p["start"], p["end"]),
                                 total(ka["followers_daily"], "gained", p["start"], p["end"])] for p in periods(kind, ka["start_date"], k_last)],
              f"LinkedIn exec tab (Kumar Chivukula's profile), by {kind}. Source: LinkedIn exports, dates in UTC")
        groups = [("company", "Company page"), ("kumar", "Kumar"), ("untagged", "Untagged")]
        write(f"linkedin_visits_to_site_by_{kind}", PERIOD_HEAD + ["from", "visits", "engaged_visits"],
              [period_cols(p) + [name, total(ga["linkedin"]["daily"], "visits", p["start"], p["end"], lambda r: r["group"] == g),
                                 total(ga["linkedin"]["daily"], "engaged", p["start"], p["end"], lambda r: r["group"] == g)] for p in ps for g, name in groups],
              f"Visits to opsera.ai from LinkedIn: company page links, Kumar's links and untagged, by {kind}. Source: Google Analytics")
        est_last = last_full_day_pacific(est.get("end_date") or ga["end_date"], est.get("pulled_at") or ga["pulled_at"])
        egroups = [("estimated_company", "Estimated: company page"), ("estimated_kumar", "Estimated: Kumar"), ("cant_tell", "Can't tell")]
        write(f"linkedin_untagged_estimate_by_{kind}", PERIOD_HEAD + ["estimate", "visits"],
              [period_cols(p) + [name, total(est["daily"], "visits", p["start"], p["end"], lambda r: r["group"] == g)]
               for p in periods(kind, est.get("start_date") or start, est_last) for g, name in egroups],
              f"Best guess at who sent the untagged LinkedIn visits, by {kind}. Source: Google Analytics matched to LinkedIn posts found with Apify")

        # YouTube: Shorts and long videos never added together
        y_last = yt.get("last_day_with_data") or yt["end_date"]
        published = lambda t, p: sum(1 for v in yt["channel"]["published"] if v["type"] == t and p["start"] <= v["date"] <= p["end"])
        write(f"youtube_by_{kind}", PERIOD_HEAD + ["long_video_views", "long_video_watch_minutes", "shorts_views", "shorts_watch_minutes",
                                                   "subscribers_gained", "subscribers_lost", "long_videos_published", "shorts_published"],
              [period_cols(p) + [total(yt["types"]["long"]["daily"], "views", p["start"], p["end"]), total(yt["types"]["long"]["daily"], "minutes", p["start"], p["end"]),
                                 total(yt["types"]["shorts"]["daily"], "views", p["start"], p["end"]), total(yt["types"]["shorts"]["daily"], "minutes", p["start"], p["end"]),
                                 total(yt["channel"]["subs_daily"], "gained", p["start"], p["end"]), total(yt["channel"]["subs_daily"], "lost", p["start"], p["end"]),
                                 published("long", p), published("shorts", p)] for p in periods(kind, yt["start_date"], y_last)],
              f"YouTube tab, by {kind}. Source: YouTube Analytics")

    # Lists without dates
    # the Content tab's pieces: each blog post, report, white paper, eBook, guide and comparison page, with its type
    kinds = [(r"^/blog/[a-z0-9-]+$", "Blog"), (r"^/resources/report/[a-z0-9-]+$", "Report"), (r"^/resources/white-papers/[a-z0-9-]+$", "White paper"),
             (r"^/resources/ebooks/[a-z0-9-]+$", "eBook"), (r"^/knowledge-base/(?!category/)[a-z0-9-]+/[a-z0-9-]+$", "Guide (knowledge base)"),
             (r"^/(resources/comparison-guides|comparison-guides|comparison)/[a-z0-9-]+$", "Comparison")]
    import re as _re
    write("content_pieces", ["page", "type", "page_title"],
          [[p, k, t] for p, t in sorted(zip(look["pages"], look["titles"])) for pat, k in kinds if _re.match(pat, p)],
          "Content tab: each blog post, report, white paper, eBook, guide and comparison page with its type. Their numbers are in the page files")
    titled = sorted((p, t) for p, t in zip(look["pages"], look["titles"]) if t)
    for section, label in PAGE_SECTIONS:
        write(f"page_titles_{section}", ["page", "page_title"], [[p, t] for p, t in titled if section_of(p) == section],
              f"The title of each page: {label[0].lower()}{label[1:]}. Source: Google Analytics")
    write("google_top_searches", ["search", "clicks", "times_google_showed_us", "click_rate_pct", "average_spot_on_google"],
          [[s["search"], s["clicks"], s["times_shown"], s["click_rate_pct"], s["avg_spot"]] for s in gsc["searches"][:600] if s["clicks"]],
          f"The searches bringing the most Google clicks, {gsc['start_date']} to {gsc_last}. Source: Search Console. Google hides rare searches")
    write("deals_one_line_each", ["month", "first_came_from", "first_page", "first_form", "product", "open_or_won", "amount_usd"],
          [[d["month"], d["came_from"], d["first_page"], d["first_form"], d["product"], d["status"], d["amount"]] for d in hub.get("deal_lines", [])],
          "How each marketing deal came in: 1 line per deal, open or won, with no company or person. Source: HubSpot. The product comes from words in the deal name")
    em = hub.get("emails") or {}
    if em.get("rows"):
        write("hubspot_marketing_emails", ["sent_on", "subject", "sends", "opens", "clicks", "open_rate_pct", "click_rate_pct"],
              [[e["sent_on"], e["subject"], e["sends"], e["opens"], e["clicks"], e["open_rate_pct"], e["click_rate_pct"]] for e in em["rows"]],
              "HubSpot marketing emails since 1 Apr 2026 with sends, opens and clicks. The subject line shows; emails aimed at named target accounts are left out. Source: HubSpot")
    kpl = json.loads((DATA / "kumar_post_list.json").read_text()) if (DATA / "kumar_post_list.json").exists() else {"posts": []}
    write("linkedin_exec_post_list", ["posted_on", "post", "link", "reactions", "comments"],
          [[x["date"], x["title"], x["link"], x["reactions"], x["comments"]] for x in kpl["posts"]],
          "Each of Kumar's own LinkedIn posts since 1 Jul 2026 with reactions and comments. Source: his public profile, read with Apify")
    ads = collections.defaultdict(lambda: [0.0, 0, 0, 0])
    for r in ga.get("google_ads_daily", []):
        x = ads[(r["date"][:7], r["campaign"])]
        x[0] += r["spend"]; x[1] += r["ad_clicks"]; x[2] += r["visits"]; x[3] += r["demo_requests"]
    if ads:
        write("google_ads_by_campaign", ["month", "campaign", "spend_usd", "ad_clicks", "visits", "demo_requests"],
              [[m, c, round(x[0], 2), x[1], x[2], x[3]] for (m, c), x in sorted(ads.items())],
              "Google Ads spend and ad clicks (counted by Google Ads) with visits and demo requests (counted by Google Analytics), per campaign per month. Brand search visits and demo requests from 16 Jun 2026 are too low because of a tracking problem. Source: Google Analytics, opsera.ai 2026, linked to Google Ads")
    if (DATA / "rankings.json").exists():
        rk = json.loads((DATA / "rankings.json").read_text())
        write("google_rankings_by_week", ["week_starting", "page", "kind", "avg_spot", "clicks", "times_shown"],
              [[w["week"], p["page"], p["group"], w["avg_spot"], w["clicks"], w["times_shown"]] for p in rk["pages"] for w in p["weeks"]],
              f"Average spot on Google, Monday-to-Sunday weeks, for the homepage, the 8 product pages and the top 20 blogs and resources by visits since {rk['new_site_live']}. 1 is the top. Source: Google Search Console, up to {rk['last_day_with_data']}")
        write("google_rankings_top_searches", ["page", "kind", "search", "clicks", "times_shown", "avg_spot"],
              [[p["page"], p["group"], q["search"], q["clicks"], q["times_shown"], q["avg_spot"]] for p in rk["pages"] for q in p["searches"]],
              f"The top 10 searches for each key page, {rk['searches_from']} to {rk['last_day_with_data']}. Source: Google Search Console")
    if (DATA / "gtm_calendar.json").exists():
        gtm = json.loads((DATA / "gtm_calendar.json").read_text())
        write("gtm_calendar", ["ship_date", "end_date", "item", "types"],
              [[i["date"], i.get("end", ""), i["name"], "; ".join(i["types"])] for i in gtm["items"]],
              f"Marketing launches, events and content from the GTM calendar, by ship date. The charts mark these dates. Source: {gtm['source']}, pulled {gtm['pulled_at'][:10]}")
    # Campaigns since 1 Apr, the same rules as the Campaigns tab
    def campaign_key(n):
        x = re.sub(r"^\d+-", "", n).strip()
        return x if re.search(r"\s", x) else x.replace("+", " ")
    left_out = lambda n: re.search(r"\b(abm|abx|microsite)\b", n, re.I) or n.startswith("ET-") or re.fullmatch(r"[a-z0-9-]+\.[a-z]{2,}", n, re.I)
    camp = collections.defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0, 0, 0])
    on = lambda n: (dt.date.fromisoformat(look["start_date"]) + dt.timedelta(days=n)).isoformat()
    for dnum, c, _, v, e in look["campaign_visits"]:
        k = campaign_key(look["campaigns"][c])
        if not left_out(k) and on(dnum) <= ga_last:
            camp[k][0] += v; camp[k][1] += e
    for dnum, _, c, n in look["forms"]:
        k = campaign_key(look["campaigns"][c]) if c >= 0 else ""
        if k and not left_out(k) and on(dnum) <= ga_last:
            camp[k][2] += n
    for e in (hub.get("emails") or {}).get("rows", []):
        if e.get("campaign") and not left_out(e["campaign"]):
            x = camp[e["campaign"]]; x[3] += 1; x[4] += e["sends"]; x[5] += e["opens"]; x[6] += e["clicks"]
    for d in hub.get("campaign_deals", []):
        if d["campaign"] and not left_out(d["campaign"]):
            camp[d["campaign"]][7] += 1; camp[d["campaign"]][8] += d["amount"]
    if camp:
        write("campaigns_since_1_apr", ["campaign", "visits_ga", "engaged_visits_ga", "form_fills_ga", "emails_sent_hubspot", "email_sends", "email_opens",
                                        "email_clicks", "deals_hubspot", "deal_amount_usd"],
              [[k, *x] for k, x in sorted(camp.items(), key=lambda kv: -kv[1][0]) if x[0] or x[2] or x[4] or x[7]],
              f"Each campaign since 1 Apr 2026: visits, engaged visits and form fills from Google Analytics link tags (to {ga_last}), emails and deals from HubSpot. Never add the two sources together. A deal belongs to the campaign its person first came in on. Target-account campaigns, sales outreach codes and spam sites are left out")
    ap = hub.get("all_pipeline")
    if ap and ap.get("rows"):
        fq = lambda d: f"FY{(int(d[:4]) + (1 if int(d[5:7]) >= 2 else 0)) % 100} Q{((int(d[5:7]) + 10) % 12) // 3 + 1}"
        ready = all(ap["salesforce_fields"].values())
        wait = lambda v: v if ready else "Not in HubSpot yet"
        write("marketing_pipeline_deals", ["created_on", "fiscal_quarter", "status", "stage", "pipeline", "product", "lead_source", "amount_usd",
                                     "primary_campaign_source", "attrib_first_campaign", "attrib_last_campaign", "counts_as"],
              [[r["date"], fq(r["date"]), r["status"], r["stage"], r["pipeline"], r["product"], r["lead_source"], r["amount"],
                wait(r["primary_campaign"] or ""), wait(r["first_campaign"] or ""), wait(r["last_campaign"] or ""), wait(r["bucket"] or "")] for r in ap["rows"]],
              "Open and won marketing deals created since 1 Apr 2026 (a marketing Lead Source, or marketing sourced or influenced once the Salesforce campaign fields arrive), 1 line each, with no company or person. Existing Customer, AE and SDR outreach, partners, vendors, bought lists, Direct and blank Lead Sources are left out. The 3 Salesforce campaign fields fill in once they reach HubSpot deals. Fiscal quarters: FY27 Q2 is May to July 2026. Source: HubSpot deals, synced from Salesforce")
    if hub.get("event_rows"):
        fills = collections.Counter()
        for line in leads["lines"].values():
            for pg in line["pages"]:
                fills[pg["page"]] += pg["count"]
        blank = lambda v: "" if v is None else v
        write("events_one_row_each", ["first_day", "last_day", "event", "kind", "signed_up_hubspot", "attended_hubspot", "event_page_form_fills_google_analytics",
                                      "meetings_afterwards_hubspot", "people_with_a_meeting", "meetings_booked_for_later", "note"],
              [[e["first_day"] or "", e["last_day"] or "", e["name"], e["kind"], blank(e["signed_up"]), blank(e["attended"]),
                sum(fills[p] for p in e["pages"]) if e["pages"] else "", blank(e["meetings_after"]), blank(e["people_with_meeting"]),
                blank(e["meetings_upcoming"]), e["note"]] for e in hub["event_rows"]],
              "Each webinar, roundtable and event since 1 Apr 2026. Sign-ups, attended and meetings come from HubSpot; event page form fills from Google Analytics. Never add the two together. Blank means no data")
    write("hubspot_event_lists", ["list", "members", "note", "first_added", "last_added"],
          [[e["label"], e["members"], e.get("note") or "", e["joined_daily"][0]["date"] if e["joined_daily"] else "", e["joined_daily"][-1]["date"] if e["joined_daily"] else ""]
           for e in hub["events"]], "Event sign-up lists in HubSpot, each on its own (never added together). Source: HubSpot")
    write("linkedin_brand_posts", ["posted_on", "post", "link", "paid", "video", "times_seen", "clicks", "likes", "comments"],
          [[p["created"], p["title"], p["link"], "yes" if p["paid"] else "no", "yes" if p["video"] else "no", p["seen"], p["clicks"], p["likes"], p["comments"]]
           for p in sorted(li["company"]["posts"], key=lambda x: x["created"])], "Each Opsera company page post. Source: LinkedIn exports")
    write("linkedin_exec_posts_by_month", ["month", "own_posts", "reposts", "month_not_finished"],
          [[m["month"], m["own_posts"], m["reposts"], "yes" if m.get("so_far") else "no"] for m in kp["months"]],
          f"Kumar's own posts and reposts by month (UTC), 2 separate counts. Source: {kp['source']}, checked {kp['as_of']}")
    write("linkedin_exec_exports", ["period", "start", "end", "times_seen", "people_reached", "engagements", "followers_gained", "day_still_being_counted"],
          [[p["label"], p["start_date"], p["end_date"], p["seen"], p["reached"], sum(r["engagements"] for r in p["daily"]),
            sum(r["gained"] for r in p["followers_daily"]), " and ".join(p.get("still_counting", []))] for p in li["kumar_october"]["periods"]]
          + [["July to September", li["kumar"]["start_date"], li["kumar"]["end_date"], li["kumar"]["seen"], li["kumar"]["reached"],
              sum(r["engagements"] for r in li["kumar"]["daily"]), sum(r["gained"] for r in li["kumar"]["followers_daily"]), ""]],
          "Each LinkedIn export of Kumar's profile as LinkedIn gave it. People reached doesn't add up across days. Source: LinkedIn exports")
    write("youtube_videos", ["video", "type", "views", "watch_minutes", "average_seconds_watched", "link"],
          [[v["title"], "Short" if t == "shorts" else "Long video", v["views"], v["minutes"], v["avg_seconds"], f"https://www.youtube.com/watch?v={v['id']}"]
           for t in ("long", "shorts") for v in yt["types"][t]["videos"]],
          f"Each video's views and watch time, {yt['start_date']} to {yt.get('last_day_with_data')}. Source: YouTube Analytics")
    km, kq, inf = load("kahoots_monthly.json"), load("kahoots_quarter.json"), load("infrasity_monthly.json")
    write("kahoots_monthly_as_reported", ["month", "website_visits", "visits_from_people", "form_fills", "first_page_searches"],
          [[r["month"], r["visits"], r["people_visits"], r["form_fills"], r.get("first_page_searches", "")] for r in km],
          "What Kahoots reported by month, July to September 2026, from the old opsera.ai 2025 Google Analytics account")
    write("kahoots_quarter_as_reported", ["measure", "q2_2026", "q3_2026"], [[r["metric"], r["q2"], r["q3"]] for r in kq],
          "What Kahoots reported for Q2 and Q3 2026")
    write("infrasity_monthly_as_reported", ["month", "google_clicks", "times_google_showed_us", "times_shown_as_reported", "click_rate_pct",
                                            "click_rate_change_as_reported", "average_spot_on_google", "forge_page_google_clicks"],
          [[r["month"], r["google_clicks"], r["times_shown"], (r.get("reported") or {}).get("times_shown", ""), r["click_rate_pct"],
            (r.get("reported") or {}).get("click_rate_pct_change", ""), r["avg_spot"], r["forge_page_clicks"]] for r in inf],
          "What Infrasity reported by month, July to September 2026")

    team = load("team_metrics.json")
    write("team_metrics", ["person", "section", "metric", "baseline_monthly_average", "this_month_so_far", "counted_from", "counted_to",
                           "goal_per_month", "share_of_goal_pct", "source"],
          [[p["name"], sec["title"], m["label"], m["baseline"], "" if m["so_far"] is None else m["so_far"], m["so_far_start"], m["so_far_end"] or "",
            m["goal"] if m["goal"] else "To set", "" if m["goal_share_pct"] is None else m["goal_share_pct"], m["source"]]
           for p in team["people"] for sec in p["sections"] for m in sec["metrics"]]
          + [[p["name"], sec["title"], "Website visits, without email robots", m["without_email_robots"]["baseline"],
              "" if m["without_email_robots"]["so_far"] is None else m["without_email_robots"]["so_far"], m["so_far_start"], m["so_far_end"] or "",
              "", "", m["source"]] for p in team["people"] for sec in p["sections"] for m in sec["metrics"] if m.get("without_email_robots")]
          + [[p["name"], "", "Metrics coming", "", "", "", "", "", "", ""] for p in team["people"] if not p["sections"]],
          f"Team metrics tab: each person's metrics, with the baseline ({team['baseline']['label']}), this month so far and the goal")
    write_guide(ga_last, gsc_last, hub, li, kp, yt, est)
    for name, n, size, *_ in files:
        print(f"{name:52} {n:6} rows {size / 1000:6.1f} KB")


def write_guide(ga_last, gsc_last, hub, li, kp, yt, est):
    link = lambda name: f"[{name}]({SITE}/for-claude/{name})"
    def listing(prefix):
        """One line per file, or per family of split files with a short link to each part."""
        lines, seen = [], set()
        for f in sorted(files, key=lambda f: f[0]):
            name, rows, _, about, base, key = f
            if not base.startswith(prefix) or base in seen:
                continue
            seen.add(base)
            family = sorted((g for g in files if g[4] == base), key=lambda g: g[0])
            if len(family) == 1 and family[0][5] is None:
                lines.append(f"- {link(name)}: {about}. {rows} rows.")
            else:
                parts = ", ".join(f"[{g[5]}]({SITE}/for-claude/{g[0]})" for g in family)
                lines.append(f"- {base}, split to stay small: {about}. Parts: {parts}.")
        return "\n".join(lines)
    ga = load("analytics.json")
    (OUT / "index.md").write_text(f"""# Opsera website analytics, in plain text

The data behind the dashboard at {SITE}/, written for AI assistants such as Claude.
Every number here also appears on the dashboard. We rebuild these files every Monday morning, India time. Last rebuilt from data pulled {ga['pulled_at'][:10]}.

## How to answer questions

- Read this guide first, then open only the files a question needs. Every file is a small CSV with a header row.
- Weeks run Monday to Sunday. Months are calendar months. `period_not_finished` is "yes" for a week or month still under way.
- Google Analytics and HubSpot dates follow US Pacific time. LinkedIn exports use UTC.
- Never add numbers from different sources together (for example Google Analytics visits and Search Console clicks). Each file and column says its source.
- "Without email robots" leaves out visits by email link checkers: visits with no engagement landing on email subscription pages (/hs/preferences-center), from Cupertino, Palo Alto, Garner or Sunnyvale, or from Safari on a Mac desktop. All visits stays as Google Analytics counts it.
- "Visits" are Google Analytics sessions. "Engaged visits" are visits where someone stayed 10+ seconds, saw 2+ pages or filled a form. They leave out most email robots.
- Form fills count the HubSpot form event in Google Analytics. We leave out job application forms everywhere.
- Asset downloads are form fills on pages under /resources/report/, /resources/white-papers/, /resources/ebooks/ or /resources/comparison-guides/. They're part of "other forms".
- Deals exist as weekly and monthly totals, and as 1 line per marketing deal in deals_one_line_each.csv, without company or person names. Closed Lost deals stay out, and there are no daily deal numbers.
- When the dashboard compares periods, it compares the last full week with the week before, or this month so far with the whole of last month.
- A page in the page files is its address on opsera.ai, so `/pricing` is https://opsera.ai/pricing. Page titles are in the page_titles files.
- We split page and page title files by part of the site: blog, resources, knowledge base and other. Big ones also split by quarter, month or week, as the file name says.
- Questions about a campaign: use the campaign files (the utm_campaign in Google Analytics). Search Console counts Google clicks by page, so campaigns don't have them.
- Questions about a channel: use customer_journey_funnel (journey channels) or visit_sources (Google Analytics channel groups).
- If a question needs something these files don't have, say so instead of guessing.

## Date ranges

- Google Analytics and HubSpot: {ga['start_date']} to {ga_last}.
- Search Console (Google search): {load('search_console.json')['start_date']} to {gsc_last}. It runs about 2 days behind.
- LinkedIn company page: {li['company']['start_date']} to {li['company']['end_date']}. LinkedIn Kumar: {li['kumar_all']['start_date']} to {li['kumar_all']['end_date']}, the last day still being counted when exported.
- YouTube: {yt['start_date']} to {yt.get('last_day_with_data')}.
- Kahoots and Infrasity: July to September 2026, as they reported it.

## Customer journey tab

How marketing turns website visits into demo requests, meetings and deals. The funnel has 6 steps. Google Analytics counts visits, demo page views and demo form fills. HubSpot counts new contacts, meetings and deals. A contact is someone who first filled in the demo form. Meetings and deals count only after sign-up, never with existing customers. A later step can be bigger than the step before because the 2 tools count differently. For Google search, every step ends on Search Console's last day, and the first 2 columns are Search Console. "All channels" visits match the Website visits tab.

{listing('customer_journey')}
{listing('deals_one_line_each')}
{listing('google_ads')}

## Website visits tab

{listing('website_visits')}
{listing('visit_sources')}

## Leads tab

Demo requests are form fills on /demo. Contact forms are on /contact. The Gartner offer is /gartner-symposium/free-modernization. Event sign-ups are /events/ pages, /gartner-symposium and /github-universe-happy-hour. Everything else is other forms. Before October, the old site sent some homepage and contact form fills only to Google, so earlier months look low. Luma event sign-ups don't show here.

{listing('leads')}
{listing('hubspot_event_lists')}
{listing('events_one_row_each')}

## Pages, campaigns and assets (the Look up tab)

Visits count people who landed on the page from outside the site. Page files list a page in a period only when it had a visit, form fill or Google click.

{listing('pages')}
{listing('page_titles')}
{listing('campaigns')}

## Content tab

One row per blog post, report, white paper, eBook, guide (knowledge base article) and comparison page. content_pieces lists each piece with its type; its visits, form fills and Google clicks are in the page files above. A deal counts for a piece when the contact's first page or first form was that piece (see deals_one_line_each.csv).

{listing('content_pieces')}

## Google search tab

{listing('google_search')}
{listing('google_top_searches')}
{listing('google_rankings')}

## AEO tab: visits from AI tools

{listing('aeo')}

## LinkedIn brand tab (Opsera company page)

Paid means sponsored posts. LinkedIn's own sheets disagree on reposts, so we leave them out.

{listing('linkedin_brand')}

## LinkedIn exec tab (Kumar Chivukula)

{listing('linkedin_exec')}

## LinkedIn visits to opsera.ai

Company page means links tagged utm_campaign=brand-page. Kumar means utm_source=linkedin with utm_campaign=kumar. Untagged is everything else from LinkedIn. We never add the 3 together. The estimate is a best guess, kept apart from the tagged numbers.

{listing('linkedin_visits_to_site')}
{listing('linkedin_untagged_estimate')}

## YouTube tab

We never add Shorts and long videos together.

{listing('youtube')}

## Pipeline tab

Marketing pipeline: open and won deals since 1 Apr from marketing Lead Sources. Marketing sourced and influenced fill in once the Salesforce campaign fields reach HubSpot deals.

{listing('marketing_pipeline')}

## Team metrics tab

Each person's metrics. The baseline is the July to September 2026 monthly average. "To set" means nobody has set a goal yet, so don't invent one. "Metrics coming" means the person hasn't sent their metrics yet.

{listing('team_metrics')}

## GTM calendar markers

The small diamonds under dated charts. Each is a launch, event or piece of content on its ship date. Use them to see what was going on when a number moved, not as proof one caused the other.

{listing('gtm_calendar')}

## Before: Kahoots and Before: Infrasity tabs

These match the agencies' own reports exactly.

{listing('kahoots')}
{listing('infrasity')}
""")


if __name__ == "__main__":
    main()
