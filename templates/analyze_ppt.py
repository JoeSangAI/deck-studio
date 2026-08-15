#!/usr/bin/env python3
"""Compatibility entry point for the canonical Deck Studio audit.

Use ``deck_audit.py`` in new workflows. This wrapper remains so older commands
keep working without maintaining a second, weaker analysis implementation.
"""

from __future__ import annotations

import sys

from deck_audit import main


if __name__ == "__main__":
    print(
        "NOTICE: analyze_ppt.py is a compatibility alias; using deck_audit.py",
        file=sys.stderr,
    )
    raise SystemExit(main())
