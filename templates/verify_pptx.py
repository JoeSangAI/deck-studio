#!/usr/bin/env python3
"""
PPTX delivery verifier for the deck-studio PPT workspace.

Checks:
- slide count equality
- visible text preservation by slide
- picture count regression by slide
- optional exact preservation of embedded audio/video by slide
- risky media resources such as SVG/bin packaged images
- optional display-ratio drift warnings for pictures
"""

from __future__ import annotations

import argparse
import hashlib
import posixpath
import re
import sys
from collections import Counter
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
from xml.etree import ElementTree as ET

try:
    from PIL import Image
except Exception:  # pragma: no cover - optional dependency
    Image = None


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

AV_SUFFIXES = {
    ".aac", ".avi", ".m4a", ".m4v", ".mov", ".mp3", ".mp4", ".mpeg",
    ".mpg", ".ogg", ".wav", ".webm", ".wma", ".wmv",
}


@dataclass
class Issue:
    level: str
    message: str


def norm(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def slide_names(z: ZipFile) -> list[str]:
    names = [
        n for n in z.namelist()
        if re.fullmatch(r"ppt/slides/slide\d+\.xml", n)
    ]
    return sorted(names, key=lambda n: int(re.search(r"slide(\d+)\.xml", n).group(1)))


def slide_number(name: str) -> int:
    return int(re.search(r"slide(\d+)\.xml", name).group(1))


def ignore_text(text: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(text) for p in patterns)


def extract_slide_texts(path: Path, ignore_patterns: list[re.Pattern[str]]) -> dict[int, list[str]]:
    result: dict[int, list[str]] = {}
    with ZipFile(path) as z:
        for name in slide_names(z):
            root = ET.fromstring(z.read(name))
            texts = []
            for t in root.findall(".//a:t", NS):
                if t.text and not ignore_text(t.text, ignore_patterns):
                    texts.append(t.text)
            result[slide_number(name)] = texts
    return result


def count_pictures(path: Path) -> dict[int, int]:
    result: dict[int, int] = {}
    with ZipFile(path) as z:
        for name in slide_names(z):
            root = ET.fromstring(z.read(name))
            result[slide_number(name)] = len(root.findall(".//p:pic", NS))
    return result


def risky_media(path: Path) -> list[str]:
    risks = []
    with ZipFile(path) as z:
        for name in z.namelist():
            if not name.startswith("ppt/media/"):
                continue
            suffix = Path(name).suffix.lower()
            data = z.read(name)[:256].lstrip()
            if suffix in {".bin", ".svg"}:
                risks.append(f"{name} ({suffix})")
            elif data.startswith(b"<svg") or b"<svg" in data[:128].lower():
                risks.append(f"{name} (svg bytes)")
    return risks


def embedded_av_bindings(path: Path) -> dict[int, Counter[tuple[str, str]]]:
    """Return per-slide embedded AV fingerprints, deduplicated by package target.

    PowerPoint commonly writes both a ``video`` relationship and a Microsoft
    ``media`` relationship to the same MP4. They describe one embedded asset,
    so the target is counted once per slide before its bytes are fingerprinted.
    External links are intentionally excluded because this gate verifies
    embedded package preservation.
    """
    result: dict[int, Counter[tuple[str, str]]] = {}
    with ZipFile(path) as z:
        names = set(z.namelist())
        for slide_name in slide_names(z):
            rel_name = slide_name.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
            bindings: Counter[tuple[str, str]] = Counter()
            seen_targets: set[str] = set()
            if rel_name in names:
                root = ET.fromstring(z.read(rel_name))
                for rel in root.findall(".//rel:Relationship", NS):
                    if rel.attrib.get("TargetMode", "").lower() == "external":
                        continue
                    target = rel.attrib.get("Target", "")
                    rel_type = rel.attrib.get("Type", "").rstrip("/").split("/")[-1].lower()
                    if not target:
                        continue
                    if target.startswith("/"):
                        package_target = posixpath.normpath(target.lstrip("/"))
                    else:
                        package_target = posixpath.normpath(
                            posixpath.join(posixpath.dirname(slide_name), target)
                        )
                    suffix = Path(package_target).suffix.lower()
                    is_av = suffix in AV_SUFFIXES or rel_type in {"audio", "sound", "video"}
                    is_media_rel = rel_type == "media" and package_target.startswith("ppt/media/")
                    if not (is_av or is_media_rel) or package_target not in names:
                        continue
                    if package_target in seen_targets:
                        continue
                    seen_targets.add(package_target)
                    digest = hashlib.sha256(z.read(package_target)).hexdigest()
                    bindings[(suffix or rel_type, digest)] += 1
            result[slide_number(slide_name)] = bindings
    return result


def rels_for_slide(z: ZipFile, slide_xml_name: str) -> dict[str, str]:
    rel_name = slide_xml_name.replace("ppt/slides/", "ppt/slides/_rels/") + ".rels"
    if rel_name not in z.namelist():
        return {}
    root = ET.fromstring(z.read(rel_name))
    out = {}
    for rel in root.findall(".//rel:Relationship", NS):
        rid = rel.attrib.get("Id")
        target = rel.attrib.get("Target", "")
        if rid and target:
            if target.startswith("../"):
                target = "ppt/" + target[3:]
            out[rid] = target
    return out


def ratio_warnings(path: Path, threshold: float) -> list[str]:
    if Image is None:
        return []
    warnings: list[str] = []
    with ZipFile(path) as z:
        for name in slide_names(z):
            rels = rels_for_slide(z, name)
            root = ET.fromstring(z.read(name))
            for pic in root.findall(".//p:pic", NS):
                blip = pic.find(".//a:blip", NS)
                rid = blip.attrib.get(f"{{{NS['r']}}}embed") if blip is not None else None
                media = rels.get(rid or "")
                ext = pic.find(".//p:spPr/a:xfrm/a:ext", NS)
                if not media or ext is None or media not in z.namelist():
                    continue
                try:
                    cx = float(ext.attrib.get("cx", "0"))
                    cy = float(ext.attrib.get("cy", "0"))
                    if cx <= 0 or cy <= 0:
                        continue
                    display_ratio = cx / cy
                    im = Image.open(BytesIO(z.read(media)))
                    image_ratio = im.width / im.height
                except Exception:
                    continue
                drift = abs(display_ratio - image_ratio) / image_ratio
                if drift > threshold:
                    warnings.append(
                        f"slide {slide_number(name)} {media}: display ratio {display_ratio:.3f}, "
                        f"image ratio {image_ratio:.3f}, drift {drift:.1%}"
                    )
    return warnings


def verify(
    source: Path,
    output: Path,
    ignore_patterns: list[re.Pattern[str]],
    fail_risky_media: bool,
    require_media_preserved: bool = False,
) -> list[Issue]:
    issues: list[Issue] = []
    source_texts = extract_slide_texts(source, ignore_patterns)
    output_texts = extract_slide_texts(output, ignore_patterns)
    if len(source_texts) != len(output_texts):
        issues.append(Issue("error", f"slide count changed: {len(source_texts)} -> {len(output_texts)}"))

    for index, texts in source_texts.items():
        out_joined = norm("".join(output_texts.get(index, [])))
        for text in texts:
            n = norm(text)
            if n and n not in out_joined:
                issues.append(Issue("error", f"slide {index}: missing text {text!r}"))

    src_pics = count_pictures(source)
    out_pics = count_pictures(output)
    for index, count in src_pics.items():
        new_count = out_pics.get(index, 0)
        if new_count < count:
            issues.append(Issue("warning", f"slide {index}: picture count decreased {count} -> {new_count}"))

    if require_media_preserved:
        source_av = embedded_av_bindings(source)
        output_av = embedded_av_bindings(output)
        for index in sorted(set(source_av) | set(output_av)):
            before = source_av.get(index, Counter())
            after = output_av.get(index, Counter())
            if before != after:
                issues.append(
                    Issue(
                        "error",
                        f"slide {index}: embedded audio/video changed {sum(before.values())} -> {sum(after.values())}",
                    )
                )

    risks = risky_media(output)
    for item in risks:
        issues.append(Issue("error" if fail_risky_media else "warning", f"risky media resource: {item}"))

    for warning in ratio_warnings(output, threshold=0.08):
        issues.append(Issue("warning", f"possible image ratio drift: {warning}"))

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify PPTX content preservation and delivery risks.")
    parser.add_argument("source", type=Path, help="Original/source PPTX")
    parser.add_argument("output", type=Path, help="Polished output PPTX")
    parser.add_argument("--ignore-pattern", action="append", default=[], help="Regex for source text to ignore")
    parser.add_argument("--fail-risky-media", action="store_true", help="Treat SVG/bin media as errors")
    parser.add_argument(
        "--require-media-preserved",
        action="store_true",
        help="Fail if any slide's embedded audio/video bindings or bytes changed",
    )
    args = parser.parse_args()

    patterns = [re.compile(p) for p in args.ignore_pattern]
    issues = verify(
        args.source,
        args.output,
        patterns,
        args.fail_risky_media,
        args.require_media_preserved,
    )

    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    print(f"PPTX VERIFY: {args.source.name} -> {args.output.name}")
    print(f"errors={len(errors)} warnings={len(warnings)}")
    for issue in issues:
        print(f"[{issue.level}] {issue.message}")

    if errors:
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
