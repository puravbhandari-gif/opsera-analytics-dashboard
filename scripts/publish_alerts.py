"""Each morning, post one Slack line in #core-marketing-team for every new blog, resource page or YouTube video (agreed with
Purav, 18 Nov 2026). Blogs and resource pages come from Contentful, videos from the channel's public YouTube feed, never
from the sitemap (it can run a day behind).

Needs CONTENTFUL_DELIVERY_TOKEN (a read-only Content Delivery API token) and SLACK_WEBHOOK_URL (the same webhook as the
weekly post). Run with --dry-run to print the lines instead of posting them.

- "New" means not in data/publish_alerts_seen.json. The first run only records what's already live and posts nothing.
- A piece counts once its page opens on opsera.ai. A Contentful entry whose page isn't live yet waits for the next run.
- More than 10 new pieces at once looks like an import, not a launch day, so nothing is posted and the run says so.
- No emojis. The webhook address is never printed.
"""
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests

SPACE = "f2pywbu2ld1m"
YOUTUBE_CHANNEL = "UCpnT0NdkrOWp8v3bodeCGhQ"
SEEN = Path(__file__).resolve().parent.parent / "data" / "publish_alerts_seen.json"
MAX_NEW = 10
# Resource kinds in Contentful and where each one lives on opsera.ai (checked 18 Nov 2026)
RESOURCE_PATHS = {"White paper": ("white-papers", "New white paper"), "Report": ("report", "New report"), "eBook": ("ebooks", "New eBook"),
                  "Webinar": ("webinars", "New webinar"), "Comparison guide": ("comparison-guides", "New comparison guide"),
                  "DevOps Huddle": ("devops-huddles", "New DevOps Huddle episode"), "Video": ("videos", "New video page")}
HEADERS = {"User-Agent": "Mozilla/5.0 (opsera-analytics-dashboard)"}


def contentful(token):
    """Every published blog post and resource page: (id, label, title, link)."""
    out = []
    for kind in ("post", "resource"):
        r = requests.get(f"https://cdn.contentful.com/spaces/{SPACE}/environments/master/entries", timeout=60,
                         headers={"Authorization": f"Bearer {token}"},
                         params={"content_type": kind, "limit": 1000, "locale": "en-US",
                                 "select": "sys.id,fields.title,fields.slug" + (",fields.kind" if kind == "resource" else "")})
        if r.status_code != 200:
            sys.exit(f"Contentful returned {r.status_code} for {kind}, so nothing was posted.")
        for e in r.json().get("items", []):
            f = e.get("fields", {})
            if not f.get("slug") or not f.get("title"):
                continue
            if kind == "post":
                out.append((f"cf:{e['sys']['id']}", "New blog", f["title"], f"https://opsera.ai/blog/{f['slug']}"))
            elif f.get("kind") in RESOURCE_PATHS:
                path, label = RESOURCE_PATHS[f["kind"]]
                out.append((f"cf:{e['sys']['id']}", label, f["title"], f"https://opsera.ai/resources/{path}/{f['slug']}"))
    return out


def youtube():
    """The channel's public videos from its feed (the latest 15): (id, label, title, link)."""
    r = requests.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={YOUTUBE_CHANNEL}", headers=HEADERS, timeout=60)
    if r.status_code != 200:
        sys.exit(f"The YouTube feed returned {r.status_code}, so nothing was posted.")
    ns = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
    return [(f"yt:{e.find('yt:videoId', ns).text}", "New YouTube video", e.find("a:title", ns).text,
             f"https://www.youtube.com/watch?v={e.find('yt:videoId', ns).text}") for e in ET.fromstring(r.content).findall("a:entry", ns)]


def is_live(link):
    try:
        return requests.get(link, headers=HEADERS, timeout=30, allow_redirects=True).status_code == 200
    except requests.RequestException:
        return False


def slack(lines):
    secret = os.environ.get("SLACK_WEBHOOK_URL") or ""
    found = re.search(r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]+", secret)
    if not found:
        sys.exit("SLACK_WEBHOOK_URL doesn't contain a Slack webhook address, so nothing was posted.")
    for line in lines:
        r = requests.post(found.group(0), json={"text": line}, timeout=30)
        if r.status_code != 200:
            sys.exit(f"Slack returned {r.status_code}, so the rest wasn't posted.")


def main():
    dry = "--dry-run" in sys.argv
    token = os.environ.get("CONTENTFUL_DELIVERY_TOKEN")
    if not token:
        sys.exit("CONTENTFUL_DELIVERY_TOKEN is not set, so nothing was checked or posted.")
    pieces = contentful(token) + youtube()
    if not SEEN.exists():
        if not dry:
            SEEN.write_text(json.dumps({"seen": sorted(p[0] for p in pieces)}, indent=1) + "\n")
        print(f"First run: recorded {len(pieces)} pieces already live. Nothing posted.")
        return
    seen = set(json.loads(SEEN.read_text())["seen"])
    new = [p for p in pieces if p[0] not in seen]
    if len(new) > MAX_NEW:
        sys.exit(f"{len(new)} new pieces at once looks like an import, so nothing was posted. Check them, then add them to {SEEN.name}.")
    live = [p for p in new if p[0].startswith("yt:") or is_live(p[3])]
    waiting = len(new) - len(live)
    lines = [f"{label} live: <{link}|{title}>" for _, label, title, link in live]
    print("\n".join(lines) or "Nothing new today.")
    if waiting:
        print(f"{waiting} new in Contentful but not live on opsera.ai yet; checked again tomorrow.")
    if dry or not lines:
        return
    slack(lines)
    SEEN.write_text(json.dumps({"seen": sorted(seen | {p[0] for p in live})}, indent=1) + "\n")


if __name__ == "__main__":
    main()
