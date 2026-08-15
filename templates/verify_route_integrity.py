#!/usr/bin/env python3
"""Verify that a hybrid PPTX preserves the intended editable/image page routes."""

from __future__ import annotations

import argparse
import hashlib
import json
import posixpath
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET


P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
O_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"p": P_NS, "a": A_NS, "r": R_NS, "or": O_R_NS}


@dataclass
class SlideFacts:
    slide: int
    text: str
    shape_count: int
    graphic_frame_count: int
    picture_count: int
    full_slide_picture_count: int
    picture_hashes: list[str]
    relationship_types: list[str]


def _read_xml(archive: zipfile.ZipFile, member: str) -> ET.Element:
    try:
        return ET.fromstring(archive.read(member))
    except KeyError as exc:
        raise ValueError(f"PPTX 缺少必要文件：{member}") from exc


def _slide_size(archive: zipfile.ZipFile) -> tuple[int, int]:
    root = _read_xml(archive, "ppt/presentation.xml")
    size = root.find("p:sldSz", NS)
    if size is None:
        return 12192000, 6858000
    return int(size.attrib.get("cx", 12192000)), int(size.attrib.get("cy", 6858000))


def _is_full_slide_picture(pic: ET.Element, width: int, height: int) -> bool:
    xfrm = pic.find("p:spPr/a:xfrm", NS)
    if xfrm is None:
        return False
    off = xfrm.find("a:off", NS)
    ext = xfrm.find("a:ext", NS)
    if off is None or ext is None:
        return False
    x = int(off.attrib.get("x", 0))
    y = int(off.attrib.get("y", 0))
    cx = int(ext.attrib.get("cx", 0))
    cy = int(ext.attrib.get("cy", 0))
    tolerance_x = width * 0.03
    tolerance_y = height * 0.03
    return x <= tolerance_x and y <= tolerance_y and cx >= width * 0.94 and cy >= height * 0.94


def _relationship_types(archive: zipfile.ZipFile, slide: int) -> list[str]:
    member = f"ppt/slides/_rels/slide{slide}.xml.rels"
    try:
        root = ET.fromstring(archive.read(member))
    except KeyError:
        return []
    return [rel.attrib.get("Type", "") for rel in root.findall("r:Relationship", NS)]


def _picture_hashes(
    archive: zipfile.ZipFile,
    slide: int,
    root: ET.Element,
) -> list[str]:
    member = f"ppt/slides/_rels/slide{slide}.xml.rels"
    try:
        rel_root = ET.fromstring(archive.read(member))
    except KeyError:
        return []
    targets = {
        rel.attrib.get("Id", ""): rel.attrib.get("Target", "")
        for rel in rel_root.findall("r:Relationship", NS)
    }
    hashes: list[str] = []
    for blip in root.findall(".//a:blip", NS):
        rel_id = blip.attrib.get(f"{{{O_R_NS}}}embed", "")
        target = targets.get(rel_id, "")
        if not target or "://" in target:
            continue
        media_member = posixpath.normpath(
            posixpath.join("ppt/slides", target)
        )
        try:
            hashes.append(hashlib.sha256(archive.read(media_member)).hexdigest())
        except KeyError:
            continue
    return hashes


def inspect_pptx(pptx: Path) -> dict[int, SlideFacts]:
    with zipfile.ZipFile(pptx) as archive:
        width, height = _slide_size(archive)
        slide_members = sorted(
            (
                name
                for name in archive.namelist()
                if name.startswith("ppt/slides/slide") and name.endswith(".xml")
                and "/_rels/" not in name
            ),
            key=lambda name: int(Path(name).stem.removeprefix("slide")),
        )
        facts: dict[int, SlideFacts] = {}
        for member in slide_members:
            slide = int(Path(member).stem.removeprefix("slide"))
            root = _read_xml(archive, member)
            pictures = root.findall(".//p:pic", NS)
            text = "".join(node.text or "" for node in root.findall(".//a:t", NS)).strip()
            facts[slide] = SlideFacts(
                slide=slide,
                text=text,
                shape_count=len(root.findall(".//p:sp", NS)),
                graphic_frame_count=len(root.findall(".//p:graphicFrame", NS)),
                picture_count=len(pictures),
                full_slide_picture_count=sum(_is_full_slide_picture(pic, width, height) for pic in pictures),
                picture_hashes=_picture_hashes(archive, slide, root),
                relationship_types=_relationship_types(archive, slide),
            )
        return facts


