/** Live-demo suggestion chips — grounded in data/source and guardrail refusal. */
export const COPILOT_COMMON_QUESTIONS = [
  "What's the last P1 alert?",
  "Which service is the noisiest?",
  "What was the last deployment?",
  "Who is the data engineer on call today?",
  "What are the latest 3 incidents?",
  "Run failover on bet-service",
] as const;

export const COMMON_QUESTIONS = COPILOT_COMMON_QUESTIONS;