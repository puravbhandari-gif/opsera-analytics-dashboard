"""Share of voice for the PR and media tab: Google News articles naming Opsera, Harness, CloudBees,
Copado, Gearset or LinearB in the headline, per Opsera fiscal quarter (Q3 is Aug to Oct) from 1 Jul 2026, and per day so the page can compare
the same days of each quarter. Writes data/share_of_voice.json. Runs every Monday.

Reads Google News' public search feed one week at a time (no key needed), so each week can return up to 100
articles. An article counts when its headline names the company, it isn't on the company's own site, and it
isn't one of the known look-alikes (football players and cups called Copado, AI "harnesses"). The same rule
applies to every company, and the counts are never added to the PR and media rows. Agreed with Purav on 4 Nov 2026;
GitLab was swapped for CloudBees, Gearset and LinearB the same day.
"""
import datetime as dt
import email.utils
import html
import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import requests

START = "2026-07-01"
OUT = Path(__file__).resolve().parent.parent / "data" / "share_of_voice.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (opsera-analytics-dashboard)"}
COMPANIES = {   # name: (search, headline must match, own sites, look-alikes left out)
    "Opsera": ('"Opsera"', r"\bOpsera\b", r"opsera", None),
    # Harness the company, not an AI "harness": the name starts the headline or follows "and", "with", "vs" and the like
    "Harness": ('"Harness" (DevOps OR "software delivery" OR CI/CD OR "AI agents" OR Harness.io)',
                r"(^|[:,;]\s*|\b(?:and|with|from|by|at|as|vs\.?|like|says|for|joins|picks|taps)\s)Harness\b(?!es| [Ee]ngineering)",
                r"^harness(\.io)?$",
                r"(?i)harness engineering|engineering harness|agent harness|harnesses|back in the harness|(strands|deepseek|aws|anthropic|claude|openai|codex|agentcore|open-source|ai) harness|adds harness to open source"),
    "CloudBees": ('"CloudBees"', r"\bCloudBees\b", r"^cloudbees(\.com)?$", None),
    "Copado": ('"Copado"', r"\bCopado\b", r"^copado(\.com)?$", r"Copa do|Lucas Copado|Transfermarkt|transfer|U20|live score"),
    "Gearset": ('"Gearset"', r"\bGearset\b", r"^gearset(\.com)?$", None),
    "LinearB": ('"LinearB"', r"\bLinearB\b", r"^linearb(\.io)?$", None),
}


def quarter(d):   # Opsera's fiscal quarters (agreed 5 Nov 2026): FY27 Q3 is Aug to Oct 2026
    return f"FY{(int(d[:4]) + (1 if int(d[5:7]) >= 2 else 0)) % 100:02d} Q{(int(d[5:7]) + 10) % 12 // 3 + 1}"


def week_items(search, a, b):
    q = urllib.parse.quote(f"{search} after:{a} before:{b}")
    for attempt in range(3):
        try:
            r = requests.get(f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en", headers=HEADERS, timeout=30)
            if r.status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(5)
    else:
        sys.exit(f"Google News didn't answer for {search} {a} to {b}, so the share of voice wasn't updated.")
    out = []
    for item in re.findall(r"<item>(.*?)</item>", r.text, re.S):
        title = html.unescape(re.search(r"<title>(.*?)</title>", item, re.S).group(1))
        source = html.unescape((re.search(r"<source[^>]*>(.*?)</source>", item, re.S) or [None, ""])[1]).strip()
        when = email.utils.parsedate_to_datetime(re.search(r"<pubDate>(.*?)</pubDate>", item).group(1)).date().isoformat()
        headline = re.sub(rf"\s+-\s+{re.escape(source)}$", "", title) if source else title
        out.append({"headline": headline, "source": source, "date": when})
    return out


def main():
    today = dt.date.today().isoformat()
    counts, kept_total, by_day = {}, {}, {}
    for name, (search, must, own, lookalike) in COMPANIES.items():
        seen, kept = set(), []
        a = dt.date.fromisoformat(START)
        while a.isoformat() <= today:
            b = a + dt.timedelta(days=7)
            for it in week_items(search, a.isoformat(), b.isoformat()):
                key = (it["headline"].lower(), it["source"].lower())
                if key in seen or not (START <= it["date"] <= today):
                    continue
                seen.add(key)
                if not re.search(must, it["headline"]):
                    continue
                if re.search(own, it["source"].lower()) or (lookalike and re.search(lookalike, it["headline"] + " " + it["source"])):
                    continue
                kept.append(it)
            a = b
            time.sleep(1)
        for it in kept:
            counts.setdefault(quarter(it["date"]), {}).setdefault(name, 0)
            counts[quarter(it["date"])][name] += 1
            by_day.setdefault(it["date"], {}).setdefault(name, 0)
            by_day[it["date"]][name] += 1
        kept_total[name] = len(kept)
        print(f"{name}: {len(kept)} articles since {START}")
    for q in counts.values():
        for name in COMPANIES:
            q.setdefault(name, 0)
    OUT.write_text(json.dumps({
        "source": "Google News search feed, US English, headlines naming each company",
        "start_date": START, "checked": today,
        "quarters": [{"quarter": q, "counts": counts[q]} for q in sorted(counts, key=lambda s: s)],
        "days": [{"date": d, "counts": by_day[d]} for d in sorted(by_day)],   # the page compares the same days of each quarter
    }, indent=1) + "\n")


if __name__ == "__main__":
    main()
