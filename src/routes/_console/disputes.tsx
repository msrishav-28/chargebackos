import { createFileRoute, Outlet } from "@tanstack/react-router";
import { validateQueueSearch } from "@/lib/queue-search";

export const Route = createFileRoute("/_console/disputes")({
  component: () => <Outlet />,
  validateSearch: validateQueueSearch,
});
