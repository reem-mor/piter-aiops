import { useCallback, useEffect, useState } from "react";
import { ApiError, fetchHealth, fetchInvestigations } from "@/lib/api-contract";
import type { HealthResponse, Investigation, InvestigationsResponse } from "@/types/api";
import { AlertCard } from "@/components/noc/AlertCard";
import { ErrorState } from "@/components/noc/ErrorState";
import { LoadingSkeleton } from "@/components/noc/LoadingSkeleton";
import { EmptyState } from "@/components/noc/EmptyState";
import { PriorityBadge } from "@/components/noc/PriorityBadge";
import type { Priority } from "@/types/api";

function countByPriority(items: Investigation[]): Record<Priority, number> {
  const counts: Record<Priority, number> = { P1: 0, P2: 0, P3: 0, P4: 0 };
  for (const item of items) {
    if (item.priority in counts) counts[item.priority as Priority] += 1;
  }
  return counts;
}

function aggregateImpact(items: Investigation[]): string[] {
  return items.map((i) => i.impact).filter(Boolean).slice(0, 5);
}

export function DashboardPage() {
  const [inv, setInv] = useState<InvestigationsResponse | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [invData, healthData] = await Promise.all([
        fetchInvestigations(12),
        fetchHealth(true),
      ]);
      setInv(invData);
      setHealth(healthData);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Failed to load dashboard";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 15_000);
    return () => clearInterval(id);
  }, [load]);

  if (loading && !inv) {
    return (
      <div className="grid-stack">
        <h1 style={{ margin: 0, fontSize: "1.25rem" }}>Operations Dashboard</h1>
        <LoadingSkeleton lines={5} />
      </div>
    );
  }

  if (error && !inv) {
    return <ErrorState message={error} onRetry={load} />;
  }

  const items = inv?.investigations ?? [];
  const counts = countByPriority(items);
  const impacts = aggregateImpact(items);

  return (
    <div className="grid-stack">
      <h1 style={{ margin: 0, fontSize: "1.25rem" }}>Operations Dashboard</h1>

      <div className="grid-4">
        {(["P1", "P2", "P3", "P4"] as Priority[]).map((p) => (
          <div key={p} className="panel" style={{ textAlign: "center" }}>
            <PriorityBadge priority={p} />
            <div className="mono" style={{ fontSize: "1.5rem", marginTop: "8px" }}>
              {counts[p]}
            </div>
          </div>
        ))}
      </div>

      <div className="grid-2">
        <section className="panel">
          <h2 className="panel-title">Infrastructure status</h2>
          <p style={{ margin: "0 0 12px", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            From GET /api/health?deep=1 — not enrichment-tool readiness.
          </p>
          {health ? (
            <ul style={{ margin: 0, padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: "8px" }}>
              <li>
                Overall: <strong>{health.status}</strong>
              </li>
              {health.checks?.app ? <li>App: {health.checks.app}</li> : null}
              {health.checks?.s3 ? <li>S3: {health.checks.s3}</li> : null}
              {health.checks?.bedrock ? <li>Bedrock: {health.checks.bedrock}</li> : null}
            </ul>
          ) : (
            <LoadingSkeleton lines={3} />
          )}
        </section>

        <section className="panel">
          <h2 className="panel-title">Business impact summary</h2>
          <p style={{ margin: "0 0 12px", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
            Aggregated from active investigations.
          </p>
          {impacts.length ? (
            <ul style={{ margin: 0, paddingLeft: "18px", fontSize: "0.875rem" }}>
              {impacts.map((text, i) => (
                <li key={i}>{text}</li>
              ))}
            </ul>
          ) : (
            <EmptyState title="No impact data" detail="Investigations returned no impact strings." />
          )}
        </section>
      </div>

      <section>
        <h2 className="panel-title">Recent incidents (investigations feed)</h2>
        {items.length ? (
          <div className="grid-stack">
            {items.map((item) => (
              <AlertCard key={item.id} item={item} />
            ))}
          </div>
        ) : (
          <EmptyState title="No active investigations" />
        )}
      </section>

      {inv?.summary ? (
        <p className="mono" style={{ color: "var(--text-muted)", fontSize: "0.75rem" }}>
          Summary: {inv.summary.active_count ?? 0} active · {inv.summary.total ?? items.length} total
        </p>
      ) : null}
    </div>
  );
}
