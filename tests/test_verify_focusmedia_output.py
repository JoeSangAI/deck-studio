import hashlib
import json
import subprocess
import sys
from pathlib import Path

from templates.verify_focusmedia_output import validate_media_output


ASSEMBLE = Path(__file__).parents[1] / "scripts" / "assemble_pptx.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_contract(tmp_path: Path):
    reference = tmp_path / "reference.jpg"
    reference.write_bytes(b"reference")
    standard = tmp_path / "lcd-32-standard.png"
    standard.write_bytes(b"approved lcd 32 standard")
    output = tmp_path / "M01.png"
    output.write_bytes(b"generated slide")
    specialist = tmp_path / "focusmedia-composite.png"
    specialist.write_bytes(b"approved media composite")
    framed = tmp_path / "framed-demo.png"
    framed.write_bytes(b"approved framed demo")
    report = tmp_path / "M01.media-validation.json"
    slide = {
        "id": "M01",
        "specialist_route": "focusmedia-image-gen",
        "specialist_asset_scope": "full-slide",
        "specialist_asset": specialist.name,
        "specialist_asset_sha256": digest(specialist),
        "framed_asset": {
            "id": "fm-lcd-framed-001",
            "path": str(framed),
            "sha256": digest(framed),
            "media_type": "lcd",
            "hardware_standard": "lcd-32",
        },
        "reference_assets": [
            {
                "id": "fm-lcd-reference-001",
                "path": str(reference),
                "sha256": digest(reference),
                "role": "environment-geometry",
                "media_type": "lcd",
            },
            {
                "id": "fm-standard-lcd-32",
                "path": str(standard),
                "sha256": digest(standard),
                "role": "verified-standard-frame",
                "media_type": "lcd",
                "hardware_standard": "lcd-32",
            },
        ],
        "media_contract": {
            "medium": "LCD",
            "hardware_standard": "lcd-32",
            "scene": "elevator-hall",
            "output_type": "environment-image",
            "integration_mode": "environment-reference-fusion",
        },
        "media_validation_report": report.name,
    }
    payload = {
        "schema_version": 2,
        "status": "passed",
        "validator": "focusmedia-image-gen/output-check",
        "validated_by": "visual-qa",
        "output": {"path": output.name, "sha256": digest(output)},
        "specialist_asset": {
            "path": specialist.name,
            "sha256": digest(specialist),
        },
        "framed_asset": {
            "id": "fm-lcd-framed-001",
            "path": str(framed),
            "sha256": digest(framed),
            "media_type": "lcd",
            "hardware_standard": "lcd-32",
        },
        "media_contract": {
            "medium": "LCD",
            "hardware_standard": "lcd-32",
            "scene": "elevator-hall",
            "output_type": "environment-image",
            "integration_mode": "environment-reference-fusion",
        },
        "environment_assembly": {
            "method": "reference-anchored-model-edit",
            "post_overlay_applied": False,
        },
        "reference_assets": [
            {
                "id": "fm-lcd-reference-001",
                "sha256": digest(reference),
            },
            {
                "id": "fm-standard-lcd-32",
                "sha256": digest(standard),
            },
        ],
        "checks": {
            "media_type": "passed",
            "hardware_geometry": "passed",
            "installation_logic": "passed",
            "creative_accuracy": "passed",
            "environment_integration": "passed",
            "scale": "passed",
            "no_flat_environment_composite": "passed",
        },
    }
    report.write_text(json.dumps(payload), encoding="utf-8")
    return slide, output, report


def test_hash_bound_focusmedia_report_passes(tmp_path):
    slide, output, _ = build_contract(tmp_path)

    assert validate_media_output(slide, base_dir=tmp_path, output_path=output) == []


def test_stale_report_fails_after_output_changes(tmp_path):
    slide, output, _ = build_contract(tmp_path)
    output.write_bytes(b"regenerated slide")

    assert any(
        "output sha256 does not match" in item
        for item in validate_media_output(slide, base_dir=tmp_path, output_path=output)
    )


def test_reference_identity_cannot_be_removed_from_report(tmp_path):
    slide, output, report = build_contract(tmp_path)
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["reference_assets"] = []
    report.write_text(json.dumps(payload), encoding="utf-8")

    errors = validate_media_output(slide, base_dir=tmp_path, output_path=output)

    assert any("report reference_assets must be non-empty" in item for item in errors)
    assert any("reference asset ids or hashes do not match" in item for item in errors)


def test_generic_vertical_screen_cannot_be_marked_passed_with_failed_geometry(tmp_path):
    slide, output, report = build_contract(tmp_path)
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["checks"]["hardware_geometry"] = "failed"
    report.write_text(json.dumps(payload), encoding="utf-8")

    assert any(
        "check hardware_geometry must be" in item
        for item in validate_media_output(slide, base_dir=tmp_path, output_path=output)
    )


def test_environment_report_rejects_any_post_overlay(tmp_path):
    slide, output, report = build_contract(tmp_path)
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["environment_assembly"]["post_overlay_applied"] = True
    report.write_text(json.dumps(payload), encoding="utf-8")

    assert any(
        "post_overlay_applied must be false" in item
        for item in validate_media_output(slide, base_dir=tmp_path, output_path=output)
    )


def test_environment_report_requires_no_flat_composite_check(tmp_path):
    slide, output, report = build_contract(tmp_path)
    payload = json.loads(report.read_text(encoding="utf-8"))
    del payload["checks"]["no_flat_environment_composite"]
    report.write_text(json.dumps(payload), encoding="utf-8")

    assert any(
        "check no_flat_environment_composite must be passed" in item
        for item in validate_media_output(slide, base_dir=tmp_path, output_path=output)
    )


def test_pptx_assembly_blocks_focusmedia_slide_without_final_report(tmp_path):
    output_dir = tmp_path / "png"
    output_dir.mkdir()
    (output_dir / "M01.png").write_bytes(b"x" * 50000)
    deck = tmp_path / "deck.json"
    deck.write_text(json.dumps({
        "size": "2048x1152",
        "outdir": "png",
        "slides": [{
            "id": "M01",
            "specialist_route": "focusmedia-image-gen",
        }],
    }), encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(ASSEMBLE), str(deck), "--out", str(tmp_path / "out.pptx")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "MEDIA VALIDATION ERROR" in result.stdout
    assert not (tmp_path / "out.pptx").exists()
