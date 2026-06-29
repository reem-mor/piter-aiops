import type { PiterStages } from "@/types/api";

const STAGE_ORDER: (keyof PiterStages)[] = [
  "priority",
  "investigation",
  "triage",
  "escalation",
  "resolution",
];

const LABELS: Record<string, string> = {
  priority: "Assessing priority…",
  investigation: "Reading incident context…",
  triage: "Searching knowledge base…",
  escalation: "Checking escalation policy…",
  resolution: "Building resolution plan…",
};

export function PipelineProgress({
  active,
  stages,
}: {
  active: boolean;
  stages?: PiterStages | null;
}) {
  if (!active && !stages) return null;

  const done = STAGE_ORDER.filter((k) => stages?.[k]);
  const current = active
    ? STAGE_ORDER.find((k) => !stages?.[k]) || STAGE_ORDER[STAGE_ORDER.length - 1]
    : null;

  return (
    <div className="pipeline panel">
      <h3 className="panel-title">Enrichment pipeline</h3>
      <ul className="pipeline-list">
        {STAGE_ORDER.map((key) => {
          const complete = Boolean(stages?.[key]);
          const isCurrent = active && key === current;
          return (
            <li
              key={key}
              className={`pipeline-step${complete ? " done" : ""}${isCurrent ? " active" : ""}`}
            >
              {complete ? "✓" : isCurrent ? "…" : "○"} {LABELS[key] || key}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
