export function LoadingSkeleton({ lines = 3, height = 14 }: { lines?: number; height?: number }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          style={{
            height,
            borderRadius: "var(--radius-sm)",
            background:
              "linear-gradient(90deg, var(--bg-elevated) 25%, var(--bg-hover) 50%, var(--bg-elevated) 75%)",
            backgroundSize: "200% 100%",
            animation: "shimmer 1.2s infinite",
            width: i === lines - 1 ? "70%" : "100%",
          }}
        />
      ))}
    </div>
  );
}
