import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export function Card({
  className,
  children,
  variant = "default",
}: {
  className?: string;
  children: ReactNode;
  variant?: "default" | "elevated" | "critical";
}) {
  return (
    <div
      className={cn(
        "panel",
        variant === "elevated" && "panel-elevated",
        variant === "critical" && "panel-critical",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function CardHeader({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <div className="card-header">
      <div>
        <h3 className="card-title">{title}</h3>
        {description ? <p className="card-description">{description}</p> : null}
      </div>
      {action}
    </div>
  );
}

export function CardContent({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cn("card-content", className)}>{children}</div>;
}
