import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/ui/EmptyState";
import { ErrorBanner, LoadingSkeleton } from "../components/ui/AsyncState";
import { MetricCard } from "../components/ui/MetricCard";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { StatusPill } from "../components/ui/StatusPill";
import { Table, THead, Th, Td } from "../components/ui/Table";
import { api, formatWhen, shortRunId } from "../api/client";
import type {
  DashboardSummary,
  IntegrationsStatus,
  PendingReviewItem,
  RunListItem,
} from "../api/types";
import { deriveRunUiState } from "../lib/runState";

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [pending, setPending] = useState<PendingReviewItem[]>([]);
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [integrations, setIntegrations] = useState<IntegrationsStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [s, p, r, i] = await Promise.all([
          api.getDashboardSummary(),
          api.getPendingReviews(10),
          api.listRuns({ limit: 8 }),
          api.getIntegrationsStatus(),
        ]);
        if (cancelled) return;
        setSummary(s);
        setPending(p.reviews);
        setRuns(r.runs);
        setIntegrations(i);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load dashboard");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const ciTone =
    integrations?.ci.label === "Connected"
      ? "success"
      : integrations?.ci.label === "Configured"
        ? "primary"
        : "muted";

  return (
    <div>
      <PageHeader
        title="QA Automation Overview"
        description="Executive and engineering view of runs, reviews, and execution health."
        actions={
          <Link to="/runs/new">
            <Button>New Run</Button>
          </Link>
        }
      />

      {error ? <ErrorBanner message={error} onRetry={() => setReloadKey((k) => k + 1)} /> : null}
      {loading && !summary ? <LoadingSkeleton rows={2} label="Loading dashboard…" /> : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        <MetricCard
          label="Active Runs"
          value={summary?.active_runs ?? "—"}
          tone="primary"
          hint="Running + paused"
        />
        <MetricCard
          label="Pending Reviews"
          value={summary?.pending_reviews ?? "—"}
          tone="amber"
          hint="H1–H5 gates awaiting decision"
        />
        <MetricCard label="Tests Executed" value={summary?.tests_executed ?? "—"} />
        <MetricCard
          label="Pass Rate"
          value={summary?.pass_rate_display ?? "—"}
          hint={summary?.pass_rate_basis ?? "Based on classified executable results"}
          tone="success"
        />
        <MetricCard label="Failed Tests" value={summary?.failed_tests ?? "—"} tone="danger" />
        <MetricCard
          label="Runs Completed"
          value={summary?.runs_completed ?? "—"}
          tone="success"
        />
      </div>
      {summary?.pass_rate_note ? (
        <p className="mt-2 text-xs text-muted" title={summary.pass_rate_note}>
          {summary.pass_rate_note}
        </p>
      ) : null}

      <div className="mt-6 grid gap-4 xl:grid-cols-3">
        <Card
          className="xl:col-span-2"
          title="Pending Your Review"
          action={
            <Link to="/reviews">
              <Button variant="ghost" size="sm">
                View all
              </Button>
            </Link>
          }
        >
          {pending.length === 0 ? (
            <EmptyPending />
          ) : (
            <ul className="divide-y divide-border">
              {pending.map((item) => (
                <li key={item.review_id} className="flex flex-wrap items-center justify-between gap-3 py-3 first:pt-0 last:pb-0">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-ink">
                      {item.gate} · {shortRunId(item.run_id)}
                    </p>
                    <p className="truncate text-xs text-muted">
                      {item.requirement_summary || "No requirement summary"}
                    </p>
                    <p className="mt-0.5 text-xs text-muted">Waiting since {formatWhen(item.waiting_since)}</p>
                  </div>
                  <Link to={`/runs/${item.run_id}/review/${item.gate}`}>
                    <Button size="sm" variant="amber">
                      Open Review
                    </Button>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="CI/CD Gate Status">
          <div className="space-y-2 text-sm">
            <div className="flex items-center justify-between">
              <span className="text-muted">Connection</span>
              <StatusPill tone={ciTone}>{integrations?.ci.label ?? "—"}</StatusPill>
            </div>
            <p className="text-xs text-muted">
              {integrations?.ci.detail ??
                "Production Jenkins is not connected. Gate can operate in mock mode."}
            </p>
            {integrations?.ci.mode ? (
              <p className="text-xs text-muted">Mode: {integrations.ci.mode}</p>
            ) : null}
          </div>
        </Card>
      </div>

      <Card
        className="mt-4"
        title="Recent Runs"
        action={
          <Link to="/runs">
            <Button variant="ghost" size="sm">
              View all
            </Button>
          </Link>
        }
      >
        {runs.length === 0 ? (
          <p className="text-sm text-muted">No runs yet. Start a QA run to populate this list.</p>
        ) : (
          <Table>
            <THead>
              <tr>
                <Th>Run ID</Th>
                <Th>Requirement</Th>
                <Th>Current Stage</Th>
                <Th>Status</Th>
                <Th>Created</Th>
                <Th>Actions</Th>
              </tr>
            </THead>
            <tbody className="divide-y divide-border">
              {runs.map((r) => {
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
                  <tr key={r.run_id} className="transition-colors hover:bg-canvas/80">
                    <Td className="font-mono text-xs" title={r.run_id}>
                      {shortRunId(r.run_id)}
                    </Td>
                    <Td className="max-w-xs truncate text-sm">
                      {r.requirement_summary || r.requirement_id || "—"}
                    </Td>
                    <Td className="text-xs">{ui.currentLabel}</Td>
                    <Td>
                      <StatusPill tone={tone}>{ui.listStatusPill.label}</StatusPill>
                    </Td>
                    <Td className="text-xs text-muted">{formatWhen(r.created_at)}</Td>
                    <Td>
                      <Link className="text-sm text-primary hover:underline" to={`/runs/${r.run_id}`}>
                        Open
                      </Link>
                      {ui.primaryCta === "open_review" && ui.actionGate ? (
                        <>
                          {" · "}
                          <Link
                            className="text-sm text-amber hover:underline"
                            to={`/runs/${r.run_id}/review/${ui.actionGate}`}
                          >
                            Review
                          </Link>
                        </>
                      ) : null}
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>
        )}
      </Card>
    </div>
  );
}

function EmptyPending() {
  return (
    <div className="rounded-md border border-dashed border-amber-200 bg-amber-soft px-4 py-8 text-center transition hover:border-amber-300">
      <p className="text-sm font-medium text-ink">No pending reviews</p>
      <p className="mt-1 text-xs text-muted">
        When a run reaches H1–H5, action-required items will appear here.
      </p>
    </div>
  );
}
