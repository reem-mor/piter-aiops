#!/usr/bin/env python3
"""Verify AWS credentials and required PITER Bedrock configuration."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import boto3  # noqa: E402

from app.config import Config, ConfigError  # noqa: E402


def main() -> int:
    errors: list[str] = []

    try:
        identity = boto3.client("sts").get_caller_identity()
        print(f"AWS account: {identity.get('Account')}")
        print(f"ARN: {identity.get('Arn')}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"STS get-caller-identity failed: {exc}")

    try:
        cfg = Config.from_env()
    except ConfigError as exc:
        errors.append(str(exc))
        for line in errors:
            print(f"FAIL: {line}")
        return 1

    print(f"Region: {cfg.AWS_REGION}")
    print(f"RAG backend: {cfg.RAG_BACKEND}")
    print(f"KB ID: {cfg.BEDROCK_KB_ID}")
    if cfg.RAG_BACKEND == "agent":
        print(f"Agent: {cfg.BEDROCK_AGENT_ID}/{cfg.BEDROCK_AGENT_ALIAS_ID}")

    try:
        agent = boto3.client("bedrock-agent", region_name=cfg.AWS_REGION)
        if cfg.RAG_BACKEND == "agent":
            alias = agent.get_agent_alias(
                agentId=cfg.BEDROCK_AGENT_ID,
                agentAliasId=cfg.BEDROCK_AGENT_ALIAS_ID,
            )["agentAlias"]
            status = alias.get("agentAliasStatus", "UNKNOWN")
            print(f"Agent alias status: {status}")
            if status != "PREPARED":
                errors.append(f"Agent alias not PREPARED (status={status})")
        kb = agent.get_knowledge_base(knowledgeBaseId=cfg.BEDROCK_KB_ID)["knowledgeBase"]
        print(f"Knowledge base status: {kb.get('status')}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"Bedrock control-plane check failed: {exc}")

    if errors:
        for line in errors:
            print(f"FAIL: {line}")
        return 1

    print("OK: credentials and Bedrock configuration look usable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
