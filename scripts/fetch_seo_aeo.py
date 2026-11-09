"""The SEO and AEO view for execs: Google search and AI tool visits, 1 Jan to 31 Oct 2026, for Opsera overall,
Forge and Insights. Writes data/seo_aeo.json. Agreed with Purav on 6 Nov 2026. Run by hand on this Mac:
    GOOGLE_APPLICATION_CREDENTIALS=~/.config/opsera-dashboard/service-account.json .venv/bin/python scripts/fetch_seo_aeo.py

- Google: clicks and times shown from Search Console, by page and month, and the top keywords by clicks. A keyword
  counts for a product when it brought clicks to that product's pages.
- AI answers: Google Analytics visits from AI tools (ChatGPT, Gemini, Perplexity, Claude, Copilot and others),
  by the page they landed on.
- Content: which pages bring the clicks, each tagged "Infrasity" when it's on Infrasity's content list
  (their Google Sheet "opsera_aeo_content", read 6 Nov 2026), "Insights knowledge base" for /knowledge-base/ articles
  (launched Mar 2026; agreed 9 Nov 2026), otherwise "Opsera".
- Rankings: the pages our Google Rankings panel tracks (data/rankings.json), each with its average Google spot in
  the last week of October and in its first week there.
- Opsera overall is the whole site. A page belongs to Forge or Insights by its address (PRODUCTS); a page can be in neither.
Counts only: no names. Search Console hides rare searches, so keyword clicks add up to less than page clicks.
"""
import calendar
import datetime as dt
import collections
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fetch_data as f   # the same Google sign-in, Search Console and Google Analytics helpers as the Monday update

START, END = "2026-01-01", "2026-10-31"
OUT = Path(__file__).resolve().parent.parent / "data" / "seo_aeo.json"
PRODUCTS = {   # by page address (agreed 6 Nov 2026)
    "forge": re.compile(r"forge|software-factory|moderni[sz]|migrat|cobol|legacy|coldfusion|dotnet|spec-driven|blitzy|8090|factory-ai|devin-ai"
                        r"|comparison-guides/claude"),
    "insights": re.compile(r"insight|dora|space-metrics|ai-code-assistant-analytics|adoption-trends|code-churn|code-quality-metrics|defect-escape"
                           r"|change-and-quality-metrics|core-devex-metrics|incident-analysis|quality-risk|developer-productivity|ai-coding-impact"
                           r"|measure-ai-roi|engineering-metrics"),
}
BRAND = re.compile(r"opsera|opserа|opsra|opersa|ospera|opsea", re.I)
CUSTOMER = re.compile(r"honeywell", re.I)   # customer names stay off the public page
RANKINGS = Path(__file__).resolve().parent.parent / "data" / "rankings.json"
RANK_WEEK = "2026-10-26"   # the last week of October in the Rankings panel
# Infrasity's pages on opsera.ai, from their content list (Published, on opsera.ai). Their posts on Medium, dev.to and daily.dev
# aren't on our site, so Search Console can't see them.
INFRASITY = {"/blog/harness-engineering", "/blog/ai-software-factory", "/blog/software-factory-compliance-tools", "/blog/factory-ai-alternatives",
             "/blog/8090-ai-alternatives", "/blog/blitzy-alternatives", "/blog/software-factory", "/blog/sast-tools", "/blog/devsecops-tools",
             "/blog/ai-sdlc", "/blog/technical-depth-in-ai-sdlc", "/blog/cobol-modernization", "/blog/legacy-code-modernization",
             "/blog/snowflake-to-databricks-migration", "/blog/application-modernization", "/blog/software-factory-model",
             "/blog/java-modernization-architecture", "/resources/comparison-guides/blitzy", "/resources/comparison-guides/devin-ai",
             "/resources/comparison-guides/8090", "/resources/comparison-guides/factory-ai", "/resources/comparison-guides/claude",
             # From their growth reports (July, August and October 2026, in ~/Desktop/Data/infrasity): pages made for SoftwareForge
             # (softwareforge.ai) that moved to opsera.ai, and the September and October sprints. Added 6 Nov 2026.
             "/software-factory", "/blog/generative-ai-security", "/blog/healthcare-data-modernization", "/blog/healthcare-it-modernization",
             "/blog/enterprise-benchmark", "/blog/application-modernization-strategy", "/blog/mcp-security", "/blog/claude-mythos-vulnerability",
             "/blog/software-factory-pattern", "/blog/github-copilot-alternatives", "/blog/migrate-dotnet-framework-to-dotnet-10",
             "/blog/migrate-coldfusion-to-java-spring-boot", "/blog/software-factory-benefits", "/blog/software-factory-as-a-service",
             "/blog/cursor-alternatives"}
