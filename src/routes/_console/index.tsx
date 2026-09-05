import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, Variants } from "framer-motion";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { ArrowRight, Shield } from "lucide-react";
import { KpiCard } from "@/components/kpi-card";
import { EmptyBook, OpsBanner, OpsLoading } from "@/components/ops-state";
import { Card, CardHint, CardHeader, CardTitle } from "@/components/ui/card";
import { CategoryBadge, StateBadge } from "@/components/status";
import {
  CATEGORY_SHORT,
  formatINR,
  formatNumber,
  formatPct,
} from "@/lib/chargebackos";
import { useDisputesQuery, useOverviewQuery } from "@/lib/ops-query";


export const Route = createFileRoute("/_console/")({
  component: OverviewPage,
});

const CHART = {
  grid: "#e3e4e8",
  tick: "#7c7f88",
  seafoam: "#44b48b",
  muted: "#7c7f88",
  warn: "#ec652b",
  danger: "#111a4a",
  indigo: "#111a4a",
};

const containerVariant: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08, delayChildren: 0.1 },
  },
};

const itemVariant: Variants = {
  hidden: { opacity: 0, y: 15 },
  show: { opacity: 1, y: 0, transition: { type: "spring", bounce: 0.3, duration: 0.8 } },
};

function OverviewPage() {
  const book = useOverviewQuery();
  const demosQ = useDisputesQuery({ is_demo: true, limit: "10" });
  if (book.isLoading) return <OpsLoading />;
  if (book.error) return <OpsBanner error={book.error} onRetry={() => void book.refetch()} />;
  const payload = book.data;
  const k = payload?.overview;
  const ev = payload?.evaluation;
  if (!k || !ev) return <EmptyBook />;

  const ml = ev.strategies.find((s) => s.strategy === "ml_policy");
  const nothing = ev.strategies.find((s) => s.strategy === "contest_nothing");
  const everything = ev.strategies.find((s) => s.strategy === "contest_everything");
  const rules = ev.strategies.find((s) => s.strategy === "rules_only");
  if (!ml || !nothing || !everything || !rules) return <EmptyBook />;

  const strategyBars = ev.strategies.map((s) => ({
    name: s.label,
    net: Math.round(s.netValue),
    fp: Math.round(s.falsePositiveCost),
    recovery: Math.round(s.grossRecovery),
  }));

  const catCounts = ev.classification.labels.map((lab, i) => ({
    name: CATEGORY_SHORT[lab] ?? lab,
    n: ev.classification.confusion[i]!.reduce((a, b) => a + b, 0),
  }));

  const q = payload?.queueCounts;
  const funnel = [
    { name: "Disputes", n: q?.total ?? k.totalDisputes },
    { name: "Auto-prep", n: q?.draftReady ?? 0 },
    { name: "Human review", n: q?.humanReview ?? k.humanReviewQueue },
    { name: "Not contested", n: q?.notContested ?? 0 },
  ];

  const demos = demosQ.data?.items ?? [];

  return (
    <motion.div variants={containerVariant} initial="hidden" animate="show" className="space-y-8">
      {demosQ.error ? <OpsBanner error={demosQ.error} onRetry={() => void demosQ.refetch()} /> : null}
      <motion.div variants={itemVariant} className="flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-accent">
            AI Risk Manager
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight text-fg md:text-4xl">
            Chargeback defense, measured
          </h1>
          <p className="mt-3 max-w-2xl text-[15px] font-medium leading-relaxed text-muted">
            One loss class. A calibrated model triages disputes; an evidence
            assembler checks proof; a deterministic policy engine decides. The
            model never executes an action.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-xl bg-surface shadow-[var(--shadow-subtle)] ring-1 ring-border/50 px-4 py-2 text-xs font-semibold text-accent">
          <Shield className="size-4" strokeWidth={2} />
          Defense-only · synthetic data · held-out test
        </div>
      </motion.div>

      <motion.div variants={itemVariant} className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard
          label="Disputed amount"
          value={formatINR(k.totalDisputedAmount, true)}
          hint={`${formatNumber(k.totalDisputes)} cases · ${formatNumber(k.heldOutN)} held-out`}
        />
        <KpiCard
          label="Simulated recovery (test)"
          value={formatINR(k.simulatedRecovered, true)}
          hint="ML + policy on frozen test split — not the leading strategy"
          tone="ok"
        />
        <KpiCard
          label="Net value after costs"
          value={formatINR(k.netValue, true)}
          hint={`ML + policy. Rules-only leads at ${formatINR(rules.netValue, true)}`}
          tone={k.netValue >= 0 ? "accent" : "danger"}
        />
        <KpiCard
          label="False-positive cost"
          value={formatINR(k.falsePositiveCost, true)}
          hint="Wasted handling + goodwill penalty"
          tone="warn"
        />
      </motion.div>

      <motion.div variants={itemVariant} className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Strategy contest precision" value={formatPct(ml.precisionContest)} hint="ML + policy on held-out test" />
        <KpiCard label="Strategy contest recall" value={formatPct(ml.recallWinnable)} hint="Share of winnable test cases contested" />
        <KpiCard label="Macro F1 (category)" value={formatPct(k.modelMacroF1)} hint="Four-class triage" />
        <KpiCard
          label="Human-review queue"
          value={formatNumber(q?.humanReview ?? k.humanReviewQueue)}
          hint={`Auto-prep ${formatPct(k.autoPrepRate)}`}
          tone="warn"
        />
      </motion.div>

      <motion.div variants={itemVariant} className="grid gap-5 lg:grid-cols-5">
        <Card className="lg:col-span-3 flex flex-col">
          <CardHeader>
            <div>
              <CardTitle>Strategy comparison · held-out test</CardTitle>
              <CardHint>Rules-only currently leads ML + policy on simulated net value. Contesting is not free.</CardHint>
            </div>
          </CardHeader>
          <div className="h-64 mt-4 flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={strategyBars} barGap={4} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
                <CartesianGrid stroke={CHART.grid} vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="name" tick={{ fill: CHART.tick, fontSize: 11, fontWeight: 500 }} axisLine={false} tickLine={false} dy={10} />
                <YAxis
                  tick={{ fill: CHART.tick, fontSize: 11, fontWeight: 500 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `₹${Math.round(Number(v) / 1000)}k`}
                />
                <RTooltip
                  cursor={{ fill: "rgba(17,26,74,0.03)" }}
                  contentStyle={{
                    background: "#ffffff",
                    border: "1px solid #e3e4e8",
                    borderRadius: 12,
                    fontSize: 12,
                    fontWeight: 500,
                    boxShadow: "0 8px 16px -2px rgba(17,26,74,0.05)",
                  }}
                  formatter={(v: number, name: string) => [formatINR(v), name]}
                />
                <Bar dataKey="net" name="Net value" fill={CHART.seafoam} radius={[6, 6, 0, 0]} />
                <Bar dataKey="fp" name="FP cost" fill={CHART.danger} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-6 grid grid-cols-2 gap-3 text-xs text-muted md:grid-cols-4">
            {[nothing, everything, rules, ml].map((s) => (
              <div key={s.strategy} className="rounded-xl bg-surface-2 px-3 py-3 ring-1 ring-border/50">
                <div className="text-subtle font-medium">
                  {s.label}
                  {s.netValue === Math.max(nothing.netValue, everything.netValue, rules.netValue, ml.netValue) ? (
                    <span className="ml-2 text-[10px] font-bold uppercase tracking-wider text-accent">leads</span>
                  ) : null}
                </div>
                <div className="font-mono text-sm tabular-nums text-fg font-semibold mt-1">{formatINR(s.netValue, true)}</div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="lg:col-span-2 flex flex-col">
          <CardHeader>
            <div>
              <CardTitle>Decision funnel</CardTitle>
              <CardHint>Policy outcomes across the book</CardHint>
            </div>
          </CardHeader>
          <div className="space-y-4 mt-2">
            {funnel.map((row) => (
              <div key={row.name}>
                <div className="mb-1.5 flex justify-between text-[11px] font-semibold tracking-wide uppercase">
                  <span className="text-muted">{row.name}</span>
                  <span className="font-mono tabular-nums text-fg">{formatNumber(row.n)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-surface-3 ring-1 ring-border/50 inset-shadow-sm">
                  <motion.div
                    initial={{ width: 0 }}
                    whileInView={{ width: `${Math.max(4, (row.n / k.totalDisputes) * 100)}%` }}
                    transition={{ duration: 1, ease: "easeOut" }}
                    viewport={{ once: true }}
                    className="h-full rounded-full bg-accent"
                  />
                </div>
              </div>
            ))}
          </div>
          <div className="mt-8">
            <CardTitle>Category mix (test support)</CardTitle>
            <div className="mt-4 h-36">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={catCounts} layout="vertical" margin={{ left: 8, right: 8 }}>
                  <XAxis type="number" hide />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={108}
                    tick={{ fill: CHART.tick, fontSize: 11, fontWeight: 500 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Bar dataKey="n" radius={[0, 6, 6, 0]} barSize={16}>
                    {catCounts.map((_, i) => (
                      <Cell
                        key={i}
                        fill={[CHART.seafoam, CHART.warn, CHART.danger, CHART.indigo][i]}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Five-minute narrative cases</CardTitle>
              <CardHint>Pinned test-set examples covering auto-draft, review, missing evidence, true fraud, and negative EV</CardHint>
            </div>
            <Link to="/disputes" className="text-[13px] font-medium text-accent hover:underline flex items-center gap-1 group">
              Open queue <ArrowRight className="size-3.5 transition-transform group-hover:translate-x-1" />
            </Link>
          </CardHeader>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5 mt-2">
            {demos.map((d) => (
              <Link
                key={d.id}
                to="/disputes/$caseId"
                params={{ caseId: d.id }}
                className="group rounded-2xl bg-surface-2 p-4 shadow-[var(--shadow-subtle)] ring-1 ring-border/50 transition-all duration-300 hover:bg-surface hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs font-semibold text-accent">{d.id}</span>
                  <StateBadge value={d.state as "draft_ready" | "human_review" | "evidence_incomplete" | "not_contested" | "closed" | "received" | "normalized" | "triaged" | "evidence_collecting" | "policy_review" | "submitted_simulated" | "won_simulated" | "lost_simulated"} />
                </div>
                <div className="mt-3 text-[13px] font-semibold text-fg group-hover:text-accent transition-colors">{d.merchantName}</div>
                <div className="mt-0.5 text-xs text-muted font-medium line-clamp-1">{d.reasonLabel}</div>
                <div className="mt-4 flex items-center justify-between pt-3 border-t border-border/50">
                  <span className="font-mono text-sm font-semibold tabular-nums text-fg">{formatINR(d.disputedAmount)}</span>
                  {d.prediction ? <CategoryBadge value={d.prediction.predictedCategory} /> : null}
                </div>
              </Link>
            ))}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Top required-evidence gaps</CardTitle>
              <CardHint>Missing mandatory fields block automated representment — always</CardHint>
            </div>
          </CardHeader>
          <div className="divide-y divide-border/50 mt-2">
            {ev.evidenceGaps.map((g) => (
              <div key={g.key} className="flex items-center justify-between py-3 text-[13px] font-medium">
                <span className="text-fg">{g.label}</span>
                <span className="font-mono text-xs font-semibold tabular-nums text-accent bg-accent/5 px-2 py-1 rounded-md">
                  {formatNumber(g.missingCount)} missing
                </span>
              </div>
            ))}
          </div>
          <Link
            to="/evaluation"
            className="mt-5 inline-flex items-center gap-1.5 text-[13px] font-semibold text-accent hover:underline group"
          >
            Open evaluation lab <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
          </Link>
        </Card>
      </motion.div>
    </motion.div>
  );
}