def validate_routes(pptx: Path, manifest: dict) -> dict:
    facts = inspect_pptx(pptx)
    issues: list[dict[str, object]] = []
    routes = manifest.get("slides")
    if not isinstance(routes, list) or not routes:
        raise ValueError("路线清单必须包含非空 slides 数组。")

    seen: set[int] = set()
    for route in routes:
        if not isinstance(route, dict):
            issues.append({
                "severity": "high",
                "code": "invalid_route_entry",
            })
            continue
        try:
            slide = int(route.get("slide", 0))
        except (TypeError, ValueError):
            issues.append({
                "severity": "high",
                "code": "invalid_slide_number",
                "value": route.get("slide"),
            })
            continue
        mode = str(route.get("mode", "")).strip()
        raw_requires = route.get("requires", [])
        if not isinstance(raw_requires, list):
            issues.append({
                "severity": "high",
                "code": "requires_must_be_an_array",
                "slide": slide,
            })
            raw_requires = []
        requires = {str(item).strip() for item in raw_requires}
        if slide in seen:
            issues.append({"severity": "high", "code": "duplicate_route", "slide": slide})
            continue
        seen.add(slide)
        if slide not in facts:
            issues.append({"severity": "high", "code": "missing_slide", "slide": slide})
            continue
        if mode not in {"editable", "image"}:
            issues.append({"severity": "high", "code": "invalid_route_mode", "slide": slide, "mode": mode})
            continue

        item = facts[slide]
        if route.get("specialist_route") == "focusmedia-image-gen":
            expected_specialist_hash = str(
                route.get("specialist_asset_sha256") or ""
            ).strip().lower()
            if len(expected_specialist_hash) != 64:
                issues.append({
                    "severity": "high",
                    "code": "focusmedia_specialist_asset_hash_missing",
                    "slide": slide,
                })
            elif expected_specialist_hash not in item.picture_hashes:
                issues.append({
                    "severity": "high",
                    "code": "focusmedia_specialist_asset_not_embedded_exactly",
                    "slide": slide,
                })
        if mode == "editable":
            has_native_content = bool(item.text) or item.graphic_frame_count > 0
            if not has_native_content:
                issues.append({
                    "severity": "high",
                    "code": "editable_slide_has_no_native_content",
                    "slide": slide,
                })
            if item.full_slide_picture_count and len(item.text) < 10 and item.graphic_frame_count == 0:
                issues.append({
                    "severity": "high",
                    "code": "editable_slide_looks_rasterized",
                    "slide": slide,
                    "full_slide_pictures": item.full_slide_picture_count,
                })

            relationship_text = " ".join(item.relationship_types).lower()
            checks = {
                "text": bool(item.text),
                "chart": item.graphic_frame_count > 0 or "chart" in relationship_text,
                "media": any(token in relationship_text for token in ("video", "media", "hyperlink")),
            }
            for required in sorted(requires):
                if required not in checks:
                    issues.append({"severity": "high", "code": "unknown_requirement", "slide": slide, "requirement": required})
                elif not checks[required]:
                    issues.append({"severity": "high", "code": f"missing_required_{required}", "slide": slide})
        else:
            overlay_pictures = item.picture_count - item.full_slide_picture_count
            overlay_policy = str(route.get("overlay_policy") or "none").strip()
            if route.get("allow_logo_overlay") is True and overlay_policy == "none":
                overlay_policy = "logo-only"
            if overlay_policy not in {
                "none",
                "logo-only",
                "precision-assets",
                "local-patch",
            }:
                issues.append({
                    "severity": "high",
                    "code": "invalid_overlay_policy",
                    "slide": slide,
                    "overlay_policy": overlay_policy,
                })
            if item.full_slide_picture_count == 0:
                issues.append({
                    "severity": "high",
                    "code": "image_slide_missing_full_slide_picture",
                    "slide": slide,
                })
            elif item.full_slide_picture_count > 1:
                issues.append({
                    "severity": "high",
                    "code": "image_slide_has_multiple_full_slide_pictures",
                    "slide": slide,
                    "full_slide_pictures": item.full_slide_picture_count,
                })
            if overlay_pictures:
                if overlay_policy in {"none", "local-patch"}:
                    issues.append({
                        "severity": "high",
                        "code": "image_slide_has_unapproved_overlay_pictures",
                        "slide": slide,
                        "overlay_pictures": overlay_pictures,
                    })
                elif overlay_policy == "logo-only" and overlay_pictures > 1:
                    issues.append({
                        "severity": "high",
                        "code": "image_slide_has_multiple_overlay_pictures",
                        "slide": slide,
                        "overlay_pictures": overlay_pictures,
                    })
                elif overlay_policy == "precision-assets":
                    overlay_assets = route.get("overlay_assets")
                    expected = len(overlay_assets) if isinstance(overlay_assets, list) else 0
                    if expected <= 0:
                        issues.append({
                            "severity": "high",
                            "code": "precision_overlay_assets_missing",
                            "slide": slide,
                        })
                    elif overlay_pictures != expected:
                        issues.append({
                            "severity": "high",
                            "code": "precision_overlay_picture_count_mismatch",
                            "slide": slide,
                            "overlay_pictures": overlay_pictures,
                            "declared_overlay_assets": expected,
                        })
            elif overlay_policy == "precision-assets":
                issues.append({
                    "severity": "high",
                    "code": "precision_overlay_assets_missing",
                    "slide": slide,
                })
            if item.text:
                issues.append({
                    "severity": "high",
                    "code": "image_slide_has_native_text",
                    "slide": slide,
                })
            if item.graphic_frame_count:
                issues.append({
                    "severity": "high",
                    "code": "image_slide_has_graphic_frame",
                    "slide": slide,
                    "graphic_frames": item.graphic_frame_count,
                })
            if item.shape_count:
                issues.append({
                    "severity": "high",
                    "code": "image_slide_has_native_shapes",
                    "slide": slide,
                    "shapes": item.shape_count,
                })
            if requires:
                issues.append({
                    "severity": "high",
                    "code": "image_slide_cannot_declare_native_requirements",
                    "slide": slide,
                    "requirements": sorted(requires),
                })

    unclassified = sorted(set(facts) - seen)
    if unclassified:
        issues.append({"severity": "high", "code": "unclassified_slides", "slides": unclassified})

    return {
        "status": "fail" if any(item["severity"] == "high" for item in issues) else "pass",
        "pptx": str(pptx),
        "slide_count": len(facts),
        "issues": issues,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("pptx", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    report = validate_routes(args.pptx, manifest)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
