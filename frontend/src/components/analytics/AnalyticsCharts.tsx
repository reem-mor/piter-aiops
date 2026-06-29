import { useMemo, type ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { AgentDecision, AlertRow } from "@/types/api";

const SEV_COLORS: Record<string, string> = {
  P1: "#ef4444",
  P2: "#f97316",
  P3: "#eab308",
  P4: "#64748b",
};

const PIE_COLORS = ["#22c55e", "#3b82f6", "#f97316"];

type Props = {
  visible: AlertRow[];
  decisions: AgentDecision[];
  compact?: boolean;
};

export function AnalyticsCharts({ visible, decisions, compact = false }: Props) {
  const importantVsNoise = useMemo(() => {
    const noise = visible.filter((r) => r.is_noise_candidate === "true").length;
    const important = visible.length - noise;
    const triggers = visible.filter((r) => r.is_trigger === "true" || r.incident_candidate_id).length;
    return [
      { name: "Important", value: Math.max(important - triggers, 0) },
      { name: "Incident candidates", value: triggers },
      { name: "Noise suppressed", value: noise },
    ].filter((d) => d.value > 0);
  }, [visible]);

  const severityTimeline = useMemo(() => {
    const buckets: Record<string, { bucket: string; P1: number; P2: number; P3: number; P4: number }> = {};
    for (const row of visible) {
      const sec = Math.floor(Number(row.seconds_offset || 0) / 15) * 15;
      const key = `${sec}s`;
      if (!buckets[key]) buckets[key] = { bucket: key, P1: 0, P2: 0, P3: 0, P4: 0 };
      const sev = (row.severity || "P4") as keyof (typeof buckets)[string];
      if (sev in buckets[key] && sev !== "bucket") {
        buckets[key][sev as "P1" | "P2" | "P3" | "P4"] += 1;
      }
    }
    return Object.values(buckets)
      .sort((a, b) => parseInt(a.bucket, 10) - parseInt(b.bucket, 10))
      .slice(compact ? -8 : -12);
  }, [visible, compact]);

  const noisiestServices = useMemo(() => {
    const counts = new Map<string, number>();
    for (const row of visible) {
      if (row.is_noise_candidate !== "true") continue;
      const svc = row.service || "unknown";
      counts.set(svc, (counts.get(svc) || 0) + 1);
    }
    return [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, compact ? 4 : 6)
      .map(([service, alerts]) => ({ service, alerts }));
  }, [visible, compact]);

  const toolDecisions = useMemo(() => {
    const kinds: Record<string, number> = { noise: 0, group: 0, escalate: 0, analyze: 0 };
    for (const d of decisions) {
      kinds[d.kind] = (kinds[d.kind] || 0) + 1;
    }
    return Object.entries(kinds)
      .filter(([, v]) => v > 0)
      .map(([kind, count]) => ({ kind, count }));
  }, [decisions]);

  const chartH = compact ? 140 : 180;

  if (!visible.length && !decisions.length) {
    return (
      <p className="mono analytics-empty" style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>
        Charts populate when the alert stream runs.
      </p>
    );
  }

  return (
    <div className={`analytics-charts-grid${compact ? " analytics-charts-compact" : ""}`}>
      <ChartPanel title="Important vs noise" compact={compact}>
        <ResponsiveContainer width="100%" height={chartH}>
          <PieChart>
            <Pie data={importantVsNoise} dataKey="value" nameKey="name" innerRadius={compact ? 32 : 48} outerRadius={compact ? 52 : 72} paddingAngle={2}>
              {importantVsNoise.map((_, i) => (
                <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }} />
            {!compact ? <Legend /> : null}
          </PieChart>
        </ResponsiveContainer>
      </ChartPanel>

      <ChartPanel title="Severity over storm" compact={compact}>
        <ResponsiveContainer width="100%" height={chartH}>
          <AreaChart data={severityTimeline}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
            <XAxis dataKey="bucket" tick={{ fontSize: 10 }} stroke="var(--text-muted)" />
            <YAxis tick={{ fontSize: 10 }} stroke="var(--text-muted)" width={28} />
            <Tooltip contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }} />
            {(["P1", "P2", "P3", "P4"] as const).map((sev) => (
              <Area key={sev} type="monotone" dataKey={sev} stackId="1" stroke={SEV_COLORS[sev]} fill={SEV_COLORS[sev]} fillOpacity={0.5} />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      </ChartPanel>

      <ChartPanel title="Noisiest services" compact={compact}>
        <ResponsiveContainer width="100%" height={chartH}>
          <BarChart data={noisiestServices} layout="vertical" margin={{ left: 4, right: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" horizontal={false} />
            <XAxis type="number" tick={{ fontSize: 10 }} stroke="var(--text-muted)" />
            <YAxis type="category" dataKey="service" width={compact ? 72 : 88} tick={{ fontSize: 10 }} stroke="var(--text-muted)" />
            <Tooltip contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }} />
            <Bar dataKey="alerts" fill="#3b82f6" radius={[0, 4, 4, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartPanel>

      {!compact ? (
        <ChartPanel title="Agent decisions" compact={compact}>
          <ResponsiveContainer width="100%" height={chartH}>
            <BarChart data={toolDecisions}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
              <XAxis dataKey="kind" tick={{ fontSize: 10 }} stroke="var(--text-muted)" />
              <YAxis tick={{ fontSize: 10 }} stroke="var(--text-muted)" width={28} />
              <Tooltip contentStyle={{ background: "var(--bg-elevated)", border: "1px solid var(--border-subtle)" }} />
              <Bar dataKey="count" fill="#22c55e" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartPanel>
      ) : null}
    </div>
  );
}

function ChartPanel({
  title,
  children,
  compact,
}: {
  title: string;
  children: ReactNode;
  compact?: boolean;
}) {
  return (
    <section className={`panel analytics-chart-panel${compact ? " analytics-chart-panel-compact" : ""}`}>
      <h3 className="analytics-chart-title">{title}</h3>
      {children}
    </section>
  );
}
