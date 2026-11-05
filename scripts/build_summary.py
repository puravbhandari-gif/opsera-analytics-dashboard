"""Write data/summary.json for the Summary tab, for Week, Month, Quarter and 3 months (Day shows Week).

At the top: 3 boxes across all areas, "Going well", "Needs attention" and "Do this week", 3 short lines each.
Below: one card per area with a main number and its change, why it matters, what to do, and a 6-week trend line.
Areas with nothing notable go in one line at the bottom.
Claude Code writes the lines into data/summary_takeaways.json when Purav asks "write this week's Summary takeaways"
(run with --facts first for the numbers). They're checked here: under 12 words, only numbers from the data, never a 0
or an unchanged number, and the copy rules. Without them, the cards and boxes come from the numbers, and only for real changes.
Agreed with Purav on 3 Nov 2026.
Run: .venv/bin/python scripts/build_summary.py
"""
import collections
import datetime as dt
import json
import re
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "summary.json"
WRITTEN = DATA / "summary_takeaways.json"   # takeaways Claude Code writes when asked, checked here like the API's
FACTS = Path(__file__).resolve().parent.parent.parent / "summary_facts.json"   # the numbers for Claude Code, outside the repo
MODES = ("week", "month", "cq", "quarter")   # the Summary has no Day view: the page shows Week instead. cq is the fiscal quarter
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
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


def quarter_start(s):   # Opsera's fiscal quarters (agreed 5 Nov 2026): the year starts in February, so Q4 is Nov to Jan
    return add_months(month_start(s), -(((int(s[5:7]) + 10) % 12) % 3))


def quarter_end(s):
    return month_end(add_months(quarter_start(s), 2))


def quarter_name(s):
    return f"FY{(int(s[:4]) + (1 if int(s[5:7]) >= 2 else 0)) % 100:02d} Q{(int(s[5:7]) + 10) % 12 // 3 + 1}"


def periods_for(mode, start, last, full_month=True):
    """The dashboard's periods (periodsFor in app.js): this period and the one before, or None.
    mode can also be ("span", first, last): one fixed range with nothing before it, for the trend lines."""
    if isinstance(mode, tuple):
        return ((mode[1], mode[2]) if mode[1] >= start and mode[2] <= last else None), None, ""
    if mode == "cq":   # fiscal quarters (Q3 is Aug to Oct): this quarter so far against the same days of the quarter before
        cur = (quarter_start(last), last)
        if cur[0] < start:
            return None, None, ""
        p = quarter_start(add_days(cur[0], -1))
        if 2 * ((d(last) - d(cur[0])).days + 1) < (d(quarter_end(cur[0])) - d(cur[0])).days + 1 and p >= start:
            # under half done: the last full quarter against the whole quarter before, like the Month view (agreed 5 Nov 2026)
            b = quarter_start(add_days(p, -1))
            return (p, quarter_end(p)), ((b, quarter_end(b)) if b >= start else None), f"in {quarter_name(b)}"
        pe = min(add_days(p, (d(last) - d(cur[0])).days), quarter_end(p))
        return cur, ((p, pe) if p >= start else None), f"in the same days of {quarter_name(p)}"
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


def area(cur, prev, before, facts, mains=(), details=(), rel=0.15, lead_with=None):
    """mains: (key, label, cur, prev, floor[, fmt]), most important first. details: (key, text) worth saying; "after:" keys go last."""
    mains = [m if len(m) == 6 else (*m, n) for m in mains]
    for key, _, c, p, _, _ in mains:
        facts.setdefault(key, c)
        facts.setdefault(key + "_before", p)
        if p:
            facts.setdefault(key + "_change_pct", pct(c, p))
    return {"cur": cur, "prev": prev, "before": before, "facts": facts, "mains": mains, "details": list(details), "rel": rel, "lead_with": lead_with}


