#!/usr/bin/env python3
"""Validate all four PPT God Gates against the separate final preflight."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from templates.project_snapshot_contract import (
        formal_export_blockers,
        is_project_snapshot,
        load_json_source,
        project_revision,
        snapshot_slides,
    )
except ModuleNotFoundError:  # direct execution from templates/
    from project_snapshot_contract import (
        formal_export_blockers,
        is_project_snapshot,
        load_json_source,
        project_revision,
        snapshot_slides,
    )


def validate_workflow_ready(snapshot: dict, preflight: dict) -> dict:
    blockers = formal_export_blockers(snapshot, preflight)
    return {
        "status": "pass" if not blockers else "fail",
        "workflow_revision": project_revision(snapshot),
        "slide_count": len(snapshot_slides(snapshot)),
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_snapshot", help="project-snapshot JSON file or HTTP(S) URL")
    parser.add_argument("final_preflight", help="final/preflight JSON file or HTTP(S) URL")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    snapshot = load_json_source(args.project_snapshot)
    preflight = load_json_source(args.final_preflight)
    if not is_project_snapshot(snapshot):
        report = {
            "status": "fail",
            "blockers": ["project_snapshot must be the live PPT God response"],
        }
    else:
        report = validate_workflow_ready(snapshot, preflight)
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload, encoding="utf-8")
    print(payload, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
