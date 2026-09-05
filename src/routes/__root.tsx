import { createRootRoute, HeadContent, Outlet, Scripts } from "@tanstack/react-router";
import { TooltipProvider } from "@/components/ui/tooltip";
import appCss from "../styles.css?url";

const APP_NAME = "ChargebackOS";

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: APP_NAME },
      {
        name: "description",
        content:
          "Defense-only AI chargeback triage: evidence verification, policy-gated representment drafts, and held-out evaluation with false-positive cost.",
      },
      { name: "theme-color", content: "#f7f9fc" },
    ],
    links: [
      { rel: "icon", type: "image/svg+xml", href: "/favicon.svg" },
      { rel: "stylesheet", href: appCss },
    ],
  }),
  component: () => (
    <html lang="en" className="antialiased" suppressHydrationWarning>
      <head>
        <HeadContent />
      </head>
      <body className="bg-bg text-fg selection:bg-accent/20 selection:text-accent">
        <TooltipProvider delay={200}>
          <Outlet />
        </TooltipProvider>
        <Scripts />
      </body>
    </html>
  ),
});
