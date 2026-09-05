import { cva, type VariantProps } from "class-variance-authority";
import * as React from "react";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] disabled:pointer-events-none disabled:opacity-40 [&_svg]:size-4 [&_svg]:shrink-0 active:scale-[0.96]",
  {
    variants: {
      variant: {
        default:
          "bg-accent text-accent-fg shadow-[0_2px_4px_rgba(17,26,74,0.1),inset_0_1px_0_rgba(255,255,255,0.2)] hover:bg-accent/90 hover:shadow-[0_4px_8px_rgba(17,26,74,0.15),inset_0_1px_0_rgba(255,255,255,0.2)]",
        secondary:
          "bg-surface-2 text-fg shadow-[var(--shadow-subtle)] ring-1 ring-border/50 hover:bg-surface-3 hover:shadow-[var(--shadow-md)]",
        outline:
          "bg-transparent text-fg ring-1 ring-border/50 shadow-sm hover:bg-surface-2",
        ghost: "bg-transparent text-muted hover:bg-surface-2 hover:text-fg",
        danger: "bg-danger text-white shadow-sm hover:bg-danger/90",
        link: "text-accent underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4",
        sm: "h-8 px-3 text-xs",
        lg: "h-12 px-6",
        icon: "size-10",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

export function Button({
  className,
  variant,
  size,
  ...props
}: React.ComponentProps<"button"> & VariantProps<typeof buttonVariants>) {
  return (
    <button className={cn(buttonVariants({ variant, size, className }))} {...props} />
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export { buttonVariants };
