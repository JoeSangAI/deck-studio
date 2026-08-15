#!/usr/bin/env python3
"""Validate the approved page-level narrative contract before bulk deck production."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


PUBLIC_REQUIRED_FIELDS = (
    "title",
    "claim",
)
NOTES_REQUIRED_FIELDS = (
    "audience_question",
    "purpose",
    "claim_key",
    "evidence_source",
    "speaker_line",
    "transition",
    "excludes",
)
LEGACY_MIXED_FIELDS = PUBLIC_REQUIRED_FIELDS + NOTES_REQUIRED_FIELDS
INTERNAL_AUTHORING_PATTERNS = (
    re.compile(r"正式方案.{0,24}(?:采用|使用).{0,40}(?:口径|年报|资料)"),
    re.compile(r"会面讨论稿|原件实景复用|原件复用"),
    re.compile(r"内部使用|仅限内部|资料待补|待确认"),
)
ALLOWED_MODES = {"editable", "image"}
PRODUCTION_ROUTES = {
    "source-preserve",
    "native-editable",
    "ppt-god-full-image",
    "reference-fusion",
}
OVERLAY_POLICIES = {
    "none",
    "logo-only",
    "precision-assets",
    "local-patch",
}
PRECISION_OVERLAY_ROLES = {
    "logo",
    "qr-code",
    "legal-mark",
    "screenshot",
}
REFERENCE_ROLES = {
    "environment-geometry",
    "hardware-identity",
    "verified-standard-frame",
    "creative",
    "layout",
    "approved-page",
    "approved-media-composite",
}
REFERENCE_ASSET_FIELDS = ("id", "path", "sha256", "role")
SOURCE_LOCK_FIELDS = ("canonical_path", "sha256", "source_kind", "position")
FOCUSMEDIA_ROUTE = "focusmedia-image-gen"
FOCUSMEDIA_KNOWLEDGE_ROUTE = "focusmedia-knowledge"
FOCUSMEDIA_CONTRACT_FIELDS = (
    "medium",
    "hardware_standard",
    "scene",
    "creative_source",
    "output_type",
    "integration_mode",
    "must_preserve",
    "acceptance_checks",
)
FOCUSMEDIA_INTEGRATION_MODES = {
    "framed-standard-composite",
    "environment-reference-fusion",
}
FOCUSMEDIA_OUTPUT_TYPES = {"framed-demo", "environment-image"}
FOCUSMEDIA_ASSET_SCOPES = {"media-visual", "full-slide"}
FOCUSMEDIA_FRAMED_ASSET_FIELDS = (
    "id",
    "path",
    "sha256",
    "media_type",
    "hardware_standard",
)
FOCUSMEDIA_MEDIA_TYPES = {"lcd", "smart-screen", "poster-frame"}
FOCUSMEDIA_HARDWARE_STANDARDS = {
    "lcd": "lcd-32",
    "smart-screen": "smart-32",
    "poster-frame": "poster-frame-standard",
}
FOCUSMEDIA_STANDARD_FILES = {
    "lcd-32": "lcd-32-standard.png",
    "smart-32": "smart-32-standard.png",
    "poster-frame-standard": "poster-frame-standard.png",
}
FOCUSMEDIA_MEDIA_ALIASES = {
    "lcd": "lcd",
    "楼宇lcd": "lcd",
    "电梯电视": "lcd",
    "smart": "smart-screen",
    "smart-screen": "smart-screen",
    "智能屏": "smart-screen",
    "poster": "poster-frame",
    "poster-frame": "poster-frame",
    "框架海报": "poster-frame",
    "海报框架": "poster-frame",
}
FOCUSMEDIA_MEDIA_TERMS = (
    "电梯电视",
    "电梯媒体",
    "楼宇电视",
    "楼宇 lcd",
    "楼宇lcd",
    "智能屏",
    "框架海报",
    "海报框架",
    "电梯海报",
    "poster frame",
    "elevator lcd",
    "smart screen",
)
KNOWLEDGE_MODES = {"knowledge", "research", "source", "connector"}


def _present(value: Any) -> bool:
    if isinstance(value, list):
        return any(_present(item) for item in value)
    if isinstance(value, dict):
        return bool(value)
    return bool(str(value or "").strip())


def _text_fragments(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _text_fragments(item)
    elif isinstance(value, list):
        for item in value:
            yield from _text_fragments(item)
    elif value is not None:
        text = str(value).strip()
        if text:
            yield text


def _sha256_file(path: Path, cache: dict[Path, str]) -> str:
    resolved = path.resolve()
    if resolved not in cache:
        digest = hashlib.sha256()
        with resolved.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        cache[resolved] = digest.hexdigest()
    return cache[resolved]


def _validate_file_evidence(
    *,
    prefix: str,
    path_value: Any,
    sha256_value: Any,
    errors: list[str],
    hash_cache: dict[Path, str],
) -> Path | None:
    raw_path = str(path_value or "").strip()
    expected = str(sha256_value or "").strip().lower()
    if not raw_path:
        errors.append(f"{prefix} path must be non-empty")
        return None
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        errors.append(f"{prefix} path must be absolute")
        return None
    if not path.is_file():
        errors.append(f"{prefix} file does not exist: {path}")
        return None
    if not re.fullmatch(r"[0-9a-f]{64}", expected):
        errors.append(f"{prefix} sha256 must be 64 lowercase hex characters")
        return path
    actual = _sha256_file(path, hash_cache)
    if actual != expected:
        errors.append(f"{prefix} sha256 does not match file")
    return path


def _validate_reference_assets(
    slide_index: int,
    assets: Any,
    errors: list[str],
    hash_cache: dict[Path, str],
    *,
    require_focusmedia: bool = False,
) -> None:
    prefix = f"slide {slide_index} reference_assets"
    if not isinstance(assets, list) or not assets:
        errors.append(f"{prefix} must be a non-empty array")
        return
    seen_ids: set[str] = set()
    for asset_index, asset in enumerate(assets, start=1):
        item_prefix = f"{prefix}[{asset_index}]"
        if not isinstance(asset, dict):
            errors.append(f"{item_prefix} must be an object")
            continue
        for field in REFERENCE_ASSET_FIELDS:
            if not _present(asset.get(field)):
                errors.append(f"{item_prefix} field {field} must be non-empty")
        asset_id = str(asset.get("id") or "").strip()
        if asset_id:
            if asset_id in seen_ids:
                errors.append(f"{item_prefix} id duplicates {asset_id}")
            seen_ids.add(asset_id)
        role = str(asset.get("role") or "").strip()
        if role and role not in REFERENCE_ROLES:
            errors.append(
                f"{item_prefix} role must be one of {sorted(REFERENCE_ROLES)}"
            )
        asset_path = _validate_file_evidence(
            prefix=item_prefix,
            path_value=asset.get("path"),
            sha256_value=asset.get("sha256"),
            errors=errors,
            hash_cache=hash_cache,
        )
        if require_focusmedia:
            media_type = str(asset.get("media_type") or "").strip().casefold()
            if media_type not in FOCUSMEDIA_MEDIA_TYPES:
                errors.append(
                    f"{item_prefix} media_type must be one of "
                    f"{sorted(FOCUSMEDIA_MEDIA_TYPES)}"
                )
        if role == "verified-standard-frame":
            normalized_media = _normalize_focusmedia_type(asset.get("media_type"))
            expected_standard = FOCUSMEDIA_HARDWARE_STANDARDS.get(
                normalized_media,
                "",
            )
            actual_standard = str(
                asset.get("hardware_standard") or ""
            ).strip().casefold()
            if not expected_standard or actual_standard != expected_standard:
                errors.append(
                    f"{item_prefix} verified-standard-frame for {normalized_media} "
                    f"requires hardware_standard {expected_standard or '<known standard>'}"
                )
            expected_filename = FOCUSMEDIA_STANDARD_FILES.get(actual_standard)
            if asset_path is not None and expected_filename and asset_path.name != expected_filename:
                errors.append(
                    f"{item_prefix} verified-standard-frame must use {expected_filename}"
                )


def _normalize_focusmedia_type(value: Any) -> str:
    key = str(value or "").strip().casefold().replace(" ", "")
    return FOCUSMEDIA_MEDIA_ALIASES.get(key, key)


def _validate_focusmedia_framed_asset(
    slide_index: int,
    asset: Any,
    errors: list[str],
    hash_cache: dict[Path, str],
    *,
    expected_medium: str,
    expected_standard: str,
) -> None:
    prefix = f"slide {slide_index} framed_asset"
    if not isinstance(asset, dict):
        errors.append(f"{prefix} must be an object for environment-image runtime")
        return
    for field in FOCUSMEDIA_FRAMED_ASSET_FIELDS:
        if not _present(asset.get(field)):
            errors.append(f"{prefix} field {field} must be non-empty")
    _validate_file_evidence(
        prefix=prefix,
        path_value=asset.get("path"),
        sha256_value=asset.get("sha256"),
        errors=errors,
        hash_cache=hash_cache,
    )
    actual_medium = _normalize_focusmedia_type(asset.get("media_type"))
    if actual_medium not in FOCUSMEDIA_MEDIA_TYPES:
        errors.append(
            f"{prefix} media_type must be one of {sorted(FOCUSMEDIA_MEDIA_TYPES)}"
        )
    elif expected_medium and actual_medium != expected_medium:
        errors.append(
            f"{prefix} media_type {actual_medium} does not match media_contract "
            f"medium {expected_medium}"
        )
    actual_standard = str(asset.get("hardware_standard") or "").strip().casefold()
    if expected_standard and actual_standard != expected_standard:
        errors.append(
            f"{prefix} hardware_standard {actual_standard or '<empty>'} does not "
            f"match media_contract hardware_standard {expected_standard}"
        )


def _validate_source_lock(
    slide_index: int,
    source_lock: Any,
    errors: list[str],
    hash_cache: dict[Path, str],
) -> None:
    prefix = f"slide {slide_index} source_lock"
    if not isinstance(source_lock, dict):
        errors.append(f"{prefix} must be an object for source-preserve")
        return
    for field in SOURCE_LOCK_FIELDS:
        if not _present(source_lock.get(field)):
            errors.append(f"{prefix} field {field} must be non-empty")
    _validate_file_evidence(
        prefix=prefix,
        path_value=source_lock.get("canonical_path"),
        sha256_value=source_lock.get("sha256"),
        errors=errors,
        hash_cache=hash_cache,
    )
    if source_lock.get("source_kind") not in {"slide", "page", "image"}:
        errors.append(f"{prefix} source_kind must be slide, page, or image")
    try:
        position = int(source_lock.get("position", 0))
    except (TypeError, ValueError):
        position = 0
    if position <= 0:
        errors.append(f"{prefix} position must be a positive integer")


def _validate_overlay_policy(
    slide_index: int,
    slide: dict[str, Any],
    errors: list[str],
    hash_cache: dict[Path, str],
) -> None:
    policy = slide.get("overlay_policy")
    if policy not in OVERLAY_POLICIES:
        errors.append(
            f"slide {slide_index} overlay_policy must be one of "
            f"{sorted(OVERLAY_POLICIES)}"
        )
        return
    route = slide.get("production_route")
    if policy == "logo-only" and slide.get("allow_logo_overlay") is not True:
        errors.append(
            f"slide {slide_index} logo-only overlay requires allow_logo_overlay true"
        )
    if policy in {"logo-only", "precision-assets"}:
        assets = slide.get("overlay_assets")
        if not isinstance(assets, list) or not assets:
            errors.append(
                f"slide {slide_index} overlay_assets must be a non-empty array "
                f"for {policy}"
            )
        else:
            if policy == "logo-only" and len(assets) != 1:
                errors.append(
                    f"slide {slide_index} logo-only overlay requires exactly one asset"
                )
            for asset_index, asset in enumerate(assets, start=1):
                prefix = f"slide {slide_index} overlay_assets[{asset_index}]"
                if not isinstance(asset, dict):
                    errors.append(f"{prefix} must be an object")
                    continue
                for field in ("id", "path", "sha256", "role"):
                    if not _present(asset.get(field)):
                        errors.append(f"{prefix} field {field} must be non-empty")
                role = str(asset.get("role") or "").strip()
                if role not in PRECISION_OVERLAY_ROLES:
                    errors.append(
                        f"{prefix} role must be one of "
                        f"{sorted(PRECISION_OVERLAY_ROLES)}"
                    )
                if policy == "logo-only" and role != "logo":
                    errors.append(f"{prefix} role must be logo for logo-only")
                _validate_file_evidence(
                    prefix=prefix,
                    path_value=asset.get("path"),
                    sha256_value=asset.get("sha256"),
                    errors=errors,
                    hash_cache=hash_cache,
                )
    if policy == "local-patch":
        if route != "source-preserve":
            errors.append(
                f"slide {slide_index} local-patch overlay requires "
                "production_route source-preserve"
            )
        if not _present(slide.get("edit_mask")):
            errors.append(
                f"slide {slide_index} edit_mask must be non-empty for local-patch"
            )
    if route == "ppt-god-full-image" and policy not in {"none", "logo-only"}:
        errors.append(
            f"slide {slide_index} ppt-god-full-image only allows none or logo-only overlay"
        )


def _validate_public_copy(
    slide_index: int,
    public: Any,
    errors: list[str],
) -> None:
    prefix = f"slide {slide_index} public"
    if not isinstance(public, dict):
        errors.append(f"{prefix} must be an object")
        return
    for field in PUBLIC_REQUIRED_FIELDS:
        if not _present(public.get(field)):
            errors.append(f"{prefix} field {field} must be non-empty")
    visible_text = " ".join(_text_fragments(public))
    if any(pattern.search(visible_text) for pattern in INTERNAL_AUTHORING_PATTERNS):
        errors.append(f"{prefix} contains internal authoring language")


def _validate_notes(
    slide_index: int,
    notes: Any,
    errors: list[str],
) -> None:
    prefix = f"slide {slide_index} notes"
    if not isinstance(notes, dict):
        errors.append(f"{prefix} must be an object")
        return
    for field in NOTES_REQUIRED_FIELDS:
        if not _present(notes.get(field)):
            errors.append(f"{prefix} field {field} must be non-empty")


def _focusmedia_visual_required(slide: dict[str, Any]) -> bool:
    if slide.get("requires_focusmedia_media") is True:
        return True
    if slide.get("production_route") == "source-preserve":
        return False
    visual_fields = (
        "visual_brief",
        "image_brief",
        "reference_assets",
    )
    fields = visual_fields
    if slide.get("mode") == "image":
        fields += ("public", "notes")
    searchable = " ".join(
        fragment
        for field in fields
        for fragment in _text_fragments(slide.get(field))
    ).casefold()
    return any(term in searchable for term in FOCUSMEDIA_MEDIA_TERMS)


def _validate_knowledge_contract(
    slide_index: int,
    contract: Any,
    errors: list[str],
) -> None:
    prefix = f"slide {slide_index} knowledge_contract"
    if not isinstance(contract, dict):
        errors.append(
            f"{prefix} must be an object for {FOCUSMEDIA_KNOWLEDGE_ROUTE}"
        )
        return

    for field in ("query", "mode", "status", "evidence"):
        if not _present(contract.get(field)):
            errors.append(f"{prefix} field {field} must be non-empty")

    mode = contract.get("mode")
    if mode not in KNOWLEDGE_MODES:
        errors.append(
            f"{prefix} mode must be one of {sorted(KNOWLEDGE_MODES)}"
        )
    if contract.get("status") != "ok":
        errors.append(f"{prefix} status must be ok")
    if mode == "research" and contract.get("candidate_only") is not True:
        errors.append(f"{prefix} research mode must set candidate_only to true")

    evidence = contract.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return
    for evidence_index, item in enumerate(evidence, start=1):
        item_prefix = f"{prefix} evidence[{evidence_index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_prefix} must be an object")
            continue
        if mode == "connector":
            for field in ("connector", "status"):
                if not _present(item.get(field)):
                    errors.append(f"{item_prefix} field {field} must be non-empty")
            if item.get("status") != "ok":
                errors.append(f"{item_prefix} status must be ok")
            continue

        for field in ("source_id", "locator"):
            if not _present(item.get(field)):
                errors.append(f"{item_prefix} field {field} must be non-empty")

        if mode in {"research", "source"}:
            if not _present(item.get("fragment_id") or item.get("entity_id")):
                errors.append(
                    f"{item_prefix} field fragment_id or entity_id must be non-empty"
                )
            for field in ("path", "kind", "position"):
                if not _present(item.get(field)):
                    errors.append(f"{item_prefix} field {field} must be non-empty")

        if mode == "source":
            if not _present(item.get("absolute_path")):
                errors.append(
                    f"{item_prefix} field absolute_path must be non-empty"
                )
            if item.get("kind") not in {"slide", "page"}:
                errors.append(f"{item_prefix} kind must be slide or page")


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def validate_page_plan(
    plan: dict[str, Any],
    route_manifest: dict[str, Any] | None = None,
) -> list[str]:
    errors: list[str] = []
    hash_cache: dict[Path, str] = {}
    if plan.get("status") != "approved":
        errors.append("page plan status must be approved")
    if not str(plan.get("approved_by") or "").strip():
        errors.append("page plan approved_by must be non-empty")
    if not str(plan.get("content_version") or "").strip():
        errors.append("page plan content_version must be non-empty")
    if not str(plan.get("approval_scope") or "").strip():
        errors.append("page plan approval_scope must be non-empty")

    slides = plan.get("slides")
    if not isinstance(slides, list) or not slides:
        return errors + ["page plan slides must be a non-empty array"]

    expected_numbers = list(range(1, len(slides) + 1))
    actual_numbers: list[Any] = []
    claim_keys: dict[str, int] = {}
    claims: dict[str, int] = {}
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            errors.append(f"slide {index} must be an object")
            continue
        number = slide.get("slide")
        actual_numbers.append(number)
        _validate_public_copy(index, slide.get("public"), errors)
        _validate_notes(index, slide.get("notes"), errors)
        for field in LEGACY_MIXED_FIELDS:
            if field in slide:
                errors.append(
                    f"slide {index} field {field} must be nested under public or notes"
                )
        public = slide.get("public") if isinstance(slide.get("public"), dict) else {}
        notes = slide.get("notes") if isinstance(slide.get("notes"), dict) else {}
        claim_key = str(notes.get("claim_key") or "").strip().casefold()
        if claim_key:
            if claim_key in claim_keys:
                errors.append(
                    f"slide {index} claim_key duplicates slide {claim_keys[claim_key]}"
                )
            else:
                claim_keys[claim_key] = index
        normalized_claim = "".join(
            char
            for char in str(public.get("claim") or "").strip().casefold()
            if char.isalnum()
        )
        if normalized_claim:
            if normalized_claim in claims:
                errors.append(
                    f"slide {index} claim duplicates slide {claims[normalized_claim]}"
                )
            else:
                claims[normalized_claim] = index
        if slide.get("mode") not in ALLOWED_MODES:
            errors.append(
                f"slide {index} mode must be editable or image"
            )
        production_route = slide.get("production_route")
        if production_route not in PRODUCTION_ROUTES:
            errors.append(
                f"slide {index} production_route must be one of "
                f"{sorted(PRODUCTION_ROUTES)}"
            )
        elif production_route == "native-editable" and slide.get("mode") != "editable":
            errors.append(
                f"slide {index} native-editable production_route requires mode editable"
            )
        elif production_route in {
            "ppt-god-full-image",
            "reference-fusion",
        } and slide.get("mode") != "image":
            errors.append(
                f"slide {index} {production_route} production_route requires mode image"
            )
        if production_route == "source-preserve":
            _validate_source_lock(
                index,
                slide.get("source_lock"),
                errors,
                hash_cache,
            )
        if (
            production_route == "reference-fusion"
            and slide.get("specialist_route") != FOCUSMEDIA_ROUTE
        ):
            _validate_reference_assets(
                index,
                slide.get("reference_assets"),
                errors,
                hash_cache,
            )
        _validate_overlay_policy(index, slide, errors, hash_cache)
        knowledge_route = slide.get("knowledge_route")
        if knowledge_route == FOCUSMEDIA_KNOWLEDGE_ROUTE:
            _validate_knowledge_contract(
                index,
                slide.get("knowledge_contract"),
                errors,
            )
        elif knowledge_route not in (None, ""):
            errors.append(
                f"slide {index} unsupported knowledge_route {knowledge_route}"
            )

        specialist_route = slide.get("specialist_route")
        if specialist_route == FOCUSMEDIA_ROUTE:
            asset_scope = slide.get("specialist_asset_scope")
            if asset_scope not in FOCUSMEDIA_ASSET_SCOPES:
                errors.append(
                    f"slide {index} specialist_asset_scope must be one of "
                    f"{sorted(FOCUSMEDIA_ASSET_SCOPES)}"
                )
            elif asset_scope == "full-slide" and (
                slide.get("mode") != "image"
                or production_route != "reference-fusion"
            ):
                errors.append(
                    f"slide {index} full-slide Focus Media asset requires mode image "
                    "and production_route reference-fusion"
                )
            elif asset_scope == "media-visual" and (
                slide.get("mode") != "editable"
                or production_route != "native-editable"
            ):
                errors.append(
                    f"slide {index} media-visual Focus Media asset requires mode editable "
                    "and production_route native-editable"
                )
            contract = slide.get("media_contract")
            if not isinstance(contract, dict):
                errors.append(
                    f"slide {index} media_contract must be an object for {FOCUSMEDIA_ROUTE}"
                )
            else:
                for field in FOCUSMEDIA_CONTRACT_FIELDS:
                    value = contract.get(field)
                    if not _present(value):
                        errors.append(
                            f"slide {index} media_contract field {field} must be non-empty"
                        )
                integration_mode = contract.get("integration_mode")
                if integration_mode not in FOCUSMEDIA_INTEGRATION_MODES:
                    errors.append(
                        f"slide {index} media_contract integration_mode must be one of "
                        f"{sorted(FOCUSMEDIA_INTEGRATION_MODES)}"
                    )
                output_type = contract.get("output_type")
                if output_type not in FOCUSMEDIA_OUTPUT_TYPES:
                    errors.append(
                        f"slide {index} media_contract output_type must be one of "
                        f"{sorted(FOCUSMEDIA_OUTPUT_TYPES)}"
                    )
                expected_mode = {
                    "framed-demo": "framed-standard-composite",
                    "environment-image": "environment-reference-fusion",
                }.get(output_type)
                if expected_mode and integration_mode != expected_mode:
                    errors.append(
                        f"slide {index} media_contract output_type {output_type} requires "
                        f"integration_mode {expected_mode}"
                    )
            _validate_reference_assets(
                index,
                slide.get("reference_assets"),
                errors,
                hash_cache,
                require_focusmedia=True,
            )
            expected_medium = _normalize_focusmedia_type(
                contract.get("medium") if isinstance(contract, dict) else ""
            )
            expected_standard = FOCUSMEDIA_HARDWARE_STANDARDS.get(
                expected_medium,
                "",
            )
            actual_standard = str(
                contract.get("hardware_standard") if isinstance(contract, dict) else ""
            ).strip().casefold()
            if expected_standard and actual_standard != expected_standard:
                errors.append(
                    f"slide {index} media_contract medium {expected_medium} requires "
                    f"hardware_standard {expected_standard}"
                )
            actual_media = {
                _normalize_focusmedia_type(item.get("media_type"))
                for item in (slide.get("reference_assets") or [])
                if isinstance(item, dict)
            }
            if expected_medium and expected_medium not in actual_media:
                errors.append(
                    f"slide {index} reference_assets do not include media type "
                    f"{expected_medium} required by media_contract"
                )
            reference_roles = {
                str(item.get("role") or "").strip()
                for item in (slide.get("reference_assets") or [])
                if isinstance(item, dict)
            }
            output_type = contract.get("output_type") if isinstance(contract, dict) else ""
            if output_type == "framed-demo" and "verified-standard-frame" not in reference_roles:
                errors.append(
                    f"slide {index} framed-demo requires a verified-standard-frame reference"
                )
            if output_type == "environment-image":
                if "environment-geometry" not in reference_roles:
                    errors.append(
                        f"slide {index} environment-image requires an "
                        "environment-geometry reference"
                    )
                if "verified-standard-frame" not in reference_roles:
                    errors.append(
                        f"slide {index} environment-image requires a "
                        "verified-standard-frame reference"
                    )
                if slide.get("framed_asset") not in (None, ""):
                    _validate_focusmedia_framed_asset(
                        index,
                        slide.get("framed_asset"),
                        errors,
                        hash_cache,
                        expected_medium=expected_medium,
                        expected_standard=expected_standard,
                    )
        elif specialist_route not in (None, ""):
            errors.append(
                f"slide {index} unsupported specialist_route {specialist_route}"
            )
        if _focusmedia_visual_required(slide) and specialist_route != FOCUSMEDIA_ROUTE:
            errors.append(
                f"slide {index} Focus Media visual requires specialist_route {FOCUSMEDIA_ROUTE}"
            )
        if (
            production_route == "ppt-god-full-image"
            and _focusmedia_visual_required(slide)
        ):
            errors.append(
                f"slide {index} Focus Media visual cannot use ppt-god-full-image; "
                "use reference-fusion"
            )

    if actual_numbers != expected_numbers:
        errors.append(
            f"page plan slide numbers must be consecutive from 1: {actual_numbers}"
        )

    if route_manifest is not None:
        routes = route_manifest.get("slides")
        if not isinstance(routes, list):
            errors.append("route manifest slides must be an array")
        else:
            route_pairs = [
                (
                    item.get("slide"),
                    item.get("mode"),
                    item.get("production_route"),
                    item.get("overlay_policy"),
                    tuple(
                        asset.get("id")
                        for asset in item.get("overlay_assets", [])
                        if isinstance(asset, dict)
                    ),
                    item.get("knowledge_route"),
                    item.get("specialist_route"),
                    item.get("specialist_asset_scope"),
                    item.get("specialist_asset_sha256"),
                )
                for item in routes
                if isinstance(item, dict)
            ]
            plan_pairs = [
                (
                    item.get("slide"),
                    item.get("mode"),
                    item.get("production_route"),
                    item.get("overlay_policy"),
                    tuple(
                        asset.get("id")
                        for asset in item.get("overlay_assets", [])
                        if isinstance(asset, dict)
                    ),
                    item.get("knowledge_route"),
                    item.get("specialist_route"),
                    item.get("specialist_asset_scope"),
                    item.get("specialist_asset_sha256"),
                )
                for item in slides
                if isinstance(item, dict)
            ]
            if route_pairs != plan_pairs:
                errors.append(
                    "route manifest slide order and production routes must match page plan"
                )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("page_plan", type=Path)
    parser.add_argument("--route-manifest", type=Path)
    args = parser.parse_args()

    plan = read_json(args.page_plan)
    route = read_json(args.route_manifest) if args.route_manifest else None
    errors = validate_page_plan(plan, route)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"page plan verified: {len(plan['slides'])} slides")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
