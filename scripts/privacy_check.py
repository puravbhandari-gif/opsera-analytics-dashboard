"""Runs after every update, before anything is published (agreed with Purav, 17 Nov 2026).
Scans every file in data/ for email addresses and for names on the private customer list, and stops the publish if it
finds one. Page addresses, our own page slugs and the titles of our own published posts, videos and emails are public, so
they're skipped; so are names on the private "public_ok" list (partners we announced). The customer list comes from the
CUSTOMER_NAMES secret (or the hand rules file on Purav's Mac); without it, only emails are checked and the log warns.
Run: python scripts/privacy_check.py"""
import json
import os
import re
import sys
from pathlib import Path

from privacy import EMAIL, W_EMAIL, customer_names, customer_pattern, HAND_RULES

DATA = Path(__file__).resolve().parent.parent / "data"
PUBLIC_KEYS = {"page", "pages", "landingPage", "pagePath", "link", "url", "path", "variants", "title", "titles", "subject", "short_title"}
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+){2,}$")   # our own page slugs used as campaign names


def public_ok():
    env = os.environ.get("CUSTOMER_NAMES_PUBLIC_OK", "")
    if env.strip():
        return {n.strip().lower() for n in env.splitlines() if n.strip()}
    return {n.lower() for n in json.loads(HAND_RULES.read_text()).get("public_ok", [])} if HAND_RULES.exists() else set()


def main():
    names = customer_names()
    if not names:
        # Until the CUSTOMER_NAMES secret is set, only emails are checked; the log says so on every run
        print("WARNING: the CUSTOMER_NAMES secret is missing, so customer names aren't checked. Emails still are.", file=sys.stderr)
    pattern, ok = customer_pattern(), public_ok()
    found = []

    def walk(x, f, key):
        if isinstance(x, str):
            if EMAIL.search(x) or W_EMAIL.search(x):
                found.append((f, key, "an email address"))
            if key in PUBLIC_KEYS or x.startswith(("/", "http")) or SLUG.match(x):
                return
            m = pattern.search(x)
            if m and m.group(0).lower() not in ok:
                found.append((f, key, "a customer name"))
        elif isinstance(x, list):
            for v in x:
                walk(v, f, key)
        elif isinstance(x, dict):
            for k, v in x.items():
                walk(k, f, key)
                walk(v, f, k)

    for p in sorted(DATA.glob("*.json")):
        walk(json.loads(p.read_text()), p.name, "")
    # The plain-text summary in index.html for AI tools (24 Nov 2026): its text, without links, tags or page addresses
    page = (DATA.parent / "index.html").read_text()
    block = re.search(r"<!-- ai-summary:start -->(.*?)<!-- ai-summary:end -->", page, re.S)
    if block:
        text = re.sub(r'<a href="[^"]*">[^<]*</a>|<[^>]+>', " ", block.group(1))
        walk([t for t in re.split(r"\s{2,}|\n", text) if t.strip()], "index.html", "ai-summary")
    print(f"Privacy check: {len(list(DATA.glob('*.json')))} files, {len(names)} customer names checked.")
    if found:
        # Where only, never the value itself: the run log is visible to anyone with access to the repo
        for f, key, what in sorted(set(found)):
            print(f"  {f}, field {key or '(top)'}: {what}", file=sys.stderr)
        print("STOPPED: private data found in data/. Nothing was published.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
