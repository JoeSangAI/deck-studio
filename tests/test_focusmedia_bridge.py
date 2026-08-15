import importlib.util
import hashlib
import json
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).parents[1] / "scripts" / "focusmedia_bridge.py"
)
SPEC = importlib.util.spec_from_file_location("focusmedia_bridge", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


def make_skill_root(tmp_path: Path, kind: str) -> Path:
    root = tmp_path / kind
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    entry = scripts / (
        "fm-kb" if kind == "knowledge" else "select_media_references.py"
    )
    entry.write_text("# fixture\n", encoding="utf-8")
    if kind == "image":
        (scripts / "fetch_reference_images.py").write_text(
            "# fixture\n",
            encoding="utf-8",
        )
    return root


def test_query_returns_empty_without_searching_originals(monkeypatch, tmp_path):
    root = make_skill_root(tmp_path, "knowledge")
    monkeypatch.setattr(MODULE, "_find_root", lambda kind: root)
    calls = []

    def fake_json(command, **kwargs):
        calls.append(command)
        return {"local_results": []}

    monkeypatch.setattr(MODULE, "_json_output", fake_json)

    result = MODULE.query_knowledge("测试问题")

    assert result["status"] == "empty"
    assert result["mode"] == "knowledge"
    assert result["candidate_only"] is False
    assert result["fallback_used"] is False
    assert result["evidence"] == []
    assert len(calls) == 1
    assert "--research" not in calls[0]
    assert calls[0][calls[0].index("--mode") + 1] == "knowledge"


def test_empty_knowledge_query_is_a_normal_cli_result(monkeypatch):
    monkeypatch.setattr(
        MODULE,
        "query_knowledge",
        lambda question, timeout: {
            "status": "empty",
            "query": question,
            "mode": "knowledge",
            "candidate_only": False,
            "fallback_used": False,
            "evidence": [],
        },
    )

    assert MODULE.main(["query", "未覆盖的问题"]) == 0


def test_query_keeps_formal_results_without_fallback(monkeypatch, tmp_path):
    root = make_skill_root(tmp_path, "knowledge")
    monkeypatch.setattr(MODULE, "_find_root", lambda kind: root)
    calls = []

    def fake_json(command, **kwargs):
        calls.append(command)
        return {
            "local_results": [{
                "source_id": "src_formal",
                "locator": "knowledge/formal.md#topic",
            }]
        }

    monkeypatch.setattr(MODULE, "_json_output", fake_json)
    result = MODULE.query_knowledge("正式知识")

    assert result["mode"] == "knowledge"
    assert result["candidate_only"] is False
    assert result["fallback_used"] is False
    assert result["evidence"][0]["source_id"] == "src_formal"
    assert len(calls) == 1


def test_formal_knowledge_entity_gets_a_traceable_source_id(
    monkeypatch,
    tmp_path,
):
    root = make_skill_root(tmp_path, "knowledge")
    monkeypatch.setattr(MODULE, "_find_root", lambda kind: root)
    monkeypatch.setattr(
        MODULE,
        "_json_output",
        lambda *args, **kwargs: {
            "local_results": [{
                "entity_id": "kb_123",
                "entity_type": "knowledge",
                "locator": "知识/公司/公司与品牌.md",
                "excerpt": "x" * 1200,
            }]
        },
    )

    result = MODULE.query_knowledge("正式知识")

    assert result["evidence"][0]["source_id"] == "kb_123"
    assert result["evidence"][0]["fragment_id"] == "kb_123"
    assert len(result["evidence"][0]["excerpt"]) == 800


def test_source_search_requires_explicit_route(monkeypatch, tmp_path):
    root = make_skill_root(tmp_path, "knowledge")
    monkeypatch.setattr(MODULE, "_find_root", lambda kind: root)
    calls = []

    def fake_json(command, **kwargs):
        calls.append(command)
        return {
            "local_results": [{
                "entity_id": "frag_123",
                "source_id": "src_123",
                "locator": "src_123#slide=4",
                "path": "原件/demo.pptx",
                "kind": "slide",
                "position": 4,
            }]
        }

    monkeypatch.setattr(MODULE, "_json_output", fake_json)

    result = MODULE.query_source("客户投放效果原页")

    assert result["status"] == "ok"
    assert result["mode"] == "source"
    assert result["candidate_only"] is True
    assert result["evidence"][0]["fragment_id"] == "frag_123"
    assert len(calls) == 1
    assert "--research" in calls[0]
    assert calls[0][calls[0].index("--mode") + 1] == "source"


def test_resolve_preserves_canonical_source_fields(monkeypatch, tmp_path):
    root = make_skill_root(tmp_path, "knowledge")
    monkeypatch.setattr(MODULE, "_find_root", lambda kind: root)
    monkeypatch.setattr(
        MODULE,
        "_json_output",
        lambda *args, **kwargs: {
            "id": "frag_123",
            "source_id": "src_123",
            "locator": "src_123#slide=4",
            "path": "原件/demo.pptx",
            "absolute_path": "/data/原件/demo.pptx",
            "kind": "slide",
            "position": 4,
        },
    )

    result = MODULE.resolve_fragment("frag_123")

    assert result["status"] == "ok"
    assert result["query"] == "frag_123"
    assert result["mode"] == "source"
    assert result["evidence"][0]["fragment_id"] == "frag_123"
    assert result["evidence"][0]["absolute_path"] == "/data/原件/demo.pptx"


def test_reference_selection_returns_absolute_paths(monkeypatch, tmp_path):
    root = make_skill_root(tmp_path, "image")
    cache = tmp_path / "cache"
    cache.mkdir()
    cached = cache / "lcd.jpg"
    cached.write_bytes(b"verified reference")
    checksum = hashlib.sha256(cached.read_bytes()).hexdigest()
    monkeypatch.setattr(MODULE, "_find_root", lambda kind: root)
    monkeypatch.setattr(
        MODULE,
        "_json_output",
        lambda *args, **kwargs: [{
            "id": "fm-lcd-001",
            "path": "assets/media-library/lcd.jpg",
            "media_type": "LCD",
            "grade": "A",
            "size": "7008x3944",
            "sha256": checksum,
        }],
    )

    result = MODULE.select_references(
        media="LCD",
        scene="elevator-hall",
        angle="front",
        shot_size="mid",
        people="nopeople",
        max_grade="A",
        limit=2,
        download_dir=cache,
    )

    assert result["status"] == "ok"
    assert result["route"] == "focusmedia-image-gen"
    assert result["candidates"][0]["absolute_path"] == str(
        cached.resolve()
    )
    assert result["candidates"][0]["reference_contract"] == {
        "id": "fm-lcd-001",
        "path": str(cached.resolve()),
        "sha256": checksum,
        "role": "environment-geometry",
        "media_type": "lcd",
    }
    assert result["candidates"][0]["edit_transport"] == {
        "preserve_original": True,
        "recommended_max_edge": 2048,
        "reason": "bound synchronous edit upload bytes",
    }


def test_standard_selection_returns_only_the_approved_32_inch_smart_screen(
    monkeypatch,
    tmp_path,
):
    root = make_skill_root(tmp_path, "image")
    standard_dir = root / "assets/framed-demo-standards"
    standard_dir.mkdir(parents=True)
    standard = standard_dir / "smart-32-standard.png"
    standard.write_bytes(b"approved 32 inch smart screen")
    (standard_dir / "manifest.json").write_text(
        json.dumps({
            "schema_version": 1,
            "assets": [{"file": standard.name}],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(MODULE, "_find_root", lambda kind: root)

    result = MODULE.select_standard("smart-screen")

    assert result["hardware_standard"] == "smart-32"
    assert result["reference_contract"] == {
        "id": "fm-standard-smart-32",
        "path": str(standard.resolve()),
        "sha256": hashlib.sha256(standard.read_bytes()).hexdigest(),
        "role": "verified-standard-frame",
        "media_type": "smart-screen",
        "hardware_standard": "smart-32",
    }
    with pytest.raises(MODULE.BridgeError, match="not yet verified"):
        MODULE.select_standard("smart-19")
    with pytest.raises(MODULE.BridgeError, match="not yet verified"):
        MODULE.select_standard("smart-25")


def test_doctor_surfaces_the_first_canonical_knowledge_failure(
    monkeypatch,
    tmp_path,
):
    knowledge_root = make_skill_root(tmp_path, "knowledge")
    image_root = make_skill_root(tmp_path, "image")
    image_assets = image_root / "assets/framed-demo-standards"
    image_assets.mkdir(parents=True)
    for filename in (
        "lcd-32-standard.png",
        "smart-32-standard.png",
        "poster-frame-standard.png",
    ):
        (image_assets / filename).write_bytes(b"standard")
    (image_assets / "manifest.json").write_text("{}", encoding="utf-8")
    (image_root / "references").mkdir()
    (image_root / "references/remote-manifest.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (image_root / "scripts/comet_image.py").write_text(
        "# fixture\n",
        encoding="utf-8",
    )
    (image_root / "SKILL.md").write_text("# fixture\n", encoding="utf-8")

    monkeypatch.setattr(
        MODULE,
        "_find_root",
        lambda kind: knowledge_root if kind == "knowledge" else image_root,
    )
    monkeypatch.setattr(
        MODULE,
        "_json_output",
        lambda *args, **kwargs: {
            "overall": "error",
            "checks": [
                {"name": "source_registry", "status": "warning"},
                {"name": "published_knowledge", "status": "error"},
            ],
        },
    )
    monkeypatch.setattr(MODULE, "_run", lambda *args, **kwargs: "healthy model=test")

    result = MODULE.doctor()
    knowledge_check = result["checks"][0]

    assert result["status"] == "fail"
    assert knowledge_check["detail"]["failed_checks"] == ["published_knowledge"]
    assert knowledge_check["detail"]["warning_checks"] == ["source_registry"]
    assert knowledge_check["next"].endswith(
        "fix its first failed check: published_knowledge"
    )
