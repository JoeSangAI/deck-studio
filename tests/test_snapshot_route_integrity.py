import hashlib
import zipfile

from templates.verify_route_integrity import validate_routes


PRESENTATION = """<?xml version="1.0" encoding="UTF-8"?>
<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldSz cx="12192000" cy="6858000"/>
</p:presentation>
"""

IMAGE = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld><p:spTree><p:pic><p:blipFill><a:blip r:embed="rId1"/></p:blipFill>
    <p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm></p:spPr>
  </p:pic></p:spTree></p:cSld>
</p:sld>
"""

HYBRID = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:cSld><p:spTree><p:pic><p:blipFill><a:blip r:embed="rId1"/></p:blipFill>
    <p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="12192000" cy="6858000"/></a:xfrm></p:spPr>
  </p:pic><p:sp><p:txBody><a:p><a:r><a:t>可编辑关键标题</a:t></a:r></a:p></p:txBody></p:sp>
  </p:spTree></p:cSld>
</p:sld>
"""

NATIVE = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>原生可编辑结构与正文</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>
</p:sld>
"""

RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/{name}"/>
</Relationships>
"""


def snapshot(slides):
    approved = {
        "status": "approved",
        "approved_revision": 4,
        "approved_at": "now",
        "invalidated_scopes": [],
    }
    return {
        "project": {
            "id": "p1",
            "title": "route test",
            "content_plan_confirmed": True,
        },
        "workflow": {
            "project_id": "p1",
            "workflow_version": "1.0",
            "revision": 4,
            "enabled": True,
            "gates": {
                "content_order": dict(approved),
                "visual_evidence_route": dict(approved),
                "family_prototypes": dict(approved),
                "final_review": {"status": "pending", "approved_revision": None, "approved_at": None},
            },
            "families": {
                "content": {
                    "label": "内容",
                    "status": "approved",
                    "representative_slide_id": slides[0]["id"],
                    "approved_production_types": [
                        "image_integrated", "hybrid", "native_editable"
                    ],
                }
            },
            "assets": [],
            "issues": [],
            "blockers": [],
        },
        "slides": slides,
    }


def slide(page, production_type, *, image_path=None):
    item = {
        "id": f"slide-{page}",
        "page_num": page,
        "type": "content",
        "content_json": {"title": f"标题 {page}", "claim": f"主张 {page}"},
        "production_type": production_type,
        "visual_role": "text_led",
        "evidence_state": {"status": "unreviewed", "candidates": [], "search_rounds": []},
        "source_ref": None,
    }
    if image_path:
        item["image_path"] = str(image_path)
    if production_type in {"hybrid", "native_editable"}:
        item["layout_spec"] = {"blocks": [{"kind": "title"}]}
    return item


def test_snapshot_accepts_image_hybrid_and_native_in_one_deck(tmp_path):
    image_bytes = b"full image page"
    hybrid_bytes = b"hybrid background"
    image_path = tmp_path / "image.png"
    hybrid_path = tmp_path / "hybrid.png"
    image_path.write_bytes(image_bytes)
    hybrid_path.write_bytes(hybrid_bytes)
    pptx = tmp_path / "mixed.pptx"
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", IMAGE)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", RELS.format(name="image.png"))
        archive.writestr("ppt/media/image.png", image_bytes)
        archive.writestr("ppt/slides/slide2.xml", HYBRID)
        archive.writestr("ppt/slides/_rels/slide2.xml.rels", RELS.format(name="hybrid.png"))
        archive.writestr("ppt/media/hybrid.png", hybrid_bytes)
        archive.writestr("ppt/slides/slide3.xml", NATIVE)
    report = validate_routes(pptx, snapshot([
        slide(1, "image_integrated", image_path=image_path),
        slide(2, "hybrid", image_path=hybrid_path),
        slide(3, "native_editable"),
    ]))
    assert report["status"] == "pass", report


def test_snapshot_rejects_rasterized_native_page(tmp_path):
    pptx = tmp_path / "rasterized.pptx"
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", IMAGE)
    report = validate_routes(pptx, snapshot([slide(1, "native_editable")]))
    codes = {item["code"] for item in report["issues"]}
    assert report["status"] == "fail"
    assert "native_editable_looks_rasterized" in codes


def test_snapshot_rejects_hybrid_without_layout_spec(tmp_path):
    background = tmp_path / "hybrid.png"
    background.write_bytes(b"hybrid background")
    pptx = tmp_path / "hybrid.pptx"
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", HYBRID)
        archive.writestr("ppt/slides/_rels/slide1.xml.rels", RELS.format(name="hybrid.png"))
        archive.writestr("ppt/media/hybrid.png", background.read_bytes())
    contract = slide(1, "hybrid", image_path=background)
    contract.pop("layout_spec")

    report = validate_routes(pptx, snapshot([contract]))

    assert "layout_spec_required" in {item["code"] for item in report["issues"]}


def test_snapshot_rejects_image_route_without_image_path(tmp_path):
    pptx = tmp_path / "image.pptx"
    with zipfile.ZipFile(pptx, "w") as archive:
        archive.writestr("ppt/presentation.xml", PRESENTATION)
        archive.writestr("ppt/slides/slide1.xml", IMAGE)

    report = validate_routes(pptx, snapshot([slide(1, "image_integrated")]))

    assert "image_path_required" in {item["code"] for item in report["issues"]}
