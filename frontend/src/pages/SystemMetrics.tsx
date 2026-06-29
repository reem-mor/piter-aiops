import { useState, type ReactNode } from "react";
import {
  ApiError,
  fetchEscalationPreview,
  fetchRecentDeployments,
  fetchServiceContext,
  fetchSimilarIncidents,
} from "@/lib/api-contract";
import { useDemo } from "@/context/demo";
import { isLiveDispatchReady } from "@/lib/notification-ui";
import type { MetricsResult } from "@/types/api";
import { ToolResultPanel } from "@/components/noc/ToolResultPanel";
import { ErrorState } from "@/components/noc/ErrorState";
import { LoadingSkeleton } from "@/components/noc/LoadingSkeleton";

export function MetricsToolsSection() {
  return (
    <div className="grid-stack">
      <h2 className="panel-title" style={{ margin: 0 }}>
        Metrics tools
      </h2>
      <DeploymentsCard />
      <ServiceContextCard />
      <SimilarIncidentsCard />
      <EscalationCard />
    </div>
  );
}

function DeploymentsCard() {
  const [service, setService] = useState("auth-service");
  const [environment, setEnvironment] = useState("MGM");
  const [alertTime, setAlertTime] = useState("2026-06-10T09:00:00Z");
  const [result, setResult] = useState<MetricsResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const run = async () => {
    setPending(true);
    setError(null);
    try {
      setResult(await fetchRecentDeployments({ service, environment, alert_time: alertTime }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Request failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <MetricCard title="Recent deployments" onRun={run} pending={pending} error={error} onRetry={run}>
      <MiniForm
        fields={[
          { label: "Service", value: service, onChange: setService },
          { label: "Environment", value: environment, onChange: setEnvironment },
          { label: "Alert time", value: alertTime, onChange: setAlertTime, mono: true },
        ]}
      />
      {pending ? <LoadingSkeleton lines={3} /> : null}
      {result ? <ToolResultPanel data={result} title="Deployments" /> : null}
    </MetricCard>
  );
}

function ServiceContextCard() {
  const [service, setService] = useState("bet-service");
  const [environment, setEnvironment] = useState("GIB-UKGC");
  const [result, setResult] = useState<MetricsResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const run = async () => {
    setPending(true);
    setError(null);
    try {
      setResult(await fetchServiceContext({ service, environment }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Request failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <MetricCard title="Service context" onRun={run} pending={pending} error={error} onRetry={run}>
      <MiniForm
        fields={[
          { label: "Service", value: service, onChange: setService },
          { label: "Environment", value: environment, onChange: setEnvironment },
        ]}
      />
      {pending ? <LoadingSkeleton lines={3} /> : null}
      {result ? <ToolResultPanel data={result} title="Service context" /> : null}
    </MetricCard>
  );
}

function SimilarIncidentsCard() {
  const [service, setService] = useState("auth-service");
  const [symptom, setSymptom] = useState("login failure spike after deployment");
  const [result, setResult] = useState<MetricsResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const run = async () => {
    setPending(true);
    setError(null);
    try {
      setResult(await fetchSimilarIncidents({ service, symptom }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Request failed");
    } finally {
      setPending(false);
    }
  };

  return (
    <MetricCard title="Similar incidents" onRun={run} pending={pending} error={error} onRetry={run}>
      <MiniForm
        fields={[
          { label: "Service", value: service, onChange: setService },
          { label: "Symptom", value: symptom, onChange: setSymptom },
        ]}
      />
      {pending ? <LoadingSkeleton lines={3} /> : null}
      {result ? <ToolResultPanel data={result} title="Similar incidents" /> : null}
    </MetricCard>
  );
}

function EscalationCard() {
  const { bootstrap } = useDemo();
  const liveReady = isLiveDispatchReady(bootstrap?.notification);
  const [service, setService] = useState("bet-service");
  const [severity, setSeverity] = useState("P1");
  const [result, setResult] = useState<MetricsResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const run = async () => {
    setPending(true);
    setError(null);
    try {
      setResult(await fetchEscalationPreview({ service, severity }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Request failed");
    } finally {
      setPending(false);
    }
  };

  const previewOnly =
    !liveReady || result?.safe_preview_only === true || result?.sends_notifications === false;

  return (
    <MetricCard
      title={liveReady ? "Escalation (live dispatch)" : "Escalation preview"}
      onRun={run}
      pending={pending}
      error={error}
      onRetry={run}
    >
      <div className={liveReady ? "live-banner" : "preview-banner"}>
        {liveReady
          ? "LIVE DISPATCH ENABLED — use Escalate on-call in the incident flow to send notifications"
          : "PREVIEW ONLY — no notifications sent"}
      </div>
      {previewOnly && result ? null : null}
      <MiniForm
        fields={[
          { label: "Service", value: service, onChange: setService },
          { label: "Severity", value: severity, onChange: setSeverity },
        ]}
      />
      {pending ? <LoadingSkeleton lines={3} /> : null}
      {result ? <ToolResultPanel data={result} title="Escalation" /> : null}
    </MetricCard>
  );
}

function MetricCard({
  title,
  children,
  onRun,
  pending,
  error,
  onRetry,
}: {
  title: string;
  children: ReactNode;
  onRun: () => void;
  pending: boolean;
  error: string | null;
  onRetry: () => void;
}) {
  return (
    <section className="panel">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <h3 className="panel-title" style={{ margin: 0 }}>
          {title}
        </h3>
        <button type="button" className="btn btn-primary" onClick={() => void onRun()} disabled={pending}>
          {pending ? "Running…" : "Run"}
        </button>
      </div>
      {error ? <ErrorState message={error} onRetry={onRetry} /> : null}
      {children}
    </section>
  );
}

function MiniForm({
  fields,
}: {
  fields: {
    label: string;
    value: string;
    onChange: (v: string) => void;
    mono?: boolean;
  }[];
}) {
  return (
    <div className="form-grid" style={{ marginBottom: "12px" }}>
      {fields.map((f) => (
        <div key={f.label} className="form-row">
          <label className="label">{f.label}</label>
          <input
            className={`input${f.mono ? " mono" : ""}`}
            value={f.value}
            onChange={(e) => f.onChange(e.target.value)}
          />
        </div>
      ))}
    </div>
  );
}
