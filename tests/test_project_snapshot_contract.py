from templates.project_snapshot_contract import (
    formal_export_blockers,
    validate_content_gate,
    validate_family_gate,
    validate_snapshot_base,
)
from templates.verify_workflow_ready import validate_workflow_ready


def valid_snapshot():
    approved = {
        "status": "approved",
        "approved_revision": 7,
        "approved_at": "2026-08-28T10:00:00+08:00",
        "invalidated_scopes": [],
    }
    return {
        "project": {
            "id": "project-001",
            "title": "客户提案",
            "content_plan_confirmed": True,
        },
        "workflow": {
            "project_id": "project-001",
            "workflow_version": "1.0",
            "revision": 7,
            "enabled": True,
            "gates": {
                "content_order": dict(approved),
                "visual_evidence_route": dict(approved),
                "family_prototypes": dict(approved),
                "final_review": {
                    "status": "pending",
                    "approved_revision": None,
                    "approved_at": None,
                    "invalidated_scopes": [],
                },
            },
            "families": {
                "cover": {
                    "label": "封面",
                    "status": "approved",
                    "representative_slide_id": "slide-1",
                    "approved_production_types": ["image_integrated"],
                    "approved_revision": 7,
                    "approved_at": "2026-08-28T10:00:00+08:00",
                }
            },
            "assets": [{
                "id": "official-photo",
                "slide_id": "slide-1",
                "role": "client-evidence",
                "process_mode": "blend",
                "fidelity": "reference",
                "review_status": "confirmed",
                "user_locked": False,
                "file_path": "/tmp/official-photo.jpg",
                "exists": True,
            }],
            "issues": [],
            "blockers": [],
        },
        "slides": [{
            "id": "slide-1",
            "page_num": 1,
            "type": "cover",
            "content_json": {"title": "增长机会", "claim": "场景触达推动增长"},
            "image_path": "/tmp/page-1.png",
            "layout_spec": None,
            "production_type": "image_integrated",
            "visual_role": "evidence",
            "evidence_state": {
                "status": "confirmed",
                "selected_asset_id": "official-photo",
                "user_decision": "confirmed",
                "candidates": [{"asset_id": "official-photo"}],
                "search_rounds": [{"scope": "project-and-official"}],
            },
            "source_ref": None,
        }],
    }


def test_live_snapshot_positive_gate_1_and_family_contract():
    snapshot = valid_snapshot()
    assert validate_content_gate(snapshot) == []
    family_report = validate_family_gate(snapshot)
    assert family_report["status"] == "pass", family_report


def test_gate_1_can_pass_before_visual_role_and_route_are_chosen():
    snapshot = valid_snapshot()
    snapshot["slides"][0]["production_type"] = None
    snapshot["slides"][0]["visual_role"] = None
    snapshot["slides"][0]["evidence_state"] = None

    assert validate_content_gate(snapshot) == []
    assert any(
        "production_type" in item
        for item in validate_snapshot_base(snapshot)
    )


def test_user_locked_original_must_remain_selected(tmp_path):
    snapshot = valid_snapshot()
    original = tmp_path / "approved-product.png"
    original.write_bytes(b"approved original product")
    snapshot["workflow"]["assets"] = [{
        "id": "approved-product",
        "slide_id": "slide-1",
        "role": "product",
        "process_mode": "blend",
        "fidelity": "exact",
        "user_locked": True,
        "file_path": str(original),
        "exists": True,
    }]
    snapshot["slides"][0]["evidence_state"]["selected_asset_id"] = "different-asset"
    errors = validate_snapshot_base(snapshot)
    assert any("user-locked page asset" in item for item in errors)
    assert any("must reference workflow.assets" in item for item in errors)


