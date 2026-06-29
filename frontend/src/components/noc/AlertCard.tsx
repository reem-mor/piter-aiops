import type { Investigation } from "@/types/api";
import { PriorityBadge } from "./PriorityBadge";
import { ServiceTag } from "./ServiceTag";

export function AlertCard({ item }: { item: Investigation }) {
  return (
    <article
      className="panel"
      style={{ display: "flex", flexDirection: "column", gap: "var(--space-2)" }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <PriorityBadge priority={item.priority} />
        <span className="mono" style={{ color: "var(--text-muted)" }}>
          {item.alertTime}
        </span>
      </div>
      <p style={{ margin: 0, fontSize: "0.875rem", fontWeight: 500 }}>{item.alert}</p>
      <ServiceTag service={item.service} environment={item.environment} />
      <div style={{ display: "flex", gap: "var(--space-3)", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
        <span>{item.status}</span>
        <span>·</span>
        <span>{item.conclusion}</span>
      </div>
      {item.impact ? (
        <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--sev-p2)" }}>{item.impact}</p>
      ) : null}
    </article>
  );
}
