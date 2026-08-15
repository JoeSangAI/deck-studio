# -*- coding: utf-8 -*-
"""Compact contact sheet for whole-deck QC (review this, never every 4K original).

Accepts deck.json (uses its outdir + slide order) or a directory of PNGs (name order).

Usage:
  python contact_sheet.py deck.json [--out _contact.webp] [--cols 5] [--width 320]
  python contact_sheet.py path/to/png_dir --out sheet.webp
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageOps

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def load_order(target):
    if os.path.isdir(target):
        files = [
            f
            for f in sorted(os.listdir(target))
            if f.lower().endswith(".png")
        ]
        ids = [os.path.splitext(f)[0] for f in files]
        ratio = (16, 9)
        if files:
            with Image.open(os.path.join(target, files[0])) as image:
                ratio = image.size
        return target, ids, ratio
    with open(target, encoding="utf-8") as stream:
        cfg = json.load(stream)
    base_dir = os.path.dirname(os.path.abspath(target))
    outdir = os.path.join(base_dir, cfg.get("outdir", "png"))
    size = cfg.get("size", "3840x2160").lower().split("x")
    try:
        ratio = (int(size[0]), int(size[1]))
    except (ValueError, IndexError):
        ratio = (16, 9)
    return outdir, [s["id"] for s in cfg["slides"]], ratio


def main():
    parser = argparse.ArgumentParser(description="build a contact sheet for deck QC")
    parser.add_argument("target", help="deck.json or a directory of PNGs")
    parser.add_argument("--out", help="output image (default: _contact.webp next to target)")
    parser.add_argument("--cols", type=int, default=5)
    parser.add_argument("--width", type=int, default=320, help="thumbnail width px")
    args = parser.parse_args()

    png_dir, ids, ratio = load_order(args.target)
    if not ids:
        sys.exit("nothing to sheet in " + args.target)
    if args.cols < 1 or args.width < 1:
        sys.exit("--cols and --width must be positive")
    if ratio[0] <= 0 or ratio[1] <= 0:
        sys.exit("invalid slide aspect ratio")

    thumb_w, pad, label_h = args.width, 12, 30
    thumb_h = round(thumb_w * ratio[1] / ratio[0])
    cols = min(args.cols, len(ids))
    rows = (len(ids) + cols - 1) // cols
    sheet_w = cols * thumb_w + (cols + 1) * pad
    sheet_h = rows * (thumb_h + label_h + pad) + pad
    sheet = Image.new("RGB", (sheet_w, sheet_h), (12, 13, 16))
    draw = ImageDraw.Draw(sheet)

    missing = []
    for i, sid in enumerate(ids):
        row, col = divmod(i, cols)
        x = pad + col * (thumb_w + pad)
        y = pad + row * (thumb_h + label_h + pad)
        png = os.path.join(png_dir, sid + ".png")
        if os.path.exists(png):
            with Image.open(png) as source:
                thumb = ImageOps.contain(
                    source.convert("RGB"),
                    (thumb_w, thumb_h),
                    Image.LANCZOS,
                )
            tile = Image.new("RGB", (thumb_w, thumb_h), (20, 21, 25))
            tile.paste(
                thumb,
                ((thumb_w - thumb.width) // 2, (thumb_h - thumb.height) // 2),
            )
            sheet.paste(tile, (x, y))
        else:
            draw.rectangle([x, y, x + thumb_w, y + thumb_h], outline=(120, 70, 50))
            missing.append(sid)
        draw.text((x + 4, y + thumb_h + 6), sid, fill=(200, 170, 120))

    default_dir = args.target if os.path.isdir(args.target) else os.path.dirname(os.path.abspath(args.target))
    out = args.out or os.path.join(default_dir, "_contact.webp")
    suffix = os.path.splitext(out)[1].lower()
    if suffix == ".webp":
        sheet.save(out, quality=76, method=6)
    elif suffix in {".jpg", ".jpeg"}:
        sheet.save(out, quality=80, optimize=True)
    else:
        sheet.save(out)
    note = " (" + ", ".join(missing) + ")" if missing else ""
    print("contact -> %s  %dx%d  pages %d  missing %d%s"
          % (out, sheet_w, sheet_h, len(ids), len(missing), note))


if __name__ == "__main__":
    main()
