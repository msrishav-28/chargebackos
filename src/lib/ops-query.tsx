import { useQuery } from "@tanstack/react-query";
import {
  disputesRequest,
  disputeRequest,
  overviewRequest,
  policiesRequest,
} from "@/lib/ops-api";

export function useOverviewQuery() {
  return useQuery({ queryKey: ["overview"], queryFn: overviewRequest });
}

export function usePoliciesQuery() {
  return useQuery({ queryKey: ["policies"], queryFn: policiesRequest });
}

export function useDisputesQuery(params: Record<string, string | boolean | undefined>) {
  return useQuery({
    queryKey: ["disputes", params],
    queryFn: () => disputesRequest(params),
  });
}

export function useDisputeQuery(id: string) {
  return useQuery({
    queryKey: ["dispute", id],
    queryFn: () => disputeRequest(id),
    enabled: Boolean(id),
  });
}
