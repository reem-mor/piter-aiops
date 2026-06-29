import { stripMarkdown } from "@/lib/piter-format";

export function IncidentTimeline({ triage }: { triage: string }) {
  const steps = triage
    .split("\n")
    .map((line) => stripMarkdown(line.trim()))
    .filter(Boolean);

  if (!steps.length) return null;

  return (
    <ol style={{ margin: 0, paddingLeft: "20px", display: "flex", flexDirection: "column", gap: "8px" }}>
      {steps.map((step, i) => (
        <li key={i} style={{ fontSize: "0.875rem", color: "var(--text-primary)", lineHeight: 1.5 }}>
          {step.replace(/^\d+\.\s*/, "")}
        </li>
      ))}
    </ol>
  );
}
