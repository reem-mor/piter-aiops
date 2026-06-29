import type { Source } from "@/types/api";

export function SourceChip({ source, index }: { source: Source; index: number }) {
  const label = source.document || source.source_uri || `Source ${index + 1}`;
  return (
    <div
      className="panel"
      style={{
        padding: "var(--space-3)",
        fontSize: "0.8125rem",
        borderLeft: "3px solid var(--accent)",
      }}
    >
      <div style={{ fontWeight: 600, marginBottom: "4px", color: "var(--accent)" }}>{label}</div>
      {source.excerpt ? (
        <p style={{ margin: 0, color: "var(--text-secondary)", lineHeight: 1.5 }}>{source.excerpt}</p>
      ) : null}
      {source.score != null ? (
        <span className="mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
          score {source.score}
        </span>
      ) : null}
    </div>
  );
}
