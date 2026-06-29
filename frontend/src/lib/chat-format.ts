import { parsePiterSection } from "./piter-format";

/** Plain text for chat bubbles — no markdown symbols. */
export function formatChatText(content: string, maxLength = 600): string {
  const lines = parsePiterSection(content);
  const plain = lines.length > 0 ? lines.join("\n") : content.replace(/[#*_`]/g, "").trim();
  if (plain.length <= maxLength) return plain;
  return `${plain.slice(0, maxLength).trim()}…`;
}

export function investigationSnippet(
  response: { piter?: { investigation?: string }; answer?: string },
  maxLines = 2,
): string {
  const lines = parsePiterSection(response.piter?.investigation || response.answer);
  return lines.slice(0, maxLines).join(" · ") || "Analysis ready — view full report in workspace.";
}
