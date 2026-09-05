import { cn } from "@/lib/utils";

export function Input({ className, ...props }: React.ComponentProps<"input">) {
  return (
    <input
      className={cn(
        "h-10 w-full rounded-md bg-surface-2 px-3 text-[14px] font-medium text-fg shadow-[var(--shadow-subtle)] ring-1 ring-border/50 placeholder:text-subtle outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-1 focus-visible:ring-offset-surface-1 transition-all",
        className,
      )}
      {...props}
    />
  );
}
