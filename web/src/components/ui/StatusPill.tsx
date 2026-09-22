import type { ReactNode } from "react";

type Tone = "neutral" | "success" | "primary" | "amber" | "danger" | "muted";

const tones: Record<Tone, string> = {
  neutral: "bg-slate-100 text-slate-700 border-slate-200",
  success: "bg-success-soft text-success border-green-200",
  primary: "bg-primary-soft text-primary border-blue-200",
  amber: "bg-amber-soft text-amber border-amber-200",
  danger: "bg-danger-soft text-danger border-red-200",
  muted: "bg-slate-50 text-muted border-border",
};

export function StatusPill({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
