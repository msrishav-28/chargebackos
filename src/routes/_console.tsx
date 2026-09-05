import { createFileRoute, Outlet, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { getToken, meRequest, OpsApiError, SESSION_EXPIRED_EVENT, type StaffUser } from "@/lib/ops-api";
import { OpsProvider } from "@/components/ops-provider";
import { OpsBanner, OpsLoading } from "@/components/ops-state";

export const Route = createFileRoute("/_console")({
  component: ConsoleLayout,
});

function ConsoleLayout() {
  const navigate = useNavigate();
  const [staff, setStaff] = useState<StaffUser | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const expire = () => {
      setStaff(null);
      void navigate({ to: "/login", replace: true });
    };
    window.addEventListener(SESSION_EXPIRED_EVENT, expire);
    const token = getToken();
    if (!token) {
      expire();
      return () => window.removeEventListener(SESSION_EXPIRED_EVENT, expire);
    }
    meRequest()
      .then((user) => {
        if (!cancelled) setStaff(user);
      })
      .catch((err) => {
        if (cancelled) return;
        if (err instanceof OpsApiError && err.status === 401) {
          expire();
          return;
        }
        setError(err);
      });
    return () => {
      cancelled = true;
      window.removeEventListener(SESSION_EXPIRED_EVENT, expire);
    };
  }, [navigate, attempt]);

  if (!staff) {
    return (
      <div className="grid min-h-dvh place-items-center bg-bg text-sm font-medium text-muted">
        <div className="max-w-lg p-6">{error ? <OpsBanner error={error} onRetry={() => { setError(null); setAttempt((n) => n + 1); }} /> : <OpsLoading label="Checking your staff session…" />}</div>
      </div>
    );
  }

  return (
    <OpsProvider staff={staff}>
      <AppShell>
        <Outlet />
      </AppShell>
    </OpsProvider>
  );
}
