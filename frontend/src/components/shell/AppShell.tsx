import { Suspense, lazy, useState } from "react";
import type { PageKey } from "@/types/api";
import { SessionProvider } from "@/context/session";
import { NavigationProvider } from "@/context/navigation";
import { DemoProvider, useDemo } from "@/context/demo";
import { ChatDockProvider } from "@/context/chat-dock";
import { ToastProvider } from "@/context/toast";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { ChatDock } from "./ChatDock";
import { AppFooter } from "./AppFooter";
import { P1Modal } from "@/components/demo/P1Modal";
import { HomePage } from "@/pages/Home";
import { useChatDock } from "@/context/chat-dock";

const AnalyticsPage = lazy(() => import("@/pages/Analytics").then((m) => ({ default: m.AnalyticsPage })));
const HistoryInvestigationsPage = lazy(() =>
  import("@/pages/HistoryInvestigations").then((m) => ({ default: m.HistoryInvestigationsPage })),
);
const AnalyzerPage = lazy(() => import("@/pages/Analyzer").then((m) => ({ default: m.AnalyzerPage })));
const SystemPage = lazy(() => import("@/pages/System").then((m) => ({ default: m.SystemPage })));
const DemoGuidePage = lazy(() => import("@/pages/DemoGuide").then((m) => ({ default: m.DemoGuidePage })));
const KnowledgeBasePage = lazy(() =>
  import("@/pages/KnowledgeBasePage").then((m) => ({ default: m.KnowledgeBasePage })),
);
const BedrockStatusPage = lazy(() =>
  import("@/pages/BedrockStatusPage").then((m) => ({ default: m.BedrockStatusPage })),
);
const PostMortemsPage = lazy(() => import("@/pages/PostMortemsPage").then((m) => ({ default: m.PostMortemsPage })));

function PageFallback() {
  return (
    <div className="panel" style={{ padding: "var(--space-5)" }}>
      <p className="mono" style={{ color: "var(--text-muted)", margin: 0 }}>
        Loading…
      </p>
    </div>
  );
}

function PageView({ page }: { page: PageKey }) {
  return (
    <Suspense fallback={<PageFallback />}>
      {page === "home" ? <HomePage /> : null}
      {page === "analytics" ? <AnalyticsPage /> : null}
      {page === "history" ? <HistoryInvestigationsPage /> : null}
      {page === "analyzer" ? <AnalyzerPage /> : null}
      {page === "knowledge" ? <KnowledgeBasePage /> : null}
      {page === "bedrock" ? <BedrockStatusPage /> : null}
      {page === "postmortems" ? <PostMortemsPage /> : null}
      {page === "system" ? <SystemPage /> : null}
      {page === "guide" ? <DemoGuidePage /> : null}
    </Suspense>
  );
}

function ShellLayout() {
  const [page, setPage] = useState<PageKey>("home");
  const { criticalMode } = useDemo();
  const { setMode } = useChatDock();
  const goHome = () => setPage("home");
  const openChat = () => setMode("open");

  return (
    <NavigationProvider navigate={setPage}>
      <div
        className={`app-shell${criticalMode ? " critical-mode" : ""}`}
        data-ui-version="demo-polish-v6"
      >
        <Sidebar page={page} onNavigate={setPage} onHome={goHome} onOpenChat={openChat} />
        <div className="app-body app-body-with-footer">
          <TopBar />
          <div className="app-workspace app-workspace-grow">
            <main className="page-content">
              <PageView page={page} />
            </main>
            <ChatDock />
          </div>
          <AppFooter onNavigate={setPage} />
        </div>
        <P1Modal />
      </div>
    </NavigationProvider>
  );
}

function ShellInner() {
  return (
    <ChatDockProvider>
      <ShellLayout />
    </ChatDockProvider>
  );
}

export function AppShell() {
  return (
    <SessionProvider>
      <ToastProvider>
        <DemoProvider>
          <ShellInner />
        </DemoProvider>
      </ToastProvider>
    </SessionProvider>
  );
}
