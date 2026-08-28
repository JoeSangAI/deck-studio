#!/usr/bin/env python3
import hashlib
import json
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from templates.verify_route_integrity import validate_routes


PRESENTATION = """<?xml version="1.0" encoding="UTF-8"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldSz cx="12192000" cy="6858000"/>
</p:presentation>
"""

IMAGE_SLIDE = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree><p:pic><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm></p:spPr></p:pic></p:spTree></p:cSld>
</p:sld>
"""

IMAGE_WITH_EMBEDDED_ASSET = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld><p:spTree><p:pic>
    <p:blipFill><a:blip r:embed="rId1"/></p:blipFill>
    <p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm></p:spPr>
  </p:pic></p:spTree></p:cSld>
</p:sld>
"""

IMAGE_ASSET_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/full-slide.png"/>
</Relationships>
"""

EDITABLE_SLIDE = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>可编辑正文内容</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>
</p:sld>
"""

EMPTY_SLIDE = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree/></p:cSld>
</p:sld>
"""

IMAGE_WITH_TEXT = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree>
    <p:pic><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm></p:spPr></p:pic>
    <p:sp><p:txBody><a:p><a:r><a:t>后叠正文</a:t></a:r></a:p></p:txBody></p:sp>
  </p:spTree></p:cSld>
</p:sld>
"""

IMAGE_WITH_GRAPHIC_FRAME = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree>
    <p:pic><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm></p:spPr></p:pic>
    <p:graphicFrame/>
  </p:spTree></p:cSld>
</p:sld>
"""

TWO_FULL_SLIDE_IMAGES = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree>
    <p:pic><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm></p:spPr></p:pic>
    <p:pic><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm></p:spPr></p:pic>
  </p:spTree></p:cSld>
</p:sld>
"""

IMAGE_WITH_LOGO = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree>
    <p:pic><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm></p:spPr></p:pic>
    <p:pic><p:spPr><a:xfrm><a:off x="11000000" y="6200000"/><a:ext cx="600000" cy="300000"/></a:xfrm></p:spPr></p:pic>
  </p:spTree></p:cSld>
</p:sld>
"""

IMAGE_WITH_EXACT_OVERLAY = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld><p:spTree>
    <p:pic><p:blipFill><a:blip r:embed="rId1"/></p:blipFill><p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm></p:spPr></p:pic>
    <p:pic><p:blipFill><a:blip r:embed="rId2"/></p:blipFill><p:spPr><a:xfrm><a:off x="11000000" y="6200000"/><a:ext cx="600000" cy="300000"/></a:xfrm></p:spPr></p:pic>
  </p:spTree></p:cSld>
</p:sld>
"""

EXACT_OVERLAY_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/full-slide.png"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/logo.png"/>
</Relationships>
"""

EDITABLE_WITH_SPECIALIST_IMAGE = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld><p:spTree>
    <p:pic><p:blipFill><a:blip r:embed="rId1"/></p:blipFill><p:spPr><a:xfrm><a:off x="500000" y="1000000"/><a:ext cx="6000000" cy="4000000"/></a:xfrm></p:spPr></p:pic>
    <p:sp><p:txBody><a:p><a:r><a:t>可编辑页面标题</a:t></a:r></a:p></p:txBody></p:sp>
  </p:spTree></p:cSld>
</p:sld>
"""

