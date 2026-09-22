import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Activity,
  Bell,
  BookOpen,
  ChevronLeft,
  ClipboardList,
  FileCode2,
  FlaskConical,
  GitBranch,
  LayoutDashboard,
  PlayCircle,
  PlusCircle,
  Settings,
  Shield,
} from "lucide-react";
import { api } from "../api/client";

const nav = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
  { to: "/runs/new", label: "New Run", icon: PlusCircle, end: true },
  { to: "/runs", label: "Runs", icon: PlayCircle, end: true },
  { to: "/reviews", label: "Reviews", icon: ClipboardList, badgeKey: "reviews" as const },
  { to: "/test-cases", label: "Test Cases", icon: FlaskConical },
  { to: "/scripts", label: "Scripts", icon: FileCode2 },
  { to: "/executions", label: "Executions", icon: Activity },
  { to: "/reports", label: "Reports", icon: BookOpen },
  { to: "/knowledge", label: "Knowledge Base", icon: BookOpen },
  { to: "/skills", label: "Skills", icon: FileCode2 },
  { to: "/cicd", label: "CI/CD", icon: GitBranch },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function AppShell() {
  const location = useLocation();
  const [pendingReviews, setPendingReviews] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const s = await api.getDashboardSummary();
        if (!cancelled) setPendingReviews(s.pending_reviews ?? 0);
      } catch {
        /* badge is best-effort */
      }
    };
    void load();
    const id = window.setInterval(load, 30_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  return (
    <div className="flex min-h-full bg-canvas">
      <aside className="flex w-60 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-white">
        <div className="border-b border-sidebar-border px-4 py-5">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary text-sm font-bold">
              QZ
            </div>
            <div>
              <p className="text-base font-semibold tracking-tight">QAZen</p>
              <p className="text-[11px] text-sidebar-muted">AI for Better Quality</p>
            </div>
          </div>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 py-3">
          {nav.map((item) => {
            const Icon = item.icon;
            const badge = item.badgeKey === "reviews" && pendingReviews > 0 ? pendingReviews : null;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 rounded-md px-2.5 py-2 text-sm transition ${
                    isActive
                      ? "bg-sidebar-active text-white"
                      : "text-slate-300 hover:bg-sidebar-hover hover:text-white"
                  }`
                }
              >
                <Icon className="h-4 w-4 shrink-0 opacity-90" />
                <span className="flex-1">{item.label}</span>
                {badge != null ? (
                  <span className="rounded-full bg-danger px-1.5 py-0.5 text-[10px] font-semibold leading-none text-white">
                    {badge}
                  </span>
                ) : null}
              </NavLink>
            );
          })}
        </nav>

        <div className="flex items-center justify-between border-t border-sidebar-border px-4 py-3 text-xs text-sidebar-muted">
          <span>v1.0.0</span>
          <ChevronLeft className="h-4 w-4 opacity-60" aria-hidden />
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-end gap-3 border-b border-border bg-surface px-5">
          <label className="flex items-center gap-2 rounded-md border border-border bg-canvas px-2.5 py-1.5 text-sm text-ink">
            <Shield className="h-3.5 w-3.5 text-muted" />
            <select className="bg-transparent text-sm outline-none" defaultValue="test" aria-label="Environment">
              <option value="test">Test Environment</option>
              <option value="staging">Staging</option>
              <option value="production">Production</option>
            </select>
          </label>

          <button
            type="button"
            className="relative rounded-md border border-border p-2 text-muted hover:bg-canvas hover:text-ink"
            aria-label="Notifications"
          >
            <Bell className="h-4 w-4" />
            {pendingReviews > 0 ? (
              <span className="absolute -right-1 -top-1 rounded-full bg-danger px-1 text-[10px] font-semibold text-white">
                {pendingReviews}
              </span>
            ) : null}
          </button>

          <div className="flex items-center gap-2 pl-1">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-xs font-semibold text-white">
              KB
            </div>
            <span className="text-sm font-medium text-ink">Konda Babu</span>
          </div>
        </header>

        <main className="flex-1 overflow-auto p-6">
          <div className="page-enter" key={location.pathname}>
            <Outlet />
          </div>
        </main>

        <footer className="flex items-center justify-between border-t border-border bg-surface px-5 py-2 text-xs text-muted">
          <span>QAZen | AI enabled QA automation framework</span>
          <span>Future Ready, Together.</span>
        </footer>
      </div>
    </div>
  );
}
