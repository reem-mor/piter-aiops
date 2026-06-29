import { useEffect, useState } from "react";
import { Check, Circle, Loader2 } from "lucide-react";
import type { ChatResponse } from "@/types/api";

const PIPELINE_STAGES = [
  { key: "alert", label: "Reading incident context…" },
  { key: "kb", label: "Searching knowledge base…" },
  { key: "runbook", label: "Retrieving service runbook…" },
  { key: "deploy", label: "Checking recent deployments…" },
  { key: "actions", label: "Querying logs through MCP tool…" },
  { key: "owner", label: "Looking up service owner and escalation policy…" },
  { key: "similar", label: "Searching similar past incidents…" },
  { key: "piter", label: "Generating source-grounded action plan…" },
] as const;

function stageComplete(response: ChatResponse, key: (typeof PIPELINE_STAGES)[number]["key"]): boolean {
  switch (key) {
    case "alert":
      return Boolean(response.alert || response.piter?.investigation);
    case "deploy":
      return Boolean(response.suspect_deployment);
    case "kb":
      return Boolean(response.sources?.length || response.matched_runbook);
    case "runbook":
      return Boolean(response.matched_runbook || response.sources?.length);
    case "similar":
      return Array.isArray(response.similar_incidents) && response.similar_incidents.length > 0;
    case "owner":
      return Boolean(response.owner?.owner_team || response.owner?.primary_oncall);
    case "actions":
      return Boolean(response.tool_results?.length);
    case "piter":
      return Boolean(response.piter?.priority && response.piter?.investigation);
    default:
      return false;
  }
}

export function AgentEnrichmentPipeline({
  response,
  analyzing,
  stepIndex = -1,
  revealOnComplete = false,
}: {
  response?: ChatResponse | null;
  analyzing?: boolean;
  stepIndex?: number;
  revealOnComplete?: boolean;
}) {
  const [revealedCount, setRevealedCount] = useState(0);

  useEffect(() => {
    if (!revealOnComplete || !response || analyzing) {
      setRevealedCount(0);
      return;
    }
    setRevealedCount(0);
    const timers = PIPELINE_STAGES.map((_, i) =>
      window.setTimeout(() => setRevealedCount(i + 1), (i + 1) * 120),
    );
    return () => timers.forEach((t) => window.clearTimeout(t));
  }, [revealOnComplete, response, analyzing]);

  return (
    <section className="enrichment-pipeline reveal-item" aria-label="Agent enrichment pipeline">
      <div className="enrichment-pipeline-header">
        <h3 className="enrichment-pipeline-title">Agent Enrichment Pipeline</h3>
        <span className="enrichment-pipeline-sub">
          {analyzing ? "Investigating…" : response ? "Enrichment complete" : "Awaiting analysis"}
        </span>
      </div>
      <div className="enrichment-pipeline-grid">
        {PIPELINE_STAGES.map((stage, i) => {
          const done = response ? stageComplete(response, stage.key) : false;
          const active = analyzing && stepIndex === i;
          const pending = analyzing && stepIndex < i && !done;
          const revealed = !revealOnComplete || revealedCount > i || analyzing;
          const showDone = done && revealed;

          return (
            <div
              key={stage.key}
              className={`enrichment-stage${showDone ? " done" : ""}${active ? " active" : ""}${pending ? " pending" : ""}${revealed ? " revealed" : ""}`}
              style={{ animationDelay: `${i * 60}ms` }}
            >
              {showDone ? (
                <Check size={14} aria-hidden />
              ) : active ? (
                <Loader2 size={14} className="btn-spinner" aria-hidden />
              ) : (
                <Circle size={14} aria-hidden />
              )}
              <span>{stage.label}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}
