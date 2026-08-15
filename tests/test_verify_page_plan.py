import hashlib

from templates.verify_page_plan import validate_page_plan


def valid_plan():
    return {
        "status": "approved",
        "approved_by": "Joe",
        "content_version": "v1",
        "approval_scope": "full_deck",
        "slides": [
            {
                "slide": 1,
                "public": {
                    "title": "三个问题指向同一机会",
                    "claim": "三个问题指向同一机会",
                },
                "notes": {
                    "audience_question": "为什么现在需要重新看这个机会？",
                    "purpose": "建立问题",
                    "claim_key": "one-opportunity",
                    "evidence_source": "客户 Brief 第 2 页",
                    "speaker_line": "先看三个问题背后的共同结构。",
                    "transition": "下一页解释共同结构",
                    "excludes": "不在本页展开具体执行方案",
                },
                "mode": "image",
                "production_route": "ppt-god-full-image",
                "overlay_policy": "none",
            },
            {
                "slide": 2,
                "public": {
                    "title": "场景触达决定转化",
                    "claim": "场景触达决定转化",
                },
                "notes": {
                    "audience_question": "共同结构是什么？",
                    "purpose": "解释结构",
                    "claim_key": "scene-conversion",
                    "evidence_source": "会议记录 00:12:30",
                    "speaker_line": "增长需要进入真实场景。",
                    "transition": "下一页给出执行方案",
                    "excludes": "不重复上一页的问题清单",
                },
                "mode": "editable",
                "production_route": "native-editable",
                "overlay_policy": "none",
            },
        ],
    }


def reference_asset(tmp_path, *, media_type="lcd"):
    path = tmp_path / "reference.jpg"
    path.write_bytes(b"verified focus media reference")
    return {
        "id": "fm-lcd-reference-001",
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "role": "environment-geometry",
        "media_type": media_type,
    }


def standard_reference_asset(tmp_path, *, media_type="lcd"):
    standards = {
        "lcd": ("lcd-32", "lcd-32-standard.png"),
        "smart-screen": ("smart-32", "smart-32-standard.png"),
        "poster-frame": ("poster-frame-standard", "poster-frame-standard.png"),
    }
    hardware_standard, filename = standards[media_type]
    path = tmp_path / filename
    path.write_bytes(f"verified {hardware_standard}".encode())
    return {
        "id": f"fm-standard-{hardware_standard}",
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "role": "verified-standard-frame",
        "media_type": media_type,
        "hardware_standard": hardware_standard,
    }


def framed_asset(tmp_path, *, media_type="lcd"):
    path = tmp_path / "framed-demo.png"
    path.write_bytes(b"verified framed media demo")
    return {
        "id": "fm-lcd-framed-demo-001",
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "media_type": media_type,
        "hardware_standard": "lcd-32",
    }


def attach_focusmedia(slide, tmp_path):
    slide["production_route"] = "reference-fusion"
    slide["specialist_route"] = "focusmedia-image-gen"
    slide["specialist_asset_scope"] = "full-slide"
    slide["reference_assets"] = [
        reference_asset(tmp_path),
        standard_reference_asset(tmp_path),
    ]
    slide["framed_asset"] = framed_asset(tmp_path)
    slide["media_contract"] = {
        "medium": "LCD",
        "hardware_standard": "lcd-32",
        "scene": "elevator-hall",
        "creative_source": "approved-client-creative.png",
        "output_type": "environment-image",
        "integration_mode": "environment-reference-fusion",
        "must_preserve": ["LCD housing", "elevator doors", "call button"],
        "acceptance_checks": ["correct media type", "exact creative", "plausible scale"],
    }


def test_valid_page_plan_and_matching_route():
    plan = valid_plan()
    route = {
        "slides": [
            {
                "slide": 1,
                "mode": "image",
                "production_route": "ppt-god-full-image",
                "overlay_policy": "none",
            },
            {
                "slide": 2,
                "mode": "editable",
                "production_route": "native-editable",
                "overlay_policy": "none",
            },
        ]
    }
    assert validate_page_plan(plan, route) == []


