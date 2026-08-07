#!/usr/bin/env python3
"""Hand-author the neofetch-style info card SVG.

Deliberately not generated from the API: the contribution graph above it
already covers the stats, so this panel is for the story the numbers can't
tell. Each line fades and slides in on a short stagger, so the card looks
like it's printing next to the portrait.

Edit CARD below - that's the whole interface. A row whose value is None is
dropped rather than rendered empty.

    python scripts/make_info_card.py            # writes info-card.svg
    STATIC=1 python scripts/make_info_card.py   # frozen frame for previews
"""

from __future__ import annotations

import os
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "info-card.svg"

USER = "damien"
HOST = "github"

# ---------------------------------------------------------------------------
# The card. Set a value to None to drop the row entirely.
# ---------------------------------------------------------------------------
CARD: list[tuple[str, str | None]] = [
    ("Now", None),  # TODO: role @ org
    ("Prev", "Indium Software"),
    ("Stack", None),  # TODO: what you want to be known for
    ("Focus", None),  # TODO
    ("Uptime", "since Aug 2024"),
    ("Repos", "8 public"),
    ("Langs", "TypeScript / Swift / Python / JavaScript"),
    ("Shell", "zsh / macOS"),
    ("Highlights", None),  # TODO: 1-2 lines the heatmap can't say
]

WIDTH = 490.0
HEIGHT = 370.0

BAR_H = 30.0
PAD = 20.0
FONT = 12.0
CHAR_W = 7.2  # 0.6em at 12px
LINE_H = 24.0
KEY_COL = 11  # characters reserved for the key column

BG = "#0d1117"
BAR = "#161b22"
EDGE = "#21262d"
KEY = "#58a6ff"
VAL = "#c9d1d9"
ACCENT = "#39d353"
MUTED = "#8b949e"

# neofetch signs off with a strip of colour blocks.
BLOCKS = ["#161b22", "#f85149", "#39d353", "#d29922",
          "#58a6ff", "#bc8cff", "#39c5cf", "#c9d1d9"]

START = 0.35
STAGGER = 0.09

STATIC = os.environ.get("STATIC") == "1"


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def wrap(value: str, width: int) -> list[str]:
    """Greedy wrap so long values continue under the value column."""
    lines: list[str] = []
    line = ""
    for word in value.split():
        candidate = f"{line} {word}".strip()
        if len(candidate) > width and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    if line:
        lines.append(line)
    return lines


def anim(index: int) -> str:
    if STATIC:
        return ""
    return f' style="animation-delay:{START + index * STAGGER:.2f}s"'


def build() -> str:
    rows = [(k, v) for k, v in CARD if v]
    parts: list[str] = []

    # Title bar: traffic lights + a window title.
    parts.append(
        f'<path d="M0 10a10 10 0 0 1 10-10h{WIDTH - 20:.0f}'
        f'a10 10 0 0 1 10 10v{BAR_H - 10:.0f}H0Z" fill="{BAR}"/>'
        f'<line x1="0" y1="{BAR_H}" x2="{WIDTH}" y2="{BAR_H}" stroke="{EDGE}"/>'
    )
    for i, colour in enumerate(["#f85149", "#d29922", "#3fb950"]):
        parts.append(
            f'<circle cx="{PAD + i * 16:.0f}" cy="{BAR_H / 2:.0f}" r="5"'
            f' fill="{colour}"/>'
        )
    parts.append(
        f'<text class="t muted" x="{WIDTH / 2:.0f}" y="{BAR_H / 2 + 4:.0f}"'
        f' text-anchor="middle">{USER}@{HOST}: ~</text>'
    )

    y = BAR_H + PAD + FONT
    line_no = 0

    # user@host, then the rule neofetch draws under it.
    parts.append(
        f'<text class="t" x="{PAD}" y="{y:.0f}"{anim(line_no)}>'
        f'<tspan class="accent b">{USER}</tspan>'
        f'<tspan class="muted">@</tspan>'
        f'<tspan class="accent b">{HOST}</tspan></text>'
    )
    line_no += 1
    y += LINE_H * 0.7
    parts.append(
        f'<text class="t muted" x="{PAD}" y="{y:.0f}"{anim(line_no)}>'
        f'{"-" * ((len(USER) + len(HOST) + 1))}</text>'
    )
    line_no += 1
    y += LINE_H

    value_chars = int((WIDTH - PAD * 2 - KEY_COL * CHAR_W) / CHAR_W)

    for key, value in rows:
        for i, chunk in enumerate(wrap(value, value_chars)):
            label = key if i == 0 else ""
            # Position the value explicitly rather than padding the key
            # with spaces - not every renderer preserves trailing spaces.
            parts.append(
                f'<text class="t" x="{PAD}" y="{y:.0f}"{anim(line_no)}>'
                f'<tspan class="key b">{label}</tspan>'
                f'<tspan x="{PAD + KEY_COL * CHAR_W:.0f}">{esc(chunk)}</tspan>'
                "</text>"
            )
            line_no += 1
            y += LINE_H

    # Colour blocks, pinned to the bottom.
    block_y = HEIGHT - PAD - 12
    for i, colour in enumerate(BLOCKS):
        parts.append(
            f'<rect class="blk" x="{PAD + i * 20:.0f}" y="{block_y:.0f}"'
            f' width="18" height="9" rx="1.5" fill="{colour}"'
            f"{anim(line_no + i // 3)}/>"
        )

    # `backwards`, not `forwards`: a line's resting state is visible, so a
    # renderer that ignores CSS animation shows the finished card rather
    # than an empty panel.
    keyframes = "" if STATIC else """
  @keyframes in { from { opacity: 0; transform: translateX(-6px); }
                    to { opacity: 1; transform: translateX(0); } }
  .t, .blk { animation: in .34s ease-out backwards; }"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH:.0f}" \
height="{HEIGHT:.0f}" viewBox="0 0 {WIDTH:.0f} {HEIGHT:.0f}" \
role="img" aria-label="{USER}@{HOST} info card">
<style>
  text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, \
"DejaVu Sans Mono", monospace; font-size: {FONT}px; fill: {VAL}; }}
  .b {{ font-weight: 600; }}
  .key {{ fill: {KEY}; }}
  .accent {{ fill: {ACCENT}; }}
  .muted {{ fill: {MUTED}; }}{keyframes}
</style>
<rect width="{WIDTH:.0f}" height="{HEIGHT:.0f}" rx="10" fill="{BG}"/>
{"".join(parts)}
<rect x="0.5" y="0.5" width="{WIDTH - 1:.0f}" height="{HEIGHT - 1:.0f}" rx="10" \
fill="none" stroke="{EDGE}"/>
</svg>
"""


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    filled = sum(1 for _, v in CARD if v)
    todo = [k for k, v in CARD if not v]
    print(f"wrote {OUT.name}  ({filled}/{len(CARD)} rows)")
    if todo:
        print(f"  still empty: {', '.join(todo)}")


if __name__ == "__main__":
    main()
