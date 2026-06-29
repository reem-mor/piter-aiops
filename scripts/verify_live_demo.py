#!/usr/bin/env python3
"""End-to-end live demo verification against a running PITER AiOps server."""
from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = "http://localhost:8080"


def _get(url: str) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def _post(url: str, payload: dict) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify PITER AiOps live demo endpoints")
    parser.add_argument("--base-url", default=DEFAULT_BASE, help="App base URL")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    failures: list[str] = []

    checks = [
        ("GET /health", f"{base}/health"),
        ("GET /api/health", f"{base}/api/health"),
        ("GET /api/tools/status", f"{base}/api/tools/status"),
    ]
    for label, url in checks:
        try:
            status, data = _get(url)
            if status != 200:
                failures.append(f"{label} HTTP {status}")
            elif label.endswith("/health") and data.get("status") != "ok":
                failures.append(f"{label} status != ok")
            else:
                print(f"OK  {label}")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            failures.append(f"{label}: {exc}")

    question = (
        "What should I check when users cannot log in after the latest deployment?"
    )
    try:
        status, data = _post(f"{base}/api/chat", {"message": question})
        if status != 200 or not data.get("ok"):
            failures.append(f"POST /api/chat failed: {data}")
        elif not data.get("answer"):
            failures.append("POST /api/chat returned empty answer")
        else:
            mode = data.get("mode", "?")
            grounded = data.get("grounded")
            print(f"OK  POST /api/chat mode={mode} grounded={grounded}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        failures.append(f"POST /api/chat: {exc}")

    if failures:
        for item in failures:
            print(f"FAIL: {item}")
        return 1

    print(f"OK: live demo checks passed against {base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
