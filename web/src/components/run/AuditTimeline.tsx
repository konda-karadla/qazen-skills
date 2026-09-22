import type { TimelineEvent } from "../../api/types";
import { formatWhen } from "../../api/client";
import { EmptyState } from "../ui/EmptyState";

export function AuditTimeline({ events }: { events: TimelineEvent[] }) {
  if (!events.length) {
    return <EmptyState title="No timeline events" description="Audit events will appear as the run progresses." />;
  }

  return (
    <ol className="relative space-y-0 border-l border-border ml-3">
      {events.map((ev, i) => (
        <li key={`${ev.at}-${ev.title}-${i}`} className="relative pb-4 pl-5">
          <span className="absolute -left-1.5 top-1.5 h-3 w-3 rounded-full border-2 border-primary bg-surface" />
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
            <time className="text-xs font-medium text-muted">{formatWhen(ev.at)}</time>
            {ev.stage ? (
              <span className="rounded bg-canvas px-1.5 py-0.5 text-[10px] font-semibold uppercase text-muted">
                {ev.stage}
              </span>
            ) : null}
            {ev.decision ? (
              <span className="text-[10px] font-semibold uppercase text-primary">{ev.decision}</span>
            ) : null}
          </div>
          <p className="mt-0.5 text-sm font-medium text-ink">{ev.title}</p>
          {(ev.actor || ev.detail || ev.artifact_version != null) && (
            <p className="mt-0.5 text-xs text-muted">
              {[
                ev.actor ? `by ${ev.actor}` : null,
                ev.artifact_version != null ? `v${ev.artifact_version}` : null,
                ev.detail,
              ]
                .filter(Boolean)
                .join(" · ")}
            </p>
          )}
        </li>
      ))}
    </ol>
  );
}
