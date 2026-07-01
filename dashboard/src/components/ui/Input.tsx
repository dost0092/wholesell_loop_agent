import { Search } from "lucide-react";
import { cn } from "@/lib/utils";
import type { InputHTMLAttributes } from "react";

export function Input({
  className,
  icon,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { icon?: boolean }) {
  return (
    <div className="relative">
      {icon && (
        <Search
          className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--muted))]"
          aria-hidden
        />
      )}
      <input
        className={cn(
          "h-10 w-full rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] px-3 text-sm transition-colors placeholder:text-[hsl(var(--muted))] focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20",
          icon && "pl-9",
          className,
        )}
        {...props}
      />
    </div>
  );
}

export function Select({
  className,
  children,
  ...props
}: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      className={cn(
        "h-10 rounded-xl border border-[hsl(var(--border))] bg-[hsl(var(--surface-elevated))] px-3 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20",
        className,
      )}
      {...props}
    >
      {children}
    </select>
  );
}
