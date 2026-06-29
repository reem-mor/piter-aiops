/** Remove inline markdown markers from a single string. */
export function stripMarkdown(text: string | undefined | null): string {
  if (!text?.trim()) return "";
  return text
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/^[-*•]\s+/gm, "")
    .replace(/^\d+\.\s+/gm, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "$1")
    .trim();
}

/** Strip markdown symbols and split into clean bullet lines for UI rendering. */
export function parsePiterSection(text: string | undefined | null): string[] {
  if (!text?.trim()) return [];
  return text
    .split(/\n+/)
    .map((line) => stripMarkdown(line))
    .filter((line) => line.length > 0);
}

/** Normalize backend step arrays that may still carry markdown. */
export function normalizeStepList(steps: string[] | undefined | null): string[] {
  if (!steps?.length) return [];
  return steps.flatMap((step) => (step.includes("\n") ? parsePiterSection(step) : [stripMarkdown(step)])).filter(Boolean);
}

export function formatCurrencyUsd(value: number | undefined | null): string | null {
  if (value == null || Number.isNaN(value)) return null;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

export function formatNumber(value: number | undefined | null): string | null {
  if (value == null || Number.isNaN(value)) return null;
  return new Intl.NumberFormat("en-US").format(value);
}
