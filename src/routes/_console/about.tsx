import { createFileRoute } from "@tanstack/react-router";
import { motion, Variants } from "framer-motion";
import { Card, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyBook, OpsBanner, OpsLoading } from "@/components/ops-state";
import { formatINR } from "@/lib/chargebackos";
import { resetDemoRequest } from "@/lib/ops-api";
import { useOverviewQuery } from "@/lib/ops-query";
import { useQueryClient } from "@tanstack/react-query";
import { useStaff } from "@/lib/ops-context";
import { useState } from "react";

export const Route = createFileRoute("/_console/about")({
  component: AboutPage,
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

function AboutPage() {
  const staff = useStaff();
  const [busy, setBusy] = useState(false);
  const [confirmReset, setConfirmReset] = useState(false);
  const book = useOverviewQuery();
  const queryClient = useQueryClient();
  const [note, setNote] = useState<string | null>(null);
  if (book.isLoading) return <OpsLoading />;
  if (book.error) return <OpsBanner error={book.error} />;
  const payload = book.data;
  if (!payload?.overview || !payload.evaluation) return <EmptyBook />;
  const ev = payload.evaluation;
  const cost = payload.costAssumptions;
  if (!cost) return <OpsBanner error={new Error("Stored cost assumptions are unavailable.")} />;
  const onReset = async () => {
    setNote(null);
    setBusy(true);
    try {
      await resetDemoRequest();
      await queryClient.invalidateQueries();
      setNote("Demo book re-seeded on the server.");
    } catch (e) {
      setNote(e instanceof Error ? e.message : "Reset requires the admin staff account.");
    } finally { setBusy(false); setConfirmReset(false); }
  };

  return (
    <motion.div variants={containerVariant} initial="hidden" animate="show" className="space-y-6">
      <motion.div variants={itemVariant}>
        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-accent">
          Razorpay AI Buildathon
        </p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight text-fg md:text-4xl">About ChargebackOS</h1>
        <p className="mt-3 max-w-3xl text-[15px] font-medium leading-relaxed text-muted">
          A defense-only AI risk manager for one loss class: merchant chargebacks and
          first-party / friendly-fraud disputes. The product triages, verifies evidence,
          and prepares a bounded representment draft — or routes the case to a human.
        </p>
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardTitle>Defense-only statement</CardTitle>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-[14px] font-medium text-muted">
            <li>No payment-card testing, fraud simulation, evasion, or impersonation tooling.</li>
            <li>No live money movement and no actual chargeback submission.</li>
            <li>No unconstrained chatbot. The language model may only summarize cited evidence.</li>
            <li>The policy engine outranks every model score and every generated sentence.</li>
            <li>Public demo uses synthetic data only. Nothing here is a production risk system.</li>
          </ul>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardTitle>Architecture in one paragraph</CardTitle>
          <p className="mt-3 text-[14px] font-medium leading-relaxed text-muted">
            ChargebackOS separates intelligence from authority. A calibrated tabular
            gradient-boosted model (trained on the 70% split, calibrated on
            validation, evaluated on a frozen 15% test set) triages dispute category and
            estimates fight-worthiness. An evidence service checks a reason-code-specific
            schema. A deterministic policy engine then decides whether a case may receive
            an automated draft, must go to human review, or should not be contested.
            Every prediction, evidence item, policy decision, action, and simulated
            outcome is on the case audit trail.
          </p>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant} className="grid gap-5 md:grid-cols-2">
        <Card>
          <CardTitle>Dataset</CardTitle>
          <ul className="mt-4 space-y-1.5 text-[14px] font-medium text-muted">
            <li><span className="font-mono text-[13px] text-fg tabular-nums">{payload.merchants.length}</span> synthetic merchants · 3 policy profiles</li>
            <li><span className="font-mono text-[13px] text-fg tabular-nums">{payload.overview.totalDisputes}</span> disputes · seed <span className="font-mono text-[13px] text-fg tabular-nums">{payload.seed}</span></li>
            <li>
              Split <span className="font-mono text-[13px] text-fg tabular-nums">{ev.nTrain} / {ev.nValid} / {ev.nTest}</span>{" "}
              (train / val / test), stratified by latent class
            </li>
            <li>No post-decision leakage: outcomes are never features</li>
            <li>Version {payload.datasetVersion ?? "unavailable"} · features {payload.featureVersion ?? "unavailable"}</li>
          </ul>
        </Card>
        <Card>
          <CardTitle>False-positive cost assumptions</CardTitle>
          <p className="mt-3 text-[14px] font-medium leading-relaxed text-muted">{cost.notes}</p>
          <ul className="mt-4 space-y-1.5 font-mono text-[13px] font-semibold tabular-nums text-muted">
            <li>Contest cost = <span className="text-fg">{formatINR(cost.contestCostFixed)}</span> + <span className="text-fg">{cost.contestCostVariable}</span> × amount</li>
            <li>FP penalty = <span className="text-fg">{formatINR(cost.fpPenaltyFixed)}</span> + <span className="text-fg">{cost.fpPenaltyVariable}</span> × amount</li>
            <li>EV = p(win)×amount − contest cost − (1−p(win))×FP penalty</li>
          </ul>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardTitle>Known limitations</CardTitle>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-[14px] font-medium text-muted">
            <li>
              The live model is scikit-learn HistGradientBoosting with calibration
              (not an XGBoost package). Alternative boosting libraries remain a later option. The website no longer scores cases in the browser.
            </li>
            <li>Latent labels are generated from the same feature families the model sees, plus noise. Real issuer data would be messier.</li>
            <li>Cost weights are synthetic INR assumptions, not a bank’s actual representment economics.</li>
            <li>Human-review quality is simulated (contest if EV is positive). Real reviewers are not oracles.</li>
            <li>Drafts use verified evidence paragraphs, with optional Grok arrangement; neither files a dispute.</li>
          </ul>
        </Card>
      </motion.div>

      <motion.div variants={itemVariant}>
        <Card>
          <CardTitle>What we are not building</CardTitle>
          <p className="mt-3 text-[14px] font-medium leading-relaxed text-muted">
            Not an all-fraud platform. Not an offense toolkit. Not a generic chatbot with
            tools. Not a claim that the synthetic model is production-ready.
          </p>
          <div className="mt-5">
            <Button disabled={busy || staff.role !== "admin"} variant="secondary" onClick={() => setConfirmReset(true)}>
              Re-seed demo book (admin)
            </Button>
            {confirmReset ? <div role="alert" className="mt-4 space-y-3 rounded-md border border-border p-4">
              <p>This permanently replaces the shared demonstration cases and their action history. Other staff will lose their current work. Staff accounts remain. This cannot be undone from the app.</p>
              <Button variant="danger" disabled={busy} onClick={() => void onReset()}>{busy ? "Replacing records…" : "Yes, replace the shared demo records"}</Button>
              <Button variant="ghost" disabled={busy} onClick={() => setConfirmReset(false)}>Cancel</Button>
            </div> : null}
            {note ? <p className="mt-3 text-[13px] font-medium text-muted">{note}</p> : null}
          </div>
        </Card>
      </motion.div>
    </motion.div>
  );
}