def test_unapproved_or_incomplete_plan_is_rejected():
    plan = valid_plan()
    plan["status"] = "draft"
    plan["slides"][1]["notes"]["speaker_line"] = ""
    errors = validate_page_plan(plan)
    assert "page plan status must be approved" in errors
    assert "slide 2 notes field speaker_line must be non-empty" in errors


def test_route_mismatch_is_rejected():
    plan = valid_plan()
    route = {
        "slides": [
            {
                "slide": 1,
                "mode": "editable",
                "production_route": "native-editable",
                "overlay_policy": "none",
            },
            {
                "slide": 2,
                "mode": "editable",
                "production_route": "native-editable",
                "overlay_policy": "none",
            },
        ]
    }
    assert "route manifest slide order and production routes must match page plan" in (
        validate_page_plan(plan, route)
    )


def test_duplicate_claims_are_rejected():
    plan = valid_plan()
    plan["slides"][1]["notes"]["claim_key"] = "one-opportunity"
    plan["slides"][1]["public"]["claim"] = "三个问题，指向同一机会"
    errors = validate_page_plan(plan)
    assert "slide 2 claim_key duplicates slide 1" in errors
    assert "slide 2 claim duplicates slide 1" in errors


def test_focusmedia_slide_requires_real_reference_assets(tmp_path):
    plan = valid_plan()
    slide = plan["slides"][0]
    attach_focusmedia(slide, tmp_path)
    assert validate_page_plan(plan) == []
    slide["reference_assets"][0]["sha256"] = "0" * 64
    assert "slide 1 reference_assets[1] sha256 does not match file" in validate_page_plan(plan)


def test_focusmedia_slide_rejects_an_empty_reference_list(tmp_path):
    plan = valid_plan()
    slide = plan["slides"][0]
    attach_focusmedia(slide, tmp_path)
    slide["reference_assets"] = []

    assert "slide 1 reference_assets must be a non-empty array" in validate_page_plan(plan)


def test_focusmedia_reference_type_must_match_media_contract(tmp_path):
    plan = valid_plan()
    slide = plan["slides"][0]
    attach_focusmedia(slide, tmp_path)
    for asset in slide["reference_assets"]:
        asset["media_type"] = "smart-screen"

    assert (
        "slide 1 reference_assets do not include media type lcd required by media_contract"
        in validate_page_plan(plan)
    )


def test_focusmedia_knowledge_and_media_routes_can_coexist(tmp_path):
    plan = valid_plan()
    slide = plan["slides"][0]
    slide["knowledge_route"] = "focusmedia-knowledge"
    slide["knowledge_contract"] = {
        "query": "分众电梯媒体为什么能覆盖城市主流人群？",
        "mode": "research",
        "status": "ok",
        "candidate_only": True,
        "evidence": [{
            "fragment_id": "frag_123",
            "source_id": "src_123",
            "locator": "src_123#slide=4",
            "path": "原件/资源-媒体-电梯媒体.pptx",
            "kind": "slide",
            "position": 4,
        }],
    }
    attach_focusmedia(slide, tmp_path)
    route = {
        "slides": [
            {
                "slide": 1,
                "mode": "image",
                "production_route": "reference-fusion",
                "overlay_policy": "none",
                "knowledge_route": "focusmedia-knowledge",
                "specialist_route": "focusmedia-image-gen",
                "specialist_asset_scope": "full-slide",
            },
            {
                "slide": 2,
                "mode": "editable",
                "production_route": "native-editable",
                "overlay_policy": "none",
            },
        ]
    }

    assert validate_page_plan(plan, route) == []


