#!/usr/bin/env python3
"""Narrow Deck Studio bridge to the two canonical Focus Media skills.

This module does not copy either skill's business logic. It only discovers their
entry points, runs bounded subprocesses, normalizes source-backed results, and
reports failures with one actionable next step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


DEFAULT_TIMEOUT_SECONDS = 45
STANDARD_MEDIA = {
    "lcd": ("lcd", "lcd-32", "lcd-32-standard.png"),
    "lcd32": ("lcd", "lcd-32", "lcd-32-standard.png"),
    "楼宇lcd": ("lcd", "lcd-32", "lcd-32-standard.png"),
    "电梯电视": ("lcd", "lcd-32", "lcd-32-standard.png"),
    "smart": ("smart-screen", "smart-32", "smart-32-standard.png"),
    "smartscreen": ("smart-screen", "smart-32", "smart-32-standard.png"),
    "smart32": ("smart-screen", "smart-32", "smart-32-standard.png"),
    "智能屏": ("smart-screen", "smart-32", "smart-32-standard.png"),
    "poster": ("poster-frame", "poster-frame-standard", "poster-frame-standard.png"),
    "posterframe": ("poster-frame", "poster-frame-standard", "poster-frame-standard.png"),
    "海报框架": ("poster-frame", "poster-frame-standard", "poster-frame-standard.png"),
    "框架海报": ("poster-frame", "poster-frame-standard", "poster-frame-standard.png"),
}


class BridgeError(RuntimeError):
    """Raised when a canonical Focus Media entry point cannot complete."""


def _candidate_roots(kind: str) -> list[Path]:
    home = Path.home()
    if kind == "knowledge":
        configured = os.environ.get("FOCUSMEDIA_KNOWLEDGE_SKILL")
        defaults = [
            home / ".codex/skills/focusmedia-knowledge",
            home / ".agents/skills/focusmedia-knowledge",
        ]
    else:
        configured = os.environ.get("FOCUSMEDIA_IMAGE_SKILL")
        defaults = [
            home / ".codex/skills/focusmedia-image-gen",
            home / ".agents/skills/focusmedia-image-gen",
            home
            / "Desktop/Development/分众媒体图片生成/focusmedia-image-gen",
        ]
    candidates = [Path(configured).expanduser()] if configured else []
    return candidates + defaults


def _find_root(kind: str) -> Path:
    for candidate in _candidate_roots(kind):
        if candidate.is_dir():
            return candidate.resolve()
    env_name = (
        "FOCUSMEDIA_KNOWLEDGE_SKILL"
        if kind == "knowledge"
        else "FOCUSMEDIA_IMAGE_SKILL"
    )
    raise BridgeError(
        f"{kind} skill not found; set {env_name} to its absolute directory"
    )


def _run(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    try:
        result = subprocess.run(
            list(command),
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise BridgeError(
            f"command timed out after {timeout}s: {command[0]}"
        ) from exc
    except OSError as exc:
        raise BridgeError(f"cannot run {command[0]}: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise BridgeError(
            f"command failed ({result.returncode}): {detail[:500]}"
        )
    return result.stdout


def _json_output(
    command: Sequence[str],
    *,
    cwd: Path,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Any:
    output = _run(command, cwd=cwd, timeout=timeout)
    try:
        return json.loads(output)
    except json.JSONDecodeError as exc:
        raise BridgeError(f"command returned invalid JSON: {command[0]}") from exc


def _knowledge_cli(root: Path) -> Path:
    cli = root / "scripts/fm-kb"
    if not cli.is_file():
        raise BridgeError(f"missing canonical knowledge entry point: {cli}")
    return cli


def _reference_selector(root: Path) -> Path:
    selector = root / "scripts/select_media_references.py"
    if not selector.is_file():
        raise BridgeError(f"missing canonical media selector: {selector}")
    return selector


def _reference_fetcher(root: Path) -> Path:
    fetcher = root / "scripts/fetch_reference_images.py"
    if not fetcher.is_file():
        raise BridgeError(f"missing canonical media fetcher: {fetcher}")
    return fetcher


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_standard(media: str) -> dict[str, Any]:
    key = "".join(
        character
        for character in str(media or "").strip().casefold()
        if character.isalnum() or "\u4e00" <= character <= "\u9fff"
    )
    if "19" in key or "25" in key:
        raise BridgeError(
            "smart-19 and smart-25 are not yet verified for production; "
            "use smart-32 for now or add an approved standard before enabling them"
        )
    normalized = STANDARD_MEDIA.get(key)
    if normalized is None:
        raise BridgeError(
            "unsupported media standard; use lcd, smart-screen, or poster-frame"
        )
    media_type, hardware_standard, filename = normalized
    root = _find_root("image")
    asset = root / "assets/framed-demo-standards" / filename
    manifest_path = asset.parent / "manifest.json"
    if not manifest_path.is_file():
        raise BridgeError(f"missing framed-standard manifest: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BridgeError(f"invalid framed-standard manifest: {manifest_path}") from exc
    records = {
        item.get("file"): item
        for item in manifest.get("assets") or []
        if isinstance(item, dict)
    }
    if filename not in records:
        raise BridgeError(
            f"hardware standard {hardware_standard} is not approved in manifest"
        )
    if not asset.is_file():
        raise BridgeError(f"approved framed-standard asset not found: {asset}")
    contract = {
        "id": f"fm-standard-{hardware_standard}",
        "path": str(asset.resolve()),
        "sha256": _sha256(asset),
        "role": "verified-standard-frame",
        "media_type": media_type,
        "hardware_standard": hardware_standard,
    }
    return {
        "status": "ok",
        "route": "focusmedia-image-gen",
        "skill_root": str(root),
        "hardware_standard": hardware_standard,
        "reference_contract": contract,
    }


def _fetch_reference(
    root: Path,
    item: dict[str, Any],
    download_dir: Path,
    *,
    timeout: int,
) -> Path:
    reference_id = str(item.get("id") or "").strip()
    remote_path = str(item.get("path") or "").strip()
    expected = str(item.get("sha256") or "").strip().lower()
    if not reference_id or not remote_path or len(expected) != 64:
        raise BridgeError(
            "selected media reference must include id, path, and sha256"
        )
    download_dir.mkdir(parents=True, exist_ok=True)
    target = download_dir / Path(remote_path).name
    if not target.is_file() or _sha256(target) != expected:
        fetcher = _reference_fetcher(root)
        _run(
            [
                sys.executable,
                str(fetcher),
                "--id",
                reference_id,
                "--output",
                str(download_dir),
            ],
            cwd=root,
            timeout=timeout,
        )
    if not target.is_file():
        raise BridgeError(f"media fetcher did not create expected file: {target}")
    actual = _sha256(target)
    if actual != expected:
        raise BridgeError(f"downloaded media reference failed checksum: {target}")
    return target.resolve()


def _normalize_evidence(results: Any) -> list[dict[str, Any]]:
    if not isinstance(results, list):
        return []
    evidence: list[dict[str, Any]] = []
    for item in results:
        if not isinstance(item, dict):
            continue
        normalized = {
            field: item[field]
            for field in (
                "entity_id",
                "entity_type",
                "title",
                "source_id",
                "locator",
                "status",
                "rank",
                "path",
                "kind",
                "position",
                "absolute_path",
                "trust",
                "content_hash",
            )
            if item.get(field) not in (None, "")
        }
        entity_id = item.get("entity_id")
        if entity_id and not normalized.get("fragment_id"):
            normalized["fragment_id"] = entity_id
        if (
            item.get("entity_type") == "knowledge"
            and entity_id
            and not normalized.get("source_id")
        ):
            normalized["source_id"] = entity_id
        excerpt = str(item.get("excerpt") or item.get("content") or "").strip()
        if excerpt:
            normalized["excerpt"] = excerpt[:800]
        metadata = item.get("metadata")
        if isinstance(metadata, dict):
            compact_metadata = {
                field: metadata[field]
                for field in ("updated", "sources", "source_ids")
                if metadata.get(field) not in (None, "", [])
            }
            if compact_metadata:
                normalized["metadata"] = compact_metadata
        evidence.append(normalized)
    return evidence


def query_knowledge(
    question: str,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    root = _find_root("knowledge")
    cli = _knowledge_cli(root)
    formal = _json_output(
        [str(cli), "query", question, "--mode", "knowledge", "--limit", "8"],
        cwd=root,
        timeout=timeout,
    )
    formal_results = _normalize_evidence(formal.get("local_results"))
    return {
        "status": "ok" if formal_results else "empty",
        "query": question,
        "mode": "knowledge",
        "candidate_only": False,
        "fallback_used": False,
        "evidence": formal_results,
    }


def query_source(
    question: str,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Search original PPT/PDF fragments only after an explicit source request."""
    root = _find_root("knowledge")
    cli = _knowledge_cli(root)
    source = _json_output(
        [
            str(cli),
            "query",
            question,
            "--mode",
            "source",
            "--research",
            "--limit",
            "8",
        ],
        cwd=root,
        timeout=timeout,
    )
    source_results = _normalize_evidence(source.get("local_results"))
    return {
        "status": "ok" if source_results else "empty",
        "query": question,
        "mode": "source",
        "candidate_only": True,
        "evidence": source_results,
    }


