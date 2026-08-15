# -*- coding: utf-8 -*-
"""Build a self-contained image-mode HTML: inline every generated PNG as a JPEG data-URI.

Driven by deck.json (slide ids + outdir) — no hard-coded page count or paths. Produces a
single portable HTML (default image mode) that opens offline / sends over chat.

Usage:
  python inline_html.py deck.json outline.html                     # -> <outline>-图片版.html
  python inline_html.py deck.json outline.html --out final.html --width 1600 --quality 85

Requires: pillow
"""
import argparse
import base64
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from PIL import Image

IMGDATA_BLOCK = re.compile(r"/\*IMGDATA\*/.*?/\*/IMGDATA\*/", re.DOTALL)


def main():
    parser = argparse.ArgumentParser(description="inline generated PNGs into a self-contained HTML")
    parser.add_argument("deck", help="path to deck.json")
    parser.add_argument("outline", help="path to the outline HTML the deck was derived from")
    parser.add_argument("--out", help="output HTML (default: <outline>-图片版.html)")
    parser.add_argument("--width", type=int, default=1600, help="max thumbnail width px")
    parser.add_argument("--quality", type=int, default=85, help="JPEG quality")
    args = parser.parse_args()

    cfg = json.load(open(args.deck, encoding="utf-8"))
    base_dir = os.path.dirname(os.path.abspath(args.deck))
    outdir = os.path.join(base_dir, cfg.get("outdir", "pptimg"))

    entries, total, missing = [], 0, []
    for slide in cfg["slides"]:
        sid = slide["id"]
        png = os.path.join(outdir, sid + ".png")
        if not os.path.exists(png):
            missing.append(sid)
            continue
        im = Image.open(png).convert("RGB")
        if im.width > args.width:
            im = im.resize((args.width, round(im.height * args.width / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=args.quality, optimize=True)
        raw = buf.getvalue()
        total += len(raw)
        entries.append('%s:"data:image/jpeg;base64,%s"'
                       % (json.dumps(sid), base64.b64encode(raw).decode()))
    if missing:
        print("WARN missing PNGs (kept as external refs): " + ", ".join(missing))
    print("inlined %d imgs @ W=%d Q=%d: %.1fMB jpeg (~%.0fMB base64)"
          % (len(entries), args.width, args.quality, total / 1e6, total * 1.34 / 1e6))

    html = open(args.outline, encoding="utf-8").read()
    if not IMGDATA_BLOCK.search(html):
        sys.exit("IMGDATA marker not found in outline — is this a deck-studio outline template?")
    injected = "/*IMGDATA*/ const IMGDATA = {\n" + ",\n".join(entries) + "\n}; /*/IMGDATA*/"
    html = IMGDATA_BLOCK.sub(lambda _: injected, html, count=1)
    html = html.replace("let viewMode='web';", "let viewMode='image';")

    out = args.out or re.sub(r"\.html?$", "", args.outline) + "-图片版.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote %s  (%.1f MB)" % (out, os.path.getsize(out) / 1e6))


if __name__ == "__main__":
    main()
