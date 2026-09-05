import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import type { ApiCase } from "@/lib/ops-schemas";
import { processCaseRequest } from "@/lib/ops-api";
import { useStaff } from "@/lib/ops-context";
import { Button } from "./ui/button";
import { OpsBanner } from "./ops-state";

export function PendingCase({ data }: { data: ApiCase }) {
  const staff = useStaff();
  const client = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const step = data.state === "normalized" ? "triage" : data.state === "triaged" || (data.state === "human_review" && !data.evidencePackage) ? "assemble-evidence" : data.state === "human_review" && !data.prediction ? "triage" : data.state === "evidence_collecting" ? "evaluate-policy" : null;
  const process = async () => {
    if (!step) return;
    setBusy(true); setError(null);
    try { await processCaseRequest(data.id, step); }
    catch (err) { setError(err); }
    finally { await client.invalidateQueries(); setBusy(false); }
  };
  return <section className="space-y-4">
    <h1 className="text-2xl font-semibold">{data.id}</h1>
    <p>{data.merchantName} · {data.reasonLabel} · {data.state.replaceAll("_", " ")}</p>
    <p className="text-muted">This case has not completed scoring, evidence assembly and policy review. An unavailable result is never shown as a score or approval.</p>
    {data.policyDecision?.blockReasons.map((reason) => <p key={reason}>{reason.replaceAll("_", " ")}</p>)}
    {step && staff.role !== "viewer" ? <Button disabled={busy} onClick={() => void process()}>{busy ? "Processing…" : step.replaceAll("-", " ")}</Button> : null}
    {error ? <OpsBanner error={error} /> : null}
    <h2 className="font-semibold">Case history</h2>
    <ol className="space-y-2 text-sm">{data.timeline.map((event) => <li key={event.id}>{event.message}</li>)}</ol>
  </section>;
}
