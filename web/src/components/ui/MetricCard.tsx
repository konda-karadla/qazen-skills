import type { ReactNode } from "react";

export function MetricCard({
  label,
  value,
  hint,
  tone = "neutral",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  tone?: "neutral" | "success" | "primary" | "amber" | "danger";
}) {
  const valueColor =
    tone === "success"
      ? "text-success"
      : tone === "primary"
        ? "text-primary"
        : tone === "amber"
          ? "text-amber"
          : tone === "danger"
            ? "text-danger"
            : "text-ink";

  return (
    <div className="rounded-lg border border-border bg-surface p-4 shadow-sm transition duration-150 hover:border-slate-300 hover:shadow">
      <p className="text-xs font-medium uppercase tracking-wide text-muted">{label}</p>
      <p className={`mt-2 text-2xl font-semibold tabular-nums ${valueColor}`}>{value}</p>
      {hint ? <p className="mt-1 text-xs text-muted">{hint}</p> : null}
    </div>
  );
}