INFRASITY_UNDER = ("/forge/modernization/", "/forge/new-apps/")   # their migration and new-app pages, moved onto opsera.ai on 12 Oct
INFRASITY_OFFSITE = 11   # their Distribution posts on Medium, dev.to and daily.dev
# What they published each month, from their reports (Jul and Aug on softwareforge.ai, before it moved to opsera.ai)
INFRASITY_PUBLISHED = [
    {"month": "2026-07", "site": "softwareforge.ai", "pages": 11, "elsewhere": 7, "what": "4 landing pages and 7 blogs on software factory and modernization"},
    {"month": "2026-08", "site": "softwareforge.ai", "pages": 21, "elsewhere": 6, "what": "15 migration and healthcare landing pages, 6 blogs on AI-SDLC and security"},
    {"month": "2026-09", "site": "opsera.ai", "pages": 6, "elsewhere": 4, "what": "Factory.ai and 8090 alternatives, AI software factory and 3 more"},
    {"month": "2026-10", "site": "opsera.ai", "pages": 25, "elsewhere": 4, "what": "12 Forge migration pages, 5 Forge comparisons and 8 blogs, 3 of them out 2 Nov"},
]


def infrasity(path):
    return path in INFRASITY or path.startswith(INFRASITY_UNDER)


def path_of(url):
    p = re.sub(r"^https?://(www\.)?opsera\.ai", "", url)
    return f.page_key(p) if p.startswith("/") else p   # other hosts (forge.opsera.ai) keep their full address


def products(path):
    return ["overall"] + [k for k, rule in PRODUCTS.items() if path.startswith("/") and rule.search(path.lower())]


def months():
    for m in range(1, 11):
        yield f"2026-{m:02d}-01", f"2026-{m:02d}-{calendar.monthrange(2026, m)[1]:02d}"


