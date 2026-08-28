#!/usr/bin/env python3
"""Validate the read-only snapshot returned by PPT God's project-snapshot API.

The live product response has top-level ``project``/``workflow``/``slides``.  The
normalizers below also accept the earlier flat draft contract for read-only audits,
but all active Deck Studio CLIs use the live product shape.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.request import urlopen


PRODUCTION_TYPES = {"image_integrated", "hybrid", "native_editable"}
VISUAL_ROLES = {"evidence", "expressive", "text_led"}
GATE_NAMES = (
    "content_order",
    "visual_evidence_route",
    "family_prototypes",
    "final_review",
)
GATE_STATUSES = {"pending", "approved", "invalidated", "rejected"}
EVIDENCE_STATUSES = {"unreviewed", "candidate", "confirmed", "gap", "waived"}
FIDELITY_LEVELS = {"exact", "reference", "generated"}
ISSUE_STATUSES = {"open", "in_progress", "resolved_pending_verification", "closed"}
ISSUE_SEVERITIES = {"blocking", "warning"}
CORE_FAMILIES = {"cover", "section", "quote", "data", "content"}
PRECISION_OVERLAY_ROLES = {"logo", "qr-code", "legal-mark", "screenshot"}


def is_project_snapshot(data: Any) -> bool:
    return (
        isinstance(data, dict)
        and isinstance(data.get("project"), dict)
        and isinstance(data.get("slides"), list)
        and (
            isinstance(data.get("workflow"), dict)
            or isinstance(data.get("gates"), dict)
        )
    )


def load_json_source(source: str | Path) -> dict[str, Any]:
    """Read a snapshot from a local file or an explicit HTTP(S) URL."""
    raw_source = str(source)
    if raw_source.startswith(("http://", "https://")):
        with urlopen(raw_source, timeout=10) as response:  # nosec: explicit trusted input
            payload = response.read().decode("utf-8")
    else:
        payload = Path(raw_source).read_text(encoding="utf-8")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("project snapshot must contain a JSON object")
    return data


def workflow_data(snapshot: dict[str, Any]) -> dict[str, Any]:
    workflow = snapshot.get("workflow")
    if isinstance(workflow, dict):
        return workflow
    return snapshot


def snapshot_slides(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    slides = snapshot.get("slides")
    if not isinstance(slides, list):
        slides = workflow_data(snapshot).get("slides")
    return [item for item in (slides or []) if isinstance(item, dict)]


def snapshot_assets(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    assets = workflow_data(snapshot).get("assets")
    if not isinstance(assets, list):
        assets = snapshot.get("assets")
    return [item for item in (assets or []) if isinstance(item, dict)]


def snapshot_issues(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    issues = workflow_data(snapshot).get("issues")
    if not isinstance(issues, list):
        issues = snapshot.get("issues")
    return [item for item in (issues or []) if isinstance(item, dict)]


def snapshot_families(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    families = workflow_data(snapshot).get("families")
    if families is None:
        families = snapshot.get("families")
    if isinstance(families, dict):
        return {str(key): value for key, value in families.items() if isinstance(value, dict)}
    if isinstance(families, list):
        result: dict[str, dict[str, Any]] = {}
        for item in families:
            if not isinstance(item, dict):
                continue
            key = str(item.get("id") or item.get("key") or "").strip()
            if key:
                result[key] = item
        return result
    return {}


def page_num(slide: dict[str, Any]) -> int:
    value = slide.get("page_num")
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def project_revision(snapshot: dict[str, Any]) -> int:
    workflow = workflow_data(snapshot)
    value = workflow.get("revision")
    if value is None:
        value = (snapshot.get("project") or {}).get("workflow_revision")
    return value if isinstance(value, int) and not isinstance(value, bool) else -1


def gate_status(snapshot: dict[str, Any], name: str) -> str:
    gate = (workflow_data(snapshot).get("gates") or {}).get(name) or {}
    return str(gate.get("status") or "").strip()


def _normal_family(value: Any) -> str:
    raw = str(value or "content").strip().lower()
    if raw in {"cover", "封面"}:
        return "cover"
    if raw in {"section", "chapter", "章节", "章页"}:
        return "section"
    if raw in {"quote", "punchline", "golden_sentence", "金句"}:
        return "quote"
    if raw in {"data", "chart", "数据"}:
        return "data"
    return raw or "content"


def slide_family(slide: dict[str, Any]) -> str:
    return _normal_family(slide.get("family") or slide.get("family_id") or slide.get("type"))


def snapshot_slide_family(snapshot: dict[str, Any], slide: dict[str, Any]) -> str:
    """Resolve the live family from workflow.slides before falling back to type."""
    slide_id = str(slide.get("id") or "")
    for summary in workflow_data(snapshot).get("slides") or []:
        if isinstance(summary, dict) and str(summary.get("id") or "") == slide_id:
            if str(summary.get("family") or "").strip():
                return _normal_family(summary["family"])
    return slide_family(slide)


def slide_content(slide: dict[str, Any]) -> dict[str, Any]:
    for field in ("content_json", "public", "content"):
        value = slide.get(field)
        if isinstance(value, dict):
            return value
    return {}


def _asset_path(asset: dict[str, Any]) -> str:
    return str(asset.get("file_path") or asset.get("path") or "").strip()


def _asset_locked(asset: dict[str, Any]) -> bool:
    return asset.get("user_locked") is True or asset.get("locked_by_user") is True


def _validate_asset(asset: dict[str, Any], prefix: str, errors: list[str]) -> None:
    if not str(asset.get("id") or "").strip():
        errors.append(f"{prefix}.id must be non-empty")
    if not str(asset.get("role") or "").strip():
        errors.append(f"{prefix}.role must be non-empty")
    fidelity = str(asset.get("fidelity") or "").strip()
    if fidelity and fidelity not in FIDELITY_LEVELS:
        errors.append(f"{prefix}.fidelity must be one of {sorted(FIDELITY_LEVELS)}")
    path = _asset_path(asset)
    if not path:
        errors.append(f"{prefix}.file_path must be non-empty")
    elif not Path(path).is_absolute():
        errors.append(f"{prefix}.file_path must be absolute")
    if asset.get("exists") is False:
        errors.append(f"{prefix}.file_path does not exist")
    if _asset_locked(asset):
        if asset.get("replacement_allowed") is True:
            errors.append(f"{prefix} user-locked asset cannot allow replacement")
    source_ref = asset.get("source_ref")
    if source_ref not in (None, {}) and not isinstance(source_ref, dict):
        errors.append(f"{prefix}.source_ref must be an object")


def _validate_evidence(
    slide: dict[str, Any],
    project_assets: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    number = page_num(slide)
    prefix = f"slide {number} evidence_state"
    state = slide.get("evidence_state")
    if not isinstance(state, dict):
        if str(slide.get("visual_role") or "") == "evidence":
            errors.append(f"{prefix} must be an object for evidence pages")
        return
    status = str(state.get("status") or "unreviewed").strip()
    if status not in EVIDENCE_STATUSES:
        errors.append(f"{prefix}.status must be one of {sorted(EVIDENCE_STATUSES)}")
    candidates = state.get("candidates") or []
    rounds = state.get("search_rounds") or []
    if not isinstance(candidates, list) or len(candidates) > 3:
        errors.append(f"{prefix}.candidates must be an array with at most 3 entries")
    if not isinstance(rounds, list) or len(rounds) > 2:
        errors.append(f"{prefix}.search_rounds must be an array with at most 2 entries")
        rounds = []
    selected = str(state.get("selected_asset_id") or "").strip()
    if selected and selected not in project_assets:
        errors.append(f"{prefix}.selected_asset_id must reference workflow.assets")

    slide_id = str(slide.get("id") or "")
    locked_ids = {
        asset_id
        for asset_id, asset in project_assets.items()
        if _asset_locked(asset) and str(asset.get("slide_id") or "") == slide_id
    }
    if locked_ids and selected not in locked_ids:
        errors.append(f"slide {number} has a user-locked page asset; it must remain selected")

    if str(slide.get("visual_role") or "") != "evidence":
        if status == "gap":
            errors.append(f"slide {number} non-evidence page cannot declare a gap")
        return
    if status == "confirmed" and not selected:
        generated_disclosed = (
            state.get("needs_disclosure") is True
            and state.get("disclosure_confirmed") is True
        )
        if not generated_disclosed:
            errors.append(
                f"slide {number} confirmed evidence requires selected_asset_id "
                "or confirmed AI disclosure"
            )
    elif status == "gap":
        if len(rounds) != 2:
            errors.append(f"slide {number} evidence gap requires exactly 2 search rounds")
        if not str(state.get("gap") or state.get("gap_reason") or "").strip():
            errors.append(f"slide {number} evidence gap requires a reason")
        if selected:
            errors.append(f"slide {number} evidence gap cannot select filler evidence")
    elif status == "waived" and not str(state.get("user_decision") or "").strip():
        errors.append(f"slide {number} waived evidence requires an explicit user decision")


def validate_snapshot_base(
    snapshot: dict[str, Any],
    *,
    require_routes: bool = True,
) -> list[str]:
    """Validate the live snapshot; Gate 1 may run before route fields exist."""
    errors: list[str] = []
    if not is_project_snapshot(snapshot):
        return ["input is not a PPT God project-snapshot response"]
    project = snapshot.get("project") or {}
    for field in ("id", "title"):
        if not str(project.get(field) or "").strip():
            errors.append(f"project.{field} must be non-empty")
    workflow = workflow_data(snapshot)
    if workflow.get("enabled") is not True:
        errors.append("workflow.enabled must be true")
    if not str(workflow.get("workflow_version") or "").strip():
        errors.append("workflow.workflow_version must be non-empty")
    revision = project_revision(snapshot)
    if revision < 0:
        errors.append("workflow.revision must be a non-negative integer")

    gates = workflow.get("gates") or {}
    for name in GATE_NAMES:
        gate = gates.get(name)
        prefix = f"workflow.gates.{name}"
        if not isinstance(gate, dict):
            errors.append(f"{prefix} must be an object")
            continue
        status = str(gate.get("status") or "").strip()
        if status not in GATE_STATUSES:
            errors.append(f"{prefix}.status must be one of {sorted(GATE_STATUSES)}")
        approved_revision = gate.get("approved_revision")
        if status == "approved":
            if not isinstance(approved_revision, int) or isinstance(approved_revision, bool):
                errors.append(f"{prefix}.approved_revision must be an integer")
            elif approved_revision > revision:
                errors.append(f"{prefix}.approved_revision cannot exceed workflow.revision")
            if not str(gate.get("approved_at") or "").strip():
                errors.append(f"{prefix}.approved_at is required when approved")

    slides = snapshot_slides(snapshot)
    if not slides:
        errors.append("slides must be a non-empty array")
        return errors
    page_nums = [page_num(slide) for slide in slides]
    if page_nums != list(range(1, len(slides) + 1)):
        errors.append(f"slide page_num values must be consecutive from 1: {page_nums}")
    slide_ids = [str(slide.get("id") or "").strip() for slide in slides]
    if any(not item for item in slide_ids):
        errors.append("every slide.id must be non-empty")
    duplicates = sorted(item for item, count in Counter(slide_ids).items() if item and count > 1)
    if duplicates:
        errors.append(f"duplicate slide ids: {duplicates}")

    assets = snapshot_assets(snapshot)
    asset_ids: list[str] = []
    for index, asset in enumerate(assets, start=1):
        _validate_asset(asset, f"workflow.assets[{index}]", errors)
        asset_ids.append(str(asset.get("id") or "").strip())
    duplicate_assets = sorted(item for item, count in Counter(asset_ids).items() if item and count > 1)
    if duplicate_assets:
        errors.append(f"duplicate asset ids: {duplicate_assets}")
    asset_map = {str(asset.get("id")): asset for asset in assets if asset.get("id")}

    for slide in slides:
        number = page_num(slide)
        production_type = str(slide.get("production_type") or "").strip()
        visual_role = str(slide.get("visual_role") or "").strip()
        if (require_routes or production_type) and production_type not in PRODUCTION_TYPES:
            errors.append(f"slide {number} production_type must be one of {sorted(PRODUCTION_TYPES)}")
        if (require_routes or visual_role) and visual_role not in VISUAL_ROLES:
            errors.append(f"slide {number} visual_role must be one of {sorted(VISUAL_ROLES)}")
        content = slide_content(slide)
        if not content:
            errors.append(f"slide {number} content_json must be a non-empty object")
        source_ref = slide.get("source_ref")
        if source_ref not in (None, {}) and not isinstance(source_ref, dict):
            errors.append(f"slide {number} source_ref must be an object")
        if require_routes or visual_role or isinstance(slide.get("evidence_state"), dict):
            _validate_evidence(slide, asset_map, errors)

    families = snapshot_families(snapshot)
    if not families:
        errors.append("workflow.families must be a non-empty object")
    undefined = sorted({snapshot_slide_family(snapshot, slide) for slide in slides} - set(families))
    if undefined:
        errors.append(f"slides reference undefined families: {undefined}")

    slide_id_set = set(slide_ids)
    for issue in snapshot_issues(snapshot):
        issue_id = str(issue.get("id") or "").strip()
        if not issue_id:
            errors.append("workflow issue id must be non-empty")
        severity = str(issue.get("severity") or "").strip()
        status = str(issue.get("status") or "").strip()
        if severity not in ISSUE_SEVERITIES:
            errors.append(f"issue {issue_id} severity must be one of {sorted(ISSUE_SEVERITIES)}")
        if status not in ISSUE_STATUSES:
            errors.append(f"issue {issue_id} status must be one of {sorted(ISSUE_STATUSES)}")
        if not str(issue.get("original_text") or "").strip():
            errors.append(f"issue {issue_id} original_text must be non-empty")
        linked_slide = str(issue.get("slide_id") or "").strip()
        if linked_slide and linked_slide not in slide_id_set:
            errors.append(f"issue {issue_id} slide_id is unknown")
        if status == "closed":
            verification = issue.get("verification_result")
            if not isinstance(verification, dict) or verification.get("passed") is not True:
                errors.append(f"issue {issue_id} cannot close without passed verification_result")
            if not isinstance(issue.get("correction_version"), int):
                errors.append(f"issue {issue_id} closed issue requires correction_version")
    return errors


def validate_content_gate(snapshot: dict[str, Any], *, require_approved: bool = True) -> list[str]:
    errors = validate_snapshot_base(snapshot, require_routes=False)
    if require_approved and gate_status(snapshot, "content_order") != "approved":
        errors.append("Gate content_order must be approved")
    if (snapshot.get("project") or {}).get("content_plan_confirmed") is False:
        errors.append("project.content_plan_confirmed must be true")
    claims: dict[str, int] = {}
    for slide in snapshot_slides(snapshot):
        content = slide_content(slide)
        claim = content.get("claim") or content.get("subtitle")
        normalized = "".join(ch for ch in str(claim or "").casefold() if ch.isalnum())
        if normalized:
            if normalized in claims:
                errors.append(f"slide {page_num(slide)} claim duplicates slide {claims[normalized]}")
            else:
                claims[normalized] = page_num(slide)
    return errors


def validate_family_gate(snapshot: dict[str, Any], *, require_approved: bool = True) -> dict[str, Any]:
    issues = validate_snapshot_base(snapshot)
    slides = snapshot_slides(snapshot)
    families = snapshot_families(snapshot)
    normalized: list[dict[str, Any]] = []
    slide_by_id = {str(slide.get("id")): slide for slide in slides}
    for key, family in families.items():
        family_slides = [
            slide for slide in slides
            if snapshot_slide_family(snapshot, slide) == key
        ]
        if not family_slides:
            continue
        prefix = f"workflow.families.{key}"
        if key not in CORE_FAMILIES and not str(family.get("label") or "").strip():
            issues.append(f"{prefix} project-specific family requires a label")
        representative_id = str(family.get("representative_slide_id") or "").strip()
        if not representative_id:
            issues.append(f"{prefix} requires one visual representative_slide_id")
        elif (
            representative_id not in slide_by_id
            or snapshot_slide_family(snapshot, slide_by_id[representative_id]) != key
        ):
            issues.append(f"{prefix} representative must belong to the family")
        if str(family.get("status") or "") != "approved":
            issues.append(f"{prefix} must be approved")
        approved_types = set(family.get("approved_production_types") or [])
        used_types = {str(slide.get("production_type") or "") for slide in family_slides}
        missing_types = sorted(used_types - approved_types)
        if missing_types:
            issues.append(
                f"{prefix} lacks approved construction samples for production types {missing_types}"
            )
        normalized.append({
            "id": key,
            "page_nums": [page_num(slide) for slide in family_slides],
            "representative_slide_id": representative_id,
            "approved_production_types": sorted(approved_types),
        })
    if require_approved and gate_status(snapshot, "family_prototypes") != "approved":
        issues.append("Gate family_prototypes must be approved")
    return {
        "status": "pass" if not issues else "fail",
        "slide_count": len(slides),
        "families": normalized,
        "issues": issues,
    }


def formal_export_blockers(
    snapshot: dict[str, Any],
    preflight: dict[str, Any] | None = None,
) -> list[str]:
    """Return formal-export blockers; callers must also supply final preflight."""
    blockers = validate_snapshot_base(snapshot)
    workflow = workflow_data(snapshot)
    for name in GATE_NAMES:
        if gate_status(snapshot, name) != "approved":
            blockers.append(f"Gate {name} is not approved")
    for slide in snapshot_slides(snapshot):
        if str(slide.get("visual_role") or "") != "evidence":
            continue
        evidence = slide.get("evidence_state") or {}
        status = str(evidence.get("status") or "")
        if status not in {"confirmed", "waived"}:
            blockers.append(f"slide {page_num(slide)} evidence is unresolved")
        if evidence.get("needs_disclosure") is True and evidence.get("disclosure_confirmed") is not True:
            blockers.append(f"slide {page_num(slide)} AI disclosure is unconfirmed")
    for issue in snapshot_issues(snapshot):
        if issue.get("severity") == "blocking" and issue.get("status") != "closed":
            blockers.append(f"blocking issue {issue.get('id')} is open")
    for item in workflow.get("blockers") or []:
        if isinstance(item, dict):
            blockers.append(str(item.get("code") or item.get("message") or "workflow blocker"))

    response = preflight or snapshot.get("export_preflight")
    if not isinstance(response, dict):
        blockers.append("final export preflight response is required")
        return list(dict.fromkeys(blockers))
    if "ok" in response:
        if response.get("ok") is not True:
            blockers.append("final export preflight is not ready")
        if response.get("workflow_revision") != project_revision(snapshot):
            blockers.append("final export preflight is stale")
        if response.get("ready_count") != len(snapshot_slides(snapshot)):
            blockers.append("final export preflight did not ready every slide")
        if response.get("blockers"):
            blockers.append("final export preflight contains blockers")
    else:  # earlier offline test shape
        if response.get("status") != "pass":
            blockers.append("export_preflight.status must be pass")
        if response.get("checked_revision") != project_revision(snapshot):
            blockers.append("export_preflight is stale")
        expected = {page_num(slide) for slide in snapshot_slides(snapshot)}
        if set(response.get("assembled_page_nums") or []) != expected:
            blockers.append("export_preflight must confirm every page")
    return list(dict.fromkeys(blockers))