def test_confirmed_generated_evidence_can_be_locked_with_disclosure(tmp_path):
    snapshot = valid_snapshot()
    generated = tmp_path / "generated.png"
    generated.write_bytes(b"generated evidence")
    snapshot["workflow"]["assets"] = [{
        "id": "generated-evidence",
        "slide_id": "slide-1",
        "role": "visual_asset",
        "process_mode": "blend",
        "fidelity": "generated",
        "user_locked": True,
        "file_path": str(generated),
        "exists": True,
    }]
    snapshot["slides"][0]["evidence_state"] = {
        "status": "confirmed",
        "selected_asset_id": "generated-evidence",
        "needs_disclosure": True,
        "disclosure_confirmed": True,
        "candidates": [{"asset_id": "generated-evidence"}],
        "search_rounds": [{"scope": "targeted-generation"}],
    }
    assert validate_snapshot_base(snapshot) == []


def test_evidence_gap_requires_two_rounds_and_no_filler():
    snapshot = valid_snapshot()
    state = snapshot["slides"][0]["evidence_state"]
    state.update({
        "status": "gap",
        "selected_asset_id": "",
        "search_rounds": [{"scope": "project"}],
        "gap": "没有权威原图",
    })
    errors = validate_snapshot_base(snapshot)
    assert any("exactly 2 search rounds" in item for item in errors)
    state["search_rounds"].append({"scope": "targeted-search"})
    assert not any("evidence gap" in item for item in validate_snapshot_base(snapshot))


def test_family_needs_approved_construction_type_for_hybrid():
    snapshot = valid_snapshot()
    snapshot["slides"][0]["production_type"] = "hybrid"
    report = validate_family_gate(snapshot)
    assert report["status"] == "fail"
    assert any("construction samples" in item for item in report["issues"])


def test_live_workflow_slide_summary_owns_family_mapping():
    snapshot = valid_snapshot()
    snapshot["slides"][0]["type"] = "case"
    snapshot["workflow"]["slides"] = [{
        "id": "slide-1",
        "page_num": 1,
        "family": "content",
    }]
    family = snapshot["workflow"]["families"].pop("cover")
    snapshot["workflow"]["families"]["content"] = family

    assert validate_family_gate(snapshot)["status"] == "pass"


def test_formal_export_requires_gate_preflight_and_verified_issue():
    snapshot = valid_snapshot()
    snapshot["workflow"]["issues"] = [{
        "id": "issue-1",
        "original_text": "视频未保留",
        "status": "resolved_pending_verification",
        "severity": "blocking",
        "page_num": 1,
    }]
    blockers = formal_export_blockers(snapshot)
    assert any("final_review" in item for item in blockers)
    assert any("blocking issue issue-1" in item for item in blockers)
    assert any("preflight response" in item for item in blockers)


def test_closed_issue_requires_passed_verification_result():
    snapshot = valid_snapshot()
    snapshot["workflow"]["issues"] = [{
        "id": "issue-1",
        "original_text": "第 1 页比例变形",
        "status": "closed",
        "severity": "blocking",
        "page_num": 1,
        "correction_version": 7,
        "verification_result": {"passed": False},
    }]
    errors = validate_snapshot_base(snapshot)
    assert any("passed verification_result" in item for item in errors)


def test_formal_workflow_ready_positive_and_stale_preflight_negative():
    snapshot = valid_snapshot()
    snapshot["workflow"]["gates"]["final_review"] = {
        "status": "approved",
        "approved_revision": 7,
        "approved_at": "2026-08-28T11:00:00+08:00",
        "invalidated_scopes": [],
    }
    preflight = {
        "ok": True,
        "workflow_revision": 7,
        "slide_count": 1,
        "ready_count": 1,
        "blockers": [],
        "warnings": [],
    }
    assert validate_workflow_ready(snapshot, preflight)["status"] == "pass"
    preflight["workflow_revision"] = 6
    report = validate_workflow_ready(snapshot, preflight)
    assert report["status"] == "fail"
    assert any("stale" in item for item in report["blockers"])
