import { useEffect, useState } from "react";
import { ApiError, postIncidentAnalyze } from "@/lib/api-contract";
import { useSession } from "@/context/session";
import { useChatDock } from "@/context/chat-dock";
import type { ChatResponse, PiterStages } from "@/types/api";
import { PiterResponseView } from "@/components/noc/PiterResponseView";
import { PipelineProgress } from "@/components/noc/PipelineProgress";
import { MTTRPanel } from "@/components/noc/MTTRPanel";
import { ErrorState } from "@/components/noc/ErrorState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Button } from "@/components/ui/Button";
import { useDemo } from "@/context/demo";

const DEFAULTS = {
  service: "auth-service",
  environment: "production",
  severity: "critical",
  symptom: "Many users cannot log in after the latest production deployment",
  alert_time: "2026-06-09T14:30:00Z",
};

const STAGE_KEYS: (keyof PiterStages)[] = [
  "priority",
  "investigation",
  "triage",
  "escalation",
  "resolution",
];

export function AnalyzerPage() {
  const { sessionId } = useSession();
  const { registerSession, send } = useChatDock();
  const { demoImpact } = useDemo();
  const [form, setForm] = useState(DEFAULTS);
  const [pending, setPending] = useState(false);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [simStages, setSimStages] = useState<PiterStages>({});

  useEffect(() => {
    if (!pending) return;
    let i = 0;
    const id = window.setInterval(() => {
      const key = STAGE_KEYS[i % STAGE_KEYS.length];
      setSimStages((s) => ({ ...s, [key]: "…" }));
      i += 1;
    }, 900);
    return () => window.clearInterval(id);
  }, [pending]);

  const analyze = async () => {
    setPending(true);
    setError(null);
    setResponse(null);
    setSimStages({});
    try {
      const data = await postIncidentAnalyze({
        ...form,
        session_id: sessionId ?? undefined,
      });
      setResponse(data);
      const sid = data.memory?.session_id || data.session_id;
      if (sid) registerSession(sid, undefined, { incident: true, activate: true });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Analysis failed");
    } finally {
      setPending(false);
    }
  };

  const set = (key: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const stages = pending ? simStages : response?.piter_stages || response?.piter;

  return (
    <div className="grid-stack">
      <PageHeader
        title="Incident Analyzer"
        subtitle="Run a structured PITER investigation against Bedrock Agent or local fallback knowledge"
      />

      <div className="panel">
        <div className="form-grid">
          <div className="form-row">
            <label className="label" htmlFor="svc">
              Service
            </label>
            <input id="svc" className="input" value={form.service} onChange={set("service")} />
          </div>
          <div className="form-row">
            <label className="label" htmlFor="env">
              Environment
            </label>
            <input id="env" className="input" value={form.environment} onChange={set("environment")} />
          </div>
          <div className="form-row">
            <label className="label" htmlFor="sev">
              Severity
            </label>
            <select id="sev" className="select" value={form.severity} onChange={set("severity")}>
              <option value="critical">critical</option>
              <option value="P1">P1</option>
              <option value="P2">P2</option>
              <option value="P3">P3</option>
            </select>
          </div>
          <div className="form-row">
            <label className="label" htmlFor="time">
              Alert time (ISO)
            </label>
            <input id="time" className="input mono" value={form.alert_time} onChange={set("alert_time")} />
          </div>
        </div>
        <div className="form-row" style={{ marginTop: "12px" }}>
          <label className="label" htmlFor="symptom">
            Symptom
          </label>
          <textarea id="symptom" className="textarea" value={form.symptom} onChange={set("symptom")} rows={3} />
        </div>
        <Button variant="primary" style={{ marginTop: "16px" }} onClick={() => void analyze()} disabled={pending} loading={pending}>
          {pending ? "Running pipeline…" : "Run analysis"}
        </Button>
      </div>

      <PipelineProgress active={pending} stages={stages as PiterStages} />
      {error ? <ErrorState message={error} onRetry={analyze} /> : null}
      {response && !pending ? (
        <>
          <MTTRPanel demoImpact={demoImpact} triageResult={response} noiseSuppressed={0} />
          <PiterResponseView response={response} onFollowUp={(q) => void send(q)} />
        </>
      ) : null}
    </div>
  );
}
