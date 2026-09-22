import type { ReactNode } from "react";
import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { Button } from "./Button";

/** Inline or block loading indicator used on every data page. */
export function LoadingBlock({
  label = "Loading…",
  className = "",
}: {
  label?: string;
  className?: string;
}) {
  return (
    <div
      className={`flex items-center gap-2 text-sm text-muted ${className}`}
      role="status"
      aria-live="polite"
    >
      <Loader2 className="h-4 w-4 shrink-0 animate-spin text-primary" aria-hidden />
      <span>{label}</span>
    </div>
  );
}

/** Full-width skeleton placeholders while a page boots. */
export function LoadingSkeleton({
  rows = 3,
  label,
}: {
  rows?: number;
  label?: string;
}) {
  return (
    <div className="space-y-3" role="status" aria-live="polite" aria-label={label || "Loading"}>
      {label ? <LoadingBlock label={label} className="mb-1" /> : null}
      {Array.from({ length: rows }).map((_, i) => (
        <div
          key={i}
          className="h-10 animate-pulse rounded-md bg-slate-100"
          style={{ animationDelay: `${i * 80}ms` }}
        />
      ))}
    </div>
  );
}

/** Consistent error banner with optional retry. */
export function ErrorBanner({
  message,
  onRetry,
  className = "",
}: {
  message: string;
  onRetry?: () => void;
  className?: string;
}) {
  return (
    <div
      className={`mb-3 flex flex-wrap items-start gap-3 rounded-md border border-red-200 bg-danger-soft px-3 py-2.5 text-sm text-danger ${className}`}
      role="alert"
    >
      <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
      <p className="min-w-0 flex-1">{message}</p>
      {onRetry ? (
        <Button variant="secondary" size="sm" onClick={onRetry} className="shrink-0">
          <RefreshCw className="h-3.5 w-3.5" aria-hidden />
          Retry
        </Button>
      ) : null}
    </div>
  );
}

/** Wrap page content for a light enter transition. */
export function PageFrame({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`page-enter ${className}`}>{children}</div>;
}
