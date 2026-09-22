import { useEffect, useState } from "react";
import { PageHeader, EmptyState } from "../components/ui/EmptyState";
import { ErrorBanner, LoadingSkeleton } from "../components/ui/AsyncState";
import { Card } from "../components/ui/Card";
import { StatusPill } from "../components/ui/StatusPill";
import { api } from "../api/client";
import type { IntegrationLabel, IntegrationsStatus } from "../api/types";

function toneFor(label: IntegrationLabel | string | undefined): "success" | "primary" | "muted" | "amber" {
  if (label === "Connected") return "success";
  if (label === "Configured") return "primary";
  if (label === "Mock") return "amber";
  return "muted";
}

export function CicdPage() {
  const [status, setStatus] = useState<IntegrationsStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const s = await api.getIntegrationsStatus();
        if (!cancelled) setStatus(s);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load CI status");
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
        title="CI/CD"
        description="Gate configuration and connection status. Labels are honest — no production Jenkins claims."
      />

      {error ? <ErrorBanner message={error} onRetry={() => setReloadKey((k) => k + 1)} /> : null}
      {loading ? <LoadingSkeleton rows={2} label="Loading CI/CD status…" /> : null}

      <div className="grid gap-4 lg:grid-cols-2">
        <Card title="Connection">
          <div className="flex items-center justify-between gap-3">
            <span className="text-sm text-muted">CI gate</span>
            <StatusPill tone={toneFor(status?.ci.label)}>{status?.ci.label ?? "—"}</StatusPill>
          </div>
          <p className="mt-3 text-sm text-ink">{status?.ci.detail || "—"}</p>
          <p className="mt-2 text-xs text-muted">Mode: {status?.ci.mode || "—"}</p>
        </Card>

        <Card title="Local evaluation thresholds (display-only)">
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Min classified pass rate</dt>
              <dd className="font-medium">80%</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Block on APPLICATION_BUG</dt>
              <dd className="font-medium">Yes</dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-muted">Push to Jenkins</dt>
              <dd>
                <StatusPill tone="muted">Not connected</StatusPill>
              </dd>
            </div>
          </dl>
          <p className="mt-3 text-xs text-muted">
            Thresholds shown for operator reference. Changing them here does not update a remote CI system.
          </p>
        </Card>
      </div>

      {status?.ci.label === "Mock" ? (
        <div className="mt-4">
          <EmptyState
            title="Mock CI gate"
            description="CI_GATE_MODE=mock evaluates locally only. Production Jenkins credentials and shared libraries are not wired."
          />
        </div>
      ) : null}
    </div>
  );
}
