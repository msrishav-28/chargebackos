import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { motion, Variants } from "framer-motion";
import { Search } from "lucide-react";
import { CategoryBadge, FamilyBadge, FightBadge, StateBadge } from "@/components/status";
import { EmptyBook, OpsBanner, OpsLoading } from "@/components/ops-state";
import { Input } from "@/components/ui/input";
import { formatINR, formatPct, formatScore } from "@/lib/chargebackos";
import { useDisputesQuery, useOverviewQuery } from "@/lib/ops-query";
import { Button } from "@/components/ui/button";
import type { DisputesSearch } from "@/lib/queue-search";


export const Route = createFileRoute("/_console/disputes/")({
  component: DisputesPage,
});

const containerVariant: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.02, delayChildren: 0.05 },
  },
};

const itemVariant: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { type: "spring", bounce: 0, duration: 0.4 } },
};


function DisputesPage() {
  const search = Route.useSearch();
  const navigate = useNavigate({ from: "/disputes" });
  const book = useOverviewQuery();
  const [localQ, setLocalQ] = useState(search.q ?? "");

  useEffect(() => setLocalQ(search.q ?? ""), [search.q]);

  const merchant = search.merchant ?? "all";
  const family = search.family ?? "all";
  const category = search.category ?? "all";
  const state = search.state ?? "all";
  const review = Boolean(search.review);
  const high = Boolean(search.high);

  const set = (patch: DisputesSearch) => {
    void navigate({
      search: (prev) => ({ ...prev, page: undefined, ...patch }),
    });
  };

  const list = useDisputesQuery({
    q: search.q,
    merchant_id: merchant !== "all" ? merchant : undefined,
    reason_family: family !== "all" ? family : undefined,
    category: category !== "all" ? category : undefined,
    state: state !== "all" ? state : undefined,
    review,
    high,
    limit: "50",
    page: String(search.page ?? 1),
  });

  const rows = list.data?.items ?? [];
  const merchants = book.data?.merchants ?? [];
  const total = list.data?.total ?? 0;

  if (list.isLoading) return <OpsLoading />;
  if (list.error) return <OpsBanner error={list.error} onRetry={() => void list.refetch()} />;
  if (book.data && book.data.queueCounts.total === 0) return <EmptyBook />;

  return (
    <motion.div variants={containerVariant} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={itemVariant} className="flex flex-col gap-1">
        <h1 className="text-3xl font-semibold tracking-tight text-fg md:text-4xl">Dispute queue</h1>
        <p className="mt-1 text-[15px] font-medium leading-relaxed text-muted">
          {rows.length} of {total} cases · filters persist when you open a case
        </p>
      </motion.div>

      <motion.div variants={itemVariant} className="flex flex-col gap-2 rounded-2xl bg-surface p-3 shadow-[var(--shadow-subtle)] ring-1 ring-border/50">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
          <Input
            aria-label="Search disputes"
            value={localQ}
            placeholder="Search ID, merchant, reason…"
            className="pl-9 h-11 border-border/50 bg-surface-2 text-fg placeholder:text-muted focus-visible:ring-1 focus-visible:ring-accent"
            onChange={(e) => setLocalQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") set({ q: localQ || undefined });
            }}
            onBlur={() => set({ q: localQ || undefined })}
          />
        </div>
        <div className="grid grid-cols-2 gap-2 md:grid-cols-5">
          <FilterSelect
            value={merchant}
            onChange={(v) => set({ merchant: v === "all" ? undefined : v })}
            options={[
              { value: "all", label: "All merchants" },
              ...merchants.map((m) => ({ value: m.id, label: m.name })),
            ]}
          />
          <FilterSelect
            value={family}
            onChange={(v) => set({ family: v === "all" ? undefined : v })}
            options={[
              { value: "all", label: "All reason families" },
              { value: "unauthorized", label: "Unauthorized" },
              { value: "not_received", label: "Not received" },
              { value: "service_issue", label: "Service / quality" },
              { value: "other", label: "Other" },
            ]}
          />
          <FilterSelect
            value={category}
            onChange={(v) => set({ category: v === "all" ? undefined : v })}
            options={[
              { value: "all", label: "All categories" },
              { value: "friendly_fraud_likely", label: "Friendly fraud" },
              { value: "merchant_service_issue", label: "Service issue" },
              { value: "true_fraud_likely", label: "True fraud" },
              { value: "technical_or_insufficient_information", label: "Insufficient info" },
            ]}
          />
          <FilterSelect
            value={state}
            onChange={(v) => set({ state: v === "all" ? undefined : v })}
            options={[
              { value: "all", label: "All states" },
              { value: "draft_ready", label: "Draft ready" },
              { value: "human_review", label: "Human review" },
              { value: "evidence_incomplete", label: "Evidence incomplete" },
              { value: "not_contested", label: "Not contested" },
            ]}
          />
          <div className="flex items-center gap-2">
            <ToggleChip
              on={review}
              label="Review only"
              onClick={() => set({ review: review ? undefined : true })}
            />
            <ToggleChip
              on={high}
              label="High-value"
              onClick={() => set({ high: high ? undefined : true })}
            />
          </div>
        </div>
      </motion.div>

      <motion.div variants={itemVariant} className="hidden overflow-hidden rounded-2xl bg-surface shadow-[var(--shadow-subtle)] ring-1 ring-border/50 md:block">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[960px] text-left text-[13px]">
            <thead className="border-b border-border/50 text-[11px] font-bold uppercase tracking-wider text-muted bg-surface-2/50">
              <tr>
                <th className="px-4 py-3">Case</th>
                <th className="px-4 py-3">Merchant</th>
                <th className="px-4 py-3">Reason</th>
                <th className="px-4 py-3 text-right">Amount</th>
                <th className="px-4 py-3">Category</th>
                <th className="px-4 py-3 text-right">p(win)</th>
                <th className="px-4 py-3 text-right">Evidence</th>
                <th className="px-4 py-3">Policy</th>
                <th className="px-4 py-3">State</th>
              </tr>
            </thead>
            <motion.tbody variants={containerVariant} className="divide-y divide-border/50">
              {rows.map((d) => (
                <motion.tr variants={itemVariant} key={d.id} className="transition-colors hover:bg-surface-2 group">
                  <td className="px-4 py-3">
                    <Link
                      to="/disputes/$caseId"
                      params={{ caseId: d.id }}
                      search={search}
                      className="font-mono text-xs font-semibold text-accent group-hover:underline"
                    >
                      {d.id}
                    </Link>
                    {d.isDemo ? (
                      <span className="ml-2 rounded bg-warn/10 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-warn">demo</span>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 font-medium text-fg">{d.merchantName}</td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FamilyBadge value={d.reasonFamily} />
                      <span className="font-mono text-[11px] font-semibold text-muted">{d.reasonCode}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs font-semibold tabular-nums text-fg">
                    {formatINR(d.disputedAmount)}
                  </td>
                  <td className="px-4 py-3">
                    {d.prediction ? (
                      <CategoryBadge value={d.prediction.predictedCategory} />
                    ) : (
                      <span className="text-muted">—</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs font-semibold tabular-nums text-muted">
                    {d.prediction ? formatScore(d.prediction.fightWorthinessProbability) : "—"}
                  </td>
                  <td className="px-4 py-3 text-right font-mono text-xs font-semibold tabular-nums text-muted">
                    {d.evidencePackage ? formatPct(d.evidencePackage.completenessScore, 0) : "—"}
                  </td>
                  <td className="px-4 py-3">
                    {d.policyDecision ? <FightBadge value={d.policyDecision.fightDecision} /> : "—"}
                  </td>
                  <td className="px-4 py-3">
                    <StateBadge value={d.state} />
                  </td>
                </motion.tr>
              ))}
            </motion.tbody>
          </table>
        </div>
      </motion.div>

      <motion.div variants={containerVariant} className="grid gap-3 md:hidden">
        {rows.map((d) => (
          <motion.div variants={itemVariant} key={d.id}>
            <Link
              to="/disputes/$caseId"
              params={{ caseId: d.id }}
                      search={search}
              className="block rounded-2xl bg-surface p-4 shadow-[var(--shadow-subtle)] ring-1 ring-border/50 transition-all duration-300 hover:bg-surface-2 hover:-translate-y-0.5"
            >
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs font-semibold text-accent">{d.id}</span>
                <StateBadge value={d.state} />
              </div>
              <div className="mt-2 text-[14px] font-medium text-fg">{d.merchantName}</div>
              <div className="mt-1 flex items-center justify-between text-xs font-medium text-muted">
                <span>{d.reasonLabel}</span>
                <span className="font-mono text-[13px] font-bold tabular-nums text-fg">{formatINR(d.disputedAmount)}</span>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {d.prediction ? <CategoryBadge value={d.prediction.predictedCategory} /> : null}
                {d.policyDecision ? (
                  <FightBadge value={d.policyDecision.fightDecision} />
                ) : null}
              </div>
            </Link>
          </motion.div>
        ))}
      </motion.div>
      {rows.length === 0 ? <p role="status" className="rounded-md border border-border p-6 text-muted">No cases match these filters. Change a filter or return to the first page.</p> : null}
      <nav aria-label="Dispute pages" className="flex items-center justify-between gap-4">
        <Button variant="secondary" disabled={(search.page ?? 1) === 1} onClick={() => set({ page: (search.page ?? 1) - 1 })}>Previous</Button>
        <span className="text-sm text-muted">Page {search.page ?? 1} of {Math.max(1, Math.ceil(total / 50))} · {total} cases</span>
        <Button variant="secondary" disabled={(search.page ?? 1) * 50 >= total} onClick={() => set({ page: (search.page ?? 1) + 1 })}>Next</Button>
      </nav>
    </motion.div>
  );
}

function FilterSelect({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      aria-label={options[0]?.label}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="h-11 w-full appearance-none rounded-xl bg-surface-2 px-3 text-[13px] font-medium text-fg ring-1 ring-border/50 transition-colors hover:bg-surface-3 focus:outline-none focus:ring-accent"
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

function ToggleChip({
  on,
  label,
  onClick,
}: {
  on: boolean;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={on}
      className={
        on
          ? "h-11 flex-1 rounded-xl bg-accent px-3 text-[13px] font-semibold text-white shadow-sm transition-transform active:scale-95"
          : "h-11 flex-1 rounded-xl bg-surface-2 px-3 text-[13px] font-medium text-muted ring-1 ring-border/50 transition-all hover:bg-surface-3 active:scale-95"
      }
    >
      {label}
    </button>
  );
}

