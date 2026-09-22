import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  api,
  ApiError,
  loadReviewer,
  saveReviewer,
  shortRunId,
} from "../api/client";
import type { ReviewEvidenceResponse } from "../api/types";
import { Card } from "../components/ui/Card";
import { StatusPill } from "../components/ui/StatusPill";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorBanner, LoadingBlock } from "../components/ui/AsyncState";
import { Button } from "../components/ui/Button";
import {
  ReviewDecisionPanel,
  type ReviewDecision,
} from "../components/review/ReviewDecisionPanel";
import {
  H1Evidence,
  H2Evidence,
  H3Evidence,
  H4Evidence,
  H5Evidence,
} from "../components/review/GateEvidence";

const GATE_TITLES: Record<string, string> = {
  H1: "H1 — Requirement Review",
  H2: "H2 — Test Case Review",
  H3: "H3 — Script Review",
  H4: "H4 — Execution & Stability Review",
  H5: "H5 — Release Review / Go-No-Go",
};

function EvidenceForGate({
  gate,
  evidence,
}: {
  gate: string;
  evidence: Record<string, unknown>;
}) {
  switch (gate) {
    case "H1":
      return <H1Evidence evidence={evidence} />;
    case "H2":
      return <H2Evidence evidence={evidence} />;
    case "H3":
      return <H3Evidence evidence={evidence} />;
    case "H4":
      return <H4Evidence evidence={evidence} />;
    case "H5":
      return <H5Evidence evidence={evidence} />;
    default:
      return (
        <pre className="overflow-auto rounded-md bg-canvas p-3 font-mono text-xs">
          {JSON.stringify(evidence, null, 2)}
        </pre>
      );
  }
}

