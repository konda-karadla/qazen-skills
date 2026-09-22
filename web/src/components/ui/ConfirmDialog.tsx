import { Button } from "./Button";

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  confirmVariant = "primary",
  busy,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  confirmVariant?: "primary" | "approve" | "amber" | "danger";
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        className="w-full max-w-md rounded-lg border border-border bg-surface p-5 shadow-xl"
      >
        <h3 id="confirm-title" className="text-base font-semibold text-ink">
          {title}
        </h3>
        <p className="mt-2 text-sm text-muted whitespace-pre-wrap">{message}</p>
        <div className="mt-5 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
          <Button variant={confirmVariant} onClick={onConfirm} disabled={busy}>
            {busy ? "Submitting…" : confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}
