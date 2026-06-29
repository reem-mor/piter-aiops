import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

type SessionContextValue = {
  sessionId: string | null;
  setSessionId: (id: string | null) => void;
};

const SessionContext = createContext<SessionContextValue | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [sessionId, setSessionIdState] = useState<string | null>(null);
  const setSessionId = useCallback((id: string | null) => setSessionIdState(id), []);
  const value = useMemo(() => ({ sessionId, setSessionId }), [sessionId, setSessionId]);
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession() {
  const ctx = useContext(SessionContext);
  if (!ctx) throw new Error("useSession must be used within SessionProvider");
  return ctx;
}
