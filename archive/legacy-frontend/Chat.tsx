import { useState, type KeyboardEvent } from "react";
import { ApiError, postChat } from "@/lib/api-contract";
import { useSession } from "@/context/session";
import type { ChatResponse } from "@/types/api";
import { PiterResponseView } from "@/components/noc/PiterResponseView";
import { ErrorState } from "@/components/noc/ErrorState";
import { LoadingSkeleton } from "@/components/noc/LoadingSkeleton";

export function ChatPage() {
  const { sessionId, setSessionId } = useSession();
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState(false);
  const [response, setResponse] = useState<ChatResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const send = async () => {
    const text = message.trim();
    if (!text || pending) return;
    setPending(true);
    setError(null);
    try {
      const data = await postChat(text, sessionId);
      setResponse(data);
      if (data.memory?.session_id) setSessionId(data.memory.session_id);
      setMessage("");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Chat request failed");
    } finally {
      setPending(false);
    }
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void send();
    }
  };

  return (
    <div className="grid-stack">
      <h1 style={{ margin: 0, fontSize: "1.25rem" }}>AI Chat</h1>
      {sessionId ? (
        <p className="mono" style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.75rem" }}>
          Session: {sessionId}
        </p>
      ) : null}

      <div className="panel">
        <label className="label" htmlFor="chat-input">
          Message
        </label>
        <textarea
          id="chat-input"
          className="textarea"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask about an incident, runbook, or escalation path…"
          disabled={pending}
          rows={3}
        />
        <div style={{ marginTop: "12px", display: "flex", gap: "8px" }}>
          <button type="button" className="btn btn-primary" onClick={() => void send()} disabled={pending || !message.trim()}>
            {pending ? "Thinking…" : "Send"}
          </button>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", alignSelf: "center" }}>
            Enter to send · Shift+Enter for newline
          </span>
        </div>
      </div>

      {error ? <ErrorState message={error} onRetry={send} /> : null}
      {pending ? <LoadingSkeleton lines={6} height={18} /> : null}
      {response && !pending ? (
        <>
          {response.answer ? (
            <section className="panel">
              <h2 className="panel-title">Answer</h2>
              <p style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.6 }}>{response.answer}</p>
            </section>
          ) : null}
          <PiterResponseView response={response} />
        </>
      ) : null}
    </div>
  );
}
