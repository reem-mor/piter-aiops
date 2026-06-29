import { Card, CardHeader, CardContent } from "@/components/ui/Card";

const STEPS = [
  "Open Operations dashboard and confirm idle state — use Start Alert Stream in the top bar.",
  "Watch the alert stream populate; noise suppression and agent decisions appear in real time.",
  "At ~20 seconds, P1 modal fires — click Analyze P1 Incident to run POST /api/triage.",
  "Review structured PITER analysis: Priority, Investigation, Triage, Escalation, Resolution.",
  "Open Agent Chat for follow-up questions; use suggested chips for guided prompts.",
  "Preview escalation (no live dispatch without token) and show safety guardrail panel.",
  "Show MTTR demo estimates and History for session memory continuity.",
];

export function DemoGuidePage() {
  return (
    <div className="grid-stack">
      <h1 style={{ margin: 0, fontSize: "1.125rem" }}>Demo Guide</h1>
      <Card>
        <CardHeader
          title="60–90 second class flow"
          description="Aligned with docs/demo_script.md — backend APIs unchanged."
        />
        <CardContent>
          <ol className="demo-guide-steps">
            {STEPS.map((step) => (
              <li key={step} className="demo-guide-step">
                {step}
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}
