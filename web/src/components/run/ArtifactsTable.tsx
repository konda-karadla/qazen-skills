import { useMemo, useState } from "react";
import type { ArtifactListItem } from "../../api/types";
import { formatWhen } from "../../api/client";
import { SearchInput } from "../ui/SearchInput";
import { StatusPill } from "../ui/StatusPill";
import { Table, THead, Th, Td } from "../ui/Table";
import { EmptyState } from "../ui/EmptyState";
import { Button } from "../ui/Button";

function statusTone(status: string): "success" | "primary" | "amber" | "danger" | "muted" {
  const s = status.toLowerCase();
  if (s === "approved" || s === "completed") return "success";
  if (s === "pending") return "amber";
  if (s === "failed") return "danger";
  return "muted";
}

export function ArtifactsTable({
  artifacts,
  stageFilter,
  onStageFilterChange,
  onView,
}: {
  artifacts: ArtifactListItem[];
  stageFilter: string;
  onStageFilterChange: (stage: string) => void;
  onView: (artifact: ArtifactListItem) => void;
}) {
  const [q, setQ] = useState("");
  const stages = useMemo(() => {
    const set = new Set(artifacts.map((a) => String(a.stage)));
    return ["All", ...Array.from(set)];
  }, [artifacts]);

  const filtered = artifacts.filter((a) => {
    if (stageFilter !== "All" && String(a.stage) !== stageFilter) return false;
    if (!q.trim()) return true;
    const hay = `${a.name} ${a.type} ${a.stage}`.toLowerCase();
    return hay.includes(q.trim().toLowerCase());
  });

  return (
    <div>
      <div className="mb-3 flex flex-wrap items-center gap-2">
        <label className="text-sm text-muted">
          Stage{" "}
          <select
            className="ml-1 rounded-md border border-border bg-surface px-2 py-1.5 text-sm text-ink"
            value={stageFilter}
            onChange={(e) => onStageFilterChange(e.target.value)}
          >
            {stages.map((s) => (
              <option key={s} value={s}>
                {s === "All" ? "All Stages" : s}
              </option>
            ))}
          </select>
        </label>
        <SearchInput className="max-w-xs flex-1" value={q} onChange={setQ} placeholder="Search artifacts…" />
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="No artifacts available" description="No artifacts match the current filters." />
      ) : (
        <Table>
          <THead>
            <tr>
              <Th>Stage</Th>
              <Th>Artifact Type</Th>
              <Th>Name</Th>
              <Th>Version</Th>
              <Th>Status</Th>
              <Th>Created At</Th>
              <Th>Actions</Th>
            </tr>
          </THead>
          <tbody className="divide-y divide-border">
            {filtered.map((a) => (
              <tr key={a.artifact_id} className="hover:bg-canvas/80">
                <Td>
                  <StatusPill tone="neutral">{a.stage}</StatusPill>
                </Td>
                <Td className="text-muted">{a.type}</Td>
                <Td className="font-mono text-xs">{a.name}</Td>
                <Td>v{a.version}</Td>
                <Td>
                  <StatusPill tone={statusTone(a.status)}>{a.status}</StatusPill>
                </Td>
                <Td className="text-xs text-muted">{formatWhen(a.created_at)}</Td>
                <Td>
                  <Button variant="ghost" size="sm" onClick={() => onView(a)}>
                    View
                  </Button>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}
    </div>
  );
}
