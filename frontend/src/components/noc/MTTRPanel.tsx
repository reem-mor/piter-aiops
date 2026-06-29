import type { MetricsResult, TriageResponse } from "@/types/api";
import { Card, CardHeader, CardContent } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";

export function MTTRPanel({
  demoImpact,
  triageResult,
  noiseSuppressed,
  p1DetectionSec,
}: {
  demoImpact: MetricsResult | null;
  triageResult: TriageResponse | null;
  noiseSuppressed: number;
  p1DetectionSec?: number;
}) {
  if (!demoImpact && !triageResult) return null;

  const mttr =
    demoImpact?.mttr_reduction_minutes ?? demoImpact?.escalation_minutes ?? null;
  const similarCount = Array.isArray(triageResult?.similar_incidents)
    ? triageResult.similar_incidents.length
    : null;
  const escalationReady =
    triageResult?.requires_escalation === true ||
    Boolean(triageResult?.escalation_policy) ||
    Boolean(triageResult?.piter?.escalation);

  return (
    <Card variant="elevated">
      <CardHeader
        title="MTTR & demo impact"
        description="Simulated operational metrics for class demo — not live production data."
      />
      <CardContent>
        <div className="mttr-panel-grid">
          <MetricCard label="Noise suppressed" value={noiseSuppressed} demo />
          <MetricCard
            label="Time to P1 detection"
            value={p1DetectionSec != null ? `${p1DetectionSec}s` : "~20s"}
            demo
          />
          {mttr != null ? (
            <MetricCard label="Est. MTTR reduction (min)" value={String(mttr)} demo />
          ) : null}
          {similarCount != null ? (
            <MetricCard label="Similar incidents" value={similarCount} demo />
          ) : null}
          <MetricCard label="Escalation draft ready" value={escalationReady ? "Yes" : "No"} demo />
        </div>
      </CardContent>
    </Card>
  );
}
