import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type { AlertRow, ChatDockPrefill, ChatResponse, HistoryMessage } from "@/types/api";
import {
  ApiError,
  clearHistory,
  fetchHistory,
  fetchIncidentsHistory,
  postChat,
  postFollowUp,
} from "@/lib/api-contract";
import { useSession } from "@/context/session";

export type DockMode = "collapsed" | "open" | "fullscreen";

type SessionEntry = { id: string; label: string; count: number; incident?: boolean };

type RegisterOptions = { label?: string; activate?: boolean; incident?: boolean };

type ChatDockContextValue = {
  mode: DockMode;
  setMode: (mode: DockMode) => void;
  toggleCollapsed: () => void;
  sessions: SessionEntry[];
  activeSessionId: string | null;
  incidentSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;
  selectSession: (id: string | null) => void;
  registerSession: (id: string, label?: string, options?: RegisterOptions) => void;
  messages: HistoryMessage[];
  pending: boolean;
  error: string | null;
  lastResponse: ChatResponse | null;
  send: (text: string) => Promise<void>;
  openWith: (prefill: ChatDockPrefill) => void;
  loadSession: (sessionId: string) => Promise<void>;
  clearChat: () => Promise<void>;
  newSession: () => Promise<void>;
  hydrateSessions: () => Promise<void>;
  clearIncidentContext: () => void;
  resetMemory: () => Promise<void>;
  contextAlert: Partial<AlertRow> | null;
  lastQuestion: string | null;
};

const ChatDockContext = createContext<ChatDockContextValue | null>(null);

const CHAT_DEFAULT_ID = "demo-default";

function assistantBubbleText(data: ChatResponse): string {
  if (data.answer?.trim()) return data.answer.trim();
  const inv = data.piter?.investigation?.trim();
  if (inv) return inv;
  return "Analysis ready — see the workspace panel for full PITER output.";
}

function resolveOutboundSessionId(
  incidentSid: string | null,
  activeSessionId: string | null,
  globalSessionId: string | null,
): string {
  return incidentSid || activeSessionId || globalSessionId || CHAT_DEFAULT_ID;
}