def main():
    s = f.session()
    site = f.find_gsc_site(s)
    out = {k: {"months": [], "pages": collections.defaultdict(lambda: {"clicks": 0, "times_shown": 0}), "keywords": collections.Counter(),
               "kw_shown": collections.Counter(), "kw_spot": collections.Counter(), "brand_clicks": 0, "keyword_clicks": 0,
               "ai": collections.Counter(), "ai_months": collections.Counter(), "ai_pages": collections.Counter()} for k in ("overall", *PRODUCTS)}
    page_months = collections.defaultdict(collections.Counter)   # page -> month -> clicks
    inf_ai = collections.Counter()   # month -> AI tool visits to Infrasity's pages

    # Google: each month's clicks and times shown, by page
    for a, b in months():
        rows = f.gsc_query(s, site, a, b, ["page"])
        tot = {k: [0, 0] for k in out}
        for r in rows:
            p = path_of(r["keys"][0])
            for k in products(p):
                tot[k][0] += r["clicks"]; tot[k][1] += r["impressions"]
                out[k]["pages"][p]["clicks"] += r["clicks"]; out[k]["pages"][p]["times_shown"] += r["impressions"]
            page_months[p][a[:7]] += r["clicks"]
        site_total = f.gsc_query(s, site, a, b, [])   # the whole site, with nothing hidden
        for k in out:
            if k == "overall":
                clicks, shown = site_total[0]["clicks"], site_total[0]["impressions"]
            else:
                clicks, shown = tot[k]
            out[k]["months"].append({"month": a[:7], "clicks": clicks, "times_shown": shown})
        print(f"  Search Console {a[:7]}: {site_total[0]['clicks']} clicks")

    # Keywords: each search and the page it brought clicks to, for the whole period
    for r in f.gsc_query(s, site, START, END, ["query", "page"]):
        q, p = r["keys"][0], path_of(r["keys"][1])
        if "@" in q or CUSTOMER.search(q):
            continue
        for k in products(p):
            out[k]["keywords"][q] += r["clicks"]; out[k]["kw_shown"][q] += r["impressions"]
            out[k]["kw_spot"][q] += r["position"] * r["impressions"]
            out[k]["keyword_clicks"] += r["clicks"]
            if BRAND.search(q):
                out[k]["brand_clicks"] += r["clicks"]

    # AI answers: visits from AI tools, by the page they landed on
    for r in f.ga_report(s, END, ["yearMonth", "landingPage", "sessionDefaultChannelGroup", "sessionSource"], ["sessions", "engagedSessions"], start=START):
        tool = f.ai_tool(r["sessionDefaultChannelGroup"], r["sessionSource"])
        if not tool:
            continue
        p = f.page_key(r["landingPage"]) if r["landingPage"].startswith("/") else "Page not recorded"
        for k in products(p):
            out[k]["ai"][tool] += r["sessions"]
            out[k]["ai_months"][f"{r['yearMonth'][:4]}-{r['yearMonth'][4:]}"] += r["sessions"]
            out[k]["ai_pages"][p] += r["sessions"]
        if infrasity(p):
            inf_ai[f"{r['yearMonth'][:4]}-{r['yearMonth'][4:]}"] += r["sessions"]

    ranked = json.loads(RANKINGS.read_text())["pages"]
    def spots(pg):
        weeks = [w for w in pg["weeks"] if w.get("avg_spot") is not None and w["week"] <= RANK_WEEK]
        return (weeks[0], weeks[-1]) if weeks else (None, None)

    result = {"source": "Google Search Console (sc-domain:opsera.ai) and Google Analytics 4, opsera.ai 2026",
              "start_date": START, "end_date": END, "pulled": dt.date.today().isoformat(), "rankings_week": RANK_WEEK,
              "infrasity": {"list": "Infrasity's content list, Google Sheet opsera_aeo_content, read 6 Nov 2026",
                            "pages_on_site": len({p for p in page_months if infrasity(p)} | INFRASITY), "posts_elsewhere": INFRASITY_OFFSITE,
                            "published": INFRASITY_PUBLISHED,
                            "months": [{"month": a[:7], "clicks": sum(m[a[:7]] for p, m in page_months.items() if infrasity(p)),
                                        "ai_visits": inf_ai.get(a[:7], 0)} for a, _ in months() if a >= "2026-07"]},
              "products": {}}
    for k, v in out.items():
        def by(page):   # knowledge base articles are their own group (Purav, 9 Nov 2026)
            return "Infrasity" if infrasity(page) else "Insights knowledge base" if page.startswith("/knowledge-base/") else "Opsera"
        pages = sorted(v["pages"].items(), key=lambda x: -x[1]["clicks"])
        inf_clicks = sum(x["clicks"] for p, x in pages if by(p) == "Infrasity")
        kb = [(p, x) for p, x in pages if by(p) == "Insights knowledge base"]
        top_kw = [q for q, _ in v["keywords"].most_common() if not BRAND.search(q)][:10]
        show = lambda p: "/resources/webinars/(a customer's modernization webinar)" if CUSTOMER.search(p) else p
        result["products"][k] = {
            "months": v["months"],
            "clicks": sum(m["clicks"] for m in v["months"]), "times_shown": sum(m["times_shown"] for m in v["months"]),
            "brand_share_pct": round(v["brand_clicks"] / v["keyword_clicks"] * 100, 1) if v["keyword_clicks"] else None,
            "keywords": [{"keyword": q, "clicks": v["keywords"][q], "times_shown": v["kw_shown"][q],
                          "avg_spot": round(v["kw_spot"][q] / v["kw_shown"][q], 1) if v["kw_shown"][q] else None} for q in top_kw],
            "pages_with_clicks": sum(1 for _, x in pages if x["clicks"]),
            "kb_clicks": sum(x["clicks"] for _, x in kb), "kb_pages_with_clicks": sum(1 for _, x in kb if x["clicks"]),
            "infrasity_clicks": inf_clicks, "infrasity_pages_with_clicks": sum(1 for p, x in pages if by(p) == "Infrasity" and x["clicks"]),
            "top_pages": [{"page": show(p), "clicks": x["clicks"], "times_shown": x["times_shown"], "by": by(p),
                           "ai_visits": v["ai_pages"].get(p, 0), "months": [page_months[p].get(a[:7], 0) for a, _ in months()]} for p, x in pages[:10]],
            "tracked": [{"page": pg["page"], "group": pg["group"], "first_week": first["week"], "first_spot": first["avg_spot"], "spot": last["avg_spot"], "by": by(pg["page"])}
                        for pg in ranked for first, last in [spots(pg)] if last and k in products(pg["page"])],
            "ai_visits": sum(v["ai"].values()), "ai_tools": dict(v["ai"].most_common()),
            "ai_months": [{"month": a[:7], "visits": v["ai_months"].get(a[:7], 0)} for a, _ in months()],
            "ai_top_pages": [{"page": show(p), "visits": n, "by": by(p)} for p, n in v["ai_pages"].most_common() if p != "Page not recorded"][:5],
            "ai_page_not_recorded": v["ai_pages"].get("Page not recorded", 0),
        }
        r = result["products"][k]
        print(f"{k}: {r['clicks']} clicks, {r['times_shown']} times shown, {r['ai_visits']} AI visits, Infrasity {inf_clicks} clicks")
    OUT.write_text(json.dumps(result, indent=1) + "\n")


if __name__ == "__main__":
    main()
