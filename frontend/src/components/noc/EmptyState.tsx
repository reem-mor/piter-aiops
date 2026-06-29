export function EmptyState({ title, detail }: { title: string; detail?: string }) {
  return (
    <div
      className="panel"
      style={{ textAlign: "center", padding: "32px", color: "var(--text-muted)" }}
    >
      <p style={{ margin: 0, fontWeight: 600, color: "var(--text-secondary)" }}>{title}</p>
      {detail ? <p style={{ margin: "8px 0 0", fontSize: "0.875rem" }}>{detail}</p> : null}
    </div>
  );
}
