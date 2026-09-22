import { Bot, Cog, UserRound, Check, Circle } from "lucide-react";
import type { PipelineNodeUi } from "../../lib/runState";

export function PipelineTimeline({
  nodes,
  onSelect,
  selectedId,
  pulseCurrent = false,
}: {
  nodes: PipelineNodeUi[];
  onSelect?: (id: string) => void;
  selectedId?: string | null;
  pulseCurrent?: boolean;
}) {
  return (
    <div className="overflow-x-auto pb-2">
      <ol className="flex min-w-max items-start gap-0">
        {nodes.map((node, i) => {
          const Icon =
            node.kind === "human" ? UserRound : node.kind === "deterministic" ? Cog : Bot;
          const isLast = i === nodes.length - 1;
          const done = node.state === "completed" || node.state === "approved";
          const current = node.state === "current";
          const failed = node.state === "failed";
          const selected = selectedId === node.id;

          const circleCls = failed
            ? "bg-danger text-white border-danger"
            : current && node.kind === "human"
              ? "bg-amber text-white border-amber"
              : current
                ? "bg-primary text-white border-primary"
                : done
                  ? "bg-success text-white border-success"
                  : "bg-white text-muted border-border";

          const lineCls = done ? "bg-success" : "bg-border";

          return (
            <li key={node.id} className="flex items-start">
              <button
                type="button"
                onClick={() => onSelect?.(node.id)}
                className={`flex w-[4.5rem] flex-col items-center text-center rounded-md p-0.5 transition duration-150 ${
                  selected ? "ring-2 ring-primary/40 bg-primary-soft/40" : "hover:bg-canvas"
                }`}
                title={node.label}
              >
                <span
                  className={`flex h-8 w-8 items-center justify-center rounded-full border-2 transition ${circleCls} ${
                    current ? "scale-110 shadow-sm" : ""
                  } ${current && pulseCurrent && node.kind !== "human" ? "animate-pulse" : ""}`}
                >
                  {done ? (
                    <Check className="h-4 w-4" />
                  ) : failed ? (
                    <Circle className="h-3 w-3 fill-current" />
                  ) : (
                    <Icon className="h-3.5 w-3.5" />
                  )}
                </span>
                <span className="mt-1.5 text-[10px] font-semibold text-ink">{node.id}</span>
                <span className="text-[9px] leading-tight text-muted">{node.shortLabel}</span>
              </button>
              {!isLast ? <div className={`mt-4 h-0.5 w-3 shrink-0 ${lineCls}`} /> : null}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
