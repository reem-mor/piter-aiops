"""
PITER AiOps â€” demo data generator.
Produces all CSV/JSON files in data/source with internal consistency.
Run: python scripts/generate_demo_data.py --output data/source
"""

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "source"
OUT = DEFAULT_OUTPUT


def configure_output(path: str | Path | None = None) -> Path:
    global OUT
    OUT = Path(path) if path else DEFAULT_OUTPUT
    if not OUT.is_absolute():
        OUT = (PROJECT_ROOT / OUT).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT

# -------------------------------------------------------------------
# Reference data â€” single source of truth for cross-file consistency
# -------------------------------------------------------------------

NOW = datetime(2026, 6, 6, 9, 30, 0, tzinfo=timezone.utc)

ENVS = ["NJ-DGE", "GIB-UKGC", "MGM", "MIRAGE"]

SERVICES = {
    "wallet-service":   {"team": "Wallet Platform",   "lead": "Sara Levy",      "slack": "#wallet-platform", "pd": "PD-WAL-001",  "primary": "Daniel Cohen", "secondary": "Maya Ben-David"},
    "bet-service":      {"team": "Betting Core",      "lead": "Yossi Avraham",  "slack": "#betting-core",    "pd": "PD-BET-001",  "primary": "Tom Friedman", "secondary": "Liat Goldberg"},
    "auth-service":     {"team": "Identity & Access", "lead": "Noa Shapira",    "slack": "#identity",        "pd": "PD-AUTH-001", "primary": "Roy Katz",     "secondary": "Shira Mizrahi"},
    "payments-service": {"team": "Payments",          "lead": "Eitan Rosen",    "slack": "#payments",        "pd": "PD-PAY-001",  "primary": "Yael Stein",   "secondary": "Amit Levi"},
    "game-service":     {"team": "Game Platform",     "lead": "Itai Bar-On",    "slack": "#game-platform",   "pd": "PD-GAME-001", "primary": "Omer Peretz",  "secondary": "Hila Aviv"},
    "replication":      {"team": "Data Platform",     "lead": "Gilad Weiss",    "slack": "#data-platform",   "pd": "PD-DATA-001", "primary": "Dana Klein",   "secondary": "Adi Yosef"},
}

# -------------------------------------------------------------------
# 1. service_owners.csv
# -------------------------------------------------------------------

def write_service_owners():
    path = OUT / "service_owners.csv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["service","owning_team","team_lead","slack_channel","pagerduty_service_id","primary_on_call","secondary_on_call"])
        for svc, meta in SERVICES.items():
            w.writerow([svc, meta["team"], meta["lead"], meta["slack"], meta["pd"], meta["primary"], meta["secondary"]])
    print(f"wrote {path} ({len(SERVICES)} rows)")

# -------------------------------------------------------------------
# 2. on_call_schedule.csv  â€” 3 weeks of rotation per team
# -------------------------------------------------------------------

def write_on_call_schedule():
    path = OUT / "on_call_schedule.csv"
    # Week 1: 2026-06-02 â†’ 2026-06-08 (current week, primary on call)
    # Week 2: 2026-06-09 â†’ 2026-06-15 (swap)
    # Week 3: 2026-06-16 â†’ 2026-06-22 (back to primary)
    weeks = [
        ("2026-06-02", "2026-06-08"),
        ("2026-06-09", "2026-06-15"),
        ("2026-06-16", "2026-06-22"),
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["team","date_start","date_end","primary","secondary","manager_escalation"])
        for svc, meta in SERVICES.items():
            for i, (start, end) in enumerate(weeks):
                if i % 2 == 0:
                    primary, secondary = meta["primary"], meta["secondary"]
                else:
                    primary, secondary = meta["secondary"], meta["primary"]
                w.writerow([meta["team"], start, end, primary, secondary, meta["lead"]])
    print(f"wrote {path} ({len(SERVICES) * len(weeks)} rows)")

# -------------------------------------------------------------------
# 3. business_impact.json
# -------------------------------------------------------------------

