import {
  Activity,
  BookOpen,
  Bot,
  ClipboardList,
  Cloud,
  FileText,
  HelpCircle,
  LayoutDashboard,
  LineChart,
  Server,
  Shield,
} from "lucide-react";
import type { PageKey } from "@/types/api";
import { SidebarMetrics } from "./SidebarMetrics";

type NavItem = { key: PageKey | "chat"; label: string; icon: typeof LayoutDashboard };

const OPS: NavItem[] = [
  { key: "home", label: "Live Demo", icon: LayoutDashboard },
  { key: "analyzer", label: "Analyzer", icon: Activity },
  { key: "chat", label: "Agent Chat", icon: Bot },
];

const INTEL: NavItem[] = [
  { key: "history", label: "Incident History", icon: ClipboardList },
  { key: "postmortems", label: "Post-Mortems", icon: FileText },
  { key: "analytics", label: "Agent Analytics", icon: LineChart },
];

const PLATFORM: NavItem[] = [
  { key: "knowledge", label: "Knowledge Base", icon: BookOpen },
  { key: "bedrock", label: "AWS / Bedrock", icon: Cloud },
  { key: "system", label: "System", icon: Server },
  { key: "guide", label: "Demo Guide", icon: HelpCircle },
];

function NavButton({
  item,
  active,
  onNavigate,
}: {
  item: NavItem;
  active: boolean;
  onNavigate: (key: PageKey | "chat") => void;
}) {
  const Icon = item.icon;
  return (
    <button
      type="button"
      className={`nav-item${active ? " active" : ""}`}
      onClick={() => onNavigate(item.key)}
      aria-current={active ? "page" : undefined}
    >
      <Icon className="nav-item-icon" aria-hidden />
      <span>{item.label}</span>
    </button>
  );
}

export function Sidebar({
  page,
  onNavigate,
  onHome,
  onOpenChat,
}: {
  page: PageKey;
  onNavigate: (key: PageKey) => void;
  onHome: () => void;
  onOpenChat: () => void;
}) {
  const handleNav = (key: PageKey | "chat") => {
    if (key === "chat") {
      onOpenChat();
      return;
    }
    onNavigate(key);
  };

  return (
    <aside className="app-sidebar">
      <button type="button" className="nav-brand nav-brand-btn" onClick={onHome}>
        <Shield className="nav-item-icon nav-brand-icon" aria-hidden />
        <span className="nav-brand-stack">
          <span className="nav-brand-text">PITER Ops</span>
          <span className="nav-brand-tagline">Priority · Investigation · Triage · Escalation · Resolution</span>
        </span>
      </button>

      <SidebarMetrics />

      <nav className="sidebar-nav">
        <div className="nav-section-label">Operations</div>
        {OPS.map((item) => (
          <NavButton
            key={item.key}
            item={item}
            active={item.key !== "chat" && page === item.key}
            onNavigate={handleNav}
          />
        ))}
        <div className="nav-section-label">Intelligence</div>
        {INTEL.map((item) => (
          <NavButton key={item.key} item={item} active={page === item.key} onNavigate={handleNav} />
        ))}
        <div className="nav-section-label">Platform</div>
        {PLATFORM.map((item) => (
          <NavButton key={item.key} item={item} active={page === item.key} onNavigate={handleNav} />
        ))}
      </nav>

      <footer className="sidebar-footer mono">PITER Ops · Demo Build</footer>
    </aside>
  );
}
