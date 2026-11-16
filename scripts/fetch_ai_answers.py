"""AI answer checks for "Does Opsera show up in AI answers?" at the top of the AEO tab. Writes data/ai_answers.json.

Ahrefs Brand Radar asks ChatGPT and Google AI Mode our questions once a day (report REPORT). For each question
and each assistant this keeps 1 character per day from first_check to last_check: 1 = the answer named Opsera,
0 = it didn't, - = no check ran.

It needs the AHREFS_API_KEY secret. Without it nothing changes, and Claude Code fills the file by hand through
its Ahrefs connection ("refresh the AI answer checks"). These calls cost 0 units.

If the questions don't add up to Ahrefs' own daily totals, it stops and leaves the file as it was.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent.parent / "data"
OUT = DATA / "ai_answers.json"
API = "https://api.ahrefs.com/v3"
REPORT = "01a17948-8055-7d23-b244-9274671d3b59"
BRAND = "Opsera"
FIRST_CHECK = "2026-10-26"   # the day the report's daily checks began
ASSISTANTS = [{"key": "chatgpt", "name": "ChatGPT"}, {"key": "google_ai_mode", "name": "Google AI Mode"}]


def call(path, key, **params):
    r = requests.get(f"{API}/{path}", headers={"Authorization": f"Bearer {key}", "Accept": "application/json"}, params=params, timeout=120)
    if r.status_code != 200:
        sys.exit(f"Ahrefs {path} returned {r.status_code}, so the AI answer checks weren't updated.")
    return r.json()


def mentions(key, assistant, today, question=None):
    """{date: mentions} for one assistant: every question, or just one."""
    params = {"report_id": REPORT, "brand": BRAND, "data_source": assistant, "prompts": "custom",
              "date_from": FIRST_CHECK, "date_to": today}
    if question:
        params["where"] = json.dumps({"field": "question", "is": ["eq", question]})
    return {m["date"][:10]: m["mentions"] for m in call("brand-radar/mentions-history", key, **params)["metrics"]}


def main():
    key = os.environ.get("AHREFS_API_KEY")
    if not key:
        print("The AHREFS_API_KEY secret is missing, so the AI answer checks weren't updated.")
        return
    today = dt.date.today().isoformat()
    questions = [p["prompt"] for p in call("management/brand-radar-prompts", key, report_id=REPORT)["prompts"]]
    if not questions:
        sys.exit("Ahrefs returned no questions, so the AI answer checks weren't updated.")

    totals = {a["key"]: mentions(key, a["key"], today) for a in ASSISTANTS}
    checked = sorted(set().union(*totals.values()))
    if not checked:
        sys.exit("Ahrefs returned no checks, so the AI answer checks weren't updated.")
    first, last = dt.date.fromisoformat(FIRST_CHECK), dt.date.fromisoformat(checked[-1])
    days = [(first + dt.timedelta(n)).isoformat() for n in range((last - first).days + 1)]

    prompts = []
    for q in questions:
        checks = {}
        for a in ASSISTANTS:
            named = mentions(key, a["key"], today, q)
            checks[a["key"]] = "".join("-" if d not in totals[a["key"]] else "1" if named.get(d) else "0" for d in days)
        prompts.append({"question": q, "names_opsera": BRAND.lower() in q.lower(), "checks": checks})

    # The questions have to add up to Ahrefs' own total for every day and assistant
    for a in ASSISTANTS:
        for i, d in enumerate(days):
            got = sum(p["checks"][a["key"]][i] == "1" for p in prompts)
            if got != totals[a["key"]].get(d, 0):
                sys.exit(f"{a['name']} on {d}: the questions add up to {got} but Ahrefs' total is {totals[a['key']][d]}, "
                         "so the AI answer checks weren't updated.")

    prompts.sort(key=lambda p: p["names_opsera"])   # questions without "Opsera" first
    OUT.write_text(json.dumps({
        "how_to_update": "scripts/fetch_ai_answers.py fills this file on the Monday run once the AHREFS_API_KEY secret exists. "
                         "Until then Claude Code fills it by hand from Ahrefs Brand Radar: ask \"refresh the AI answer checks\". "
                         "Each check string has 1 character per day from first_check to last_check: 1 = the answer named Opsera, "
                         "0 = it didn't, - = no check ran.",
        "source": "Ahrefs Brand Radar", "pulled": today, "by_hand": False, "first_check": FIRST_CHECK, "last_check": checked[-1],
        "assistants": ASSISTANTS, "prompts": prompts}, indent=1) + "\n")
    print(f"AI answer checks: {len(prompts)} questions, {FIRST_CHECK} to {checked[-1]}.")


if __name__ == "__main__":
    main()
