import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchAlertStream,
  fetchIncidentDetail,
  fetchIncidentsHistory,
  fetchInvestigations,
} from "@/lib/api-contract";
import { useChatDock } from "@/context/chat-dock";
import { useDemo } from "@/context/demo";
import { useNavigate } from "@/context/navigation";
import { alertFromDetail, detailToChatResponse } from "@/lib/incident-detail";
import type { AlertRow, ChatResponse, Investigation, PersistedInvestigation } from "@/types/api";
import { PriorityBadge } from "@/components/noc/PriorityBadge";
import { PiterResponseView } from "@/components/noc/PiterResponseView";
import { ErrorState } from "@/components/noc/ErrorState";
import { LoadingSkeleton } from "@/components/noc/LoadingSkeleton";
import { PageHeader } from "@/components/ui/PageHeader";

type View = "alerts" | "incidents" | "past";

function formatTs(ts?: number | string): string {
  if (ts == null) return "—";
  if (typeof ts === "number") {
    return new Date(ts * 1000).toISOString().slice(0, 19).replace("T", " ");
  }
  return String(ts).slice(0, 19);
}

export function HistoryInvestigationsPage() {
  const [view, setView] = useState<View>("alerts");
  const [alerts, setAlerts] = useState<AlertRow[]>([]);
  const [incidents, setIncidents] = useState<Investigation[]>([]);
  const [past, setPast] = useState<PersistedInvestigation[]>([]);
  const [q, setQ] = useState("");
  const [sev, setSev] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const { openWith, send } = useChatDock();
  const { setTriageResult } = useDemo();
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detailLoading, setDetailLoading] = useState<string | null>(null);
  const [restoredAnalysis, setRestoredAnalysis] = useState<ChatResponse | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [stream, inv, hist] = await Promise.all([
        fetchAlertStream(true),
        fetchInvestigations(100),
        fetchIncidentsHistory(100),
      ]);
      setAlerts(stream.rows || []);
      setIncidents(inv.investigations || []);
      setPast(hist.investigations || []);
    } catch {
      setError("Failed to load history data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const filteredAlerts = useMemo(() => {
    return alerts.filter((r) => {
      if (sev && r.severity !== sev) return false;
      if (!q) return true;
      const hay = `${r.service} ${r.environment} ${r.title} ${r.timestamp}`.toLowerCase();
      return hay.includes(q.toLowerCase());
    });
  }, [alerts, q, sev]);

  const filteredIncidents = useMemo(() => {
    return incidents.filter((i) => {
      if (sev && i.priority !== sev) return false;
      if (!q) return true;
      const hay = `${i.service} ${i.environment} ${i.alert} ${i.conclusion}`.toLowerCase();
      return hay.includes(q.toLowerCase());
    });
  }, [incidents, q, sev]);

  const filteredPast = useMemo(() => {
    return past.filter((p) => {
      if (sev && p.severity !== sev) return false;
      if (!q) return true;
      const hay = `${p.service} ${p.environment} ${p.symptom} ${p.alert_id}`.toLowerCase();
      return hay.includes(q.toLowerCase());
    });
  }, [past, q, sev]);

  const openPastSession = async (sessionId: string, row?: PersistedInvestigation) => {
    setDetailLoading(sessionId);
    setError(null);
    try {
      const detail = await fetchIncidentDetail(sessionId);
      const response = detailToChatResponse(detail);
      setRestoredAnalysis(response);
      setTriageResult(response);
      openWith({
        sessionId,
        alert: alertFromDetail(detail, row),
        triageResponse: response,
      });
      navigate("home");
    } catch {
      setError("Failed to load investigation session");
    } finally {
      setDetailLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="grid-stack">
        <PageHeader title="History & Investigations" subtitle="Alerts, incidents, and persisted AI sessions" />
        <LoadingSkeleton lines={6} />
      </div>
    );
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  const selectedPast = expanded ? filteredPast.find((p) => p.session_id === expanded) : null;

  return (
    <div className="grid-stack">
      <PageHeader
        title="History & Investigations"
        subtitle="Open past investigations to restore PITER analysis and continue in Agent Copilot"
      />

      <section className="history-section panel">
        <h2 className="history-section-title">Conversation history</h2>
        <p className="mono" style={{ fontSize: "0.8125rem", margin: 0, color: "var(--text-muted)" }}>
          {filteredPast.length} persisted session{filteredPast.length === 1 ? "" : "s"} — restore analysis and
          continue in Agent Copilot.
        </p>
      </section>

      {restoredAnalysis ? (
        <section className="history-section">
          <h2 className="history-section-title">Restored PITER analysis</h2>
          <PiterResponseView response={restoredAnalysis} onFollowUp={(q) => void send(q)} />
        </section>
      ) : null}

      {selectedPast ? (
        <section className="history-section panel">
          <h2 className="history-section-title">Selected incident context</h2>
          <div className="piter-field-grid">
            <div className="piter-field">
              <div className="piter-field-label">Session</div>
              <div className="piter-field-value mono">{selectedPast.session_id}</div>
            </div>
            <div className="piter-field">
              <div className="piter-field-label">Service</div>
              <div className="piter-field-value">{selectedPast.service || "—"}</div>
            </div>
            <div className="piter-field">
              <div className="piter-field-label">Severity</div>
              <div className="piter-field-value">
                <PriorityBadge priority={(selectedPast.severity as "P1") || "P4"} />
              </div>
            </div>
            <div className="piter-field">
              <div className="piter-field-label">Symptom</div>
              <div className="piter-field-value">{selectedPast.symptom || "—"}</div>
            </div>
          </div>
        </section>
      ) : null}

      <div className="history-toolbar">
        <div className="toggle-group">
          <button
            type="button"
            className={`btn${view === "alerts" ? " active" : ""}`}
            onClick={() => setView("alerts")}
          >
            Alerts
          </button>
          <button
            type="button"
            className={`btn${view === "incidents" ? " active" : ""}`}
            onClick={() => setView("incidents")}
          >
            Incidents
          </button>
          <button
            type="button"
            className={`btn${view === "past" ? " active" : ""}`}
            onClick={() => setView("past")}
          >
            Past investigations
          </button>
        </div>
        <input
          className="input"
          placeholder="Search service, symptom…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <select className="select" value={sev} onChange={(e) => setSev(e.target.value)}>
          <option value="">All severities</option>
          <option value="P1">P1</option>
          <option value="P2">P2</option>
          <option value="P3">P3</option>
          <option value="P4">P4</option>
        </select>
      </div>

      {view === "alerts" ? (
        <section className="history-section">
          <h2 className="history-section-title">Alert history</h2>
        <div className="table-wrap panel">
          <table className="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Time</th>
                <th>Service</th>
                <th>Sev</th>
                <th>Title</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {filteredAlerts.slice(0, 80).map((r) => (
                <tr key={r.alert_id}>
                  <td className="mono">{r.alert_id}</td>
                  <td className="mono">{r.timestamp}</td>
                  <td>{r.service}</td>
                  <td>
                    <PriorityBadge priority={(r.severity as "P1") || "P4"} />
                  </td>
                  <td>{r.title}</td>
                  <td>
                    <button
                      type="button"
                      className="btn btn-sm"
                      onClick={() =>
                        openWith({
                          message: `Review alert ${r.alert_id}: ${r.title}`,
                          alert: r,
                        })
                      }
                    >
                      Ask agent
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        </section>
      ) : view === "incidents" ? (
        <section className="history-section">
          <h2 className="history-section-title">Incident investigation history</h2>
        <div className="grid-stack">
          {filteredIncidents.map((i) => (
            <article key={i.id} className="panel">
              <button
                type="button"
                className="btn"
                style={{ width: "100%", justifyContent: "space-between" }}
                onClick={() => setExpanded(expanded === i.id ? null : i.id)}
              >
                <span>
                  <PriorityBadge priority={i.priority} /> {i.service} — {i.alert.slice(0, 48)}
                </span>
                <span className="mono">{i.alertTime}</span>
              </button>
              {expanded === i.id ? (
                <div style={{ marginTop: 12, fontSize: "0.875rem" }}>
                  <p>
                    <strong>Conclusion:</strong> {i.conclusion}
                  </p>
                  <p>{i.conclusionDetail}</p>
                  <p className="mono">Impact: {i.impact}</p>
                  <button
                    type="button"
                    className="btn btn-sm"
                    onClick={() =>
                      openWith({ message: `Investigation ${i.id}: ${i.conclusionDetail}` })
                    }
                  >
                    Ask agent
                  </button>
                </div>
              ) : null}
            </article>
          ))}
        </div>
        </section>
      ) : (
        <section className="history-section">
          <h2 className="history-section-title">Recent follow-ups & past investigations</h2>
        <div className="table-wrap panel">
          {filteredPast.length === 0 ? (
            <p className="mono" style={{ padding: 12, color: "var(--text-muted)" }}>
              No persisted investigations yet. Run Analyze on a P1 alert first.
            </p>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Session</th>
                  <th>Time</th>
                  <th>Service</th>
                  <th>Sev</th>
                  <th>Symptom</th>
                  <th>Mode</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filteredPast.map((p) => (
                  <tr key={p.session_id}>
                    <td className="mono">{p.session_id.slice(0, 8)}…</td>
                    <td className="mono">{formatTs(p.timestamp || p.created_at)}</td>
                    <td>{p.service || "—"}</td>
                    <td>
                      <PriorityBadge priority={(p.severity as "P1") || "P4"} />
                    </td>
                    <td>{(p.symptom || "").slice(0, 64)}</td>
                    <td className="mono">
                      {p.mode || "—"}
                      {p.fallback_used ? " · fb" : ""}
                    </td>
                    <td>
                      <button
                        type="button"
                        className="btn btn-sm"
                        disabled={detailLoading === p.session_id}
                        onClick={() => {
                          setExpanded(p.session_id);
                          void openPastSession(p.session_id, p);
                        }}
                      >
                        {detailLoading === p.session_id ? "Loading…" : "Open in chat"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
        </section>
      )}
    </div>
  );
}
