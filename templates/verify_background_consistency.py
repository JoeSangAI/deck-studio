#!/usr/bin/env python3
"""Verify one exact slide-background color across a declared PPTX page route."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def parse_slides(value: str) -> set[int]:
    slides: set[int] = set()
    for part in (item.strip() for item in value.split(",")):
        if not part:
            continue
        if "-" in part:
            start, end = (int(item) for item in part.split("-", 1))
            slides.update(range(start, end + 1))
        else:
            slides.add(int(part))
    return slides


def slide_number(member: str) -> int:
    return int(re.search(r"slide(\d+)\.xml$", member).group(1))


def explicit_background(root: ET.Element) -> str | None:
    solid = root.find("./p:cSld/p:bg/p:bgPr/a:solidFill", NS)
    if solid is None:
        return None
    srgb = solid.find("a:srgbClr", NS)
    if srgb is not None and srgb.attrib.get("val"):
        return f"#{srgb.attrib['val'].upper()}"
    scheme = solid.find("a:schemeClr", NS)
    if scheme is not None and scheme.attrib.get("val"):
        return f"scheme:{scheme.attrib['val']}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify an exact background color on all non-excluded slides."
    )
    parser.add_argument("pptx", type=Path)
    parser.add_argument("--expected", required=True, help="Expected HEX color, e.g. F7F5F0")
    parser.add_argument(
        "--exclude-slides",
        default="",
        help="Comma-separated slide numbers or ranges, e.g. 1,2,9,22,35-36",
    )
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    expected = "#" + args.expected.strip().lstrip("#").upper()
    excluded = parse_slides(args.exclude_slides)
    records: list[dict[str, object]] = []
    issues: list[str] = []

    with ZipFile(args.pptx) as archive:
        members = sorted(
            (
                name
                for name in archive.namelist()
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
            ),
            key=slide_number,
        )
        for member in members:
            page = slide_number(member)
            if page in excluded:
                records.append({"slide": page, "status": "excluded"})
                continue
            root = ET.fromstring(archive.read(member))
            background = explicit_background(root)
            status = "pass" if background == expected else "fail"
            records.append(
                {"slide": page, "background": background, "status": status}
            )
            if status == "fail":
                issues.append(
                    f"P{page} background {background or '(missing/inherited)'} != {expected}"
                )

    report = {
        "pptx": str(args.pptx),
        "expected": expected,
        "excluded_slides": sorted(excluded),
        "records": records,
        "issues": issues,
        "status": "pass" if not issues else "fail",
    }
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
