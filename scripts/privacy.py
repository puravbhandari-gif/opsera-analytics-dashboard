"""Keeps visitor emails out of the public data files (agreed with Purav, 17 Nov 2026).
Email links can put a visitor's email in a page address or a Google Analytics source (w_email=...), so every value is
cleaned before it's saved: the w_email= part goes, and anything else shaped like an email address is removed."""
import json
import os
import re
from pathlib import Path

W_EMAIL = re.compile(r"(?<=[?&])w_email=[^&\s\"]*&?|w_email=[^&\s\"]*", re.I)
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+(?:@|%40)[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")


def has_email(s):
    return bool(EMAIL.search(s) or W_EMAIL.search(s))


# A customer's own Opsera portal (portal.<company>.opsera.io) names the company, so it becomes one neutral label.
# Our own portals (portal.opsera.io, sandbox, test and staging ones) keep their address (agreed 17 Nov 2026).
PORTAL = re.compile(r"portal\.(?!(?:sandbox|opsera-uat|uat|dev|test|staging|demo)\.)[a-z0-9-]+\.opsera\.io", re.I)
CUSTOMER_PORTALS = "Customer portals"


def clean(s):
    """A value without any email or customer portal: 'email?w_email=a@b.com' becomes 'email'."""
    if not isinstance(s, str):
        return s
    if PORTAL.fullmatch(s.strip()):
        return CUSTOMER_PORTALS
    if not has_email(s):
        return s
    s = W_EMAIL.sub("", s)
    s = EMAIL.sub("", s)
    return s.rstrip("?&").strip()


def clean_tree(x):
    """Every string in a JSON-style value, cleaned."""
    if isinstance(x, str):
        return clean(x)
    if isinstance(x, list):
        return [clean_tree(v) for v in x]
    if isinstance(x, dict):
        return {clean(k): clean_tree(v) for k, v in x.items()}
    return x


# Customer names come from a private list, never from this repo: the CUSTOMER_NAMES secret in GitHub (one name per line),
# or on Purav's Mac the "customers" list in the hand rules file next to David's exports (agreed 17 Nov 2026).
HAND_RULES = Path(os.path.expanduser("~/Desktop/Data/salesforce-exports/hand-rules.json"))


def customer_names():
    env = os.environ.get("CUSTOMER_NAMES", "")
    if env.strip():
        return [n.strip() for n in env.splitlines() if n.strip()]
    if HAND_RULES.exists():
        return json.loads(HAND_RULES.read_text()).get("customers", [])
    return []


def customer_pattern():
    """Matches any customer name as a whole word, any case; matches nothing when the list isn't available."""
    names = customer_names()
    if not names:
        return re.compile(r"(?!x)x")
    return re.compile(r"(?<![A-Za-z0-9])(" + "|".join(re.escape(n) for n in sorted(names, key=len, reverse=True)) + r")(?![A-Za-z0-9])", re.I)
