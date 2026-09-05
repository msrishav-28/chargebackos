import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, Variants } from "framer-motion";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip as RTooltip,
  XAxis,
  YAxis,
} from "recharts";
import { KpiCard } from "@/components/kpi-card";
import { EmptyBook, OpsBanner, OpsLoading } from "@/components/ops-state";
import { CategoryBadge } from "@/components/status";
import { Card, CardHint, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CATEGORY_SHORT,
  formatINR,
  formatNumber,
  formatPct,
  formatScore,
} from "@/lib/chargebackos";
import { useOverviewQuery } from "@/lib/ops-query";
import { EvaluationRun } from "@/components/evaluation-run";

export const Route = createFileRoute("/_console/evaluation")({
  component: EvaluationPage,
});

const CHART = {
  grid: "#e3e4e8",
  tick: "#7c7f88",
  seafoam: "#44b48b",
  danger: "#111a4a",
  warn: "#ec652b",
  muted: "#7c7f88",
};

const containerVariant: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05, delayChildren: 0.05 },
  },
};

const itemVariant: Variants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { type: "spring", bounce: 0.2, duration: 0.6 } },
};

function EvaluationPage() {
  const book = useOverviewQuery();
  if (book.isLoading) return <OpsLoading />;
  if (book.error) return <OpsBanner error={book.error} />;
  const ev = book.data?.evaluation;
  if (!ev) return <EmptyBook />;
  const cls = ev.classification;
  const ml = ev.strategies.find((s) => s.strategy === "ml_policy");
  if (!ml) return <EmptyBook />;
  const leadingNet = Math.max(...ev.strategies.map((s) => s.netValue));
  const gallery = book.data?.failureGallery ?? [];

  const calData = ev.calibration.bins
    .filter((b) => b.count > 0)
    .map((b) => ({
      pred: Number(b.meanPred.toFixed(2)),
      actual: Number(b.meanActual.toFixed(2)),
      perfect: Number(b.meanPred.toFixed(2)),
    }));

  const thr = ev.thresholdCurve.map((p) => ({
    t: p.threshold,
    precision: p.precision,
    recall: p.recall,
    net: p.netValue,
    fp: p.falsePositiveCost,
  }));

  return (
    <motion.div variants={containerVariant} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={itemVariant}>
        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-accent">Held-out lab</p>
        <EvaluationRun />
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-fg md:text-4xl">Evaluation</h1>
        <p className="mt-3 max-w-3xl text-[15px] font-medium leading-relaxed text-muted">
          Train {ev.nTrain} · validation {ev.nValid} · frozen test {ev.nTest}. Threshold
          selected on validation only, then locked. Seed {ev.seed} · {ev.datasetVersion} ·{" "}
          {ev.modelVersion}.
        </p>
      </motion.div>

      <motion.div variants={itemVariant} className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <KpiCard label="Category accuracy" value={formatPct(cls.accuracy)} />
        <KpiCard label="Macro F1" value={formatPct(cls.macroF1)} />
        <KpiCard label="Fight PR-AUC" value={formatScore(ev.fightWorthiness.prAuc)} />
        <KpiCard label="Fight ROC-AUC" value={formatScore(ev.fightWorthiness.rocAuc)} />
        <KpiCard label="Brier (p win)" value={formatScore(ev.calibration.brierScore, 3)} />
        <KpiCard label="ECE" value={formatScore(ev.calibration.ece, 3)} />
        <KpiCard
          label="Operating threshold"
          value={formatScore(ev.selectedThreshold)}
          hint="Frozen from validation"
        />
        <KpiCard
          label="ML + policy test net"
          value={formatINR(ml.netValue, true)}
          hint="Rules-only currently leads on this split"
          tone="accent"
        />
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardTitle>Threshold rationale</CardTitle>
          <p className="mt-3 text-[14px] font-medium leading-relaxed text-muted">{ev.thresholdRationale}</p>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant} className="grid gap-5 lg:grid-cols-2">
        <Card className="flex flex-col">
          <CardHeader>
            <div>
              <CardTitle>Confusion matrix · category (test)</CardTitle>
              <CardHint>Rows are true class, columns are predicted</CardHint>
            </div>
          </CardHeader>
          <div className="overflow-x-auto mt-2">
            <table className="w-full text-[13px]">
              <thead>
                <tr>
                  <th className="p-2 text-left font-semibold text-muted border-b border-border/50">true \ pred</th>
                  {cls.labels.map((l) => (
                    <th key={l} className="p-2 text-right font-semibold text-muted border-b border-border/50">
                      {CATEGORY_SHORT[l]}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {cls.labels.map((row, i) => (
                  <tr key={row}>
                    <td className="p-2 font-medium text-muted">{CATEGORY_SHORT[row]}</td>
                    {cls.confusion[i]!.map((n, j) => (
                      <td
                         key={j}
                        className={`p-2 text-right font-mono text-[13px] font-semibold tabular-nums ${
                          i === j ? "text-accent bg-accent/5 rounded" : "text-fg"
                        }`}
                      >
                        {n}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-6 divide-y divide-border/50 pt-2 flex-1">
            {cls.labels.map((l) => {
              const m = cls.perClass[l];
              return (
                <div key={l} className="flex flex-wrap items-center justify-between gap-3 py-3">
                  <CategoryBadge value={l} />
                  <div className="font-mono text-xs font-semibold uppercase tracking-wider tabular-nums text-muted">
                    P <span className="text-fg">{formatPct(m.precision)}</span> · R <span className="text-fg">{formatPct(m.recall)}</span> · F1 <span className="text-fg">{formatPct(m.f1)}</span> · n{" "}
                    <span className="text-fg">{m.support}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </Card>

        <Card className="flex flex-col">
          <CardHeader>
            <div>
              <CardTitle>Calibration · fight-worthiness</CardTitle>
              <CardHint>Reliability on held-out p(win) vs simulated win rate</CardHint>
            </div>
          </CardHeader>
          <div className="h-64 mt-4 flex-1">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={calData} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
                <CartesianGrid stroke={CHART.grid} vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="pred" tick={{ fill: CHART.tick, fontSize: 11, fontWeight: 500 }} axisLine={false} tickLine={false} dy={10} />
                <YAxis tick={{ fill: CHART.tick, fontSize: 11, fontWeight: 500 }} domain={[0, 1]} axisLine={false} tickLine={false} />
                <RTooltip
                  cursor={{ stroke: "rgba(17,26,74,0.05)", strokeWidth: 2 }}
                  contentStyle={{
                    background: "#ffffff",
                    border: "1px solid #e3e4e8",
                    borderRadius: 12,
                    fontSize: 12,
                    fontWeight: 500,
                    boxShadow: "0 8px 16px -2px rgba(17,26,74,0.05)",
                  }}
                />
                <Line type="monotone" dataKey="perfect" stroke={CHART.muted} strokeDasharray="4 4" dot={false} name="Perfect" />
                <Line type="monotone" dataKey="actual" stroke={CHART.seafoam} strokeWidth={2} name="Observed win rate" activeDot={{ r: 6, fill: CHART.seafoam, stroke: "#fff", strokeWidth: 2 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Threshold–cost trade-off (validation)</CardTitle>
              <CardHint>Precision, recall, net value, and false-positive cost vs p(win) threshold</CardHint>
            </div>
          </CardHeader>
          <div className="h-72 mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={thr} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
                <CartesianGrid stroke={CHART.grid} vertical={false} strokeDasharray="3 3" />
                <XAxis dataKey="t" tick={{ fill: CHART.tick, fontSize: 11, fontWeight: 500 }} axisLine={false} tickLine={false} dy={10} />
                <YAxis yAxisId="l" tick={{ fill: CHART.tick, fontSize: 11, fontWeight: 500 }} domain={[0, 1]} axisLine={false} tickLine={false} />
                <YAxis
                  yAxisId="r"
                  orientation="right"
                  tick={{ fill: CHART.tick, fontSize: 11, fontWeight: 500 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `₹${Math.round(Number(v) / 1000)}k`}
                />
                <RTooltip
                  cursor={{ stroke: "rgba(17,26,74,0.05)", strokeWidth: 2 }}
                  contentStyle={{
                    background: "#ffffff",
                    border: "1px solid #e3e4e8",
                    borderRadius: 12,
                    fontSize: 12,
                    fontWeight: 500,
                    boxShadow: "0 8px 16px -2px rgba(17,26,74,0.05)",
                  }}
                />
                <Line yAxisId="l" type="monotone" dataKey="precision" stroke={CHART.seafoam} strokeWidth={2} name="Precision" dot={false} />
                <Line yAxisId="l" type="monotone" dataKey="recall" stroke={CHART.warn} strokeWidth={2} name="Recall" dot={false} />
                <Line yAxisId="r" type="monotone" dataKey="net" stroke="#111a4a" strokeWidth={2} name="Net value" dot={false} />
                <Line yAxisId="r" type="monotone" dataKey="fp" stroke={CHART.danger} strokeWidth={2} name="FP cost" dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Baseline comparison · frozen test</CardTitle>
              <CardHint>Same cases, four strategies. Human-review under ML+policy contests only if expected value is positive.</CardHint>
            </div>
          </CardHeader>
          <div className="overflow-x-auto mt-4">
            <table className="w-full min-w-[720px] text-[13px]">
              <thead className="text-[11px] font-bold uppercase tracking-wider text-muted border-b border-border/50">
                <tr>
                  <th className="px-3 py-3 text-left">Strategy</th>
                  <th className="px-3 py-3 text-right">Contested</th>
                  <th className="px-3 py-3 text-right">Wins</th>
                  <th className="px-3 py-3 text-right">Recovery</th>
                  <th className="px-3 py-3 text-right">Contest cost</th>
                  <th className="px-3 py-3 text-right">FP cost</th>
                  <th className="px-3 py-3 text-right">Net</th>
                  <th className="px-3 py-3 text-right">Precision</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/50">
                {ev.strategies.map((s) => (
                  <tr key={s.strategy}>
                    <td className="px-3 py-3 font-medium text-fg">
                      {s.label}
                      {s.netValue === leadingNet ? (
                        <span className="ml-3 rounded bg-accent/10 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-accent">
                          leads net value
                        </span>
                      ) : null}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-xs font-semibold tabular-nums text-muted">
                      {formatNumber(s.contested)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-xs font-semibold tabular-nums text-muted">
                      {formatNumber(s.wins)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-xs font-semibold tabular-nums text-muted">
                      {formatINR(s.grossRecovery, true)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-xs font-semibold tabular-nums text-muted">
                      {formatINR(s.contestCost, true)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-xs font-semibold tabular-nums text-muted">
                      {formatINR(s.falsePositiveCost, true)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-xs font-bold tabular-nums text-accent">
                      {formatINR(s.netValue, true)}
                    </td>
                    <td className="px-3 py-3 text-right font-mono text-xs font-semibold tabular-nums text-muted">
                      {formatPct(s.precisionContest)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Honest failure gallery</CardTitle>
              <CardHint>
                Misclassified held-out cases. Policy often still blocked a harmful automatic draft.
              </CardHint>
            </div>
          </CardHeader>
          <div className="grid gap-4 md:grid-cols-2 mt-4">
            {gallery.map((f) => (
              <Link
                key={f.caseId}
                to="/disputes/$caseId"
                params={{ caseId: f.caseId }}
                className="group rounded-2xl bg-surface-2 p-4 shadow-[var(--shadow-subtle)] ring-1 ring-border/50 transition-all duration-300 hover:bg-surface hover:shadow-[var(--shadow-md)] hover:-translate-y-0.5"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="font-mono text-xs font-semibold text-accent">{f.caseId}</span>
                  <span className="font-mono text-xs font-semibold tabular-nums text-muted group-hover:text-fg transition-colors">
                    conf <span className="text-fg">{formatPct(f.confidence)}</span>
                  </span>
                </div>
                <div className="mt-4 flex flex-wrap items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted">true</span>
                  <CategoryBadge value={f.trueCategory} />
                  <span className="text-[10px] font-bold uppercase tracking-wider text-muted ml-2">pred</span>
                  <CategoryBadge value={f.predictedCategory} />
                </div>
                <p className="mt-4 text-[13px] font-medium leading-relaxed text-muted">{f.whyFailed}</p>
                <p className="mt-3 border-t border-border/50 pt-3 text-[13px] font-medium">
                  {f.policyPreventedHarm ? (
                    <span className="text-ok">
                      Policy prevented automatic action ({f.policyAction.replaceAll("_", " ")}).
                    </span>
                  ) : (
                    <span className="text-warn">
                      Policy action: {f.policyAction.replaceAll("_", " ")}.
                    </span>
                  )}
                </p>
              </Link>
            ))}
          </div>
        </Card>
      </motion.div>
    </motion.div>
  );
}
