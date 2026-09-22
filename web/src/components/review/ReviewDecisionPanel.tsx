import { useState } from "react";
import { Button } from "../ui/Button";
import { ConfirmDialog } from "../ui/ConfirmDialog";

export type ReviewDecision = "approve" | "request-changes" | "reject";

const COPY: Record<
  ReviewDecision,
  { title: string; message: string; label: string; variant: "approve" | "amber" | "danger" }
> = {
  approve: {
    title: "Approve this gate?",
    message: "The pipeline will continue to the next stage. This records your approval with the comment below.",
    label: "Approve",
    variant: "approve",
  },
  "request-changes": {
    title: "Request changes?",
    message:
      "The prior phase will re-run with your feedback, then this same gate will reopen with a new artifact version.\n\nThis is not a rejection — the run stays alive.",
    label: "Request Changes",
    variant: "amber",
  },
  reject: {
    title: "Reject this run?",
    message:
      "This is a terminal decision. The run will be marked failed at this gate and will not resume.\n\nUse Request Changes if you want a revision instead.",
    label: "Reject",
    variant: "danger",
  },
};

export function ReviewDecisionPanel({
  reviewer,
  onReviewerChange,
  comment,
  onCommentChange,
  disabled,
  busy,
  onSubmit,
}: {
  reviewer: string;
  onReviewerChange: (v: string) => void;
  comment: string;
  onCommentChange: (v: string) => void;
  disabled?: boolean;
  busy?: boolean;
  onSubmit: (decision: ReviewDecision) => Promise<void> | void;
}) {
  const [pending, setPending] = useState<ReviewDecision | null>(null);

  return (
    <>
      <div className="space-y-3">
        <label className="block text-sm">
          <span className="font-medium text-ink">Reviewer</span>
          <input
            className="mt-1 w-full rounded-md border border-border px-3 py-2 text-sm"
            value={reviewer}
            onChange={(e) => onReviewerChange(e.target.value)}
            placeholder="qa-lead"
            disabled={disabled || busy}
            required
          />
        </label>
        <label className="block text-sm">
          <span className="font-medium text-ink">Comments</span>
          <textarea
            className="mt-1 w-full rounded-md border border-border px-3 py-2 text-sm"
            rows={5}
            value={comment}
            onChange={(e) => onCommentChange(e.target.value)}
            placeholder="Optional notes for the audit trail"
            disabled={disabled || busy}
          />
        </label>
        <div className="flex flex-col gap-2">
          <Button
            variant="approve"
            disabled={disabled || busy || !reviewer.trim()}
            onClick={() => setPending("approve")}
          >
            Approve
          </Button>
          <Button
            variant="amber"
            disabled={disabled || busy || !reviewer.trim()}
            onClick={() => setPending("request-changes")}
          >
            Request Changes
          </Button>
          <Button
            variant="danger"
            disabled={disabled || busy || !reviewer.trim()}
            onClick={() => setPending("reject")}
          >
            Reject
          </Button>
        </div>
        <p className="text-xs text-muted">
          Request Changes revises and returns to this gate. Reject is terminal. Decisions are recorded for
          audit — no AI recommendation is shown.
        </p>
      </div>

      <ConfirmDialog
        open={pending != null}
        title={pending ? COPY[pending].title : ""}
        message={pending ? COPY[pending].message : ""}
        confirmLabel={pending ? COPY[pending].label : "Confirm"}
        confirmVariant={pending ? COPY[pending].variant : "primary"}
        busy={busy}
        onCancel={() => setPending(null)}
        onConfirm={async () => {
          if (!pending) return;
          const d = pending;
          await onSubmit(d);
          setPending(null);
        }}
      />
    </>
  );
}
