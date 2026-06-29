import { useEffect, useState } from "react";
import { fetchBootstrap, fetchHealth } from "@/lib/api-contract";
import { useDemo } from "@/context/demo";
import { countSeverities } from "@/lib/storm-engine";

export function SidebarMetrics() {
  const { demoMode, visible, bootstrap, demoImpact } = useDemo();
  const [bedrockStatus, setBedrockStatus] = useState<string>("—");
  const [kbStatus, setKbStatus] = useState<string>("—");

  useEffect(() => {
    void fetchHealth(true)
      .then((h) => {
        setBedrockStatus(h.checks?.bedrock || h.status);
        setKbStatus(h.checks?.s3 || "—");
      })
      .catch(() => {
        setBedrockStatus("unavailable");
      });
  }, []);

  // Counts mirror the live storm only — idle shows zeros (matches reference behavior).
  const sev = countSeverities(demoMode ? visible : []);
  const incidents24h = demoMode ? visible.length : 0;
  const noise = demoMode ? visible.filter((r) => r.is_noise_candidate === "true").length : 0;
  const mttr = demoImpact?.mttr_reduction_minutes ?? demoImpact?.escalation_minutes;

  return (
    <div className="sidebar-metrics" aria-label="Operations metrics">
      <div className="sidebar-metrics-title">Live metrics</div>
      <dl className="sidebar-metrics-grid">
        <div>
          <dt>Incidents (stream)</dt>
          <dd>{incidents24h}</dd>
        </div>
        <div>
          <dt>Noise suppressed</dt>
          <dd>{noise}</dd>
        </div>
        <div>
          <dt>MTTR saved (min)</dt>
          <dd>{mttr != null ? mttr : "—"}</dd>
        </div>
        <div>
          <dt>P1 / P2 / P3</dt>
          <dd className="mono">
            {sev.P1} / {sev.P2} / {sev.P3}
          </dd>
        </div>
        <div>
          <dt>Bedrock agent</dt>
          <dd className={`sidebar-status sidebar-status-${bedrockStatus === "ok" ? "ok" : "warn"}`}>
            {bedrockStatus}
          </dd>
        </div>
        <div>
          <dt>Knowledge base</dt>
          <dd className={`sidebar-status sidebar-status-${kbStatus === "ok" ? "ok" : "warn"}`}>
            {bootstrap?.kb_id ? kbStatus : "local"}
          </dd>
        </div>
      </dl>
    </div>
  );
}
