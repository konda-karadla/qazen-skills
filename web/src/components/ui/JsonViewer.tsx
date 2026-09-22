import { Button } from "../ui/Button";

export function JsonViewer({
  title,
  value,
  onClose,
}: {
  title: string;
  value: unknown;
  onClose: () => void;
}) {
  const text = typeof value === "string" ? value : JSON.stringify(value, null, 2);
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
      <div className="flex max-h-[85vh] w-full max-w-3xl flex-col rounded-lg border border-border bg-surface shadow-xl">
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <h3 className="text-sm font-semibold text-ink">{title}</h3>
          <Button variant="ghost" size="sm" onClick={onClose}>
            Close
          </Button>
        </header>
        <pre className="overflow-auto bg-slate-950 p-4 font-mono text-xs leading-relaxed text-slate-100">
          {text}
        </pre>
      </div>
    </div>
  );
}