export function ReviewWorkspacePage() {
  const { runId = "", gate: gateParam = "" } = useParams();
  const navigate = useNavigate();
  const gate = gateParam.toUpperCase();

  const [review, setReview] = useState<ReviewEvidenceResponse | null>(null);
  const [requirement, setRequirement] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [reviewer, setReviewer] = useState(loadReviewer);
  const [comment, setComment] = useState("");
  const [polling, setPolling] = useState(false);

  const load = useCallback(async () => {
    if (!runId) return;
    setError(null);
    try {
      const [rev, detail] = await Promise.all([api.getReview(runId), api.getRun(runId)]);
      setReview(rev);
      setRequirement(detail.requirement_summary ?? null);

      // Sync mid-flight UI with server truth (Refresh was leaving "revising…" stuck).
      const stage = rev.current_stage ?? "";
      const inFlight =
        stage.endsWith("_revising") ||
        rev.run_status === "running" ||
        (detail.status === "running" && !rev.pending_gate);
      if (rev.pending_gate || rev.run_status === "failed" || rev.run_status === "completed") {
        setPolling(false);
        if (rev.pending_gate) {
          setStatusMsg((prev) =>
            prev && /revising|continuing/i.test(prev) ? null : prev,
          );
        }
      } else if (!inFlight) {
        setPolling(false);
      }
      return rev;
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load review");
      return null;
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    setLoading(true);
    void load();
  }, [load]);

  // Poll while revising / running after request-changes or approve mid-flight
  useEffect(() => {
    if (!polling || !runId) return;
    const id = window.setInterval(async () => {
      const rev = await load();
      if (!rev) return;
      const stage = rev.current_stage ?? "";
      if (rev.pending_gate && rev.pending_gate !== gate) {
        navigate(`/runs/${runId}/review/${rev.pending_gate}`, { replace: true });
      } else if (
        !rev.pending_gate &&
        (rev.run_status === "completed" || rev.run_status === "failed") &&
        !stage.endsWith("_pending") &&
        !stage.endsWith("_revising")
      ) {
        setStatusMsg("No pending gate — returning to run detail.");
        window.setTimeout(() => navigate(`/runs/${runId}`), 1200);
      }
    }, 2000);
    return () => window.clearInterval(id);
  }, [polling, runId, gate, load, navigate]);

  async function onSubmit(decision: ReviewDecision) {
    if (!runId || !reviewer.trim()) return;
    saveReviewer(reviewer.trim());
    setBusy(true);
    setError(null);
    setStatusMsg(null);
    const body = { reviewer: reviewer.trim(), comment: comment.trim() || undefined };
    try {
      if (decision === "approve") {
        await api.approve(runId, body);
        setStatusMsg("Approved — pipeline continuing…");
        setPolling(true);
        await load();
      } else if (decision === "request-changes") {
        await api.requestChanges(runId, body);
        setStatusMsg("Changes requested — revising prior phase, then this gate will reopen…");
        setComment("");
        setPolling(true);
        await load();
      } else {
        await api.reject(runId, body);
        setStatusMsg("Rejected — run stopped.");
        await load();
        window.setTimeout(() => navigate(`/runs/${runId}`), 1500);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Decision failed");
    } finally {
      setBusy(false);
    }
  }

  if (loading && !review) {
    return <LoadingBlock label="Loading review…" className="py-8" />;
  }

  if (error && !review) {
    return (
      <EmptyState title="Could not load review" description={error} actionLabel="Retry" onAction={() => void load()} />
    );
  }

  if (!review) return null;

  const pending = review.pending_gate;
  const gateMismatch = pending != null && pending !== gate;
  const noPending = pending == null;
  const canDecide = pending === gate && !busy && !polling;
  const evidence = review.evidence ?? {};

  return (
    <div>
      <Link to={`/runs/${runId}`} className="text-sm text-primary hover:underline">
        ← Back to Run
      </Link>

      <div className="mt-3 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold text-ink">
              {GATE_TITLES[gate] ?? `${gate} Review`}
            </h1>
            {pending === gate ? (
              <StatusPill tone="amber">Action Required</StatusPill>
            ) : (review.current_stage ?? "").match(/^H[1-5]_revising$/) ? (
              <StatusPill tone="primary">Revising…</StatusPill>
            ) : polling ? (
              <StatusPill tone="primary">Pipeline continuing…</StatusPill>
            ) : noPending ? (
              <StatusPill tone="muted">No pending gate</StatusPill>
            ) : (
              <StatusPill tone="primary">Pending {pending}</StatusPill>
            )}
          </div>
          <p className="mt-1 text-sm text-ink">
            {requirement || "Requirement summary unavailable."}
          </p>
          <p className="mt-1 text-xs text-muted">
            Run {shortRunId(runId)} · Stage {review.current_stage ?? "—"} · Status {review.run_status}
            {review.artifact_version != null ? ` · Artifact v${review.artifact_version}` : ""}
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => void load()} disabled={busy}>
          Refresh
        </Button>
      </div>

      {statusMsg ? (
        <p className="mt-3 rounded-md border border-primary/20 bg-primary-soft px-3 py-2 text-sm text-primary">
          {statusMsg}
        </p>
      ) : null}
      {error ? <ErrorBanner className="mt-2 mb-0" message={error} /> : null}

      {gateMismatch ? (
        <div className="mt-4 rounded-md border border-amber-200 bg-amber-soft px-4 py-3 text-sm">
          This URL is for <strong>{gate}</strong>, but the run is awaiting <strong>{pending}</strong>.
          <Link className="ml-2 text-primary hover:underline" to={`/runs/${runId}/review/${pending}`}>
            Open {pending} review →
          </Link>
        </div>
      ) : null}

      {noPending && !polling ? (
        <div className="mt-4">
          <EmptyState
            title="No gate awaiting review"
            description={review.message || "This run is not paused at a human gate."}
            actionLabel="View run detail"
            onAction={() => navigate(`/runs/${runId}`)}
          />
        </div>
      ) : (
        <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
          <Card
            title={
              gate === "H3"
                ? "Script review evidence"
                : gate === "H5"
                  ? "Release evidence (facts only)"
                  : "Review evidence"
            }
          >
            {polling && !Object.keys(evidence).length ? (
              <p className="text-sm text-muted">Waiting for revised artifacts…</p>
            ) : (
              <EvidenceForGate gate={pending === gate ? gate : gate} evidence={evidence} />
            )}
          </Card>

          <Card title="Review decision">
            <ReviewDecisionPanel
              reviewer={reviewer}
              onReviewerChange={setReviewer}
              comment={comment}
              onCommentChange={setComment}
              disabled={!canDecide}
              busy={busy || polling}
              onSubmit={onSubmit}
            />
          </Card>
        </div>
      )}
    </div>
  );
}
