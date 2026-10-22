"""Find every LinkedIn post since 1 Sep 2026 from the Opsera company page and from
Kumar Chivukula that links to opsera.ai, with the date and the page it links to.
Writes data/linkedin_posts.json. Used only for the "Estimated" LinkedIn lines.

Posts come from two Apify tools that read public posts without a LinkedIn login:
harvestapi/linkedin-company-posts and harvestapi/linkedin-profile-posts.
Needs the APIFY_TOKEN env var (a GitHub secret). Reposts are left out: a repost's
link belongs to whoever wrote the original. Comments are read too, so a link the
account itself put in a comment (such as "link in first comment") counts, dated
when the comment was posted. Comments by anyone else are ignored.

    python3 scripts/fetch_linkedin_posts.py                 # runs the two Apify tools
    python3 scripts/fetch_linkedin_posts.py --from posts.json   # uses posts already saved
"""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests

START_DATE = "2026-09-01"
ACCOUNTS = [
    ("company", "harvestapi~linkedin-company-posts", "https://www.linkedin.com/company/opsera"),
    ("kumar", "harvestapi~linkedin-profile-posts", "https://www.linkedin.com/in/kumar-chivukula/"),
]
OWN = {"company": "/company/opsera", "kumar": "/in/kumar-chivukula"}   # whose posts and comments count
MAX_COMMENTS = 10    # per post; the account's own first comment is usually among the first few
MAX_CHARGE_USD = 2   # each weekly run costs about $0.10 to $0.40; this caps a run that goes wrong
OUT = Path(__file__).resolve().parent.parent / "data" / "linkedin_posts.json"
PACIFIC = ZoneInfo("America/Los_Angeles")   # Google Analytics days follow US Pacific time
URL = re.compile(r"https?://[^\s<>\"')\]]+")
HEADERS = {"User-Agent": "Mozilla/5.0 (opsera-analytics-dashboard)"}


def stop(msg):
    print(f"\nSTOPPED: {msg}", file=sys.stderr)
    sys.exit(1)


def run_apify(actor, target, token):
    r = requests.post(
        f"https://api.apify.com/v2/acts/{actor}/run-sync-get-dataset-items",
        params={"token": token, "maxTotalChargeUsd": MAX_CHARGE_USD, "clean": "true"},
        json={"targetUrls": [target], "maxPosts": 0, "postedLimitDate": START_DATE,
              "includeReposts": False, "includeQuotePosts": True, "scrapeReactions": False,
              "scrapeComments": True, "maxComments": MAX_COMMENTS},
        timeout=300,
    )
    if r.status_code not in (200, 201):
        stop(f"Apify {actor} returned {r.status_code}: {r.text[:300]}")
    return r.json()


def links_in(item):
    found = URL.findall(item.get("content") or item.get("commentary") or "")
    found += [a.get("hyperlink") for a in (item.get("contentAttributes") or []) + (item.get("commentaryAttributes") or []) if a.get("hyperlink")]
    if (item.get("article") or {}).get("link"):
        found.append(item["article"]["link"])
    return list(dict.fromkeys(u.rstrip(".,;") for u in found))


def resolve(url, seen=None):
    """Follow redirects, including LinkedIn's lnkd.in pages, to the address people end up on."""
    seen = seen or set()
    if url in seen or len(seen) > 6:
        return url
    seen.add(url)
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
    except requests.RequestException:
        return url
    final = r.url
    if urlparse(final).netloc.endswith("lnkd.in") or "linkedin.com/safety" in final:
        m = re.search(r'href="(https?://(?!(?:www\.)?(?:linkedin\.com|lnkd\.in|static\.licdn))[^"]+)"', r.text)
        if m:
            return resolve(m.group(1).replace("&amp;", "&"), seen)
    return final


def opsera_path(url):
    u = urlparse(url)
    if not (u.netloc == "opsera.ai" or u.netloc.endswith(".opsera.ai")):
        return None
    path = u.path.rstrip("/") or "/"
    return path


def main():
    if "--from" in sys.argv:
        saved = json.loads(Path(sys.argv[sys.argv.index("--from") + 1]).read_text())
        raw = [(p["account"], {"linkedinUrl": p["url"], "postedAt": {"date": p["posted"]}, "content": " ".join(p["links"])}) for p in saved]
        source = "saved Apify results"
    else:
        token = os.environ.get("APIFY_TOKEN")
        if not token:
            stop("The APIFY_TOKEN secret is missing. Add it in GitHub under Settings > Secrets and variables > Actions.")
        raw = [(acct, item) for acct, actor, target in ACCOUNTS for item in run_apify(actor, target, token)]
        source = "Apify, harvestapi/linkedin-company-posts and harvestapi/linkedin-profile-posts"

    posts, cache = {}, {}
    def pages_in(item):
        pages = []
        for link in links_in(item):
            final = cache.setdefault(link, resolve(link))
            path = opsera_path(final)
            if path:
                pages.append({"link": link, "lands_on": path})
        return pages
    def pacific(stamp):
        return dt.datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone(PACIFIC).date().isoformat()

    for acct, item in raw:
        if item.get("type") == "comment" or item.get("repostedBy") or item.get("type") == "repost":
            continue
        author = (item.get("author") or {}).get("linkedinUrl")
        if author and OWN[acct] not in author:
            continue   # the company feed can include other people's posts
        if pacific(item["postedAt"]["date"]) < START_DATE:
            continue
        posts[item.get("linkedinUrl")] = {"account": acct, "post": item.get("linkedinUrl"), "posted_utc": item["postedAt"]["date"],
                                          "date_pacific": pacific(item["postedAt"]["date"]), "opsera_pages": pages_in(item)}
    for acct, item in raw:
        if item.get("type") != "comment":
            continue
        post = posts.get((item.get("query") or {}).get("post"))
        commenter = (item.get("actor") or {}).get("linkedinUrl") or ""
        if not post or post["account"] != acct or OWN[acct] not in commenter:
            continue
        for page in pages_in(item):
            post.setdefault("comment_pages", []).append({**page, "date_pacific": pacific(item["createdAt"])})
    posts = list(posts.values())

    for acct, _, _ in ACCOUNTS:
        if not any(p["account"] == acct for p in posts):
            stop(f"No {acct} posts came back since {START_DATE}. Check the Apify run before guessing.")
    OUT.write_text(json.dumps({"source": source, "start_date": START_DATE,
                               "pulled_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="minutes"),
                               "posts": sorted(posts, key=lambda p: p["posted_utc"])}, indent=1))
    linked = [p for p in posts if p["opsera_pages"] or p.get("comment_pages")]
    print(f"LinkedIn posts since {START_DATE}: {len(posts)}, of which {len(linked)} link to opsera.ai in the post or the account's own comment")
    for p in linked:
        print(f"  {p['date_pacific']} {p['account']:<8} " + ", ".join(x["lands_on"] for x in p["opsera_pages"]) +
              "".join(f" [comment {c['date_pacific']}: {c['lands_on']}]" for c in p.get("comment_pages", [])))


if __name__ == "__main__":
    main()
