#!/usr/bin/env python3
"""Run local PITER demo readiness checks against a running Flask server."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]


def _request(method: str, url: str, payload: dict | None = None, *, timeout: float = 10) -> tuple[int, dict]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    request = Request(url, data=body, headers=headers, method=method)
    with urlopen(request, timeout=timeout) as response:
        text = response.read().decode("utf-8")
        return response.status, json.loads(text) if text else {}


def _check_endpoint(method: str, base_url: str, path: str, payload: dict | None = None) -> str:
    url = f"{base_url.rstrip('/')}{path}"
    timeout = 90.0 if method == "POST" else 10.0
    try:
        status, data = _request(method, url, payload, timeout=timeout)
    except HTTPError as exc:
        raise RuntimeError(f"{method} {path} returned HTTP {exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc.reason}") from exc
    if status >= 400:
        raise RuntimeError(f"{method} {path} returned HTTP {status}")
    if path.startswith("/api/") and data.get("ok") is not True and path != "/api/health":
        raise RuntimeError(f"{method} {path} response missing ok=true")
    return f"OK {method} {path}"


def run(base_url: str) -> list[str]:
    messages: list[str] = []
    validate_cmd = [sys.executable, str(ROOT / "scripts" / "validate_data.py")]
    subprocess.run(validate_cmd, cwd=ROOT, check=True, capture_output=True, text=True)
    messages.append("OK data validation")
    checks = [
        ("GET", "/health", None),
        ("GET", "/api/health", None),
        ("GET", "/api/tools/status", None),
        ("GET", "/api/history", None),
        ("POST", "/api/chat", {"message": "What should I check when users cannot log in after the latest deployment?"}),
        (
            "POST",
            "/api/incidents/analyze",
            {
                "service": "auth-service",
                "environment": "production",
                "severity": "P1",
                "symptom": "Many users cannot log in after the latest production deployment.",
                "description": "Many users cannot log in after the latest production deployment.",
            },
        ),
    ]
    for method, path, payload in checks:
        messages.append(_check_endpoint(method, base_url, path, payload))
    return messages


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local PITER demo readiness")
    parser.add_argument("--base-url", default="http://localhost:8080")
    args = parser.parse_args()
    try:
        for message in run(args.base_url):
            print(message)
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"DEMO CHECK FAILED: {exc}")
        return 1
    print("PITER demo checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
