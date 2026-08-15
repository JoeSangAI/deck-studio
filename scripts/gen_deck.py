# -*- coding: utf-8 -*-
"""Generate full-bleed deck slides from a validated runtime manifest.

deck.json is derived from the approved outline and page plan. It is the runtime
manifest, not a second text source:
{
  "outdir": "png",                  # relative to deck.json (absolute also works)
  "size": "3840x2160",              # each dimension must be divisible by 16
  "quality": "high",
  "workers": 1,
  "min_bytes": 400000,              # optional cache threshold; auto-derived if omitted
  "slides": [
    {"id": "S01", "prompt": "..."},
    {"id": "K01", "prompt": "...", "photo": "assets/person.jpg"},
    {
      "id": "M01",
      "prompt": "...",
      "production_route": "reference-fusion",
      "specialist_route": "focusmedia-image-gen",
      "specialist_asset_scope": "full-slide",
      "reference_assets": [
        {"id": "fm-lcd-001", "path": "/abs/ref.jpg", "sha256": "...", "role": "environment-geometry", "media_type": "lcd"},
        {"id": "fm-standard-lcd-32", "path": "/abs/lcd-32-standard.png", "sha256": "...", "role": "verified-standard-frame", "media_type": "lcd", "hardware_standard": "lcd-32"}
      ],
      "framed_asset": {"id": "fm-lcd-framed-001", "path": "/abs/framed.png", "sha256": "...", "media_type": "lcd", "hardware_standard": "lcd-32"},
      "specialist_asset": "assets/focusmedia-lcd.png",
      "specialist_asset_sha256": "...",
      "media_contract": {"medium": "LCD", "...": "..."}
    }
  ]
}

photo present -> POST /images/edits (preserves that person's likeness)
photo absent  -> POST /images/generations
Focus Media pages must use reference fusion with hash-bound real references and a
hash-bound framed_asset plus a final full-slide specialist_asset produced by
focusmedia-image-gen. The specialist slide is copied byte-for-byte and never sent to
generic image generation. Final output validation is a separate gate before assembly.

Usage:
  python gen_deck.py deck.json                 # all missing pages (cached skipped)
  python gen_deck.py deck.json --only S01,K01  # sample gate / selective pages
  python gen_deck.py deck.json --force         # ignore cache for selected pages
  python gen_deck.py deck.json --dry-run       # validate + print prompts, no API calls

Credentials: env OPENAI_API_KEY; OPENAI_BASE_URL is optional.
Proxy: requests honors standard environment variables. Exits 1 if any page failed.
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import struct
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import requests

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from templates.verify_page_plan import (
    FOCUSMEDIA_ASSET_SCOPES,
    FOCUSMEDIA_CONTRACT_FIELDS,
    FOCUSMEDIA_INTEGRATION_MODES,
    FOCUSMEDIA_HARDWARE_STANDARDS,
    FOCUSMEDIA_MEDIA_TERMS,
    FOCUSMEDIA_OUTPUT_TYPES,
    FOCUSMEDIA_ROUTE,
    _normalize_focusmedia_type,
    _validate_focusmedia_framed_asset,
    _validate_reference_assets,
)


def _focusmedia_visual_required(slide):
    if slide.get("requires_focusmedia_media") is True:
        return True
    prompt = str(slide.get("prompt") or "").casefold()
    return any(term in prompt for term in FOCUSMEDIA_MEDIA_TERMS)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _png_dimensions(path):
    with open(path, "rb") as handle:
        header = handle.read(24)
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", header[16:24])


def _validate_specialist_routes(slides, base_dir, expected_size):
    for slide in slides:
        sid = slide.get("id", "<unknown>")
        route = slide.get("specialist_route")
        if _focusmedia_visual_required(slide) and route != FOCUSMEDIA_ROUTE:
            sys.exit(
                "%s is a Focus Media visual but does not use specialist_route %s"
                % (sid, FOCUSMEDIA_ROUTE)
            )
        if route in (None, ""):
            continue
        if route != FOCUSMEDIA_ROUTE:
            sys.exit("%s has unsupported specialist_route: %s" % (sid, route))
        asset_scope = slide.get("specialist_asset_scope")
        if asset_scope not in FOCUSMEDIA_ASSET_SCOPES:
            sys.exit(
                "%s specialist_asset_scope must be one of: %s"
                % (sid, ", ".join(sorted(FOCUSMEDIA_ASSET_SCOPES)))
            )
        if asset_scope == "media-visual":
            sys.exit(
                "%s is a media-visual for native-editable assembly; "
                "gen_deck only accepts full-slide specialist assets" % sid
            )
        if slide.get("production_route") != "reference-fusion":
            sys.exit(
                "%s full-slide Focus Media asset requires production_route "
                "reference-fusion" % sid
            )
        contract = slide.get("media_contract")
        if not isinstance(contract, dict):
            sys.exit("%s requires a media_contract object" % sid)
        missing_contract = [
            field
            for field in FOCUSMEDIA_CONTRACT_FIELDS
            if not contract.get(field)
        ]
        if missing_contract:
            sys.exit(
                "%s media_contract missing fields: %s"
                % (sid, ", ".join(missing_contract))
            )
        if contract.get("integration_mode") not in FOCUSMEDIA_INTEGRATION_MODES:
            sys.exit(
                "%s media_contract integration_mode must be one of: %s"
                % (sid, ", ".join(sorted(FOCUSMEDIA_INTEGRATION_MODES)))
            )
        if contract.get("output_type") not in FOCUSMEDIA_OUTPUT_TYPES:
            sys.exit(
                "%s media_contract output_type must be one of: %s"
                % (sid, ", ".join(sorted(FOCUSMEDIA_OUTPUT_TYPES)))
            )
        expected_integration = {
            "framed-demo": "framed-standard-composite",
            "environment-image": "environment-reference-fusion",
        }[contract["output_type"]]
        if contract.get("integration_mode") != expected_integration:
            sys.exit(
                "%s output_type %s requires integration_mode %s"
                % (sid, contract["output_type"], expected_integration)
            )
        reference_errors = []
        _validate_reference_assets(
            1,
            slide.get("reference_assets"),
            reference_errors,
            {},
            require_focusmedia=True,
        )
        if reference_errors:
            sys.exit("%s invalid reference_assets: %s" % (sid, "; ".join(reference_errors)))
        expected_medium = _normalize_focusmedia_type(contract.get("medium"))
        expected_standard = FOCUSMEDIA_HARDWARE_STANDARDS.get(expected_medium, "")
        actual_standard = str(contract.get("hardware_standard") or "").strip().casefold()
        if expected_standard and actual_standard != expected_standard:
            sys.exit(
                "%s medium %s requires hardware_standard %s"
                % (sid, expected_medium, expected_standard)
            )
        actual_media = {
            _normalize_focusmedia_type(item.get("media_type"))
            for item in slide.get("reference_assets") or []
            if isinstance(item, dict)
        }
        if expected_medium not in actual_media:
            sys.exit(
                "%s reference_assets do not match media_contract medium %s"
                % (sid, expected_medium)
            )
        reference_roles = {
            str(item.get("role") or "").strip()
            for item in slide.get("reference_assets") or []
            if isinstance(item, dict)
        }
        if contract["output_type"] == "framed-demo":
            if "verified-standard-frame" not in reference_roles:
                sys.exit("%s framed-demo requires a verified-standard-frame reference" % sid)
        else:
            if "environment-geometry" not in reference_roles:
                sys.exit("%s environment-image requires an environment-geometry reference" % sid)
            if "verified-standard-frame" not in reference_roles:
                sys.exit("%s environment-image requires a verified-standard-frame reference" % sid)
            framed_errors = []
            _validate_focusmedia_framed_asset(
                1,
                slide.get("framed_asset"),
                framed_errors,
                {},
                expected_medium=expected_medium,
                expected_standard=expected_standard,
            )
            if framed_errors:
                sys.exit("%s invalid framed_asset: %s" % (sid, "; ".join(framed_errors)))
        asset = str(slide.get("specialist_asset") or "").strip()
        if not asset:
            sys.exit(
                "%s requires specialist_asset from focusmedia-image-gen; "
                "generic generation is blocked" % sid
            )
        asset_path = asset if os.path.isabs(asset) else os.path.join(base_dir, asset)
        if not os.path.isfile(asset_path):
            sys.exit("%s specialist_asset not found: %s" % (sid, asset))
        expected_asset_hash = str(
            slide.get("specialist_asset_sha256") or ""
        ).strip().lower()
        if len(expected_asset_hash) != 64:
            sys.exit("%s specialist_asset_sha256 must be 64 lowercase hex characters" % sid)
        if _sha256(asset_path) != expected_asset_hash:
            sys.exit("%s specialist_asset_sha256 does not match file" % sid)
        dimensions = _png_dimensions(asset_path)
        if dimensions is None:
            sys.exit("%s full-slide specialist_asset must be a PNG" % sid)
        if dimensions != expected_size:
            sys.exit(
                "%s full-slide specialist_asset size %sx%s does not match deck size %sx%s"
                % (sid, dimensions[0], dimensions[1], expected_size[0], expected_size[1])
            )
        slide["prebuilt_slide_asset"] = asset_path


def load_config(deck_path):
    with open(deck_path, encoding="utf-8") as stream:
        cfg = json.load(stream)
    if not isinstance(cfg, dict):
        sys.exit("deck.json must contain an object")
    slides = cfg.get("slides") or []
    if not isinstance(slides, list) or not slides:
        sys.exit("deck.json has no slides")
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            sys.exit("slide %d must be an object" % index)
        for field in ("id", "prompt"):
            if not str(slide.get(field) or "").strip():
                sys.exit("slide %d field %s must be non-empty" % (index, field))
    ids = [s["id"] for s in slides]
    duplicate_ids = {i for i in ids if ids.count(i) > 1}
    if duplicate_ids:
        sys.exit("duplicate slide ids: %s" % ", ".join(sorted(duplicate_ids)))
    size = cfg.get("size", "3840x2160")
    try:
        width, height = (int(x) for x in size.lower().split("x"))
    except (AttributeError, TypeError, ValueError):
        sys.exit("invalid size: %s" % size)
    if width <= 0 or height <= 0:
        sys.exit("size dimensions must be positive")
    if width % 16 or height % 16:
        sys.exit("size %s rejected: each dimension must be divisible by 16 "
                 "(3840x2160 / 2048x1152 OK — 1920x1080 is NOT). The API also enforces "
                 "a minimum pixel budget: sizes around 1024x576 get HTTP 400" % size)
    base_dir = os.path.dirname(os.path.abspath(deck_path))
    _validate_specialist_routes(slides, base_dir, (width, height))
    outdir = os.path.join(base_dir, cfg.get("outdir", "png"))
    min_bytes = cfg.get("min_bytes") or (400000 if min(width, height) >= 2000 else 60000)
    return cfg, slides, size, outdir, base_dir, min_bytes


def resolve_credentials():
    key = os.environ.get("OPENAI_API_KEY")
    base = os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    if not key:
        sys.exit("no OPENAI_API_KEY in environment")
    return key, base.rstrip("/")


def generate_one(slide, ctx):
    sid = slide["id"]
    out_path = os.path.join(ctx["outdir"], sid + ".png")
    prebuilt = slide.get("prebuilt_slide_asset")
    if prebuilt:
        if (
            not ctx["force"]
            and os.path.isfile(out_path)
            and _sha256(out_path) == _sha256(prebuilt)
        ):
            return sid, "cached exact specialist asset"
        temp_path = out_path + ".tmp"
        shutil.copyfile(prebuilt, temp_path)
        os.replace(temp_path, out_path)
        return sid, "COPIED exact specialist asset"
    if not ctx["force"] and os.path.exists(out_path) and os.path.getsize(out_path) > ctx["min_bytes"]:
        return sid, "cached"
    photo = slide.get("photo")
    last_error = ""
    for attempt in range(2):
        try:
            if photo:
                photo_path = os.path.join(ctx["base_dir"], photo)
                mime = "image/png" if photo_path.lower().endswith(".png") else "image/jpeg"
                with open(photo_path, "rb") as f:
                    response = requests.post(
                        ctx["base"] + "/images/edits", headers=ctx["headers"],
                        files={"image": (os.path.basename(photo_path), f, mime)},
                        data={"model": "gpt-image-2", "prompt": slide["prompt"],
                              "size": ctx["size"], "quality": ctx["quality"]},
                        proxies=ctx["proxies"], timeout=600)
            else:
                response = requests.post(
                    ctx["base"] + "/images/generations", headers=ctx["headers"],
                    json={"model": "gpt-image-2", "prompt": slide["prompt"],
                          "size": ctx["size"], "quality": ctx["quality"], "n": 1},
                    proxies=ctx["proxies"], timeout=600)
            if response.status_code == 200:
                first = response.json()["data"][0]
                if first.get("b64_json"):
                    raw = base64.b64decode(first["b64_json"])
                else:
                    raw = requests.get(
                        first["url"],
                        proxies=ctx["proxies"],
                        timeout=600,
                    ).content
                temp_path = out_path + ".tmp"
                with open(temp_path, "wb") as stream:
                    stream.write(raw)
                os.replace(temp_path, out_path)
                return sid, "OK %.1fMB" % (len(raw) / 1e6)
            if response.status_code == 429 or response.status_code >= 500:
                last_error = "HTTP %d" % response.status_code
                time.sleep(10 * (attempt + 1))
                continue
            return sid, "FAIL HTTP %d %s" % (response.status_code, response.text[:160])
        except Exception as e:
            last_error = repr(e)[:140]
            time.sleep(10 * (attempt + 1))
    return sid, "FAIL " + last_error


def main():
    parser = argparse.ArgumentParser(description="generate deck slides via gpt-image-2")
    parser.add_argument("deck", help="path to deck.json")
    parser.add_argument("--only", help="comma-separated slide ids (sample gate / regen)")
    parser.add_argument("--force", action="store_true", help="regenerate even if cached")
    parser.add_argument("--dry-run", action="store_true", help="print resolved prompts, no API calls")
    parser.add_argument("--workers", type=int, help="override workers from deck.json")
    args = parser.parse_args()

    cfg, slides, size, outdir, base_dir, min_bytes = load_config(args.deck)
    if args.only:
        wanted = {s.strip() for s in args.only.split(",") if s.strip()}
        unknown = wanted - {s["id"] for s in slides}
        if unknown:
            sys.exit("unknown ids: %s" % ", ".join(sorted(unknown)))
        slides = [s for s in slides if s["id"] in wanted]

    for slide in slides:
        if slide.get("photo") and not os.path.exists(os.path.join(base_dir, slide["photo"])):
            sys.exit("photo not found for %s: %s" % (slide["id"], slide["photo"]))

    if args.dry_run:
        print("deck: %d slides selected | size %s | outdir %s | min_bytes %d"
              % (len(slides), size, outdir, min_bytes))
        for slide in slides:
            if slide.get("prebuilt_slide_asset"):
                kind = "COPY(specialist_asset=%s)" % slide["prebuilt_slide_asset"]
            else:
                kind = "EDIT(photo=%s)" % slide["photo"] if slide.get("photo") else "GEN"
            print("\n[%s] %s\n%s" % (slide["id"], kind, slide["prompt"]))
        return

    needs_api = any(not slide.get("prebuilt_slide_asset") for slide in slides)
    if needs_api:
        key, base = resolve_credentials()
        headers = {"Authorization": "Bearer " + key}
    else:
        base, headers = "", {}
    os.makedirs(outdir, exist_ok=True)
    ctx = {"outdir": outdir, "base_dir": base_dir, "size": size,
           "quality": cfg.get("quality", "high"), "min_bytes": min_bytes, "force": args.force,
           "base": base, "headers": headers,
           "proxies": None}
    workers = args.workers if args.workers is not None else cfg.get("workers", 1)
    if not isinstance(workers, int):
        sys.exit("workers must be an integer")
    if workers < 1 or workers > 4:
        sys.exit("workers must be between 1 and 4")
    print("generating %d pages | size %s | workers %d -> %s"
          % (len(slides), size, workers, outdir), flush=True)
    failed, done = [], 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(generate_one, slide, ctx): slide["id"] for slide in slides}
        for future in as_completed(futures):
            sid, status = future.result()
            done += 1
            print("[%2d/%2d] %-14s %s" % (done, len(slides), sid, status), flush=True)
            if status.startswith("FAIL"):
                failed.append(sid)
    if failed:
        print("FAILED: " + ", ".join(sorted(failed)), flush=True)
        sys.exit(1)
    print("ALL DONE", flush=True)


if __name__ == "__main__":
    main()
