#!/usr/bin/env python3
"""Prep a photo for ASCII conversion.

A flatly-lit subject converts to a dark, unreadable blob. Three steps fix that:

  1. Cut the background out with rembg so only the subject survives.
  2. Boost local contrast with CLAHE, which gives a flat face real
     highlights and shadows instead of one mid-gray mush.
  3. Composite onto pure white, so the background lands on the blank end
     of the ASCII ramp (white -> space) and only the subject prints.

Run this once per photo:

    python scripts/prep_photo.py source-photo.jpg

Writes source-prepped.png (grayscale) next to the repo root.

Requires scripts/requirements-portrait.txt. rembg is optional: without it
the script falls back to compositing whatever alpha channel the source
already has, which is fine for PNGs that are already cut out.
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "source-prepped.png"

# CLAHE tuning. clipLimit caps how much any one tile may amplify contrast
# (higher = punchier, but noise gets amplified too); tileGridSize is how
# finely the image is divided for local equalization.
CLAHE_CLIP = 1.8
CLAHE_TILES = (8, 8)

# Gamma < 1 brightens midtones, pushing more of the subject toward the
# sparse end of the ramp so the portrait reads as line art, not a blob.
GAMMA = 0.6


def cut_background(img: Image.Image) -> Image.Image:
    """Return an RGBA image with the background removed."""
    try:
        from rembg import remove
    except ImportError:
        print("  rembg not installed - using the source alpha channel as-is")
        return img.convert("RGBA")

    print("  removing background with rembg...")
    return remove(img).convert("RGBA")


def on_white(img: Image.Image) -> Image.Image:
    """Flatten an RGBA image onto pure white."""
    white = Image.new("RGBA", img.size, (255, 255, 255, 255))
    return Image.alpha_composite(white, img).convert("RGB")


def boost_contrast(img: Image.Image) -> Image.Image:
    """Grayscale + CLAHE + gamma, keeping the white background pinned."""
    gray = np.array(img.convert("L"))

    # Remember what was already pure white so equalization can't drag the
    # background into a printable gray.
    background = gray >= 250

    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP, tileGridSize=CLAHE_TILES)
    gray = clahe.apply(gray)

    lut = np.array(
        [((i / 255.0) ** GAMMA) * 255 for i in range(256)], dtype=np.uint8
    )
    gray = cv2.LUT(gray, lut)

    gray[background] = 255
    return Image.fromarray(gray, mode="L")


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit(f"usage: {Path(sys.argv[0]).name} <photo>")

    src = Path(sys.argv[1])
    if not src.exists():
        sys.exit(f"no such file: {src}")

    print(f"prepping {src.name}")
    img = Image.open(src)
    img = cut_background(img)
    img = on_white(img)
    img = boost_contrast(img)
    img.save(OUT)
    print(f"  wrote {OUT.relative_to(ROOT)}  ({img.width}x{img.height})")


if __name__ == "__main__":
    main()
