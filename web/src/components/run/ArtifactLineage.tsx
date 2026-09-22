import type { LineageNode } from "../../api/types";
import { EmptyState } from "../ui/EmptyState";

export function ArtifactLineage({ nodes }: { nodes: LineageNode[] }) {
  if (!nodes.length) {
    return <EmptyState title="No lineage yet" description="Artifacts will appear as stages complete." />;
  }

  return (
    <ol className="flex flex-wrap items-center gap-2">
      {nodes.map((node, i) => (
        <li key={`${node.node_id}-${node.version ?? i}`} className="flex items-center gap-2">
          <div className="rounded-md border border-border bg-surface px-3 py-2 text-center shadow-sm">
            <p className="text-xs font-semibold text-ink">{node.label}</p>
            <p className="text-[10px] text-muted">
              {node.version != null ? `v${node.version}` : "—"} · {node.status}
            </p>
          </div>
          {i < nodes.length - 1 ? <span className="text-muted">→</span> : null}
        </li>
      ))}
    </ol>
  );
}
