import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "framer-motion";
import { useState, type ReactNode } from "react";
import { OpsApiError } from "@/lib/ops-api";
import { StaffContext } from "@/lib/ops-context";
import type { StaffUser } from "@/lib/ops-schemas";

export function OpsProvider({ children, staff }: { children: ReactNode; staff: StaffUser }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: { queries: {
      staleTime: 15_000,
      retry: (count, err) => err instanceof OpsApiError && err.waking && count < 2,
    } },
  }));
  return <StaffContext.Provider value={staff}>
    <QueryClientProvider client={client}>
      <MotionConfig reducedMotion="user">{children}</MotionConfig>
    </QueryClientProvider>
  </StaffContext.Provider>;
}
