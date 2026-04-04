import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center text-xs font-normal",
  {
    variants: {
      variant: {
        default: "bg-[var(--bg-surface-warm)] text-[var(--color-text)] px-2 py-0.5",
        citation: "bg-[var(--bg-surface-hover)] border border-[var(--color-brand-amber)] text-[var(--color-text)] px-1.5 py-0.5",
        status: "px-2 py-0.5",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant, className }))} {...props} />;
}
