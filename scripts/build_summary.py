"""Write data/summary.json for the Summary tab: up to 3 takeaways per area, for Week, Month and 3 months.

1. What happened: the most important change against the period before.
2. What stands out: the most interesting detail behind it.
3. What it means and what to do: one insight with its number, and one action.
Claude writes all 3 from the numbers: through the API if ANTHROPIC_API_KEY is set, or by Claude Code into data/summary_takeaways.json
when Purav asks "write this week's Summary takeaways" (run with --facts to get the numbers first). Every number Claude uses must be one it was given, never a 0,
and its text must follow the dashboard's copy rules; a takeaway that breaks a rule is dropped.
Without the key, takeaways 1 and 2 are written here, and only for areas with a real change.
Never a takeaway about a 0, an unchanged number or anything tiny. Agreed with Purav on 3 Nov 2026.
Run: .venv/bin/python scripts/build_summary.py
"""
import collections
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "summary.json"
WRITTEN = DATA / "summary_takeaways.json"   # takeaways Claude Code writes when asked, checked here like the API's
FACTS = Path(__file__).resolve().parent.parent.parent / "summary_facts.json"   # the numbers for Claude Code, outside the repo
MODES = ("week", "month", "quarter")   # the Summary has no Day view: the page shows Week instead
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
MODEL = "claude-opus-5-5"
NOTES = []   # why a period isn't the one asked for, filled in by periods_for
TOOLS = {"chatgpt": "ChatGPT", "gemini": "Gemini", "perplexity": "Perplexity", "claude": "Claude", "copilot": "Copilot"}
CHANNELS = {"search": "Google search", "linkedin": "LinkedIn", "email": "email", "events": "events", "paid": "paid ads", "ai": "AI tools",
            "youtube": "YouTube", "direct": "direct visits", "referral": "other websites", "other": "other sources"}
CONTENT = [re.compile(p) for p in (r"^/blog/[a-z0-9-]+$", r"^/resources/report/[a-z0-9-]+$", r"^/resources/white-papers/[a-z0-9-]+$",
                                   r"^/resources/ebooks/[a-z0-9-]+$", r"^/knowledge-base/(?!category/)[a-z0-9-]+/[a-z0-9-]+$",
                                   r"^/(resources/comparison-guides|comparison-guides|comparison)/[a-z0-9-]+$")]   # the Content tab's types
GA_CHANNELS = {"Direct": "Direct (typed in, or unknown)", "Organic Search": "Search engines (mostly Google)", "Email": "Email",
               "Referral": "Other websites", "Organic Social": "Social media (LinkedIn and others)", "AI Assistant": "AI tools",
               "Unassigned": "Unlabelled", "Paid Search": "Paid search ads", "Paid Social": "Paid social ads", "Organic Shopping": "Shopping search",
               "Organic Video": "Video sites", "Display": "Display ads", "Cross-network": "Google ad network"}   # the Website visits tab's names
LEFT_OUT_CAMPAIGN = re.compile(r"\b(abm|abx|microsite)\b|^ET-|^[a-z0-9-]+\.[a-z]{2,}$", re.I)   # the Campaigns tab's rule


def load(name):
    p = DATA / name
    return json.loads(p.read_text()) if p.exists() else None


def d(s):
    return dt.date.fromisoformat(s)


def iso(x):
    return x.isoformat()


def add_days(s, n):
    return iso(d(s) + dt.timedelta(days=n))


def month_start(s):
    return s[:8] + "01"


