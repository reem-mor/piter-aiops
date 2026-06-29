export function ServiceTag({ service, environment }: { service: string; environment?: string }) {
  return (
    <span
      style={{
        display: "inline-flex",
        gap: "6px",
        alignItems: "center",
        fontSize: "0.75rem",
        fontFamily: "var(--font-mono)",
        color: "var(--text-secondary)",
      }}
    >
      <span style={{ color: "var(--accent)" }}>{service}</span>
      {environment ? <span style={{ opacity: 0.7 }}>@{environment}</span> : null}
    </span>
  );
}
