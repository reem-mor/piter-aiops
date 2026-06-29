import { useEffect, useState } from "react";
import { fetchHealth } from "@/lib/api-contract";
import type { HealthResponse } from "@/types/api";

const ENV_LABEL = import.meta.env.VITE_PITER_ENV ?? "production";

function healthDotClass(status?: string): string {
  if (status === "ok") return "ok";
  if (status === "degraded") return "degraded";
  return "down";
}

export function StatusBar() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [utc, setUtc] = useState(() => new Date().toUTCString());

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await fetchHealth(false);
        if (!cancelled) setHealth(data);
      } catch {
        if (!cancelled) setHealth({ status: "down" });
      }
    };
    load();
    const id = setInterval(load, 30_000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    const id = setInterval(() => setUtc(new Date().toUTCString()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="status-bar">
      <span
        className={`health-dot ${healthDotClass(health?.status)}`}
        title={health?.status ?? "unknown"}
      />
      <span>
        System: <strong>{health?.status ?? "checking…"}</strong>
      </span>
      <span>Env: {ENV_LABEL}</span>
      <span className="mono" style={{ marginLeft: "auto" }}>
        {utc}
      </span>
    </header>
  );
}
