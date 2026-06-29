import type { AgentDecision, AlertRow } from "@/types/api";

/** Wall-clock second when the P1 candidate modal fires (presenter choreography). */
export const P1_WALL_SECONDS = 20;
/** Total compressed storm playback duration on the wall clock. */
export const STORM_WALL_SECONDS = 90;
const DATA_P1_OFFSET = 175;
const DATA_DURATION = 300;

export function dataOffsetForWall(wallSec: number): number {
  if (wallSec <= P1_WALL_SECONDS) {
    return (wallSec / P1_WALL_SECONDS) * DATA_P1_OFFSET;
  }
  const tail = wallSec - P1_WALL_SECONDS;
  const tailWall = STORM_WALL_SECONDS - P1_WALL_SECONDS;
  return DATA_P1_OFFSET + (tail / tailWall) * (DATA_DURATION - DATA_P1_OFFSET);
}

export function visibleRowsAt(rows: AlertRow[], wallSec: number): AlertRow[] {
  const threshold = dataOffsetForWall(wallSec);
  return rows.filter((r) => Number(r.seconds_offset) <= threshold);
}

export function shouldShowP1Popup(
  rows: AlertRow[],
  wallSec: number,
  alreadyShown: boolean,
): boolean {
  if (alreadyShown) return false;
  if (wallSec < P1_WALL_SECONDS) return false;
  return rows.some((r) => r.is_trigger === "true" || r.severity === "P1");
}

export function deriveDecisions(
  prev: AgentDecision[],
  added: AlertRow[],
  wallSec: number,
): AgentDecision[] {
  const next = [...prev];
  const noise = added.filter((r) => r.is_noise_candidate === "true");
  if (noise.length) {
    next.push({
      id: `noise-${wallSec}`,
      at: wallSec,
      kind: "noise",
      text: `Suppressed ${noise.length} duplicate alert${noise.length > 1 ? "s" : ""} (rolling window).`,
    });
  }
  const groups = new Map<string, { count: number; service: string; title: string }>();
  for (const r of added) {
    const key = r.correlation_id || `${r.environment}:${r.service}`;
    const g = groups.get(key) || { count: 0, service: r.service, title: r.title };
    g.count += 1;
    groups.set(key, g);
  }
  for (const [key, g] of groups) {
    if (g.count > 1) {
      next.push({
        id: `grp-${key}-${wallSec}`,
        at: wallSec,
        kind: "group",
        text: `Grouping ${g.count} ${g.service} alerts by service, time window, environment, error signature.`,
      });
    }
  }
  const noisePattern = noise.find((r) => r.service && r.title);
  if (noisePattern && noise.length >= 3) {
    next.push({
      id: `pattern-${wallSec}`,
      at: wallSec,
      kind: "noise",
      text: `Noise pattern detected: ${noisePattern.service} ${noisePattern.title}.`,
    });
  }
  const p1 = added.find((r) => r.is_trigger === "true" || r.severity === "P1");
  if (p1) {
    next.push({
      id: `p1-${p1.alert_id}`,
      at: wallSec,
      kind: "p1",
      text: `P1 candidate detected: ${p1.title} — ${p1.service}.`,
    });
  }
  return next.slice(-40);
}

export function countSeverities(rows: AlertRow[]): Record<string, number> {
  const out: Record<string, number> = { P1: 0, P2: 0, P3: 0, P4: 0 };
  for (const r of rows) {
    const s = r.severity || "P4";
    out[s] = (out[s] || 0) + 1;
  }
  return out;
}

export function alertToTriagePayload(row: AlertRow) {
  return {
    alert_id: row.alert_id,
    service: row.service,
    environment: row.environment,
    severity: row.severity,
    symptom: row.title,
    description: row.title,
    alert_time: row.timestamp,
  };
}