def headline(a, key=None):
    """The card's main number: the given main, else the most important real change, else the first main if the area has a lead."""
    mains = {m[0]: m for m in a["mains"]}
    real = [m for m in a["mains"] if a["prev"] and notable(m[2], m[3], m[4], a["rel"])]
    if a.get("lead_with") and (real or a.get("lead") or mains[a["lead_with"]][2]):
        key = a["lead_with"]   # Leads always leads with demo requests (agreed 3 Nov 2026)
    m = mains.get(key) if key else (real[0] if real else (a["mains"][0] if a.get("lead") and a["mains"] else None))
    if not m:
        return None
    k, label, c, p, _, fmt = m
    return {"key": k, "label": label, "value": fmt(c), "cur": c, "prev": p, "before": fmt(p) if p is not None else None,
            "change_pct": pct(c, p), "good": None if not p or c == p else c > p, "min_change_pct": round(a["rel"] * 100)}   # every main is better when it goes up


def short_line(text):
    return text if text and len(text.split()) < 12 else None


def pipeline(mode):
    sf = load("salesforce_pipeline.json")
    last = add_days(sf["exports"]["opportunities"], -1)
    cur, prev, before = periods_for(mode, sf["opportunities_cover_from"], last)
    if not cur:
        return None
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
    if not cur:
        return None
    t = lambda k, p: total(l["daily"], k, *p) if p else None
    ev, evp = t("events", cur), t("events", prev)
    details = [("events_form_fills", f"Event sign-ups: {n(ev)}, {'up' if ev > evp else 'down'} from {n(evp)}.")] if prev and notable(ev, evp, 5) else []
    return area(cur, prev, before, {}, [("demo_requests", "Demo requests", t("demo", cur), t("demo", prev), 5)] +
                [(f"{k}_form_fills", l["lines"][k]["label"], t(k, cur), t(k, prev), 5) for k in ("events", "contact", "gartner_offer")],
                details, lead_with="demo_requests")


def journey(mode):
    hub = load("hubspot.json")
    cur, prev, before = periods_for(mode, hub["start_date"], hub["end_date"])
    if not cur:
        return None
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
    if not cur:
        return None
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
                details, rel=0.10)   # website visits move less, so 10% counts (agreed 3 Nov 2026)
    if jump:
        a["lead"] = details[0]   # worth saying even when real visits barely moved
        a["short"] = f"Unlabelled visits jumped to {n(un[0])}, likely robots."
    return a


def search(mode):
    g = load("search_console.json")
    cur, prev, before = periods_for(mode, g["start_date"], g["last_day_with_data"])
    if not cur:
        return None
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
    if not cur:
        return None
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
    if not cur:
        return None
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
    if not cur:
        return None
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
    big = "attended" if e.get("attended") else "signed_up"
    if e.get(big):
        a["headline"] = {"key": big, "label": f"{e['name']}: {'attended' if big == 'attended' else 'signed up'}", "value": n(e[big]),
                         "cur": e[big], "prev": None, "before": None, "change_pct": None, "good": None}
        a["short"] = (f"{n(e['signed_up'])} signed up. " if big == "attended" and e.get("signed_up") else "") + \
                     (f"{n(met)} had a meeting since." if met else "")
    if met:
        a["details"].append(("met", f"{n(met)} people from its Salesforce campaign have had a meeting since."))
    if len(inside) > 1:
        a["details"].append(("count", f"{len(inside)} events ended in this period."))
    return a


def content(mode):
    lk = load("lookup.json")
    cur, prev, before = periods_for(mode, lk["start_date"], last_full_day_pacific(lk["end_date"], lk["pulled_at"]))
    if not cur:
        return None
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
    if not cur:
        return None
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
    if not cur:
        return None
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
    if not cur:
        return None
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




# ---------- the lines: written by Claude Code when asked, or from the numbers ----------

