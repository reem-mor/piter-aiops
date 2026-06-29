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
import type {
  AgentDecision,
  AlertRow,
  BootstrapResponse,
  MetricsResult,
  TriageResponse,
} from "@/types/api";
import {
  deriveDecisions,
  shouldShowP1Popup,
  STORM_WALL_SECONDS,
  visibleRowsAt,
} from "@/lib/storm-engine";
import { fetchAlertStream, fetchBootstrap, fetchBusinessImpact } from "@/lib/api-contract";

type DemoContextValue = {
  demoMode: boolean;
  paused: boolean;
  wallSec: number;
  rows: AlertRow[];
  visible: AlertRow[];
  decisions: AgentDecision[];
  p1Row: AlertRow | null;
  showP1Modal: boolean;
  p1Shown: boolean;
  criticalMode: boolean;
  stormComplete: boolean;
  escalatedIds: Set<string>;
  triageResult: TriageResponse | null;
  triageAnalyzing: boolean;
  demoImpact: MetricsResult | null;
  bootstrap: BootstrapResponse | null;
  startStorm: () => void;
  resetDemo: () => void;
  pauseStorm: () => void;
  resumeStorm: () => void;
  dismissP1: () => void;
  setTriageResult: (r: TriageResponse | null) => void;
  setTriageAnalyzing: (v: boolean) => void;
  markEscalated: (incidentId: string) => void;
};

const DemoContext = createContext<DemoContextValue | null>(null);

export function DemoProvider({ children }: { children: ReactNode }) {
  const [demoMode, setDemoMode] = useState(false);
  const [paused, setPaused] = useState(false);
  const [wallSec, setWallSec] = useState(0);
  const [rows, setRows] = useState<AlertRow[]>([]);
  const [visible, setVisible] = useState<AlertRow[]>([]);
  const [decisions, setDecisions] = useState<AgentDecision[]>([]);
  const [showP1Modal, setShowP1Modal] = useState(false);
  const [p1Shown, setP1Shown] = useState(false);
  const [stormComplete, setStormComplete] = useState(false);
  const [escalatedIds, setEscalatedIds] = useState<Set<string>>(new Set());
  const [triageResult, setTriageResult] = useState<TriageResponse | null>(null);
  const [triageAnalyzing, setTriageAnalyzing] = useState(false);
  const [demoImpact, setDemoImpact] = useState<MetricsResult | null>(null);
  const [bootstrap, setBootstrap] = useState<BootstrapResponse | null>(null);
  const prevVisibleRef = useRef<AlertRow[]>([]);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    void fetchBootstrap().then(setBootstrap);
    void fetchAlertStream(true).then((s) => setRows(s.rows || []));
  }, []);

  const p1Row = useMemo(
    () => rows.find((r) => r.is_trigger === "true") || rows.find((r) => r.severity === "P1") || null,
    [rows],
  );

  const tick = useCallback(() => {
    setWallSec((w) => {
      const next = Math.min(STORM_WALL_SECONDS, w + 0.25);
      const vis = visibleRowsAt(rows, next);
      setVisible(vis);
      const added = vis.filter((r) => !prevVisibleRef.current.some((p) => p.alert_id === r.alert_id));
      if (added.length) {
        setDecisions((d) => deriveDecisions(d, added, next));
      }
      prevVisibleRef.current = vis;
      if (!p1Shown && shouldShowP1Popup(rows, next, p1Shown)) {
        setShowP1Modal(true);
        setPaused(true);
        setP1Shown(true);
      }
      if (next >= STORM_WALL_SECONDS) {
        setStormComplete(true);
        setPaused(true);
        if (p1Row) {
          void fetchBusinessImpact({
            service: p1Row.service,
            environment: p1Row.environment,
            severity: p1Row.severity,
            duration_minutes: "45",
          }).then(setDemoImpact);
        }
      }
      return next;
    });
  }, [p1Row, p1Shown, rows]);

  useEffect(() => {
    if (!demoMode || paused || stormComplete) return;
    timerRef.current = window.setInterval(tick, 250);
    return () => {
      if (timerRef.current) window.clearInterval(timerRef.current);
    };
  }, [demoMode, paused, stormComplete, tick]);

  const startStorm = useCallback(() => {
    setDemoMode(true);
    setPaused(false);
    setWallSec(0);
    setVisible([]);
    setDecisions([
      {
        id: "storm-start",
        at: 0,
        kind: "group",
        text: "Alert storm started. Streaming alerts into the agent.",
      },
    ]);
    setShowP1Modal(false);
    setP1Shown(false);
    setStormComplete(false);
    setEscalatedIds(new Set());
    setTriageResult(null);
    setTriageAnalyzing(false);
    setDemoImpact(null);
    prevVisibleRef.current = [];
  }, []);

  const resetDemo = useCallback(() => {
    if (timerRef.current) window.clearInterval(timerRef.current);
    setDemoMode(false);
    setPaused(false);
    setWallSec(0);
    setVisible([]);
    setDecisions([]);
    setShowP1Modal(false);
    setP1Shown(false);
    setStormComplete(false);
    setEscalatedIds(new Set());
    setTriageResult(null);
    setTriageAnalyzing(false);
    setDemoImpact(null);
    prevVisibleRef.current = [];
  }, []);

  const criticalMode = showP1Modal || p1Shown || Boolean(triageResult) || triageAnalyzing;

  const value = useMemo(
    () => ({
      demoMode,
      paused,
      wallSec,
      rows,
      visible,
      decisions,
      p1Row,
      showP1Modal,
      p1Shown,
      criticalMode,
      stormComplete,
      escalatedIds,
      triageResult,
      triageAnalyzing,
      demoImpact,
      bootstrap,
      startStorm,
      resetDemo,
      pauseStorm: () => setPaused(true),
      resumeStorm: () => setPaused(false),
      dismissP1: () => {
        setShowP1Modal(false);
        setPaused(false);
      },
      setTriageResult,
      setTriageAnalyzing,
      markEscalated: (id: string) => setEscalatedIds((s) => new Set(s).add(id)),
    }),
    [
      demoMode,
      paused,
      wallSec,
      rows,
      visible,
      decisions,
      p1Row,
      showP1Modal,
      p1Shown,
      criticalMode,
      stormComplete,
      escalatedIds,
      triageResult,
      triageAnalyzing,
      demoImpact,
      bootstrap,
      startStorm,
      resetDemo,
    ],
  );

  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>;
}

export function useDemo() {
  const ctx = useContext(DemoContext);
  if (!ctx) throw new Error("useDemo must be used within DemoProvider");
  return ctx;
}
