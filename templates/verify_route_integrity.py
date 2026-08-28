#!/usr/bin/env python3
"""Verify final PPTX structure against the PPT God project snapshot.

The public CLI reads ``project_snapshot``.  ``validate_routes`` still accepts the
former route manifest in-process so archived projects remain auditable.
"""

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

try:
    from templates.project_snapshot_contract import (
        PRECISION_OVERLAY_ROLES as SNAPSHOT_PRECISION_OVERLAY_ROLES,
        gate_status,
        is_project_snapshot,
        load_json_source,
        page_num,
        snapshot_assets,
        snapshot_slides,
        validate_snapshot_base,
    )
except ModuleNotFoundError:  # direct execution from templates/
    from project_snapshot_contract import (
        PRECISION_OVERLAY_ROLES as SNAPSHOT_PRECISION_OVERLAY_ROLES,
        gate_status,
        is_project_snapshot,
        load_json_source,
        page_num,
        snapshot_assets,
        snapshot_slides,
        validate_snapshot_base,
    )


P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
O_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"p": P_NS, "a": A_NS, "r": R_NS, "or": O_R_NS}
PRECISION_OVERLAY_ROLES = {
    "logo",
    "qr-code",
    "legal-mark",
    "screenshot",
}
EXACT_ASSET_ROLES = {
    "logo",
    "product",
    "client-evidence",
    "qr-code",
    "legal-mark",
    "approved-creative",
    "storyboard",
    "client-original",
    "screenshot",
}


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


