#!/usr/bin/env python3
"""Regression checks for local image edit boundary verification."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image, ImageDraw


MODULE_PATH = Path(__file__).parents[1] / "templates" / "verify_local_image_edit.py"
SPEC = spec_from_file_location("verify_local_image_edit", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"cannot load {MODULE_PATH}")
MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
verify_local_edit = MODULE.verify_local_edit


def _save_pair(directory: Path, *, outside_change: bool = False) -> tuple[Path, Path]:
    source_path = directory / "source.png"
    edited_path = directory / "edited.png"
    source = Image.new("RGB", (80, 60), "white")
    edited = source.copy()
    draw = ImageDraw.Draw(edited)
    draw.rectangle((20, 15, 39, 34), fill="red")
    if outside_change:
        draw.point((70, 50), fill="black")
    source.save(source_path)
    edited.save(edited_path)
    return source_path, edited_path


def test_allows_changes_inside_approved_region() -> None:
    with TemporaryDirectory() as temp_dir:
        source, edited = _save_pair(Path(temp_dir))
        report = verify_local_edit(source, edited, [(20, 15, 40, 35)])
        assert report["ok"] is True
        assert report["outside_changed_pixels"] == 0
        assert report["inside_changed_pixels"] == 400


def test_rejects_change_outside_approved_region() -> None:
    with TemporaryDirectory() as temp_dir:
        source, edited = _save_pair(Path(temp_dir), outside_change=True)
        report = verify_local_edit(source, edited, [(20, 15, 40, 35)])
        assert report["ok"] is False
        assert report["reason"] == "outside_edit_boundary_changed"
        assert report["outside_changed_pixels"] == 1


def test_rejects_dimension_change() -> None:
    with TemporaryDirectory() as temp_dir:
        source = Path(temp_dir) / "source.png"
        edited = Path(temp_dir) / "edited.png"
        Image.new("RGB", (80, 60), "white").save(source)
        Image.new("RGB", (81, 60), "white").save(edited)
        report = verify_local_edit(source, edited, [(20, 15, 40, 35)])
        assert report["ok"] is False
        assert report["reason"] == "dimension_mismatch"


def main() -> None:
    test_allows_changes_inside_approved_region()
    test_rejects_change_outside_approved_region()
    test_rejects_dimension_change()
    print("verify_local_image_edit regression checks passed")


if __name__ == "__main__":
    main()