BANNED = re.compile(r"\bthat\b|—|–|\bjourney\b|\bleverage\b|\bsynergy\b|\bunlock\b|\bdelve\b", re.I)
NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")
FLAT = re.compile(r"\b(stayed|unchanged|the same|flat|held steady|no change|steady)\b", re.I)
ZERO = re.compile(r"(?<![\d.,])\$?0(?![\d.,]*\d)")   # a standalone 0, like "0 deals" or "$0"

RULES = """Write the Summary lines for each period view (week, month, quarter) from these numbers only.
- 3 boxes across all areas, 3 lines each, most important first: "well" (going well), "attention" (needs attention), "do" (do this week).
- For each area: "main", the key of the number to show large (one of its mains, or "" if the area has nothing notable), "why" (why it matters) and "do" (what to do).
- A suggestion ("do", and the "do" box) must come from our own numbers and name them, for example "Kumar's 3 video posts got 2x the comments of his text posts".
  Never give best-practice advice or a generic tip. If the data doesn't support a specific suggestion, leave "do" empty. The "do" box can have fewer than 3 lines.
- Every line is under 12 words. Plain English, sentence case, numerals, active voice, at most 2 commas.
- Use only numbers given for that view. A *_change_pct can be written without its minus sign ("fell 76.5%").
- Never write about a 0, an unchanged number or anything tiny (under 15%, or 10% for website visits). Unlabelled visit jumps are likely robots, never growth.
- Leads always has "demo_requests" as its main, with event sign-ups as the second line if they moved.
- LinkedIn counts every click on a post, so a post's clicks can be higher than its views. Never set a post's clicks against its views.
- Never use "that", dashes, semicolons, "journey", "leverage", "unlock" or exclamation marks.
- Copy each view's and each area's period and period_before exactly, or the lines are ignored."""


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


def check(text, facts, suggestion=False):
    """A line is kept only if it's under 12 words, follows the copy rules, never leans on a 0, and every number in it was given.
    A suggestion must also name a number from our data: no best-practice tips (agreed 3 Nov 2026)."""
    if not text:
        return None, "empty"
    if suggestion and not NUMBER.search(text):
        return None, "is a suggestion with no number from our data"
    if len(text.split()) >= 12:
        return None, "is 12 words or more"
    if BANNED.search(text) or ";" in text or "!" in text:
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


def trend(fn, key, week_cur):
    """The headline number for each of the last 6 full weeks, oldest first."""
    if not week_cur or not key:
        return []
    out = []
    for i in range(5, -1, -1):
        a, b = add_days(week_cur[0], -7 * i), add_days(week_cur[1], -7 * i)
        got = fn(("span", a, b))
        m = next((m for m in (got or {}).get("mains", []) if m[0] == key), None)
        out.append({"week": span(a, b), "value": m[2] if m else None})
    return out


def from_numbers(view):
    """The boxes without Claude Code: the biggest real moves up and down. No "Do this week" without Claude Code."""
    moves = [(s["title"], s["main"]) for s in view["areas"]
             if s["notable"] and s["main"] and s["main"]["good"] is not None and abs(s["main"]["change_pct"]) >= s["main"].get("min_change_pct", 15)]
    up = sorted((m for m in moves if m[1]["good"]), key=lambda m: -abs(m[1]["change_pct"]))
    down = sorted((m for m in moves if not m[1]["good"]), key=lambda m: -abs(m[1]["change_pct"]))
    line = lambda m, w: short_line(f"{m[1]['label']} {w} {abs(m[1]['change_pct']):g}%")
    return {"well": [x for x in (line(m, "up") for m in up) if x][:3], "attention": [x for x in (line(m, "down") for m in down) if x][:3], "do": []}


