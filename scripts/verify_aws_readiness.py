#!/usr/bin/env python3
"""Pre-presentation AWS readiness checklist for PITER Bedrock agent demo.

Checks functional wiring, security hardening, and cost guards described in
docs/readiness_report.md. Prints a green/red/warn checklist; exit 1 if any FAIL
in the required (--strict) sections.

Usage:
  py -3.12 scripts/verify_aws_readiness.py
  py -3.12 scripts/verify_aws_readiness.py --profile reemmor --region us-east-1
  py -3.12 scripts/verify_aws_readiness.py --include-polish --include-ec2
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import boto3  # noqa: E402
from botocore.exceptions import ClientError  # noqa: E402

from app.config import Config, ConfigError  # noqa: E402

# Deploy defaults (override via CLI, .env, or AWS_ACCOUNT_ID env var)
DEFAULT_ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "")
DEFAULT_S3_BUCKETS = (
    "your-artifacts-bucket",
    "your-logs-bucket",
)
DEFAULT_LAMBDAS = (
    "piter-recent-deployments",
    "piter-service-context",
    "piter-similar-incidents",
    "piter-escalation",
)
DEFAULT_MODELS = (
    "amazon.nova-lite-v1:0",
    "amazon.titan-embed-text-v2:0",
)
DEFAULT_IAM_USER = "your-aws-profile"
DEFAULT_EC2_NAME = "piter-aiops-demo"
LAMBDA_LOG_PREFIX = "/aws/lambda/"
MIN_LOG_RETENTION_DAYS = 7
BUDGET_ALARM_THRESHOLD_USD = 10.0


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class Check:
    section: str
    name: str
    status: Status
    detail: str
    fix: str = ""

    @property
    def required(self) -> bool:
        return self.section in {"functional", "security", "cost"}


def _session(profile: str | None, region: str) -> boto3.Session:
    kwargs: dict[str, str] = {"region_name": region}
    if profile:
        kwargs["profile_name"] = profile
    return boto3.Session(**kwargs)


def _client(session: boto3.Session, service: str, region: str | None = None):
    if region and service in {"budgets", "ce"}:
        return session.client(service, region_name="us-east-1")
    return session.client(service, region_name=session.region_name)


def _print_check(check: Check) -> None:
    label = check.status.value.ljust(4)
    print(f"{label} [{check.section}] {check.name}")
    if check.detail:
        print(f"      {check.detail}")
    if check.fix and check.status != Status.PASS:
        print(f"      fix: {check.fix}")


def _agent_source_arn(account_id: str, region: str, agent_id: str) -> str:
    return f"arn:aws:bedrock:{region}:{account_id}:agent/{agent_id}"


def _lambda_has_bedrock_permission(
    lam: Any,
    function_name: str,
    agent_source_arn: str,
) -> tuple[bool, str]:
    try:
        resp = lam.get_policy(FunctionName=function_name)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ResourceNotFoundException":
            return False, "no resource-based policy on function"
        raise
    policy = json.loads(resp["Policy"])
    for stmt in policy.get("Statement", []):
        if stmt.get("Effect") != "Allow":
            continue
        principal = stmt.get("Principal", {})
        service = principal.get("Service") if isinstance(principal, dict) else None
        if service != "bedrock.amazonaws.com":
            continue
        condition = stmt.get("Condition", {})
        arn_like = (
            condition.get("ArnLike", {}).get("AWS:SourceArn")
            or condition.get("StringLike", {}).get("AWS:SourceArn")
        )
        if arn_like == agent_source_arn or (
            isinstance(arn_like, str) and agent_source_arn in arn_like
        ):
            return True, "bedrock.amazonaws.com invoke allowed for agent ARN"
        if not condition:
            return True, "bedrock.amazonaws.com invoke allowed (no SourceArn scope)"
    return False, "missing bedrock.amazonaws.com lambda:InvokeFunction permission"


def _policy_allows_actions(
    iam: Any,
    role_name: str,
    required_actions: set[str],
) -> tuple[set[str], set[str]]:
    """Return (found_actions, missing_actions) from role policies (best effort)."""
    found: set[str] = set()
    paginator = iam.get_paginator("list_role_policies")
    for page in paginator.paginate(RoleName=role_name):
        for policy_name in page.get("PolicyNames", []):
            doc = iam.get_role_policy(RoleName=role_name, PolicyName=policy_name)[
                "PolicyDocument"
            ]
            found |= _actions_from_document(doc)

    for policy_arn in iam.list_attached_role_policies(RoleName=role_name).get(
        "AttachedPolicies", []
    ):
        version_id = iam.get_policy(PolicyArn=policy_arn["PolicyArn"])["Policy"][
            "DefaultVersionId"
        ]
        doc = iam.get_policy_version(
            PolicyArn=policy_arn["PolicyArn"], VersionId=version_id
        )["PolicyVersion"]["Document"]
        found |= _actions_from_document(doc)

    missing = {a for a in required_actions if not _action_covered(a, found)}
    return found, missing


def _actions_from_document(doc: dict) -> set[str]:
    actions: set[str] = set()
    for stmt in doc.get("Statement", []):
        if stmt.get("Effect") != "Allow":
            continue
        raw = stmt.get("Action", [])
        if isinstance(raw, str):
            raw = [raw]
        actions.update(raw)
    return actions


def _action_covered(required: str, granted: set[str]) -> bool:
    if required in granted:
        return True
    prefix = required.split(":")[0]
    for action in granted:
        if action == "*":
            return True
        if action.endswith(":*") and required.startswith(action[:-1]):
            return True
        if action == f"{prefix}:*":
            return True
    return False


def check_functional(
    *,
    agent: Any,
    lam: Any,
    iam: Any,
    bedrock: Any,
    account_id: str,
    region: str,
    agent_id: str,
    alias_id: str,
    kb_id: str,
    lambdas: tuple[str, ...],
) -> list[Check]:
    checks: list[Check] = []
    agent_source = _agent_source_arn(account_id, region, agent_id)

    # KB associated with agent (draft)
    try:
        kb_ids: set[str] = set()
        for version in ("DRAFT",):
            resp = agent.list_agent_knowledge_bases(agentId=agent_id, agentVersion=version)
            for item in resp.get("agentKnowledgeBaseSummaries", []):
                kb_ids.add(item.get("knowledgeBaseId", ""))
        if kb_id in kb_ids:
            checks.append(
                Check(
                    "functional",
                    "Agent KB association (DRAFT)",
                    Status.PASS,
                    f"KB {kb_id} attached to agent {agent_id}",
                )
            )
        else:
            checks.append(
                Check(
                    "functional",
                    "Agent KB association (DRAFT)",
                    Status.FAIL,
                    f"KB {kb_id} not in draft associations: {sorted(kb_ids) or 'none'}",
                    "Console -> Agent -> Knowledge bases -> attach KB -> Prepare agent",
                )
            )
    except ClientError as exc:
        checks.append(
            Check(
                "functional",
                "Agent KB association (DRAFT)",
                Status.FAIL,
                str(exc),
                "Verify agent ID and bedrock-agent ListAgentKnowledgeBases permission",
            )
        )

    # Alias PREPARED and routed to a version
    try:
        alias = agent.get_agent_alias(agentId=agent_id, agentAliasId=alias_id)["agentAlias"]
        status = alias.get("agentAliasStatus", "UNKNOWN")
        routes = alias.get("routingConfiguration", [])
        route_versions = [r.get("agentVersion") for r in routes]
        if status == "PREPARED" and route_versions:
            checks.append(
                Check(
                    "functional",
                    "Agent alias prepared",
                    Status.PASS,
                    f"Alias {alias_id} PREPARED -> version(s) {route_versions}",
                )
            )
        else:
            checks.append(
                Check(
                    "functional",
                    "Agent alias prepared",
                    Status.FAIL,
                    f"status={status}, routes={route_versions}",
                    "Prepare agent after KB/tool changes; confirm alias routes to prepared version",
                )
            )
    except ClientError as exc:
        checks.append(
            Check(
                "functional",
                "Agent alias prepared",
                Status.FAIL,
                str(exc),
                "Check PITER_BEDROCK_AGENT_ALIAS_ID",
            )
        )

    # Lambda resource policies (4 functions)
    for fn in lambdas:
        try:
            ok, detail = _lambda_has_bedrock_permission(lam, fn, agent_source)
            checks.append(
                Check(
                    "functional",
                    f"Lambda permission: {fn}",
                    Status.PASS if ok else Status.FAIL,
                    detail,
                    f"aws lambda add-permission --function-name {fn} "
                    f"--statement-id bedrock-agent-invoke --action lambda:InvokeFunction "
                    f"--principal bedrock.amazonaws.com "
                    f'--source-arn "{agent_source}"',
                )
            )
        except ClientError as exc:
            checks.append(
                Check(
                    "functional",
                    f"Lambda permission: {fn}",
                    Status.FAIL,
                    str(exc),
                    "Confirm function exists in region/account",
                )
            )

    # Agent execution role (least-privilege smoke check) + memory
    agent_meta: dict[str, Any] = {}
    try:
        agent_meta = agent.get_agent(agentId=agent_id)["agent"]
        role_arn = agent_meta.get("agentResourceRoleArn", "")
        role_name = role_arn.split("/")[-1] if role_arn else ""
        required = {
            "bedrock:InvokeModel",
            "bedrock:Retrieve",
            "bedrock:RetrieveAndGenerate",
            "lambda:InvokeFunction",
        }
        if role_name:
            _, missing = _policy_allows_actions(iam, role_name, required)
            if not missing:
                checks.append(
                    Check(
                        "functional",
                        "Agent execution role actions",
                        Status.PASS,
                        f"Role {role_name} allows required Bedrock/Lambda actions",
                    )
                )
            else:
                checks.append(
                    Check(
                        "functional",
                        "Agent execution role actions",
                        Status.WARN,
                        f"Role {role_name} may be missing: {sorted(missing)} "
                        "(wildcard policies not fully parsed)",
                        "Attach least-privilege policy for Nova, Titan embed, KB ARN, four Lambdas",
                    )
                )
        else:
            checks.append(
                Check(
                    "functional",
                    "Agent execution role actions",
                    Status.FAIL,
                    "agentResourceRoleArn empty",
                    "Set agent execution role in Bedrock console",
                )
            )
    except ClientError as exc:
        checks.append(
            Check(
                "functional",
                "Agent execution role actions",
                Status.FAIL,
                str(exc),
                "",
            )
        )

    # Agent memory configuration (optional feature)
    try:
        memory = agent_meta.get("memoryConfiguration")
        if memory and memory.get("enabledMemoryTypes"):
            checks.append(
                Check(
                    "functional",
                    "Agent memory (cross-session)",
                    Status.PASS,
                    f"Enabled: {memory.get('enabledMemoryTypes')}",
                )
            )
        else:
            checks.append(
                Check(
                    "functional",
                    "Agent memory (cross-session)",
                    Status.WARN,
                    "Not enabled - reuse sessionId for within-session context only",
                    "Console -> Agent -> Memory -> SESSION_SUMMARY, or persist history in Flask",
                )
            )
    except ClientError:
        pass

    # Foundation model access
    for model_id in DEFAULT_MODELS:
        try:
            bedrock.get_foundation_model(modelIdentifier=model_id)
            checks.append(
                Check(
                    "functional",
                    f"Model access: {model_id}",
                    Status.PASS,
                    "Model visible in account/region",
                )
            )
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in {"ResourceNotFoundException", "AccessDeniedException"}:
                checks.append(
                    Check(
                        "functional",
                        f"Model access: {model_id}",
                        Status.FAIL,
                        f"{code}: enable in Bedrock -> Model access ({region})",
                        "Bedrock console -> Model access -> enable Nova Lite and Titan embeddings",
                    )
                )
            else:
                checks.append(
                    Check(
                        "functional",
                        f"Model access: {model_id}",
                        Status.WARN,
                        str(exc),
                        "",
                    )
                )

    return checks


def check_security(
    *,
    session: boto3.Session,
    iam: Any,
    sts_user: str,
    s3_buckets: tuple[str, ...],
) -> list[Check]:
    checks: list[Check] = []
    s3 = session.client("s3")

    # MFA on admin user
    user = sts_user.split("/")[-1] if "/" in sts_user else DEFAULT_IAM_USER
    try:
        devices = iam.list_mfa_devices(UserName=user).get("MFADevices", [])
        if devices:
            checks.append(
                Check(
                    "security",
                    f"IAM MFA ({user})",
                    Status.PASS,
                    f"{len(devices)} MFA device(s) registered",
                )
            )
        else:
            checks.append(
                Check(
                    "security",
                    f"IAM MFA ({user})",
                    Status.FAIL,
                    "No MFA devices - IAM dashboard will flag this",
                    "IAM -> Users -> Security credentials -> Assign MFA device",
                )
            )
    except ClientError as exc:
        checks.append(
            Check(
                "security",
                f"IAM MFA ({user})",
                Status.WARN,
                f"Could not verify: {exc}",
                "Enable MFA on your admin IAM user",
            )
        )

    # S3 block public access + encryption per bucket
    for bucket in s3_buckets:
        try:
            bpa = s3.get_public_access_block(Bucket=bucket)
            cfg = bpa.get("PublicAccessBlockConfiguration", {})
            all_on = all(
                cfg.get(k, False)
                for k in (
                    "BlockPublicAcls",
                    "IgnorePublicAcls",
                    "BlockPublicPolicy",
                    "RestrictPublicBuckets",
                )
            )
            checks.append(
                Check(
                    "security",
                    f"S3 Block Public Access: {bucket}",
                    Status.PASS if all_on else Status.FAIL,
                    str(cfg),
                    "S3 -> bucket -> Permissions -> Block all public access -> ON",
                )
            )
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in {"NoSuchPublicAccessBlockConfiguration", "AccessDenied"}:
                checks.append(
                    Check(
                        "security",
                        f"S3 Block Public Access: {bucket}",
                        Status.FAIL if code == "NoSuchPublicAccessBlockConfiguration" else Status.WARN,
                        str(exc),
                        "Enable Block Public Access on artifacts and logs buckets",
                    )
                )
            else:
                checks.append(
                    Check(
                        "security",
                        f"S3 Block Public Access: {bucket}",
                        Status.WARN,
                        str(exc),
                        "",
                    )
                )

        try:
            enc = s3.get_bucket_encryption(Bucket=bucket)
            rules = enc.get("ServerSideEncryptionConfiguration", {}).get("Rules", [])
            algo = rules[0].get("ApplyServerSideEncryptionByDefault", {}).get(
                "SSEAlgorithm", "?"
            ) if rules else "none"
            checks.append(
                Check(
                    "security",
                    f"S3 default encryption: {bucket}",
                    Status.PASS if rules else Status.FAIL,
                    f"SSE: {algo}",
                    "S3 -> bucket -> Properties -> Default encryption -> SSE-S3 or SSE-KMS",
                )
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ServerSideEncryptionConfigurationNotFoundError":
                checks.append(
                    Check(
                        "security",
                        f"S3 default encryption: {bucket}",
                        Status.FAIL,
                        "No default encryption configured",
                        "Enable default encryption (SSE-S3 is fine for demo)",
                    )
                )
            else:
                checks.append(
                    Check(
                        "security",
                        f"S3 default encryption: {bucket}",
                        Status.WARN,
                        str(exc),
                        "",
                    )
                )

    # IAM sprawl (informational)
    try:
        role_count = 0
        for page in iam.get_paginator("list_roles").paginate():
            role_count += len(page.get("Roles", []))
        policy_count = 0
        for page in iam.get_paginator("list_policies").paginate(Scope="Local"):
            policy_count += len(page.get("Policies", []))
        status = Status.WARN if role_count > 10 or policy_count > 8 else Status.PASS
        checks.append(
            Check(
                "security",
                "IAM sprawl (informational)",
                status,
                f"{role_count} roles, {policy_count} customer-managed policies in account",
                "Delete unused lab roles/policies so the account reads as deliberate",
            )
        )
    except ClientError as exc:
        checks.append(
            Check(
                "security",
                "IAM sprawl (informational)",
                Status.SKIP,
                str(exc),
                "",
            )
        )

    return checks


def check_cost(
    *,
    session: boto3.Session,
    account_id: str,
    lambdas: tuple[str, ...],
    include_ec2: bool,
    ec2_name: str,
) -> list[Check]:
    checks: list[Check] = []
    logs = session.client("logs")
    cw = session.client("cloudwatch", region_name="us-east-1")

    # Billing alarm or budget
    alarm_ok = False
    try:
        paginator = cw.get_paginator("describe_alarms")
        for page in paginator.paginate():
            for alarm in page.get("MetricAlarms", []):
                metric = alarm.get("MetricName", "")
                namespace = alarm.get("Namespace", "")
                if namespace == "AWS/Billing" or metric == "EstimatedCharges":
                    alarm_ok = True
                    break
            if alarm_ok:
                break
    except ClientError:
        pass

    budget_ok = False
    try:
        budgets = session.client("budgets", region_name="us-east-1")
        resp = budgets.describe_budgets(AccountId=account_id)
        budget_ok = bool(resp.get("Budgets"))
    except ClientError:
        pass

    if alarm_ok or budget_ok:
        checks.append(
            Check(
                "cost",
                "Billing alarm or AWS Budget",
                Status.PASS,
                "At least one budget or EstimatedCharges alarm found",
            )
        )
    else:
        checks.append(
            Check(
                "cost",
                "Billing alarm or AWS Budget",
                Status.FAIL,
                "No billing alarm or budget detected (CloudWatch us-east-1 / Budgets API)",
                f"Create a ${int(BUDGET_ALARM_THRESHOLD_USD)} budget alert or "
                "Billing EstimatedCharges CloudWatch alarm",
            )
        )

    # Lambda log retention
    for fn in lambdas:
        group = f"{LAMBDA_LOG_PREFIX}{fn}"
        try:
            resp = logs.describe_log_groups(logGroupNamePrefix=group, limit=1)
            groups = resp.get("logGroups", [])
            if not groups:
                checks.append(
                    Check(
                        "cost",
                        f"Log retention: {fn}",
                        Status.WARN,
                        "Log group not created yet (function never invoked?)",
                        f"After first invoke: aws logs put-retention-policy "
                        f"--log-group-name {group} --retention-in-days 14",
                    )
                )
                continue
            retention = groups[0].get("retentionInDays")
            if retention and retention <= 14:
                checks.append(
                    Check(
                        "cost",
                        f"Log retention: {fn}",
                        Status.PASS,
                        f"{retention} days",
                    )
                )
            else:
                checks.append(
                    Check(
                        "cost",
                        f"Log retention: {fn}",
                        Status.FAIL,
                        f"retention={retention or 'never expire'}",
                        f"aws logs put-retention-policy --log-group-name {group} "
                        f"--retention-in-days 14",
                    )
                )
        except ClientError as exc:
            checks.append(
                Check(
                    "cost",
                    f"Log retention: {fn}",
                    Status.WARN,
                    str(exc),
                    "",
                )
            )

    if include_ec2:
        ec2 = session.client("ec2")
        try:
            resp = ec2.describe_instances(
                Filters=[{"Name": "tag:Name", "Values": [ec2_name]}]
            )
            instances = [
                inst
                for res in resp.get("Reservations", [])
                for inst in res.get("Instances", [])
                if inst.get("State", {}).get("Name") != "terminated"
            ]
            if not instances:
                checks.append(
                    Check(
                        "cost",
                        f"EC2 demo instance ({ec2_name})",
                        Status.SKIP,
                        "No running/stopped instance with that Name tag",
                    )
                )
            else:
                inst = instances[0]
                state = inst.get("State", {}).get("Name", "?")
                profile = inst.get("IamInstanceProfile")
                sgs = inst.get("SecurityGroups", [])
                sg_ids = [g.get("GroupId") for g in sgs]
                checks.append(
                    Check(
                        "cost",
                        f"EC2 instance profile ({ec2_name})",
                        Status.PASS if profile else Status.FAIL,
                        "Instance profile attached" if profile else "No IAM instance profile",
                        "Launch with instance profile - do not embed access keys in Docker/EC2",
                    )
                )
                open_ssh = False
                for sg_id in sg_ids:
                    sg = ec2.describe_security_groups(GroupIds=[sg_id])["SecurityGroups"][0]
                    for perm in sg.get("IpPermissions", []):
                        if perm.get("FromPort") == 22 and perm.get("ToPort") == 22:
                            for rng in perm.get("IpRanges", []):
                                if rng.get("CidrIp") == "0.0.0.0/0":
                                    open_ssh = True
                checks.append(
                    Check(
                        "cost",
                        f"EC2 SSH exposure ({ec2_name})",
                        Status.FAIL if open_ssh else Status.PASS,
                        f"state={state}, open 0.0.0.0/0:22={open_ssh}",
                        "Restrict SG port 22 to your IP; stop instance when idle",
                    )
                )
        except ClientError as exc:
            checks.append(
                Check(
                    "cost",
                    f"EC2 checks ({ec2_name})",
                    Status.WARN,
                    str(exc),
                    "",
                )
            )

    return checks


def check_polish(*, agent: Any, agent_id: str, session: boto3.Session) -> list[Check]:
    checks: list[Check] = []
    bedrock = session.client("bedrock")
    cw = session.client("cloudwatch")

    try:
        cfg = bedrock.get_model_invocation_logging_configuration()
        logging_cfg = cfg.get("loggingConfig", {})
        if logging_cfg.get("cloudWatchConfig") or logging_cfg.get("s3Config"):
            checks.append(
                Check(
                    "polish",
                    "Bedrock model invocation logging",
                    Status.PASS,
                    "Logging destination configured",
                )
            )
        else:
            checks.append(
                Check(
                    "polish",
                    "Bedrock model invocation logging",
                    Status.WARN,
                    "Not configured",
                    "Bedrock -> Settings -> Model invocation logging -> CloudWatch or S3",
                )
            )
    except ClientError as exc:
        checks.append(
            Check(
                "polish",
                "Bedrock model invocation logging",
                Status.WARN,
                str(exc),
                "",
            )
        )

    try:
        meta = agent.get_agent(agentId=agent_id)["agent"]
        guardrail = meta.get("guardrailConfiguration")
        if guardrail and guardrail.get("guardrailIdentifier"):
            checks.append(
                Check(
                    "polish",
                    "Agent guardrail",
                    Status.PASS,
                    f"Guardrail {guardrail.get('guardrailIdentifier')}",
                )
            )
        else:
            checks.append(
                Check(
                    "polish",
                    "Agent guardrail",
                    Status.WARN,
                    "No guardrail on agent (optional for demo)",
                    "Attach a guardrail for 'what works well / next steps' talking point",
                )
            )
    except ClientError as exc:
        checks.append(
            Check(
                "polish",
                "Agent guardrail",
                Status.SKIP,
                str(exc),
                "",
            )
        )

    try:
        resp = cw.list_dashboards()
        names = [d.get("DashboardName", "") for d in resp.get("DashboardEntries", [])]
        piter_dash = [n for n in names if "piter" in n.lower() or "bedrock" in n.lower()]
        if piter_dash:
            checks.append(
                Check(
                    "polish",
                    "CloudWatch dashboard",
                    Status.PASS,
                    f"Found: {', '.join(piter_dash[:3])}",
                )
            )
        elif names:
            checks.append(
                Check(
                    "polish",
                    "CloudWatch dashboard",
                    Status.WARN,
                    f"{len(names)} dashboard(s) exist, none named for PITER/Bedrock",
                    "Optional: tiny dashboard for architecture slide",
                )
            )
        else:
            checks.append(
                Check(
                    "polish",
                    "CloudWatch dashboard",
                    Status.WARN,
                    "No CloudWatch dashboards",
                    "Optional: create a minimal Bedrock/Lambda metrics dashboard",
                )
            )
    except ClientError as exc:
        checks.append(
            Check(
                "polish",
                "CloudWatch dashboard",
                Status.SKIP,
                str(exc),
                "",
            )
        )

    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="PITER AWS readiness checklist")
    parser.add_argument("--profile", default="", help="AWS profile (default: env chain)")
    parser.add_argument("--region", default="", help="AWS region (default: from .env)")
    parser.add_argument("--account-id", default=DEFAULT_ACCOUNT_ID)
    parser.add_argument("--agent-id", default="")
    parser.add_argument("--alias-id", default="")
    parser.add_argument("--kb-id", default="")
    parser.add_argument(
        "--s3-bucket",
        action="append",
        dest="s3_buckets",
        help="S3 bucket to check (repeatable; default: artifacts + logs)",
    )
    parser.add_argument("--include-polish", action="store_true")
    parser.add_argument("--include-ec2", action="store_true")
    parser.add_argument(
        "--strict",
        action="store_true",
        default=True,
        help="Exit 1 on any FAIL in functional/security/cost (default: true)",
    )
    parser.add_argument(
        "--no-strict",
        action="store_false",
        dest="strict",
        help="Always exit 0; print checklist only",
    )
    args = parser.parse_args()

    try:
        cfg = Config.from_env()
    except ConfigError as exc:
        print(f"FAIL: {exc}")
        print("Tip: copy .env.example -> .env or pass --agent-id / --kb-id overrides")
        return 1

    region = args.region or cfg.AWS_REGION
    profile = args.profile or None
    agent_id = args.agent_id or cfg.BEDROCK_AGENT_ID
    alias_id = args.alias_id or cfg.BEDROCK_AGENT_ALIAS_ID
    kb_id = args.kb_id or cfg.BEDROCK_KB_ID
    s3_buckets = tuple(args.s3_buckets) if args.s3_buckets else DEFAULT_S3_BUCKETS

    session = _session(profile, region)
    sts = session.client("sts")
    identity = sts.get_caller_identity()
    account_id = args.account_id or identity.get("Account", DEFAULT_ACCOUNT_ID)
    sts_arn = identity.get("Arn", "")

    print(f"Account: {account_id}  Region: {region}  Profile: {profile or '(default)'}")
    print(f"Agent: {agent_id}/{alias_id}  KB: {kb_id}")
    print("")

    agent = session.client("bedrock-agent")
    lam = session.client("lambda")
    iam = session.client("iam")
    bedrock = session.client("bedrock")

    all_checks: list[Check] = []
    all_checks.extend(
        check_functional(
            agent=agent,
            lam=lam,
            iam=iam,
            bedrock=bedrock,
            account_id=account_id,
            region=region,
            agent_id=agent_id,
            alias_id=alias_id,
            kb_id=kb_id,
            lambdas=DEFAULT_LAMBDAS,
        )
    )
    all_checks.extend(
        check_security(
            session=session,
            iam=iam,
            sts_user=sts_arn,
            s3_buckets=s3_buckets,
        )
    )
    all_checks.extend(
        check_cost(
            session=session,
            account_id=account_id,
            lambdas=DEFAULT_LAMBDAS,
            include_ec2=args.include_ec2,
            ec2_name=DEFAULT_EC2_NAME,
        )
    )
    if args.include_polish:
        all_checks.extend(check_polish(agent=agent, agent_id=agent_id, session=session))

    for check in all_checks:
        _print_check(check)

    passes = sum(1 for c in all_checks if c.status == Status.PASS)
    fails = [c for c in all_checks if c.status == Status.FAIL]
    warns = sum(1 for c in all_checks if c.status == Status.WARN)
    required_fails = [c for c in fails if c.required]

    print("")
    print(f"Summary: {passes} PASS, {len(fails)} FAIL, {warns} WARN, {len(all_checks)} total")
    if required_fails:
        print("Required failures:")
        for c in required_fails:
            print(f"  - [{c.section}] {c.name}")

    if args.strict and required_fails:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
