import type { Priority } from "@/types/api";

const COLORS: Record<Priority, string> = {
  P1: "var(--sev-p1)",
  P2: "var(--sev-p2)",
  P3: "var(--sev-p3)",
  P4: "var(--sev-p4)",
};

export function PriorityBadge({ priority }: { priority: Priority | string }) {
  const p = (priority in COLORS ? priority : "P4") as Priority;
  return (
    <span
      style={{
        display: "inline-block",
        padding: "2px 8px",
        borderRadius: "var(--radius-sm)",
        fontSize: "0.75rem",
        fontWeight: 700,
        fontFamily: "var(--font-mono)",
        background: `${COLORS[p]}22`,
        color: COLORS[p],
        border: `1px solid ${COLORS[p]}55`,
      }}
    >
      {p}
    </span>
  );
}
