"""List everything Opsera published from 1 Jul 2026 for the Content tab's "Published this quarter":
blog posts, reports, white papers, eBooks, guides, webinars and YouTube videos, with the date and a link.
Writes data/published.json. Runs every Monday after fetch_youtube.py.

Pages come from opsera.ai's sitemap. Each page's date is the publish date the page itself states
(datePublished, or article:published_time). A page with no publish date is left out and counted.
YouTube videos come from data/youtube.json (public videos only), so this makes no YouTube calls.
Agreed with Purav on 4 Nov 2026.
"""
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
        title = re.sub(r"\s*[|-]\s*Opsera\s*$", "", title)
        title = title.translate(str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'}))
    return url, (m.group(1) if m else None), title


def main():
    r = requests.get(SITEMAP, headers=HEADERS, timeout=60)
    if r.status_code != 200:
        stop(f"The sitemap returned {r.status_code}.")
    urls = [u.strip() for u in re.findall(r"<loc>([^<]+)</loc>", r.text)]
    wanted = {}
    for u in urls:
        path = re.sub(r"^https?://(www\.)?opsera\.ai", "", u).rstrip("/")
        k = kind(path)
        if k:
            wanted[u] = (path, k)
    if len(wanted) < 100:
        stop(f"Only {len(wanted)} content pages in the sitemap, which looks wrong.")

    rows, undated = [], []
    with concurrent.futures.ThreadPoolExecutor(8) as pool:
        for url, date, title in pool.map(page_facts, wanted):
            path, k = wanted[url]
            if not date:
                undated.append(path)
            elif date >= START:
                rows.append({"date": date, "type": k, "title": title or path, "link": url})

    yt = json.loads((DATA / "youtube.json").read_text())
    for v in yt["channel"]["published"]:
        if v["date"] >= START:
            rows.append({"date": v["date"], "type": "YouTube short" if v["type"] == "shorts" else "YouTube video",
                         "title": v["title"], "link": f"https://www.youtube.com/watch?v={v['id']}"})

    rows.sort(key=lambda x: (x["date"], x["title"]), reverse=True)
    OUT.write_text(json.dumps({
        "source": "opsera.ai sitemap, with each page's own publish date, and YouTube Analytics for public videos",
        "start_date": START, "checked": dt.date.today().isoformat(), "youtube_pulled_at": yt["pulled_at"],
        "pages_checked": len(wanted), "pages_without_date": len(undated), "items": rows,
    }, indent=1) + "\n")
    print(f"Checked {len(wanted)} pages ({len(undated)} without a publish date). Published since {START}: {len(rows)}")
    for k in sorted({x['type'] for x in rows}):
        print(f"  {k}: {sum(x['type'] == k for x in rows)}")


if __name__ == "__main__":
    main()