SPECIALIST_RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/specialist.png"/>
</Relationships>
"""


def build_fixture(path: Path) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", IMAGE_SLIDE)
        archive.writestr("ppt/slides/slide2.xml", EDITABLE_SLIDE)


def build_single_slide_fixture(path: Path, slide_xml: str) -> None:
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", slide_xml)


with tempfile.TemporaryDirectory() as temp_dir:
    pptx = Path(temp_dir) / "hybrid.pptx"
    build_fixture(pptx)

    valid = validate_routes(pptx, {
        "slides": [
            {"slide": 1, "mode": "image"},
            {"slide": 2, "mode": "editable", "requires": ["text"]},
        ]
    })
    assert valid["status"] == "pass", json.dumps(valid, ensure_ascii=False)

    rasterized = validate_routes(pptx, {
        "slides": [
            {"slide": 1, "mode": "editable", "requires": ["text"]},
            {"slide": 2, "mode": "editable", "requires": ["text"]},
        ]
    })
    assert rasterized["status"] == "fail"
    codes = {issue["code"] for issue in rasterized["issues"]}
    assert "editable_slide_looks_rasterized" in codes
    assert "missing_required_text" in codes

print("test_verify_route_integrity passed")


def validate_image_fixture(
    tmp_path: Path,
    xml: str,
    *,
    allow_logo_overlay: bool = False,
) -> dict:
    pptx = tmp_path / "image-route.pptx"
    build_single_slide_fixture(pptx, xml)
    route = {"slide": 1, "mode": "image"}
    if allow_logo_overlay:
        route["allow_logo_overlay"] = True
    return validate_routes(
        pptx,
        {"slides": [route]},
    )


def test_image_route_rejects_empty_slide(tmp_path):
    report = validate_image_fixture(tmp_path, EMPTY_SLIDE)
    assert report["status"] == "fail"
    assert report["issues"][0]["code"] == "image_slide_missing_full_slide_picture"


def test_image_route_rejects_native_text_and_shapes(tmp_path):
    report = validate_image_fixture(tmp_path, IMAGE_WITH_TEXT)
    codes = {issue["code"] for issue in report["issues"]}
    assert report["status"] == "fail"
    assert "image_slide_has_native_text" in codes
    assert "image_slide_has_native_shapes" in codes


def test_image_route_rejects_graphic_frame(tmp_path):
    report = validate_image_fixture(tmp_path, IMAGE_WITH_GRAPHIC_FRAME)
    assert report["status"] == "fail"
    assert "image_slide_has_graphic_frame" in {
        issue["code"] for issue in report["issues"]
    }


def test_image_route_rejects_two_full_slide_images(tmp_path):
    report = validate_image_fixture(tmp_path, TWO_FULL_SLIDE_IMAGES)
    assert report["status"] == "fail"
    assert "image_slide_has_multiple_full_slide_pictures" in {
        issue["code"] for issue in report["issues"]
    }


def test_image_route_allows_one_full_slide_image_and_logo(tmp_path):
    pptx = tmp_path / "image-with-logo.pptx"
    full_slide = b"approved full slide"
    logo = b"exact approved logo"
    logo_path = tmp_path / "logo.png"
    logo_path.write_bytes(logo)
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", IMAGE_WITH_EXACT_OVERLAY)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", EXACT_OVERLAY_RELS)
        archive.writestr("ppt/media/full-slide.png", full_slide)
        archive.writestr("ppt/media/logo.png", logo)
    report = validate_routes(pptx, {"slides": [{
        "slide": 1,
        "mode": "image",
        "overlay_policy": "logo-only",
        "allow_logo_overlay": True,
        "overlay_assets": [{
            "id": "approved-logo",
            "role": "logo",
            "path": str(logo_path),
            "sha256": hashlib.sha256(logo).hexdigest(),
        }],
    }]})
    assert report["status"] == "pass"
    assert report["issues"] == []


def test_logo_overlay_requires_declared_exact_asset(tmp_path):
    report = validate_image_fixture(
        tmp_path,
        IMAGE_WITH_LOGO,
        allow_logo_overlay=True,
    )
    assert report["status"] == "fail"
    assert "overlay_assets_missing" in {
        issue["code"] for issue in report["issues"]
    }


def test_logo_overlay_rejects_non_logo_asset(tmp_path):
    pptx = tmp_path / "image-with-wrong-overlay-role.pptx"
    full_slide = b"approved full slide"
    overlay = b"qr image mislabeled as logo overlay"
    overlay_path = tmp_path / "qr.png"
    overlay_path.write_bytes(overlay)
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", IMAGE_WITH_EXACT_OVERLAY)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", EXACT_OVERLAY_RELS)
        archive.writestr("ppt/media/full-slide.png", full_slide)
        archive.writestr("ppt/media/logo.png", overlay)
    report = validate_routes(pptx, {"slides": [{
        "slide": 1,
        "mode": "image",
        "overlay_policy": "logo-only",
        "allow_logo_overlay": True,
        "overlay_assets": [{
            "id": "qr-code",
            "role": "qr-code",
            "path": str(overlay_path),
            "sha256": hashlib.sha256(overlay).hexdigest(),
        }],
    }]})
    assert report["status"] == "fail"
    assert "logo_overlay_role_must_be_logo" in {
        issue["code"] for issue in report["issues"]
    }


def test_image_route_rejects_unapproved_picture_overlay(tmp_path):
    report = validate_image_fixture(tmp_path, IMAGE_WITH_LOGO)
    assert report["status"] == "fail"
    assert "image_slide_has_unapproved_overlay_pictures" in {
        issue["code"] for issue in report["issues"]
    }


def test_ppt_god_route_rejects_flattened_page_without_native_provenance(tmp_path):
    pptx = tmp_path / "flattened-page.pptx"
    build_single_slide_fixture(pptx, IMAGE_SLIDE)
    report = validate_routes(pptx, {
        "slides": [{
            "slide": 1,
            "mode": "image",
            "production_route": "ppt-god-full-image",
            "overlay_policy": "none",
        }]
    })
    assert report["status"] == "fail"
    assert "ppt_god_generation_provenance_missing" in {
        issue["code"] for issue in report["issues"]
    }


def test_ppt_god_route_accepts_native_generation_provenance(tmp_path):
    pptx = tmp_path / "ppt-god-native.pptx"
    generated = tmp_path / "generated-slide.png"
    image_bytes = b"ppt-god native generated full slide"
    generated.write_bytes(image_bytes)
    image_hash = hashlib.sha256(image_bytes).hexdigest()
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", IMAGE_WITH_EMBEDDED_ASSET)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", IMAGE_ASSET_RELS)
        archive.writestr("ppt/media/full-slide.png", image_bytes)

    report = validate_routes(pptx, {
        "slides": [{
            "slide": 1,
            "mode": "image",
            "production_route": "ppt-god-full-image",
            "overlay_policy": "none",
            "generation_provenance": {
                "producer": "ppt-god",
                "method": "native-generate-slides",
                "project_id": "project-123",
                "page_num": 1,
                "asset_path": str(generated),
                "sha256": image_hash,
            },
        }]
    })
    assert report["status"] == "pass", json.dumps(report, ensure_ascii=False)


def test_reference_fusion_rejects_flattened_page_without_sources(tmp_path):
    pptx = tmp_path / "fake-reference-fusion.pptx"
    build_single_slide_fixture(pptx, IMAGE_SLIDE)
    report = validate_routes(pptx, {
        "slides": [{
            "slide": 1,
            "mode": "image",
            "production_route": "reference-fusion",
            "overlay_policy": "none",
        }]
    })
    codes = {issue["code"] for issue in report["issues"]}
    assert report["status"] == "fail"
    assert "reference_fusion_assets_missing" in codes
    assert "reference_fusion_generation_provenance_missing" in codes


def test_reference_fusion_accepts_verified_sources_and_output(tmp_path):
    pptx = tmp_path / "verified-reference-fusion.pptx"
    generated = tmp_path / "fused-slide.png"
    reference = tmp_path / "reference-photo.jpg"
    output_bytes = b"professionally generated reference fusion slide"
    reference_bytes = b"approved reference photograph"
    generated.write_bytes(output_bytes)
    reference.write_bytes(reference_bytes)
    output_hash = hashlib.sha256(output_bytes).hexdigest()
    reference_hash = hashlib.sha256(reference_bytes).hexdigest()
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", IMAGE_WITH_EMBEDDED_ASSET)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", IMAGE_ASSET_RELS)
        archive.writestr("ppt/media/full-slide.png", output_bytes)

    report = validate_routes(pptx, {
        "slides": [{
            "slide": 1,
            "mode": "image",
            "production_route": "reference-fusion",
            "overlay_policy": "none",
            "reference_assets": [{
                "id": "research-photo",
                "role": "subject-reference",
                "path": str(reference),
                "sha256": reference_hash,
            }],
            "generation_provenance": {
                "producer": "imagegen",
                "method": "reference-edit",
                "asset_path": str(generated),
                "sha256": output_hash,
            },
        }]
    })
    assert report["status"] == "pass", json.dumps(report, ensure_ascii=False)


def test_precision_overlay_requires_declared_exact_asset_count(tmp_path):
    pptx = tmp_path / "precision-overlay.pptx"
    build_single_slide_fixture(pptx, IMAGE_WITH_LOGO)

    report = validate_routes(pptx, {
        "slides": [{
            "slide": 1,
            "mode": "image",
            "overlay_policy": "precision-assets",
            "overlay_assets": [
                {"role": "logo", "path": "brand-logo.png"},
                {"role": "qr-code", "path": "qr.png"},
            ],
        }]
    })

    assert report["status"] == "fail"
    assert "precision_overlay_picture_count_mismatch" in {
        issue["code"] for issue in report["issues"]
    }


def test_focusmedia_specialist_asset_must_be_embedded_byte_for_byte(tmp_path):
    pptx = tmp_path / "focusmedia-editable.pptx"
    specialist = b"exact specialist media visual"
    specialist_hash = hashlib.sha256(specialist).hexdigest()
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", EDITABLE_WITH_SPECIALIST_IMAGE)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", SPECIALIST_RELS)
        archive.writestr("ppt/media/specialist.png", specialist)

    route = {
        "slides": [{
            "slide": 1,
            "mode": "editable",
            "production_route": "native-editable",
            "specialist_route": "focusmedia-image-gen",
            "specialist_asset_scope": "media-visual",
            "specialist_asset_sha256": specialist_hash,
            "requires": ["text"],
        }]
    }
    assert validate_routes(pptx, route)["status"] == "pass"

    route["slides"][0]["specialist_asset_sha256"] = "0" * 64
    report = validate_routes(pptx, route)
    assert report["status"] == "fail"
    assert "focusmedia_specialist_asset_not_embedded_exactly" in {
        issue["code"] for issue in report["issues"]
    }


def test_editable_route_accepts_exact_client_asset(tmp_path):
    pptx = tmp_path / "editable-with-product.pptx"
    product = b"exact approved product image"
    product_path = tmp_path / "approved-product.png"
    product_path.write_bytes(product)
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", EDITABLE_WITH_SPECIALIST_IMAGE)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", SPECIALIST_RELS)
        archive.writestr("ppt/media/specialist.png", product)

    report = validate_routes(pptx, {"slides": [{
        "slide": 1,
        "mode": "editable",
        "production_route": "native-editable",
        "requires": ["text"],
        "exact_assets": [{
            "id": "approved-product",
            "role": "product",
            "path": str(product_path),
            "sha256": hashlib.sha256(product).hexdigest(),
        }],
    }]})
    assert report["status"] == "pass", json.dumps(report, ensure_ascii=False)


def test_editable_route_rejects_substituted_exact_client_asset(tmp_path):
    pptx = tmp_path / "editable-with-substitute.pptx"
    approved = b"approved client storyboard"
    substitute = b"similar but fabricated storyboard"
    approved_path = tmp_path / "approved-storyboard.png"
    approved_path.write_bytes(approved)
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", EDITABLE_WITH_SPECIALIST_IMAGE)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", SPECIALIST_RELS)
        archive.writestr("ppt/media/specialist.png", substitute)

    report = validate_routes(pptx, {"slides": [{
        "slide": 1,
        "mode": "editable",
        "production_route": "native-editable",
        "requires": ["text"],
        "exact_assets": [{
            "id": "approved-storyboard",
            "role": "storyboard",
            "path": str(approved_path),
            "sha256": hashlib.sha256(approved).hexdigest(),
        }],
    }]})
    assert report["status"] == "fail"
    assert "exact_asset_not_embedded_exactly" in {
        issue["code"] for issue in report["issues"]
    }
