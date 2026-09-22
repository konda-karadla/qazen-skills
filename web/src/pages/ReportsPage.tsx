import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader, EmptyState } from "../components/ui/EmptyState";
import { ErrorBanner, LoadingSkeleton } from "../components/ui/AsyncState";
import { Card } from "../components/ui/Card";
import { MetricCard } from "../components/ui/MetricCard";
import { StatusPill } from "../components/ui/StatusPill";
import { Button } from "../components/ui/Button";
import { api, shortRunId } from "../api/client";
import type { ArtifactListItem, IntegrationsStatus, RunListItem } from "../api/types";

type S9Metrics = {
  total?: number;
  passed?: number;
  failed?: number;
  skipped?: number;
  pass_rate?: number;
};

type S9ReportContent = {
  aggregate_metrics?: S9Metrics;
  human_readable_summary?: string;
  trend_data?: { baseline_run_id?: string | null };
  run_id?: string;
};

type AllureContent = {
  enabled?: boolean;
  results_dir?: string | null;
  report_dir?: string | null;
  test_count?: number;
  result_files?: string[];
};

export function ReportsPage() {
  const [params, setParams] = useSearchParams();
  const runFilter = params.get("run") || "";
  const [runs, setRuns] = useState<RunListItem[]>([]);
  const [artifacts, setArtifacts] = useState<ArtifactListItem[]>([]);
  const [report, setReport] = useState<S9ReportContent | null>(null);
  const [allure, setAllure] = useState<AllureContent | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationsStatus | null>(null);
  const [runsWithReports, setRunsWithReports] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [runList, integ] = await Promise.all([
          api.listRuns({ limit: 50 }),
          api.getIntegrationsStatus(),
        ]);
        if (cancelled) return;
        setRuns(runList.runs);
        setIntegrations(integ);
        // Prefer an explicit run, else first completed/paused with later stages, else first run
        if (!runFilter && runList.runs[0]) {
          const preferred =
            runList.runs.find((r) => r.status === "completed") ||
            runList.runs.find((r) => r.pending_gate === "H4") ||
            runList.runs[0];
          const next = new URLSearchParams(params);
          next.set("run", preferred.run_id);
          setParams(next, { replace: true });
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load runs");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!runFilter) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError(null);
      setReport(null);
      setAllure(null);
      try {
        const arts = await api.getArtifacts(runFilter);
        if (cancelled) return;
        setArtifacts(arts.artifacts);
        const s9 = arts.artifacts.find((a) => a.type === "s9_report");
        const al = arts.artifacts.find((a) => a.type === "s9_allure_results");
        if (s9) {
          const detail = await api.getArtifact(runFilter, s9.artifact_id);
          if (!cancelled) setReport((detail.content || null) as S9ReportContent);
        }
        if (al) {
          const detail = await api.getArtifact(runFilter, al.artifact_id);
          if (!cancelled) setAllure((detail.content || null) as AllureContent);
        }
        // Count how many listed runs have s9 (sample up to 12 for honesty on trends)
        const sample = runs.slice(0, 12);
        let withReport = 0;
        await Promise.all(
          sample.map(async (r) => {
            try {
              const a = await api.getArtifacts(r.run_id);
              if (a.artifacts.some((x) => x.type === "s9_report")) withReport += 1;
            } catch {
              /* ignore */
            }
          }),
        );
        if (!cancelled) setRunsWithReports(withReport);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load report");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runFilter, runs]);

  const metrics = report?.aggregate_metrics;
  const passDisplay =
    metrics?.pass_rate != null ? `${(metrics.pass_rate * 100).toFixed(1)}%` : "—";

  const selectedRun = useMemo(
    () => runs.find((r) => r.run_id === runFilter) || null,
    [runs, runFilter],
  );

  return (
    <div>
      <PageHeader
        title="Reports"
        description="Current-run analytics from S9. No invented cross-run or flaky trends."
      />

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm text-muted">
          Run
          <select
            className="rounded-md border border-border bg-surface px-2.5 py-1.5 text-sm text-ink"
            value={runFilter}
            onChange={(e) => {
              const next = new URLSearchParams(params);
              if (e.target.value) next.set("run", e.target.value);
              else next.delete("run");
              setParams(next);
            }}
          >
            <option value="">Select a run…</option>
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {shortRunId(r.run_id)} · {r.status}
              </option>
            ))}
          </select>
        </label>
        {selectedRun ? (
          <Link to={`/runs/${selectedRun.run_id}`}>
            <Button variant="ghost" size="sm">
              Open run
            </Button>
          </Link>
        ) : null}
      </div>

      {error ? <ErrorBanner message={error} /> : null}
      {loading ? <LoadingSkeleton rows={3} label="Loading report…" /> : null}

      {!runFilter ? (
        <EmptyState title="Select a run" description="Choose a run to view its S9 report artifacts." />
      ) : !report && !loading ? (
        <EmptyState
          title="No S9 report for this run"
          description="Reports appear after S9. Pipeline may still be earlier, or reporting was skipped."
        />
      ) : report ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <MetricCard label="Total" value={metrics?.total ?? "—"} />
            <MetricCard label="Passed" value={metrics?.passed ?? "—"} tone="success" />
            <MetricCard label="Failed" value={metrics?.failed ?? "—"} tone="danger" />
            <MetricCard label="Skipped" value={metrics?.skipped ?? "—"} />
            <MetricCard
              label="Pass Rate"
              value={passDisplay}
              tone="success"
              hint="From this run’s S9 aggregate_metrics"
            />
          </div>

          <div className="mt-4 grid gap-4 xl:grid-cols-3">
            <Card className="xl:col-span-2" title="Human-readable summary">
              <pre className="whitespace-pre-wrap rounded-md bg-canvas p-3 font-mono text-xs leading-relaxed text-ink">
                {report.human_readable_summary || "No summary text on this artifact."}
              </pre>
            </Card>
            <Card title="Allure">
              {allure ? (
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted">Results</span>
                    <StatusPill tone={allure.enabled ? "success" : "muted"}>
                      {allure.enabled ? "Present" : "Disabled"}
                    </StatusPill>
                  </div>
                  <p className="text-xs text-muted">Tests: {allure.test_count ?? "—"}</p>
                  <p className="break-all font-mono text-[11px] text-muted">
                    {allure.results_dir || "No results_dir"}
                  </p>
                  {allure.report_dir ? (
                    <p className="break-all font-mono text-[11px] text-ink">{allure.report_dir}</p>
                  ) : (
                    <p className="text-xs text-muted">
                      HTML report not generated. Install Allure CLI and set ALLURE_GENERATE_HTML=true.
                    </p>
                  )}
                </div>
              ) : (
                <p className="text-sm text-muted">No s9_allure_results artifact on this run.</p>
              )}
            </Card>
          </div>

          <div className="mt-4 grid gap-4 md:grid-cols-2">
            <Card title="Cross-run trends">
              {runsWithReports >= 2 ? (
                <p className="text-sm text-muted">
                  {runsWithReports} sampled runs have S9 reports. Trend charts are not wired in v1 —
                  open each run’s report individually.
                </p>
              ) : (
                <EmptyState
                  title="Not enough historical runs"
                  description="Cross-run trend charts require ≥2 runs with S9 report data."
                />
              )}
            </Card>
            <Card title="Flakiness">
              <p className="text-sm text-muted">
                {integrations?.flaky_history.message || "No historical flaky-test data loaded"}
              </p>
              <StatusPill className="mt-2" tone="muted">
                Unavailable
              </StatusPill>
            </Card>
          </div>

          <Card className="mt-4" title="Report artifacts">
            <ul className="space-y-1 text-sm">
              {artifacts
                .filter((a) => a.type === "s9_report" || a.type === "s9_allure_results")
                .map((a) => (
                  <li key={a.artifact_id} className="flex justify-between gap-3">
                    <span className="font-mono text-xs">{a.type}</span>
                    <span className="text-xs text-muted">v{a.version}</span>
                  </li>
                ))}
            </ul>
          </Card>
        </>
      ) : null}
    </div>
  );
}
