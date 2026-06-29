import type {
  AlertStreamResponse,
  AnalyzePayload,
  BootstrapResponse,
  ChatResponse,
  EscalationNotifyPayload,
  EscalationNotifyResponse,
  HealthResponse,
  HistoryResponse,
  IncidentDetailResponse,
  IncidentsHistoryResponse,
  InvestigationsResponse,
  KbManifestResponse,
  MetricsResult,
  TriageResponse,
} from "@/types/api";

const JSON_HEADERS: HeadersInit = {
  Accept: "application/json",
  "Content-Type": "application/json",
};

export class ApiError extends Error {
  status: number;
  reason?: string;

  constructor(message: string, status: number, reason?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.reason = reason;
  }
}

async function parseJson<T>(response: Response): Promise<T> {
  const data = (await response.json()) as T & { message?: string; reason?: string };
  if (!response.ok) {
    const msg =
      typeof data === "object" && data && "message" in data && data.message
        ? String(data.message)
        : response.statusText;
    throw new ApiError(
      msg || `Request failed (${response.status})`,
      response.status,
      typeof data === "object" && data && "reason" in data ? String(data.reason) : undefined,
    );
  }
  return data;
}

export async function fetchKbManifest(): Promise<KbManifestResponse> {
  const response = await fetch("/api/kb/manifest", {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  return parseJson<KbManifestResponse>(response);
}

export async function fetchBootstrap(): Promise<BootstrapResponse> {
  const response = await fetch("/api/bootstrap", {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  return parseJson<BootstrapResponse>(response);
}

export async function fetchHealth(deep = false): Promise<HealthResponse> {
  const qs = deep ? "?deep=1" : "";
  const response = await fetch(`/api/health${qs}`, {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  return parseJson<HealthResponse>(response);
}

export async function fetchAlertStream(includeRows = true): Promise<AlertStreamResponse> {
  const qs = includeRows ? "?include_rows=true" : "";
  const response = await fetch(`/api/alert-stream${qs}`, {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  return parseJson<AlertStreamResponse>(response);
}

export async function fetchIncidentsHistory(limit = 50): Promise<IncidentsHistoryResponse> {
  const response = await fetch(`/api/incidents/history?limit=${limit}`, {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  return parseJson<IncidentsHistoryResponse>(response);
}

export async function fetchIncidentDetail(sessionId: string): Promise<IncidentDetailResponse> {
  const response = await fetch(`/api/incidents/history/${encodeURIComponent(sessionId)}`, {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  return parseJson<IncidentDetailResponse>(response);
}

export async function fetchInvestigations(limit = 50): Promise<InvestigationsResponse> {
  const response = await fetch(`/api/investigations?limit=${limit}`, {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  return parseJson<InvestigationsResponse>(response);
}

export async function postIncidentStatus(
  incidentId: string,
  status: "open" | "in_process" | "resolved" | "escalated",
): Promise<{ ok: boolean; incident_id: string; status: string }> {
  const response = await fetch(`/api/incidents/${encodeURIComponent(incidentId)}/status`, {
    method: "POST",
    headers: JSON_HEADERS,
    credentials: "same-origin",
    body: JSON.stringify({ status }),
  });
  return parseJson<{ ok: boolean; incident_id: string; status: string }>(response);
}

export async function postChat(message: string, sessionId?: string | null): Promise<ChatResponse> {
  const body: { message: string; session_id?: string } = { message };
  if (sessionId) body.session_id = sessionId;

  const response = await fetch("/api/chat", {
    method: "POST",
    headers: JSON_HEADERS,
    credentials: "same-origin",
    body: JSON.stringify(body),
  });
  return parseJson<ChatResponse>(response);
}

export async function postTriage(payload: AnalyzePayload): Promise<TriageResponse> {
  const response = await fetch("/api/triage", {
    method: "POST",
    headers: JSON_HEADERS,
    credentials: "same-origin",
    body: JSON.stringify(payload),
  });
  return parseJson<TriageResponse>(response);
}

export async function postIncidentAnalyze(payload: AnalyzePayload): Promise<TriageResponse> {
  const response = await fetch("/api/incident/analyze", {
    method: "POST",
    headers: JSON_HEADERS,
    credentials: "same-origin",
    body: JSON.stringify(payload),
  });
  return parseJson<TriageResponse>(response);
}

export async function postFollowUp(sessionId: string, question: string): Promise<ChatResponse> {
  const response = await fetch("/api/follow-up", {
    method: "POST",
    headers: JSON_HEADERS,
    credentials: "same-origin",
    body: JSON.stringify({ session_id: sessionId, question }),
  });
  return parseJson<ChatResponse>(response);
}

export async function fetchHistory(sessionId?: string | null): Promise<HistoryResponse> {
  const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
  const response = await fetch(`/api/history${qs}`, {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  return parseJson<HistoryResponse>(response);
}

export async function postPostMortemDraft(
  sessionId: string,
  draft: string,
): Promise<{ ok: boolean; session_id: string; post_mortem_draft: string }> {
  const response = await fetch(`/api/incidents/history/${encodeURIComponent(sessionId)}/post-mortem`, {
    method: "POST",
    headers: JSON_HEADERS,
    credentials: "same-origin",
    body: JSON.stringify({ draft }),
  });
  return parseJson(response);
}

export async function clearHistory(sessionId?: string | null): Promise<{ ok: boolean }> {
  const response = await fetch("/api/history", {
    method: "DELETE",
    headers: JSON_HEADERS,
    credentials: "same-origin",
    body: JSON.stringify(sessionId ? { session_id: sessionId } : {}),
  });
  return parseJson(response);
}

export type UploadDocumentResult = {
  ok: boolean;
  filename: string;
  s3_key: string;
  s3_uri: string;
  size_bytes: number;
  sync_started: boolean;
  ingestion_job_id?: string | null;
  sync_warning?: string;
  message?: string;
};

export async function uploadDocument(file: File, syncKb: boolean): Promise<UploadDocumentResult> {
  const form = new FormData();
  form.append("document", file);
  if (syncKb) form.append("sync_kb", "true");

  const response = await fetch("/documents/upload?format=json", {
    method: "POST",
    credentials: "same-origin",
    body: form,
  });
  const data = (await response.json()) as UploadDocumentResult & { message?: string; reason?: string };
  if (!response.ok || !data.ok) {
    throw new ApiError(
      data.message || data.reason || `Upload failed (${response.status})`,
      response.status,
      data.reason,
    );
  }
  return data;
}

export async function postEscalationNotify(
  payload: EscalationNotifyPayload,
): Promise<EscalationNotifyResponse> {
  const response = await fetch("/api/escalation/notify", {
    method: "POST",
    headers: JSON_HEADERS,
    credentials: "same-origin",
    body: JSON.stringify(payload),
  });
  const data = (await response.json()) as EscalationNotifyResponse;
  if (!response.ok && !data.message) {
    throw new ApiError(response.statusText, response.status, data.reason as string | undefined);
  }
  return data;
}

function metricsUrl(path: string, params: Record<string, string | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value);
  }
  const qs = search.toString();
  return `/api/metrics/${path}${qs ? `?${qs}` : ""}`;
}

export async function fetchRecentDeployments(params: {
  service: string;
  environment: string;
  alert_time: string;
  lookback_hours?: string;
}): Promise<MetricsResult> {
  const response = await fetch(
    metricsUrl("recent-deployments", {
      service: params.service,
      environment: params.environment,
      alert_time: params.alert_time,
      lookback_hours: params.lookback_hours,
    }),
    { headers: { Accept: "application/json" }, credentials: "same-origin" },
  );
  return parseJson<MetricsResult>(response);
}

export async function fetchServiceContext(params: {
  service: string;
  environment: string;
  severity?: string;
}): Promise<MetricsResult> {
  const response = await fetch(metricsUrl("service-context", params), {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  return parseJson<MetricsResult>(response);
}

export async function fetchSimilarIncidents(params: {
  service: string;
  symptom: string;
  environment?: string;
  limit?: string;
}): Promise<MetricsResult> {
  const response = await fetch(metricsUrl("similar-incidents", params), {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  return parseJson<MetricsResult>(response);
}

export async function fetchEscalationPreview(params: {
  service: string;
  severity?: string;
  business_impact?: string;
}): Promise<MetricsResult> {
  const response = await fetch(metricsUrl("escalation-preview", params), {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  return parseJson<MetricsResult>(response);
}

export async function fetchBusinessImpact(params: {
  service: string;
  environment: string;
  severity: string;
  duration_minutes?: string;
}): Promise<MetricsResult> {
  const response = await fetch(metricsUrl("business-impact", params), {
    headers: { Accept: "application/json" },
    credentials: "same-origin",
  });
  return parseJson<MetricsResult>(response);
}

/** Frozen + demo contract endpoints (F2-R inventory). */
export const FROZEN_API_ENDPOINTS = [
  "GET /api/health",
  "GET /api/bootstrap",
  "GET /api/kb/manifest",
  "GET /api/alert-stream",
  "GET /api/investigations",
  "GET /api/incidents/history",
  "GET /api/incidents/history/:id",
  "GET /api/history",
  "DELETE /api/history",
  "POST /api/chat",
  "POST /api/triage",
  "POST /api/incident/analyze",
  "POST /api/follow-up",
  "POST /api/escalation/notify",
  "GET /api/metrics/recent-deployments",
  "GET /api/metrics/service-context",
  "GET /api/metrics/similar-incidents",
  "GET /api/metrics/escalation-preview",
  "GET /api/metrics/business-impact",
  "GET /api/sessions/:id/history",
] as const;
