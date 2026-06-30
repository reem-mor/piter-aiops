import { useCallback, useEffect, useState } from "react";
import { ApiError, fetchHealth } from "@/lib/api-contract";
import type { HealthResponse } from "@/types/api";
import { ErrorState } from "@/components/noc/ErrorState";
import { LoadingSkeleton } from "@/components/noc/LoadingSkeleton";

const KB_ID = "${PITER_BEDROCK_KB_ID}";
const S3_PREFIX = "projects/piter-aiops/knowledge_base/";

export function KnowledgeBasePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      setHealth(await fetchHealth(true));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Health check failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="grid-stack">
      <h1 style={{ margin: 0, fontSize: "1.25rem" }}>Knowledge Base</h1>

      <section className="panel">
        <h2 className="panel-title">Configuration — not live API data</h2>
        <div className="grid-2">
          <div>
            <div className="config-label">Knowledge Base ID</div>
            <div className="mono">{KB_ID}</div>
          </div>
          <div>
            <div className="config-label">S3 document prefix</div>
            <div className="mono">{S3_PREFIX}</div>
          </div>
        </div>
        <p style={{ margin: "12px 0 0", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
          Static values from project documentation. Live sync status and document categories are not
          exposed by GET /api/health.
        </p>
      </section>

      <section className="panel">
        <h2 className="panel-title">Live infrastructure checks</h2>
        {loading ? <LoadingSkeleton lines={3} /> : null}
        {error ? <ErrorState message={error} onRetry={load} /> : null}
        {health && !error ? (
          <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <Badge label="Overall" value={health.status} />
            {health.checks?.bedrock ? <Badge label="Bedrock" value={health.checks.bedrock} /> : null}
            {health.checks?.s3 ? <Badge label="S3" value={health.checks.s3} /> : null}
            {health.checks?.app ? <Badge label="App" value={health.checks.app} /> : null}
          </ul>
        ) : null}
      </section>
    </div>
  );
}

function Badge({ label, value }: { label: string; value: string }) {
  const ok = value === "ok" || value === "healthy";
  return (
    <span
      style={{
        padding: "6px 12px",
        borderRadius: "var(--radius-sm)",
        border: `1px solid ${ok ? "var(--success)" : "var(--warning)"}`,
        background: ok ? "rgba(34,197,94,0.1)" : "rgba(234,179,8,0.1)",
        fontSize: "0.8125rem",
      }}
    >
      {label}: <strong>{value}</strong>
    </span>
  );
}
