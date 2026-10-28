"""Count Kumar Chivukula's own posts and reposts by month into data/kumar_posts.json,
for the LinkedIn exec tab. Own posts and reposts are two separate lines, never added together.

Reads his public profile with the Apify tool harvestapi/linkedin-profile-posts, reposts
included and comments left out, so a weekly run costs a few cents.
Needs the APIFY_TOKEN env var (a GitHub secret).
Agreed with Purav on 27 Oct 2026: this replaces the hand count. Checked against it first:
July to September and October up to 22 Oct match exactly.
Months follow UTC, the same as LinkedIn's own exports. A post he reposted twice counts twice.

    python3 scripts/count_kumar_posts.py                    # runs Apify
    python3 scripts/count_kumar_posts.py --from items.json  # uses Apify results already saved
"""
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

import requests

START_MONTH = "2026-07"
PROFILE = "https://www.linkedin.com/in/kumar-chivukula/"
HANDLE = "kumar-chivukula"
MAX_CHARGE_USD = 1
OUT = Path(__file__).resolve().parent.parent / "data" / "kumar_posts.json"
POSTS = Path(__file__).resolve().parent.parent / "data" / "kumar_post_list.json"


def stop(msg):
    print(f"\nSTOPPED: {msg}", file=sys.stderr)
    sys.exit(1)


def word_index(text):
    """A post's words as short scrambled codes (FNV-1a, 32 bits), so Look up can tell whether a post mentions
    a word without the file holding the post's text, which often names people. Words of 3+ letters, each once."""
    out = []
    for w in dict.fromkeys(re.findall(r"[a-z0-9]+", (text or "").lower())):
        if len(w) < 3:
            continue
        h = 0x811C9DC5
        for b in w.encode():
            h = ((h ^ b) * 0x01000193) & 0xFFFFFFFF
        out.append(f"{h:08x}")
    return out


def fetch(token):
    r = requests.post(
        "https://api.apify.com/v2/acts/harvestapi~linkedin-profile-posts/run-sync-get-dataset-items",
        params={"token": token, "maxTotalChargeUsd": MAX_CHARGE_USD, "clean": "true"},
        json={"targetUrls": [PROFILE], "maxPosts": 0, "postedLimitDate": f"{START_MONTH}-01",
              "includeReposts": True, "includeQuotePosts": True, "scrapeReactions": False, "scrapeComments": False},
        timeout=300,
    )
    if r.status_code not in (200, 201):
        stop(f"Apify returned {r.status_code}: {r.text[:300]}")
    return r.json()


def main():
    if "--from" in sys.argv:
        items = json.loads(Path(sys.argv[sys.argv.index("--from") + 1]).read_text())
    else:
        token = os.environ.get("APIFY_TOKEN")
        if not token:
            stop("The APIFY_TOKEN secret is missing. Add it in GitHub under Settings > Secrets and variables > Actions.")
        items = fetch(token)

    now = dt.datetime.now(dt.timezone.utc)
    months = {}
    m = dt.date.fromisoformat(f"{START_MONTH}-01")
    while m.isoformat()[:7] <= now.date().isoformat()[:7]:
        months[m.isoformat()[:7]] = {"own_posts": 0, "reposts": 0}
        m = (m.replace(day=28) + dt.timedelta(days=4)).replace(day=1)

    posts = []   # Kumar's own posts for Look up: date, opening words, reactions and comments, words scrambled
    seen = set()
    for item in items:
        reposter = (item.get("repostedBy") or {}).get("publicIdentifier")
        author = (item.get("author") or {}).get("linkedinUrl") or ""
        when = ((item.get("repostedAt") if reposter else None) or item.get("postedAt") or {}).get("date")
        if not when:
            continue
        if reposter:
            if reposter != HANDLE:
                continue
            kind = "reposts"
        else:
            if author and f"/in/{HANDLE}" not in author:
                continue   # someone else's post that isn't a repost by him
            kind = "own_posts"
        key = (item.get("linkedinUrl"), when)
        if key in seen:
            continue   # the same post at the same moment, returned twice
        seen.add(key)
        month = when[:7]
        if month in months:
            months[month][kind] += 1
        if kind == "own_posts":
            text = " ".join((item.get("content") or "").split())
            eng = item.get("engagement") or {}
            posts.append({"date": when[:10], "link": item.get("linkedinUrl"), "title": text[:100] + ("..." if len(text) > 100 else ""),
                          "reactions": eng.get("likes"), "comments": eng.get("comments"), "words": word_index(text)})

    if not any(v["own_posts"] for v in months.values()):
        stop(f"No posts by Kumar came back since {START_MONTH}. Check the Apify run before guessing.")
    this_month = now.date().isoformat()[:7]
    OUT.write_text(json.dumps({
        "source": "Kumar's public LinkedIn profile, read with Apify",
        "as_of": now.date().isoformat(),
        "months": [{"month": k, **v, **({"so_far": True} if k == this_month else {})} for k, v in months.items()],
    }, indent=1))
    POSTS.write_text(json.dumps({"source": "Kumar's public LinkedIn profile, read with Apify", "as_of": now.date().isoformat(),
                                 "posts": sorted(posts, key=lambda x: x["date"])}, indent=1))
    for k, v in months.items():
        print(f"{k}: own posts {v['own_posts']}, reposts {v['reposts']}")


if __name__ == "__main__":
    main()
