"""
PITER AiOps — alert storm generator for the live demo.

Generates ~400 alerts distributed over 5 minutes (300 seconds) of demo time.
Most are P3/P4 noise. A single P1 fires at T+175 seconds to trigger the
"stop and show" PITER workflow with SMS/email escalation.

Output: data/source/alert_stream.csv with a `seconds_offset` column the Flask
streaming endpoint uses to emit alerts at the right pace.
"""

import argparse
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "source"
DEFAULT_SEED = 42
OUT = DEFAULT_OUTPUT


def configure_output(path: str | Path | None = None) -> Path:
    global OUT
    OUT = Path(path) if path else DEFAULT_OUTPUT
    if not OUT.is_absolute():
        OUT = (PROJECT_ROOT / OUT).resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    return OUT

# Demo day baseline timestamp (presentation: June 10, 2026, 10:00 AM UTC)
DEMO_START = datetime(2026, 6, 10, 10, 0, 0, tzinfo=timezone.utc)
DEMO_DURATION_SECONDS = 300  # 5 minutes
TOTAL_ALERTS = 400

# Random seed for reproducibility — same alerts every demo run

# ---------------------------------------------------------------
# P1 trigger — must fire at exactly T+175s with this exact content
# ---------------------------------------------------------------
P1_OFFSET_SECONDS = 175
P1_ALERT = {
    "alert_id": "ALT-DEMO-P1-001",
    "seconds_offset": P1_OFFSET_SECONDS,
    "environment": "GIB-UKGC",
    "service": "bet-service",
    "severity": "P1",
    "title": "CRITICAL: bet-service nodes unresponsive — 100% error rate on GIB-UKGC",
    "status": "active",
    "affected_users": 32000,
    "error_rate_pct": 100.0,
    "is_trigger": "true",
}

# ---------------------------------------------------------------
# Severity distribution targets (excluding the P1 trigger)
# ---------------------------------------------------------------
SEVERITY_MIX = {
    "P4": 0.70,   # ~279 noise
    "P3": 0.22,   # ~88
    "P2": 0.08,   # ~32
}

# ---------------------------------------------------------------
# Services & environments
# ---------------------------------------------------------------
SERVICES = ["wallet-service", "bet-service", "auth-service",
            "payments-service", "game-service", "replication"]
ENVIRONMENTS = ["NJ-DGE", "GIB-UKGC", "MGM", "MIRAGE"]

# ---------------------------------------------------------------
# Alert title templates — realistic NOC noise
# ---------------------------------------------------------------
P4_TEMPLATES = [
    "{service} memory utilization {n}%",
    "{service} certificate expiring in {n} days",
    "Background job queue depth at {n}",
    "{service} cache hit rate {n}%",
    "Connection pool {n}% utilized",
    "Log rotation completed on {service}",
    "Slow query detected ({n}ms) on {service}",
    "Disk usage at {n}% on {service}",
    "GC pause {n}ms on {service}",
    "Health check warning: {service} response time {n}ms",
    "DNS resolution intermittent for {service}",
    "Auto-scaling event triggered for {service}",
    "Webhook delivery retried for {service}",
    "TLS handshake duration elevated for {service}",
    "{service} backup completed in {n}s",
]

P3_TEMPLATES = [
    "{service} latency p95 increased to {n}s",
    "Elevated 4xx response rate on {service}",
    "Slow transaction commits on {service}",
    "{service} cache hit rate dropped to {n}%",
    "Connection pool exhausted briefly on {service}",
    "Replication lag {n}s on {service}",
    "Failed login rate increased on {service}",
    "{service} read replica falling behind",
    "Queue depth elevated on {service}",
    "Memory pressure on {service} ({n}%)",
    "Intermittent timeouts to upstream on {service}",
    "Failed deploy on staging for {service}",
]

P2_TEMPLATES = [
    "{service} 5xx rate above 2% ({n}%)",
    "Failed transaction rate {n}% on {service}",
    "Deposit success rate dropped to {n}%",
    "{service} sync delay exceeding SLA",
    "Payment gateway latency >3s on {service}",
    "Replication lag exceeded 30s threshold on {service}",
    "Authentication failures spike on {service}",
    "{service} circuit breaker tripped briefly",
]

