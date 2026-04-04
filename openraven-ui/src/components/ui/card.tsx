import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
}

export function Card({ className, elevated, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "bg-[var(--bg-surface)] p-6",
        className
      )}
      style={{ boxShadow: elevated ? "var(--shadow-golden)" : "var(--shadow-card)" }}
      {...props}
    />
  );
}
