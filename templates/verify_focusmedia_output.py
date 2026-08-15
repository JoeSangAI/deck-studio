#!/usr/bin/env python3
"""Verify hash-bound Focus Media output reports before deck assembly.

The semantic checks are performed through the focusmedia-image-gen Output Check.
This verifier makes that judgment auditable and prevents a report from being
reused after the output or any reference asset changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_CHECKS = (
    "media_type",
    "hardware_geometry",
    "installation_logic",
    "creative_accuracy",
    "environment_integration",
    "scale",
)
ENVIRONMENT_ONLY_CHECKS = ("no_flat_environment_composite",)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve(base_dir: Path, value: Any) -> Path:
    path = Path(str(value or "").strip()).expanduser()
    return path if path.is_absolute() else (base_dir / path)


def validate_media_output(
    slide: dict[str, Any],
    *,
    base_dir: Path,
    output_path: Path,
) -> list[str]:
    sid = str(slide.get("id") or slide.get("slide") or "<unknown>")
    prefix = f"{sid} media validation"
    errors: list[str] = []
    report_value = slide.get("media_validation_report")
    if not str(report_value or "").strip():
        return [f"{prefix} requires media_validation_report"]
    report_path = _resolve(base_dir, report_value)
    if not report_path.is_file():
        return [f"{prefix} report not found: {report_path}"]
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{prefix} report is invalid JSON: {exc}"]
    if not isinstance(report, dict):
        return [f"{prefix} report must contain an object"]
    if report.get("schema_version") != 2:
        errors.append(f"{prefix} schema_version must be 2")
    if report.get("status") != "passed":
        errors.append(f"{prefix} status must be passed")
    if report.get("validator") != "focusmedia-image-gen/output-check":
        errors.append(
            f"{prefix} validator must be focusmedia-image-gen/output-check"
        )
    if not str(report.get("validated_by") or "").strip():
        errors.append(f"{prefix} validated_by must be non-empty")

    if not output_path.is_file():
        errors.append(f"{prefix} output not found: {output_path}")
    else:
        output = report.get("output")
        if not isinstance(output, dict):
            errors.append(f"{prefix} output must be an object")
        else:
            report_output_path = _resolve(base_dir, output.get("path"))
            if report_output_path.resolve() != output_path.resolve():
                errors.append(f"{prefix} output path does not match generated slide")
            expected_output_hash = str(output.get("sha256") or "").lower()
            if expected_output_hash != sha256_file(output_path):
                errors.append(f"{prefix} output sha256 does not match generated slide")

    contract = slide.get("media_contract")
    report_contract = report.get("media_contract")
    if not isinstance(contract, dict) or not isinstance(report_contract, dict):
        errors.append(f"{prefix} media_contract must exist in slide and report")
    else:
        for field in (
            "medium",
            "hardware_standard",
            "scene",
            "output_type",
            "integration_mode",
        ):
            if report_contract.get(field) != contract.get(field):
                errors.append(f"{prefix} media_contract field {field} does not match")

    output_type = contract.get("output_type") if isinstance(contract, dict) else ""
    if output_type == "environment-image":
        slide_framed = slide.get("framed_asset")
        report_framed = report.get("framed_asset")
        if not isinstance(slide_framed, dict):
            errors.append(f"{prefix} slide framed_asset must be an object")
        if not isinstance(report_framed, dict):
            errors.append(f"{prefix} report framed_asset must be an object")
        if isinstance(slide_framed, dict):
            framed_path = _resolve(base_dir, slide_framed.get("path"))
            framed_hash = str(slide_framed.get("sha256") or "").lower()
            if not framed_path.is_file():
                errors.append(f"{prefix} framed_asset not found: {framed_path}")
            elif framed_hash != sha256_file(framed_path):
                errors.append(f"{prefix} framed_asset sha256 does not match file")
            if isinstance(report_framed, dict):
                report_framed_path = _resolve(base_dir, report_framed.get("path"))
                if report_framed_path.resolve() != framed_path.resolve():
                    errors.append(f"{prefix} report framed_asset path does not match")
                for field in ("id", "sha256", "media_type", "hardware_standard"):
                    if str(report_framed.get(field) or "").lower() != str(
                        slide_framed.get(field) or ""
                    ).lower():
                        errors.append(
                            f"{prefix} report framed_asset field {field} does not match"
                        )
        assembly = report.get("environment_assembly")
        if not isinstance(assembly, dict):
            errors.append(f"{prefix} environment_assembly must be an object")
        else:
            if assembly.get("method") != "reference-anchored-model-edit":
                errors.append(
                    f"{prefix} environment_assembly method must be "
                    "reference-anchored-model-edit"
                )
            if assembly.get("post_overlay_applied") is not False:
                errors.append(
                    f"{prefix} environment_assembly post_overlay_applied must be false"
                )

    specialist_path = _resolve(base_dir, slide.get("specialist_asset"))
    specialist_hash = str(slide.get("specialist_asset_sha256") or "").lower()
    report_specialist = report.get("specialist_asset")
    if not specialist_path.is_file():
        errors.append(f"{prefix} specialist_asset not found: {specialist_path}")
    elif specialist_hash != sha256_file(specialist_path):
        errors.append(f"{prefix} specialist_asset_sha256 does not match file")
    if not isinstance(report_specialist, dict):
        errors.append(f"{prefix} report specialist_asset must be an object")
    else:
        report_specialist_path = _resolve(base_dir, report_specialist.get("path"))
        if report_specialist_path.resolve() != specialist_path.resolve():
            errors.append(f"{prefix} report specialist_asset path does not match")
        if str(report_specialist.get("sha256") or "").lower() != specialist_hash:
            errors.append(f"{prefix} report specialist_asset sha256 does not match")

    slide_refs = slide.get("reference_assets")
    report_refs = report.get("reference_assets")
    if not isinstance(slide_refs, list) or not slide_refs:
        errors.append(f"{prefix} slide reference_assets must be non-empty")
    if not isinstance(report_refs, list) or not report_refs:
        errors.append(f"{prefix} report reference_assets must be non-empty")
    if isinstance(slide_refs, list) and isinstance(report_refs, list):
        for item in slide_refs:
            if not isinstance(item, dict):
                continue
            reference_path = _resolve(base_dir, item.get("path"))
            if not reference_path.is_file():
                errors.append(f"{prefix} reference file not found: {reference_path}")
                continue
            if str(item.get("sha256") or "").lower() != sha256_file(reference_path):
                errors.append(
                    f"{prefix} reference sha256 does not match file: {reference_path}"
                )
        slide_evidence = {
            (str(item.get("id")), str(item.get("sha256")).lower())
            for item in slide_refs
            if isinstance(item, dict)
        }
        report_evidence = {
            (str(item.get("id")), str(item.get("sha256")).lower())
            for item in report_refs
            if isinstance(item, dict)
        }
        if slide_evidence != report_evidence:
            errors.append(f"{prefix} reference asset ids or hashes do not match")

    checks = report.get("checks")
    if not isinstance(checks, dict):
        errors.append(f"{prefix} checks must be an object")
    else:
        for name in REQUIRED_CHECKS:
            status = checks.get(name)
            if output_type == "framed-demo" and name in {
                "installation_logic",
                "environment_integration",
                "scale",
            }:
                allowed = {"passed", "not_applicable"}
            else:
                allowed = {"passed"}
            if status not in allowed:
                errors.append(
                    f"{prefix} check {name} must be one of {sorted(allowed)}"
                )
        if output_type == "environment-image":
            for name in ENVIRONMENT_ONLY_CHECKS:
                if checks.get(name) != "passed":
                    errors.append(f"{prefix} check {name} must be passed")
        if checks.get("scale") == "not_applicable" and not str(
            report.get("scale_not_applicable_reason") or ""
        ).strip():
            errors.append(
                f"{prefix} scale_not_applicable_reason must be non-empty"
            )
    return errors


def validate_deck(deck_path: Path) -> list[str]:
    deck = json.loads(deck_path.read_text(encoding="utf-8"))
    base_dir = deck_path.parent.resolve()
    outdir = _resolve(base_dir, deck.get("outdir", "png"))
    errors: list[str] = []
    for slide in deck.get("slides") or []:
        if not isinstance(slide, dict):
            continue
        if slide.get("specialist_route") != "focusmedia-image-gen":
            continue
        output_path = outdir / f"{slide.get('id')}.png"
        errors.extend(
            validate_media_output(slide, base_dir=base_dir, output_path=output_path)
        )
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("deck", type=Path)
    args = parser.parse_args()
    errors = validate_deck(args.deck.resolve())
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Focus Media output reports verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