# ---------------------------------------------------------------
# Narrative warning shots — P3/P2 alerts on bet-service GIB-UKGC
# leading up to the P1 trigger. These build dramatic tension.
# ---------------------------------------------------------------
WARNING_SHOTS = [
    # T+90s: first weak signal
    {"seconds_offset": 90, "environment": "GIB-UKGC", "service": "bet-service",
     "severity": "P3", "title": "bet-service latency p95 increased to 2.4s",
     "status": "active", "affected_users": 32000, "error_rate_pct": 0.8},
    # T+125s: second signal
    {"seconds_offset": 125, "environment": "GIB-UKGC", "service": "bet-service",
     "severity": "P3", "title": "Connection pool exhausted briefly on bet-service",
     "status": "active", "affected_users": 32000, "error_rate_pct": 1.4},
    # T+155s: escalating warning
    {"seconds_offset": 155, "environment": "GIB-UKGC", "service": "bet-service",
     "severity": "P2", "title": "bet-service 5xx rate above 2% (3.8%)",
     "status": "active", "affected_users": 32000, "error_rate_pct": 3.8},
    # T+170s: last warning before the crash
    {"seconds_offset": 170, "environment": "GIB-UKGC", "service": "bet-service",
     "severity": "P2", "title": "bet-service circuit breaker tripped briefly",
     "status": "active", "affected_users": 32000, "error_rate_pct": 7.2},
    # T+175s: THE P1 (added separately, not here)
]

def gen_title(severity, service):
    if severity == "P4":
        tpl = random.choice(P4_TEMPLATES)
        n = random.choice([45, 52, 58, 65, 70, 75, 78, 82, 85, 200, 350, 500, 750, 1200])
        return tpl.format(service=service, n=n)
    if severity == "P3":
        tpl = random.choice(P3_TEMPLATES)
        n = random.choice([1.2, 1.5, 1.8, 2.1, 2.4, 3.0, 3.5, 8, 12, 18, 65, 70, 75])
        return tpl.format(service=service, n=n)
    if severity == "P2":
        tpl = random.choice(P2_TEMPLATES)
        n = random.choice([2.1, 2.4, 2.8, 3.2, 3.5, 4.1, 88, 90])
        return tpl.format(service=service, n=n)
    return "Unknown alert"

def gen_affected_users(severity):
    if severity == "P4":
        return 0  # P4 is operational noise, no user impact
    if severity == "P3":
        return random.choice([0, 0, 1500, 4500, 8000, 12000])
    if severity == "P2":
        return random.choice([4500, 8000, 12000, 18000, 28000])
    return 0

def gen_error_rate(severity):
    if severity == "P4":
        return 0.0
    if severity == "P3":
        return round(random.uniform(0.2, 1.5), 2)
    if severity == "P2":
        return round(random.uniform(1.8, 4.5), 2)
    return 0.0

def gen_status(severity, seconds_offset):
    # Older P4 alerts more likely auto-resolved; P2 stay active
    if severity == "P4":
        return random.choices(["active", "auto-resolved", "acknowledged"],
                              weights=[0.3, 0.5, 0.2])[0]
    if severity == "P3":
        return random.choices(["active", "acknowledged"], weights=[0.7, 0.3])[0]
    return "active"

def gen_inter_arrival_seconds():
    """Bursty arrivals: exponential with occasional bursts."""
    if random.random() < 0.05:
        return random.uniform(0.05, 0.15)  # burst (rapid)
    return random.expovariate(1.0 / 0.75)  # mean 0.75s

# ---------------------------------------------------------------
# Generate the stream
# ---------------------------------------------------------------

