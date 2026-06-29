/** Shared P1 investigation progress labels (UI only — does not change storm timing). */
export const P1_ANALYZE_STEPS = [
  "Reading incident context…",
  "Searching knowledge base…",
  "Retrieving service runbook…",
  "Checking recent deployments…",
  "Querying logs through MCP tool…",
  "Looking up service owner and escalation policy…",
  "Searching similar past incidents…",
  "Generating source-grounded action plan…",
] as const;

/** Rotating "what is the agent doing" labels for chat while a reply is pending. */
export const AGENT_ACTIVITY_LABELS = [
  "Searching knowledge base…",
  "Checking recent deployments…",
  "Querying MCP / Lambda tools…",
  "Reviewing similar past incidents…",
  "Composing source-grounded answer…",
] as const;
