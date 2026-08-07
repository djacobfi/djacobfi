#!/usr/bin/env python3
"""Scrape the public contribution calendar and derive stats.

No GraphQL API and no personal access token: GitHub serves the calendar
as public HTML at /users/<username>/contributions - the same fragment the
profile page itself renders. Each day is a <td class="ContributionCalendar-day">
carrying data-date and data-level, and the exact count lives in the
<tool-tip for="<cell id>"> that GitHub pairs with it.

    python scripts/fetch_contributions.py   # writes data/contributions.json
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

USER = os.environ.get("GH_USER", "djacobfi")
URL = f"https://github.com/users/{USER}/contributions"
OUT = Path(__file__).resolve().parent.parent / "data" / "contributions.json"

HEADERS = {
    "User-Agent": f"{USER}-profile-art/1.0 (+https://github.com/{USER})",
    "Accept": "text/html",
}

COUNT_RE = re.compile(r"^([\d,]+)\s+contribution")


def fetch() -> str:
    resp = requests.get(URL, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_days(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")

    # Counts live in the tooltips, keyed by the cell they describe.
    counts: dict[str, int] = {}
    for tip in soup.find_all("tool-tip"):
        target = tip.get("for")
        if not target:
            continue
        match = COUNT_RE.match(tip.get_text(strip=True))
        counts[target] = int(match.group(1).replace(",", "")) if match else 0

    days = []
    for cell in soup.select("td.ContributionCalendar-day"):
        iso = cell.get("data-date")
        if not iso:  # padding cells at the edges of the grid
            continue
        days.append(
            {
                "date": iso,
                "count": counts.get(cell.get("id", ""), 0),
                "level": int(cell.get("data-level", 0)),
            }
        )

    days.sort(key=lambda d: d["date"])
    return days


def streaks(days: list[dict]) -> tuple[dict, dict]:
    """Longest streak overall, and the streak running up to today."""
    longest = {"length": 0, "start": None, "end": None}
    run = 0
    run_start = None

    for day in days:
        if day["count"] > 0:
            run_start = run_start or day["date"]
            run += 1
            if run > longest["length"]:
                longest = {"length": run, "start": run_start, "end": day["date"]}
        else:
            run = 0
            run_start = None

    # Walk backwards for the current streak. An empty today doesn't break
    # it - the day isn't over yet.
    by_date = {d["date"]: d["count"] for d in days}
    cursor = date.fromisoformat(days[-1]["date"]) if days else None
    if cursor and by_date.get(cursor.isoformat(), 0) == 0:
        cursor -= timedelta(days=1)

    current = {"length": 0, "start": None, "end": None}
    while cursor and by_date.get(cursor.isoformat(), 0) > 0:
        current["length"] += 1
        current["start"] = cursor.isoformat()
        current["end"] = current["end"] or cursor.isoformat()
        cursor -= timedelta(days=1)

    return current, longest


def build(days: list[dict]) -> dict:
    total = sum(d["count"] for d in days)
    best = max(days, key=lambda d: d["count"]) if days else None

    months: dict[str, int] = defaultdict(int)
    for day in days:
        months[day["date"][:7]] += 1 * day["count"]

    current, longest = streaks(days)
    active = sum(1 for d in days if d["count"] > 0)

    return {
        "user": USER,
        "generated_from": URL,
        "range": {"start": days[0]["date"], "end": days[-1]["date"]},
        "total": total,
        "active_days": active,
        "busiest_day": best,
        "current_streak": current,
        "longest_streak": longest,
        "monthly": dict(sorted(months.items())),
        "days": days,
    }


def main() -> None:
    print(f"fetching {URL}")
    days = parse_days(fetch())
    if not days:
        sys.exit("no day cells parsed - GitHub's markup may have changed")

    data = build(days)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    print(
        f"  {len(days)} days, {data['total']:,} contributions, "
        f"{data['active_days']} active, "
        f"current streak {data['current_streak']['length']}, "
        f"longest {data['longest_streak']['length']}"
    )
    print(f"  wrote {OUT.parent.name}/{OUT.name}")


if __name__ == "__main__":
    main()
