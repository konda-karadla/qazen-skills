import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/ui/EmptyState";
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

function Row({
  label,
  value,
  detail,
}: {
  label: string;
  value: string;
  detail?: string | null;
}) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-2 border-b border-border py-2.5 last:border-0">
      <div>
        <p className="text-sm font-medium text-ink">{label}</p>
        {detail ? <p className="mt-0.5 text-xs text-muted">{detail}</p> : null}
      </div>
      <StatusPill tone={toneFor(value)}>{value}</StatusPill>
    </div>
  );
}

export function SettingsPage() {
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
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load settings");
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
        title="Settings"
        description="Configured vs unavailable integrations. No false claims for Jenkins, MCP, or ECS."
      />

      {error ? <ErrorBanner message={error} onRetry={() => setReloadKey((k) => k + 1)} /> : null}
      {loading ? <LoadingSkeleton rows={2} label="Loading settings…" /> : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <Card title="General">
          <Row label="Product" value="Configured" detail="QAZen Review UI v1" />
          <Row label="Environment selector" value="Configured" detail="UI-only filter; does not remount services" />
        </Card>

        <Card title="LLM Gateway">
          <Row
            label="Gateway"
            value={status?.llm_gateway.label ?? "—"}
            detail={
              status?.llm_gateway.detail ||
              (status?.llm_gateway.provider ? `Provider: ${status.llm_gateway.provider}` : null)
            }
          />
          {status?.llm_gateway.llm_profile ? (
            <Row label="LLM profile" value="Configured" detail={status.llm_gateway.llm_profile} />
          ) : null}
          {status?.llm_gateway.openai_model ? (
            <Row label="Model" value="Configured" detail={status.llm_gateway.openai_model} />
          ) : null}
          {status?.llm_gateway.openai_base_url ? (
            <Row
              label="Base URL"
              value="Configured"
              detail={status.llm_gateway.openai_base_url}
            />
          ) : null}
          <p className="mt-2 text-xs text-muted">
            {status?.llm_setup_hint ||
              "Set LLM_PROFILE / API keys in repo-root .env, then restart gateway :8000. Keys are never accepted here."}
          </p>
          <p className="mt-1 text-xs text-muted">
            View skill prompts under{" "}
            <Link className="text-primary hover:underline" to="/skills?id=S1">
              Skills
            </Link>
            .
          </p>
        </Card>

        <Card title="Playwright">
          <Row
            label="Runner"
            value={status?.playwright.label ?? "—"}
            detail={`${status?.playwright.runner || "playwright_test"} · MCP: ${status?.playwright.mcp ? "yes" : "no"}`}
          />
        </Card>

        <Card title="CI/CD">
          <Row
            label="CI gate"
            value={status?.ci.label ?? "—"}
            detail={status?.ci.detail}
          />
        </Card>

        <Card title="Storage">
          <Row label="MinIO / object store" value={status?.minio.label ?? "—"} />
        </Card>

        <Card title="Knowledge Base">
          <Row
            label="Knowledge API"
            value={status?.knowledge_base.label ?? "Not Wired"}
            detail={status?.knowledge_base.writable ? "Writable" : "Read-only; writes not wired"}
          />
        </Card>

        <Card title="Security">
          <Row label="Stop / cancel running execution" value="Not Available" detail={status?.stop_run.message} />
          <Row label="Auth / SSO" value="Coming Soon" detail="Local single-user UI for now" />
        </Card>

        <Card title="Users & notifications">
          <Row label="Users / roles" value="Coming Soon" />
          <Row label="Notifications" value="Coming Soon" detail="Bell badge shows pending review count only" />
          <Row label="Audit export" value="Not Wired" detail="Use per-run Timeline for now" />
        </Card>

        <Card title="Flaky history">
          <Row
            label="Flaky store"
            value="Not Available"
            detail={status?.flaky_history.message}
          />
        </Card>

        <Card title="Cloud hosting">
          <Row label="AWS ECS / EKS" value="Coming Soon" detail="Local Docker Compose pilot only" />
        </Card>
      </div>
    </div>
  );
}
