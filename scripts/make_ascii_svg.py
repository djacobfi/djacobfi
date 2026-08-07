#!/usr/bin/env python3
"""Turn the prepped photo into a self-typing monochrome ASCII SVG.

The prepped image is downsampled to a character grid and each cell's
brightness picks a glyph from a density ramp - sparse glyphs for bright
areas, dense ones for dark. Every row is then wrapped in a horizontal
clip that wipes left to right, staggered top to bottom, with a small
block cursor riding the wipe edge. The portrait prints once and freezes.

The animation is SMIL inside the SVG, which is the only kind of motion
GitHub will run in a README (it strips <script> and sanitizes inline CSS,
but renders SVGs embedded via <img>).

    python scripts/make_ascii_svg.py            # writes avi-ascii.svg
    STATIC=1 python scripts/make_ascii_svg.py   # frozen frame for previews
"""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "source-prepped.png"
OUT = ROOT / "avi-ascii.svg"

RAMP = " .`:-=+*cs#%@"  # bright (sparse) -> dark (dense)
#       ^ leading space clears the background to nothing

COLS = 100

FONT_SIZE = 10.0
CHAR_W = 6.0  # monospace advance ~= 0.6em
LINE_H = 10.5
PAD = 14.0

BG = "#0d1117"
INK = "#c9d1d9"  # one fill colour: per-character rainbow is what makes
#                  most ASCII portraits look like static
CURSOR = "#39d353"

# Wipe timing, in seconds.
START = 0.25
ROW_STAGGER = 0.035
ROW_DUR = 0.22

STATIC = os.environ.get("STATIC") == "1"


def load_grid() -> list[str]:
    """Downsample the prepped photo to a grid of ramp glyphs."""
    img = Image.open(SRC).convert("L")

    # Character cells are taller than they are wide, so the row count has
    # to be scaled by the glyph aspect or the portrait comes out stretched.
    aspect = CHAR_W / LINE_H
    rows = max(1, round(img.height / img.width * COLS * aspect))

    img = img.resize((COLS, rows), Image.LANCZOS)
    px = img.load()

    grid = []
    for y in range(rows):
        line = []
        for x in range(COLS):
            # Invert: bright pixels take the sparse end of the ramp.
            idx = (255 - px[x, y]) * len(RAMP) // 256
            line.append(RAMP[idx])
        grid.append("".join(line))
    return grid


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build(grid: list[str]) -> str:
    width = PAD * 2 + COLS * CHAR_W
    height = PAD * 2 + len(grid) * LINE_H

    defs: list[str] = []
    body: list[str] = []

    for i, raw in enumerate(grid):
        content = raw.rstrip()
        if not content:
            continue

        # Absorb leading spaces into the x offset rather than trusting
        # every renderer to preserve them.
        lead = len(content) - len(content.lstrip())
        text = content[lead:]

        x = PAD + lead * CHAR_W
        baseline = PAD + i * LINE_H + FONT_SIZE * 0.8
        span = len(text) * CHAR_W
        begin = START + i * ROW_STAGGER

        if STATIC:
            body.append(
                f'<text x="{x:.1f}" y="{baseline:.1f}" textLength="{span:.1f}"'
                f' lengthAdjust="spacing">{esc(text)}</text>'
            )
            continue

        # The clip rect rests at full width so a renderer without SMIL
        # shows the finished portrait rather than nothing. The row's
        # stagger is folded into the animation as a hold at zero instead
        # of a begin offset, because SMIL shows the *base* value before
        # begin - which would flash the row in, then snap it away.
        clip = f"r{i}"
        total = begin + ROW_DUR
        hold = begin / total
        defs.append(
            f'<clipPath id="{clip}">'
            f'<rect x="{x:.1f}" y="{PAD + i * LINE_H:.1f}"'
            f' width="{span:.1f}" height="{LINE_H:.1f}">'
            f'<animate attributeName="width" values="0;0;{span:.1f}"'
            f' keyTimes="0;{hold:.4f};1" begin="0s" dur="{total:.2f}s"'
            f' fill="freeze"/>'
            f"</rect></clipPath>"
        )
        body.append(
            f'<text clip-path="url(#{clip})" x="{x:.1f}" y="{baseline:.1f}"'
            f' textLength="{span:.1f}" lengthAdjust="spacing">{esc(text)}</text>'
        )
        # The cursor rides the wipe edge, then blinks out.
        body.append(
            f'<rect y="{PAD + i * LINE_H + 1:.1f}" width="{CHAR_W:.1f}"'
            f' height="{FONT_SIZE:.1f}" fill="{CURSOR}" opacity="0">'
            f'<animate attributeName="x" from="{x:.1f}" to="{x + span:.1f}"'
            f' begin="{begin:.2f}s" dur="{ROW_DUR}s" fill="freeze"/>'
            f'<set attributeName="opacity" to="0.9" begin="{begin:.2f}s"/>'
            f'<set attributeName="opacity" to="0" begin="{begin + ROW_DUR:.2f}s"/>'
            f"</rect>"
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width:.0f}"'
        f' height="{height:.0f}" viewBox="0 0 {width:.0f} {height:.0f}"'
        ' role="img" aria-label="ASCII portrait">'
        f'<rect width="{width:.0f}" height="{height:.0f}" rx="10" fill="{BG}"/>'
        f'<defs>{"".join(defs)}</defs>'
        f'<g font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,'
        f'&quot;DejaVu Sans Mono&quot;,monospace" font-size="{FONT_SIZE}"'
        f' fill="{INK}" xml:space="preserve">{"".join(body)}</g>'
        "</svg>"
    )


def main() -> None:
    if not SRC.exists():
        raise SystemExit(
            f"missing {SRC.name} - run scripts/prep_photo.py <photo> first"
        )

    grid = load_grid()
    OUT.write_text(build(grid), encoding="utf-8")
    print(f"wrote {OUT.name}  ({COLS}x{len(grid)} chars, {OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