def generate():
    rows = []
    counter = 1

    # Reserve narrative slots so we don't overlap them with random alerts
    reserved_offsets = {ws["seconds_offset"] for ws in WARNING_SHOTS} | {P1_OFFSET_SECONDS}

    # Generate background alerts with bursty arrival until we fill the window
    t = 0.0
    while t < DEMO_DURATION_SECONDS and counter < TOTAL_ALERTS - len(WARNING_SHOTS) - 1:
        # Skip if we land too close to a reserved narrative slot (keep them clean)
        if any(abs(t - r) < 1.5 for r in reserved_offsets):
            t += 2.0
            continue

        severity = random.choices(list(SEVERITY_MIX.keys()),
                                  weights=list(SEVERITY_MIX.values()))[0]
        # Suppress bet-service GIB-UKGC P2/P3 from random stream BEFORE T+175
        # so narrative warning shots stay distinct
        service = random.choice(SERVICES)
        env = random.choice(ENVIRONMENTS)
        if t < P1_OFFSET_SECONDS and severity in ("P2", "P3") and service == "bet-service" and env == "GIB-UKGC":
            severity = "P4"  # downgrade to noise

        rows.append({
            "alert_id": f"ALT-DEMO-{counter:04d}",
            "seconds_offset": round(t, 2),
            "environment": env,
            "service": service,
            "severity": severity,
            "title": gen_title(severity, service),
            "status": gen_status(severity, t),
            "affected_users": gen_affected_users(severity),
            "error_rate_pct": gen_error_rate(severity),
            "is_trigger": "false",
        })
        counter += 1
        t += gen_inter_arrival_seconds()

    # Inject narrative warning shots
    for ws in WARNING_SHOTS:
        rows.append({
            "alert_id": f"ALT-DEMO-WARN-{WARNING_SHOTS.index(ws)+1:02d}",
            "seconds_offset": ws["seconds_offset"],
            "environment": ws["environment"],
            "service": ws["service"],
            "severity": ws["severity"],
            "title": ws["title"],
            "status": ws["status"],
            "affected_users": ws["affected_users"],
            "error_rate_pct": ws["error_rate_pct"],
            "is_trigger": "false",
        })

    # Inject the P1 trigger
    rows.append(P1_ALERT)

    # Sort by seconds_offset so the stream replays in chronological order
    rows.sort(key=lambda r: r["seconds_offset"])

    # Convert seconds_offset to actual timestamps anchored to demo start
    for r in rows:
        ts = DEMO_START + timedelta(seconds=r["seconds_offset"])
        r["timestamp"] = ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")[:-4] + "Z"

    return rows

def write_stream(rows):
    path = OUT / "alert_stream.csv"
    fieldnames = ["alert_id", "seconds_offset", "timestamp", "environment",
                  "service", "severity", "title", "status",
                  "affected_users", "error_rate_pct", "is_trigger"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return path

def summary(rows):
    by_sev = {}
    for r in rows:
        by_sev[r["severity"]] = by_sev.get(r["severity"], 0) + 1
    print(f"\nTotal alerts: {len(rows)}")
    print(f"Window: T+0 to T+{DEMO_DURATION_SECONDS}s")
    print("Severity mix:")
    for s in ["P1", "P2", "P3", "P4"]:
        n = by_sev.get(s, 0)
        pct = 100.0 * n / len(rows)
        print(f"  {s}: {n:>4} ({pct:5.1f}%)")

    p1s = [r for r in rows if r["severity"] == "P1"]
    print("\nP1 trigger:")
    for r in p1s:
        print(f"  {r['alert_id']} at T+{r['seconds_offset']}s — {r['service']} on {r['environment']}")
        print(f"    {r['title']}")

    warn = [r for r in rows if "WARN" in r["alert_id"]]
    print(f"\nNarrative warning shots ({len(warn)}):")
    for r in warn:
        print(f"  T+{r['seconds_offset']:>3}s  [{r['severity']}]  {r['title']}")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate deterministic PITER AiOps alert stream data")
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help="Output directory for alert_stream.csv. Defaults to data/source.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="Random seed for reproducible alert streams.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    configure_output(args.output)
    random.seed(args.seed)
    rows = generate()
    path = write_stream(rows)
    summary(rows)
    print(f"\nwrote {path}")


if __name__ == "__main__":
    main()
