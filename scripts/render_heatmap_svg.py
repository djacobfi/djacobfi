#!/usr/bin/env python3
"""Render data/contributions.json as an animated contribution heatmap.

The classic 53-week x 7-day calendar of rounded boxes, revealed once with
a diagonal slide-down and then frozen - no looping glow. The motion is CSS
keyframes declared inside the SVG, which is fine because GitHub only
sanitizes CSS in the README markup, not inside an SVG it serves as an image.

    python scripts/render_heatmap_svg.py        # writes contrib-heatmap.svg
    STATIC=1 python scripts/render_heatmap_svg.py
"""

from __future__ import annotations

import json
import os
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"

PALETTE = [
    "#161b22",  # none
    "#0e4429",
    "#006d32",
    "#26a641",
    "#39d353",
    "#69f0a0",  # neon top end
]

# A level-4 day this busy gets promoted to the neon shade.
NEON_AT = 12

CELL = 11.0
GAP = 3.0
PITCH = CELL + GAP

PAD = 20.0
LABEL_W = 30.0  # gutter for Mon / Wed / Fri
MONTH_H = 20.0
FOOTER_H = 46.0

BG = "#0d1117"
MUTED = "#8b949e"
BRIGHT = "#c9d1d9"

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
DAY_LABELS = {1: "Mon", 3: "Wed", 5: "Fri"}  # Sunday-first row index

STATIC = os.environ.get("STATIC") == "1"


def sunday_index(d: date) -> int:
    """Row index with Sunday as row 0."""
    return (d.weekday() + 1) % 7


def place(days: list[dict]) -> tuple[list[dict], int]:
    """Assign every day a (week, row) slot on the calendar grid."""
    first = date.fromisoformat(days[0]["date"])
    origin = first - timedelta(days=sunday_index(first))

    placed = []
    for day in days:
        d = date.fromisoformat(day["date"])
        placed.append(
            {
                **day,
                "week": (d - origin).days // 7,
                "row": sunday_index(d),
                "d": d,
            }
        )
    return placed, max(p["week"] for p in placed) + 1


def shade(day: dict) -> str:
    level = day["level"]
    if level >= 4 and day["count"] >= NEON_AT:
        level = 5
    return PALETTE[min(level, 5)]


def month_labels(placed: list[dict]) -> list[tuple[int, str]]:
    """One label per month, at the column where that month starts."""
    labels: list[tuple[int, str]] = []
    seen: set[tuple[int, int]] = set()

    for day in placed:
        key = (day["d"].year, day["d"].month)
        if key in seen:
            continue
        seen.add(key)
        # Skip a month whose first visible column is too close to the
        # previous label, or it collides.
        if labels and day["week"] - labels[-1][0] < 3:
            continue
        labels.append((day["week"], MONTHS[day["d"].month - 1]))
    return labels


def fmt_day(iso: str | None) -> str:
    if not iso:
        return "-"
    d = date.fromisoformat(iso)
    return f"{MONTHS[d.month - 1]} {d.day}"


