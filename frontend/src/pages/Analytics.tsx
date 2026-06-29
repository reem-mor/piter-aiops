import { useMemo } from "react";
import { AnalyticsCharts } from "@/components/analytics/AnalyticsCharts";
import { useDemo } from "@/context/demo";
import type { AgentDecision, Priority } from "@/types/api";
import { PriorityBadge } from "@/components/noc/PriorityBadge";

export function AnalyticsPage() {
  const { decisions, triageResult, visible, demoMode } = useDemo();

  const sevDist = useMemo(() => {
    const d: Record<string, number> = { P1: 0, P2: 0, P3: 0, P4: 0 };
    for (const r of visible) {
      const s = r.severity || "P4";
      d[s] = (d[s] || 0) + 1;
    }
    return d;
  }, [visible]);

  const toolCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const t of triageResult?.tool_results || []) {
      counts[t.name] = (counts[t.name] || 0) + 1;
    }
    return counts;
  }, [triageResult]);

  const suppressionStats = useMemo(() => {
    const noise = decisions.filter((d) => d.kind === "noise").length;
    const groups = decisions.filter((d) => d.kind === "group").length;
    return { noise, groups };
  }, [decisions]);

  const confidence = triageResult?.confidence || "—";
  const analyzed = visible.filter((r) => r.incident_candidate_id || r.is_trigger === "true").length;

  return (
    <div className="grid-stack">
      <h1 style={{ margin: 0, fontSize: "1.125rem" }}>Agent Analytics</h1>
      {!demoMode && !triageResult ? (
        <p className="mono" style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>
          Metrics populate from alert stream playback and triage results. Start the demo or run an analysis.
        </p>
      ) : null}

      <div className="grid-4">
        <Stat label="Incidents analyzed" value={analyzed} />
        <Stat label="Avg confidence" value={confidence} />
        <Stat label="Noise decisions" value={suppressionStats.noise} />
        <Stat label="Group decisions" value={suppressionStats.groups} />
      </div>

      <AnalyticsCharts visible={visible} decisions={decisions} />

      <section className="panel">
        <h2 className="panel-title">Severity distribution (stream)</h2>
        <div style={{ display: "flex", gap: 12 }}>
          {(["P1", "P2", "P3", "P4"] as Priority[]).map((p) => (
            <span key={p}>
              <PriorityBadge priority={p} /> {sevDist[p] || 0}
            </span>
          ))}
        </div>
      </section>

      <section className="panel">
        <h2 className="panel-title">Tool invocations</h2>
        {Object.keys(toolCounts).length === 0 ? (
          <p className="mono" style={{ color: "var(--text-muted)" }}>No tool_results yet — run P1 analysis.</p>
        ) : (
          <ul>
            {Object.entries(toolCounts).map(([name, n]) => (
              <li key={name} className="mono">
                {name}: {n}
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel">
        <h2 className="panel-title">Decision timeline</h2>
        <Timeline decisions={decisions} />
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="panel" style={{ textAlign: "center" }}>
      <div className="kpi-label">{label}</div>
      <div className="kpi-value">{value}</div>
    </div>
  );
}

function Timeline({ decisions }: { decisions: AgentDecision[] }) {
  if (!decisions.length) {
    return <p className="mono" style={{ color: "var(--text-muted)" }}>No decisions recorded.</p>;
  }
  return (
    <ol className="timeline">
      {decisions.map((d) => (
        <li key={d.id}>
          <span className="mono">{d.at}s</span> — {d.text}
        </li>
      ))}
    </ol>
  );
}
