import type { CorrelationChainStep } from "@/types/api";

const STEP_LABELS: Record<string, string> = {
  deployment: "Deployment",
  alert: "Alert",
  similar_incident: "Similar incident",
};

export function CorrelationChainTimeline({ chain }: { chain: CorrelationChainStep[] }) {
  if (!chain.length) return null;

  return (
    <ol className="correlation-chain">
      {chain.map((item, index) => (
        <li
          key={`${item.step}-${item.label}-${index}`}
          className="correlation-chain-item reveal-item"
          style={{ animationDelay: `${index * 80}ms` }}
        >
          <div className="correlation-chain-marker" aria-hidden>
            <span className="correlation-chain-dot" />
            {index < chain.length - 1 ? <span className="correlation-chain-line" /> : null}
          </div>
          <div className="correlation-chain-body">
            <div className="correlation-chain-meta">
              <span className="piter-field-label">{STEP_LABELS[item.step] || item.step}</span>
              {item.timestamp ? <span className="mono correlation-chain-time">{item.timestamp}</span> : null}
            </div>
            <div className="correlation-chain-label">{item.label}</div>
            {item.detail ? <div className="correlation-chain-detail">{item.detail}</div> : null}
          </div>
        </li>
      ))}
    </ol>
  );
}
