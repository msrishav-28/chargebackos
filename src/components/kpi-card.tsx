import { cn } from "@/lib/utils";

export function KpiCard({
  label,
  value,
  hint,
  tone = "default",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "ok" | "warn" | "danger" | "accent";
}) {
  const valueColor =
    tone === "ok"
      ? "text-ok"
      : tone === "warn"
        ? "text-warn"
        : tone === "danger"
          ? "text-danger"
          : tone === "accent"
            ? "text-accent"
            : "text-fg";
  return (
    <div className="relative overflow-hidden rounded-[24px] bg-surface p-5 shadow-[var(--shadow-subtle)] ring-1 ring-border/50">
      <div className="text-xs font-semibold tracking-wide uppercase text-muted">{label}</div>
      <div className={cn("mt-2 font-mono text-2xl tracking-tighter md:text-3xl font-medium", valueColor)}>
        {value}
      </div>
      {hint ? <div className="mt-1 text-xs text-subtle font-medium">{hint}</div> : null}
    </div>
  );
}
