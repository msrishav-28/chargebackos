import { createFileRoute, Link } from "@tanstack/react-router";
import { motion, Variants } from "framer-motion";
import { Card, CardHint, CardHeader, CardTitle } from "@/components/ui/card";
import { OpsBanner, OpsLoading } from "@/components/ops-state";
import { ActionBadge } from "@/components/status";
import { REASON_FAMILY_LABELS, formatPct } from "@/lib/chargebackos";
import { useDisputesQuery, useOverviewQuery, usePoliciesQuery } from "@/lib/ops-query";
import type { ReasonFamily } from "@/lib/chargebackos/types";

export const Route = createFileRoute("/_console/policies")({
  component: PoliciesPage,
});

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

function PoliciesPage() {
  const pol = usePoliciesQuery();
  const book = useOverviewQuery();
  const blockedQ = useDisputesQuery({ blocked: true, limit: "6" });
  if (pol.isLoading || book.isLoading) return <OpsLoading />;
  if (pol.error) return <OpsBanner error={pol.error} />;
  if (book.error) return <OpsBanner error={book.error} />;

  const profiles = pol.data?.profiles ?? [];
  const schemas = pol.data?.evidenceSchemas ?? [];
  const version = pol.data?.policyVersion ?? "Unavailable";
  const merchants = book.data?.merchants ?? [];
  const blocked = blockedQ.data?.items ?? [];

  return (
    <motion.div variants={containerVariant} initial="hidden" animate="show" className="space-y-6">
      {blockedQ.error ? <OpsBanner error={blockedQ.error} onRetry={() => void blockedQ.refetch()} /> : null}
      <motion.div variants={itemVariant}>
        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-accent">
          {version}
        </p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-fg md:text-4xl">Policy engine</h1>
        <p className="mt-3 max-w-3xl text-[15px] font-medium leading-relaxed text-muted">
          Deterministic, versioned, and independent of the model. Every automatic draft
          requires a passing decision. Analysts cannot edit these thresholds in the demo.
        </p>
      </motion.div>

      <motion.div variants={itemVariant} className="grid gap-5 md:grid-cols-3">
        {profiles.map((p) => {
          const n = merchants.filter((m) => m.policyProfile === p.id).length;
          return (
            <Card key={p.id}>
              <CardHeader>
                <div className="flex w-full items-start justify-between">
                  <CardTitle>{p.label}</CardTitle>
                  <span className="font-mono text-xs font-semibold tabular-nums text-muted bg-surface-2 px-2 py-1 rounded-md">{n} merchants</span>
                </div>
              </CardHeader>
              <p className="text-[13px] font-medium leading-relaxed text-muted mt-2">{p.description}</p>
              <dl className="mt-5 space-y-2 border-t border-border/50 pt-4">
                <Row k="Min confidence" v={formatPct(p.minConfidence)} />
                <Row k="Min p(win)" v={formatPct(p.minWinProbability)} />
                <Row k="Min expected value" v={`₹${p.minExpectedValue}`} />
                <Row k="True-fraud default" v={p.trueFraudDefault.replaceAll("_", " ")} />
                <Row k="Max auto-prep" v={formatPct(p.maxAutoPrepRate)} />
              </dl>
            </Card>
          );
        })}
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardTitle>Mandatory checks (evaluation order)</CardTitle>
          <ol className="mt-4 list-decimal space-y-2.5 pl-5 text-[14px] font-medium text-muted marker:text-accent/70 marker:font-semibold">
            <li>Case is in a policy-evaluable state.</li>
            <li>Reason family selects the mandatory evidence checklist.</li>
            <li>Mandatory evidence completeness equals 1.00 — otherwise block auto-draft.</li>
            <li>Calibrated classification confidence vs merchant minimum.</li>
            <li>Calibrated fight-worthiness vs merchant minimum.</li>
            <li>Expected recovered value vs merchant minimum.</li>
            <li>Sensitive category (true-fraud-likely) routes to human review.</li>
            <li>Conflicting support vs fulfillment evidence routes to human review.</li>
          </ol>
          <p className="mt-5 rounded-xl bg-accent/5 p-4 text-[13px] font-medium leading-relaxed text-accent/90 ring-1 ring-accent/10">
            The language model cannot override any of these rules. A direct prepare-draft
            call is rejected without a passing policy decision.
          </p>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Required evidence schemas</CardTitle>
              <CardHint>Reason-family registry v1 · missing required fields always block automation</CardHint>
            </div>
          </CardHeader>
          <div className="grid gap-4 md:grid-cols-2 mt-4">
            {schemas.map((s) => (
              <div key={s.reasonFamily} className="rounded-2xl bg-surface-2 p-4 shadow-[var(--shadow-subtle)] ring-1 ring-border/50 transition-all hover:bg-surface-3">
                <div className="text-[14px] font-semibold text-fg">{REASON_FAMILY_LABELS[s.reasonFamily as ReasonFamily] ?? s.reasonFamily}</div>
                <div className="mt-3 text-[13px] font-medium">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-warn">Required</div>
                  <p className="text-muted mt-0.5">{s.required.join(" · ")}</p>
                  <div className="mt-3 text-[10px] font-bold uppercase tracking-wider text-accent">Preferred</div>
                  <p className="text-muted mt-0.5">{s.preferred.join(" · ")}</p>
                  <div className="mt-3 text-[10px] font-bold uppercase tracking-wider text-subtle">Optional</div>
                  <p className="text-muted mt-0.5">{s.optional.join(" · ")}</p>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card className="flex flex-col">
          <CardHeader>
            <div>
              <CardTitle>Example blocked decisions</CardTitle>
              <CardHint>Live cases where policy withheld automatic representment</CardHint>
            </div>
          </CardHeader>
          <div className="divide-y divide-border/50 mt-4 flex-1">
            {blocked.map((d) => (
              <Link
                key={d.id}
                to="/disputes/$caseId"
                params={{ caseId: d.id }}
                className="group flex flex-col gap-2 py-3.5 transition-colors hover:bg-surface-2 md:flex-row md:items-center md:justify-between -mx-4 px-4 rounded-xl"
              >
                <div>
                  <div className="font-mono text-xs font-semibold text-accent group-hover:underline">{d.id}</div>
                  <div className="text-[14px] font-medium text-fg mt-1">
                    {d.merchantName} <span className="text-border/50 mx-1">|</span> {d.reasonLabel}
                  </div>
                  <div className="text-[13px] font-medium text-muted mt-1">
                    {(d.policyDecision?.blockReasons ?? []).map((b) => b.replaceAll("_", " ")).join(" · ") ||
                      "Routed without auto-prep"}
                  </div>
                </div>
                {d.policyDecision ? <ActionBadge value={d.policyDecision.recommendedAction} /> : null}
              </Link>
            ))}
          </div>
        </Card>
      </motion.div>
    </motion.div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between gap-3 text-[13px] font-medium">
      <dt className="text-muted">{k}</dt>
      <dd className="font-mono text-xs font-semibold tabular-nums text-fg">{v}</dd>
    </div>
  );
}
