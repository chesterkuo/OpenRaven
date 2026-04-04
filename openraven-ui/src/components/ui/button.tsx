import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center text-base font-normal transition-colors disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-[var(--color-dark)] text-[var(--color-text-on-brand)] hover:bg-[#333333]",
        secondary: "bg-[var(--bg-surface-warm)] text-[var(--color-text)] hover:bg-[var(--bg-surface-hover)]",
        ghost: "text-[var(--color-text)] opacity-60 hover:opacity-100",
        destructive: "bg-[var(--color-error)] text-[var(--color-text-on-brand)] hover:bg-red-700",
      },
      size: {
        default: "px-3 py-1.5 text-sm",
        lg: "px-5 py-2.5 text-base",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}