def write_business_impact():
    data = {
        "services": {
            "wallet-service": {
                "revenue_per_minute_usd": 4200,
                "active_users_typical": 12000,
                "sla_target_uptime_pct": 99.95,
                "regulatory_exposure": ["UKGC", "DGE"],
                "p1_cost_per_minute_usd": 4200,
                "p2_cost_per_minute_usd": 1800,
                "p3_cost_per_minute_usd": 400,
                "p4_cost_per_minute_usd": 0,
            },
            "bet-service": {
                "revenue_per_minute_usd": 9800,
                "active_users_typical": 32000,
                "sla_target_uptime_pct": 99.95,
                "regulatory_exposure": ["UKGC", "DGE", "MGM"],
                "p1_cost_per_minute_usd": 9800,
                "p2_cost_per_minute_usd": 4100,
                "p3_cost_per_minute_usd": 800,
                "p4_cost_per_minute_usd": 0,
            },
            "auth-service": {
                "revenue_per_minute_usd": 14000,
                "active_users_typical": 50000,
                "sla_target_uptime_pct": 99.99,
                "regulatory_exposure": ["UKGC", "DGE"],
                "p1_cost_per_minute_usd": 14000,
                "p2_cost_per_minute_usd": 6200,
                "p3_cost_per_minute_usd": 1200,
                "p4_cost_per_minute_usd": 0,
            },
            "payments-service": {
                "revenue_per_minute_usd": 2100,
                "active_users_typical": 4500,
                "sla_target_uptime_pct": 99.9,
                "regulatory_exposure": ["UKGC", "DGE", "PCI-DSS"],
                "p1_cost_per_minute_usd": 2100,
                "p2_cost_per_minute_usd": 900,
                "p3_cost_per_minute_usd": 200,
                "p4_cost_per_minute_usd": 0,
            },
            "game-service": {
                "revenue_per_minute_usd": 6500,
                "active_users_typical": 28000,
                "sla_target_uptime_pct": 99.9,
                "regulatory_exposure": ["UKGC", "DGE", "MGM"],
                "p1_cost_per_minute_usd": 6500,
                "p2_cost_per_minute_usd": 2700,
                "p3_cost_per_minute_usd": 600,
                "p4_cost_per_minute_usd": 0,
            },
            "replication": {
                "revenue_per_minute_usd": 0,
                "active_users_typical": 0,
                "sla_target_uptime_pct": 99.99,
                "regulatory_exposure": ["UKGC", "DGE"],
                "p1_cost_per_minute_usd": 8000,
                "p2_cost_per_minute_usd": 3500,
                "p3_cost_per_minute_usd": 800,
                "p4_cost_per_minute_usd": 0,
                "note": "no direct revenue but underlies wallet, bet, payments"
            },
        }
    }
    path = OUT / "business_impact.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {path} ({len(data['services'])} services)")

# -------------------------------------------------------------------
# 4. priority_matrix.json
# -------------------------------------------------------------------

def write_priority_matrix():
    data = {
        "factors": {
            "customer_impact_pct":     {"weight": 0.30, "description": "% of active users impacted"},
            "revenue_per_minute_usd":  {"weight": 0.25, "description": "estimated $ loss per minute of degradation"},
            "regulatory_exposure":     {"weight": 0.20, "description": "presence of regulated markets (UKGC/DGE/MGM)"},
            "sla_risk":                {"weight": 0.15, "description": "proximity to SLA breach"},
            "alert_frequency":         {"weight": 0.10, "description": "noise vs signal â€” repeated alerts raise priority"},
        },
        "thresholds": {
            "P1": {"customer_impact_pct": ">=20", "revenue_per_minute_usd": ">=5000", "any_regulatory": True,  "description": "Customer-facing outage with revenue and regulatory exposure"},
            "P2": {"customer_impact_pct": ">=5",  "revenue_per_minute_usd": ">=1500", "any_regulatory": False, "description": "Major degradation, single market impacted"},
            "P3": {"customer_impact_pct": ">=1",  "revenue_per_minute_usd": ">=300",  "any_regulatory": False, "description": "Partial degradation, recoverable without escalation"},
            "P4": {"customer_impact_pct": "<1",   "revenue_per_minute_usd": "<300",   "any_regulatory": False, "description": "Minor issue, no customer impact"},
        },
        "examples": [
            {"alert": "wallet-service down on GIB-UKGC", "priority": "P1", "rationale": "100% wallet impact, UKGC regulatory exposure"},
            {"alert": "replication lag 30s on GIB-UKGC wallet", "priority": "P2", "rationale": "degraded but online, single market"},
            {"alert": "slow query on transactions_log", "priority": "P3", "rationale": "elevated latency but no failures"},
            {"alert": "memory 82% on MGM auth-service", "priority": "P4", "rationale": "no user impact, capacity warning"},
        ]
    }
    path = OUT / "priority_matrix.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {path}")

# -------------------------------------------------------------------
# 5. escalation_policies.json
# -------------------------------------------------------------------

