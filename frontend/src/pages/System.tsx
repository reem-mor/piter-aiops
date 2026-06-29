import { useCallback, useEffect, useState } from "react";
import { fetchBootstrap, fetchHealth } from "@/lib/api-contract";
import type { BootstrapResponse, HealthResponse } from "@/types/api";
import { MetricsToolsSection } from "@/pages/SystemMetrics";
import { ErrorState } from "@/components/noc/ErrorState";
import { LoadingSkeleton } from "@/components/noc/LoadingSkeleton";

export function SystemPage() {
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
      setError("Failed to load system status");
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
        <h1 style={{ margin: 0, fontSize: "1.125rem" }}>System</h1>
        <LoadingSkeleton lines={5} />
      </div>
    );
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  return (
    <div className="grid-stack">
      <h1 style={{ margin: 0, fontSize: "1.125rem" }}>System</h1>

      <section className="panel">
        <h2 className="panel-title">Infrastructure status</h2>
        <p style={{ margin: "0 0 12px", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
          GET /api/health?deep=1
        </p>
        <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: "8px" }}>
          <li>
            Overall: <strong>{health?.status}</strong>
          </li>
          {health?.checks?.app ? <li>App: {health.checks.app}</li> : null}
          {health?.checks?.s3 ? <li>S3 / data: {health.checks.s3}</li> : null}
          {health?.checks?.bedrock ? <li>Bedrock agent: {health.checks.bedrock}</li> : null}
        </ul>
      </section>

      <section className="panel">
        <h2 className="panel-title">Knowledge base</h2>
        <dl className="config-dl">
          <dt>KB ID</dt>
          <dd className="mono">{bootstrap?.kb_id || "—"}</dd>
          <dt>S3 prefix</dt>
          <dd className="mono">{bootstrap?.s3_prefix || "—"}</dd>
          <dt>Execution mode</dt>
          <dd className="mono">{bootstrap?.execution_mode_hint || "—"}</dd>
          <dt>Notification mode</dt>
          <dd className="mono">{bootstrap?.notification?.mode || "—"}</dd>
        </dl>
      </section>

      <MetricsToolsSection />
    </div>
  );
}
