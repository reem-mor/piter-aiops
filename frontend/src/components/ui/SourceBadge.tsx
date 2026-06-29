import { sourceLabel } from "@/lib/source-label";
import { Badge } from "./Badge";

export function SourceBadge({
  mode,
  fallbackUsed,
}: {
  mode?: string;
  fallbackUsed?: boolean;
}) {
  const label = sourceLabel(mode, fallbackUsed);
  const variant =
    fallbackUsed || mode === "local_fallback" || mode === "local"
      ? "warning"
      : mode?.includes("bedrock") || mode === "agent" || mode === "bedrock_agent"
        ? "cyan"
        : "default";

  return <Badge variant={variant}>{label}</Badge>;
}