def write_escalation_policies():
    data = {
        "default_policy": {
            "P1": {"notify_immediately": ["primary_on_call", "secondary_on_call", "team_lead", "incident_commander"], "max_response_minutes": 5,  "war_room": True},
            "P2": {"notify_immediately": ["primary_on_call", "team_lead"], "max_response_minutes": 15, "war_room": False},
            "P3": {"notify_immediately": ["primary_on_call"], "max_response_minutes": 30, "war_room": False},
            "P4": {"notify_immediately": [], "next_business_day": True, "war_room": False},
        },
        "regulatory_overrides": {
            "UKGC": {
                "P1": {"additional_notify": ["compliance_officer"], "reporting_window_hours": 1,  "report_to": "UKGC Compliance Desk"},
                "P2": {"additional_notify": ["compliance_officer"], "reporting_window_hours": 24, "report_to": "UKGC Compliance Desk"},
            },
            "DGE": {
                "P1": {"additional_notify": ["compliance_officer"], "reporting_window_hours": 4,  "report_to": "NJ-DGE Reporting"},
            },
            "MGM": {
                "P1": {"additional_notify": ["mgm_liaison"], "reporting_window_hours": 2, "report_to": "MGM Operations"},
            }
        },
        "incident_commander_rotation": {
            "2026-W23": {"primary": "Sara Levy",    "backup": "Yossi Avraham"},
            "2026-W24": {"primary": "Eitan Rosen",  "backup": "Noa Shapira"},
            "2026-W25": {"primary": "Itai Bar-On",  "backup": "Gilad Weiss"},
        }
    }
    path = OUT / "escalation_policies.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {path}")

# -------------------------------------------------------------------
# 6. deploys.csv  â€” 7 days, ~50 rows, with the CRITICAL DEMO ROW
# -------------------------------------------------------------------

