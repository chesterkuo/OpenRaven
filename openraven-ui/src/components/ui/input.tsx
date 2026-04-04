import { cn } from "@/lib/utils";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export function Input({ className, ...props }: InputProps) {
  return (
    <input
      className={cn(
        "bg-[var(--bg-surface)] border border-[var(--color-border)] px-3 py-2.5 text-base text-[var(--color-text)] placeholder:text-[var(--color-text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--color-brand)]",
        className
      )}
      {...props}
    />
  );
}
