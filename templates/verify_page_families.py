#!/usr/bin/env python3
"""Validate page-family coverage before batch PPT refinement."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path


ALLOWED_MODES = {"image-led", "native-redesign", "shell-unify", "preserve"}


def _int_slides(value: object, label: str, issues: list[str]) -> list[int]:
    if not isinstance(value, list) or not value:
        issues.append(f"{label} must be a non-empty list")
        return []
    slides: list[int] = []
    for item in value:
        if not isinstance(item, int) or isinstance(item, bool):
            issues.append(f"{label} contains non-integer slide: {item!r}")
            continue
        slides.append(item)
    return slides


def validate_page_families(data: dict) -> dict:
    issues: list[str] = []
    slide_count = data.get("slide_count")
    if not isinstance(slide_count, int) or isinstance(slide_count, bool) or slide_count < 1:
        issues.append("slide_count must be a positive integer")
        slide_count = 0

    changed = _int_slides(data.get("changed_slides"), "changed_slides", issues)
    families = data.get("families")
    if not isinstance(families, list) or not families:
        issues.append("families must be a non-empty list")
        families = []

    names: list[str] = []
    assignments: list[int] = []
    normalized: list[dict] = []

    for index, family in enumerate(families, start=1):
        prefix = f"family[{index}]"
        if not isinstance(family, dict):
            issues.append(f"{prefix} must be an object")
            continue

        name = family.get("name")
        if not isinstance(name, str) or not name.strip():
            issues.append(f"{prefix}.name must be non-empty")
            name = f"(unnamed-{index})"
        names.append(name)

        mode = family.get("mode")
        if mode not in ALLOWED_MODES:
            issues.append(
                f"{prefix}.mode must be one of {sorted(ALLOWED_MODES)}"
            )

        slides = _int_slides(family.get("slides"), f"{prefix}.slides", issues)
        assignments.extend(slides)

        representative = family.get("representative")
        if not isinstance(representative, int) or isinstance(representative, bool):
            issues.append(f"{prefix}.representative must be an integer")
        elif representative not in slides:
            issues.append(f"{prefix}.representative must belong to family slides")

        visual_contract = family.get("visual_contract")
        if not isinstance(visual_contract, dict) or not visual_contract:
            issues.append(f"{prefix}.visual_contract must be a non-empty object")

        if mode == "shell-unify":
            must_preserve = family.get("must_preserve")
            if not isinstance(must_preserve, list) or not must_preserve:
                issues.append(
                    f"{prefix}.must_preserve is required for shell-unify"
                )

        normalized.append(
            {
                "name": name,
                "mode": mode,
                "slides": slides,
                "representative": representative,
            }
        )

    duplicate_names = sorted(
        name for name, count in Counter(names).items() if count > 1
    )
    if duplicate_names:
        issues.append(f"duplicate family names: {duplicate_names}")

    duplicate_slides = sorted(
        slide for slide, count in Counter(assignments).items() if count > 1
    )
    if duplicate_slides:
        issues.append(f"slides assigned to multiple families: {duplicate_slides}")

    changed_set = set(changed)
    assigned_set = set(assignments)
    missing = sorted(changed_set - assigned_set)
    unexpected = sorted(assigned_set - changed_set)
    if missing:
        issues.append(f"changed slides missing a family: {missing}")
    if unexpected:
        issues.append(f"family slides not declared changed: {unexpected}")

    out_of_range = sorted(
        slide
        for slide in changed_set | assigned_set
        if slide_count and not 1 <= slide <= slide_count
    )
    if out_of_range:
        issues.append(f"slides out of range 1..{slide_count}: {out_of_range}")

    return {
        "status": "pass" if not issues else "fail",
        "slide_count": slide_count,
        "changed_slides": sorted(changed_set),
        "families": normalized,
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    data = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = validate_page_families(data)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
