import subprocess
import sys
from pathlib import Path

from PIL import Image


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = SKILL_ROOT / "scripts" / "contact_sheet.py"


def test_default_contact_sheet_is_compact_webp(tmp_path):
    slides = tmp_path / "slides"
    slides.mkdir()
    for index in range(44):
        image = Image.new(
            "RGB",
            (1600, 900),
            ((index * 17) % 255, (index * 31) % 255, (index * 47) % 255),
        )
        image.save(slides / f"slide-{index + 1:02d}.png")

    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(slides)],
        check=True,
        capture_output=True,
        text=True,
    )

    output = slides / "_contact.webp"
    assert output.exists()
    assert "pages 44" in result.stdout
    with Image.open(output) as sheet:
        assert sheet.format == "WEBP"
        assert sheet.width <= 1800
        assert sheet.height <= 2200
    assert output.stat().st_size < 1_000_000


def test_directory_contact_sheet_preserves_four_by_three_ratio(tmp_path):
    slides = tmp_path / "slides-4x3"
    slides.mkdir()
    Image.new("RGB", (800, 600), "white").save(slides / "slide-01.png")

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(slides),
            "--width",
            "320",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    output = slides / "_contact.webp"
    assert output.exists()
    assert "344x294" in result.stdout
    with Image.open(output) as sheet:
        assert sheet.width == 344
        assert sheet.height == 294
