import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type BadgeVariant = "default" | "cyan" | "purple" | "warning" | "danger" | "success" | "demo";

export function Badge({
  children,
  variant = "default",
  className,
}: {
  children: ReactNode;
  variant?: BadgeVariant;
  className?: string;
}) {
  return <span className={cn("ui-badge", `ui-badge-${variant}`, className)}>{children}</span>;
}
