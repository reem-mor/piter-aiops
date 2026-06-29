import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Bell,
  DollarSign,
  Layers,
  Radio,
  ShieldAlert,
  Timer,
  TrendingDown,
  Wrench,
} from "lucide-react";
import { fetchInvestigations, postIncidentStatus } from "@/lib/api-contract";
import { useDemo } from "@/context/demo";
import { useChatDock } from "@/context/chat-dock";
import { countSeverities } from "@/lib/storm-engine";
import type { AlertRow, Investigation, InvestigationsResponse, Priority } from "@/types/api";
import { AlertStreamRow } from "@/components/noc/AlertStreamRow";
import { PriorityBadge } from "@/components/noc/PriorityBadge";
import { AnalysisInProgressCard } from "@/components/noc/AnalysisInProgressCard";
import { PiterResponseView } from "@/components/noc/PiterResponseView";
import { CriticalIncidentBanner } from "@/components/demo/CriticalIncidentBanner";
const AnalyticsCharts = lazy(() =>
  import("@/components/analytics/AnalyticsCharts").then((m) => ({ default: m.AnalyticsCharts })),
);
import { MetricCard } from "@/components/ui/MetricCard";
import { PageHeader } from "@/components/ui/PageHeader";

function noiseCount(rows: AlertRow[]): number {
  return rows.filter((r) => r.is_noise_candidate === "true").length;
}