def _valid_sha256(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _validate_embedded_picture_assets(
    *,
    route: dict,
    field: str,
    slide: int,
    item: SlideFacts,
    issues: list[dict[str, object]],
    allowed_roles: set[str],
    required: bool = False,
) -> None:
    raw_assets = route.get(field)
    code_prefix = field.removesuffix("s")
    if raw_assets in (None, ""):
        if required:
            issues.append({
                "severity": "high",
                "code": f"{code_prefix}s_missing",
                "slide": slide,
            })
        return
    if not isinstance(raw_assets, list) or not raw_assets:
        issues.append({
            "severity": "high",
            "code": f"{code_prefix}s_invalid",
            "slide": slide,
        })
        return

    seen_ids: set[str] = set()
    for asset_index, asset in enumerate(raw_assets):
        if not isinstance(asset, dict):
            issues.append({
                "severity": "high",
                "code": f"{code_prefix}_invalid",
                "slide": slide,
                "asset_index": asset_index,
            })
            continue
        asset_id = str(asset.get("id", "")).strip()
        role = str(asset.get("role", "")).strip()
        if not asset_id or not role:
            issues.append({
                "severity": "high",
                "code": f"{code_prefix}_identity_missing",
                "slide": slide,
                "asset_index": asset_index,
            })
        elif asset_id in seen_ids:
            issues.append({
                "severity": "high",
                "code": f"{code_prefix}_id_duplicate",
                "slide": slide,
                "asset_index": asset_index,
                "asset_id": asset_id,
            })
        else:
            seen_ids.add(asset_id)
        if role and role not in allowed_roles:
            issues.append({
                "severity": "high",
                "code": f"{code_prefix}_role_invalid",
                "slide": slide,
                "asset_index": asset_index,
                "role": role,
            })

        path_value = str(asset.get("path", "")).strip()
        asset_path = Path(path_value) if path_value else None
        declared_hash = str(asset.get("sha256", "")).strip().lower()
        actual_hash = ""
        if asset_path is None or not asset_path.is_absolute() or not asset_path.is_file():
            issues.append({
                "severity": "high",
                "code": f"{code_prefix}_path_invalid",
                "slide": slide,
                "asset_index": asset_index,
            })
        else:
            actual_hash = hashlib.sha256(asset_path.read_bytes()).hexdigest()
        if not _valid_sha256(declared_hash):
            issues.append({
                "severity": "high",
                "code": f"{code_prefix}_hash_missing",
                "slide": slide,
                "asset_index": asset_index,
            })
            continue
        if actual_hash and actual_hash != declared_hash:
            issues.append({
                "severity": "high",
                "code": f"{code_prefix}_hash_mismatch",
                "slide": slide,
                "asset_index": asset_index,
            })
        if declared_hash not in item.picture_hashes:
            issues.append({
                "severity": "high",
                "code": f"{code_prefix}_not_embedded_exactly",
                "slide": slide,
                "asset_index": asset_index,
            })


def _snapshot_asset_hash(
    asset: dict,
    *,
    slide: int,
    asset_index: int,
    issues: list[dict[str, object]],
) -> str:
    raw_path = str(asset.get("path") or "").strip()
    raw_hash = str(asset.get("sha256") or "").strip().lower()
    if not raw_path or not Path(raw_path).is_absolute() or not Path(raw_path).is_file():
        issues.append({
            "severity": "high",
            "code": "snapshot_asset_path_invalid",
            "slide": slide,
            "asset_index": asset_index,
        })
        return ""
    if not _valid_sha256(raw_hash):
        issues.append({
            "severity": "high",
            "code": "snapshot_asset_hash_missing",
            "slide": slide,
            "asset_index": asset_index,
        })
        return ""
    actual = hashlib.sha256(Path(raw_path).read_bytes()).hexdigest()
    if actual != raw_hash:
        issues.append({
            "severity": "high",
            "code": "snapshot_asset_hash_mismatch",
            "slide": slide,
            "asset_index": asset_index,
        })
        return ""
    return raw_hash


def _snapshot_output_asset(slide: dict) -> dict | None:
    for candidate in (
        slide.get("render_asset"),
        slide.get("output_asset"),
        (slide.get("evidence_state") or {}).get("output_asset")
        if isinstance(slide.get("evidence_state"), dict)
        else None,
    ):
        if isinstance(candidate, dict):
            return candidate
    image_path = str(slide.get("image_path") or "").strip()
    if image_path:
        return {"file_path": image_path}
    return None


def _snapshot_file_hash(
    asset: dict,
    *,
    slide: int,
    code: str,
    issues: list[dict[str, object]],
) -> str:
    raw_path = str(asset.get("file_path") or asset.get("path") or "").strip()
    path = Path(raw_path) if raw_path else None
    if path is None or not path.is_absolute() or not path.is_file():
        issues.append({"severity": "high", "code": code + "_path_invalid", "slide": slide})
        return ""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    declared = str(asset.get("sha256") or "").strip().lower()
    if declared and declared != digest:
        issues.append({"severity": "high", "code": code + "_hash_mismatch", "slide": slide})
        return ""
    return digest


def validate_snapshot_routes(pptx: Path, snapshot: dict) -> dict:
    facts = inspect_pptx(pptx)
    issues: list[dict[str, object]] = [
        {"severity": "high", "code": "project_snapshot_invalid", "detail": message}
        for message in validate_snapshot_base(snapshot)
    ]
    if gate_status(snapshot, "visual_evidence_route") != "approved":
        issues.append({"severity": "high", "code": "gate_2_not_approved"})

    project_assets = snapshot_assets(snapshot)
    seen: set[int] = set()
    for snapshot_slide in snapshot_slides(snapshot):
        if not isinstance(snapshot_slide, dict):
            continue
        slide = page_num(snapshot_slide)
        production_type = str(snapshot_slide.get("production_type") or "").strip()
        if slide in seen:
            issues.append({"severity": "high", "code": "duplicate_route", "slide": slide})
            continue
        seen.add(slide)
        item = facts.get(slide)
        if item is None:
            issues.append({"severity": "high", "code": "missing_slide", "slide": slide})
            continue

        slide_id = str(snapshot_slide.get("id") or "")
        raw_assets = [asset for asset in project_assets if str(asset.get("slide_id") or "") == slide_id]
        overlay_assets = [
            asset for asset in raw_assets
            if str(asset.get("role") or "") in SNAPSHOT_PRECISION_OVERLAY_ROLES
            and str(asset.get("process_mode") or "") in {"paste", "overlay", "exact", "native"}
        ]
        embedded_assets = [
            asset for asset in raw_assets
            if production_type != "image_integrated"
            and (asset.get("user_locked") is True or asset.get("fidelity") == "exact")
            and str(asset.get("process_mode") or "") in {"paste", "overlay", "exact", "native"}
        ]
        for asset in embedded_assets:
            digest = _snapshot_file_hash(
                asset, slide=slide, code="exact_asset", issues=issues
            )
            if digest and digest not in item.picture_hashes:
                issues.append({
                    "severity": "high",
                    "code": "exact_asset_not_embedded_exactly",
                    "slide": slide,
                    "asset_id": asset.get("id"),
                })

        output_asset = _snapshot_output_asset(snapshot_slide)
        if production_type in {"image_integrated", "hybrid"} and output_asset is None:
            issues.append({
                "severity": "high",
                "code": "image_path_required",
                "slide": slide,
            })
        if output_asset is not None:
            output_hash = _snapshot_file_hash(
                output_asset, slide=slide, code="render_asset", issues=issues
            )
            if output_hash and output_hash not in item.picture_hashes:
                issues.append({
                    "severity": "high",
                    "code": "render_asset_not_embedded_exactly",
                    "slide": slide,
                })

        native_relationships = " ".join(item.relationship_types).lower()
        has_native_content = (
            bool(item.text)
            or item.graphic_frame_count > 0
            or any(token in native_relationships for token in ("chart", "video", "media", "hyperlink"))
        )
        overlays_in_pptx = item.picture_count - item.full_slide_picture_count

        if production_type == "image_integrated":
            if item.full_slide_picture_count != 1:
                issues.append({
                    "severity": "high",
                    "code": "image_integrated_requires_one_full_slide_picture",
                    "slide": slide,
                    "full_slide_pictures": item.full_slide_picture_count,
                })
            if item.text or item.graphic_frame_count or item.shape_count:
                issues.append({
                    "severity": "high",
                    "code": "image_integrated_has_native_core_objects",
                    "slide": slide,
                })
            if overlays_in_pptx > len(overlay_assets):
                issues.append({
                    "severity": "high",
                    "code": "image_integrated_overlay_count_mismatch",
                    "slide": slide,
                    "actual": overlays_in_pptx,
                    "declared": len(overlay_assets),
                })
        elif production_type == "hybrid":
            if item.full_slide_picture_count != 1:
                issues.append({
                    "severity": "high",
                    "code": "hybrid_requires_one_full_slide_background",
                    "slide": slide,
                    "full_slide_pictures": item.full_slide_picture_count,
                })
            if not has_native_content:
                issues.append({
                    "severity": "high",
                    "code": "hybrid_requires_native_core_objects",
                    "slide": slide,
                })
        elif production_type == "native_editable":
            if not has_native_content:
                issues.append({
                    "severity": "high",
                    "code": "native_editable_has_no_native_content",
                    "slide": slide,
                })
            if item.full_slide_picture_count and len(item.text) < 10 and item.graphic_frame_count == 0:
                issues.append({
                    "severity": "high",
                    "code": "native_editable_looks_rasterized",
                    "slide": slide,
                })

        layout_spec = snapshot_slide.get("layout_spec")
        if production_type in {"hybrid", "native_editable"} and not isinstance(layout_spec, dict):
            issues.append({
                "severity": "high",
                "code": "layout_spec_required",
                "slide": slide,
            })
            layout_spec = {}
        blocks = layout_spec.get("blocks") if isinstance(layout_spec, dict) else []
        if production_type in {"hybrid", "native_editable"} and not isinstance(blocks, list):
            issues.append({
                "severity": "high",
                "code": "layout_spec_blocks_invalid",
                "slide": slide,
            })
            blocks = []
        required_kinds = {
            str(block.get("kind") or "")
            for block in blocks
            if isinstance(block, dict)
        }
        kind_checks = {
            "title": bool(item.text),
            "subtitle": bool(item.text),
            "body": bool(item.text),
            "text": bool(item.text),
            "bullets": bool(item.text),
            "kpi": bool(item.text),
            "chart": item.graphic_frame_count > 0 or "chart" in native_relationships,
            "table": item.graphic_frame_count > 0,
            "image": item.picture_count > item.full_slide_picture_count,
            "shape": item.shape_count > 0,
        }
        for kind in sorted(required_kinds):
            if kind in kind_checks and not kind_checks[kind]:
                issues.append({
                    "severity": "high",
                    "code": f"missing_layout_spec_{kind}",
                    "slide": slide,
                })

    unclassified = sorted(set(facts) - seen)
    if unclassified:
        issues.append({"severity": "high", "code": "unclassified_slides", "slides": unclassified})
    return {
        "status": "fail" if any(issue["severity"] == "high" for issue in issues) else "pass",
        "pptx": str(pptx),
        "slide_count": len(facts),
        "issues": issues,
    }


def validate_routes(pptx: Path, manifest: dict) -> dict:
    if is_project_snapshot(manifest):
        return validate_snapshot_routes(pptx, manifest)
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
        production_route = str(route.get("production_route", "")).strip()
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
        overlay_policy = str(route.get("overlay_policy") or "none").strip()
        if route.get("allow_logo_overlay") is True and overlay_policy == "none":
            overlay_policy = "logo-only"
        _validate_embedded_picture_assets(
            route=route,
            field="exact_assets",
            slide=slide,
            item=item,
            issues=issues,
            allowed_roles=EXACT_ASSET_ROLES,
        )
        if overlay_policy in {"logo-only", "precision-assets"}:
            _validate_embedded_picture_assets(
                route=route,
                field="overlay_assets",
                slide=slide,
                item=item,
                issues=issues,
                allowed_roles=PRECISION_OVERLAY_ROLES,
                required=True,
            )
            overlay_assets = route.get("overlay_assets")
            if overlay_policy == "logo-only" and isinstance(overlay_assets, list):
                if len(overlay_assets) != 1:
                    issues.append({
                        "severity": "high",
                        "code": "logo_overlay_requires_exactly_one_asset",
                        "slide": slide,
                    })
                elif str(overlay_assets[0].get("role", "")).strip() != "logo":
                    issues.append({
                        "severity": "high",
                        "code": "logo_overlay_role_must_be_logo",
                        "slide": slide,
                    })
        if production_route == "ppt-god-full-image":
            provenance = route.get("generation_provenance")
            if not isinstance(provenance, dict):
                issues.append({
                    "severity": "high",
                    "code": "ppt_god_generation_provenance_missing",
                    "slide": slide,
                })
            else:
                if str(provenance.get("producer", "")).strip() != "ppt-god":
                    issues.append({
                        "severity": "high",
                        "code": "ppt_god_producer_invalid",
                        "slide": slide,
                    })
                if str(provenance.get("method", "")).strip() != "native-generate-slides":
                    issues.append({
                        "severity": "high",
                        "code": "ppt_god_generation_method_invalid",
                        "slide": slide,
                    })
                if not str(provenance.get("project_id", "")).strip():
                    issues.append({
                        "severity": "high",
                        "code": "ppt_god_project_id_missing",
                        "slide": slide,
                    })
                try:
                    page_num = int(provenance.get("page_num", 0))
                except (TypeError, ValueError):
                    page_num = 0
                if page_num <= 0:
                    issues.append({
                        "severity": "high",
                        "code": "ppt_god_page_num_invalid",
                        "slide": slide,
                    })
                asset_value = str(provenance.get("asset_path", "")).strip()
                asset_path = Path(asset_value) if asset_value else None
                declared_hash = str(provenance.get("sha256", "")).strip().lower()
                actual_hash = ""
                if asset_path is None or not asset_path.is_absolute() or not asset_path.is_file():
                    issues.append({
                        "severity": "high",
                        "code": "ppt_god_asset_path_invalid",
                        "slide": slide,
                    })
                else:
                    actual_hash = hashlib.sha256(asset_path.read_bytes()).hexdigest()
                if not _valid_sha256(declared_hash):
                    issues.append({
                        "severity": "high",
                        "code": "ppt_god_asset_hash_missing",
                        "slide": slide,
                    })
                else:
                    if actual_hash and actual_hash != declared_hash:
                        issues.append({
                            "severity": "high",
                            "code": "ppt_god_asset_hash_mismatch",
                            "slide": slide,
                        })
                    if declared_hash not in item.picture_hashes:
                        issues.append({
                            "severity": "high",
                            "code": "ppt_god_asset_not_embedded_exactly",
                            "slide": slide,
                        })
        if production_route == "reference-fusion":
            reference_assets = route.get("reference_assets")
            if not isinstance(reference_assets, list) or not reference_assets:
                issues.append({
                    "severity": "high",
                    "code": "reference_fusion_assets_missing",
                    "slide": slide,
                })
            else:
                for index, asset in enumerate(reference_assets):
                    if not isinstance(asset, dict):
                        issues.append({
                            "severity": "high",
                            "code": "reference_fusion_asset_invalid",
                            "slide": slide,
                            "asset_index": index,
                        })
                        continue
                    if not str(asset.get("id", "")).strip() or not str(asset.get("role", "")).strip():
                        issues.append({
                            "severity": "high",
                            "code": "reference_fusion_asset_identity_missing",
                            "slide": slide,
                            "asset_index": index,
                        })
                    ref_value = str(asset.get("path", "")).strip()
                    ref_path = Path(ref_value) if ref_value else None
                    ref_hash = str(asset.get("sha256", "")).strip().lower()
                    if ref_path is None or not ref_path.is_absolute() or not ref_path.is_file():
                        issues.append({
                            "severity": "high",
                            "code": "reference_fusion_asset_path_invalid",
                            "slide": slide,
                            "asset_index": index,
                        })
                    if not _valid_sha256(ref_hash):
                        issues.append({
                            "severity": "high",
                            "code": "reference_fusion_asset_hash_missing",
                            "slide": slide,
                            "asset_index": index,
                        })
                    elif ref_path is not None and ref_path.is_file():
                        actual_ref_hash = hashlib.sha256(ref_path.read_bytes()).hexdigest()
                        if actual_ref_hash != ref_hash:
                            issues.append({
                                "severity": "high",
                                "code": "reference_fusion_asset_hash_mismatch",
                                "slide": slide,
                                "asset_index": index,
                            })

            provenance = route.get("generation_provenance")
            if not isinstance(provenance, dict):
                issues.append({
                    "severity": "high",
                    "code": "reference_fusion_generation_provenance_missing",
                    "slide": slide,
                })
            else:
                producer = str(provenance.get("producer", "")).strip()
                method = str(provenance.get("method", "")).strip()
                if not producer:
                    issues.append({
                        "severity": "high",
                        "code": "reference_fusion_producer_missing",
                        "slide": slide,
                    })
                disallowed_methods = {
                    "native-slide-render",
                    "powerpoint-render",
                    "screenshot",
                    "flattened-slide",
                    "rasterized-native-slide",
                }
                if not method or method in disallowed_methods:
                    issues.append({
                        "severity": "high",
                        "code": "reference_fusion_method_invalid",
                        "slide": slide,
                        "method": method,
                    })
                output_value = str(provenance.get("asset_path", "")).strip()
                output_path = Path(output_value) if output_value else None
                output_hash = str(provenance.get("sha256", "")).strip().lower()
                actual_output_hash = ""
                if output_path is None or not output_path.is_absolute() or not output_path.is_file():
                    issues.append({
                        "severity": "high",
                        "code": "reference_fusion_output_path_invalid",
                        "slide": slide,
                    })
                else:
                    actual_output_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
                if not _valid_sha256(output_hash):
                    issues.append({
                        "severity": "high",
                        "code": "reference_fusion_output_hash_missing",
                        "slide": slide,
                    })
                else:
                    if actual_output_hash and actual_output_hash != output_hash:
                        issues.append({
                            "severity": "high",
                            "code": "reference_fusion_output_hash_mismatch",
                            "slide": slide,
                        })
                    if output_hash not in item.picture_hashes:
                        issues.append({
                            "severity": "high",
                            "code": "reference_fusion_output_not_embedded_exactly",
                            "slide": slide,
                        })
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
    parser = argparse.ArgumentParser(
        description="Verify final PPTX routes from a read-only PPT God project snapshot"
    )
    parser.add_argument("pptx", type=Path)
    parser.add_argument("project_snapshot", help="snapshot JSON file or HTTP(S) URL")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    manifest = load_json_source(args.project_snapshot)
    if not is_project_snapshot(manifest):
        print(json.dumps({
            "status": "fail",
            "issues": [{
                "severity": "high",
                "code": "project_snapshot_required",
                "detail": (
                    "new CLI workflow requires a PPT God project_snapshot; "
                    "legacy route_manifest.json is read-only compatibility data"
                ),
            }],
        }, ensure_ascii=False, indent=2))
        return 1
    report = validate_routes(args.pptx, manifest)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    print(output, end="")
    return 1 if report["status"] == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
