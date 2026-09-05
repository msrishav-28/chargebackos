import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium tracking-wide",
  {
    variants: {
      tone: {
        neutral: "bg-surface-3 text-muted ring-1 ring-border/30",
        accent: "bg-accent/15 text-accent ring-1 ring-accent/20",
        ok: "bg-ok/15 text-ok ring-1 ring-ok/20",
        warn: "bg-warn/15 text-warn ring-1 ring-warn/20",
        danger: "bg-danger/15 text-danger ring-1 ring-danger/20",
        info: "bg-info/15 text-info ring-1 ring-info/20",
      },
    },
    defaultVariants: { tone: "neutral" },
  },
);

export function Badge({
  className,
  tone,
  ...props
}: React.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
