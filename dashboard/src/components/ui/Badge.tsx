import { cn, titleCase } from "@/lib/utils";

const styles: Record<string, string> = {
  new: "bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-300",
  scored: "bg-violet-100 text-violet-800 dark:bg-violet-950 dark:text-violet-300",
  traced: "bg-cyan-100 text-cyan-800 dark:bg-cyan-950 dark:text-cyan-300",
  tax_delinquent: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
  tax_sale_scheduled: "bg-orange-100 text-orange-800 dark:bg-orange-950 dark:text-orange-300",
  pending: "bg-yellow-100 text-yellow-800 dark:bg-yellow-950 dark:text-yellow-300",
  approved: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
  default: "bg-[hsl(var(--surface-muted))] text-[hsl(var(--muted))]",
};

export function Badge({ label, className }: { label: string; className?: string }) {
  const key = label.toLowerCase();
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        styles[key] ?? styles.default,
        className,
      )}
    >
      {titleCase(label)}
    </span>
  );
}
