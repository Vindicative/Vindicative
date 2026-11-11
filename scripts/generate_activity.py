#!/usr/bin/env python3
"""Generate .github/assets/activity.svg: a monochrome contribution graph on #0a0a0a.

Usage:
    GH_TOKEN=... python3 scripts/generate_activity.py            # real data
    python3 scripts/generate_activity.py --empty                 # blank grid
    python3 scripts/generate_activity.py --demo out.svg          # random data (preview)

Environment:
    GH_TOKEN / GITHUB_TOKEN   token used for the GitHub GraphQL API
    GH_USER                   username (defaults to GITHUB_REPOSITORY_OWNER, then "Vindicative")
"""
import datetime as dt
import json
import math
import os
import random
import sys
import urllib.request

BG = "#0a0a0a"
BORDER = "#1c1c1c"
TITLE = "#e6e6e6"
MUTED = "#7a7a7a"
LEVELS = ["#151515", "#2b2b2b", "#4d4d4d", "#7d7d7d", "#cfcfcf"]
FONT = "'Segoe UI', -apple-system, Helvetica, Arial, sans-serif"
MONO = "'SF Mono', Consolas, 'Courier New', monospace"

CELL, GAP = 12, 3
STEP = CELL + GAP
WIDTH = 900

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount weekday } }
      }
    }
  }
}
"""


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-activity-graph",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = [[(d["date"], d["contributionCount"], d["weekday"]) for d in w["contributionDays"]]
             for w in cal["weeks"]]
    return weeks, cal["totalContributions"]


def blank_weeks():
    today = dt.date.today()
    start = today - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # back to Sunday
    weeks, d = [], start
    while d <= today:
        week = []
        for wd in range(7):
            if d <= today:
                week.append((d.isoformat(), 0, wd))
            d += dt.timedelta(days=1)
        weeks.append(week)
    return weeks


def demo_weeks():
    weeks = blank_weeks()
    rnd = random.Random(7)
    return [[(d, rnd.choice([0, 0, 0, 1, 2, 3, 5, 8, 12]), wd) for d, _, wd in w] for w in weeks]


def level(count, peak):
    if count <= 0 or peak <= 0:
        return 0
    return max(1, min(4, math.ceil(4 * count / peak)))


def render(weeks, total):
    peak = max((c for w in weeks for _, c, _ in w), default=0)
    ncols = len(weeks)
    grid_w = ncols * STEP - GAP
    x0 = (WIDTH - grid_w) // 2
    y0 = 100
    height = y0 + 7 * STEP + 62

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}">',
        f'  <rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="14" fill="{BG}" stroke="{BORDER}"/>',
        f'  <text x="{x0}" y="48" font-family="{FONT}" font-size="22" font-weight="600" fill="{TITLE}">Activity</text>',
        f'  <text x="{x0 + grid_w}" y="48" text-anchor="end" font-family="{MONO}" font-size="13" fill="{MUTED}">'
        f'{total:,} contributions in the last year</text>',
    ]

    # month labels
    prev = None
    for i, week in enumerate(weeks):
        month = dt.date.fromisoformat(week[0][0]).strftime("%b")
        if month != prev and i < ncols - 2:
            out.append(f'  <text x="{x0 + i * STEP}" y="{y0 - 12}" font-family="{MONO}" font-size="11" fill="{MUTED}">{month}</text>')
        prev = month

    # cells
    for i, week in enumerate(weeks):
        for date, count, wd in week:
            out.append(
                f'  <rect x="{x0 + i * STEP}" y="{y0 + wd * STEP}" width="{CELL}" height="{CELL}" rx="3" '
                f'fill="{LEVELS[level(count, peak)]}"><title>{date}: {count}</title></rect>'
            )

    # legend
    ly = y0 + 7 * STEP + 26
    lx = x0 + grid_w - (5 * STEP + 70)
    out.append(f'  <text x="{lx - 8}" y="{ly + 10}" text-anchor="end" font-family="{MONO}" font-size="11" fill="{MUTED}">Less</text>')
    for k, c in enumerate(LEVELS):
        out.append(f'  <rect x="{lx + k * STEP}" y="{ly}" width="{CELL}" height="{CELL}" rx="3" fill="{c}"/>')
    out.append(f'  <text x="{lx + 5 * STEP + 6}" y="{ly + 10}" font-family="{MONO}" font-size="11" fill="{MUTED}">More</text>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main():
    args = sys.argv[1:]
    out_path = ".github/assets/activity.svg"
    if "--demo" in args:
        i = args.index("--demo")
        out_path = args[i + 1] if len(args) > i + 1 else "activity-demo.svg"
        weeks = demo_weeks()
        total = sum(c for w in weeks for _, c, _ in w)
    elif "--empty" in args:
        weeks, total = blank_weeks(), 0
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        if not token:
            sys.exit("Set GH_TOKEN (or GITHUB_TOKEN), or use --empty / --demo.")
        user = os.environ.get("GH_USER") or os.environ.get("GITHUB_REPOSITORY_OWNER") or "Vindicative"
        weeks, total = fetch(user, token)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(render(weeks, total))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
