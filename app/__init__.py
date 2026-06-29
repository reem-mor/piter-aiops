"""PITER AiOps application package.

Keep this module free of Flask imports so action-group Lambdas can import
``app.enrichment_tools`` without bundling the web stack.
"""
from __future__ import annotations

import logging
import os

from app.config import Config, ConfigError

log = logging.getLogger(__name__)


def _resolve_config() -> Config:
    """Load Bedrock config, falling back to offline-safe local config."""
    mock = os.environ.get("PITER_MOCK_MODE", "").strip().lower()
    if mock in {"true", "1", "yes", "on"}:
        log.info("PITER_MOCK_MODE enabled — starting PITER AiOps in LOCAL mode")
        return Config.local()
    raw = os.environ.get("PITER_USE_BEDROCK", os.environ.get("USE_BEDROCK", "")).strip().lower()
    if raw in {"false", "0", "no", "off"}:
        log.info("USE_BEDROCK disabled — starting PITER AiOps in LOCAL mode")
        return Config.local()
    try:
        return Config.from_env()
    except ConfigError as exc:
        if raw in {"true", "1", "yes", "on"}:
            raise
        log.warning("AWS/Bedrock config incomplete (%s) — falling back to LOCAL mode", exc)
        return Config.local()


def create_app(config: Config | None = None):
    from flask import Flask
    from flask_wtf.csrf import CSRFProtect

    csrf = CSRFProtect()
    app = Flask(__name__)
    config_obj = config or _resolve_config()
    app.config.from_object(config_obj)
    app.config["PITER_CONFIG"] = config_obj
    app.config["LOCAL_FALLBACK"] = config_obj.LOCAL_FALLBACK

    app.config.setdefault("SESSION_COOKIE_HTTPONLY", True)
    app.config.setdefault("SESSION_COOKIE_SAMESITE", "Lax")
    app.config.setdefault("SESSION_COOKIE_SECURE", app.config.get("FLASK_ENV") == "production")
    app.config.setdefault("FORCE_LEGACY_UI", os.getenv("FORCE_LEGACY_UI", "").lower() in {"1", "true", "yes"})

    csrf.init_app(app)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )

    from app.routes import bp as main_bp
    from app.spa import bp as spa_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(spa_bp)

    csrf.exempt(main_bp)

    @app.after_request
    def cors_for_vite_dev(response):
        from flask import request

        origin = os.getenv("FRONTEND_DEV_ORIGIN", "http://localhost:5173")
        request_origin = request.headers.get("Origin")
        if os.getenv("FLASK_ENV") == "development" and request_origin == origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-CSRFToken"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        return response

    @app.context_processor
    def inject_ui_context():
        arn = app.config.get("BEDROCK_MODEL_ARN", "") or ""
        model_label = arn.rsplit("/", 1)[-1] if arn else "Bedrock model"
        return {
            "model_label": model_label,
            "kb_id": app.config.get("BEDROCK_KB_ID", ""),
        }

    return app
