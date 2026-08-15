from templates.verify_page_families import validate_page_families


def valid_manifest():
    return {
        "slide_count": 12,
        "changed_slides": [2, 6, 10, 11],
        "families": [
            {
                "name": "image-chapters",
                "mode": "image-led",
                "slides": [2, 11],
                "representative": 2,
                "visual_contract": {
                    "visual_motif": "full-bleed campus photo",
                    "title_system": "large sans-serif title",
                },
            },
            {
                "name": "native-structure",
                "mode": "native-redesign",
                "slides": [6, 10],
                "representative": 6,
                "visual_contract": {
                    "background": "#FFFFFF",
                    "typeface": "微软雅黑",
                },
            },
        ],
    }


def test_page_family_manifest_passes_when_every_changed_slide_is_owned_once():
    report = validate_page_families(valid_manifest())
    assert report["status"] == "pass"
    assert report["issues"] == []


def test_page_family_manifest_rejects_missing_and_duplicate_ownership():
    data = valid_manifest()
    data["families"][0]["slides"].append(6)
    data["families"][1]["slides"].remove(10)
    report = validate_page_families(data)
    assert report["status"] == "fail"
    assert "slides assigned to multiple families: [6]" in report["issues"]
    assert "changed slides missing a family: [10]" in report["issues"]


def test_shell_unify_requires_explicit_preservation_contract():
    data = valid_manifest()
    data["families"][1]["mode"] = "shell-unify"
    report = validate_page_families(data)
    assert report["status"] == "fail"
    assert (
        "family[2].must_preserve is required for shell-unify"
        in report["issues"]
    )
