import { useState } from "react";
import { AlertBanner } from "@/components/ui/AlertBanner";
import { Button } from "@/components/ui/Button";
import { useDemo } from "@/context/demo";
import { useChatDock } from "@/context/chat-dock";
import { useSession } from "@/context/session";
import { useNavigate } from "@/context/navigation";
import { alertToTriagePayload } from "@/lib/storm-engine";
import { postTriage } from "@/lib/api-contract";
import { formatCurrencyUsd, formatNumber } from "@/lib/piter-format";
import { EscalationModal } from "./EscalationModal";

export function CriticalIncidentBanner() {
  const {
    demoMode,
    p1Row,
    p1Shown,
    triageResult,
    triageAnalyzing,
    showP1Modal,
    pauseStorm,
    resumeStorm,
    setTriageResult,
    setTriageAnalyzing,
    demoImpact,
  } = useDemo();
  const { openWith, registerSession } = useChatDock();
  const { setSessionId } = useSession();
  const navigate = useNavigate();
  const analyzing = triageAnalyzing;
  const [showEscalation, setShowEscalation] = useState(false);
  const [escalationMode, setEscalationMode] = useState<"escalate" | "email">("escalate");

  if (!demoMode || !p1Row || showP1Modal) return null;
  if (!p1Shown && !triageResult) return null;

  const incidentId = p1Row.incident_candidate_id || `INC-${p1Row.alert_id}`;
  const impact = triageResult?.impact;
  const users =
    impact?.users_affected != null
      ? formatNumber(Number(impact.users_affected))
      : demoImpact?.users_affected != null
        ? formatNumber(Number(demoImpact.users_affected))
        : null;
  const revenue =
    impact?.revenue_impact_usd_per_hour != null
      ? formatCurrencyUsd(Number(impact.revenue_impact_usd_per_hour))
      : demoImpact?.revenue_impact_usd_per_hour != null
        ? formatCurrencyUsd(Number(demoImpact.revenue_impact_usd_per_hour))
        : null;

  const analyze = async () => {
    if (analyzing || triageResult) return;
    pauseStorm();
    setTriageAnalyzing(true);
    try {
      const data = await postTriage(alertToTriagePayload(p1Row));
      setTriageResult(data);
      const sid = data.memory?.session_id || data.session_id;
      if (sid) {
        registerSession(sid, `${p1Row.service} P1`, { incident: true, activate: true });
        setSessionId(sid);
      }
      navigate("home");
    } finally {
      setTriageAnalyzing(false);
    }
  };

  return (
    <>
      <AlertBanner title="P1 INCIDENT CANDIDATE DETECTED" variant="critical">
        <p className="banner-headline">
          {p1Row.title} — {p1Row.service}
        </p>
        {triageResult?.business_impact ? (
          <p style={{ marginTop: 8 }}>{triageResult.business_impact}</p>
        ) : (
          <p style={{ marginTop: 8, color: "var(--text-secondary)" }}>
            <strong>Business risk:</strong> Revenue, customer trust, SLA, and reputation impact. Alert
            storm paused for human review.
          </p>
        )}
        {(users || revenue) && (
          <p className="mono" style={{ marginTop: 8, fontSize: "0.8125rem" }}>
            {users ? `Users affected: ~${users}` : null}
            {users && revenue ? " · " : null}
            {revenue ? `Revenue at risk: ${revenue}/hr` : null}
          </p>
        )}
        <div className="alert-banner-actions">
          {!triageResult ? (
            <Button variant="primary" loading={analyzing} onClick={() => void analyze()}>
              Analyze Incident
            </Button>
          ) : null}
          <Button
            variant="secondary"
            onClick={() => {
              setEscalationMode("escalate");
              setShowEscalation(true);
            }}
          >
            Escalate On-Call
          </Button>
          <Button
            variant="secondary"
            onClick={() =>
              openWith({
                message: "What should I check next for this P1 incident?",
                sessionId: triageResult?.memory?.session_id || triageResult?.session_id,
                alert: p1Row,
              })
            }
          >
            Open Chat
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              setEscalationMode("email");
              setShowEscalation(true);
            }}
          >
            Notify via Email
          </Button>
          <Button variant="ghost" onClick={() => resumeStorm()}>
            Continue Live
          </Button>
        </div>
      </AlertBanner>
      {showEscalation ? (
        <EscalationModal
          incidentId={incidentId}
          service={p1Row.service}
          severity={p1Row.severity}
          mode={escalationMode}
          onClose={() => setShowEscalation(false)}
        />
      ) : null}
    </>
  );
}
