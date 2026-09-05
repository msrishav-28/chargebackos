import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { motion, Variants } from "framer-motion";
import {
  ArrowLeft,
  Check,
  Lock,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import {
  ActionBadge,
  CategoryBadge,
  FamilyBadge,
  FightBadge,
  SplitBadge,
  StateBadge,
} from "@/components/status";
import { Button } from "@/components/ui/button";
import { Card, CardHint, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyBook, OpsBanner, OpsLoading } from "@/components/ops-state";
import {
  CATEGORY_HINT,
  FEATURE_LABELS,
  formatDate,
  formatINR,
  formatPct,
  formatScore,
} from "@/lib/chargebackos";
import { actionRequest, OpsApiError, rewriteDraftRequest } from "@/lib/ops-api";
import { useDisputeQuery } from "@/lib/ops-query";
import { useQueryClient } from "@tanstack/react-query";
import type { ActionType, FeatureKey } from "@/lib/chargebackos/types";
import { PendingCase } from "@/components/pending-case";
import { useStaff } from "@/lib/ops-context";

export const Route = createFileRoute("/_console/disputes/$caseId")({
  component: CasePage,
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


function CasePage() {
  const staff = useStaff();
  const search = Route.useSearch();
  const { caseId } = Route.useParams();
  const queryClient = useQueryClient();
  const q = useDisputeQuery(caseId);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  if (q.isLoading) return <OpsLoading />;
  if (q.error instanceof OpsApiError && q.error.status === 404) {
    return (
      <div className="space-y-3">
        <Link to="/disputes" search={search} className="inline-flex items-center gap-1 text-sm font-medium text-muted hover:text-fg transition-colors">
          <ArrowLeft className="size-4" /> Queue
        </Link>
        <p className="text-fg font-medium">Case {caseId} was not found.</p>
      </div>
    );
  }
  if (q.error) return <OpsBanner error={q.error} onRetry={() => void q.refetch()} />;

  const c = q.data;
  if (!c) return <EmptyBook />;

  const pred = c.prediction;
  const ev = c.evidencePackage;
  const pol = c.policyDecision;
  if (!pred || !ev || !pol) {
    return <><Link to="/disputes" search={search} className="mb-4 inline-block underline">Back to queue</Link><PendingCase data={c} /></>;
  }
  const snap = c.featureSnapshot;
  const maxAbs = Math.max(...(pred.shap ?? []).map((s) => Math.abs(s.contribution)), 0.001);

  const onAction = async (action: Extract<ActionType, "request_human_review" | "recommend_do_not_contest" | "prepare_representment_draft" | "close_case">) => {
    setErr(null);
    setBusy(true);
    try {
      await actionRequest(c.id, action);
      await queryClient.invalidateQueries({ queryKey: ["dispute", caseId] });
      await queryClient.invalidateQueries({ queryKey: ["disputes"] });
      await queryClient.invalidateQueries({ queryKey: ["overview"] });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Blocked");
    } finally {
      await queryClient.invalidateQueries({ queryKey: ["dispute", caseId] });
      setBusy(false);
    }
  };

  const onGrok = async () => {
    setBusy(true);
    setErr(null);
    try {
      await rewriteDraftRequest(c.id);
      await queryClient.invalidateQueries({ queryKey: ["dispute", caseId] });
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Draft rewrite failed");
    } finally {
      setBusy(false);
    }
  };

  const canAct = (action: (typeof c.allowedActions)[number]) => c.allowedActions.includes(action);
  const draftAllowed = canAct("prepare_representment_draft");

  return (
    <motion.div variants={containerVariant} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={itemVariant} className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div>
          <Link to="/disputes" search={search} className="group inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-muted hover:text-fg transition-colors">
            <ArrowLeft className="size-3.5 transition-transform group-hover:-translate-x-1" /> Queue
          </Link>
          <div className="mt-3 flex flex-wrap items-center gap-2.5">
            <h1 className="font-mono text-2xl font-bold tracking-tight text-fg md:text-3xl">{c.id}</h1>
            <StateBadge value={c.state} />
            {c.isDemo ? (
              <span className="rounded-full bg-warn/15 px-2 py-0.5 text-[11px] font-bold text-warn">
                Narrative case
              </span>
            ) : null}
            <SplitBadge value={c.split} />
          </div>
          <p className="mt-2 text-[15px] font-medium text-muted">
            {c.merchantName} · {c.reasonLabel} <span className="font-mono text-xs">({c.reasonCode})</span> · {formatDate(c.openedAt)}
          </p>
        </div>
        <div className="text-right mt-3 md:mt-0">
          <div className="font-mono text-3xl font-bold tabular-nums text-fg">{formatINR(c.disputedAmount)}</div>
          <div className="text-xs font-semibold uppercase tracking-wider text-muted mt-1">Disputed amount</div>
        </div>
      </motion.div>

      {err ? (
        <motion.div role="alert" variants={itemVariant} className="rounded-xl bg-danger/10 ring-1 ring-danger/20 px-4 py-3 text-[13px] font-medium text-danger">
          {err}
        </motion.div>
      ) : null}

      <motion.div variants={itemVariant} className="flex flex-wrap gap-2.5 pt-2 pb-2">
        <Button
          disabled={busy || !draftAllowed}
          onClick={() => onAction("prepare_representment_draft")}
        >
          {c.state === "human_review" ? "Approve draft (reviewer)" : "Confirm auto-draft"}
        </Button>
        <Button disabled={busy || !canAct("request_human_review")} variant="secondary" onClick={() => onAction("request_human_review")}>
          Route to review
        </Button>
        <Button disabled={busy || !canAct("recommend_do_not_contest")} variant="outline" onClick={() => onAction("recommend_do_not_contest")}>
          Do not contest
        </Button>
        <Button disabled={busy || !canAct("close_case")} variant="ghost" onClick={() => onAction("close_case")}>
          Close
        </Button>
      </motion.div>

      <motion.div variants={itemVariant} className="grid gap-5 lg:grid-cols-3">
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle>Transaction</CardTitle>
          </CardHeader>
          <dl className="mt-3 space-y-2.5 text-[13px] flex-1">
            <Row k="Transaction" v={c.transactionId} mono />
            <Row k="Order" v={c.orderId ?? "Unavailable"} mono />
            <Row k="Customer" v={c.customerLabel} />
            <Row k="Paid" v={snap?.transaction.transactionAt ? formatDate(snap.transaction.transactionAt) : "—"} />
            <Row
              k="Auth"
              v={snap?.transaction.authorizationApproved ? "Approved" : "Incomplete"}
            />
            <Row
              k="Descriptor"
              v={snap?.transaction.billingDescriptorRecognized ? "Recognized" : "Uncertain"}
            />
            <Row k="Fulfillment" v={snap?.fulfillment.type ?? "—"} />
            <Row
              k="Delivery"
              v={snap?.fulfillment.delivered ? "Confirmed" : snap?.fulfillment.shipped ? "Shipped" : "Not shipped"}
            />
          </dl>
        </Card>

        <Card className="flex flex-col">
          <CardHeader>
            <div>
              <CardTitle>Model assessment</CardTitle>
              <CardHint>Operational estimate — not a legal finding</CardHint>
            </div>
            <CategoryBadge value={pred.predictedCategory} />
          </CardHeader>
          <p className="text-[13px] font-medium text-muted mt-2">{CATEGORY_HINT[pred.predictedCategory]}</p>
          <dl className="mt-4 space-y-2.5 text-[13px] flex-1">
            <Row k="Calibrated confidence" v={formatPct(pred.categoryConfidence)} />
            <Row k="Fight-worthiness p(win)" v={formatScore(pred.fightWorthinessProbability)} />
            <Row k="Expected recovered value" v={formatINR(pred.expectedRecoveredValue)} />
            <Row k="Model" v={pred.modelVersion} mono />
          </dl>
          <div className="mt-4 space-y-2 border-t border-border/50 pt-4">
            {Object.entries(pred.classScores).map(([k, v]) => (
              <div key={k} className="flex items-center gap-2">
                <div className="w-28 truncate text-[11px] font-medium uppercase tracking-wide text-muted">
                  {k.replaceAll("_", " ")}
                </div>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface-3 ring-1 ring-border/50 inset-shadow-sm">
                  <motion.div
                    initial={{ width: 0 }}
                    whileInView={{ width: `${v * 100}%` }}
                    transition={{ duration: 0.8, ease: "easeOut" }}
                    viewport={{ once: true }}
                    className="h-full bg-accent"
                  />
                </div>
                <div className="w-10 text-right font-mono text-xs font-semibold tabular-nums text-fg">
                  {formatPct(v, 0)}
                </div>
              </div>
            ))}
          </div>
        </Card>

        <Card className="flex flex-col">
          <CardHeader>
            <div>
              <CardTitle>Policy decision</CardTitle>
              <CardHint>
                {pol.policyVersion} · {pol.profile} · hash {pol.inputSnapshotHash.slice(0, 8)}...
              </CardHint>
            </div>
            {pol.allowed ? (
              <span className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-ok">
                <Check className="size-4" /> Allowed
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-warn">
                <Lock className="size-4" /> Gated
              </span>
            )}
          </CardHeader>
          <div className="flex flex-wrap gap-2 mt-2">
            <FightBadge value={pol.fightDecision} />
            <ActionBadge value={pol.recommendedAction} />
          </div>
          <div className="flex-1 mt-4">
            {pol.blockReasons.length ? (
              <ul className="space-y-2 text-[13px] font-medium text-warn bg-warn/5 p-3 rounded-xl ring-1 ring-warn/20">
                {pol.blockReasons.map((b) => (
                  <li key={b} className="flex gap-2">
                    <ShieldAlert className="mt-0.5 size-4 shrink-0" />
                    {b.replaceAll("_", " ")}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[13px] font-medium leading-relaxed text-muted bg-surface-2 p-3 rounded-xl ring-1 ring-border/50">
                Evidence complete, confidence and expected value passed the {pol.profile} profile.
              </p>
            )}
            <div className="mt-4 space-y-2 border-t border-border/50 pt-4">
              {pol.rulesEvaluated.map((r) => (
                <div key={r.rule} className="flex items-start justify-between gap-3 text-[13px] font-medium">
                  <span className={r.passed ? "text-muted" : "text-warn"}>
                    {r.rule.replaceAll("_", " ")}
                  </span>
                  <span className={`shrink-0 font-mono text-[11px] font-semibold uppercase tracking-wider ${r.passed ? "text-subtle" : "text-warn"}`}>
                    {r.passed ? "pass" : "flag"}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant} className="grid gap-5 lg:grid-cols-2">
        <Card className="flex flex-col">
          <CardHeader>
            <div>
              <CardTitle>Signals considered</CardTitle>
              <CardHint className="mt-1">
                Approximate Shapley contributions to the predicted class, relative to the training median. These explain model behavior, not causation.
              </CardHint>
            </div>
          </CardHeader>
          <div className="mt-4 space-y-3">
            {pred.shap.slice(0, 8).map((s) => {
              const pct = Math.min(100, (Math.abs(s.contribution) / maxAbs) * 50);
              const pos = s.contribution >= 0;
              return (
                <div key={s.feature} className="grid grid-cols-[minmax(0,1fr)_8rem] items-center gap-3 md:grid-cols-[minmax(0,1fr)_11rem]">
                  <div className="truncate text-[13px] font-medium text-fg">{s.label}</div>
                  <div className="flex h-2 overflow-hidden rounded-full bg-surface-3 ring-1 ring-border/50 inset-shadow-sm">
                    <div className="flex w-1/2 justify-end border-r border-border/50">
                      {!pos ? (
                        <motion.div
                          initial={{ width: 0 }}
                          whileInView={{ width: `${pct * 2}%` }}
                          transition={{ duration: 0.8, ease: "easeOut" }}
                          viewport={{ once: true }}
                          className="h-full rounded-l-full bg-danger"
                        />
                      ) : null}
                    </div>
                    <div className="flex w-1/2">
                      {pos ? (
                        <motion.div
                          initial={{ width: 0 }}
                          whileInView={{ width: `${pct * 2}%` }}
                          transition={{ duration: 0.8, ease: "easeOut" }}
                          viewport={{ once: true }}
                          className="h-full rounded-r-full bg-accent"
                        />
                      ) : null}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
          <ul className="mt-6 space-y-2.5 border-t border-border/50 pt-4 flex-1">
            {pred.shap.map((s) => (
              <li key={`l-${s.feature}`} className="flex items-center justify-between text-[13px] font-medium">
                <span className="text-muted">{FEATURE_LABELS[s.feature as FeatureKey] ?? s.label}</span>
                <span className={`font-mono text-xs font-semibold ${s.direction === "supports" ? "text-accent" : "text-danger"}`}>
                  {s.direction} · {s.contribution.toFixed(2)}
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <Card className="flex flex-col">
          <CardHeader>
            <div>
              <CardTitle>Evidence checklist</CardTitle>
              <CardHint>
                Completeness {formatPct(ev.completenessScore)} · mandatory{" "}
                {ev.mandatoryComplete ? "complete" : "blocked"} · hash {ev.packageHash.slice(0, 8)}...
              </CardHint>
            </div>
            <FamilyBadge value={c.reasonFamily as "unauthorized" | "not_received" | "service_issue" | "other"} />
          </CardHeader>
          <div className="space-y-3 mt-4 flex-1">
            {ev.items.map((item) => (
              <div
                key={item.id}
                className="rounded-xl bg-surface-2 p-4 shadow-[var(--shadow-subtle)] ring-1 ring-border/50"
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="text-[14px] font-semibold text-fg">{item.label}</div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-subtle">
                      {item.tier}
                    </span>
                    <span className={`text-xs font-bold uppercase tracking-wider ${item.present ? "text-ok" : "text-warn"}`}>
                      {item.present ? "on file" : "missing"}
                    </span>
                  </div>
                </div>
                <p className="mt-1.5 text-[13px] font-medium leading-relaxed text-muted">{item.summary}</p>
                {item.present ? (
                  <p className="mt-3 border-t border-border/50 pt-2 font-mono text-[10px] font-semibold uppercase tracking-wider text-subtle">
                    {item.sourceSystem} · {item.sourceReference}
                  </p>
                ) : null}
              </div>
            ))}
          </div>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardHeader>
            <div>
              <CardTitle>Representment draft</CardTitle>
              <CardHint>
                Grounded in cited evidence. Not a live filing. LLM rewrite is optional and
                still cannot invent facts.
              </CardHint>
            </div>
            <Button
              variant="secondary"
              disabled={busy || staff.role === "viewer" || !pol.allowed || c.state !== "draft_ready"}
              onClick={() => void onGrok()}
            >
              <Sparkles className="size-4" />
              {busy ? "Arranging…" : "Arrange with Grok"}
            </Button>
          </CardHeader>
          <div className="mt-4">
            {!draftAllowed ? (
              <p className="rounded-xl bg-warn/10 ring-1 ring-warn/20 px-4 py-3 text-[13px] font-medium text-warn">
                Draft control is disabled until policy allows it, or a human reviewer
                explicitly approves from the review queue.
              </p>
            ) : (
              <pre className="whitespace-pre-wrap rounded-xl bg-surface-2 ring-1 ring-border/50 p-5 font-sans text-[14px] font-medium leading-relaxed text-fg shadow-[var(--shadow-subtle)]">
                {c.draft?.text ?? "No draft."}
              </pre>
            )}
          </div>
          {c.draft && c.draft.citations.length > 0 ? (
            <div className="mt-5 border-t border-border/50 pt-5">
              <div className="text-[11px] font-bold uppercase tracking-widest text-muted">Citations</div>
              <ul className="mt-2 space-y-1.5 text-[13px] font-medium text-muted">
                {c.draft.citations.map((cit, i) => (
                  <li key={i} className="flex gap-2">
                    <span className="font-mono text-[11px] font-semibold text-accent mt-0.5">{cit.evidenceId}</span>
                    <span>{cit.evidenceLabel}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </Card>
      </motion.div>

      <motion.div variants={itemVariant} className="grid gap-5 lg:grid-cols-2">
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle>Simulated outcome</CardTitle>
          </CardHeader>
          <dl className="mt-3 space-y-2.5 text-[13px] flex-1">
            <Row k="Would win if contested" v={c.wouldWinIfContested == null ? "No simulation label" : c.wouldWinIfContested ? "Yes" : "No"} />
            <Row k="Latent p(win)" v={formatScore(c.latentWinProb ?? 0)} />
            <Row k="True class (eval only)" v={(c.trueCategory ?? "unknown").replaceAll("_", " ")} />
            <Row k="Hypothetical result" v={c.simulatedOutcome ?? "pending review"} />
            <Row k="Recovered" v={c.recoveredAmount == null ? "Unavailable" : formatINR(c.recoveredAmount)} />
            <Row k="Contest cost" v={formatINR(c.contestCost ?? 0)} />
            <Row k="FP penalty" v={c.falsePositiveCost == null ? "Unavailable" : formatINR(c.falsePositiveCost)} />
            <Row k="Case net" v={c.netValue == null ? "Unavailable" : formatINR(c.netValue)} />
          </dl>
          <p className="mt-5 border-t border-border/50 pt-4 text-[12px] font-medium leading-relaxed text-subtle">
            True labels are hidden from operators in production. Shown here because this
            is a Buildathon evaluation console.
          </p>
        </Card>
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle>Audit trail</CardTitle>
          </CardHeader>
          <ol className="mt-4 space-y-5 flex-1">
            {(c.timeline ?? []).map((evn, i) => (
              <li key={evn.id} className="relative pl-5">
                <span className="absolute left-0 top-1.5 size-2 rounded-full bg-accent ring-4 ring-surface" />
                {i !== (c.timeline ?? []).length - 1 && (
                  <span className="absolute left-[3px] top-4 h-[calc(100%+12px)] w-0.5 bg-border/50" />
                )}
                <div className="text-[11px] font-bold uppercase tracking-wider text-subtle">
                  {formatDate(evn.at)} · <span className="text-muted">{evn.actor}</span>
                  {evn.afterState ? ` · ${evn.afterState}` : ""}
                </div>
                <div className="text-[14px] font-medium text-fg mt-1 leading-relaxed">{evn.message}</div>
              </li>
            ))}
          </ol>
        </Card>
      </motion.div>
    </motion.div>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="text-muted">{k}</dt>
      <dd className={mono ? "font-mono text-[13px] text-right font-medium text-fg" : "text-right font-medium text-fg"}>{v}</dd>
    </div>
  );
}