def test_research_knowledge_requires_candidate_identity_and_sources():
    plan = valid_plan()
    slide = plan["slides"][0]
    slide["knowledge_route"] = "focusmedia-knowledge"
    slide["knowledge_contract"] = {
        "query": "候选证据",
        "mode": "research",
        "status": "ok",
        "candidate_only": False,
        "evidence": [{"path": "原件/demo.pptx", "kind": "slide", "position": 2}],
    }

    errors = validate_page_plan(plan)

    assert (
        "slide 1 knowledge_contract research mode must set candidate_only to true"
        in errors
    )
    assert (
        "slide 1 knowledge_contract evidence[1] field source_id must be non-empty"
        in errors
    )
    assert (
        "slide 1 knowledge_contract evidence[1] field locator must be non-empty"
        in errors
    )
    assert (
        "slide 1 knowledge_contract evidence[1] field fragment_id or entity_id must be non-empty"
        in errors
    )


def test_source_reuse_requires_resolved_absolute_path_and_page_kind():
    plan = valid_plan()
    slide = plan["slides"][0]
    slide["knowledge_route"] = "focusmedia-knowledge"
    slide["knowledge_contract"] = {
        "query": "复用原页",
        "mode": "source",
        "status": "ok",
        "evidence": [{
            "fragment_id": "frag_123",
            "source_id": "src_123",
            "locator": "src_123#slide=4",
            "path": "原件/demo.pptx",
            "kind": "unknown",
            "position": 4,
        }],
    }

    errors = validate_page_plan(plan)

    assert (
        "slide 1 knowledge_contract evidence[1] field absolute_path must be non-empty"
        in errors
    )
    assert (
        "slide 1 knowledge_contract evidence[1] kind must be slide or page"
        in errors
    )


def test_focusmedia_image_page_cannot_omit_specialist_route():
    plan = valid_plan()
    plan["slides"][0]["public"]["claim"] = "电梯电视在真实候梯场景中形成高频触达"

    assert (
        "slide 1 Focus Media visual requires specialist_route focusmedia-image-gen"
        in validate_page_plan(plan)
    )


def test_editable_page_with_focusmedia_visual_brief_requires_specialist():
    plan = valid_plan()
    plan["slides"][1]["visual_brief"] = "使用真实楼宇 LCD 环境图片"

    assert (
        "slide 2 Focus Media visual requires specialist_route focusmedia-image-gen"
        in validate_page_plan(plan)
    )


def test_route_manifest_cannot_drop_specialist_routes(tmp_path):
    plan = valid_plan()
    slide = plan["slides"][0]
    attach_focusmedia(slide, tmp_path)
    route = {
        "slides": [
            {
                "slide": 1,
                "mode": "image",
                "production_route": "reference-fusion",
                "overlay_policy": "none",
            },
            {
                "slide": 2,
                "mode": "editable",
                "production_route": "native-editable",
                "overlay_policy": "none",
            },
        ]
    }

    assert "route manifest slide order and production routes must match page plan" in (
        validate_page_plan(plan, route)
    )


def test_internal_authoring_language_stays_in_notes_and_never_public():
    plan = valid_plan()
    slide = plan["slides"][0]
    slide["notes"]["speaker_line"] = "正式方案统一使用年报口径。"
    slide["notes"]["evidence_source"] = "新旧资料口径冲突，以年报核定事实为准。"

    assert validate_page_plan(plan) == []

    slide["public"]["claim"] = "正式方案统一采用 2026 年年报的境外自营媒体口径"
    assert "slide 1 public contains internal authoring language" in (
        validate_page_plan(plan)
    )


def test_every_page_requires_an_explicit_production_route_and_overlay_policy():
    plan = valid_plan()
    del plan["slides"][0]["production_route"]
    del plan["slides"][1]["overlay_policy"]

    errors = validate_page_plan(plan)

    assert any("slide 1 production_route must be one of" in item for item in errors)
    assert any("slide 2 overlay_policy must be one of" in item for item in errors)


