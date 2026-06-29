import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { AgentEnrichmentPipeline } from "./AgentEnrichmentPipeline";
import { P1_ANALYZE_STEPS } from "@/lib/analyze-steps";

function formatElapsed(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  const mm = String(Math.floor(s / 60)).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return `00:${mm}:${ss}`;
}

const SKELETON_FIELDS = [
  "Affected service",
  "Noise reduction",
  "Log enrichment",
  "Recommended priority",
  "Detected pattern",
  "Recent deployment",
  "Similar past incident",
  "Confidence",
] as const;

export function AnalysisInProgressCard({ title = "P1 analysis in progress" }: { title?: string }) {
  const [stepIndex, setStepIndex] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);

  useEffect(() => {
    setStepIndex(0);
    setElapsedSec(0);
    const startedAt = Date.now();
    const stepTimers = P1_ANALYZE_STEPS.map((_, i) =>
      window.setTimeout(() => setStepIndex(i), i * 900),
    );
    const clock = window.setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => {
      stepTimers.forEach((t) => window.clearTimeout(t));
      window.clearInterval(clock);
    };
  }, []);

  return (
    <section className="panel analysis-in-progress-card" role="status" aria-live="polite">
      <div className="analysis-in-progress-header">
        <div className="analysis-in-progress-title-row">
          <Loader2 size={16} className="analysis-in-progress-spinner" aria-hidden />
          <h2 className="panel-title" style={{ margin: 0 }}>
            {title}
          </h2>
        </div>
        <span className="mono analysis-in-progress-elapsed">{formatElapsed(elapsedSec)}</span>
      </div>
      <p className="analysis-in-progress-sub">
        Enriching incident context with knowledge base, deployments, logs, and escalation data…
      </p>
      <AgentEnrichmentPipeline analyzing stepIndex={stepIndex} />
      <div className="piter-field-grid piter-field-grid-dense analysis-skeleton-grid" aria-hidden>
        {SKELETON_FIELDS.map((label) => (
          <div key={label} className="piter-field analysis-skeleton-field">
            <div className="piter-field-label">{label}</div>
            <div className="analysis-skeleton-bar" />
          </div>
        ))}
      </div>
    </section>
  );
}
