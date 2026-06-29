import { useCallback, useEffect, useState } from "react";
import { fetchBootstrap, fetchHealth } from "@/lib/api-contract";
import type { BootstrapResponse, HealthResponse } from "@/types/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { LoadingSkeleton } from "@/components/noc/LoadingSkeleton";
import { ErrorState } from "@/components/noc/ErrorState";
import { SourceBadge } from "@/components/ui/SourceBadge";

const ACTION_GROUPS = [
  "get_recent_deployments",
  "get_service_context",
  "get_similar_incidents",
  "get_escalation_policy",
] as const;

export function BedrockStatusPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [bootstrap, setBootstrap] = useState<BootstrapResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [h, b] = await Promise.all([fetchHealth(true), fetchBootstrap()]);
      setHealth(h);
      setBootstrap(b);
    } catch {
      setError("Failed to load AWS / Bedrock status");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
    const id = setInterval(() => void load(), 20_000);
    return () => clearInterval(id);
  }, [load]);

  if (loading) {
    return (
      <div className="grid-stack">
        <PageHeader title="AWS / Bedrock Status" subtitle="Agent runtime, knowledge base, and action groups" />
        <LoadingSkeleton lines={6} />
      </div>
    );
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  const ext = bootstrap as BootstrapResponse & {
    use_bedrock?: boolean;
    model_label?: string;
    execution_mode_hint?: string;
  };

  return (
    <div className="grid-stack">
      <PageHeader
        title="AWS / Bedrock Status"
        subtitle="Live health checks — no simulated agent responses on this page"
      />

      <section className="panel">
        <h2 className="panel-title">Runtime health</h2>
        <ul className="status-list">
          <li>
            Overall: <strong>{health?.status}</strong>
          </li>
          {health?.checks?.app ? <li>Application: {health.checks.app}</li> : null}
          {health?.checks?.s3 ? <li>S3 / artifacts: {health.checks.s3}</li> : null}
          {health?.checks?.bedrock ? <li>Bedrock agent: {health.checks.bedrock}</li> : null}
        </ul>
      </section>

      <section className="panel">
        <h2 className="panel-title">Agent configuration</h2>
        <dl className="config-dl">
          <dt>Bedrock enabled</dt>
          <dd>{ext.use_bedrock ? "Yes" : "No (local fallback path)"}</dd>
          <dt>Model</dt>
          <dd className="mono">{ext.model_label || "—"}</dd>
          <dt>Execution mode</dt>
          <dd className="mono">{ext.execution_mode_hint || "—"}</dd>
          <dt>KB ID</dt>
          <dd className="mono">{bootstrap?.kb_id || "—"}</dd>
        </dl>
        <div style={{ marginTop: 12 }}>
          <SourceBadge mode={ext.use_bedrock ? "bedrock_agent" : "local_fallback"} />
        </div>
      </section>

      <section className="panel">
        <h2 className="panel-title">Action groups</h2>
        <p style={{ margin: "0 0 12px", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
          Exposed via /api/metrics/* — invoked during P1 triage enrichment.
        </p>
        <ul className="action-group-list">
          {ACTION_GROUPS.map((name) => (
            <li key={name} className="action-group-item">
              <span className="mono">{name}</span>
              <span className="action-group-badge">registered</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="panel">
        <h2 className="panel-title">Notifications</h2>
        <dl className="config-dl">
          <dt>Mode</dt>
          <dd className="mono">{bootstrap?.notification?.mode || "preview"}</dd>
          <dt>Live dispatch</dt>
          <dd>{bootstrap?.notification?.live_dispatch_enabled ? "Enabled" : "Preview only"}</dd>
        </dl>
      </section>
    </div>
  );
}
