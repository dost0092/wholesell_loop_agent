import { NavLink, Outlet } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  Database,
  ShieldCheck,
  Settings,
  Moon,
  Sun,
  Menu,
  X,
  Command,
} from "lucide-react";
import { useState } from "react";
import { useTheme } from "@/context/ThemeContext";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/leads", label: "Leads", icon: Users },
  { to: "/sources", label: "Sources", icon: Database },
  { to: "/approval", label: "Approval", icon: ShieldCheck },
  { to: "/settings", label: "Settings", icon: Settings },
];

interface AppLayoutProps {
  onOpenCommand: () => void;
}

export function AppLayout({ onOpenCommand }: AppLayoutProps) {
  const { resolved, toggle } = useTheme();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen">
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] transition-transform lg:static lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full",
        )}
        aria-label="Main navigation"
      >
        <div className="flex h-16 items-center gap-2 border-b border-[hsl(var(--border))] px-6">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-600 text-sm font-bold text-white">
            LG
          </div>
          <div>
            <p className="text-sm font-semibold">LeadGen</p>
            <p className="text-xs text-[hsl(var(--muted))]">TX / FL</p>
          </div>
          <button
            type="button"
            className="ml-auto lg:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="Close menu"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="flex-1 space-y-1 p-4">
          {nav.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              onClick={() => setMobileOpen(false)}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand-600/10 text-brand-700 dark:text-brand-300"
                    : "text-[hsl(var(--muted))] hover:bg-[hsl(var(--surface-muted))] hover:text-[hsl(var(--foreground))]",
                )
              }
            >
              <Icon className="h-4 w-4" aria-hidden />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-[hsl(var(--border))] p-4">
          <button
            type="button"
            onClick={onOpenCommand}
            className="flex w-full items-center gap-2 rounded-xl border border-[hsl(var(--border))] px-3 py-2 text-xs text-[hsl(var(--muted))] hover:bg-[hsl(var(--surface-muted))]"
          >
            <Command className="h-3.5 w-3.5" />
            <span>Command palette</span>
            <kbd className="ml-auto rounded bg-[hsl(var(--surface-muted))] px-1.5 py-0.5 font-mono text-[10px]">
              ⌘K
            </kbd>
          </button>
        </div>
      </aside>

      {mobileOpen && (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setMobileOpen(false)}
          aria-label="Close overlay"
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex h-16 items-center gap-4 border-b border-[hsl(var(--border))] bg-[hsl(var(--surface))]/80 px-4 backdrop-blur-xl lg:px-8">
          <button
            type="button"
            className="rounded-xl p-2 hover:bg-[hsl(var(--surface-muted))] lg:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Open menu"
          >
            <Menu className="h-5 w-5" />
          </button>
          <div className="flex-1" />
          <button
            type="button"
            onClick={toggle}
            className="rounded-xl p-2.5 hover:bg-[hsl(var(--surface-muted))]"
            aria-label={resolved === "dark" ? "Switch to light mode" : "Switch to dark mode"}
          >
            {resolved === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
          </button>
        </header>

        <main className="flex-1 p-4 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
