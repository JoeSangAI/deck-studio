# -*- coding: utf-8 -*-
"""Assemble a full-bleed 16:9 PPTX from deck.json (its slide order + outdir).

Usage: python assemble_pptx.py deck.json --out final.pptx
Adds a blank slide for any missing/undersized PNG, prints them, exits 1. Focus
Media slides are rejected before assembly unless their hash-bound Output Check
report matches the exact current PNG and reference assets.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from pptx import Presentation
from pptx.util import Emu

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from templates.verify_focusmedia_output import validate_media_output

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

SLIDE_W, SLIDE_H = 12192000, 6858000  # 16:9 EMU


def main():
    parser = argparse.ArgumentParser(description="assemble full-bleed PPTX from generated PNGs")
    parser.add_argument("deck", help="path to deck.json")
    parser.add_argument("--out", required=True, help="output .pptx path")
    args = parser.parse_args()

    cfg = json.load(open(args.deck, encoding="utf-8"))
    base_dir = Path(args.deck).resolve().parent
    outdir = base_dir / cfg.get("outdir", "png")
    width = int(cfg.get("size", "3840x2160").lower().split("x")[0])
    min_bytes = 300000 if width >= 3000 else 40000

    media_errors = []
    for slide_def in cfg["slides"]:
        if slide_def.get("specialist_route") != "focusmedia-image-gen":
            continue
        png = outdir / (slide_def["id"] + ".png")
        media_errors.extend(
            validate_media_output(
                slide_def,
                base_dir=base_dir,
                output_path=png,
            )
        )
    if media_errors:
        for error in media_errors:
            print("MEDIA VALIDATION ERROR: " + error)
        sys.exit(1)

    prs = Presentation()
    prs.slide_width = Emu(SLIDE_W)
    prs.slide_height = Emu(SLIDE_H)
    blank = prs.slide_layouts[6]

    placed, missing = [], []
    for slide_def in cfg["slides"]:
        sid = slide_def["id"]
        png = outdir / (sid + ".png")
        slide = prs.slides.add_slide(blank)
        if png.exists() and png.stat().st_size > min_bytes:
            slide.shapes.add_picture(str(png), 0, 0, width=prs.slide_width, height=prs.slide_height)
            placed.append(sid)
        else:
            missing.append(sid)

    prs.save(args.out)
    print("saved: %s  (%.1f MB)" % (args.out, os.path.getsize(args.out) / 1e6))
    print("placed %d / %d" % (len(placed), len(cfg["slides"])))
    if missing:
        print("MISSING: " + ", ".join(missing))
        sys.exit(1)


if __name__ == "__main__":
    main()
