#!/usr/bin/env python3
"""Compatibility wrapper for the live Bedrock Agent smoke test."""
from __future__ import annotations

from agent_smoke_test import main


if __name__ == "__main__":
    raise SystemExit(main())