def write_deploys():
    path = OUT / "deploys.csv"
    rows = []

    # CRITICAL DEMO ROW â€” must exist exactly like this
    rows.append({
        "deploy_id": "DEP-2026-06-06-014",
        "timestamp": "2026-06-06T08:30:00Z",
        "environment": "GIB-UKGC",
        "service": "wallet-service",
        "version": "v4.12.3",
        "deployer": "jenkins-prod",
        "status": "success",
        "rollback_available": "true",
    })

    # supporting deploys around the critical timestamp
    supporting = [
        ("DEP-2026-06-06-013", "2026-06-06T07:15:00Z", "NJ-DGE",  "payments-service", "v2.8.1",  "jenkins-prod",  "success", "true"),
        ("DEP-2026-06-06-012", "2026-06-06T06:50:00Z", "MGM",     "game-service",     "v5.2.4",  "jenkins-prod",  "success", "true"),
        ("DEP-2026-06-06-011", "2026-06-06T05:30:00Z", "MIRAGE",  "auth-service",     "v3.1.0",  "jenkins-prod",  "success", "true"),
        ("DEP-2026-06-05-010", "2026-06-05T22:00:00Z", "GIB-UKGC","bet-service",      "v3.4.0",  "jenkins-prod",  "success", "true"),
        ("DEP-2026-06-05-009", "2026-06-05T17:45:00Z", "NJ-DGE",  "wallet-service",   "v4.12.2", "jenkins-prod",  "success", "true"),
        ("DEP-2026-06-05-008", "2026-06-05T14:20:00Z", "GIB-UKGC","auth-service",     "v3.0.9",  "jenkins-prod",  "success", "true"),
        ("DEP-2026-06-05-007", "2026-06-05T11:10:00Z", "MGM",     "wallet-service",   "v4.12.2", "jenkins-prod",  "success", "true"),
        ("DEP-2026-06-05-006", "2026-06-05T09:30:00Z", "MIRAGE",  "bet-service",      "v3.3.9",  "jenkins-prod",  "success", "true"),
        ("DEP-2026-06-04-005", "2026-06-04T16:00:00Z", "NJ-DGE",  "game-service",     "v5.2.3",  "jenkins-prod",  "failed",  "true"),
        ("DEP-2026-06-04-004", "2026-06-04T15:00:00Z", "NJ-DGE",  "game-service",     "v5.2.2",  "jenkins-prod",  "success", "true"),
        ("DEP-2026-06-04-003", "2026-06-04T10:15:00Z", "GIB-UKGC","payments-service", "v2.7.9",  "jenkins-prod",  "success", "true"),
        ("DEP-2026-06-04-002", "2026-06-04T08:45:00Z", "MGM",     "bet-service",      "v3.3.8",  "jenkins-prod",  "success", "true"),
        ("DEP-2026-06-03-001", "2026-06-03T19:30:00Z", "GIB-UKGC","wallet-service",   "v4.12.1", "jenkins-prod",  "success", "true"),
    ]
    for d in supporting:
        rows.append(dict(zip(["deploy_id","timestamp","environment","service","version","deployer","status","rollback_available"], d)))

    # broader history â€” last 7 days
    history = [
        ("DEP-2026-06-03-X01","2026-06-03T16:00:00Z","NJ-DGE",  "auth-service",     "v3.0.8","jenkins-prod","success","true"),
        ("DEP-2026-06-03-X02","2026-06-03T13:20:00Z","MIRAGE",  "game-service",     "v5.2.1","jenkins-prod","success","true"),
        ("DEP-2026-06-03-X03","2026-06-03T10:05:00Z","GIB-UKGC","game-service",     "v5.2.1","jenkins-prod","success","true"),
        ("DEP-2026-06-03-X04","2026-06-03T08:30:00Z","MGM",     "auth-service",     "v3.0.8","jenkins-prod","success","true"),
        ("DEP-2026-06-02-Y01","2026-06-02T20:00:00Z","NJ-DGE",  "bet-service",      "v3.3.7","jenkins-prod","success","true"),
        ("DEP-2026-06-02-Y02","2026-06-02T17:15:00Z","GIB-UKGC","payments-service", "v2.7.8","jenkins-prod","success","true"),
        ("DEP-2026-06-02-Y03","2026-06-02T14:00:00Z","MGM",     "wallet-service",   "v4.12.0","jenkins-prod","success","true"),
        ("DEP-2026-06-02-Y04","2026-06-02T11:30:00Z","MIRAGE",  "wallet-service",   "v4.12.0","jenkins-prod","success","true"),
        ("DEP-2026-06-02-Y05","2026-06-02T09:00:00Z","NJ-DGE",  "wallet-service",   "v4.12.0","jenkins-prod","success","true"),
        ("DEP-2026-06-01-Z01","2026-06-01T18:30:00Z","GIB-UKGC","auth-service",     "v3.0.7","jenkins-prod","success","true"),
        ("DEP-2026-06-01-Z02","2026-06-01T15:45:00Z","MGM",     "payments-service", "v2.7.7","jenkins-prod","success","true"),
        ("DEP-2026-06-01-Z03","2026-06-01T12:10:00Z","NJ-DGE",  "game-service",     "v5.2.0","jenkins-prod","success","true"),
        ("DEP-2026-06-01-Z04","2026-06-01T09:30:00Z","MIRAGE",  "bet-service",      "v3.3.6","jenkins-prod","success","true"),
        ("DEP-2026-05-31-A01","2026-05-31T16:00:00Z","GIB-UKGC","bet-service",      "v3.3.6","jenkins-prod","success","true"),
        ("DEP-2026-05-31-A02","2026-05-31T13:20:00Z","MGM",     "auth-service",     "v3.0.6","jenkins-prod","success","true"),
        ("DEP-2026-05-31-A03","2026-05-31T10:00:00Z","NJ-DGE",  "payments-service", "v2.7.6","jenkins-prod","success","true"),
        ("DEP-2026-05-30-B01","2026-05-30T17:30:00Z","MIRAGE",  "auth-service",     "v3.0.5","jenkins-prod","success","true"),
        ("DEP-2026-05-30-B02","2026-05-30T14:15:00Z","GIB-UKGC","wallet-service",   "v4.11.9","jenkins-prod","success","true"),
        ("DEP-2026-05-30-B03","2026-05-30T11:00:00Z","NJ-DGE",  "auth-service",     "v3.0.5","jenkins-prod","success","true"),
        ("DEP-2026-05-30-B04","2026-05-30T08:30:00Z","MGM",     "game-service",     "v5.1.9","jenkins-prod","success","true"),
        ("DEP-2026-05-29-C01","2026-05-29T19:00:00Z","GIB-UKGC","game-service",     "v5.1.9","jenkins-prod","success","true"),
        ("DEP-2026-05-29-C02","2026-05-29T16:30:00Z","MIRAGE",  "payments-service", "v2.7.5","jenkins-prod","success","true"),
        ("DEP-2026-05-29-C03","2026-05-29T13:00:00Z","NJ-DGE",  "wallet-service",   "v4.11.9","jenkins-prod","success","true"),
        ("DEP-2026-05-29-C04","2026-05-29T10:15:00Z","MGM",     "bet-service",      "v3.3.5","jenkins-prod","success","true"),
        ("DEP-2026-05-29-C05","2026-05-29T08:00:00Z","GIB-UKGC","auth-service",     "v3.0.4","jenkins-prod","success","true"),
        ("DEP-2026-05-28-D01","2026-05-28T18:45:00Z","NJ-DGE",  "bet-service",      "v3.3.5","jenkins-prod","success","true"),
        ("DEP-2026-05-28-D02","2026-05-28T15:30:00Z","MIRAGE",  "wallet-service",   "v4.11.9","jenkins-prod","success","true"),
        ("DEP-2026-05-28-D03","2026-05-28T12:00:00Z","MGM",     "payments-service", "v2.7.5","jenkins-prod","success","true"),
        ("DEP-2026-05-28-D04","2026-05-28T09:30:00Z","GIB-UKGC","game-service",     "v5.1.8","jenkins-prod","success","true"),
    ]
    for d in history:
        rows.append(dict(zip(["deploy_id","timestamp","environment","service","version","deployer","status","rollback_available"], d)))

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["deploy_id","timestamp","environment","service","version","deployer","status","rollback_available"])
        w.writeheader()
        # sort newest first
        rows_sorted = sorted(rows, key=lambda r: r["timestamp"], reverse=True)
        w.writerows(rows_sorted)
    print(f"wrote {path} ({len(rows)} rows)")

