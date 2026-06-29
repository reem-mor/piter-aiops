import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "./Badge";
import { cn } from "@/lib/utils";

export type MetricTone = "default" | "info" | "success" | "warning" | "danger" | "purple";

const toneClass: Record<MetricTone, string> = {
  default: "",
  info: "kpi-tone-info",
  success: "kpi-tone-success",
  warning: "kpi-tone-warning",
  danger: "kpi-tone-danger",
  purple: "kpi-tone-purple",
};

export function MetricCard({
  label,
  value,
  mono,
  demo,
  hint,
  icon: Icon,
  tone = "default",
  className,
}: {
  label: string;
  value: string | number;
  mono?: boolean;
  demo?: boolean;
  hint?: ReactNode;
  icon?: LucideIcon;
  tone?: MetricTone;
  className?: string;
}) {
  return (
    <div className={cn("panel kpi-card", demo && "kpi-demo", toneClass[tone], className)}>
      <div className="kpi-label">
        {Icon ? <Icon className="kpi-icon" aria-hidden size={14} /> : null}
        <span>{label}</span>
        {demo ? <Badge variant="demo">DEMO</Badge> : null}
      </div>
      <div className={mono ? "mono kpi-value" : "kpi-value"}>{value}</div>
      {hint ? <div className="kpi-hint">{hint}</div> : null}
    </div>
  );
}
