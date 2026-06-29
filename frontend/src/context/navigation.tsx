import { createContext, useContext, type ReactNode } from "react";
import type { PageKey } from "@/types/api";

type NavContextValue = {
  navigate: (page: PageKey) => void;
};

const NavContext = createContext<NavContextValue | null>(null);

export function NavigationProvider({
  navigate,
  children,
}: {
  navigate: (page: PageKey) => void;
  children: ReactNode;
}) {
  return <NavContext.Provider value={{ navigate }}>{children}</NavContext.Provider>;
}

export function useNavigate() {
  const ctx = useContext(NavContext);
  if (!ctx) throw new Error("useNavigate must be used within NavigationProvider");
  return ctx.navigate;
}
