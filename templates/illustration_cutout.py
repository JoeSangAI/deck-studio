#!/usr/bin/env python3
"""
Cut white or solid-color illustration backgrounds into transparent PNG assets.

This tool does not generate images. Use it after a small illustration has already
been generated on a white or plain solid background.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import cv2
import numpy as np
from PIL import Image, ImageFilter, ImageOps


@dataclass
class CutoutResult:
    success: bool
    output_path: Path | None
    fallback_card_path: Path | None
    message: str


def _load_rgb(path: Path) -> Image.Image:
    image = Image.open(path)
    if image.mode not in {"RGB", "RGBA"}:
        image = image.convert("RGBA")
    if image.mode == "RGBA":
        white = Image.new("RGBA", image.size, (255, 255, 255, 255))
        white.alpha_composite(image)
        return white.convert("RGB")
    return image.convert("RGB")


def _corner_samples(rgb: np.ndarray, sample_size: int) -> np.ndarray:
    h, w, _ = rgb.shape
    s = max(1, min(sample_size, h // 4 or 1, w // 4 or 1))
    patches = [
        rgb[:s, :s],
        rgb[:s, w - s:],
        rgb[h - s:, :s],
        rgb[h - s:, w - s:],
    ]
    return np.array([np.median(patch.reshape(-1, 3), axis=0) for patch in patches], dtype=np.float32)


def _background_color(samples: np.ndarray, ambiguity_threshold: float) -> tuple[np.ndarray | None, float]:
    distances = []
    for i in range(len(samples)):
        for j in range(i + 1, len(samples)):
            distances.append(float(np.linalg.norm(samples[i] - samples[j])))
    spread = max(distances) if distances else 0.0
    if spread > ambiguity_threshold:
        return None, spread
    return np.median(samples, axis=0), spread


def _edge_connected_background(candidate: np.ndarray) -> np.ndarray:
    count, labels = cv2.connectedComponents(candidate.astype(np.uint8), connectivity=8)
    if count <= 1:
        return np.zeros(candidate.shape, dtype=bool)

    edge_labels = set(labels[0, :].tolist())
    edge_labels.update(labels[-1, :].tolist())
    edge_labels.update(labels[:, 0].tolist())
    edge_labels.update(labels[:, -1].tolist())
    edge_labels.discard(0)
    if not edge_labels:
        return np.zeros(candidate.shape, dtype=bool)
    return np.isin(labels, list(edge_labels))


def _write_fallback_card(source: Image.Image, fallback_card: Path) -> None:
    fallback_card.parent.mkdir(parents=True, exist_ok=True)
    card = Image.new("RGBA", source.size, (255, 255, 255, 255))
    card.alpha_composite(source.convert("RGBA"))
    card.save(fallback_card)


def cutout_image(
    input_path: str | Path,
    output_path: str | Path,
    *,
    mode: str = "auto",
    fallback_card: str | Path | None = None,
    tolerance: float | None = None,
    feather_radius: float = 0.7,
    sample_size: int = 6,
    ambiguity_threshold: float = 45.0,
) -> CutoutResult:
    """Remove only the background region connected to the image edges."""

    source_path = Path(input_path)
    out_path = Path(output_path)
    fallback_path = Path(fallback_card) if fallback_card else None

    source = _load_rgb(source_path)
    rgb = np.asarray(source, dtype=np.float32)
    samples = _corner_samples(rgb, sample_size)
    bg, spread = _background_color(samples, ambiguity_threshold)
    if bg is None:
        if fallback_path:
            _write_fallback_card(source, fallback_path)
        return CutoutResult(
            success=False,
            output_path=None,
            fallback_card_path=fallback_path,
            message=f"ambiguous edge background; corner spread={spread:.1f}",
        )

    if mode not in {"auto", "white", "solid"}:
        raise ValueError("mode must be one of: auto, white, solid")

    if tolerance is None:
        tolerance = 38.0 if mode in {"auto", "solid"} else 28.0
        if mode == "auto" and float(np.mean(bg)) > 235:
            tolerance = 30.0

    distance = np.linalg.norm(rgb - bg.reshape(1, 1, 3), axis=2)
    candidate = distance <= tolerance
    background = _edge_connected_background(candidate)
    background_ratio = float(np.mean(background))
    if background_ratio < 0.02 or background_ratio > 0.98:
        if fallback_path:
            _write_fallback_card(source, fallback_path)
        return CutoutResult(
            success=False,
            output_path=None,
            fallback_card_path=fallback_path,
            message=f"background ratio out of range: {background_ratio:.1%}",
        )

    alpha = Image.new("L", source.size, 255)
    bg_mask = Image.fromarray((background * 255).astype(np.uint8), mode="L")
    if feather_radius > 0:
        bg_mask = bg_mask.filter(ImageFilter.GaussianBlur(radius=feather_radius))
    alpha = ImageOps.invert(bg_mask)
    alpha_array = np.asarray(alpha).copy()
    alpha_array[~background] = 255
    alpha_array[background] = np.minimum(alpha_array[background], 8)
    alpha = Image.fromarray(alpha_array.astype(np.uint8), mode="L")

    result = source.convert("RGBA")
    result.putalpha(alpha)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.save(out_path)
    return CutoutResult(
        success=True,
        output_path=out_path,
        fallback_card_path=None,
        message=f"removed edge background; background ratio={background_ratio:.1%}",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Remove a white or solid background from a generated illustration.")
    parser.add_argument("input", type=Path, help="Input PNG/JPEG image")
    parser.add_argument("--output", "-o", required=True, type=Path, help="Transparent PNG output path")
    parser.add_argument("--mode", choices=["auto", "white", "solid"], default="auto")
    parser.add_argument("--fallback-card", type=Path, help="Write opaque fallback card here if cutout fails")
    parser.add_argument("--tolerance", type=float, help="Override color-distance tolerance")
    args = parser.parse_args(argv)

    try:
        result = cutout_image(
            args.input,
            args.output,
            mode=args.mode,
            fallback_card=args.fallback_card,
            tolerance=args.tolerance,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(result.message)
    if result.success:
        print(f"wrote {result.output_path}")
        return 0
    if result.fallback_card_path:
        print(f"wrote fallback card {result.fallback_card_path}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
