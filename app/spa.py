"""Serve the Vite-built React SPA from app/static/spa when present."""
from __future__ import annotations

from pathlib import Path

from flask import Blueprint, abort, current_app, send_from_directory

bp = Blueprint("spa", __name__)

_SPA_ROOT = Path(__file__).resolve().parent / "static" / "spa"
_RESERVED_PREFIXES = ("api/", "assets/", "documents/", "workflow/")
_RESERVED_EXACT = frozenset({"ask", "health"})


def spa_index_path() -> Path | None:
    index = _SPA_ROOT / "index.html"
    return index if index.is_file() else None


def spa_enabled() -> bool:
    if current_app.config.get("FORCE_LEGACY_UI"):
        return False
    return spa_index_path() is not None


@bp.get("/assets/<path:filename>")
def spa_assets(filename: str):
    assets_dir = _SPA_ROOT / "assets"
    if not assets_dir.is_dir():
        abort(404)
    return send_from_directory(assets_dir, filename)


@bp.get("/<path:path>")
def spa_fallback(path: str):
    if current_app.config.get("FORCE_LEGACY_UI"):
        abort(404)
    if path in _RESERVED_EXACT or path.startswith(_RESERVED_PREFIXES):
        abort(404)
    if spa_index_path() is None:
        abort(404)
    return send_from_directory(_SPA_ROOT, "index.html")
