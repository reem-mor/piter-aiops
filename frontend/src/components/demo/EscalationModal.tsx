import { useEffect, useMemo, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { fetchEscalationPreview, postEscalationNotify } from "@/lib/api-contract";
import { useDemo } from "@/context/demo";
import { useToast } from "@/context/toast";
import { isLiveDispatchReady, notificationModeLabel } from "@/lib/notification-ui";
import type { MetricsResult } from "@/types/api";
import { AlertBanner } from "@/components/ui/AlertBanner";
import { Button } from "@/components/ui/Button";

export function EscalationModal({
  incidentId,
  service,
  severity,
  mode = "escalate",
  onClose,
}: {
  incidentId: string;
  service: string;
  severity: string;
  mode?: "escalate" | "email";
  onClose: () => void;
}) {
  const { bootstrap, markEscalated, pauseStorm } = useDemo();
  const { push } = useToast();
  const [channel, setChannel] = useState<"email" | "sms">(mode === "email" ? "email" : "email");
  const [preview, setPreview] = useState<MetricsResult | null>(null);
  const [pending, setPending] = useState(false);
  const notification = bootstrap?.notification;
  const liveReady = isLiveDispatchReady(notification);
  const modeLabel = notificationModeLabel(notification);
  // The preview endpoint itself never sends (safe_preview_only is always true);
  // dispatch availability is decided by bootstrap readiness only.
  const previewOnly = !liveReady;

  const emailRecipients = useMemo(() => {
    const fromBootstrap = notification?.email_recipients;
    if (Array.isArray(fromBootstrap) && fromBootstrap.length) {
      return fromBootstrap.map(String);
    }
    const fromPreview = preview?.email_recipients;
    if (Array.isArray(fromPreview) && fromPreview.length) {
      return fromPreview.map(String);
    }
    const single = preview?.recipient || preview?.on_call_email;
    return single ? [String(single)] : [];
  }, [notification?.email_recipients, preview]);

  useEffect(() => {
    setChannel(mode === "email" ? "email" : "email");
    void fetchEscalationPreview({ service, severity }).then(setPreview);
    pauseStorm();
  }, [service, severity, pauseStorm, mode]);

  const recipient =
    channel === "email"
      ? String(preview?.recipient || preview?.on_call_email || emailRecipients[0] || "on-call@ops")
      : String(preview?.sms_recipient || preview?.on_call_phone || "+1-555-0100");
  const team = String(preview?.team || preview?.escalation_team || "Platform On-Call");
  const rootCause = String(preview?.root_cause || preview?.summary || `P1 ${service} degradation`);
  const checks = Array.isArray(preview?.immediate_checks)
    ? (preview.immediate_checks as string[])
    : ["Verify error rate spike", "Check recent deployment", "Confirm on-call availability"];

  const confirm = async () => {
    setPending(true);
    try {
      const result = await postEscalationNotify({
        channel,
        incident_id: incidentId,
        service,
        severity,
        message: `P1 ${service}: escalation requested via ${channel}`,
      });
      const dispatchMode = result.mode || (result.sent ? "live" : "mock");
      const deliveries = result.deliveries || [];
      if (deliveries.length) {
        const summary = deliveries
          .map((d) => `${d.recipient}: ${d.sent ? "sent" : "failed"}${d.message_id ? ` (${d.message_id})` : ""}`)
          .join(" · ");
        push(`Dispatch receipt · ${channel} · ${summary}`, result.sent ? "success" : "error");
      } else {
        push(
          `Dispatch receipt · ${channel} · mode=${dispatchMode} · sent=${String(result.sent ?? false)}`,
          result.sent ? "success" : "error",
        );
      }
      markEscalated(incidentId);
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Dispatch failed";
      push(liveReady ? message : "Escalation recorded (preview/mock gate)", liveReady ? "error" : "success");
      if (!liveReady) {
        markEscalated(incidentId);
        onClose();
      }
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="modal-backdrop modal-backdrop-top" role="presentation">
      <div className="modal" role="dialog" aria-labelledby="esc-title">
        <h2 id="esc-title" className="panel-title" style={{ fontSize: "1rem" }}>
          {mode === "email" ? "Email notification preview" : "Escalation preview"}
        </h2>

        <AlertBanner
          title={previewOnly ? "Preview only — human approval required" : "Live dispatch armed — confirm to send"}
          variant="warning"
        >
          {previewOnly
            ? `No live notifications will be sent (${modeLabel}). Review the draft below before any dispatch.`
            : "Nothing is sent until you press Confirm dispatch — then the server dispatches via SES to the recipients below."}
        </AlertBanner>

        <div className="escalation-preview-card panel" style={{ marginTop: 12 }}>
          <div className="escalation-preview-row">
            <span className="escalation-preview-label">Summary</span>
            <span>{rootCause}</span>
          </div>
          <div className="escalation-preview-row">
            <span className="escalation-preview-label">Severity</span>
            <span>{severity}</span>
          </div>
          <div className="escalation-preview-row">
            <span className="escalation-preview-label">Service</span>
            <span>{service}</span>
          </div>
          <div className="escalation-preview-row">
            <span className="escalation-preview-label">Incident</span>
            <span className="mono">{incidentId}</span>
          </div>
          <div className="escalation-preview-row">
            <span className="escalation-preview-label">Owner team</span>
            <span>{team}</span>
          </div>
          {channel === "email" && emailRecipients.length > 0 ? (
            <div className="escalation-preview-row escalation-recipients-row">
              <span className="escalation-preview-label">Recipients ({emailRecipients.length})</span>
              <ul className="escalation-recipient-list">
                {emailRecipients.map((email) => (
                  <li key={email} className="mono">
                    {email}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="escalation-preview-row">
              <span className="escalation-preview-label">Recipient</span>
              <span className="mono">{recipient}</span>
            </div>
          )}
          <div className="escalation-preview-row">
            <span className="escalation-preview-label">Immediate checks</span>
            <ul className="piter-bullet-list" style={{ margin: 0 }}>
              {checks.map((c) => (
                <li key={c}>{c}</li>
              ))}
            </ul>
          </div>
        </div>

        <div className="form-row" style={{ marginTop: 12 }}>
          <label className="label">Channel</label>
          <select className="select" value={channel} onChange={(e) => setChannel(e.target.value as "email" | "sms")}>
            <option value="email">Email</option>
            <option value="sms">SMS</option>
          </select>
        </div>

        <div style={{ display: "flex", gap: "8px", marginTop: "16px" }}>
          <Button variant="secondary" onClick={onClose}>
            Close preview
          </Button>
          <Button variant="primary" onClick={() => void confirm()} disabled={pending || previewOnly} loading={pending}>
            {pending ? "Dispatching…" : "Confirm dispatch"}
          </Button>
        </div>
        {previewOnly ? (
          <p className="mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: 8 }}>
            <AlertTriangle size={12} style={{ display: "inline", verticalAlign: "middle" }} /> Dispatch
            disabled in preview mode — demo focuses on draft quality.
          </p>
        ) : null}
      </div>
    </div>
  );
}