def resolve_fragment(
    fragment_id: str,
    *,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    root = _find_root("knowledge")
    cli = _knowledge_cli(root)
    resolved = _json_output(
        [str(cli), "resolve", fragment_id],
        cwd=root,
        timeout=timeout,
    )
    if not isinstance(resolved, dict):
        raise BridgeError("resolve did not return an object")
    required = ("source_id", "locator", "path", "absolute_path", "kind", "position")
    missing = [field for field in required if not resolved.get(field)]
    if missing:
        raise BridgeError(f"resolve result missing fields: {', '.join(missing)}")
    resolved = {
        field: resolved[field]
        for field in (
            "id",
            "source_id",
            "locator",
            "path",
            "absolute_path",
            "kind",
            "position",
            "title",
            "source_title",
            "media_type",
            "trust",
            "content_hash",
        )
        if resolved.get(field) not in (None, "")
    }
    resolved["fragment_id"] = resolved.get("id") or fragment_id
    return {
        "status": "ok",
        "query": fragment_id,
        "mode": "source",
        "candidate_only": True,
        "evidence": [resolved],
    }


def select_references(
    *,
    media: str,
    scene: str,
    angle: str,
    shot_size: str,
    people: str,
    max_grade: str,
    limit: int,
    download_dir: Path | None = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    root = _find_root("image")
    selector = _reference_selector(root)
    command = [
        sys.executable,
        str(selector),
        "--media",
        media,
        "--scene",
        scene,
        "--angle",
        angle,
        "--shot-size",
        shot_size,
        "--people",
        people,
        "--max-grade",
        max_grade,
        "--limit",
        str(limit),
        "--json",
    ]
    raw = _json_output(command, cwd=root, timeout=timeout)
    if not isinstance(raw, list):
        raise BridgeError("media selector did not return an array")
    cache_dir = (
        download_dir.expanduser().resolve()
        if download_dir is not None
        else (root / ".focusmedia-cache/references").resolve()
    )
    candidates: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict) or not item.get("path"):
            continue
        normalized = dict(item)
        local_path = _fetch_reference(
            root,
            normalized,
            cache_dir,
            timeout=timeout,
        )
        normalized["reference_id"] = normalized.get("id")
        normalized["absolute_path"] = str(local_path)
        normalized["reference_contract"] = {
            "id": normalized.get("id"),
            "path": str(local_path),
            "sha256": normalized.get("sha256"),
            "role": "environment-geometry",
            "media_type": str(normalized.get("media_type") or "").casefold(),
        }
        size = str(item.get("size") or "").lower().split("x")
        try:
            width, height = int(size[0]), int(size[1])
        except (ValueError, IndexError):
            width, height = 0, 0
        if max(width, height) > 4096:
            normalized["edit_transport"] = {
                "preserve_original": True,
                "recommended_max_edge": 2048,
                "reason": "bound synchronous edit upload bytes",
            }
        candidates.append(normalized)
    return {
        "status": "ok" if candidates else "empty",
        "route": "focusmedia-image-gen",
        "skill_root": str(root),
        "download_dir": str(cache_dir),
        "candidates": candidates,
    }


def doctor(*, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    try:
        knowledge_root = _find_root("knowledge")
        cli = _knowledge_cli(knowledge_root)
        report = _json_output(
            [str(cli), "doctor"],
            cwd=knowledge_root,
            timeout=timeout,
        )
        report_checks = report.get("checks") or []
        failed_checks = [
            str(check.get("name"))
            for check in report_checks
            if isinstance(check, dict)
            and check.get("status") in {"error", "fail"}
            and check.get("name")
        ]
        warning_checks = [
            str(check.get("name"))
            for check in report_checks
            if isinstance(check, dict)
            and check.get("status") == "warning"
            and check.get("name")
        ]
        knowledge_ok = report.get("overall") == "ok"
        checks.append({
            "name": "focusmedia-knowledge",
            "status": "ok" if knowledge_ok else "fail",
            "root": str(knowledge_root),
            "detail": {
                "overall": report.get("overall"),
                "failed_checks": failed_checks,
                "warning_checks": warning_checks,
            },
            **({
                "next": (
                    f"run {cli} doctor and fix its first failed check: "
                    f"{failed_checks[0] if failed_checks else 'inspect the canonical report'}"
                )
            } if not knowledge_ok else {}),
        })
    except BridgeError as exc:
        checks.append({
            "name": "focusmedia-knowledge",
            "status": "fail",
            "next": str(exc),
        })

    try:
        image_root = _find_root("image")
        selector = _reference_selector(image_root)
        fetcher = _reference_fetcher(image_root)
        manifest = image_root / "references/remote-manifest.json"
        framed_manifest = image_root / "assets/framed-demo-standards/manifest.json"
        provider_health = image_root / "scripts/comet_image.py"
        missing = [
            str(path)
            for path in (
                selector,
                fetcher,
                manifest,
                framed_manifest,
                image_root / "assets/framed-demo-standards/lcd-32-standard.png",
                image_root / "assets/framed-demo-standards/smart-32-standard.png",
                image_root / "assets/framed-demo-standards/poster-frame-standard.png",
                provider_health,
                image_root / "SKILL.md",
            )
            if not path.is_file()
        ]
        health = ""
        if not missing:
            health = _run(
                [sys.executable, str(provider_health), "health"],
                cwd=image_root,
                timeout=timeout,
            ).strip()
            if not health.startswith("healthy "):
                missing.append("working image provider health response")
        checks.append({
            "name": "focusmedia-image-gen",
            "status": "fail" if missing else "ok",
            "root": str(image_root),
            "detail": {"missing": missing, "provider": health},
            **({"next": f"restore required file: {missing[0]}"} if missing else {}),
        })
    except BridgeError as exc:
        checks.append({
            "name": "focusmedia-image-gen",
            "status": "fail",
            "next": str(exc),
        })

    return {
        "status": (
            "ok"
            if checks and all(check["status"] == "ok" for check in checks)
            else "fail"
        ),
        "checks": checks,
    }


def _write(payload: dict[str, Any], *, empty_ok: bool = False) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    status = payload.get("status")
    return 0 if status == "ok" or (empty_ok and status == "empty") else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="subprocess timeout in seconds",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="verify both canonical skill entry points")

    query_parser = subparsers.add_parser(
        "query",
        help="query reviewed Markdown knowledge only",
    )
    query_parser.add_argument("question")

    source_parser = subparsers.add_parser(
        "source",
        help="explicitly search original PPT/PDF fragments",
    )
    source_parser.add_argument("question")

    resolve_parser = subparsers.add_parser(
        "resolve",
        help="resolve one source fragment to its canonical file and page",
    )
    resolve_parser.add_argument("fragment_id")

    reference_parser = subparsers.add_parser(
        "select-reference",
        help="select real Focus Media image references",
    )
    reference_parser.add_argument("--media", required=True)
    reference_parser.add_argument(
        "--scene",
        choices=("elevator-hall", "elevator-inside", "corridor", "any"),
        default="any",
    )
    reference_parser.add_argument(
        "--angle",
        choices=("front", "angle", "wide", "any"),
        default="any",
    )
    reference_parser.add_argument(
        "--shot-size",
        choices=("mid", "wide", "any"),
        default="any",
    )
    reference_parser.add_argument(
        "--people",
        choices=("nopeople", "people", "any"),
        default="any",
    )
    reference_parser.add_argument(
        "--max-grade",
        choices=("A", "B", "C"),
        default="A",
    )
    reference_parser.add_argument("--limit", type=int, default=4)
    reference_parser.add_argument(
        "--download-dir",
        type=Path,
        help="local checksum cache; defaults to the canonical image skill cache",
    )

    standard_parser = subparsers.add_parser(
        "select-standard",
        help="resolve the approved complete framed-media standard",
    )
    standard_parser.add_argument("--media", required=True)

    args = parser.parse_args(argv)
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    try:
        if args.command == "doctor":
            return _write(doctor(timeout=args.timeout))
        if args.command == "query":
            return _write(
                query_knowledge(args.question, timeout=args.timeout),
                empty_ok=True,
            )
        if args.command == "source":
            return _write(
                query_source(args.question, timeout=args.timeout),
                empty_ok=True,
            )
        if args.command == "resolve":
            return _write(resolve_fragment(args.fragment_id, timeout=args.timeout))
        if args.command == "select-standard":
            return _write(select_standard(args.media))
        return _write(
            select_references(
                media=args.media,
                scene=args.scene,
                angle=args.angle,
                shot_size=args.shot_size,
                people=args.people,
                max_grade=args.max_grade,
                limit=args.limit,
                download_dir=args.download_dir,
                timeout=args.timeout,
            )
        )
    except BridgeError as exc:
        next_step = (
            "use --media smart-screen for the current smart-32 route; future sizes "
            "require an approved standard and validation"
            if args.command == "select-standard" and "not yet verified" in str(exc)
            else "run focusmedia_bridge.py doctor and fix its first failed check"
        )
        return _write({
            "status": "fail",
            "error": str(exc),
            "next": next_step,
        })


if __name__ == "__main__":
    raise SystemExit(main())
