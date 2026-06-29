# Figma Design Rules — PITER AiOps

Use this document when syncing designs via Figma MCP or handoff to engineers.

## Stack

- React 19 + Vite + TypeScript
- Styling: CSS variables in `src/design-system/tokens.css` + `src/styles.css`
- Tailwind is configured but **not active** in components — use CSS classes and tokens
- Icons: `lucide-react` (16–20px, stroke 2)

## Token source

All colors, spacing, typography, and motion live in:

```
frontend/src/design-system/tokens.css
```

### Semantic colors

| Token | Use |
|-------|-----|
| `--ai-cyan` | Live systems, agent tools, stream counters |
| `--intel-purple` | Agent reasoning, guardrails |
| `--sev-p1` / `--critical-glow` | P1 incidents, critical mode |
| `--warning` | Amber alerts, demo estimates |
| `--success` | Resolved, MTTR wins |

### Layout

| Token | Value |
|-------|-------|
| `--sidebar-width` | 220px |
| `--dock-width` | 420px |
| `--content-max-width` | 1440px |

### Critical mode

Apply class `critical-mode` on `.app-shell` when P1 is active. Overrides accent and glow tokens.

## Component locations

| Area | Path |
|------|------|
| UI primitives | `src/components/ui/` — Card, Badge, Button, AlertBanner, MetricCard, SourceBadge |
| NOC panels | `src/components/noc/` — PiterAnalysisPanel, MTTRPanel, SafetyGuardrail |
| Shell | `src/components/shell/` — AppShell, Sidebar, TopBar, ChatDock |
| Demo | `src/components/demo/` — P1Modal, EscalationModal, CriticalIncidentBanner |

## Patterns

- **Panels**: `.panel` with optional `.panel-elevated` or `.panel-critical`
- **Badges**: severity via `.ui-badge-*`, source via `SourceBadge`
- **Buttons**: `.btn`, `.btn-primary`, `.btn-danger`, `.btn-ghost`
- **No raw markdown** in analysis UI — structured fields and bullet lists only

## Design-to-code workflow

1. Read tokens from `tokens.css` before hardcoding hex values
2. Map Figma components to `src/components/ui/` primitives
3. Use Space Grotesk for display labels, DM Sans for body, IBM Plex Mono for metrics
4. Prefer 150–250ms transitions; respect `prefers-reduced-motion`