def main():
    saved = json.loads(WRITTEN.read_text()) if WRITTEN.exists() else {}
    week_runs = {}
    views, facts_out, kept, dropped = {}, {}, 0, 0   # mains is taken off each row once it's in the facts
    for mode in MODES:
        areas, all_facts = [], {}
        written = saved.get(mode) or {}
        for key, title, fn, source in AREAS:
            NOTES.clear()
            try:
                a = fn(mode)
                if mode == "week":
                    week_runs[key] = a
            except (KeyError, TypeError, ValueError, ZeroDivisionError, AttributeError) as e:
                print(f"  {title} ({mode}): skipped, {type(e).__name__}: {e}")
                a = None
            row = {"key": key, "title": title, "tab": key, "source": source, "note": NOTES[0] if NOTES else None,
                   "period": span(*a["cur"]) if a else None, "period_before": span(*a["prev"]) if a and a["prev"] else None,
                   "notable": False, "main": None, "why": None, "do": None, "trend": []}
            if a:
                all_facts[key] = a["facts"]
                w = (written.get("areas") or {}).get(key)
                if w and (w.get("period"), w.get("period_before")) != (row["period"], row["period_before"]):
                    w = None   # written for another period, so last week's lines never sit on this week's numbers
                main_ = a.get("headline") or headline(a, w.get("main") if w and w.get("main") else None)
                if w:
                    row["notable"] = bool(w.get("main")) and bool(main_)
                    for k in ("why", "do"):
                        text, why_not = check((w.get(k) or "").strip(), a["facts"], suggestion=k == "do")
                        row[k] = text
                        kept += bool(text)
                        if why_not and why_not != "empty":
                            dropped += 1
                            print(f"  {title} ({mode}) {k} dropped: {why_not}")
                else:
                    row["notable"] = bool(main_)   # headline() only gives a number for a real change, a lead or an event
                    row["why"] = short_line(a.get("short")) or next((x for x in (short_line(t) for _, t in a["details"]) if x), None)
                row["main"] = main_ if row["notable"] else None
                if row["main"] and any(m[0] == row["main"]["key"] for m in a["mains"]):
                    row["trend"] = trend(fn, row["main"]["key"], (week_runs.get(key) or {}).get("cur"))
                row["mains"] = [m[0] for m in a["mains"]]
            areas.append(row)
        periods = collections.Counter((s["period"], s["period_before"]) for s in areas if s["period"])
        top = periods.most_common(1)[0][0] if periods else (None, None)
        view = {"period": top[0], "period_before": top[1], "areas": areas}
        boxes = written.get("boxes") if (written.get("period"), written.get("period_before")) == top else None
        view["by_claude"] = bool(boxes)
        if boxes:
            view["boxes"] = {}
            for b in ("well", "attention", "do"):
                good = []
                for text in (boxes.get(b) or [])[:3]:
                    t, why_not = check(text.strip(), all_facts, suggestion=b == "do")
                    if t:
                        good.append(t); kept += 1
                    else:
                        dropped += 1
                        print(f"  box {b} ({mode}) dropped: {why_not}: {text}")
                view["boxes"][b] = good
        else:
            view["boxes"] = from_numbers(view)
        views[mode] = view
        facts_out[mode] = {"period": top[0], "period_before": top[1],
                           "areas": {s["key"]: {"area": s["title"], "period": s["period"], "period_before": s["period_before"],
                                                "mains": s.pop("mains", []),
                                                "numbers": all_facts.get(s["key"])} for s in areas if s["period"]}}
    if "--facts" in sys.argv:   # for Claude Code: the numbers to write from, saved next to the repo, not in it
        FACTS.write_text(json.dumps({"rules": RULES, "views": facts_out}, indent=1) + "\n")
        print(f"Wrote the numbers for Claude Code to {FACTS}")
    OUT.write_text(json.dumps({"written_on": dt.date.today().isoformat(), "views": views}, indent=1) + "\n")
    print(f"Wrote {OUT.name}: " + ", ".join(f"{m} {sum(s['notable'] for s in v['areas'])} notable areas" + (" (Claude Code's lines)" if v["by_claude"] else "")
                                            for m, v in views.items()) + f"; lines kept {kept}, dropped {dropped}")


if __name__ == "__main__":
    main()