def test_source_preserve_binds_the_canonical_file_hash(tmp_path):
    plan = valid_plan()
    source = tmp_path / "canonical.pptx"
    source.write_bytes(b"canonical source")
    slide = plan["slides"][0]
    slide["production_route"] = "source-preserve"
    slide["source_lock"] = {
        "canonical_path": str(source),
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_kind": "slide",
        "position": 4,
    }

    assert validate_page_plan(plan) == []

    source.write_bytes(b"changed source")
    assert "slide 1 source_lock sha256 does not match file" in validate_page_plan(plan)


def test_focusmedia_visual_cannot_use_unreferenced_full_image_route():
    plan = valid_plan()
    slide = plan["slides"][0]
    slide["public"]["claim"] = "真实电梯电视形成高频触达"

    errors = validate_page_plan(plan)

    assert any("cannot use ppt-god-full-image" in item for item in errors)


def test_precision_overlay_cannot_declare_a_whole_media_device():
    plan = valid_plan()
    slide = plan["slides"][0]
    slide["overlay_policy"] = "precision-assets"
    slide["overlay_assets"] = [{"role": "media-device", "path": "screen.png"}]

    assert any(
        "overlay_assets[1] role must be one of" in item
        for item in validate_page_plan(plan)
    )


def test_screen_creative_is_not_a_slide_overlay_role():
    plan = valid_plan()
    slide = plan["slides"][0]
    slide["overlay_policy"] = "precision-assets"
    slide["overlay_assets"] = [{"role": "screen-creative", "path": "screen.png"}]

    assert any(
        "overlay_assets[1] role must be one of" in item
        for item in validate_page_plan(plan)
    )


def test_focusmedia_environment_route_rejects_a_framed_demo_mode(tmp_path):
    plan = valid_plan()
    slide = plan["slides"][0]
    attach_focusmedia(slide, tmp_path)
    slide["media_contract"]["integration_mode"] = "framed-standard-composite"

    assert any(
        "output_type environment-image requires integration_mode "
        "environment-reference-fusion" in item
        for item in validate_page_plan(plan)
    )


def test_focusmedia_media_visual_uses_native_editable_page_route(tmp_path):
    plan = valid_plan()
    slide = plan["slides"][1]
    attach_focusmedia(slide, tmp_path)
    slide["mode"] = "editable"
    slide["production_route"] = "native-editable"
    slide["specialist_asset_scope"] = "media-visual"

    assert validate_page_plan(plan) == []


def test_smart_screen_route_only_accepts_the_32_inch_standard(tmp_path):
    plan = valid_plan()
    slide = plan["slides"][0]
    attach_focusmedia(slide, tmp_path)
    slide["media_contract"]["medium"] = "smart-screen"
    slide["media_contract"]["hardware_standard"] = "smart-19"
    slide["reference_assets"][1] = standard_reference_asset(
        tmp_path,
        media_type="smart-screen",
    )
    slide["reference_assets"][0]["media_type"] = "smart-screen"
    slide["framed_asset"]["media_type"] = "smart-screen"
    slide["framed_asset"]["hardware_standard"] = "smart-19"

    assert any(
        "medium smart-screen requires hardware_standard smart-32" in item
        for item in validate_page_plan(plan)
    )


def test_logo_overlay_is_bound_to_one_real_asset(tmp_path):
    plan = valid_plan()
    logo = tmp_path / "logo.png"
    logo.write_bytes(b"official logo")
    slide = plan["slides"][0]
    slide["overlay_policy"] = "logo-only"
    slide["allow_logo_overlay"] = True
    slide["overlay_assets"] = [{
        "id": "official-logo",
        "path": str(logo),
        "sha256": hashlib.sha256(logo.read_bytes()).hexdigest(),
        "role": "logo",
    }]

    assert validate_page_plan(plan) == []

    slide["overlay_assets"][0]["sha256"] = "f" * 64
    assert any(
        "overlay_assets[1] sha256 does not match" in item
        for item in validate_page_plan(plan)
    )