# -------------------------------------------------------------------
# 7. alerts.csv  â€” current and recent alerts, includes the demo alert
# -------------------------------------------------------------------

def write_alerts():
    path = OUT / "alerts.csv"
    # THE DEMO ALERT must exist exactly like this
    rows = [
        # active demo storyline â€” GIB-UKGC wallet-service replication lag
        ("ALT-2026-06-06-001","2026-06-06T09:14:22Z","GIB-UKGC","wallet-service","P2","Replication lag exceeded 30s threshold","active","12000","2.4"),
        ("ALT-2026-06-06-002","2026-06-06T09:11:03Z","GIB-UKGC","wallet-service","P3","Slow query detected on transactions_log","acknowledged","12000","0.8"),
        ("ALT-2026-06-06-003","2026-06-06T09:08:45Z","GIB-UKGC","replication",   "P3","Replica node lag warning","active","0","0.0"),

        # other current alerts across envs/services for realism
        ("ALT-2026-06-06-004","2026-06-06T08:42:11Z","NJ-DGE",  "payments-service","P3","Payment gateway latency p95 > 2s","active","4500","1.1"),
        ("ALT-2026-06-06-005","2026-06-06T08:18:55Z","MGM",     "auth-service",    "P4","Memory utilization 82%","resolved","0","0.0"),
        ("ALT-2026-06-06-006","2026-06-06T07:55:30Z","GIB-UKGC","bet-service",     "P4","Connection pool 75% utilized","acknowledged","0","0.0"),
        ("ALT-2026-06-06-007","2026-06-06T07:22:18Z","MIRAGE",  "game-service",    "P3","Elevated 4xx response rate","resolved","2200","3.1"),
        ("ALT-2026-06-06-008","2026-06-06T06:48:09Z","NJ-DGE",  "auth-service",    "P4","Certificate expiring in 30 days","active","0","0.0"),
        ("ALT-2026-06-06-009","2026-06-06T05:30:42Z","MGM",     "wallet-service",  "P3","Cache hit rate dropped to 78%","resolved","8500","0.2"),
        ("ALT-2026-06-06-010","2026-06-06T04:15:11Z","GIB-UKGC","game-service",    "P4","Background job queue depth high","resolved","0","0.0"),

        # yesterday and earlier â€” variety for the analytics panel
        ("ALT-2026-06-05-011","2026-06-05T22:10:33Z","NJ-DGE",  "bet-service",     "P2","Failed bet processing rate > 2%","resolved","18000","3.4"),
        ("ALT-2026-06-05-012","2026-06-05T19:45:22Z","MIRAGE",  "payments-service","P3","Deposit success rate dropped","resolved","2100","2.8"),
        ("ALT-2026-06-05-013","2026-06-05T16:22:08Z","GIB-UKGC","wallet-service",  "P3","Slow transaction commits","resolved","11500","0.9"),
        ("ALT-2026-06-05-014","2026-06-05T13:00:45Z","MGM",     "game-service",    "P2","Game state sync delay","resolved","19000","4.2"),
        ("ALT-2026-06-05-015","2026-06-05T10:30:11Z","NJ-DGE",  "wallet-service",  "P4","Disk usage at 78%","resolved","0","0.0"),
        ("ALT-2026-06-04-016","2026-06-04T15:15:00Z","NJ-DGE",  "game-service",    "P1","Service down on 2 of 4 nodes","resolved","28000","18.7"),
        ("ALT-2026-06-04-017","2026-06-04T11:42:30Z","GIB-UKGC","auth-service",    "P3","Login latency spike","resolved","48000","1.5"),
        ("ALT-2026-06-03-018","2026-06-03T20:18:22Z","MIRAGE",  "bet-service",     "P3","Bet acceptance latency increased","resolved","9000","2.0"),
        ("ALT-2026-06-03-019","2026-06-03T14:30:00Z","MGM",     "payments-service","P2","Withdrawal processing delayed","resolved","3800","4.5"),
        ("ALT-2026-06-02-020","2026-06-02T18:00:11Z","GIB-UKGC","game-service",    "P3","Asset CDN latency increased","resolved","26000","0.7"),
        ("ALT-2026-06-02-021","2026-06-02T09:15:33Z","NJ-DGE",  "replication",     "P4","Backup job took longer than usual","resolved","0","0.0"),
        ("ALT-2026-06-01-022","2026-06-01T16:45:00Z","MIRAGE",  "auth-service",    "P3","Session validation errors","resolved","45000","1.3"),
        ("ALT-2026-06-01-023","2026-06-01T12:08:18Z","GIB-UKGC","bet-service",     "P4","Slack notification webhook failed","resolved","0","0.0"),
        ("ALT-2026-05-31-024","2026-05-31T22:30:55Z","MGM",     "wallet-service",  "P2","Transaction commit timeouts","resolved","9200","3.8"),
        ("ALT-2026-05-31-025","2026-05-31T11:00:00Z","NJ-DGE",  "payments-service","P3","Refund processing slow","resolved","4100","1.8"),
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["alert_id","timestamp","environment","service","severity","title","status","affected_users","error_rate_pct"])
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")

