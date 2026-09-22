import type { ReactNode } from "react";

export interface TabItem {
  id: string;
  label: string;
  count?: number;
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: TabItem[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1 border-b border-border" role="tablist">
      {tabs.map((tab) => {
        const isActive = tab.id === active;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={() => onChange(tab.id)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition ${
              isActive
                ? "border-primary text-primary"
                : "border-transparent text-muted hover:text-ink"
            }`}
          >
            {tab.label}
            {typeof tab.count === "number" ? (
              <span className="ml-1.5 text-xs text-muted">({tab.count})</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

export function TabPanel({
  active,
  id,
  children,
}: {
  active: string;
  id: string;
  children: ReactNode;
}) {
  if (active !== id) return null;
  return (
    <div role="tabpanel" className="pt-4">
      {children}
    </div>
  );
}
