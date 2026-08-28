from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from templates.verify_pptx import embedded_av_bindings, verify


SLIDE_XML = b'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree/></p:cSld>
</p:sld>'''


def write_pptx(path: Path, media_bytes: bytes | None, duplicate_media_rel: bool = True) -> None:
    relationships = [
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/video" Target="../media/media1.mp4"/>'
    ]
    if duplicate_media_rel:
        relationships.append(
            '<Relationship Id="rId2" Type="http://schemas.microsoft.com/office/2007/relationships/media" Target="../media/media1.mp4"/>'
        )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + ''.join(relationships if media_bytes is not None else [])
        + '</Relationships>'
    ).encode()
    with ZipFile(path, "w", ZIP_DEFLATED) as z:
        z.writestr("ppt/slides/slide1.xml", SLIDE_XML)
        z.writestr("ppt/slides/_rels/slide1.xml.rels", rels_xml)
        if media_bytes is not None:
            z.writestr("ppt/media/media1.mp4", media_bytes)


def test_embedded_av_bindings_deduplicates_video_and_media_relationships(tmp_path: Path) -> None:
    pptx = tmp_path / "source.pptx"
    write_pptx(pptx, b"same-video")

    bindings = embedded_av_bindings(pptx)

    assert sum(bindings[1].values()) == 1


def test_verify_media_preservation_passes_when_unchanged(tmp_path: Path) -> None:
    source = tmp_path / "source.pptx"
    output = tmp_path / "output.pptx"
    write_pptx(source, b"same-video")
    write_pptx(output, b"same-video")

    issues = verify(source, output, [], False, require_media_preserved=True)

    assert not [issue for issue in issues if issue.level == "error"]


def test_verify_media_preservation_fails_when_media_is_missing(tmp_path: Path) -> None:
    source = tmp_path / "source.pptx"
    output = tmp_path / "output.pptx"
    write_pptx(source, b"same-video")
    write_pptx(output, None)

    issues = verify(source, output, [], False, require_media_preserved=True)

    assert any("embedded audio/video changed 1 -> 0" in issue.message for issue in issues)


def test_verify_media_preservation_fails_when_media_bytes_change(tmp_path: Path) -> None:
    source = tmp_path / "source.pptx"
    output = tmp_path / "output.pptx"
    write_pptx(source, b"original-video")
    write_pptx(output, b"changed-video")

    issues = verify(source, output, [], False, require_media_preserved=True)

    assert any("embedded audio/video changed 1 -> 1" in issue.message for issue in issues)
