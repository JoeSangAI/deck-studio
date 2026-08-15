from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "templates"))

from illustration_cutout import cutout_image


def alpha_at(path: Path, xy: tuple[int, int]) -> int:
    image = Image.open(path).convert("RGBA")
    return image.getpixel(xy)[3]


def test_white_background_is_removed_and_subject_is_preserved(tmp_path):
    source = tmp_path / "white_bg.png"
    output = tmp_path / "cutout.png"
    image = Image.new("RGB", (80, 80), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((25, 20, 55, 60), fill=(20, 30, 40))
    image.save(source)

    result = cutout_image(source, output)

    assert result.success is True
    assert output.exists()
    assert alpha_at(output, (2, 2)) == 0
    assert alpha_at(output, (40, 40)) == 255


def test_solid_color_background_is_removed(tmp_path):
    source = tmp_path / "green_bg.png"
    output = tmp_path / "cutout.png"
    image = Image.new("RGB", (80, 80), (0, 180, 90))
    draw = ImageDraw.Draw(image)
    draw.rectangle((28, 22, 52, 58), fill=(210, 60, 40))
    image.save(source)

    result = cutout_image(source, output)

    assert result.success is True
    assert alpha_at(output, (1, 1)) == 0
    assert alpha_at(output, (40, 40)) == 255


def test_only_edge_connected_background_is_removed(tmp_path):
    source = tmp_path / "white_interior.png"
    output = tmp_path / "cutout.png"
    image = Image.new("RGB", (90, 90), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((25, 25, 65, 65), fill=(25, 25, 25))
    draw.rectangle((36, 36, 54, 54), fill="white")
    image.save(source)

    result = cutout_image(source, output)

    assert result.success is True
    assert alpha_at(output, (3, 3)) == 0
    assert alpha_at(output, (45, 45)) == 255


def test_fallback_card_is_written_when_background_is_ambiguous(tmp_path):
    source = tmp_path / "ambiguous.png"
    output = tmp_path / "cutout.png"
    fallback = tmp_path / "card.png"
    image = Image.new("RGB", (80, 80), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 39, 39), fill=(20, 30, 40))
    draw.rectangle((40, 0, 79, 39), fill=(180, 50, 60))
    draw.rectangle((0, 40, 39, 79), fill=(70, 160, 90))
    draw.rectangle((40, 40, 79, 79), fill=(210, 200, 70))
    image.save(source)

    result = cutout_image(source, output, fallback_card=fallback)

    assert result.success is False
    assert fallback.exists()
    assert Image.open(fallback).mode == "RGBA"
