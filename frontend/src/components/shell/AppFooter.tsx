import { useEffect, useState } from "react";
import type { PageKey } from "@/types/api";
import { useDemo } from "@/context/demo";

const UI_VERSION = "demo-polish-v6";

export function AppFooter({ onNavigate }: { onNavigate: (page: PageKey) => void }) {
  const { bootstrap } = useDemo();
  const [utc, setUtc] = useState(() => new Date().toISOString().slice(11, 19));

  useEffect(() => {
    const id = window.setInterval(() => setUtc(new Date().toISOString().slice(11, 19)), 1000);
    return () => window.clearInterval(id);
  }, []);

  const bedrock = bootstrap?.use_bedrock ? "Bedrock" : "Local";
  const mode = bootstrap?.execution_mode_hint || bootstrap?.rag_backend || "demo";

  return (
    <footer className="app-footer" role="contentinfo">
      <div className="app-footer-left">
        <span>PITER Ops · Enterprise Demo</span>
        <span className="app-footer-badge">{UI_VERSION}</span>
        <span className={`app-footer-badge${bootstrap?.use_bedrock ? " app-footer-badge-live" : ""}`}>
          {bedrock}
        </span>
        <span className="app-footer-badge">{mode}</span>
      </div>
      <div className="app-footer-right">
        <button type="button" className="app-footer-link" onClick={() => onNavigate("bedrock")}>
          Bedrock Status
        </button>
        <button type="button" className="app-footer-link" onClick={() => onNavigate("knowledge")}>
          KB Manifest
        </button>
        <button type="button" className="app-footer-link" onClick={() => onNavigate("guide")}>
          Demo Guide
        </button>
        <span className="mono">UTC {utc}</span>
        <span>© {new Date().getFullYear()} PITER Ops</span>
      </div>
    </footer>
  );
}
