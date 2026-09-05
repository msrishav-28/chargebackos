import { Link, useNavigate, useRouterState } from "@tanstack/react-router";
import { useState } from "react";
import { Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import { logoutRequest, setToken } from "@/lib/ops-api";
import { useOverviewQuery } from "@/lib/ops-query";
import { useStaff } from "@/lib/ops-context";
import { Button } from "@/components/ui/button";
import { OpsBanner } from "@/components/ops-state";

const NAV = [
  { to: "/", label: "Overview" },
  { to: "/disputes", label: "Disputes" },
  { to: "/evaluation", label: "Evaluation" },
  { to: "/policies", label: "Policies" },
  { to: "/about", label: "About" },
] as const;

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const navigate = useNavigate();
  const overview = useOverviewQuery();
  const staff = useStaff();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const signOut = async () => {
    setBusy(true);
    setError(null);
    try {
      await logoutRequest();
      setToken(null);
      await navigate({ to: "/login", replace: true });
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="min-h-dvh bg-bg font-sans text-fg">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:z-50 focus:bg-surface focus:p-4">Skip to content</a>
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-[1200px] flex-wrap items-center justify-between gap-4 px-4 py-4 md:px-6">
          <Link to="/" className="flex items-center gap-3 font-semibold text-accent">
            <span className="grid size-9 place-items-center rounded-md bg-accent text-white"><Shield aria-hidden className="size-5" /></span>
            ChargebackOS
          </Link>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-muted">{staff.displayName} · {staff.role}</span>
            <Button variant="outline" disabled={busy} onClick={() => void signOut()}>{busy ? "Signing out…" : "Sign out"}</Button>
          </div>
        </div>
        <nav aria-label="Main navigation" className="mx-auto flex max-w-[1200px] gap-2 overflow-x-auto px-4 pb-3 md:px-6">
          {NAV.map(({ to, label }) => {
            const active = to === "/" ? pathname === "/" : pathname === to || pathname.startsWith(`${to}/`);
            return <Link key={to} to={to} aria-current={active ? "page" : undefined} className={cn("shrink-0 rounded-md px-4 py-2 text-sm font-medium transition-colors", active ? "bg-accent text-white" : "text-muted hover:bg-surface-2 hover:text-fg")}>{label}</Link>;
          })}
        </nav>
      </header>
      <main id="main-content" className="mx-auto min-h-[70vh] w-full max-w-[1200px] px-4 py-6 md:px-6 md:py-8">
        {error ? <div className="mb-6"><OpsBanner error={error} onRetry={() => void signOut()} /></div> : null}
        {children}
      </main>
      <footer className="mx-auto flex max-w-[1200px] flex-wrap justify-between gap-3 border-t border-border px-6 py-5 text-xs text-muted">
        <span>Synthetic data only · No live filing or money movement</span>
        <span className="font-mono">{overview.data?.modelVersion ?? "Model unavailable"} · {overview.data?.policyVersion ?? "Policy unavailable"} · Seed {overview.data?.seed ?? "—"}</span>
      </footer>
    </div>
  );
}
