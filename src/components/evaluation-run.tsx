import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { evaluationStatusRequest, runEvaluationRequest } from "@/lib/ops-api";
import { useStaff } from "@/lib/ops-context";
import { Button } from "./ui/button";
import { OpsBanner } from "./ops-state";

export function EvaluationRun() {
  const staff = useStaff();
  const client = useQueryClient();
  const [id, setId] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const run = useQuery({ queryKey: ["evaluation-run", id], enabled: id !== null,
    queryFn: () => { if (!id) throw new Error("No evaluation selected"); return evaluationStatusRequest(id); },
    refetchInterval: (query) => ["completed", "failed"].includes(query.state.data?.state ?? "") ? false : 3000,
  });
  useEffect(() => {
    if (run.data?.state === "completed") void client.invalidateQueries({ queryKey: ["overview"] });
  }, [run.data?.state, client]);
  const start = async () => {
    setPending(true); setError(null);
    try { const result = await runEvaluationRequest(crypto.randomUUID()); setId(result.batchRunId); }
    catch (err) { setError(err); }
    finally { setPending(false); }
  };
  const running = id !== null && !["completed", "failed"].includes(run.data?.state ?? "");
  if (staff.role !== "admin") return null;
  return <div className="space-y-3">
    <Button variant="secondary" disabled={pending || running} onClick={() => void start()}>{pending || running ? "Evaluation running…" : "Run frozen evaluation"}</Button>
    {id ? <p role="status" className="break-all text-sm text-muted">Run {id}: {run.data?.state ?? "checking"}. {run.data?.summary.error}</p> : null}
    {error || run.error ? <OpsBanner error={error || run.error} onRetry={run.error ? () => void run.refetch() : undefined} /> : null}
  </div>;
}
