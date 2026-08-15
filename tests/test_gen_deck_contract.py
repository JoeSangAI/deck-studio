import importlib.util
import hashlib
import json
import struct
from pathlib import Path

import pytest


SKILL_ROOT = Path(__file__).parents[1]
GEN_PATH = SKILL_ROOT / "scripts" / "gen_deck.py"
OUTLINE_PATH = SKILL_ROOT / "scripts" / "outline_to_deck.py"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


GEN = load_module("gen_deck_contract", GEN_PATH)
OUTLINE = load_module("outline_to_deck_contract", OUTLINE_PATH)


def write_deck(tmp_path: Path, slide: dict) -> Path:
    path = tmp_path / "deck.json"
    path.write_text(
        json.dumps(
            {
                "size": "2048x1152",
                "workers": 1,
                "slides": [slide],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def media_contract() -> dict:
    return {
        "medium": "LCD",
        "hardware_standard": "lcd-32",
        "scene": "elevator hall",
        "creative_source": "approved campaign key visual",
        "output_type": "environment-image",
        "integration_mode": "environment-reference-fusion",
        "must_preserve": ["screen structure"],
        "acceptance_checks": ["screen is recognizable"],
    }


def reference_asset(tmp_path: Path) -> dict:
    path = tmp_path / "reference.jpg"
    path.write_bytes(b"reference")
    return {
        "id": "fm-lcd-reference-001",
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "role": "environment-geometry",
        "media_type": "lcd",
    }


def standard_reference_asset(tmp_path: Path) -> dict:
    path = tmp_path / "lcd-32-standard.png"
    path.write_bytes(b"verified lcd 32 standard")
    return {
        "id": "fm-standard-lcd-32",
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "role": "verified-standard-frame",
        "media_type": "lcd",
        "hardware_standard": "lcd-32",
    }


def specialist_fields(tmp_path: Path) -> dict:
    asset = tmp_path / "focusmedia.png"
    asset.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + b"\x00\x00\x00\rIHDR"
        + struct.pack(">II", 2048, 1152)
        + b"verified specialist asset"
    )
    framed = tmp_path / "framed-demo.png"
    framed.write_bytes(b"verified framed demo")
    return {
        "production_route": "reference-fusion",
        "specialist_route": "focusmedia-image-gen",
        "specialist_asset_scope": "full-slide",
        "specialist_asset": asset.name,
        "specialist_asset_sha256": hashlib.sha256(asset.read_bytes()).hexdigest(),
        "reference_assets": [
            reference_asset(tmp_path),
            standard_reference_asset(tmp_path),
        ],
        "framed_asset": {
            "id": "fm-lcd-framed-001",
            "path": str(framed),
            "sha256": hashlib.sha256(framed.read_bytes()).hexdigest(),
            "media_type": "lcd",
            "hardware_standard": "lcd-32",
        },
        "media_contract": media_contract(),
    }


def test_generator_does_not_scan_other_products_for_credentials():
    source = GEN_PATH.read_text(encoding="utf-8")

    assert "settings.local.json" not in source
    assert "127.0.0.1:10808" not in source


def test_focusmedia_visual_cannot_fall_through_to_generic_generation(tmp_path):
    path = write_deck(
        tmp_path,
        {
            "id": "M01",
            "prompt": "Premium elevator LCD campaign visual",
        },
    )

    with pytest.raises(SystemExit, match="does not use specialist_route"):
        GEN.load_config(path)


def test_specialist_route_requires_existing_specialist_asset(tmp_path):
    fields = specialist_fields(tmp_path)
    Path(tmp_path / fields["specialist_asset"]).unlink()
    path = write_deck(
        tmp_path,
        {
            "id": "M01",
            "prompt": "Premium campaign visual",
            **fields,
        },
    )

    with pytest.raises(SystemExit, match="specialist_asset not found"):
        GEN.load_config(path)


def test_specialist_route_rejects_a_tampered_specialist_asset(tmp_path):
    fields = specialist_fields(tmp_path)
    (tmp_path / fields["specialist_asset"]).write_bytes(b"tampered")
    path = write_deck(
        tmp_path,
        {
            "id": "M01",
            "prompt": "Premium campaign visual",
            **fields,
        },
    )

    with pytest.raises(SystemExit, match="specialist_asset_sha256 does not match"):
        GEN.load_config(path)


def test_specialist_asset_becomes_the_exact_prebuilt_slide_source(tmp_path):
    fields = specialist_fields(tmp_path)
    path = write_deck(
        tmp_path,
        {
            "id": "M01",
            "prompt": "Premium campaign visual",
            **fields,
        },
    )

    _, slides, _, _, _, _ = GEN.load_config(path)

    assert Path(slides[0]["prebuilt_slide_asset"]).resolve() == (
        tmp_path / fields["specialist_asset"]
    ).resolve()
    assert "photo" not in slides[0]


def test_environment_runtime_requires_the_framed_demo_stage(tmp_path):
    fields = specialist_fields(tmp_path)
    del fields["framed_asset"]
    path = write_deck(
        tmp_path,
        {
            "id": "M01",
            "prompt": "Premium campaign visual",
            **fields,
        },
    )

    with pytest.raises(SystemExit, match="invalid framed_asset"):
        GEN.load_config(path)


def test_full_slide_specialist_asset_is_copied_without_model_generation(tmp_path):
    fields = specialist_fields(tmp_path)
    path = write_deck(
        tmp_path,
        {
            "id": "M01",
            "prompt": "This prompt must never be sent to a model",
            **fields,
        },
    )
    _, slides, _, outdir, _, _ = GEN.load_config(path)
    Path(outdir).mkdir()
    sid, status = GEN.generate_one(
        slides[0],
        {
            "outdir": outdir,
            "force": False,
            "min_bytes": 1,
        },
    )

    output = Path(outdir) / "M01.png"
    source = tmp_path / fields["specialist_asset"]
    assert sid == "M01"
    assert status.startswith("COPIED")
    assert output.read_bytes() == source.read_bytes()


def test_outline_maps_orthogonal_knowledge_and_media_routes(tmp_path):
    html = tmp_path / "outline.html"
    html.write_text(
        """
        <script id="deck-config" type="application/json">
        {"style":{"scene_domain":"elevator hall"},"workers":1}
        </script>
        <section class="page" data-id="M01" data-title="INTERNAL-OUTLINE-COPY"></section>
        """,
        encoding="utf-8",
    )
    fields = specialist_fields(tmp_path)
    plan = {
        "slides": [{
            "slide": 1,
            "mode": "image",
            "overlay_policy": "none",
            "public": {
                "title": "客户可见覆盖能力",
                "claim": "核心生活场景形成稳定触达",
            },
            "knowledge_route": "focusmedia-knowledge",
            "knowledge_contract": {"status": "ok"},
            **fields,
        }]
    }

    deck = OUTLINE.parse_outline(str(html), plan)

    slide = deck["slides"][0]
    assert deck["workers"] == 1
    assert slide["knowledge_route"] == "focusmedia-knowledge"
    assert slide["specialist_route"] == "focusmedia-image-gen"
    assert slide["specialist_asset"] == fields["specialist_asset"]
    assert slide["reference_assets"][0]["id"] == "fm-lcd-reference-001"
    assert "客户可见覆盖能力" in slide["prompt"]
    assert "INTERNAL-OUTLINE-COPY" not in slide["prompt"]
