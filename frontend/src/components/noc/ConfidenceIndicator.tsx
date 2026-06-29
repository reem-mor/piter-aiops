export function ConfidenceIndicator({ level }: { level?: string }) {
  const normalized = (level || "medium").toLowerCase();
  const color =
    normalized.includes("high")
      ? "var(--success)"
      : normalized.includes("low")
        ? "var(--warning)"
        : "var(--accent)";

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        fontSize: "0.75rem",
        fontWeight: 600,
        textTransform: "uppercase",
        letterSpacing: "0.05em",
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: color,
        }}
      />
      Confidence: {normalized}
    </span>
  );
}