def month_end(s):
    x = d(month_start(s))
    return iso((x.replace(day=28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1))


def add_months(s, n):
    x = d(s)
    m = x.month - 1 + n
    y, m = x.year + m // 12, m % 12 + 1
    last = (dt.date(y, m, 28) + dt.timedelta(days=4)).replace(day=1) - dt.timedelta(days=1)
    return iso(dt.date(y, m, min(x.day, last.day)))


def last_full_day_pacific(end, pulled_at):
    """The same rule as the page: Google Analytics days follow US Pacific time."""
    pt = dt.datetime.fromisoformat(pulled_at).astimezone(ZoneInfo("America/Los_Angeles")).date()
    return end if iso(pt) > end else add_days(end, -1)


def periods_for(mode, start, last, full_month=True):
    """The dashboard's periods (periodsFor in app.js): this period and the one before, or None."""
    if mode == "quarter":
        q = lambda e: (add_days(add_months(e, -3), 1), e)
        cur, prev = q(last), q(add_days(q(last)[0], -1))
        return (cur if cur[0] >= start else (start, last)), (prev if prev[0] >= start else None), "the 3 months before"
    if mode == "week":
        end = last if d(last).weekday() == 6 else add_days(last, -(d(last).weekday() + 1))
        cur, prev = (add_days(end, -6), end), (add_days(end, -13), add_days(end, -7))
        return (cur if cur[0] >= start else None), (prev if prev[0] >= start else None), "the week before"
    cur = (month_start(last), last)
    if full_month:   # the Pipeline tab's rule: less than half the month so far means the last full month, so 1 day isn't set against 31
        days = (d(last) - d(cur[0])).days + 1
        if days * 2 < (d(month_end(cur[0])) - d(cur[0])).days + 1:
            NOTES.append(f"{MONTH_NAMES[d(last).month - 1]} has only {days} day{'s' if days > 1 else ''} so far, so this shows the last full month.")
            cur = (month_start(add_days(cur[0], -1)), add_days(cur[0], -1))
    p = month_start(add_days(cur[0], -1))
    prev = (p, month_end(p))
    return cur, (prev if prev[0] >= start else None), "in " + MONTH_NAMES[d(p).month - 1]


def day_name(s):
    return f"{d(s).day} {MONTHS[d(s).month - 1]}"


def span(a, b):
    if a == b:
        return f"{day_name(a)} {a[:4]}"
    first = str(d(a).day) if a[:7] == b[:7] else day_name(a)
    return f"{first} to {day_name(b)} {b[:4]}"


def n(v):
    return f"{round(v):,}"


def money(v):
    return f"${round(v):,}"


def total(rows, key, a, b, keep=lambda r: True):
    return sum((key(r) if callable(key) else r.get(key, 0) or 0) for r in rows if a <= r["date"] <= b and keep(r))


def pct(cur, prev):
    return None if not prev else round((cur - prev) / prev * 100, 1)


# ---------- the 12 areas ----------
# Each area gives its periods, its numbers (facts), the changes it could lead with (mains) and the details it could add.
# A change is worth a takeaway only if it's real: both periods above 0, a move of at least 15%, and big enough to matter.

def notable(cur, prev, floor, rel=0.15):
    return bool(cur) and bool(prev) and cur != prev and max(cur, prev) >= floor and abs(cur - prev) / prev >= rel


def area(cur, prev, before, facts, mains=(), details=()):
    """mains: (key, label, cur, prev, floor[, fmt]), most important first. details: (key, text) worth saying; "after:" keys go last."""
    mains = [m if len(m) == 6 else (*m, n) for m in mains]
    for key, _, c, p, _, _ in mains:
        facts.setdefault(key, c)
        facts.setdefault(key + "_before", p)
        if p:
            facts.setdefault(key + "_change_pct", pct(c, p))
    return {"cur": cur, "prev": prev, "before": before, "facts": facts, "mains": mains, "details": list(details)}


def written(a):
    """Takeaways 1 and 2 from the numbers: the most important real change, then the best detail behind it. None if nothing is worth saying."""
    real = [m for m in a["mains"] if a["prev"] and notable(m[2], m[3], m[4])]
    if real:
        key, label, c, p, _, fmt = real[0]   # mains are listed most important first
        t1 = f"{label}: {fmt(c)}, {'up' if c > p else 'down'} from {fmt(p)} {a['before']}."
    elif a.get("lead"):
        key, t1 = a["lead"]
    else:
        return None, None
    extra = [t for k, t in a["details"] if k != key and not k.startswith("after:")]
    extra += [f"{l}: {f(c2)}, {'up' if c2 > p2 else 'down'} from {f(p2)}." for k, l, c2, p2, fl, f in real if k != key]
    extra += [t for k, t in a["details"] if k.startswith("after:")]   # caveats come after any other real change
    return t1, (extra[0] if extra else None)


def pipeline(mode):
    sf = load("salesforce_pipeline.json")
    last = add_days(sf["exports"]["opportunities"], -1)
    cur, prev, before = periods_for(mode, sf["opportunities_cover_from"], last)
    t = lambda k, p: total(sf["days"], k, *p) if p else None
    nc = t("nocontact_deals", cur)
    return area(cur, prev, before, {"no_contact_deals": nc, "share_of_all_deals_without_contact_pct": sf.get("share_without_contact_pct")},
                [("sourced_deals", "Marketing sourced deals (estimate)", t("sourced_deals", cur), t("sourced_deals", prev), 3),
                 ("sourced_value", "Marketing sourced pipeline (estimate)", t("sourced_value", cur), t("sourced_value", prev), 100000, money),
                 ("influenced_deals", "Marketing influenced deals", t("influenced_deals", cur), t("influenced_deals", prev), 3),
                 ("influenced_value", "Marketing influenced pipeline", t("influenced_value", cur), t("influenced_value", prev), 100000, money)],
                [("after:no_contact", f"{n(nc)} more deals had no contact linked, so we can't see where they came from.")] if nc >= 5 else [])


def leads(mode):
    l = load("leads.json")
    cur, prev, before = periods_for(mode, l["start_date"], last_full_day_pacific(l["end_date"], l["pulled_at"]))
    t = lambda k, p: total(l["daily"], k, *p) if p else None
    return area(cur, prev, before, {}, [("demo_requests", "Demo requests", t("demo", cur), t("demo", prev), 5)] +
                [(f"{k}_form_fills", l["lines"][k]["label"], t(k, cur), t(k, prev), 5) for k in ("events", "contact", "gartner_offer")])


def journey(mode):
    hub = load("hubspot.json")
    cur, prev, before = periods_for(mode, hub["start_date"], hub["end_date"])
    booked = lambda p: total(hub["meetings_daily"], "count", *p, keep=lambda r: r["kind"] == "booked") if p else None
    contacts = lambda p: total(hub["contacts_daily"], "count", *p) if p else None
    by = collections.Counter()
    for r in hub["contacts_daily"]:
        if cur[0] <= r["date"] <= cur[1]:
            by[CHANNELS.get(r["channel"], r["channel"])] += r["count"]
    c = contacts(cur)
    top = by.most_common(1)
    details = [("top_channel", f"The most new contacts came from {top[0][0]}: {n(top[0][1])} of {n(c)}.")] if top and top[0][1] >= 5 else []
    return area(cur, prev, before, {"new_contacts_by_channel": dict(by.most_common(5))},
                [("meetings_booked", "Meetings booked with marketing contacts", booked(cur), booked(prev), 3),
                 ("new_marketing_contacts", "New marketing contacts", c, contacts(prev), 10)], details)


def visits(mode):
    ga = load("analytics.json")
    cur, prev, before = periods_for(mode, ga["start_date"], last_full_day_pacific(ga["end_date"], ga["pulled_at"]))
    t = lambda k, p, rows=ga["daily"]: total(rows, k, *p) if p else None
    ch = collections.defaultdict(lambda: [0, 0])
    for r in ga["channel_daily"]:
        for i, p in enumerate((cur, prev)):
            if p and p[0] <= r["date"] <= p[1]:
                ch[GA_CHANNELS.get(r["sessionDefaultChannelGroup"], r["sessionDefaultChannelGroup"])][i] += r["sessions"]
    robots = ga.get("email_robots_daily", [])
    clean = lambda p: t("sessions", p) - (t("robots", p, robots) or 0) if p else None   # the dashboard's "Without email robots" rule
    un = ch.get("Unlabelled", [0, 0])
    jump = bool(prev) and notable(un[0], un[1], 100) and un[0] > un[1]   # a jump in unlabelled visits is likely robots, not growth
    movers = sorted(((k, x) for k, x in ch.items() if notable(x[0], x[1], 100) and k != "Unlabelled"), key=lambda kv: -abs(kv[1][0] - kv[1][1]))
    details = [("robots", f"Unlabelled visits jumped to {n(un[0])}, up from {n(un[1])}. These are likely robots, not real growth.")] if jump else []
    details += [("channel", f"The biggest change was {k}: {n(x[0])} visits, {'up' if x[0] > x[1] else 'down'} from {n(x[1])}. Visits by source still include robots.") for k, x in movers[:1]]
    a = area(cur, prev, before, {"all_visits_including_robots": t("sessions", cur), "all_visits_including_robots_before": t("sessions", prev),
                                    "unlabelled_visits": un[0], "unlabelled_visits_before": un[1], "unlabelled_jump_is_likely_robots": jump,
                                    "visits_by_channel": {k: x[0] for k, x in sorted(ch.items(), key=lambda kv: -kv[1][0])[:6]},
                                    "visits_by_channel_before": {k: x[1] for k, x in sorted(ch.items(), key=lambda kv: -kv[1][0])[:6]}},
                [("visits_without_email_robots", "Visits without email robots", clean(cur), clean(prev), 200), ("engaged_visits", "Engaged visits", t("engagedSessions", cur), t("engagedSessions", prev), 100)],
                details)
    if jump:
        a["lead"] = details[0]   # worth saying even when real visits barely moved
    return a


def search(mode):
    g = load("search_console.json")
    cur, prev, before = periods_for(mode, g["start_date"], g["last_day_with_data"])
    t = lambda k, p: total(g["daily"], k, *p) if p else None
    spot = lambda p: (round(total(g["daily"], lambda r: r["avg_spot"] * r["times_shown"], *p) / t("times_shown", p), 1)
                      if p and t("times_shown", p) else None)
    s, sp = spot(cur), spot(prev)
    details = [("spot", f"The average spot on Google moved from {sp} to {s} (lower is better).")] if s and sp and abs(s - sp) >= 0.5 else []
    return area(cur, prev, before, {"average_spot": s, "average_spot_before": sp},
                [("clicks", "Clicks from Google search", t("clicks", cur), t("clicks", prev), 50),
                 ("times_shown", "Times Google showed our pages", t("times_shown", cur), t("times_shown", prev), 1000)], details)


def aeo(mode):
    ga = load("analytics.json")
    cur, prev, before = periods_for(mode, ga["start_date"], last_full_day_pacific(ga["end_date"], ga["pulled_at"]))
    rows = ga["ai"]["daily"]
    v = total(rows, "visits", *cur)
    by = collections.Counter()
    for r in rows:
        if cur[0] <= r["date"] <= cur[1]:
            by[TOOLS.get(r["tool"], r["tool"])] += r["visits"]
    forms = total(rows, "demo_form", *cur)
    details = [("forms", f"Visits from AI tools led to {n(forms)} demo form fill{'s' if forms > 1 else ''}.")] if forms else []
    top = by.most_common(1)
    if top and top[0][1] >= 10:
        details.append(("tool", f"{top[0][0]} sent the most: {n(top[0][1])} of {n(v)}."))
    return area(cur, prev, before, {"ai_visits_by_tool": dict(by.most_common()), "ai_demo_form_fills": forms},
                [("ai_visits", "Visits from AI tools", v, total(rows, "visits", *prev) if prev else None, 20)], details)


def campaign_key(name):
    x = re.sub(r"^\d+-", "", name).strip()
    return x if re.search(r"\s", x) else x.replace("+", " ")


def campaigns(mode):
    lk = load("lookup.json")
    cur, prev, before = periods_for(mode, lk["start_date"], last_full_day_pacific(lk["end_date"], lk["pulled_at"]))
    by = collections.defaultdict(lambda: [0, 0, 0])
    for day, c, _, v, e in lk["campaign_visits"]:
        k = campaign_key(lk["campaigns"][c])
        if LEFT_OUT_CAMPAIGN.search(k):
            continue
        date = add_days(lk["start_date"], day)
        if cur[0] <= date <= cur[1]:
            by[k][0] += v; by[k][1] += e
        elif prev and prev[0] <= date <= prev[1]:
            by[k][2] += v
    top = sorted(((k, x) for k, x in by.items() if x[0]), key=lambda kv: -kv[1][0])[:3]
    details = [("top", f"{k} brought the most: {n(x[0])} visits" + (f", {n(x[1])} of them engaged." if x[1] else "."))
               for k, x in top[:1] if x[0] >= 20]
    return area(cur, prev, before, {"top_campaigns": [{"campaign": k, "visits": x[0], "engaged_visits": x[1], "visits_before": x[2]} for k, x in top]},
                [("campaign_visits", "Visits from tagged campaigns", sum(x[0] for x in by.values()), sum(x[2] for x in by.values()) if prev else None, 50)],
                details)


def events(mode):
    hub, ga = load("hubspot.json"), load("analytics.json")
    rows = [e for e in hub.get("event_rows", []) if e.get("last_day")]
    cur, prev, before = periods_for(mode, hub["start_date"], last_full_day_pacific(ga["end_date"], ga["pulled_at"]))
    inside = [e for e in rows if cur[0] <= e["last_day"] <= cur[1]]
    size = lambda e: (e.get("sf_people_with_meeting") or 0, e.get("attended") or e.get("signed_up") or 0)
    a = area(cur, prev, before, {"events_ended": [e["name"] for e in inside]})
    if not inside:
        return a
    e = max(inside, key=size)
    bits = [f"{n(e[k])} {w}" for k, w in (("signed_up", "signed up"), ("attended", "attended")) if e.get(k)]
    met = e.get("sf_people_with_meeting")
    if not bits and not met:
        return a   # nothing to say about it yet
    a["facts"].update({"event": e["name"], "signed_up": e.get("signed_up"), "attended": e.get("attended"),
                       "people_with_a_meeting_after": met, "in_its_salesforce_campaign": e.get("sf_members")})
    a["lead"] = ("event", f"{e['name']}: {' and '.join(bits)}." if bits else f"{e['name']} ended in this period.")
    if met:
        a["details"].append(("met", f"{n(met)} people from its Salesforce campaign have had a meeting since."))
    if len(inside) > 1:
        a["details"].append(("count", f"{len(inside)} events ended in this period."))
    return a


def content(mode):
    lk = load("lookup.json")
    cur, prev, before = periods_for(mode, lk["start_date"], last_full_day_pacific(lk["end_date"], lk["pulled_at"]))
    is_content = [any(rx.match(p) for rx in CONTENT) for p in lk["pages"]]
    by = collections.defaultdict(lambda: [0, 0, 0])
    for day, pg, _, v, e in lk["visits"]:
        if not is_content[pg]:
            continue
        date = add_days(lk["start_date"], day)
        if cur[0] <= date <= cur[1]:
            by[pg][0] += v; by[pg][1] += e
        elif prev and prev[0] <= date <= prev[1]:
            by[pg][2] += v
    title = lambda i: re.sub(r"\s*[|—–-]\s*Opsera\s*$", "", lk["titles"][i] or lk["pages"][i]).strip()
    top = sorted(((k, x) for k, x in by.items() if x[0]), key=lambda kv: -kv[1][0])[:3]
    details = [("top", f"The top piece was \"{title(k)}\": {n(x[0])} visits" + (f", {n(x[1])} of them engaged." if x[1] else "."))
               for k, x in top[:1] if x[0] >= 50]
    return area(cur, prev, before, {"top_pieces": [{"title": title(k), "visits": x[0], "engaged_visits": x[1], "visits_before": x[2]} for k, x in top]},
                [("content_visits", "Content page visits", sum(x[0] for x in by.values()),
                  sum(x[2] for x in by.values()) if prev else None, 200)], details)


def linkedin_brand(mode):
    co = load("linkedin.json")["company"]
    cur, prev, before = periods_for(mode, co["daily"][0]["date"], co["end_date"])
    t = lambda k, p, rows=co["daily"]: total(rows, k, *p) if p else None
    posts = sorted((p for p in co["posts"] if cur[0] <= p["created"] <= cur[1]), key=lambda p: -p["seen"])
    details = [("post", f"The most seen was the {'video ' if p['video'] else ''}post from {day_name(p['created'])}: "
                        f"{n(p['seen'])} times, with {n(p['clicks'])} clicks.") for p in posts[:1] if p["seen"] >= 500]
    return area(cur, prev, before, {"new_posts": len(posts),
                                    "top_posts": [{"posted": day_name(p["created"]), "seen": p["seen"], "clicks": p["clicks"], "video": p["video"], "paid": p["paid"]} for p in posts[:3]]},
                [("times_seen", "Times the company page's posts were seen", t("seen_total", cur), t("seen_total", prev), 1000),
                 ("clicks", "Clicks on the company page's posts", t("clicks_total", cur), t("clicks_total", prev), 100),
                 ("followers_gained", "Company page followers gained", t("gained", cur, co["followers_daily"]), t("gained", prev, co["followers_daily"]), 10)],
                details)


def linkedin_exec(mode):
    k = load("linkedin.json")["kumar_all"]
    cur, prev, before = periods_for(mode, k["start_date"], k["end_date"])
    if mode == "month" and cur[1] != month_end(cur[0]):
        NOTES.append(f"Kumar's export ends on {day_name(k['end_date'])}, so Month shows once it covers the whole month.")
        return None
    t = lambda key, p, rows=k["daily"]: total(rows, key, *p) if p else None
    return area(cur, prev, before, {},
                [("times_seen", "Times Kumar's posts were seen", t("seen", cur), t("seen", prev), 1000),
                 ("engagements", "Engagements on Kumar's posts", t("engagements", cur), t("engagements", prev), 30),
                 ("followers_gained", "Followers Kumar gained", t("gained", cur, k["followers_daily"]), t("gained", prev, k["followers_daily"]), 10)])


def youtube(mode):
    y = load("youtube.json")
    cur, prev, before = periods_for(mode, y["start_date"], y.get("last_day_with_data") or y["end_date"])
    t = lambda kind, key, p: total(y["types"][kind]["daily"], key, *p) if p else None   # long videos and Shorts kept apart, like the tab
    subs = lambda p: total(y["channel"]["subs_daily"], "gained", *p) if p else None
    return area(cur, prev, before, {"long_video_watch_minutes": t("long", "minutes", cur)},
                [("long_video_views", "Long video views", t("long", "views", cur), t("long", "views", prev), 50),
                 ("shorts_views", "Shorts views", t("shorts", "views", cur), t("shorts", "views", prev), 50),
                 ("subscribers_gained", "Subscribers gained", subs(cur), subs(prev), 5)])


AREAS = [("pipeline", "Pipeline", pipeline, "Salesforce exports, marketing deals"),
         ("leads", "Leads", leads, "Google Analytics, form fills"),
         ("journey", "Customer journey", journey, "HubSpot, marketing contacts and meetings"),
         ("visits", "Website visits", visits, "Google Analytics"),
         ("search", "Google search", search, "Search Console"),
         ("aeo", "AEO", aeo, "Google Analytics, visits from AI tools"),
         ("campaigns", "Campaigns", campaigns, "Google Analytics, tagged campaign links"),
         ("events", "Events", events, "HubSpot and Salesforce event campaigns"),
         ("content", "Content", content, "Google Analytics, landing pages"),
         ("linkedin", "LinkedIn brand", linkedin_brand, "LinkedIn company page exports"),
         ("linkedin-exec", "LinkedIn exec", linkedin_exec, "Kumar's LinkedIn exports"),
         ("youtube", "YouTube", youtube, "YouTube Analytics")]


# ---------- all 3 takeaways, written by Claude ----------

BANNED = re.compile(r"\bthat\b|—|–|\bjourney\b|\bleverage\b|\bsynergy\b|\bunlock\b|\bdelve\b", re.I)
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
FLAT = re.compile(r"\b(stayed|unchanged|the same|flat|held steady|no change|steady)\b", re.I)
ZERO = re.compile(r"(?<![\d.,])\$?0(?![\d.,]*\d)")   # a standalone 0, like "0 deals" or "$0"

SYSTEM = """You write the Summary of a marketing dashboard for Opsera, a software company. For each area and each period view you get the numbers for one period and the period before. Write 3 takeaways:
1. What happened: the most important change, with its number against the period before. Example: "Demo requests: 20, up from 6."
2. What stands out: the most interesting detail behind it, such as the top page, campaign, source or biggest drop.
3. What it means and what to do: one insight with the number behind it, then one suggested action. Example: "LinkedIn posts with a link drove 3x the visits. Add a link to every post."

Rules:
- Use only facts and numbers given for that area and view. Never invent, estimate or add numbers, causes, names or events. Use a number exactly as given, or a percentage given in a *_change_pct field.
- If unlabelled_jump_is_likely_robots is true, say the unlabelled visits are likely robots. Never call them growth.
- Never write about a 0, a number with no change, or anything tiny (a move under 15%, or a handful of visits). If an area has nothing worth saying in a view, return empty strings for all 3. If only takeaway 2 or 3 has nothing worth saying, return an empty string for it.
- Each takeaway is 1 or 2 short sentences. Plain, everyday English. Sentence case. Numbers as numerals. Active voice. At most 2 commas a sentence.
- Never use the word "that", em dashes, en dashes, semicolons, "journey", "leverage", "unlock" or exclamation marks."""


def numbers_in(obj):
    out = set()
    def walk(x):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            out.add(round(float(x), 1))
            out.add(round(abs(float(x)), 1))   # "fell 76.5%" for a change of -76.5
        elif isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
        elif isinstance(x, str):
            for m in NUMBER.findall(x):
                out.add(round(float(m.replace(",", "")), 1))
    walk(obj)
    return out


def check(text, facts):
    """A takeaway is kept only if it follows the copy rules, never leans on a 0, and every number in it was given."""
    if not text:
        return None, "empty"
    if BANNED.search(text) or ";" in text or "!" in text or len(text) > 320:
        return None, "breaks a copy rule"
    if ZERO.search(text):
        return None, "is about a 0"
    if FLAT.search(text):
        return None, "is about a number with no change"
    given = numbers_in(facts)
    for m in NUMBER.findall(text):
        v = round(float(m.replace(",", "")), 1)
        if v not in given and not (m.isdigit() and int(m) in (1, 2, 3)):   # small counts like "3x" or "2 posts" are allowed
            return None, f"uses {m}, which isn't in the numbers"
    return text, None


def numbers_for_claude(sections):
    return {mode: {s["key"]: {"area": s["title"], "period": s["period"], "period_before": s["period_before"], "numbers": s["facts"],
                              "changes_worth_noting": [x for x in (s["t1"], s["t2"]) if x]}
                   for s in sections[mode] if s["period"]} for mode in MODES}


def from_file(sections):
    """Takeaways Claude Code wrote into data/summary_takeaways.json. Each area view is used only while its period is still the one shown,
    so last week's takeaways never sit on this week's numbers."""
    if not WRITTEN.exists():
        return {}
    saved = json.loads(WRITTEN.read_text())
    out = {}
    for mode in MODES:
        for s in sections[mode]:
            got = (saved.get(mode) or {}).get(s["key"])
            if got and s["period"] and got.get("period") == s["period"] and got.get("period_before") == s["period_before"]:
                out.setdefault(mode, {})[s["key"]] = got
    return out


def ask_claude(sections):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return {}, "no key"
    import anthropic
    client = anthropic.Anthropic()
    ask = numbers_for_claude(sections)
    takeaways = {"type": "object", "additionalProperties": False, "required": ["t1", "t2", "t3"],
                 "properties": {k: {"type": "string"} for k in ("t1", "t2", "t3")}}
    schema = {"type": "object", "additionalProperties": False, "required": list(MODES),
              "properties": {mode: {"type": "object", "additionalProperties": False, "required": [a[0] for a in AREAS],
                                    "properties": {a[0]: takeaways for a in AREAS}} for mode in MODES}}
    try:
        response = client.beta.messages.create(
            model=MODEL, max_tokens=20000, betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            system=SYSTEM, output_config={"effort": "medium", "format": {"type": "json_schema", "schema": schema}},
            messages=[{"role": "user", "content": "Write the 3 takeaways for every area and every period view. The numbers:\n" + json.dumps(ask, indent=1)}])
    except anthropic.APIStatusError as e:
        print(f"Claude returned {e.status_code}, so the Summary is written from the numbers.")
        return {}, f"Claude returned {e.status_code}"
    except anthropic.APIConnectionError:
        print("Couldn't reach Claude, so the Summary is written from the numbers.")
        return {}, "couldn't reach Claude"
    if response.stop_reason == "refusal":
        print("Claude declined, so the Summary is written from the numbers.")
        return {}, "Claude declined"
    try:
        return json.loads(next((b.text for b in response.content if b.type == "text"), "")), None
    except json.JSONDecodeError:
        print("Claude's answer wasn't valid JSON, so the Summary is written from the numbers.")
        return {}, "answer wasn't valid JSON"


def main():
    sections = {}
    for mode in MODES:
        sections[mode] = []
        for key, title, fn, source in AREAS:
            row = {"key": key, "title": title, "tab": key, "source": source, "period": None, "period_before": None,
                   "t1": None, "t2": None, "t3": None, "facts": {}, "note": None}
            NOTES.clear()
            try:
                a = fn(mode)
            except (KeyError, TypeError, ValueError, ZeroDivisionError, AttributeError) as e:
                print(f"  {title} ({mode}): skipped, {type(e).__name__}: {e}")
                a = None
            if a and a["cur"]:
                t1, t2 = written(a)
                row.update({"period": span(*a["cur"]), "period_before": span(*a["prev"]) if a["prev"] else None,
                            "t1": t1, "t2": t2, "facts": a["facts"]})
            row["note"] = NOTES[0] if NOTES else None
            sections[mode].append(row)
    claude, problem = ask_claude(sections)
    if not claude:
        claude = from_file(sections)
        print(f"Takeaways from {WRITTEN.name}: " + (", ".join(f"{m} ({len(v)} areas)" for m, v in claude.items()) or "none for these periods") + ".")
    if "--facts" in sys.argv:   # for Claude Code: the numbers to write from, saved next to the repo, not in it
        FACTS.write_text(json.dumps({"rules": SYSTEM, "views": numbers_for_claude(sections)}, indent=1) + "\n")
        print(f"Wrote the numbers for Claude Code to {FACTS}")
    kept = dropped = 0
    for mode in MODES:
        for s in sections[mode]:
            got = (claude.get(mode) or {}).get(s["key"]) if claude else None
            if not got or not s["period"]:
                continue
            checked = {k: check((got.get(k) or "").strip(), s["facts"]) for k in ("t1", "t2", "t3")}
            for k, (text, why) in checked.items():
                if why and why != "empty":
                    dropped += 1
                    print(f"  {s['title']} ({mode}) takeaway {k[1]} dropped: {why}")
            if not (got.get("t1") or "").strip():
                s["t1"] = s["t2"] = None   # Claude found nothing notable
            elif checked["t1"][0]:
                s["t1"], s["t2"], s["t3"] = checked["t1"][0], checked["t2"][0], checked["t3"][0]
                kept += sum(1 for k in checked if checked[k][0])
            # if Claude's takeaway 1 failed a check, the takeaways written from the numbers stay
    out = {"written_on": dt.date.today().isoformat(), "by_claude": bool(claude), "claude_views": {m: m in claude for m in MODES},
           "model": MODEL if claude else None,
           "problem": problem, "views": sections}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    shown = sum(1 for m in MODES for s in sections[m] if s["t1"])
    print(f"Wrote {OUT.name}: {shown} of {len(MODES) * len(AREAS)} area views have something notable; Claude takeaways kept {kept}, dropped {dropped}")


if __name__ == "__main__":
    main()
