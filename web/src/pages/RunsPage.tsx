import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { PageHeader, EmptyState } from "../components/ui/EmptyState";
import { ErrorBanner, LoadingSkeleton } from "../components/ui/AsyncState";
import { SearchInput } from "../components/ui/SearchInput";
import { Table, THead, Th, Td } from "../components/ui/Table";
import { StatusPill } from "../components/ui/StatusPill";
import { Button } from "../components/ui/Button";
import { api, formatWhen, shortRunId } from "../api/client";
import type { RunListItem } from "../api/types";
import { deriveRunUiState } from "../lib/runState";

const STATUS_FILTERS: { value: string; label: string }[] = [
  { value: "", label: "All" },
  { value: "running", label: "Running" },
  { value: "paused", label: "Paused" },
  { value: "completed", label: "Completed" },
  { value: "failed", label: "Failed" },
];

export function RunsPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);
  const hasLoadedRef = useRef(false);

  useEffect(() => {
    hasLoadedRef.current = false;
  }, [status]);

  useEffect(() => {
    let cancelled = false;
    const silent = hasLoadedRef.current;
    (async () => {
      if (!silent) {
        setLoading(true);
        setError(null);
      }
      try {
        const data = await api.listRuns({
          limit: 50,
          status: status || undefined,
        });
        if (!cancelled) {
          setRuns(data.runs);
          setTotal(data.total ?? data.runs.length);
          hasLoadedRef.current = true;
        }
      } catch (e) {
        if (!cancelled && !silent) setError(e instanceof Error ? e.message : "Failed to load runs");
      } finally {
        if (!cancelled && !silent) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [status, reloadKey]);

  const hasRunning = runs.some((r) => r.status === "running");

  useEffect(() => {
    if (!hasRunning) return;
    const id = window.setInterval(() => setReloadKey((k) => k + 1), 5000);
    return () => window.clearInterval(id);
  }, [hasRunning]);

  const filtered = runs.filter((r) => {
    if (!q.trim()) return true;
    const hay =
      `${r.run_id} ${r.requirement_id ?? ""} ${r.requirement_summary ?? ""} ${r.current_stage ?? ""}`.toLowerCase();
    return hay.includes(q.trim().toLowerCase());
  });

  return (
    <div>
      <PageHeader
        title="Runs"
        description="Searchable pipeline runs across environments."
        actions={
          <Link to="/runs/new">
            <Button>New Run</Button>
          </Link>
        }
      />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="max-w-sm flex-1">
          <SearchInput value={q} onChange={setQ} placeholder="Search runs…" />
        </div>
        <div className="flex flex-wrap gap-1.5">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f.value || "all"}
              type="button"
              onClick={() => setStatus(f.value)}
              className={`rounded-md border px-2.5 py-1.5 text-xs font-medium transition ${
                status === f.value
                  ? "border-primary bg-primary-soft text-primary"
                  : "border-border bg-surface text-muted hover:bg-canvas hover:text-ink"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>
      {!loading && !error ? (
        <p className="mb-2 text-xs text-muted">
          Showing {filtered.length}
          {total ? ` of ${total}` : ""} run{total === 1 ? "" : "s"}
        </p>
      ) : null}
      {error ? <ErrorBanner message={error} onRetry={() => setReloadKey((k) => k + 1)} /> : null}
      {loading ? (
        <LoadingSkeleton rows={5} label="Loading runs…" />
      ) : filtered.length === 0 ? (
        <EmptyState
          title="No runs yet"
          description="Start a QA run to populate this list."
          actionLabel="New Run"
          onAction={() => navigate("/runs/new")}
        />
      ) : (
        <Table>
          <THead>
            <tr>
              <Th>Run ID</Th>
              <Th>Requirement</Th>
              <Th>Status</Th>
              <Th>Current Stage</Th>
              <Th>Human Gate</Th>
              <Th>Started</Th>
              <Th>Actions</Th>
            </tr>
          </THead>
          <tbody className="divide-y divide-border">
            {filtered.map((r) => {
              const ui = deriveRunUiState({
                status: r.status,
                current_stage: r.current_stage,
                pending_gate: r.pending_gate,
              });
              const tone =
                ui.listStatusPill.key === "awaiting_review"
                  ? "amber"
                  : ui.listStatusPill.key === "completed"
                    ? "success"
                    : ui.listStatusPill.key === "rejected" || ui.listStatusPill.key === "failed"
                      ? "danger"
                      : "primary";
              return (
                <tr key={r.run_id} className="hover:bg-canvas/80">
                  <Td className="font-mono text-xs" title={r.run_id}>
                    {shortRunId(r.run_id)}
                  </Td>
                  <Td className="max-w-xs truncate text-sm">
                    {r.requirement_summary || r.requirement_id || "—"}
                  </Td>
                  <Td>
                    <StatusPill tone={tone}>{ui.listStatusPill.label}</StatusPill>
                  </Td>
                  <Td className="text-xs">{ui.currentLabel}</Td>
                  <Td>{r.pending_gate ?? "—"}</Td>
                  <Td className="text-xs text-muted">{formatWhen(r.created_at)}</Td>
                  <Td className="space-x-2">
                    <Link className="text-sm text-primary hover:underline" to={`/runs/${r.run_id}`}>
                      Open
                    </Link>
                    {ui.primaryCta === "open_review" && ui.actionGate ? (
                      <Link
                        className="text-sm text-amber hover:underline"
                        to={`/runs/${r.run_id}/review/${ui.actionGate}`}
                      >
                        Review
                      </Link>
                    ) : null}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </Table>
      )}
    </div>
  );
}
