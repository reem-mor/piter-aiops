import type { AlertRow, ChatResponse, IncidentDetailResponse, PersistedInvestigation } from "@/types/api";

function buildPiterFromCard(card: Record<string, unknown>) {
  const sections = (card.piter_sections || card.piter) as Record<string, unknown> | undefined;
  if (!sections || typeof sections !== "object") return undefined;
  const triagePlan = sections.triage_plan;
  const triage =
    Array.isArray(triagePlan) ? triagePlan.join("\n") : String(sections.triage || sections.triage_plan || "");
  return {
    priority: String(card.priority || sections.priority || ""),
    investigation: String(sections.investigation || ""),
    triage,
    escalation: String(sections.escalation || ""),
    resolution: String(sections.resolution || ""),
  };
}

/** Map persisted session detail into a ChatResponse for PiterAnalysisPanel. */
export function detailToChatResponse(detail: IncidentDetailResponse): ChatResponse {
  const card = detail.triage_card || {};
  const piter = buildPiterFromCard(card);
  const sections = (card.piter_sections || card.piter) as Record<string, unknown> | undefined;

  return {
    ok: true,
    answer: typeof card.answer === "string" ? card.answer : undefined,
    piter,
    session_id: detail.session_id,
    memory: { session_id: detail.session_id },
    alert: detail.alert,
    priority: typeof card.priority === "string" ? card.priority : undefined,
    mode: typeof card.mode === "string" ? card.mode : undefined,
    fallback_used: Boolean(card.fallback_used),
    grounded: card.grounded as boolean | undefined,
    business_impact:
      (typeof card.business_impact === "string" ? card.business_impact : undefined) ||
      (typeof sections?.business_impact === "string" ? sections.business_impact : undefined),
    confidence:
      (typeof card.confidence === "string" ? card.confidence : undefined) ||
      (typeof sections?.confidence === "string" ? sections.confidence : undefined),
    owner: card.owner as ChatResponse["owner"],
    impact: card.impact as ChatResponse["impact"],
    similar_incidents: card.similar_incidents as ChatResponse["similar_incidents"],
    suspect_deployment: card.suspect_deployment,
    escalation_policy: card.escalation_policy as ChatResponse["escalation_policy"],
    requires_escalation: card.requires_escalation as boolean | undefined,
    recommended_steps: Array.isArray(card.recommended_steps)
      ? (card.recommended_steps as string[])
      : undefined,
    piter_stages: card.piter_stages as ChatResponse["piter_stages"],
    sources: card.sources as ChatResponse["sources"],
    recommended_followups: card.recommended_followups as string[] | undefined,
    next_questions: card.next_questions as string[] | undefined,
    matched_runbook: typeof card.matched_runbook === "string" ? card.matched_runbook : undefined,
  };
}

export function alertFromDetail(
  detail: IncidentDetailResponse,
  row?: PersistedInvestigation,
): Partial<AlertRow> {
  const a = detail.alert || {};
  return {
    alert_id: String(a.alert_id || row?.alert_id || ""),
    service: String(a.service || row?.service || ""),
    environment: String(a.environment || row?.environment || ""),
    severity: String(a.severity || row?.severity || "P1"),
    title: String(a.title || a.symptom || row?.symptom || "Investigation"),
    timestamp: String(a.timestamp || a.alert_time || row?.timestamp || ""),
  };
}