# -------------------------------------------------------------------
# 8. past_incidents.csv â€” 12 months of resolved incidents
# -------------------------------------------------------------------

def write_past_incidents():
    path = OUT / "past_incidents.csv"
    # THE CRITICAL "SIMILAR INCIDENT" â€” must exist exactly like this
    rows = [
        ("INC-2025-11-04","2025-11-04","NJ-DGE","wallet-service","P2","Replication lag after wallet deploy",
         "replication lag>30s; transaction commit delays",
         "v4.10.1 introduced unindexed query on transactions_log",
         "rolled back to v4.9.8 then deployed fixed v4.10.2",
         "28","replication"),

        # Other incidents â€” 12 month history, varied
        ("INC-2025-09-22","2025-09-22","GIB-UKGC","payments-service","P1","Payment gateway timeouts",
         "payment_failures>5%; gateway latency>5s",
         "upstream provider partial outage",
         "switched to secondary payment provider, root cause resolved upstream",
         "42","payments"),
        ("INC-2026-01-15","2026-01-15","MGM","wallet-service","P3","Transaction log disk 95% full",
         "disk_space critical alert; log writes slowing",
         "log rotation cron job failed silently for 6 days",
         "manual log rotation; fixed cron monitoring",
         "18","disk"),
        ("INC-2026-03-08","2026-03-08","GIB-UKGC","auth-service","P2","Auth latency p95>2s",
         "login latency spike; session timeouts",
         "connection pool exhausted after traffic surge",
         "increased pool size from 50 to 200; restart",
         "22","auth"),
        ("INC-2026-05-12","2026-05-12","NJ-DGE","bet-service","P2","Failed deploy caused 5xx spike",
         "5xx_rate>10% immediately after deploy",
         "missing schema migration in v3.3.9",
         "rolled back to v3.3.8; migration applied; v3.3.9 redeployed",
         "15","deploys"),
        ("INC-2025-12-19","2025-12-19","GIB-UKGC","wallet-service","P2","Replication lag during high traffic",
         "replication lag>45s; transaction commit delays",
         "traffic surge during promotional event overwhelmed replica",
         "added read replica; tuned replication batch size",
         "35","replication"),
        ("INC-2026-02-04","2026-02-04","MGM","game-service","P1","Game state desync across nodes",
         "player state inconsistency; complaints spiked",
         "cache invalidation race condition",
         "deployed hotfix v5.1.3; manual state reconciliation",
         "55","game"),
        ("INC-2025-10-11","2025-10-11","NJ-DGE","auth-service","P3","Slow password reset emails",
         "email delivery delayed by 5-10 min",
         "SMTP provider rate limiting",
         "increased email provider tier; added retry queue",
         "30","auth"),
        ("INC-2026-04-22","2026-04-22","GIB-UKGC","payments-service","P2","Deposit success rate dropped",
         "deposit_success_rate dropped from 96% to 78%",
         "payment provider certificate near expiry triggered cautious rejections",
         "rotated certificate; engaged provider support",
         "48","payments"),
        ("INC-2025-08-30","2025-08-30","MIRAGE","bet-service","P2","Bet acceptance latency",
         "p95 bet placement latency increased to 3.5s",
         "database stats stale after schema change",
         "ran ANALYZE on affected tables; latency normalized",
         "40","performance"),
        ("INC-2025-11-28","2025-11-28","NJ-DGE","wallet-service","P3","Cache stampede on warm-up",
         "elevated DB load on service restart",
         "no cache warming on deploy",
         "added cache pre-warming step to deploy pipeline",
         "20","deploys"),
        ("INC-2026-03-30","2026-03-30","MGM","auth-service","P3","Memory leak in session handler",
         "memory utilization climbing 3%/hour",
         "session objects not GC'd after timeout",
         "deployed fixed session cleanup logic",
         "65","memory"),
        ("INC-2025-09-08","2025-09-08","GIB-UKGC","game-service","P2","Asset CDN cache miss storm",
         "asset latency p95>5s; player experience degraded",
         "CDN purge after deploy invalidated all assets simultaneously",
         "phased CDN purge; warmed cache before traffic peak",
         "32","performance"),
        ("INC-2026-04-05","2026-04-05","NJ-DGE","replication","P2","Mirror failover required",
         "primary DB node unresponsive",
         "underlying EBS volume degraded",
         "promoted mirror to primary; AWS replaced volume",
         "12","replication"),
        ("INC-2025-12-02","2025-12-02","MIRAGE","payments-service","P3","Refund queue backlog",
         "refund processing delayed by 30 min",
         "worker pod OOM-killed twice",
         "increased pod memory limits; added autoscaling",
         "45","capacity"),
        ("INC-2026-01-22","2026-01-22","GIB-UKGC","bet-service","P1","Bet placement outage",
         "bet placement failing for 12 minutes",
         "DB connection exhaustion after dependency timeout",
         "restarted service; added connection pool circuit breaker",
         "12","outage"),
        ("INC-2025-07-15","2025-07-15","MGM","wallet-service","P3","Slow withdrawals",
         "withdrawal processing p95>10s",
         "third-party identity verification slow",
         "added timeout + fallback verification path",
         "55","performance"),
        ("INC-2026-02-17","2026-02-17","NJ-DGE","game-service","P3","Sporadic game freezes",
         "intermittent freezes for ~2% of sessions",
         "WebSocket library bug under load",
         "patched library; deployed across env",
         "70","game"),
        ("INC-2025-10-28","2025-10-28","GIB-UKGC","auth-service","P2","Login failures regional",
         "logins failing only from EU traffic",
         "regional CDN config drift",
         "reverted CDN config; added drift detection",
         "25","auth"),
        ("INC-2026-05-29","2026-05-29","MGM","bet-service","P3","Bet history query slow",
         "history page loads >8s",
         "missing index on user_id+timestamp",
         "added composite index; query time 200ms",
         "38","performance"),
        ("INC-2025-08-12","2025-08-12","MIRAGE","wallet-service","P2","Duplicate transaction risk",
         "idempotency key collision warning",
         "key generation collision under high concurrency",
         "switched to UUIDv7; replayed audit logs",
         "50","data-integrity"),
        ("INC-2026-03-19","2026-03-19","NJ-DGE","payments-service","P2","Withdrawal rejection spike",
         "12% withdrawal rejection rate",
         "fraud rules deployed without staging review",
         "rolled back rules; manual review queue cleared",
         "28","deploys"),
        ("INC-2025-11-15","2025-11-15","GIB-UKGC","replication","P3","Replica restart loop",
         "replica node restarted 4 times in 1 hour",
         "OOM after schema change increased row size",
         "tuned innodb_buffer_pool_size; restored stability",
         "60","replication"),
        ("INC-2026-04-12","2026-04-12","MGM","game-service","P2","Leaderboard not updating",
         "leaderboard stale by 15+ minutes",
         "Redis cluster split-brain after network blip",
         "re-elected primary; reduced failover timeout",
         "33","game"),
        ("INC-2025-09-30","2025-09-30","MIRAGE","auth-service","P3","2FA SMS delays",
         "2FA SMS delivery >2 min for 8% of users",
         "SMS provider degradation in EU region",
         "failed over to backup SMS provider",
         "42","auth"),
        ("INC-2026-01-08","2026-01-08","NJ-DGE","wallet-service","P3","Inconsistent balance display",
         "balances briefly displayed stale values",
         "cache TTL too long after balance update",
         "reduced TTL to 5s; added cache invalidation on write",
         "26","data-integrity"),
        ("INC-2025-12-12","2025-12-12","GIB-UKGC","payments-service","P3","Failed deposit retries piling up",
         "retry queue at 10x normal depth",
         "downstream provider 502s; retry logic too aggressive",
         "exponential backoff implemented",
         "44","payments"),
        ("INC-2026-05-03","2026-05-03","MGM","auth-service","P3","Account lockout spike",
         "account lockouts 3x normal rate",
         "bot scanning campaign detected",
         "WAF rule deployed; IP block list updated",
         "30","security"),
        ("INC-2025-08-25","2025-08-25","NJ-DGE","bet-service","P2","Bet limits not enforced",
         "responsible-gaming limit checks bypassed",
         "race condition between limit check and bet placement",
         "added distributed lock on player ID",
         "45","data-integrity"),
        ("INC-2026-02-26","2026-02-26","GIB-UKGC","game-service","P1","Slot game crash regional",
         "specific slot game crashing 100% of plays in EU",
         "incompatible asset version cached at EU CDN",
         "purged CDN cache; emergency hotfix",
         "18","game"),
        ("INC-2025-10-04","2025-10-04","MIRAGE","wallet-service","P3","Slow KYC document upload",
         "document upload latency p95>15s",
         "S3 multipart upload misconfigured",
         "fixed multipart threshold and concurrency",
         "55","performance"),
        ("INC-2026-03-11","2026-03-11","NJ-DGE","game-service","P3","Tournament leaderboard reset",
         "leaderboard reset to zero for 4 minutes",
         "Redis key collision during deploy",
         "fixed key namespacing; restored from backup",
         "28","game"),
        ("INC-2025-11-20","2025-11-20","MGM","replication","P2","Replication broken to read replica",
         "replica diverged from primary",
         "long-running transaction held lock through replication restart",
         "rebuilt replica from snapshot",
         "90","replication"),
        ("INC-2026-04-30","2026-04-30","GIB-UKGC","bet-service","P3","Cashout calculation off by cents",
         "small rounding errors in cashout amounts",
         "floating-point arithmetic in cashout calculation",
         "moved to fixed-point decimal; audit pass clean",
         "35","data-integrity"),
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["incident_id","date","environment","service","severity","title","symptoms","root_cause","resolution","mttr_minutes","similar_alerts"])
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")

