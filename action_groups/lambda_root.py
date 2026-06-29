"""Resolve project root for local dev and flat Lambda deployment packages."""
from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_root() -> Path:
    here = Path(__file__).resolve().parent
    for root in (here, *here.parents):
        if (root / "app").is_dir():
            root_str = str(root)
            if root_str not in sys.path:
                sys.path.insert(0, root_str)
            return root
    return here
