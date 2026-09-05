import { OpsApiError } from "@/lib/ops-api";

export function OpsBanner({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const waking = error instanceof OpsApiError && error.waking;
  const text =
    error instanceof OpsApiError
      ? error.message
      : error instanceof Error
        ? error.message
        : "Cannot reach the operations server.";
  return (
    <div
      role="alert"
      className={
        waking
          ? "rounded-xl bg-warn/10 px-4 py-3 text-[13px] font-medium text-warn ring-1 ring-warn/20"
          : "rounded-xl bg-danger/10 px-4 py-3 text-[13px] font-medium text-danger ring-1 ring-danger/20"
      }
    >
      {text}
      <button type="button" onClick={onRetry ?? (() => window.location.reload())} className="ml-3 rounded-md px-3 py-2 font-semibold underline">Retry</button>
    </div>
  );
}

export function OpsLoading({ label = "Loading from the operations server…" }: { label?: string }) {
  return <p role="status" className="text-sm font-medium text-muted">{label}</p>;
}

export function EmptyBook() {
  return (
    <div className="rounded-xl bg-surface px-4 py-6 text-[14px] font-medium text-muted ring-1 ring-border/50">
      The demonstration records have not been prepared yet. Ask the administrator to prepare the synthetic cases, then refresh this page.
    </div>
  );
}
