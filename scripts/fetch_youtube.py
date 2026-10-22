"""Pull the Opsera YouTube channel's numbers from YouTube's own APIs into
data/youtube.json. Read-only. Run: python3 scripts/fetch_youtube.py

The login (a refresh token from scripts/youtube_login.py) is read from the
YOUTUBE_TOKEN env var (GitHub Actions) or ~/.config/opsera-dashboard/youtube-token.json.

Agreed with Purav on 21 Oct 2026: Shorts and long videos are kept apart,
"Google Search" and "Google" outside-site views are shown as one Google line,
end screen clicks are left out for now (only in the Reporting API).
"""
import datetime as dt
import json
import os
import sys
import time
from pathlib import Path

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials

START_DATE = "2026-04-01"   # from 1 Apr, so "Last 3 months" can compare with the 3 months before
CHANNEL_ID = "UCpnT0NdkrOWp8v3bodeCGhQ"
TOKEN_FILE = Path.home() / ".config" / "opsera-dashboard" / "youtube-token.json"
OUT = Path(__file__).resolve().parent.parent / "data" / "youtube.json"
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"
DATA = "https://www.googleapis.com/youtube/v3"

TYPES = {"videoOnDemand": "long", "shorts": "shorts"}
TRAFFIC = {
    "YT_SEARCH": "YouTube search",
    "RELATED_VIDEO": "Suggested videos",
    "EXT_URL": "Other websites",          # split into Google and other websites below
    "NO_LINK_OTHER": "Direct or unknown",
    "YT_CHANNEL": "Our channel page",
    "SUBSCRIBER": "Subscribers' home feeds",
    "PLAYLIST": "Playlists",
    "YT_PLAYLIST_PAGE": "Playlists",
    "YT_OTHER_PAGE": "Other YouTube pages",
    "SHORTS": "Shorts feed",
    "NOTIFICATION": "Notifications",
    "END_SCREEN": "End screens",
    "ANNOTATION": "Cards",
    "HASHTAGS": "Hashtag pages",
    "NO_LINK_EMBEDDED": "Embedded videos",
    "ADVERTISING": "YouTube ads",
}
GOOGLE_LABELS = {"Google Search", "Google"}


def stop(msg):
    print(f"\nSTOPPED: {msg}", file=sys.stderr)
    sys.exit(1)


def session():
    raw = os.environ.get("YOUTUBE_TOKEN") or (TOKEN_FILE.read_text() if TOKEN_FILE.exists() else None)
    if not raw:
        stop("No YouTube login found. Run scripts/youtube_login.py first.")
    t = json.loads(raw)
    creds = Credentials(None, refresh_token=t["refresh_token"], client_id=t["client_id"],
                        client_secret=t["client_secret"], token_uri=t["token_uri"], scopes=t["scopes"])
    return AuthorizedSession(creds)


def get(s, url, **params):
    for wait in (0, 5, 20, 60):   # YouTube sometimes answers with a brief internal error; try again before giving up
        time.sleep(wait)
        r = s.get(url, params=params, timeout=60)
        if r.status_code < 500:
            break
    if r.status_code != 200:
        stop(f"{url} returned {r.status_code}: {r.text[:400]}")
    return r.json()


def report(s, end, **params):
    j = get(s, ANALYTICS, ids="channel==MINE", startDate=START_DATE, endDate=end, **params)
    cols = [h["name"] for h in j["columnHeaders"]]
    return [dict(zip(cols, row)) for row in j.get("rows", [])]


def content_type(raw):
    if raw not in TYPES:
        return None
    return TYPES[raw]


