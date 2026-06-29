import { useCallback, useEffect, useState } from "react";
import { ApiError, fetchHistory } from "@/lib/api-contract";
import { useSession } from "@/context/session";
import { useNavigate } from "@/context/navigation";
import type { HistoryResponse } from "@/types/api";
import { ErrorState } from "@/components/noc/ErrorState";
import { EmptyState } from "@/components/noc/EmptyState";
import { LoadingSkeleton } from "@/components/noc/LoadingSkeleton";

export function HistoryPage() {
  const { sessionId, setSessionId } = useSession();
  const navigate = useNavigate();
  const [data, setData] = useState<HistoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<number | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const result = await fetchHistory(sessionId);
      setData(result);
      if (result.session_id) setSessionId(result.session_id);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load history");
    } finally {
      setLoading(false);
    }
  }, [sessionId, setSessionId]);

  useEffect(() => {
    void load();
  }, [load]);

  const continueInChat = () => {
    if (data?.session_id) setSessionId(data.session_id);
    navigate("chat");
  };

  if (loading) {
    return (
      <div className="grid-stack">
        <h1 style={{ margin: 0, fontSize: "1.25rem" }}>Chat History</h1>
        <LoadingSkeleton lines={5} />
      </div>
    );
  }

  if (error) return <ErrorState message={error} onRetry={load} />;

  const messages = data?.messages ?? [];

  return (
    <div className="grid-stack">
      <h1 style={{ margin: 0, fontSize: "1.25rem" }}>Chat History</h1>
      <p style={{ margin: 0, fontSize: "0.8125rem", color: "var(--text-muted)" }}>
        API returns one session per request. Default demo session shown below.
      </p>
      {data?.session_id ? (
        <p className="mono" style={{ margin: 0, fontSize: "0.75rem", color: "var(--text-secondary)" }}>
          session_id: {data.session_id} · {data.count} messages
        </p>
      ) : null}

      {messages.length ? (
        <div className="grid-stack">
          {messages.map((msg, i) => (
            <article key={i} className="panel">
              <button
                type="button"
                className="btn"
                style={{ width: "100%", justifyContent: "space-between", marginBottom: expanded === i ? "12px" : 0 }}
                onClick={() => setExpanded(expanded === i ? null : i)}
              >
                <span>
                  {msg.role === "user" ? "Q" : "A"} · {msg.content.slice(0, 60)}
                  {msg.content.length > 60 ? "…" : ""}
                </span>
                {msg.ts ? (
                  <span className="mono" style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    {new Date(msg.ts * 1000).toISOString()}
                  </span>
                ) : null}
              </button>
              {expanded === i ? (
                <p style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.6, fontSize: "0.875rem" }}>
                  {msg.content}
                </p>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <EmptyState title="No messages" detail="Start a conversation in AI Chat." />
      )}

      <button type="button" className="btn btn-primary" onClick={continueInChat}>
        Continue in Chat
      </button>
    </div>
  );
}
