"""List everything Opsera published from 1 Jul 2026 for the Content tab's "Published this quarter":
blog posts, reports, white papers, eBooks, guides, webinars and YouTube videos, with the date and a link.
Writes data/published.json. Runs every Monday after fetch_youtube.py.

Pages come from opsera.ai's sitemap. Each page's date is the publish date the page itself states
(datePublished, or article:published_time). A page with no publish date is left out and counted, except knowledge
base articles: they take their last edit on the old WordPress site, from data/kb_dates.json (read from Contentful on
9 Nov 2026), since the site shows no publish date for them.
YouTube videos come from data/youtube.json (public videos only), so this makes no YouTube calls.
Agreed with Purav on 4 Nov 2026.

Blogs come from Contentful instead (agreed 18 Nov 2026), since the sitemap can run a day behind: every published blog post,
dated by its own date field, counted only once its page opens on opsera.ai, so drafts and pages not live yet are left out.
Needs CONTENTFUL_DELIVERY_TOKEN (read-only Content Delivery API token).
"""
import os
import concurrent.futures
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path

import requests

START = "2026-07-01"
SITEMAP = "https://opsera.ai/sitemap.xml"
# Pages live on opsera.ai but not yet in the sitemap. Each still uses the publish date the page states (17 Nov 2026).
# Blogs no longer need this: they come from Contentful (18 Nov 2026).
NOT_IN_SITEMAP = []
CONTENTFUL_SPACE = "f2pywbu2ld1m"
DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "published.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (opsera-analytics-dashboard)"}
TYPES = [   # the Content tab's own types, plus webinars
    (r"^/blog/[a-z0-9-]+$", "Blog"),
    (r"^/resources/report/[a-z0-9-]+$", "Report"),
    (r"^/resources/white-papers/[a-z0-9-]+$", "White paper"),
    (r"^/resources/ebooks/[a-z0-9-]+$", "eBook"),
    (r"^/knowledge-base/(?!category/)[a-z0-9-]+/[a-z0-9-]+$", "Guide"),
    (r"^/(resources/comparison-guides|comparison-guides|comparison)/[a-z0-9-]+$", "Guide"),
    (r"^/resources/webinars/[a-z0-9-]+$", "Webinar"),
]


def stop(msg):
    print(f"\nSTOPPED: {msg}", file=sys.stderr)
    sys.exit(1)


def kind(path):
    return next((name for rule, name in TYPES if re.match(rule, path)), None)


def page_facts(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
    except requests.RequestException:
        return url, None, None
    if r.status_code != 200:
        return url, None, None
    m = re.search(r'"datePublished"\s*:\s*"(\d{4}-\d{2}-\d{2})', r.text) or \
        re.search(r'article:published_time"\s+content="(\d{4}-\d{2}-\d{2})', r.text)
    t = re.search(r'<meta property="og:title" content="([^"]*)"', r.text) or re.search(r"<title>(.*?)</title>", r.text, re.S)
    title = html.unescape(t.group(1)).strip() if t else None
    if title:
        title = re.sub(r"(\s*[|-]\s*Opsera( Forge)?)+\s*$", "", title)
        title = title.translate(str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}))
    return url, (m.group(1) if m else None), title


def contentful_blogs(token):
    """Every published blog post in Contentful from START: (date, title, link)."""
    r = requests.get(f"https://cdn.contentful.com/spaces/{CONTENTFUL_SPACE}/environments/master/entries", timeout=60,
                     headers={"Authorization": f"Bearer {token}"},
                     params={"content_type": "post", "limit": 1000, "locale": "en-US", "select": "fields.title,fields.slug,fields.date"})
    if r.status_code != 200:
        stop(f"Contentful returned {r.status_code}.")
    items = r.json().get("items", [])
    if len(items) < 100:
        stop(f"Only {len(items)} blog posts in Contentful, which looks wrong.")
    out = []
    for e in items:
        f = e.get("fields", {})
        if f.get("slug") and f.get("title") and (f.get("date") or "")[:10] >= START:
            out.append((f["date"][:10], f["title"].strip(), f"https://opsera.ai/blog/{f['slug']}"))
    return out


def page_live(link):
    try:
        return requests.get(link, headers=HEADERS, timeout=30).status_code == 200
    except requests.RequestException:
        return False


def main():
    token = os.environ.get("CONTENTFUL_DELIVERY_TOKEN")
    if not token:
        stop("CONTENTFUL_DELIVERY_TOKEN is not set, so blogs can't be read from Contentful.")
    blogs = contentful_blogs(token)
    r = requests.get(SITEMAP, headers=HEADERS, timeout=60)
    if r.status_code != 200:
        stop(f"The sitemap returned {r.status_code}.")
    urls = [u.strip() for u in re.findall(r"<loc>([^<]+)</loc>", r.text)]
    urls += [u for u in NOT_IN_SITEMAP if u not in urls]
    wanted = {}
    for u in urls:
        path = re.sub(r"^https?://(www\.)?opsera\.ai", "", u).rstrip("/")
        k = kind(path)
        if k and k != "Blog":   # blogs come from Contentful
            wanted[u] = (path, k)
    if len(wanted) < 30:
        stop(f"Only {len(wanted)} content pages other than blogs in the sitemap, which looks wrong.")

    kb_dates = json.loads((DATA / "kb_dates.json").read_text())["dates"] if (DATA / "kb_dates.json").exists() else {}
    rows, undated = [], []
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        for url, date, title in pool.map(page_facts, wanted):
            path, k = wanted[url]
            date = date or kb_dates.get(path)
            if not date:
                undated.append(path)
            elif date >= START:
                rows.append({"date": date, "type": k, "title": title or path, "link": url})

    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        live = list(pool.map(lambda b: page_live(b[2]), blogs))
    rows += [{"date": d, "type": "Blog", "title": t, "link": l} for (d, t, l), ok in zip(blogs, live) if ok]
    not_live = [l for (d, t, l), ok in zip(blogs, live) if not ok]

    yt = json.loads((DATA / "youtube.json").read_text())
    for v in yt["channel"]["published"]:
        if v["date"] >= START:
            rows.append({"date": v["date"], "type": "YouTube short" if v["type"] == "shorts" else "YouTube video",
                         "title": v["title"], "link": f"https://www.youtube.com/watch?v={v['id']}"})

    rows.sort(key=lambda x: (x["date"], x["title"]), reverse=True)
    OUT.write_text(json.dumps({
        "source": "Contentful for blogs (published and live on opsera.ai), the opsera.ai sitemap with each page's own publish date for other pages, and YouTube Analytics for public videos",
        "blogs_not_live": len(not_live),
        "start_date": START, "checked": dt.date.today().isoformat(), "youtube_pulled_at": yt["pulled_at"],
        "pages_checked": len(wanted), "pages_without_date": len(undated), "items": rows,
    }, indent=1) + "\n")
    print(f"Checked {len(wanted)} pages ({len(undated)} without a publish date). Published since {START}: {len(rows)}")
    for k in sorted({x['type'] for x in rows}):
        print(f"  {k}: {sum(x['type'] == k for x in rows)}")


if __name__ == "__main__":
    main()
