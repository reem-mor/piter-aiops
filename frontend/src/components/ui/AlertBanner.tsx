import type { ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

export function AlertBanner({
  title,
  children,
  variant = "critical",
  className,
  icon,
}: {
  title: string;
  children?: ReactNode;
  variant?: "critical" | "warning" | "info";
  className?: string;
  icon?: ReactNode;
}) {
  return (
    <div className={cn("alert-banner", `alert-banner-${variant}`, className)} role="alert">
      <div className="alert-banner-icon">{icon ?? <AlertTriangle size={20} />}</div>
      <div className="alert-banner-body">
        <div className="alert-banner-title">{title}</div>
        {children ? <div className="alert-banner-content">{children}</div> : null}
      </div>
    </div>
  );
}
