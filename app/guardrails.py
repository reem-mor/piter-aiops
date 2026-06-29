"""Runtime guardrails for operator questions and dangerous remediation requests."""
from __future__ import annotations

import re

from app.errors import BedrockError

# Destructive or high-blast-radius actions — block unless user explicitly asks for review only.
_DANGEROUS_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(
            r"\b(flushall|flushdb|drop\s+database|drop\s+table|truncate\s+table|"
            r"delete\s+from\s+\w+|rm\s+-rf|format\s+disk|wipe\s+data)\b",
            re.I,
        ),
        "destructive_data_action",
        "That request involves destructive data operations. PITER will not provide "
        "execution steps for FLUSHALL, DROP, TRUNCATE, or mass deletes. "
        "Escalate to the database owner and follow the approved runbook with change control.",
    ),
    (
        re.compile(
            r"\b(promote\s+replica|failover\s+primary|force\s+failover|"
            r"take\s+primary\s+offline|disable\s+replication)\b",
            re.I,
        ),
        "unsafe_failover_action",
        "Failover and replica promotion require explicit approval from the platform "
        "SRE and database owner. PITER can explain the runbook criteria but will not "
        "auto-recommend production failover without cited evidence and human sign-off.",
    ),
    (
        re.compile(
            r"\b(disable\s+waf|turn\s+off\s+waf|remove\s+rate\s+limit|"
            r"open\s+firewall|0\.0\.0\.0/0|disable\s+mfa|bypass\s+auth)\b",
            re.I,
        ),
        "security_control_bypass",
        "Disabling WAF, MFA, auth, or widening firewall rules is not permitted through "
        "this assistant. Open a security-reviewed change request if policy allows an exception.",
    ),
    (
        re.compile(
            r"\b(kill\s+all\s+sessions|terminate\s+all|pg_terminate_backend\s*\(\s*\)|"
            r"restart\s+all\s+pods|scale\s+to\s+zero)\b",
            re.I,
        ),
        "mass_disruption_action",
        "Mass session termination or fleet-wide restarts can cause cascading outages. "
        "Use targeted remediation from the cited runbook and confirm blast radius with on-call.",
    ),
)

# Requests to bypass PITER safety / notification gates.
_POLICY_BYPASS_PATTERNS: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (
        re.compile(
            r"\b(skip\s+confirmation|bypass\s+allowlist|ignore\s+allowlist|"
            r"send\s+without\s+token|disable\s+guardrail|turn\s+off\s+safety)\b",
            re.I,
        ),
        "policy_bypass_request",
        "Notification and escalation safety gates cannot be bypassed from chat. "
        "Use the Escalate on-call flow with a valid confirmation token and allowlisted recipient.",
    ),
    (
        re.compile(
            r"\b(remove\s+escalation|cancel\s+all\s+alerts|silence\s+all|"
            r"delete\s+incident|purge\s+audit)\b",
            re.I,
        ),
        "audit_or_escalation_tamper",
        "PITER cannot remove audit trails, silence all alerts, or delete incidents. "
        "Use approved incident management tools and document actions in the ticket.",
    ),
)


def check_operator_guardrails(question: str) -> None:
    """Raise BedrockError when the question requests disallowed operational actions."""
    text = (question or "").strip()
    if not text:
        return
    for patterns in (_DANGEROUS_PATTERNS, _POLICY_BYPASS_PATTERNS):
        for pattern, code, message in patterns:
            if pattern.search(text):
                raise BedrockError(message, code=code)