def main():
    end = (dt.datetime.now(IST).date() - dt.timedelta(days=1)).isoformat()
    s = session()
    ch = get(s, f"{DATA}/channels", part="snippet", mine="true")["items"]
    if [c["id"] for c in ch] != [CHANNEL_ID]:
        stop(f"The YouTube login is for {[c['id'] for c in ch]}, not the Opsera channel {CHANNEL_ID}.")
    print(f"YouTube channel: {ch[0]['snippet']['title']} ({CHANNEL_ID})")

    base = "views,estimatedMinutesWatched,averageViewDuration"
    totals = report(s, end, metrics=base + ",subscribersGained,subscribersLost")[0]

    by_type = {}
    for r in report(s, end, dimensions="creatorContentType", metrics=base):
        t = content_type(r["creatorContentType"])
        if t is None:
            if r["views"]:
                stop(f"YouTube reports {r['views']} views for content type '{r['creatorContentType']}', "
                     "which isn't Shorts or long videos. Check before showing it.")
            continue
        by_type[t] = {"views": r["views"], "minutes": r["estimatedMinutesWatched"], "avg_seconds": r["averageViewDuration"]}
    for t in TYPES.values():
        by_type.setdefault(t, {"views": 0, "minutes": 0, "avg_seconds": 0})
    if sum(v["views"] for v in by_type.values()) != totals["views"]:
        stop(f"Shorts and long video views don't add up to the channel's {totals['views']} views.")

    daily = []
    for r in report(s, end, dimensions="day,creatorContentType", metrics="views,estimatedMinutesWatched", sort="day"):
        t = content_type(r["creatorContentType"])
        if t:
            daily.append({"date": r["day"], "type": t, "views": r["views"], "minutes": r["estimatedMinutesWatched"]})
    for t, v in by_type.items():
        day_views = sum(r["views"] for r in daily if r["type"] == t)
        if day_views != v["views"]:
            stop(f"{t} views by day add up to {day_views}, but the total is {v['views']}.")

    subs = [{"date": r["day"], "gained": r["subscribersGained"], "lost": r["subscribersLost"]}
            for r in report(s, end, dimensions="day", metrics="subscribersGained,subscribersLost", sort="day")]
    if (sum(r["gained"] for r in subs), sum(r["lost"] for r in subs)) != (totals["subscribersGained"], totals["subscribersLost"]):
        stop("Subscribers gained or lost by day don't add up to the channel total.")

    # Videos: YouTube can't split the video list by type in one query, so each video is checked on its own.
    videos = [v for v in report(s, end, dimensions="video", metrics=base, sort="-views", maxResults=200) if v["views"]]
    ids = [v["video"] for v in videos]
    titles = {}
    for i in range(0, len(ids), 50):
        for item in get(s, f"{DATA}/videos", part="snippet", id=",".join(ids[i:i + 50])).get("items", []):
            titles[item["id"]] = item["snippet"]["title"]
    top = {t: [] for t in TYPES.values()}
    for v in videos:
        kinds = [r for r in report(s, end, dimensions="creatorContentType", metrics="views", filters=f"video=={v['video']}") if r["views"]]
        if len(kinds) != 1 or content_type(kinds[0]["creatorContentType"]) is None:
            stop(f"Video {v['video']} doesn't fall clearly into Shorts or long videos: {kinds}")
        top[content_type(kinds[0]["creatorContentType"])].append({
            "id": v["video"], "title": titles.get(v["video"], v["video"]), "views": v["views"],
            "minutes": v["estimatedMinutesWatched"], "avg_seconds": v["averageViewDuration"],
        })
    # YouTube lists a little less by video than its totals (agreed: show the list and say how much it covers).
    listed = {}
    for t, rows in top.items():
        listed[t] = {"views": sum(r["views"] for r in rows), "minutes": sum(r["minutes"] for r in rows)}
        if listed[t]["views"] > by_type[t]["views"] or listed[t]["minutes"] > by_type[t]["minutes"]:
            stop(f"{t} videos add up to more than the {t} total, which shouldn't happen.")

    sources = {t: {} for t in TYPES.values()}
    for r in report(s, end, dimensions="insightTrafficSourceType,creatorContentType", metrics="views"):
        t = content_type(r["creatorContentType"])
        if t:
            sources[t][r["insightTrafficSourceType"]] = sources[t].get(r["insightTrafficSourceType"], 0) + r["views"]
    for t, src in sources.items():
        if sum(src.values()) != by_type[t]["views"]:
            stop(f"{t} views by where they came from don't add up to the total.")

    # YouTube names outside sites for the whole channel only. That's fine while all of them are long videos.
    sites = report(s, end, dimensions="insightTrafficSourceDetail", filters="insightTrafficSourceType==EXT_URL",
                   metrics="views", sort="-views", maxResults=25)
    if sources["shorts"].get("EXT_URL"):
        stop("Shorts now get views from outside websites, so YouTube's site list can't be given to long videos alone.")
    google = sum(r["views"] for r in sites if r["insightTrafficSourceDetail"] in GOOGLE_LABELS)
    listed_other = [{"site": r["insightTrafficSourceDetail"], "views": r["views"]} for r in sites
                    if r["insightTrafficSourceDetail"] not in GOOGLE_LABELS]

    def plain(t):
        out = {}
        for key, views in sources[t].items():
            if key == "EXT_URL" and t == "long":
                other = views - google
                if other < 0:
                    stop("Google views are more than all outside-website views.")
                if google:
                    out["Google"] = out.get("Google", 0) + google
                if other:
                    out["Other websites"] = out.get("Other websites", 0) + other
                continue
            label = TRAFFIC.get(key, key.replace("_", " ").title())
            out[label] = out.get(label, 0) + views
        return sorted(({"source": k, "views": v} for k, v in out.items()), key=lambda x: -x["views"])

    searches = report(s, end, dimensions="insightTrafficSourceDetail", filters="insightTrafficSourceType==YT_SEARCH",
                      metrics="views", sort="-views", maxResults=25)
    cards = report(s, end, metrics="cardImpressions,cardClicks,cardTeaserImpressions,cardTeaserClicks")[0]

    # Videos published: public uploads only (agreed 22 Oct 2026). Type comes from YouTube's own split of each video's views.
    uploads, page = [], None
    while True:
        r = get(s, f"{DATA}/playlistItems", part="contentDetails", playlistId="UU" + CHANNEL_ID[2:], maxResults=50,
                **({"pageToken": page} if page else {}))
        uploads += [i["contentDetails"]["videoId"] for i in r["items"]]
        page = r.get("nextPageToken")
        if not page:
            break
    kind = {v["id"]: t for t, rows in top.items() for v in rows}
    published = []
    for i in range(0, len(uploads), 50):
        for v in get(s, f"{DATA}/videos", part="snippet,status", id=",".join(uploads[i:i + 50])).get("items", []):
            day = v["snippet"]["publishedAt"][:10]
            if v["status"]["privacyStatus"] == "public" and START_DATE <= day <= end:
                published.append({"date": day, "id": v["id"], "title": v["snippet"]["title"], "type": kind.get(v["id"], "unknown")})
    published.sort(key=lambda x: x["date"])

    out = {
        "source": "YouTube Analytics API, Opsera channel",
        "start_date": START_DATE, "end_date": end,
        "last_day_with_data": max((r["date"] for r in daily), default=None),
        "pulled_at": dt.datetime.now(IST).isoformat(timespec="minutes"),
        "channel": {
            "views": totals["views"], "minutes": totals["estimatedMinutesWatched"],
            "subs_gained": totals["subscribersGained"], "subs_lost": totals["subscribersLost"],
            "subs_daily": subs,
            "card_clicks": cards["cardClicks"], "card_teaser_clicks": cards["cardTeaserClicks"],
            "card_impressions": cards["cardImpressions"],
            "search_terms": [{"term": r["insightTrafficSourceDetail"], "views": r["views"]} for r in searches],
            "search_views": sum(sources[t].get("YT_SEARCH", 0) for t in sources),
            "other_sites": listed_other,
            "published": published,
        },
        "types": {t: {**by_type[t], "daily": [r for r in daily if r["type"] == t],
                      "videos": top[t], "videos_listed": listed[t], "sources": plain(t)} for t in TYPES.values()},
    }
    OUT.write_text(json.dumps(out, indent=1))
    print(f"YouTube {START_DATE} to {end} (last day with data {out['last_day_with_data']}): "
          f"long videos {by_type['long']['views']} views, Shorts {by_type['shorts']['views']} views, "
          f"subscribers +{totals['subscribersGained']} -{totals['subscribersLost']}")


if __name__ == "__main__":
    main()
