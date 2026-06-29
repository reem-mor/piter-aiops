import { useEffect, useRef, useState } from "react";
import {
  Bot,
  ChevronRight,
  Database,
  Loader2,
  Maximize2,
  MessageSquare,
  Minimize2,
  Plus,
  RotateCcw,
  Search,
  Trash2,
  Wrench,
  X,
} from "lucide-react";
import { COPILOT_COMMON_QUESTIONS } from "@/lib/common-questions";
import { AGENT_ACTIVITY_LABELS } from "@/lib/analyze-steps";
import { DocumentUploadPanel } from "@/components/shell/DocumentUploadPanel";
import { ChatMarkdown } from "@/components/shell/ChatMarkdown";
import { useChatDock } from "@/context/chat-dock";
import { useSession } from "@/context/session";
import { useDemo } from "@/context/demo";
import { investigationSnippet } from "@/lib/chat-format";
import { SafetyGuardrail } from "@/components/noc/SafetyGuardrail";
import { Button } from "@/components/ui/Button";
import { PriorityBadge } from "@/components/noc/PriorityBadge";
import type { Priority } from "@/types/api";

export function ChatDock() {
  const {
    mode,
    setMode,
    toggleCollapsed,
    sessions,
    activeSessionId,
    selectSession,
    messages,
    pending,
    error,
    lastResponse,
    send,
    clearChat,
    newSession,
    clearIncidentContext,
    resetMemory,
    contextAlert,
    incidentSessionId,
    registerSession,
    lastQuestion,
  } = useChatDock();
  const { setSessionId } = useSession();
  const { triageResult } = useDemo();
  const [draft, setDraft] = useState("");
  const [memoryOpen, setMemoryOpen] = useState(true);
  const [activityIndex, setActivityIndex] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Rotate the "what is the agent doing" label and tick the elapsed timer while pending.
  useEffect(() => {
    if (!pending) {
      setActivityIndex(0);
      setElapsedSec(0);
      return;
    }
    const startedAt = Date.now();
    const labelTimer = window.setInterval(() => {
      setActivityIndex((i) => Math.min(i + 1, AGENT_ACTIVITY_LABELS.length - 1));
    }, 1600);
    const clockTimer = window.setInterval(() => {
      setElapsedSec(Math.floor((Date.now() - startedAt) / 1000));
    }, 1000);
    return () => {
      window.clearInterval(labelTimer);
      window.clearInterval(clockTimer);
    };
  }, [pending]);

  useEffect(() => {
    const sid = triageResult?.memory?.session_id || triageResult?.session_id;
    if (!sid) return;
    registerSession(sid, `${triageResult?.piter?.service || "Investigation"} P1`, {
      incident: true,
      activate: !incidentSessionId,
    });
  }, [triageResult, registerSession, incidentSessionId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  if (mode === "collapsed") {
    return (
      <aside className="chat-dock chat-dock-collapsed">
        <button type="button" className="dock-rail-btn" onClick={toggleCollapsed} title="Open Agent Copilot">
          <MessageSquare size={18} />
        </button>
      </aside>
    );
  }

  const submit = () => {
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    void send(text);
  };

  const followups = lastResponse?.recommended_followups || lastResponse?.next_questions || [];
  const lastAnswer = messages.filter((m) => m.role === "assistant").at(-1)?.content;

  const scrollToAnalysis = () => {
    document.getElementById("piter-analysis-panel")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <aside className={`chat-dock${mode === "fullscreen" ? " chat-dock-full" : ""}`}>
      <header className="chat-dock-header">
        <div className="chat-dock-title">
          <Bot size={18} className="chat-dock-title-icon" aria-hidden />
          <div>
            <span className="chat-dock-title-text">Agent Copilot</span>
            <span className="chat-dock-title-sub">PITER Ops incident assistant</span>
          </div>
        </div>
        <div className="chat-dock-tools">
          <button type="button" className="btn btn-sm" onClick={() => void newSession()} title="New session">
            <Plus size={14} /> New Session
          </button>
          <button
            type="button"
            className="btn btn-sm"
            onClick={() => void clearChat()}
            title="Clear active session messages"
          >
            <Trash2 size={14} /> Clear Chat
          </button>
          <button
            type="button"
            className="btn btn-icon"
            onClick={() => setMode(mode === "fullscreen" ? "open" : "fullscreen")}
            title={mode === "fullscreen" ? "Exit full panel" : "Expand full panel"}
          >
            {mode === "fullscreen" ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>
          <button type="button" className="btn btn-icon" onClick={toggleCollapsed} title="Collapse">
            <ChevronRight size={16} />
          </button>
        </div>
      </header>

      {contextAlert ? (
        <div className="chat-context-chip">
          <span className="chat-context-label">
            Current context: {(contextAlert.severity as string) || "P1"} {contextAlert.service} incident
          </span>
          <PriorityBadge priority={(contextAlert.severity as Priority) || "P4"} />
          <span className="mono chat-context-meta">
            {contextAlert.service} · {contextAlert.environment} · {contextAlert.alert_id}
          </span>
          <button
            type="button"
            className="chat-context-clear"
            onClick={clearIncidentContext}
            title="Clear incident context"
            aria-label="Clear incident context"
          >
            <X size={14} />
          </button>
        </div>
      ) : null}

      {mode === "fullscreen" || contextAlert ? (
        <details className="chat-memory-panel" open={memoryOpen} onToggle={(e) => setMemoryOpen(e.currentTarget.open)}>
          <summary>
            Memory Active
            <span className="chat-memory-on" aria-label="memory on">
              ● ON
            </span>
          </summary>
          <dl className="chat-memory-dl">
            <div>
              <dt>Current incident</dt>
              <dd>
                {contextAlert
                  ? `${contextAlert.title || contextAlert.service} · ${contextAlert.service}`
                  : "None selected"}
              </dd>
            </div>
            <div>
              <dt>Last question</dt>
              <dd>{lastQuestion || "—"}</dd>
            </div>
            <div>
              <dt>Last assistant answer</dt>
              <dd className="chat-memory-answer">{lastAnswer ? `${lastAnswer.slice(0, 160)}…` : "—"}</dd>
            </div>
          </dl>
          <p className="chat-memory-rule">
            <strong>Memory rule:</strong> Use previous question only for follow-up questions in the active
            incident.
          </p>
          <button type="button" className="btn btn-sm" onClick={() => void resetMemory()}>
            <RotateCcw size={14} /> Reset Memory
          </button>
        </details>
      ) : null}

      <div className="chat-common-questions">
        {COPILOT_COMMON_QUESTIONS.map((q) => (
          <button key={q} type="button" className="follow-up-chip" onClick={() => void send(q)} disabled={pending}>
            {q}
          </button>
        ))}
      </div>

      <div className="chat-sessions">
        <label className="label" htmlFor="chat-session-select">
          Session
        </label>
        <select
          id="chat-session-select"
          className="select"
          value={activeSessionId || ""}
          onChange={(e) => {
            const id = e.target.value || null;
            selectSession(id);
            setSessionId(id);
          }}
        >
          <option value="">New / unsaved session</option>
          {sessions.map((s) => (
            <option key={s.id} value={s.id}>
              {s.label}
              {s.count > 0 ? ` (${s.count} msgs)` : ""}
            </option>
          ))}
        </select>
        {contextAlert ? (
          <button type="button" className="btn btn-sm chat-clear-context-btn" onClick={clearIncidentContext}>
            Clear Incident Context
          </button>
        ) : null}
      </div>

      <div className="chat-messages">
        {messages.length === 0 && !pending ? (
          <p className="chat-empty">
            Ask about the selected incident, prior alerts, runbooks, or escalation paths. Follow-ups use session memory
            when an incident session is active.
          </p>
        ) : null}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`chat-bubble chat-${m.role}${m.guardrail_blocked ? " chat-guardrail" : ""}`}
          >
            <div className="chat-role">{m.role === "user" ? "You" : "PITER Agent"}</div>
            {m.guardrail_blocked ? (
              <div className="chat-guardrail-wrap">
                <SafetyGuardrail previewOnly />
              </div>
            ) : null}
            <div className="chat-text">
              {m.role === "assistant" ? <ChatMarkdown text={m.content} /> : m.content}
            </div>
          </div>
        ))}
        {pending ? (
          <div className="chat-bubble chat-assistant chat-thinking chat-thinking-live" role="status" aria-live="polite">
            <div className="chat-thinking-head">
              <span className="chat-thinking-icon" aria-hidden>
                {activityIndex % 4 === 0 ? (
                  <Search size={14} />
                ) : activityIndex % 4 === 1 ? (
                  <Database size={14} />
                ) : activityIndex % 4 === 2 ? (
                  <Wrench size={14} />
                ) : (
                  <Loader2 size={14} className="chat-thinking-spinner" />
                )}
              </span>
              <span className="chat-thinking-label">{AGENT_ACTIVITY_LABELS[activityIndex]}</span>
              <span className="chat-thinking-clock mono">{elapsedSec}s</span>
            </div>
            <div className="chat-thinking-steps" aria-hidden>
              {AGENT_ACTIVITY_LABELS.map((label, i) => (
                <span
                  key={label}
                  className={`chat-thinking-dot${
                    i < activityIndex ? " done" : i === activityIndex ? " active" : ""
                  }`}
                  title={label}
                />
              ))}
            </div>
            <div className="chat-thinking-bar" aria-hidden>
              <span
                className="chat-thinking-bar-fill"
                style={{ width: `${Math.min(100, ((activityIndex + 1) / AGENT_ACTIVITY_LABELS.length) * 100)}%` }}
              />
            </div>
          </div>
        ) : null}
        {error ? <div className="chat-error">{error}</div> : null}
        <div ref={bottomRef} />
      </div>

      {lastResponse?.piter && messages.length > 0 ? (
        <div className="chat-summary-card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong>Analysis summary</strong>
          </div>
          {lastResponse.piter.priority ? (
            <div style={{ marginTop: 6 }}>
              <PriorityBadge priority={lastResponse.piter.priority as Priority} />
            </div>
          ) : null}
          <p className="chat-summary-snippet">{investigationSnippet(lastResponse)}</p>
          <Button variant="secondary" size="sm" onClick={scrollToAnalysis}>
            View full analysis
          </Button>
          {followups.length > 0 ? (
            <div className="follow-up-chips">
              {followups.slice(0, 4).map((q) => (
                <button key={q} type="button" className="follow-up-chip" onClick={() => void send(q)}>
                  {q}
                </button>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      <DocumentUploadPanel compact />

      <footer className="chat-compose">
        <textarea
          className="textarea chat-input"
          rows={2}
          value={draft}
          placeholder="Ask the copilot about this incident…"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              submit();
            }
          }}
        />
        <Button variant="primary" onClick={submit} disabled={pending} loading={pending}>
          Send
        </Button>
      </footer>
    </aside>
  );
}
