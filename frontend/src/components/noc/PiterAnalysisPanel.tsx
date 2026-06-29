import { useState, type ReactNode } from "react";
import type { ChatResponse } from "@/types/api";
import { useChatDock } from "@/context/chat-dock";
import { useToast } from "@/context/toast";
import { useDemo } from "@/context/demo";
import { postIncidentStatus } from "@/lib/api-contract";
import { Button } from "@/components/ui/Button";
import { EscalationModal } from "@/components/demo/EscalationModal";
import { normalizeStepList, parsePiterSection, stripMarkdown } from "@/lib/piter-format";
import { CorrelationChainTimeline } from "./CorrelationChainTimeline";
import { ConfidenceIndicator } from "./ConfidenceIndicator";
import { ToolResultPanel } from "./ToolResultPanel";
import { PriorityBadge } from "./PriorityBadge";
import { SafetyGuardrail } from "./SafetyGuardrail";
import { AgentEnrichmentPipeline } from "./AgentEnrichmentPipeline";

function FieldGrid({ fields }: { fields: Array<{ label: string; value: ReactNode }> }) {
  const visible = fields.filter((f) => f.value != null && f.value !== "");
  if (!visible.length) return null;
  return (
    <div className="piter-field-grid piter-field-grid-dense">
      {visible.map((f) => (
        <div key={f.label} className="piter-field reveal-item">
          <div className="piter-field-label">{f.label}</div>
          <div className="piter-field-value">{f.value}</div>
        </div>
      ))}
    </div>
  );
}

function truncateExcerpt(text: string, max = 120): string {
  const cleaned = stripMarkdown(text);
  if (cleaned.length <= max) return cleaned;
  return `${cleaned.slice(0, max - 1).trim()}…`;
}

