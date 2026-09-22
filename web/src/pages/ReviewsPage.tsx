import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader, EmptyState } from "../components/ui/EmptyState";
import { ErrorBanner, LoadingSkeleton } from "../components/ui/AsyncState";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { StatusPill } from "../components/ui/StatusPill";
import { Table, THead, Th, Td } from "../components/ui/Table";
import { api, formatWhen, shortRunId } from "../api/client";
import type { PendingReviewItem, RecentReviewItem } from "../api/types";

export function ReviewsPage() {
  const [pending, setPending] = useState<PendingReviewItem[]>([]);
  const [recent, setRecent] = useState<RecentReviewItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [p, r] = await Promise.all([api.getPendingReviews(50), api.getRecentReviews(30)]);
        if (cancelled) return;
        setPending(p.reviews);
        setRecent(r.reviews);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load reviews");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return (
    <div>
      <PageHeader
        title="Reviews"
        description="Pending human gates H1–H5 and recent decisions."
      />
      {error ? <ErrorBanner message={error} onRetry={() => setReloadKey((k) => k + 1)} /> : null}
      {loading ? <LoadingSkeleton rows={3} label="Loading reviews…" /> : null}

      <Card
        title={`Pending (${pending.length})`}
        className="mb-4"
        action={
          pending.length > 0 ? (
            <StatusPill tone="amber">{pending.length} awaiting</StatusPill>
          ) : null
        }
      >
        {!loading && pending.length === 0 ? (
          <EmptyState
            title="No pending reviews"
            description="When a run reaches H1–H5, action-required items will appear here."
          />
        ) : pending.length > 0 ? (
          <Table>
            <THead>
              <tr>
                <Th>Gate</Th>
                <Th>Run</Th>
                <Th>Requirement</Th>
                <Th>Waiting since</Th>
                <Th>Version</Th>
                <Th>Actions</Th>
              </tr>
            </THead>
            <tbody className="divide-y divide-border">
              {pending.map((item) => (
                <tr key={item.review_id} className="hover:bg-canvas/80">
                  <Td>
                    <StatusPill tone="amber">{item.gate}</StatusPill>
                  </Td>
                  <Td className="font-mono text-xs" title={item.run_id}>
                    {shortRunId(item.run_id)}
                  </Td>
                  <Td className="max-w-xs truncate text-sm">
                    {item.requirement_summary || "—"}
                  </Td>
                  <Td className="text-xs text-muted">{formatWhen(item.waiting_since)}</Td>
                  <Td className="text-xs">{item.artifact_version ?? "—"}</Td>
                  <Td className="space-x-2">
                    <Link to={`/runs/${item.run_id}/review/${item.gate}`}>
                      <Button size="sm" variant="amber">
                        Open Review
                      </Button>
                    </Link>
                    <Link className="text-sm text-primary hover:underline" to={`/runs/${item.run_id}`}>
                      Run
                    </Link>
                  </Td>
                </tr>
              ))}
            </tbody>
          </Table>
        ) : null}
      </Card>

      <Card title="Recent decisions">
        {recent.length === 0 && !loading ? (
          <p className="text-sm text-muted">No completed review decisions yet.</p>
        ) : (
          <Table>
            <THead>
              <tr>
                <Th>Gate</Th>
                <Th>Decision</Th>
                <Th>Run</Th>
                <Th>Reviewer</Th>
                <Th>When</Th>
                <Th>Actions</Th>
              </tr>
            </THead>
            <tbody className="divide-y divide-border">
              {recent.map((item) => {
                const tone =
                  item.decision === "approved"
                    ? "success"
                    : item.decision === "rejected"
                      ? "danger"
                      : item.decision === "changes_requested"
                        ? "amber"
                        : "neutral";
                return (
                  <tr key={item.review_id} className="hover:bg-canvas/80">
                    <Td className="text-sm font-medium">{item.gate}</Td>
                    <Td>
                      <StatusPill tone={tone}>{item.decision}</StatusPill>
                    </Td>
                    <Td className="font-mono text-xs" title={item.run_id}>
                      {shortRunId(item.run_id)}
                    </Td>
                    <Td className="text-sm">{item.reviewer || "—"}</Td>
                    <Td className="text-xs text-muted">
                      {formatWhen(item.decided_at || item.created_at)}
                    </Td>
                    <Td>
                      <Link className="text-sm text-primary hover:underline" to={`/runs/${item.run_id}`}>
                        Open run
                      </Link>
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