# -------------------------------------------------------------------
# 9. Sanity / consistency checks
# -------------------------------------------------------------------

def consistency_checks():
    print("\n--- consistency checks ---")
    # 1. Demo alert exists
    with open(OUT/"alerts.csv") as f:
        assert any("ALT-2026-06-06-001" in line for line in f), "missing demo alert"
    # 2. Demo deploy exists and predates alert
    with open(OUT/"deploys.csv") as f:
        deploy_lines = f.readlines()
    assert any("DEP-2026-06-06-014" in line and "2026-06-06T08:30:00Z" in line and "wallet-service" in line and "GIB-UKGC" in line
               for line in deploy_lines), "missing critical demo deploy"
    # 3. Similar incident exists
    with open(OUT/"past_incidents.csv") as f:
        assert any("INC-2025-11-04" in line for line in f), "missing similar incident"
    # 4. Service owners covers every service in alerts/deploys
    with open(OUT/"service_owners.csv") as f:
        owners = {row["service"] for row in csv.DictReader(f)}
    assert owners >= set(SERVICES.keys()), "service_owners.csv missing services"
    # 5. Business impact covers same services
    with open(OUT/"business_impact.json") as f:
        bi = json.load(f)
    assert set(bi["services"].keys()) >= set(SERVICES.keys()), "business_impact.json missing services"
    print("all checks passed")

# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate canonical PITER AiOps source data")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output directory for generated CSV/JSON files. Defaults to data/source.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_output(args.output)
    write_service_owners()
    write_on_call_schedule()
    write_business_impact()
    write_priority_matrix()
    write_escalation_policies()
    write_deploys()
    write_alerts()
    write_past_incidents()
    consistency_checks()
    print(f"\nall files written to {OUT}/")


if __name__ == "__main__":
    main()