export function PiterAnalysisPanel({
  response,
  onFollowUp,
}: {
  response: ChatResponse;
  onFollowUp?: (question: string) => void;
}) {
  const { openWith } = useChatDock();
  const { push: toast } = useToast();
  const { visible: alertRows } = useDemo();
  const [incidentStatus, setIncidentStatus] = useState<"open" | "in_process" | "resolved">("open");
  const [showEscalation, setShowEscalation] = useState(false);
  const [showTools, setShowTools] = useState(false);

  const piter = response.piter;
  const structured = response.structured_analysis;
  const followups = response.recommended_followups || response.next_questions || [];

  const triageSteps = structured?.recommended_actions?.length
    ? structured.recommended_actions
    : response.recommended_steps?.length
      ? normalizeStepList(response.recommended_steps)
      : parsePiterSection(piter?.triage);

  const correlationChain = structured?.correlation_chain || [];
  const similarRows = structured?.similar_incidents?.length
    ? structured.similar_incidents
    : Array.isArray(response.similar_incidents)
      ? response.similar_incidents
      : [];

  const alertService = response.alert?.service ? String(response.alert.service) : null;
  const dep = (response.suspect_deployment || null) as Record<string, unknown> | null;
  const recentDeployment = dep
    ? [
        dep.service ? String(dep.service) : null,
        dep.version ? String(dep.version) : null,
        dep.deployed_at ? `(${String(dep.deployed_at)})` : null,
      ]
        .filter(Boolean)
        .join(" ") || null
    : null;

  const similarFirst =
    similarRows.length > 0
      ? String(
          (similarRows[0] as Record<string, unknown>).incident_id ||
            (similarRows[0] as Record<string, unknown>).id ||
            "",
        ) || null
      : null;

  const incidentId = response.alert?.incident_candidate_id
    ? String(response.alert.incident_candidate_id)
    : response.alert?.alert_id
      ? `INC-${String(response.alert.alert_id)}`
      : "INC-001";

  const noiseSuppressed =
    structured?.noise_suppressed ??
    alertRows.filter((r) => r.is_noise_candidate === "true").length;

  const noiseLabel =
    noiseSuppressed > 0 ? `${noiseSuppressed} duplicate alerts suppressed` : "No noise suppression yet";

  const toolsCalled =
    structured?.tools_called?.length
      ? structured.tools_called
      : (response.tool_results || []).map((t) => t.name);

  const sourcesList = (response.sources || []).slice(0, 6);
  const businessImpact =
    stripMarkdown(response.business_impact || structured?.summary || "") ||
    stripMarkdown(piter?.investigation || "");

  const escalation = structured?.escalation_suggestion;
  const escalationLine = [
    escalation?.owner_team ? `Team: ${escalation.owner_team}` : null,
    response.escalation_policy?.summary
      ? `Policy: ${String(response.escalation_policy.summary)}`
      : escalation?.escalation_path
        ? `Policy: ${escalation.escalation_path}`
        : null,
    escalation?.primary_oncall ? `On-call: ${escalation.primary_oncall}` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  const updateStatus = async (status: "in_process" | "resolved") => {
    setIncidentStatus(status);
    try {
      await postIncidentStatus(incidentId, status);
      toast(`Incident marked ${status.replace("_", " ")}`, "success");
    } catch {
      toast("Failed to update incident status", "error");
    }
  };

  const titleService = alertService || "service";
  const titleSymptom = response.alert?.title || response.alert?.symptom || "incident";

  return (
    <div className="grid-stack piter-response piter-response-lovable" id="piter-analysis-panel">
      {response.fallback_used ? (
        <div className="fallback-banner reveal-item" role="status">
          Offline knowledge base — live Bedrock unavailable ({response.mode || "local_fallback"})
        </div>
      ) : null}

      <header className="piter-response-header reveal-item">
        <div>
          <div className="piter-p1-badge">P1 Incident Analysis</div>
          <h2 className="piter-analysis-title">
            {titleSymptom} — {titleService}
          </h2>
        </div>
        <div className="piter-response-badges">
          {piter?.priority ? <PriorityBadge priority={piter.priority as "P1"} /> : null}
          <ConfidenceIndicator level={response.confidence} />
        </div>
      </header>

      <SafetyGuardrail previewOnly={response.escalation_policy?.safe_preview_only === true} />

      <AgentEnrichmentPipeline response={response} revealOnComplete />

      <section className="piter-analysis-card reveal-item">
        <FieldGrid
          fields={[
            { label: "Affected service", value: alertService },
            { label: "Noise reduction", value: noiseLabel },
            { label: "Log enrichment", value: structured?.log_enrichment },
            {
              label: "Recommended priority",
              value: structured?.severity || piter?.priority || response.priority,
            },
            { label: "Detected pattern", value: structured?.detected_pattern },
            { label: "Recent deployment", value: recentDeployment },
            { label: "Similar past incident", value: similarFirst },
            { label: "Confidence", value: response.confidence },
          ]}
        />
      </section>

      {businessImpact ? (
        <section className="piter-impact-card reveal-item">
          <h3 className="piter-section-label">Business impact</h3>
          <p className="piter-impact-text">{businessImpact}</p>
        </section>
      ) : null}

      {triageSteps.length > 0 ? (
        <section className="piter-analysis-card reveal-item">
          <h3 className="piter-section-label">Recommended action plan</h3>
          <ol className="piter-action-plan">
            {triageSteps.slice(0, 8).map((step, i) => (
              <li key={`${i}-${step.slice(0, 24)}`}>{stripMarkdown(step)}</li>
            ))}
          </ol>
        </section>
      ) : null}

      {(sourcesList.length > 0 || toolsCalled.length > 0) && (
        <section className="piter-dual-column reveal-item">
          <div className="piter-dual-col">
            <h3 className="piter-section-label">Sources</h3>
            {sourcesList.length > 0 ? (
              <ul className="piter-chip-list">
                {sourcesList.map((s, i) => {
                  const label =
                    typeof s === "string"
                      ? s
                      : String((s as { document?: string }).document || `source-${i}`);
                  const excerpt =
                    typeof s === "object" && s && "excerpt" in s
                      ? truncateExcerpt(String((s as { excerpt?: string }).excerpt || ""))
                      : null;
                  return (
                    <li key={`${label}-${i}`} className="piter-chip mono">
                      {label}
                      {excerpt ? <span className="piter-chip-detail">{excerpt}</span> : null}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="piter-muted">No sources cited</p>
            )}
          </div>
          <div className="piter-dual-col">
            <h3 className="piter-section-label">Tools called</h3>
            {toolsCalled.length > 0 ? (
              <ul className="piter-chip-list">
                {toolsCalled.map((name) => (
                  <li key={name} className="piter-chip mono">
                    {name}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="piter-muted">Awaiting MCP enrichment</p>
            )}
          </div>
        </section>
      )}

      {correlationChain.length > 0 ? (
        <section className="piter-analysis-card reveal-item">
          <h3 className="piter-section-label">Correlation chain</h3>
          <CorrelationChainTimeline chain={correlationChain} />
        </section>
      ) : null}

      {structured?.evidence?.length ? (
        <section className="piter-analysis-card reveal-item">
          <h3 className="piter-section-label">Evidence</h3>
          <ul className="piter-evidence-list">
            {structured.evidence.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {escalationLine ? (
        <div className="piter-escalation-strip reveal-item" role="status">
          {escalationLine}
        </div>
      ) : null}

      {response.tool_results && response.tool_results.length > 0 ? (
        <section className="reveal-item">
          <button
            type="button"
            className="btn btn-sm piter-tools-toggle"
            onClick={() => setShowTools((v) => !v)}
            aria-expanded={showTools}
          >
            {showTools ? "Hide enrichment details" : "Show enrichment details"}
          </button>
          {showTools
            ? response.tool_results.map((t, i) => (
                <ToolResultPanel key={i} data={t.result} title={t.name} />
              ))
            : null}
        </section>
      ) : null}

      {followups.length > 0 ? (
        <div className="reveal-item">
          <div className="piter-subsection-label">Recommended follow-ups</div>
          <div className="follow-up-chips">
            {followups.slice(0, 6).map((q) => (
              <button key={q} type="button" className="follow-up-chip" onClick={() => onFollowUp?.(q)}>
                {q}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="analysis-footer-actions reveal-item">
        {incidentStatus === "in_process" ? <span className="pill pill-warning">In process</span> : null}
        {incidentStatus === "resolved" ? <span className="pill pill-success">Resolved</span> : null}
        {incidentStatus === "open" ? (
          <Button variant="secondary" onClick={() => void updateStatus("in_process")}>
            Mark In Process
          </Button>
        ) : null}
        <Button variant="primary" onClick={() => setShowEscalation(true)}>
          Escalate On-Call
        </Button>
        <Button variant="secondary" onClick={() => onFollowUp?.("Summarize this incident")}>
          Summarize
        </Button>
        <Button
          variant="secondary"
          onClick={() =>
            openWith({
              message: "What should I check next for this P1 incident?",
              sessionId: response.memory?.session_id || response.session_id,
            })
          }
        >
          Open Incident Chat
        </Button>
        {incidentStatus !== "resolved" ? (
          <Button variant="secondary" onClick={() => void updateStatus("resolved")}>
            Mark Resolved
          </Button>
        ) : null}
      </div>

      {showEscalation ? (
        <EscalationModal
          incidentId={incidentId}
          service={alertService || "service"}
          severity={piter?.priority || response.priority || "P1"}
          onClose={() => setShowEscalation(false)}
        />
      ) : null}
    </div>
  );
}
