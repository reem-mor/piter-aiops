import { useState } from "react";

export function ToolResultPanel({ data, title }: { data: unknown; title?: string }) {
  const [raw, setRaw] = useState(false);

  if (data == null) {
    return <EmptyResult />;
  }

  const record = typeof data === "object" && data !== null ? (data as Record<string, unknown>) : {};

  return (
    <div className="panel" style={{ marginTop: "var(--space-3)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <span className="panel-title" style={{ margin: 0 }}>
          {title || "Result"}
        </span>
        <button type="button" className="btn" onClick={() => setRaw((v) => !v)}>
          {raw ? "Structured" : "Raw JSON"}
        </button>
      </div>
      {raw ? (
        <pre
          className="mono"
          style={{
            margin: 0,
            padding: "12px",
            background: "var(--bg-base)",
            borderRadius: "var(--radius-sm)",
            overflow: "auto",
            fontSize: "0.75rem",
          }}
        >
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : (
        <StructuredView data={record} />
      )}
    </div>
  );
}

function EmptyResult() {
  return (
    <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.875rem" }}>No result yet.</p>
  );
}

function StructuredView({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data).filter(([k]) => k !== "ok" && k !== "error");

  if (!entries.length) {
    return <EmptyResult />;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {entries.map(([key, value]) => (
        <div key={key}>
          <div className="config-label">{key.replace(/_/g, " ")}</div>
          <div className="mono" style={{ fontSize: "0.8125rem", color: "var(--text-primary)" }}>
            {formatValue(value)}
          </div>
        </div>
      ))}
    </div>
  );
}

function formatValue(value: unknown): string {
  if (value == null) return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    if (!value.length) return "[]";
    if (typeof value[0] === "object" && value[0] !== null) {
      return value
        .slice(0, 5)
        .map((item) => {
          const r = item as Record<string, unknown>;
          return [r.incident_id, r.service, r.summary || r.title].filter(Boolean).join(" · ");
        })
        .join("\n");
    }
    return value.slice(0, 8).join(", ");
  }
  return JSON.stringify(value);
}
