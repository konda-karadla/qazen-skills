import type { ReactNode } from "react";

export function Table({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <div className={`overflow-x-auto rounded-lg border border-border bg-surface ${className}`}>
      <table className="min-w-full divide-y divide-border text-left text-sm">{children}</table>
    </div>
  );
}

export function THead({ children }: { children: ReactNode }) {
  return <thead className="bg-canvas text-xs font-semibold uppercase tracking-wide text-muted">{children}</thead>;
}

export function Th({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <th className={`px-3 py-2.5 font-semibold ${className}`}>{children}</th>;
}

export function Td({
  children,
  className = "",
  colSpan,
  title,
}: {
  children: ReactNode;
  className?: string;
  colSpan?: number;
  title?: string;
}) {
  return (
    <td colSpan={colSpan} title={title} className={`px-3 py-2.5 text-ink ${className}`}>
      {children}
    </td>
  );
}