def build(data: dict) -> str:
    placed, weeks = place(data["days"])

    grid_x = PAD + LABEL_W
    grid_y = PAD + MONTH_H
    grid_w = weeks * PITCH - GAP
    grid_h = 7 * PITCH - GAP

    width = grid_x + grid_w + PAD
    height = grid_y + grid_h + FOOTER_H + PAD

    parts: list[str] = []

    # Month labels across the top.
    for week, name in month_labels(placed):
        parts.append(
            f'<text class="lbl" x="{grid_x + week * PITCH:.1f}"'
            f' y="{PAD + MONTH_H - 7:.1f}">{name}</text>'
        )

    # Weekday gutter.
    for row, name in DAY_LABELS.items():
        parts.append(
            f'<text class="lbl" x="{PAD:.1f}"'
            f' y="{grid_y + row * PITCH + CELL - 1.5:.1f}">{name}</text>'
        )

    # The grid itself. Delay keyed on (week + row) gives the diagonal wipe.
    for day in placed:
        x = grid_x + day["week"] * PITCH
        y = grid_y + day["row"] * PITCH
        delay = "" if STATIC else (
            f' style="animation-delay:{0.25 + (day["week"] + day["row"]) * 0.014:.2f}s"'
        )
        count = day["count"]
        noun = "contribution" if count == 1 else "contributions"
        parts.append(
            f'<rect class="c" x="{x:.1f}" y="{y:.1f}" width="{CELL}"'
            f' height="{CELL}" rx="2.5" fill="{shade(day)}"{delay}>'
            f'<title>{count} {noun} on {fmt_day(day["date"])}</title></rect>'
        )

    # Legend, bottom right.
    legend_y = grid_y + grid_h + 20
    legend_x = width - PAD - (len(PALETTE) * PITCH) - 34
    parts.append(
        f'<text class="lbl" x="{legend_x - 6:.1f}"'
        f' y="{legend_y + CELL - 1.5:.1f}" text-anchor="end">Less</text>'
    )
    for i, colour in enumerate(PALETTE):
        parts.append(
            f'<rect class="c" x="{legend_x + i * PITCH:.1f}" y="{legend_y:.1f}"'
            f' width="{CELL}" height="{CELL}" rx="2.5" fill="{colour}"'
            + ("" if STATIC else f' style="animation-delay:{1.6 + i * 0.05:.2f}s"')
            + "/>"
        )
    parts.append(
        f'<text class="lbl" x="{legend_x + (len(PALETTE) - 1) * PITCH + CELL + 6:.1f}"'
        f' y="{legend_y + CELL - 1.5:.1f}">More</text>'
    )

    # Stats footer, bottom left.
    total = data["total"]
    busiest = data["busiest_day"] or {"count": 0, "date": None}
    stats = (
        f'<tspan class="hi">{total:,}</tspan> contributions in the last year'
        f'  &#183;  streak <tspan class="hi">{data["current_streak"]["length"]}</tspan>'
        f'  &#183;  longest <tspan class="hi">{data["longest_streak"]["length"]}</tspan>'
        f'  &#183;  best day <tspan class="hi">{busiest["count"]}</tspan>'
        f' ({fmt_day(busiest["date"])})'
    )
    parts.append(
        f'<text class="foot" x="{PAD:.1f}" y="{legend_y + CELL - 1.5:.1f}">{stats}</text>'
    )

    # `backwards` rather than `forwards`, and no opacity:0 base rule: the
    # resting state of a cell is visible, and the fill mode borrows the
    # from-frame during the delay. A renderer that ignores CSS animation
    # then shows a complete heatmap instead of an empty box.
    anim = "" if STATIC else """
    @keyframes drop { from { opacity: 0; transform: translateY(-7px); }
                        to { opacity: 1; transform: translateY(0); } }
    .c { animation: drop .42s ease-out backwards; }"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}" \
height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}" \
role="img" aria-label="{total} contributions in the last year">
<style>
    text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, \
"DejaVu Sans Mono", monospace; }}
    .lbl {{ font-size: 9px; fill: {MUTED}; }}
    .foot {{ font-size: 11px; fill: {MUTED}; }}
    .hi {{ fill: {BRIGHT}; font-weight: 600; }}{anim}
</style>
<rect width="{width:.0f}" height="{height:.0f}" rx="10" fill="{BG}"/>
{"".join(parts)}
</svg>
"""


def main() -> None:
    if not SRC.exists():
        raise SystemExit(
            "missing data/contributions.json - run scripts/fetch_contributions.py first"
        )

    data = json.loads(SRC.read_text(encoding="utf-8"))
    OUT.write_text(build(data), encoding="utf-8")
    print(f"wrote {OUT.name}  ({len(data['days'])} days, {OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
