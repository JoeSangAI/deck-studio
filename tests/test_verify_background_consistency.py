import importlib.util
from pathlib import Path
from xml.etree import ElementTree as ET


MODULE_PATH = (
    Path(__file__).parents[1] / "templates" / "verify_background_consistency.py"
)
SPEC = importlib.util.spec_from_file_location(
    "verify_background_consistency", MODULE_PATH
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


SLIDE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld>
    <p:bg>
      <p:bgPr>
        <a:solidFill><a:srgbClr val="{color}"/></a:solidFill>
      </p:bgPr>
    </p:bg>
  </p:cSld>
</p:sld>
"""


def test_background_color_distinguishes_white_from_warm_white():
    white = ET.fromstring(SLIDE_XML.format(color="FFFFFF"))
    warm_white = ET.fromstring(SLIDE_XML.format(color="F4F1EA"))

    assert MODULE.explicit_background(white) == "#FFFFFF"
    assert MODULE.explicit_background(warm_white) == "#F4F1EA"
    assert MODULE.explicit_background(white) != MODULE.explicit_background(
        warm_white
    )


def test_background_slide_ranges_are_deterministic():
    assert MODULE.parse_slides("2,6,10-12") == {2, 6, 10, 11, 12}
