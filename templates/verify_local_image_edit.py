#!/usr/bin/env python3
"""Verify that an image edit stays inside approved rectangular regions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops


Box = tuple[int, int, int, int]


def _parse_box(value: str) -> Box:
    try:
        box = tuple(int(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("mask must be x1,y1,x2,y2") from exc
    if len(box) != 4:
        raise argparse.ArgumentTypeError("mask must be x1,y1,x2,y2")
    x1, y1, x2, y2 = box
    if x1 < 0 or y1 < 0 or x2 <= x1 or y2 <= y1:
        raise argparse.ArgumentTypeError("mask must have non-negative coordinates and positive area")
    return box


def verify_local_edit(
    source_path: str | Path,
    edited_path: str | Path,
    masks: Iterable[Box],
    *,
    tolerance: int = 0,
    max_outside_change_ratio: float = 0.0,
) -> dict[str, object]:
    """Return a JSON-serializable boundary verification report."""
    if not 0 <= tolerance <= 255:
        raise ValueError("tolerance must be between 0 and 255")
    if not 0.0 <= max_outside_change_ratio <= 1.0:
        raise ValueError("max_outside_change_ratio must be between 0 and 1")

    source = Image.open(source_path).convert("RGBA")
    edited = Image.open(edited_path).convert("RGBA")
    if source.size != edited.size:
        return {
            "ok": False,
            "reason": "dimension_mismatch",
            "source_size": source.size,
            "edited_size": edited.size,
        }

    width, height = source.size
    approved = Image.new("1", source.size, 0)
    approved_pixels = approved.load()
    normalized_masks = list(masks)
    if not normalized_masks:
        raise ValueError("at least one mask is required")

    for x1, y1, x2, y2 in normalized_masks:
        if x2 > width or y2 > height:
            raise ValueError(f"mask {(x1, y1, x2, y2)} exceeds image bounds {source.size}")
        for y in range(y1, y2):
            for x in range(x1, x2):
                approved_pixels[x, y] = 1

    difference = ImageChops.difference(source, edited)
    difference_pixels = difference.load()
    inside_pixels = 0
    inside_changed = 0
    outside_pixels = 0
    outside_changed = 0

    for y in range(height):
        for x in range(width):
            changed = max(difference_pixels[x, y]) > tolerance
            if approved_pixels[x, y]:
                inside_pixels += 1
                inside_changed += int(changed)
            else:
                outside_pixels += 1
                outside_changed += int(changed)

    inside_ratio = inside_changed / inside_pixels if inside_pixels else 0.0
    outside_ratio = outside_changed / outside_pixels if outside_pixels else 0.0
    ok = outside_ratio <= max_outside_change_ratio
    return {
        "ok": ok,
        "reason": "ok" if ok else "outside_edit_boundary_changed",
        "image_size": source.size,
        "masks": normalized_masks,
        "tolerance": tolerance,
        "inside_changed_pixels": inside_changed,
        "inside_change_ratio": inside_ratio,
        "outside_changed_pixels": outside_changed,
        "outside_change_ratio": outside_ratio,
        "max_outside_change_ratio": max_outside_change_ratio,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("edited", type=Path)
    parser.add_argument(
        "--mask",
        action="append",
        required=True,
        type=_parse_box,
        help="approved edit rectangle x1,y1,x2,y2; repeat for multiple regions",
    )
    parser.add_argument("--tolerance", type=int, default=0, help="per-channel difference tolerance")
    parser.add_argument(
        "--max-outside-change-ratio",
        type=float,
        default=0.0,
        help="maximum fraction of pixels allowed to change outside approved regions",
    )
    args = parser.parse_args()
    report = verify_local_edit(
        args.source,
        args.edited,
        args.mask,
        tolerance=args.tolerance,
        max_outside_change_ratio=args.max_outside_change_ratio,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