export function HomePage() {
  const {
    demoMode,
    rows,
    visible,
    decisions,
    stormComplete,
    demoImpact,
    triageResult,
    triageAnalyzing,
    escalatedIds,
    p1Row,
    wallSec,
  } = useDemo();
  const { openWith, send } = useChatDock();
  const [inv, setInv] = useState<InvestigationsResponse | null>(null);
  const seenAlerts = useRef<Set<string>>(new Set());

  const loadInv = useCallback(async () => {
    try {
      setInv(await fetchInvestigations(50));
    } catch {
      setInv(null);
    }
  }, []);

  useEffect(() => {
    void loadInv();
  }, [loadInv, stormComplete]);

  const alertRows = demoMode ? visible : [];
  const sev = countSeverities(alertRows);
  const totalReceived = demoMode ? alertRows.length : 0;
  const streamTotal = rows.length;
  const suppressed = demoMode ? noiseCount(alertRows) : 0;
  const activeIncidents = demoMode
    ? new Set(alertRows.filter((r) => r.incident_candidate_id).map((r) => r.incident_candidate_id)).size
    : 0;

  const demoKpis = useMemo(() => {
    if (!demoMode || !demoImpact) return { mttr: "—", cost: "—" };
    const mttr = demoImpact.mttr_reduction_minutes ?? demoImpact.escalation_minutes;
    const cost = demoImpact.estimated_total_cost ?? demoImpact.cost_avoided_usd;
    return {
      mttr: mttr != null ? `${mttr} min` : "—",
      cost: cost != null ? `$${Number(cost).toLocaleString()}` : "—",
    };
  }, [demoMode, demoImpact]);

  // Dominant noise pattern (most frequent suppressed service+signature pair).
  const noisePattern = useMemo(() => {
    const noisy = alertRows.filter((r) => r.is_noise_candidate === "true");
    if (!noisy.length) return null;
    const counts = new Map<string, { count: number; row: AlertRow }>();
    for (const r of noisy) {
      const key = `${r.service}::${r.title}`;
      const entry = counts.get(key) || { count: 0, row: r };
      entry.count += 1;
      counts.set(key, entry);
    }
    let best: { count: number; row: AlertRow } | null = null;
    for (const entry of counts.values()) {
      if (!best || entry.count > best.count) best = entry;
    }
    return best;
  }, [alertRows]);

  const askAlert = (row: AlertRow) => {
    openWith({
      message: `Alert ${row.alert_id}: ${row.service} @ ${row.environment}, ${row.severity} at ${row.timestamp}. ${row.title}. Summarize impact and next checks.`,
      alert: row,
    });
  };

  const scrollToAnalysis = () => {
    document.getElementById("piter-analysis-panel")?.scrollIntoView({ behavior: "smooth" });
  };

  const visibleSlice = alertRows.slice().reverse().slice(0, 60);
  const streamStatus = stormComplete ? "captured" : "streaming";
  const suppressionPct =
    totalReceived > 0 ? Math.round((suppressed / totalReceived) * 100) : 0;

  return (
    <div className="grid-stack home-page">
      <PageHeader
        title="Operations Dashboard"
        subtitle="Live production operations state — alert stream, incident queue, and AI copilot"
      />

      <CriticalIncidentBanner />

      <div className="kpi-grid kpi-grid-seven">
        <MetricCard
          label="Alerts received"
          value={demoMode ? `${totalReceived} / ${streamTotal}` : "0"}
          icon={Radio}
          tone="info"
          mono
        />
        <MetricCard label="Noise suppressed" value={suppressed} icon={TrendingDown} tone="success" />
        <MetricCard label="Active incidents" value={activeIncidents} icon={Layers} tone="warning" />
        <MetricCard
          label="P1 / P2 / P3"
          value={`${sev.P1} / ${sev.P2} / ${sev.P3}`}
          icon={ShieldAlert}
          tone={sev.P1 > 0 ? "danger" : "default"}
          mono
        />
        <MetricCard
          label="Escalations"
          value={escalatedIds.size}
          icon={Bell}
          tone={escalatedIds.size > 0 ? "danger" : "default"}
        />
        <MetricCard
          label="MTTR reduced"
          value={demoKpis.mttr}
          icon={Timer}
          tone="success"
          demo={demoMode}
          hint="vs baseline"
        />
        <MetricCard label="Cost avoided" value={demoKpis.cost} icon={DollarSign} tone="success" demo={demoMode} />
      </div>

      {demoMode ? (
        <Suspense fallback={null}>
          <AnalyticsCharts visible={alertRows} decisions={decisions} compact />
        </Suspense>
      ) : null}

      <div className="home-grid">
        <section className="panel home-panel">
          <div className="stream-header">
            <h2 className="panel-title" style={{ margin: 0 }}>
              Alert stream
            </h2>
            {demoMode ? (
              <span className="stream-counter stream-live-pulse">
                {visibleSlice.length} visible · {totalReceived} total
              </span>
            ) : null}
          </div>
          {!demoMode ? (
            <div className="idle-state-card">
              <p>
                Idle — use <strong>Start Alert Stream</strong> in the top bar to begin demo playback.
              </p>
            </div>
          ) : null}
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Service</th>
                  <th>Alert</th>
                  <th>Sev</th>
                  <th>Status</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {alertRows.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="mono" style={{ color: "var(--text-muted)" }}>
                      {demoMode ? "Awaiting alerts…" : "No alerts in view"}
                    </td>
                  </tr>
                ) : (
                  visibleSlice.map((r) => {
                    const isNew = !seenAlerts.current.has(r.alert_id);
                    if (isNew) seenAlerts.current.add(r.alert_id);
                    const rowClass = [
                      isNew ? "alert-row-enter" : "",
                      p1Row && r.alert_id === p1Row.alert_id ? "alert-row-p1" : "",
                      r.is_noise_candidate === "true" ? "alert-row-noise" : "",
                      r.is_trigger === "true" ? "alert-row-trigger" : "",
                    ]
                      .filter(Boolean)
                      .join(" ");
                    return (
                      <AlertStreamRow
                        key={r.alert_id}
                        row={r}
                        rowClass={rowClass}
                        streamStatus={streamStatus}
                        onAsk={askAlert}
                      />
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel home-panel">
          <h2 className="panel-title">Agent decisions</h2>
          <ul className="decision-feed">
            {decisions.length === 0 ? (
              <li className="mono" style={{ color: "var(--text-muted)" }}>
                Awaiting stream…
              </li>
            ) : (
              decisions
                .slice()
                .reverse()
                .map((d) => (
                  <li key={d.id} className={`decision decision-${d.kind}`}>
                    <div className="decision-meta mono">
                      {formatElapsed(d.at)} · <span className="decision-kind">{d.kind.toUpperCase()}</span>
                    </div>
                    <div className="decision-text">{d.text}</div>
                  </li>
                ))
            )}
          </ul>
        </section>
      </div>

      <div className="home-grid">
        <section className="panel">
          <div className="stream-header">
            <h2 className="panel-title" style={{ margin: 0 }}>
              Noise pattern detected
            </h2>
            {suppressed > 0 ? (
              <span className="pill pill-success">{suppressed} duplicates suppressed</span>
            ) : null}
          </div>
          {noisePattern ? (
            <dl className="noise-pattern-grid">
              <div>
                <dt>Pattern</dt>
                <dd className="mono">
                  {noisePattern.row.service} {noisePattern.row.title}
                </dd>
              </div>
              <div>
                <dt>Frequency</dt>
                <dd>
                  {noisePattern.count} alerts in {Math.max(1, Math.ceil(wallSec / 60))} minutes
                </dd>
              </div>
              <div>
                <dt>Reason</dt>
                <dd>Same service, error signature, env &amp; window</dd>
              </div>
              <div>
                <dt>Action</dt>
                <dd>Grouped into one incident candidate</dd>
              </div>
            </dl>
          ) : (
            <p className="mono" style={{ fontSize: "0.8125rem", margin: 0, color: "var(--text-muted)" }}>
              No noise pattern yet — start the alert stream to see suppression in action.
            </p>
          )}
        </section>

        <section className="panel">
          <div className="stream-header">
            <h2 className="panel-title" style={{ margin: 0 }}>
              Incident queue
            </h2>
            {activeIncidents > 0 ? <span className="pill pill-warning">{activeIncidents} active</span> : null}
          </div>
          <IncidentQueue items={inv?.investigations ?? []} escalatedIds={escalatedIds} onAsk={openWith} />
        </section>
      </div>

      <div className="home-grid">
        <section className="panel">
          <h2 className="panel-title">
            <Wrench size={14} style={{ verticalAlign: "-2px", marginRight: 6 }} />
            MCP / Lambda tool calls
          </h2>
          {triageResult?.tool_results?.length ? (
            <ul className="tool-call-feed">
              {triageResult.tool_results.map((t, i) => (
                <li key={`${t.name}-${i}`} className="tool-call-row">
                  <span className="tool-call-dot" aria-hidden />
                  <code className="mono">{t.name}</code>
                  <span className="tool-call-status">completed</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="mono empty-state-text">
              No tools called yet — start the demo and trigger Analyze.
            </p>
          )}
        </section>

        <section className="panel">
          <h2 className="panel-title">Business impact</h2>
          {demoMode && (demoImpact || triageResult) ? (
            <>
              <div className="business-impact-grid">
                <div className="business-impact-stat">
                  <span className="business-impact-value">{demoKpis.mttr}</span>
                  <span className="business-impact-label">MTTR reduced</span>
                </div>
                <div className="business-impact-stat">
                  <span className="business-impact-value">{demoKpis.cost}</span>
                  <span className="business-impact-label">Cost avoided</span>
                </div>
                <div className="business-impact-stat">
                  <span className="business-impact-value">{suppressionPct}%</span>
                  <span className="business-impact-label">Noise suppression</span>
                </div>
              </div>
              <p className="business-impact-note">
                By grouping noise, enriching with RAG and AWS Lambda tools, and prioritizing the P1, PITER
                Ops protects revenue, customer trust, SLA commitments, and brand reputation.
              </p>
            </>
          ) : (
            <p className="mono empty-state-text">
              Impact metrics appear after the storm completes and the P1 is analyzed.
            </p>
          )}
        </section>
      </div>

      {triageAnalyzing && !triageResult ? <AnalysisInProgressCard /> : null}

      {triageResult ? (
        <section>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 className="panel-title">P1 analysis</h2>
            <button type="button" className="btn btn-sm" onClick={scrollToAnalysis}>
              Jump to analysis
            </button>
          </div>
          <PiterResponseView
            response={triageResult}
            onFollowUp={(q) => void send(q)}
          />
        </section>
      ) : null}
    </div>
  );
}

function formatElapsed(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `00:${mm}:${ss}`;
}

function IncidentQueue({
  items,
  escalatedIds,
  onAsk,
}: {
  items: Investigation[];
  escalatedIds: Set<string>;
  onAsk: (p: { message: string }) => void;
}) {
  const [state, setState] = useState<Record<string, string>>({});

  const updateStatus = (id: string, status: "in_process" | "resolved") => {
    setState((s) => ({ ...s, [id]: status }));
    // Persist operator action server-side (survives reload via /api/investigations).
    void postIncidentStatus(id, status).catch(() => {});
  };

  if (!items.length) {
    return (
      <p className="mono empty-state-text">
        No incidents yet — start the alert stream to populate the queue.
      </p>
    );
  }

  return (
    <ul className="incident-queue">
      {items.slice(0, 8).map((item) => {
        const st = state[item.id] || item.operator_status || "open";
        const escalated = escalatedIds.has(item.id);
        return (
          <li key={item.id} className={`incident-row${item.priority === "P1" ? " incident-row-p1" : ""}`}>
            <div>
              <PriorityBadge priority={item.priority} />
              <span style={{ marginLeft: 8, fontWeight: 600 }}>{item.alert}</span>
              <div className="mono" style={{ fontSize: "0.75rem", marginTop: 4, color: "var(--text-muted)" }}>
                {item.service} · {item.id}
              </div>
            </div>
            <div className="incident-actions">
              {escalated ? <span className="pill pill-danger">Escalated</span> : null}
              {st === "in_process" ? <span className="pill pill-warning">In process</span> : null}
              {st === "resolved" ? <span className="pill pill-success">Resolved</span> : null}
              {st !== "resolved" ? (
                <>
                  {st !== "in_process" ? (
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() => updateStatus(item.id, "in_process")}
                    >
                      Mark in process
                    </button>
                  ) : null}
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() => updateStatus(item.id, "resolved")}
                  >
                    Resolve
                  </button>
                </>
              ) : null}
              <button
                type="button"
                className="btn btn-sm"
                onClick={() =>
                  onAsk({
                    message: `Incident ${item.id}: ${item.service} ${item.priority} — ${item.conclusionDetail || item.alert}`,
                  })
                }
              >
                Ask agent
              </button>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