export function ChatDockProvider({ children }: { children: ReactNode }) {
  const { sessionId: globalSessionId, setSessionId: setGlobalSessionId } = useSession();
  const incidentIdsRef = useRef(new Set<string>());
  const [mode, setMode] = useState<DockMode>("open");
  const [sessions, setSessions] = useState<SessionEntry[]>([
    { id: CHAT_DEFAULT_ID, label: "General chat", count: 0, incident: false },
  ]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(CHAT_DEFAULT_ID);
  const [incidentSessionId, setIncidentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<HistoryMessage[]>([]);
  const [pending, setPending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<ChatResponse | null>(null);
  const [contextAlert, setContextAlert] = useState<Partial<AlertRow> | null>(null);
  const [lastQuestion, setLastQuestion] = useState<string | null>(null);

  const isIncidentSession = useCallback((id: string | null | undefined) => {
    return Boolean(id && incidentIdsRef.current.has(id));
  }, []);

  const registerSession = useCallback(
    (id: string, label?: string, options?: RegisterOptions) => {
      const incident = options?.incident !== false;
      if (incident) incidentIdsRef.current.add(id);
      setSessions((prev) => {
        const next = prev.some((s) => s.id === id)
          ? prev.map((s) =>
              s.id === id ? { ...s, label: label || s.label, incident: incident || s.incident } : s,
            )
          : [{ id, label: label || id.slice(0, 12), count: 0, incident }, ...prev];
        return next;
      });
      if (options?.activate) {
        setActiveSessionId(id);
        setIncidentSessionId(incident ? id : null);
        setGlobalSessionId(id);
      }
    },
    [setGlobalSessionId],
  );

  const routingSessionId = useCallback(() => {
    if (incidentSessionId && isIncidentSession(incidentSessionId)) return incidentSessionId;
    const sid = activeSessionId || globalSessionId;
    if (sid && isIncidentSession(sid)) return sid;
    return null;
  }, [activeSessionId, globalSessionId, incidentSessionId, isIncidentSession]);

  const loadSession = useCallback(
    async (sessionId: string) => {
      setError(null);
      try {
        const data = await fetchHistory(sessionId);
        setActiveSessionId(data.session_id);
        setMessages(data.messages);
        const incident = isIncidentSession(data.session_id);
        if (incident) {
          setIncidentSessionId(data.session_id);
          setGlobalSessionId(data.session_id);
        } else if (data.session_id === CHAT_DEFAULT_ID) {
          setIncidentSessionId(null);
        }
        registerSession(data.session_id, data.session_id.slice(0, 12), {
          incident,
          activate: false,
        });
        setSessions((prev) =>
          prev.map((s) => (s.id === data.session_id ? { ...s, count: data.count } : s)),
        );
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Failed to load session");
      }
    },
    [isIncidentSession, registerSession, setGlobalSessionId],
  );

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || pending) return;
      setPending(true);
      setError(null);
      setLastQuestion(trimmed);
      setMessages((m) => [...m, { role: "user", content: trimmed, ts: Date.now() / 1000 }]);
      try {
        const incidentSid = routingSessionId();
        const outboundSid = resolveOutboundSessionId(incidentSid, activeSessionId, globalSessionId);
        const data =
          incidentSid && isIncidentSession(incidentSid)
            ? await postFollowUp(incidentSid, trimmed)
            : await postChat(trimmed, outboundSid);
        setLastResponse(data);
        const nextSid = data.memory?.session_id || data.session_id || outboundSid;
        if (nextSid && isIncidentSession(nextSid)) {
          setIncidentSessionId(nextSid);
          setActiveSessionId(nextSid);
          registerSession(nextSid, undefined, { incident: true, activate: false });
        } else if (nextSid) {
          setActiveSessionId(nextSid);
          registerSession(nextSid, "General chat", { incident: false, activate: false });
        }
        const answer = assistantBubbleText(data);
        setMessages((m) => [
          ...m,
          {
            role: "assistant",
            content: answer,
            ts: Date.now() / 1000,
            mode: data.guardrail_blocked ? "guardrail" : data.fallback_used ? "local_fallback" : data.mode,
            guardrail_blocked: data.guardrail_blocked,
          },
        ]);
        setSessions((prev) =>
          prev.map((s) =>
            s.id === (nextSid || outboundSid) ? { ...s, count: s.count + 2 } : s,
          ),
        );
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Chat failed");
      } finally {
        setPending(false);
      }
    },
    [
      pending,
      registerSession,
      routingSessionId,
      isIncidentSession,
      activeSessionId,
      globalSessionId,
    ],
  );

  const clearChat = useCallback(async () => {
    const sid = activeSessionId || globalSessionId || CHAT_DEFAULT_ID;
    setError(null);
    try {
      await clearHistory(sid);
      setMessages([]);
      setLastResponse(null);
      setLastQuestion(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to clear chat");
    }
  }, [activeSessionId, globalSessionId]);

  const resetMemory = useCallback(async () => {
    await clearChat();
    setContextAlert(null);
    setIncidentSessionId(null);
  }, [clearChat]);

  const hydrateSessions = useCallback(async () => {
    try {
      const hist = await fetchIncidentsHistory(50);
      const entries: SessionEntry[] = (hist.investigations || []).map((p) => {
        incidentIdsRef.current.add(p.session_id);
        return {
          id: p.session_id,
          label: `${p.service || "Investigation"} · ${p.severity || "—"}`,
          count: 0,
          incident: true,
        };
      });
      setSessions((prev) => {
        const seen = new Set(prev.map((s) => s.id));
        const merged = [...prev];
        for (const e of entries) {
          if (!seen.has(e.id)) merged.push(e);
        }
        return merged;
      });
    } catch {
      /* history optional for demo */
    }
  }, []);

  const newSession = useCallback(async () => {
    setError(null);
    setActiveSessionId(CHAT_DEFAULT_ID);
    setIncidentSessionId(null);
    setGlobalSessionId(CHAT_DEFAULT_ID);
    setMessages([]);
    setLastResponse(null);
    setLastQuestion(null);
    setContextAlert(null);
    try {
      await clearHistory(CHAT_DEFAULT_ID);
    } catch {
      /* fresh session */
    }
  }, [setGlobalSessionId]);

  const openWith = useCallback(
    (prefill: ChatDockPrefill) => {
      setMode("open");
      if (prefill.alert) setContextAlert(prefill.alert);
      if (prefill.triageResponse) setLastResponse(prefill.triageResponse);
      if (prefill.sessionId) {
        registerSession(prefill.sessionId, undefined, { incident: true, activate: true });
        void loadSession(prefill.sessionId);
      }
      if (prefill.message) {
        void send(prefill.message);
      }
    },
    [loadSession, registerSession, send],
  );

  const toggleCollapsed = useCallback(() => {
    setMode((m) => (m === "collapsed" ? "open" : "collapsed"));
  }, []);

  const clearIncidentContext = useCallback(() => {
    setContextAlert(null);
    setIncidentSessionId(null);
  }, []);

  const selectSession = useCallback(
    (id: string | null) => {
      setActiveSessionId(id);
      setGlobalSessionId(id);
      if (!id) {
        setIncidentSessionId(null);
        setMessages([]);
        setLastResponse(null);
        setLastQuestion(null);
        return;
      }
      void loadSession(id);
    },
    [loadSession, setGlobalSessionId],
  );

  useEffect(() => {
    void hydrateSessions();
    void fetchHistory(CHAT_DEFAULT_ID).then((h) => {
      if (h.messages?.length) {
        setMessages(h.messages);
        setActiveSessionId(h.session_id);
      }
    });
  }, [hydrateSessions]);

  const value = useMemo(
    () => ({
      mode,
      setMode,
      toggleCollapsed,
      sessions,
      activeSessionId,
      incidentSessionId,
      setActiveSessionId,
      selectSession,
      registerSession,
      messages,
      pending,
      error,
      lastResponse,
      send,
      openWith,
      loadSession,
      clearChat,
      newSession,
      hydrateSessions,
      clearIncidentContext,
      resetMemory,
      contextAlert,
      lastQuestion,
    }),
    [
      mode,
      sessions,
      activeSessionId,
      incidentSessionId,
      messages,
      pending,
      error,
      lastResponse,
      send,
      openWith,
      loadSession,
      selectSession,
      registerSession,
      toggleCollapsed,
      clearChat,
      newSession,
      hydrateSessions,
      clearIncidentContext,
      resetMemory,
      contextAlert,
      lastQuestion,
    ],
  );

  return <ChatDockContext.Provider value={value}>{children}</ChatDockContext.Provider>;
}

export function useChatDock() {
  const ctx = useContext(ChatDockContext);
  if (!ctx) throw new Error("useChatDock must be used within ChatDockProvider");
  return ctx;
}
