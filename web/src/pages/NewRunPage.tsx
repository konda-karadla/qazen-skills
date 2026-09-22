import { useRef, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { PageHeader } from "../components/ui/EmptyState";
import { ErrorBanner } from "../components/ui/AsyncState";
import { Card } from "../components/ui/Card";
import { Button } from "../components/ui/Button";
import { ApiError, api } from "../api/client";
import type { RequirementType } from "../api/types";

const REQUIREMENT_TYPES: RequirementType[] = [
  "BRD",
  "User Story",
  "Jira",
  "API Requirement",
  "Other",
];

export function NewRunPage() {
  const navigate = useNavigate();
  const [raw, setRaw] = useState(
    "Users must log in with valid credentials and reach the dashboard.",
  );
  const [requirementId, setRequirementId] = useState("");
  const [requirementType, setRequirementType] = useState<RequirementType>("User Story");
  const [environment, setEnvironment] = useState("test");
  const [baseUrl, setBaseUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [labels, setLabels] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const submittingRef = useRef(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (submittingRef.current) return;
    const text = raw.trim();
    if (!text) {
      setError("Requirement text is required.");
      return;
    }
    submittingRef.current = true;
    setSubmitting(true);
    setError(null);
    try {
      const labelList = labels
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const body = {
        requirement_id: requirementId.trim() || undefined,
        input: {
          raw: text,
          requirement_type: requirementType,
          environment,
          ...(baseUrl.trim() ? { base_url: baseUrl.trim() } : {}),
          ...(branch.trim() ? { branch: branch.trim() } : {}),
          ...(labelList.length ? { labels: labelList } : {}),
        },
      };
      const res = await api.startRun(body);
      navigate(`/runs/${res.run_id}`);
    } catch (err) {
      submittingRef.current = false;
      setSubmitting(false);
      const msg =
        err instanceof ApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Failed to start run";
      setError(msg);
    }
  }

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Start a New QA Run"
        description="QAZen will normalize and analyze the requirement before generating test cases. Human approval is required at review gates."
      />
      <Card>
        <form className="space-y-4" onSubmit={onSubmit}>
          <label className="block">
            <span className="text-sm font-medium text-ink">Requirement / User Story</span>
            <textarea
              required
              rows={8}
              value={raw}
              onChange={(e) => setRaw(e.target.value)}
              className="mt-1.5 w-full rounded-md border border-border bg-canvas px-3 py-2 text-sm outline-none ring-primary focus:ring-2"
              placeholder="Users must log in with valid credentials and reach the dashboard."
            />
          </label>

          <label className="block text-sm">
            <span className="font-medium">Requirement ID (optional)</span>
            <input
              value={requirementId}
              onChange={(e) => setRequirementId(e.target.value)}
              className="mt-1.5 w-full rounded-md border border-border px-3 py-2"
              placeholder="REQ-123 or leave blank to auto-assign"
            />
          </label>

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="font-medium">Requirement Type</span>
              <select
                className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2"
                value={requirementType}
                onChange={(e) => setRequirementType(e.target.value as RequirementType)}
              >
                {REQUIREMENT_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
              <span className="mt-1 block text-xs text-muted">
                Passthrough metadata — not a Jira integration.
              </span>
            </label>
            <label className="block text-sm">
              <span className="font-medium">Environment</span>
              <select
                className="mt-1.5 w-full rounded-md border border-border bg-surface px-3 py-2"
                value={environment}
                onChange={(e) => setEnvironment(e.target.value)}
              >
                <option value="test">Test</option>
                <option value="staging">Staging</option>
                <option value="production">Production</option>
              </select>
            </label>
            <label className="block text-sm">
              <span className="font-medium">Application / Base URL</span>
              <input
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
                className="mt-1.5 w-full rounded-md border border-border px-3 py-2"
                placeholder="https://…"
              />
            </label>
            <label className="block text-sm">
              <span className="font-medium">Branch</span>
              <input
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                className="mt-1.5 w-full rounded-md border border-border px-3 py-2"
              />
            </label>
          </div>

          <label className="block text-sm">
            <span className="font-medium">Labels / tags (optional)</span>
            <input
              value={labels}
              onChange={(e) => setLabels(e.target.value)}
              className="mt-1.5 w-full rounded-md border border-border px-3 py-2"
              placeholder="Authentication, Smoke Test"
            />
            <span className="mt-1 block text-xs text-muted">Comma-separated. Stored as passthrough metadata.</span>
          </label>

          <p className="rounded-md bg-primary-soft px-3 py-2 text-xs text-primary">
            You will be taken to the run immediately. S1–S2 continue in the background until H1 is
            ready for review.
          </p>

          {error ? <ErrorBanner className="mb-0" message={error} /> : null}

          <Button type="submit" disabled={submitting}>
            {submitting ? "Starting QA Run…" : "Start QA Run"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
