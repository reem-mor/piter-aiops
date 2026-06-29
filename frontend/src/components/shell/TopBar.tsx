import { useCallback, useEffect, useState } from "react";
import { Pause, Play, RotateCcw } from "lucide-react";
import { fetchHealth } from "@/lib/api-contract";
import { useDemo } from "@/context/demo";
import { isLiveDispatchReady } from "@/lib/notification-ui";
import { useNavigate } from "@/context/navigation";
import type { HealthResponse } from "@/types/api";

function healthDotClass(status: string | undefined): string {
  if (status === "ok") return "ok";
  if (status === "degraded") return "degraded";
  return "down";
}

export function TopBar() {
  const navigate = useNavigate();
  const {
    demoMode,
    startStorm,
    resetDemo,
    pauseStorm,
    resumeStorm,
    bootstrap,
    wallSec,
    visible,
    paused,
    criticalMode,
    p1Shown,
  } = useDemo();
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [utc, setUtc] = useState(() => new Date().toISOString().slice(11, 19));

  const loadHealth = useCallback(async () => {
    try {
      setHealth(await fetchHealth(true));
    } catch {
      setHealth({ status: "degraded" });
    }
  }, []);

  useEffect(() => {
    void loadHealth();
    const h = setInterval(() => void loadHealth(), 20_000);
    const c = setInterval(() => setUtc(new Date().toISOString().slice(11, 19)), 1000);
    return () => {
      clearInterval(h);
      clearInterval(c);
    };
  }, [loadHealth]);

  const env = bootstrap?.alert_stream?.label?.includes("GIB") ? "GIB-UKGC" : "production";
  const notifyLive = isLiveDispatchReady(bootstrap?.notification);
  const agentLabel = criticalMode || p1Shown ? "Alert Mode" : "Ready";
  const agentClass = criticalMode || p1Shown ? "agent-pill-alert" : "agent-pill-ready";

  return (
    <header className="top-bar">
      <button type="button" className="top-bar-brand" onClick={() => navigate("home")}>
        <span className="top-bar-logo" aria-hidden>
          ◆
        </span>
        <span className="top-bar-title">PITER Ops</span>
        <span className="top-bar-sub">AI Incident Operations Center</span>
      </button>

      <div className="top-bar-center">
        <span className="status-chip status-chip-demo">Demo Mode</span>
        <span className={`status-chip ${notifyLive ? "status-chip-live" : "status-chip-preview"}`}>
          {notifyLive ? "AWS Connected" : "Preview Mode"}
        </span>
        <span className={`status-chip ${agentClass}`}>Agent: {agentLabel}</span>
        {demoMode ? (
          <span className="storm-timer mono" title="Storm playback elapsed">
            Storm {wallSec.toFixed(0)}s · {visible.length} alerts
            {paused ? " · paused" : ""}
          </span>
        ) : null}
        <span className="mono top-bar-meta">ENV {env}</span>
        <span className="mono top-bar-meta">UTC {utc}</span>
        <span className="top-bar-health" title={`Infrastructure: ${health?.status ?? "unknown"}`}>
          <span className={`health-dot ${healthDotClass(health?.status)}`} />
          Infra
        </span>
      </div>

      <div className="top-bar-actions">
        {demoMode ? (
          <>
            <button
              type="button"
              className="btn btn-icon"
              onClick={paused ? resumeStorm : pauseStorm}
              title={paused ? "Resume stream" : "Pause stream"}
            >
              {paused ? <Play size={16} /> : <Pause size={16} />}
            </button>
            <button type="button" className="btn" onClick={resetDemo} title="Reset demo">
              <RotateCcw size={14} /> Reset
            </button>
          </>
        ) : null}
        {!demoMode ? (
          <button type="button" className="btn btn-primary" onClick={startStorm}>
            <Play size={14} /> Start Alert Stream
          </button>
        ) : null}
        <span className="top-bar-avatar" title="Operator">
          OP
        </span>
      </div>
    </header>
  );
}
